#!/usr/bin/env python3
import os
import subprocess
import tempfile
import logging
from datetime import datetime
import time

class S3Syncer:
    def __init__(self):
        self.logger = logging.getLogger('S3Syncer')

    def sync_repository(self, s3_config, repo_path, logger):
        """Sync a Borg repository to S3 using AWS CLI.
        
        Args:
            s3_config: S3 configuration dictionary
            repo_path: Path to the repository
            logger: Logger instance
        
        Returns:
            dict: Statistics from the sync operation including data_transferred and elapsed_time
        """
        try:
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
                    s3_path = f"s3://{bucket_name}/{prefix_path.strip('/')}/{repo_name}"
                else:
                    # Just bucket name, no prefix
                    s3_path = f"s3://{bucket_and_path}/{repo_name}"
            else:
                # Assume it's already just the bucket name/path - handle potential slashes
                s3_path = f"s3://{s3_bucket_raw.strip('/')}/{repo_name}"
            
            # Prepare AWS credentials
            env = os.environ.copy()
            env['AWS_ACCESS_KEY_ID'] = s3_config['access_key']
            env['AWS_SECRET_ACCESS_KEY'] = s3_config['secret_key']
            if s3_config.get('region'):
                env['AWS_DEFAULT_REGION'] = s3_config['region']
            
            # Run aws sync
            stats = self._run_aws_sync(repo_path, s3_path, s3_config, env, logger)
            
            logger.info(f"Successfully synced repository to S3: {s3_path}")
            
            return stats
            
        except Exception as e:
            logger.error(f"S3 sync failed: {e}")
            raise

    def _run_aws_sync(self, source_path, dest_path, s3_config, env, logger):
        """Run aws sync command.
        
        Args:
            source_path: Source directory for sync
            dest_path: Destination S3 path
            s3_config: S3 configuration dictionary
            env: Environment variables with AWS credentials
            logger: Logger instance
        
        Returns:
            dict: Statistics including data_transferred and elapsed_time
        """
        
        # Build aws sync command
        cmd = [
            'aws', 's3', 'sync',
            source_path, dest_path,
            '--delete',
        ]
        
        # Add region if specified
        if s3_config.get('region'):
            cmd.extend(['--region', s3_config['region']])
        
        # Add storage class if specified
        if s3_config.get('storage_class'):
            cmd.extend(['--storage-class', s3_config['storage_class']])
        
        # Add filters to exclude temporary files
        cmd.append('--exclude=.jogoborg_*')
        cmd.append('--exclude=tmp/*')
        cmd.append('--exclude=*.tmp')
        
        logger.info(f"Running aws sync: {' '.join(cmd)}")
        
        # Create temporary AWS config file with S3 sync settings if provided
        temp_config_file = None
        try:
            temp_config_file = self._create_aws_config_file(s3_config, logger)
            if temp_config_file:
                env['AWS_CONFIG_FILE'] = temp_config_file
                logger.info(f"Using custom AWS config file for S3 sync")
            
            # Track elapsed time
            start_time = time.time()
            
            # Execute aws sync command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                env=env
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract transfer statistics
            stats = self._extract_aws_sync_stats(stdout, stderr, elapsed_time)
            
            # Log stdout
            if stdout:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        logger.debug(f"aws sync: {line.strip()}")
            
            # Log stderr
            if stderr:
                for line in stderr.strip().split('\n'):
                    if line.strip():
                        if 'error' in line.lower() or 'failed' in line.lower():
                            logger.error(f"aws sync error: {line.strip()}")
                        else:
                            logger.info(f"aws sync: {line.strip()}")
            
            if process.returncode != 0:
                error_msg = f"aws sync failed with return code {process.returncode}"
                if stderr:
                    error_msg += f". Error: {stderr.strip()}"
                raise Exception(error_msg)
            
            return stats
        
        finally:
            # Clean up temporary config file
            if temp_config_file:
                try:
                    os.unlink(temp_config_file)
                except Exception as e:
                    logger.debug(f"Failed to delete temporary AWS config file: {e}")

    def _extract_aws_sync_stats(self, stdout, stderr, elapsed_time):
        """Extract transfer statistics from aws sync output.
        
        Parses aws sync output to extract:
        - file_count: Number of files transferred (from output lines)
        - elapsed_time: Total elapsed time
        - data_transferred: Estimated size of transferred files in human-readable format
        
        Returns:
            dict: Statistics with keys 'data_transferred', 'elapsed_time', and 'file_count'
        """
        stats = {
            'data_transferred': None,
            'elapsed_time': None,
            'file_count': None
        }
        
        # Format elapsed time as a readable string
        minutes = int(elapsed_time) // 60
        seconds = int(elapsed_time) % 60
        if minutes > 0:
            stats['elapsed_time'] = f"{minutes}m {seconds}s"
        else:
            stats['elapsed_time'] = f"{seconds}s"
        
        # Parse file operations from stdout to extract file paths and calculate transferred bytes
        # AWS CLI outputs lines like:
        # "upload: /local/path/to/file to s3://bucket/path/file"
        # "delete: s3://bucket/path/file"
        transferred_bytes = 0
        file_count = 0
        
        if stdout:
            for line in stdout.split('\n'):
                line_lower = line.lower()
                if 'upload:' in line_lower:
                    # Extract the local file path (between "upload: " and " to s3://")
                    try:
                        parts = line.split(' to s3://')
                        if len(parts) >= 1:
                            local_path = parts[0].replace('upload:', '').strip()
                            # Get the file size
                            if os.path.exists(local_path):
                                file_size = os.path.getsize(local_path)
                                transferred_bytes += file_size
                            file_count += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to parse upload line: {e}")
                        file_count += 1
                elif 'delete:' in line_lower:
                    # For deletions, we can't know the exact size, so just count them
                    file_count += 1
        
        if file_count > 0:
            stats['file_count'] = str(file_count)
        
        # Format estimated data transferred
        if transferred_bytes > 0 or file_count > 0:
            if transferred_bytes > 0:
                stats['data_transferred'] = self._format_bytes(transferred_bytes)
            else:
                # If we only had deletes and no uploads, show file count
                stats['data_transferred'] = f"{file_count} file(s)"
        
        return stats

    def _format_bytes(self, bytes_value):
        """Format bytes to human-readable format.
        
        Args:
            bytes_value: Number of bytes
            
        Returns:
            str: Formatted string (e.g., "1.5 MB", "2.3 GB")
        """
        if bytes_value is None:
            return None
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_value)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def _create_aws_config_file(self, s3_config, logger):
        """Create a temporary AWS config file with S3 sync settings.
        
        Args:
            s3_config: S3 configuration dictionary
            logger: Logger instance
        
        Returns:
            str: Path to temporary config file, or None if no S3 settings to configure
        """
        # Check if any S3 sync settings are provided
        has_sync_settings = (
            s3_config.get('max_concurrent_requests') or
            s3_config.get('max_queue_size') or
            s3_config.get('multipart_chunksize')
        )
        
        if not has_sync_settings:
            return None
        
        try:
            # Build AWS config content
            config_content = "[default]\n"
            config_content += "s3 =\n"
            
            if s3_config.get('max_concurrent_requests'):
                config_content += f"    max_concurrent_requests = {s3_config['max_concurrent_requests']}\n"
            
            if s3_config.get('max_queue_size'):
                config_content += f"    max_queue_size = {s3_config['max_queue_size']}\n"
            
            if s3_config.get('multipart_chunksize'):
                config_content += f"    multipart_chunksize = {s3_config['multipart_chunksize']}\n"
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
                f.write(config_content)
                temp_file = f.name
            
            logger.info(f"AWS S3 sync settings: max_concurrent_requests={s3_config.get('max_concurrent_requests', 10)}, max_queue_size={s3_config.get('max_queue_size', 1000)}, multipart_chunksize={s3_config.get('multipart_chunksize', '8MB')}")
            logger.info(f"Created temporary AWS config file at {temp_file}")
            return temp_file
        
        except Exception as e:
            logger.warning(f"Failed to create temporary AWS config file: {e}")
            return None

    def test_s3_connection(self, s3_config):
        """Test S3 connection and credentials, including write permissions.
        
        This test verifies:
        1. Bucket exists and is accessible (read access)
        2. User has write permissions (by creating and deleting a test file)
        3. Region configuration is correct
        """
        try:
            # Extract bucket name from bucket field
            bucket_raw = s3_config['bucket']
            if bucket_raw.startswith('s3://'):
                bucket_and_path = bucket_raw[5:]
                if '/' in bucket_and_path:
                    bucket_name = bucket_and_path.split('/')[0]
                    prefix_path = '/'.join(bucket_and_path.split('/')[1:])
                else:
                    bucket_name = bucket_and_path
                    prefix_path = ''
            else:
                parts = bucket_raw.split('/')
                bucket_name = parts[0]
                prefix_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
            
            # Prepare AWS credentials
            env = os.environ.copy()
            env['AWS_ACCESS_KEY_ID'] = s3_config['access_key']
            env['AWS_SECRET_ACCESS_KEY'] = s3_config['secret_key']
            if s3_config.get('region'):
                env['AWS_DEFAULT_REGION'] = s3_config['region']
            
            # Step 1: Test read access by listing bucket contents
            self.logger.info(f"Testing S3 read access...")
            list_cmd = [
                'aws', 's3', 'ls',
                f"s3://{bucket_name}",
            ]
            
            if s3_config.get('region'):
                list_cmd.extend(['--region', s3_config['region']])
            
            result = subprocess.run(
                list_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            self.logger.info(f"aws s3 ls returned with code: {result.returncode}")
            
            if result.returncode != 0:
                stderr_lines = result.stderr.strip().split('\n')
                error_msg = stderr_lines[-1] if stderr_lines else result.stderr
                self.logger.error(f"S3 read access test failed: {error_msg}")
                return False, f"S3 read access failed: {error_msg}"
            
            # Step 2: Test write access by creating and deleting a test file
            self.logger.info(f"Testing S3 write access...")
            
            # Create a temporary test file
            test_file_name = f".jogoborg_test_{int(datetime.now().timestamp())}"
            test_content = "jogoborg-s3-test"
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(test_content)
                temp_local_path = f.name
            
            try:
                # Build S3 test path
                if prefix_path:
                    s3_test_file = f"s3://{bucket_name}/{prefix_path.strip('/')}/{test_file_name}"
                else:
                    s3_test_file = f"s3://{bucket_name}/{test_file_name}"
                
                # Upload test file
                upload_cmd = [
                    'aws', 's3', 'cp',
                    temp_local_path,
                    s3_test_file,
                ]
                
                if s3_config.get('region'):
                    upload_cmd.extend(['--region', s3_config['region']])
                
                self.logger.info(f"Uploading test file: {test_file_name}")
                result = subprocess.run(
                    upload_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
                
                if result.returncode != 0:
                    stderr_lines = result.stderr.strip().split('\n')
                    error_msg = stderr_lines[-1] if stderr_lines else result.stderr
                    self.logger.error(f"S3 write test failed: {error_msg}")
                    
                    # Check for permission errors
                    if 'AccessDenied' in result.stderr or 'Forbidden' in result.stderr:
                        return False, f"S3 permission denied: {error_msg}"
                    elif '403' in result.stderr:
                        return False, f"S3 permission denied (403): {error_msg}"
                    else:
                        return False, f"S3 write failed: {error_msg}"
                
                self.logger.info(f"Test file uploaded successfully")
                
                # Delete test file
                delete_cmd = [
                    'aws', 's3', 'rm',
                    s3_test_file,
                ]
                
                if s3_config.get('region'):
                    delete_cmd.extend(['--region', s3_config['region']])
                
                self.logger.info(f"Deleting test file...")
                result = subprocess.run(
                    delete_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
                
                if result.returncode != 0:
                    self.logger.warning(f"Failed to delete test file (non-critical): {result.stderr}")
                    # Don't fail the test if deletion fails, as it's not critical
                else:
                    self.logger.info(f"Test file deleted successfully")
                
                return True, "S3 connection successful with read and write access verified"
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_local_path)
                except Exception as e:
                    self.logger.debug(f"Failed to delete temporary file: {e}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("S3 connection test timed out")
            return False, "S3 connection test timed out"
        except Exception as e:
            self.logger.error(f"S3 connection test error: {e}")
            return False, f"S3 connection test error: {str(e)}"

    def list_backups(self, s3_config, repo_name=None):
        """List backups available in S3."""
        try:
            # Extract bucket name and prefix from bucket field
            bucket_raw = s3_config['bucket']
            if bucket_raw.startswith('s3://'):
                bucket_and_path = bucket_raw[5:]
                if '/' in bucket_and_path:
                    bucket_name = bucket_and_path.split('/')[0]
                    prefix_path = '/'.join(bucket_and_path.split('/')[1:])
                else:
                    bucket_name = bucket_and_path
                    prefix_path = ''
            else:
                parts = bucket_raw.split('/')
                bucket_name = parts[0]
                prefix_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
            
            # Prepare AWS credentials
            env = os.environ.copy()
            env['AWS_ACCESS_KEY_ID'] = s3_config['access_key']
            env['AWS_SECRET_ACCESS_KEY'] = s3_config['secret_key']
            if s3_config.get('region'):
                env['AWS_DEFAULT_REGION'] = s3_config['region']
            
            # Build S3 path
            if repo_name:
                if prefix_path:
                    s3_path = f"s3://{bucket_name}/{prefix_path.strip('/')}/{repo_name}"
                else:
                    s3_path = f"s3://{bucket_name}/{repo_name}"
            else:
                if prefix_path:
                    s3_path = f"s3://{bucket_name}/{prefix_path.strip('/')}"
                else:
                    s3_path = f"s3://{bucket_name}"
            
            cmd = [
                'aws', 's3', 'ls',
                s3_path,
                '--recursive',
            ]
            
            if s3_config.get('region'):
                cmd.extend(['--region', s3_config['region']])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            if result.returncode == 0:
                return self._parse_aws_list_output(result.stdout)
            else:
                raise Exception(f"Failed to list S3 backups: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Failed to list S3 backups: {e}")
            raise

    def _parse_aws_list_output(self, output):
        """Parse aws s3 ls output into structured data."""
        files = []
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
                
            # Format: "2023-10-15 14:30:45     1234567 filename"
            parts = line.strip().split(None, 3)
            if len(parts) >= 4:
                try:
                    date_str = f"{parts[0]} {parts[1]}"
                    size = int(parts[2])
                    filename = parts[3]
                    
                    files.append({
                        'name': filename,
                        'size': size,
                        'modified': date_str,
                    })
                except (ValueError, IndexError):
                    continue
        
        return files

    def restore_from_s3(self, s3_config, repo_name, local_path, logger):
        """Restore a repository from S3 to local storage."""
        temp_config_file = None
        try:
            # Extract bucket name and prefix from bucket field
            s3_bucket_raw = s3_config['bucket']
            
            # Parse bucket field to handle s3:// URLs and extract bucket name and prefix
            if s3_bucket_raw.startswith('s3://'):
                # Remove s3:// prefix and split into bucket and path
                bucket_and_path = s3_bucket_raw[5:]  # Remove 's3://'
                if '/' in bucket_and_path:
                    bucket_name = bucket_and_path.split('/')[0]
                    prefix_path = '/'.join(bucket_and_path.split('/')[1:])
                    # Ensure no double slashes in path construction
                    s3_path = f"s3://{bucket_name}/{prefix_path.strip('/')}/{repo_name}"
                else:
                    # Just bucket name, no prefix
                    s3_path = f"s3://{bucket_and_path}/{repo_name}"
            else:
                # Assume it's already just the bucket name/path - handle potential slashes
                s3_path = f"s3://{s3_bucket_raw.strip('/')}/{repo_name}"
            
            # Ensure local directory exists
            os.makedirs(local_path, exist_ok=True)
            
            # Prepare AWS credentials
            env = os.environ.copy()
            env['AWS_ACCESS_KEY_ID'] = s3_config['access_key']
            env['AWS_SECRET_ACCESS_KEY'] = s3_config['secret_key']
            if s3_config.get('region'):
                env['AWS_DEFAULT_REGION'] = s3_config['region']
            
            # Create temporary AWS config file with S3 sync settings if provided
            temp_config_file = self._create_aws_config_file(s3_config, logger)
            if temp_config_file:
                env['AWS_CONFIG_FILE'] = temp_config_file
                logger.info(f"Using custom AWS config file for S3 restore")
            
            cmd = [
                'aws', 's3', 'sync',
                s3_path, local_path,
            ]
            
            if s3_config.get('region'):
                cmd.extend(['--region', s3_config['region']])
            
            logger.info(f"Restoring from S3: {s3_path} -> {local_path}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                env=env
            )
            
            # Log output in real-time
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    logger.debug(f"aws sync restore: {line.strip()}")
            
            process.wait()
            
            if process.returncode != 0:
                raise Exception(f"aws sync restore failed with return code {process.returncode}")
            
            logger.info("Repository restored successfully from S3")
            
        except Exception as e:
            logger.error(f"S3 restore failed: {e}")
            raise
        
        finally:
            # Clean up temporary config file
            if temp_config_file:
                try:
                    os.unlink(temp_config_file)
                except Exception as e:
                    logger.debug(f"Failed to delete temporary AWS config file: {e}")

if __name__ == '__main__':
    # This can be used for testing S3 sync functionality
    pass