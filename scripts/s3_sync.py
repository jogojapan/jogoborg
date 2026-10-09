#!/usr/bin/env python3
"""S3/MinIO repository sync via boto3 (no aws CLI dependency).

Provides the same public API as the previous AWS-CLI-based implementation
(sync_repository, test_s3_connection, list_backups, restore_from_s3) so callers
are unaffected. Using boto3 directly removes the large `awscli` package from the
Docker image.
"""

import io
import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError


class S3Syncer:
    def __init__(self):
        self.logger = logging.getLogger('S3Syncer')

    # -- helpers ------------------------------------------------------------

    def _client(self, s3_config):
        """Build a boto3 S3 client from a Jogoborg s3_config dict.

        `endpoint` is used for MinIO/other S3-compatible services; AWS uses the
        default endpoint when it is unset.
        """
        kwargs = {
            'service_name': 's3',
            'aws_access_key_id': s3_config.get('access_key'),
            'aws_secret_access_key': s3_config.get('secret_key'),
        }
        if s3_config.get('region'):
            kwargs['region_name'] = s3_config['region']
        if s3_config.get('endpoint'):
            kwargs['endpoint_url'] = s3_config['endpoint']
        workers = int(s3_config.get('max_concurrent_requests') or 10)
        kwargs['config'] = BotoConfig(
            max_pool_connections=max(10, workers),
            connect_timeout=10,
            read_timeout=60,
        )
        return boto3.client(**kwargs)

    @staticmethod
    def _workers(s3_config):
        return max(1, int(s3_config.get('max_concurrent_requests') or 10))

    @staticmethod
    def _parse_bucket(bucket_raw):
        """Return (bucket_name, prefix_path) from a bucket field that may be a
        plain bucket, a `bucket/prefix`, or an `s3://bucket/prefix` URL."""
        value = bucket_raw
        if value.startswith('s3://'):
            value = value[5:]
        if '/' in value:
            bucket, _, prefix = value.partition('/')
            return bucket, prefix.strip('/')
        return value, ''

    @staticmethod
    def _remote_prefix(prefix, repo_name):
        return '/'.join(part for part in [prefix, repo_name] if part)

    @staticmethod
    def _obj_mtime(obj):
        lm = obj.get('LastModified')
        return lm.timestamp() if lm else 0

    def _list_prefix(self, client, bucket, prefix):
        """Yield all objects under a prefix, following pagination."""
        kwargs = {'Bucket': bucket}
        if prefix:
            kwargs['Prefix'] = prefix
        while True:
            result = client.list_objects_v2(**kwargs)
            for obj in result.get('Contents', []):
                yield obj
            if not result.get('IsTruncated') or not result.get('NextContinuationToken'):
                break
            kwargs['ContinuationToken'] = result['NextContinuationToken']

    @staticmethod
    def _excluded(rel, basename):
        """Excluded like the old `aws s3 sync --exclude` rules."""
        if basename.startswith('.jogoborg_'):
            return True
        if basename.endswith('.tmp'):
            return True
        return 'tmp' in rel.split('/')[:-1]

    def _walk(self, root):
        """Yield (relpath, abspath) for files under root, applying excludes."""
        for dirpath, _dirnames, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            for fn in filenames:
                rel = os.path.join(rel_dir, fn) if rel_dir != '.' else fn
                rel = rel.replace(os.sep, '/')
                if self._excluded(rel, fn):
                    continue
                yield rel, os.path.join(dirpath, fn)

    @staticmethod
    def _format_bytes(bytes_value):
        if bytes_value is None:
            return None
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_value)
        index = 0
        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1
        return f"{int(size)} {units[index]}" if index == 0 else f"{size:.1f} {units[index]}"

    @staticmethod
    def _human_elapsed(seconds):
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes}m {secs}s" if minutes else f"{secs}s"

    # -- public API ----------------------------------------------------------

    def sync_repository(self, s3_config, repo_path, logger):
        """Sync a Borg repository to S3 (upload new/changed, delete removed).

        Returns a stats dict with data_transferred, elapsed_time, file_count.
        """
        start = time.time()
        bucket, prefix = self._parse_bucket(s3_config['bucket'])
        repo_name = os.path.basename(repo_path)
        remote_prefix = self._remote_prefix(prefix, repo_name)
        client = self._client(s3_config)

        local = dict(self._walk(repo_path))

        remote = {}
        for obj in self._list_prefix(client, bucket, remote_prefix):
            key = obj['Key']
            rel = key[len(remote_prefix) + 1:] if remote_prefix else key
            remote[rel] = obj

        # Upload files that are new, a different size, or have a newer mtime.
        to_upload = []
        for rel, abspath in local.items():
            robj = remote.get(rel)
            size = os.path.getsize(abspath)
            mtime = int(os.path.getmtime(abspath))
            if robj is None or robj.get('Size') != size or self._obj_mtime(robj) < mtime:
                to_upload.append((rel, abspath))

        transferred = 0
        workers = self._workers(s3_config)

        def do_upload(rel_abspath):
            rel, abspath = rel_abspath
            key = f"{remote_prefix}/{rel}" if remote_prefix else rel
            extra = {}
            if s3_config.get('storage_class'):
                extra['StorageClass'] = s3_config['storage_class']
            client.upload_file(abspath, bucket, key, ExtraArgs=extra or None)
            return os.path.getsize(abspath)

        if to_upload:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for size in pool.map(do_upload, to_upload):
                    transferred += size

        # Delete remote objects that no longer exist locally (aws --delete).
        to_delete = [rel for rel in remote if rel not in local]

        def do_delete(rel):
            key = f"{remote_prefix}/{rel}" if remote_prefix else rel
            client.delete_object(Bucket=bucket, Key=key)

        if to_delete:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(do_delete, to_delete))

        elapsed = time.time() - start
        file_count = len(to_upload) + len(to_delete)
        if transferred > 0:
            data_transferred = self._format_bytes(transferred)
        elif file_count > 0:
            data_transferred = f"{file_count} file(s)"
        else:
            data_transferred = None

        logger.info(
            f"S3 sync: uploaded {len(to_upload)}, deleted {len(to_delete)} "
            f"({elapsed:.1f}s)"
        )
        return {
            'data_transferred': data_transferred,
            'elapsed_time': self._human_elapsed(elapsed),
            'file_count': str(file_count),
        }

    def test_s3_connection(self, s3_config):
        """Verify read and write access to the bucket."""
        try:
            bucket, prefix = self._parse_bucket(s3_config['bucket'])
            client = self._client(s3_config)

            # Read access.
            try:
                client.list_objects_v2(Bucket=bucket, MaxKeys=1)
            except ClientError as e:
                msg = (e.response.get('Error', {}) or {}).get('Message', str(e))
                return False, f"S3 read access failed: {msg or e}"

            # Write access: put + delete a small test file.
            test_name = f".jogoborg_test_{int(time.time())}"
            key = f"{prefix}/{test_name}" if prefix else test_name
            try:
                client.put_object(Bucket=bucket, Key=key, Body=b"jogoborg-s3-test")
                client.delete_object(Bucket=bucket, Key=key)
            except ClientError as e:
                code = (e.response.get('Error', {}) or {}).get('Code', '')
                if code in ('AccessDenied', 'Forbidden', '403'):
                    return False, f"S3 permission denied: {e}"
                return False, f"S3 write failed: {e}"
            except Exception as e:
                return False, f"S3 write failed: {e}"

            return True, "S3 connection successful with read and write access verified"
        except Exception as e:
            return False, f"S3 connection test error: {str(e)}"

    def list_backups(self, s3_config, repo_name=None):
        """List objects available in S3 (optionally under a repository)."""
        try:
            bucket, prefix = self._parse_bucket(s3_config['bucket'])
            key_prefix = self._remote_prefix(prefix, repo_name) if repo_name else prefix
            client = self._client(s3_config)
            files = []
            for obj in self._list_prefix(client, bucket, key_prefix):
                files.append({
                    'name': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                })
            return files
        except Exception as e:
            self.logger.error(f"Failed to list S3 backups: {e}")
            raise

    def restore_from_s3(self, s3_config, repo_name, local_path, logger):
        """Download a repository from S3 into local_path."""
        bucket, prefix = self._parse_bucket(s3_config['bucket'])
        remote_prefix = self._remote_prefix(prefix, repo_name)
        os.makedirs(local_path, exist_ok=True)
        client = self._client(s3_config)
        objs = list(self._list_prefix(client, bucket, remote_prefix))
        workers = self._workers(s3_config)

        def do_get(key):
            rel = key[len(remote_prefix) + 1:] if remote_prefix else key
            dest = os.path.join(local_path, *rel.split('/'))
            os.makedirs(os.path.dirname(dest) or local_path, exist_ok=True)
            client.download_file(bucket, key, dest)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(do_get, [o['Key'] for o in objs]))

        logger.info(f"Restored {len(objs)} files from S3")