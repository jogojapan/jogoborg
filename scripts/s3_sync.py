#!/usr/bin/env python3
import os
import subprocess
import tempfile
import json
import logging
from datetime import datetime

class S3Syncer:
    def __init__(self):
        self.logger = logging.getLogger('S3Syncer')
        config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
        self.rclone_config_dir = os.path.join(config_dir, 'rclone')
        
        # Ensure rclone config directory exists
        os.makedirs(self.rclone_config_dir, exist_ok=True)

    def sync_repository(self, s3_config, repo_path, logger):
        """Sync a Borg repository to S3 using rclone."""
        try:
            # Create rclone remote configuration
            remote_name = self._create_rclone_config(s3_config)
            
            # Determine source and destination paths
            repo_name = os.path.basename(repo_path)
            s3_bucket_raw = s3_config['bucket']
            
            # Parse bucket field to handle s3:// URLs and extract bucket name and prefix
            if s3_bucket_raw.startswith('s3://'):
                # Remove s3:// prefix and split into bucket and path
                bucket_and_path = s3_bucket_raw[5:]  # Remove 's3://'
                if '/' in bucket_and_path:
                    bucket_name = bucket_and_path.split('/')[0]
                    prefix_path = '/'.join(bucket_and_path.split('/')[1:])
                    # Ensure no double slashes in path construction
                    s3_path = f"{remote_name}:{bucket_name}/{prefix_path.strip('/')}/{repo_name}"
                else:
                    # Just bucket name, no prefix
                    s3_path = f"{remote_name}:{bucket_and_path}/{repo_name}"
            else:
                # Assume it's already just the bucket name/path - handle potential slashes
                s3_path = f"{remote_name}:{s3_bucket_raw.strip('/')}/{repo_name}"
            
            # Run rclone sync with options to only copy modified files
            self._run_rclone_sync(repo_path, s3_path, logger)
            
            # Update last sync timestamp
            self._update_last_sync_time(repo_path)
            
            logger.info(f"Successfully synced repository to S3: {s3_path}")
            
        except Exception as e:
            logger.error(f"S3 sync failed: {e}")
            raise

    def _create_rclone_config(self, s3_config):
        """Create rclone configuration for the S3 remote."""
        provider = s3_config.get('provider', 'aws')
        remote_name = f"s3_{provider}_{hash(json.dumps(s3_config, sort_keys=True)) % 10000}"
        
        config_file = os.path.join(self.rclone_config_dir, 'rclone.conf')
        
        # Read existing config
        existing_config = ""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                existing_config = f.read()
        
        # Check if this remote already exists
        if f"[{remote_name}]" in existing_config:
            return remote_name
        
        # Create new remote configuration
        if provider == 'aws':
            region = s3_config.get('region', 'us-east-1')
            remote_config = f"""
[{remote_name}]
type = s3
provider = AWS
access_key_id = {s3_config['access_key']}
secret_access_key = {s3_config['secret_key']}
region = {region}
storage_class = {s3_config.get('storage_class', 'STANDARD')}
"""
        elif provider == 'minio':
            remote_config = f"""
[{remote_name}]
type = s3
provider = Minio
access_key_id = {s3_config['access_key']}
secret_access_key = {s3_config['secret_key']}
endpoint = {s3_config['endpoint']}
"""
        else:
            raise ValueError(f"Unsupported S3 provider: {provider}")
        
        # Append to config file
        with open(config_file, 'a') as f:
            f.write(remote_config)
        
        # Set secure permissions
        os.chmod(config_file, 0o600)
        
        return remote_name

    def _run_rclone_sync(self, source_path, dest_path, logger):
        """Run rclone sync command with appropriate options."""
        
        # Get the last sync time
        last_sync_file = os.path.join(source_path, '.jogoborg_last_sync')
        last_sync_time = None
        
        if os.path.exists(last_sync_file):
            try:
                with open(last_sync_file, 'r') as f:
                    last_sync_time = f.read().strip()
            except Exception:
                pass
        
        # Build rclone command
        cmd = [
            'rclone', 'sync',
            source_path, dest_path,
            '--config', os.path.join(self.rclone_config_dir, 'rclone.conf'),
            '--verbose',
            '--stats', '30s',
            '--transfers', '4',
            '--checkers', '8',
        ]
        
        # If we have a last sync time, only sync files modified since then
        if last_sync_time:
            cmd.extend(['--max-age', self._calculate_max_age(last_sync_time)])
        
        # Add filters to exclude temporary files
        cmd.extend([
            '--exclude', '.jogoborg_*',
            '--exclude', 'tmp/**',
            '--exclude', '*.tmp',
        ])
        
        logger.info(f"Running rclone sync: {' '.join(cmd)}")
        
        # Execute rclone command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True
        )
        
        # Capture both stdout and stderr
        stdout, stderr = process.communicate()
        
        # Log stdout at appropriate levels based on content
        if stdout:
            for line in stdout.strip().split('\n'):
                if line.strip():
                    line_content = line.strip()
                    # Log INFO and NOTICE messages at info level, others at debug
                    if 'INFO' in line_content or 'NOTICE' in line_content:
                        logger.info(f"rclone: {line_content}")
                    else:
                        logger.debug(f"rclone: {line_content}")
        
        # Only log stderr as errors if they contain actual error keywords
        if stderr:
            for line in stderr.strip().split('\n'):
                if line.strip():
                    line_content = line.strip()
                    if 'ERROR' in line_content.upper() or 'FATAL' in line_content.upper():
                        logger.error(f"rclone error: {line_content}")
                    elif 'WARNING' in line_content.upper() or 'WARN' in line_content.upper():
                        logger.warning(f"rclone warning: {line_content}")
                    else:
                        logger.info(f"rclone: {line_content}")
        
        if process.returncode != 0:
            # Extract key error messages from rclone output for better reporting
            error_summary = self._extract_key_errors(stderr)
            error_msg = f"rclone sync failed with return code {process.returncode}"
            if error_summary:
                error_msg += f"\n\nKey errors:\n{error_summary}"
            elif stderr:
                error_msg += f". Errors: {stderr.strip()}"
            raise Exception(error_msg)

    def _extract_key_errors(self, stderr):
        """Extract key error messages from rclone stderr output.
        
        Filters out duplicate errors and retry attempts, keeping only the most
        important error messages for user notification.
        """
        key_errors = []
        seen_errors = set()  # Track unique errors to avoid duplicates
        
        if not stderr:
            return ""
        
        lines = stderr.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for ERROR lines
            if not line or 'ERROR' not in line:
                continue
            
            # Skip retry attempt lines - these are just informational
            if 'Attempt' in line and 'failed with' in line:
                continue
            
            # Extract the part after 'ERROR'
            if 'ERROR' in line:
                # Split on 'ERROR' and get everything after it
                error_part = line.split('ERROR', 1)[1].strip()
                # Clean up leading colons and spaces (handles ': : ' patterns)
                error_part = error_part.lstrip(': ').lstrip()

                
                # Check for specific error types that are important to report
                important_error_types = [
                    'BucketRegionError', 'AccessDenied', 'InvalidAccessKeyId', 
                    'SignatureDoesNotMatch', 'NoSuchBucket', 'NoSuchKey',
                    'Unauthorized'
                ]
                
                # Check if this is an important error type
                is_important = any(err_type in error_part for err_type in important_error_types)
                
                # Also flag common S3 permission/access errors
                if not is_important:
                    is_important = any(phrase in error_part.lower() for phrase in 
                                      ['not authorized', 'denied', 'permission', 'credentials',
                                       'failed to update region', 'status code: 403'])
                
                if is_important:
                    # Try to extract a concise error message
                    # For multi-line errors in a single line, just take the key part
                    if len(error_part) > 150:
                        # For very long error messages, try to extract the key bit
                        if 'BucketRegionError' in error_part:
                            error_part = 'BucketRegionError: ' + error_part.split('BucketRegionError')[-1].split('\n')[0]
                        elif 'AccessDenied' in error_part:
                            error_part = 'AccessDenied: ' + error_part.split('AccessDenied')[-1].split('\n')[0]
                    
                    # Avoid adding duplicate errors
                    if error_part not in seen_errors:
                        key_errors.append(error_part)
                        seen_errors.add(error_part)
        
        # If we found key errors, format them nicely
        if key_errors:
            # Remove duplicates while preserving order
            unique_errors = []
            for err in key_errors:
                if err not in unique_errors:
                    unique_errors.append(err)
            
            # Format as a bulleted list, limiting to top 5 errors
            return '\n- '.join([''] + unique_errors[:5])
        
        return ""

    def _calculate_max_age(self, last_sync_time):
        """Calculate max-age parameter for rclone based on last sync time."""
        try:
            last_sync = datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
            now = datetime.now(last_sync.tzinfo)
            diff = now - last_sync
            
            # Add some buffer time to ensure we don't miss files
            total_seconds = int(diff.total_seconds()) + 300  # Add 5 minutes buffer
            
            return f"{total_seconds}s"
            
        except Exception:
            # If we can't parse the time, sync everything
            return "1000d"  # 1000 days should cover everything

    def _update_last_sync_time(self, repo_path):
        """Update the last sync timestamp file."""
        last_sync_file = os.path.join(repo_path, '.jogoborg_last_sync')
        
        try:
            with open(last_sync_file, 'w') as f:
                f.write(datetime.utcnow().isoformat() + 'Z')
        except Exception as e:
            self.logger.warning(f"Failed to update last sync time: {e}")

    def test_s3_connection(self, s3_config):
        """Test S3 connection and credentials."""
        try:
            remote_name = self._create_rclone_config(s3_config)
            
            # Test with rclone lsd (list directories)
            cmd = [
                'rclone', 'lsd',
                f"{remote_name}:{s3_config['bucket']}",
                '--config', os.path.join(self.rclone_config_dir, 'rclone.conf'),
                '--max-depth', '1'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "S3 connection successful"
            else:
                return False, f"S3 connection failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "S3 connection test timed out"
        except Exception as e:
            return False, f"S3 connection test error: {str(e)}"

    def list_backups(self, s3_config, repo_name=None):
        """List backups available in S3."""
        try:
            remote_name = self._create_rclone_config(s3_config)
            bucket = s3_config['bucket']
            
            if repo_name:
                path = f"{remote_name}:{bucket}/{repo_name}"
            else:
                path = f"{remote_name}:{bucket}"
            
            cmd = [
                'rclone', 'lsl',
                path,
                '--config', os.path.join(self.rclone_config_dir, 'rclone.conf'),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return self._parse_rclone_list_output(result.stdout)
            else:
                raise Exception(f"Failed to list S3 backups: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Failed to list S3 backups: {e}")
            raise

    def _parse_rclone_list_output(self, output):
        """Parse rclone lsl output into structured data."""
        files = []
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.strip().split(None, 3)
            if len(parts) >= 4:
                size = int(parts[0])
                date_str = f"{parts[1]} {parts[2]}"
                filename = parts[3]
                
                files.append({
                    'name': filename,
                    'size': size,
                    'modified': date_str,
                })
        
        return files

    def restore_from_s3(self, s3_config, repo_name, local_path, logger):
        """Restore a repository from S3 to local storage."""
        try:
            remote_name = self._create_rclone_config(s3_config)
            s3_bucket_raw = s3_config['bucket']
            
            # Parse bucket field to handle s3:// URLs and extract bucket name and prefix
            if s3_bucket_raw.startswith('s3://'):
                # Remove s3:// prefix and split into bucket and path
                bucket_and_path = s3_bucket_raw[5:]  # Remove 's3://'
                if '/' in bucket_and_path:
                    bucket_name = bucket_and_path.split('/')[0]
                    prefix_path = '/'.join(bucket_and_path.split('/')[1:])
                    # Ensure no double slashes in path construction
                    s3_path = f"{remote_name}:{bucket_name}/{prefix_path.strip('/')}/{repo_name}"
                else:
                    # Just bucket name, no prefix
                    s3_path = f"{remote_name}:{bucket_and_path}/{repo_name}"
            else:
                # Assume it's already just the bucket name/path - handle potential slashes
                s3_path = f"{remote_name}:{s3_bucket_raw.strip('/')}/{repo_name}"
            
            # Ensure local directory exists
            os.makedirs(local_path, exist_ok=True)
            
            cmd = [
                'rclone', 'sync',
                s3_path, local_path,
                '--config', os.path.join(self.rclone_config_dir, 'rclone.conf'),
                '--verbose',
                '--stats', '30s',
                '--transfers', '4',
                '--checkers', '8',
            ]
            
            logger.info(f"Restoring from S3: {s3_path} -> {local_path}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            # Log output in real-time
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    logger.debug(f"rclone restore: {line.strip()}")
            
            process.wait()
            
            if process.returncode != 0:
                raise Exception(f"rclone restore failed with return code {process.returncode}")
            
            logger.info("Repository restored successfully from S3")
            
        except Exception as e:
            logger.error(f"S3 restore failed: {e}")
            raise

if __name__ == '__main__':
    # This can be used for testing S3 sync functionality
    pass