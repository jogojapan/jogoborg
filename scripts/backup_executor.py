#!/usr/bin/env python3
import os
import sys
import subprocess
import sqlite3
import json
import logging
import time
from datetime import datetime, timezone

# Add project root to Python path
sys.path.append('/app')

from scripts.database_dumper import DatabaseDumper
from scripts.s3_sync import S3Syncer
from scripts.notification_service import NotificationService


class BackupExecutor:
    def __init__(self, env_overrides=None):
        # Support environment variable overrides for local testing
        self.env_overrides = env_overrides or {}
        
        # Get environment variables with fallbacks
        config_dir = self._get_env('JOGOBORG_CONFIG_DIR', '/config')
        self.db_path = os.path.join(config_dir, 'jogoborg.db')
        self.log_dir = self._get_env('JOGOBORG_LOG_DIR', '/log')
        self.borgspace_dir = self._get_env('JOGOBORG_BORGSPACE_DIR', '/borgspace')
        
        # Validate that required paths exist or can be created
        self._validate_paths()
        
        self.db_dumper = DatabaseDumper()
        self.s3_syncer = S3Syncer()
        self.notification_service = NotificationService()
        
        # Set up logging
        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('BackupExecutor')
        
        # Log environment configuration for debugging
        self._log_config()

    def _get_env(self, key, default=None):
        """Get environment variable with override support for testing."""
        # Check overrides first (for local testing)
        if key in self.env_overrides:
            return self.env_overrides[key]
        # Then check actual environment
        return os.environ.get(key, default)

    def _validate_paths(self):
        """Validate that required directories exist or can be created."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            os.makedirs(self.borgspace_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        except Exception as e:
            raise Exception(f"Failed to validate/create required directories: {e}")

    def _log_config(self):
        """Log configuration for debugging (excluding sensitive data)."""
        self.logger.info(f"BackupExecutor initialized with:")
        self.logger.info(f"  Config directory: {self._get_env('JOGOBORG_CONFIG_DIR', '/config')}")
        self.logger.info(f"  Log directory: {self._get_env('JOGOBORG_LOG_DIR', '/log')}")
        self.logger.info(f"  Borgspace directory: {self._get_env('JOGOBORG_BORGSPACE_DIR', '/borgspace')}")
        self.logger.debug(f"  Database path: {self.db_path}")
        
        # Log which environment variables are being used
        debug_mode = self._get_env('JOGOBORG_DEBUG', 'false').lower() == 'true'
        if debug_mode:
            self.logger.debug("Debug mode enabled - environment details:")
            for key in ['JOGOBORG_CONFIG_DIR', 'JOGOBORG_LOG_DIR', 'JOGOBORG_BORGSPACE_DIR']:
                value = self._get_env(key, '<not set>')
                self.logger.debug(f"  {key}: {value}")

    def _get_borg_env(self, passphrase):
        """Get environment dict with BORG_PASSPHRASE set."""
        env = dict(os.environ)
        
        # Apply any test overrides to subprocess environment
        for key, value in self.env_overrides.items():
            if not key.startswith('JOGOBORG_'):
                env[key] = value
        
        if passphrase:
            env['BORG_PASSPHRASE'] = passphrase
        return env

    def execute_job(self, job):
        """Execute a complete backup job."""
        job_id = job['id']
        job_name = job['name']
        started_at = datetime.now(timezone.utc)
        
        # Create job-specific logger
        job_logger = self._setup_job_logger(job_name)
        job_logger.info(f"Starting backup job: {job_name}")
        
        # Validate job configuration
        try:
            self._validate_job_config(job, job_logger)
        except Exception as e:
            job_logger.error(f"Invalid job configuration: {e}")
            raise
        
        # Initialize log entry
        log_entry_id = self._create_log_entry(job_id, started_at)
        
        try:
            # Execute pre-command if specified
            if job.get('pre_command'):
                job_logger.info(f"Executing pre-command: {job['pre_command']}")
                self._execute_command(job['pre_command'], job_logger)
            
            # Determine repository path
            repo_path = os.path.join(self.borgspace_dir, job_name)
            
            # Initialize repository if it doesn't exist
            if not os.path.exists(repo_path):
                self._init_repository(repo_path, job['repository_passphrase'], job_logger)
            
            # Execute main backup
            create_duration, create_max_memory = self._execute_borg_create(
                job, repo_path, started_at, job_logger
            )
            
            # Execute pruning
            prune_duration, prune_max_memory = self._execute_borg_prune(
                job, repo_path, job_logger
            )
            
            # Execute compacting
            compact_duration, compact_max_memory = self._execute_borg_compact(
                job, repo_path, job_logger
            )
            
            # Handle database dumps if configured
            db_dump_duration = None
            db_dump_max_memory = None
            db_archive_duration = None  
            db_archive_max_memory = None
            db_prune_duration = None
            db_prune_max_memory = None
            db_compact_duration = None
            db_compact_max_memory = None
            
            if job.get('db_config'):
                (db_dump_duration, db_dump_max_memory, 
                 db_archive_duration, db_archive_max_memory,
                 db_prune_duration, db_prune_max_memory,
                 db_compact_duration, db_compact_max_memory) = self._execute_db_backup(
                    job, repo_path, started_at, job_logger
                )
            
            # Sync to S3 if configured
            if job.get('s3_config'):
                self._execute_s3_sync(job, repo_path, job_logger)
            
            # Execute post-command if specified
            if job.get('post_command'):
                job_logger.info(f"Executing post-command: {job['post_command']}")
                self._execute_command(job['post_command'], job_logger)
            
            # Update log entry with success
            finished_at = datetime.now(timezone.utc)
            self._update_log_entry(
                log_entry_id, finished_at, 'completed',
                create_duration, create_max_memory,
                prune_duration, prune_max_memory,
                compact_duration, compact_max_memory,
                db_dump_duration, db_dump_max_memory,
                db_archive_duration, db_archive_max_memory,
                db_prune_duration, db_prune_max_memory,
                db_compact_duration, db_compact_max_memory
            )
            
            job_logger.info(f"Backup job completed successfully: {job_name}")
            
            # Send success notification
            self._send_success_notification(job, started_at, finished_at, {
                'create_duration': create_duration,
                'create_max_memory': create_max_memory,
                'prune_duration': prune_duration,
                'prune_max_memory': prune_max_memory,
                'compact_duration': compact_duration,
                'compact_max_memory': compact_max_memory,
                'db_dump_duration': db_dump_duration,
                'db_dump_max_memory': db_dump_max_memory,
                'db_archive_duration': db_archive_duration,
                'db_archive_max_memory': db_archive_max_memory,
                'db_prune_duration': db_prune_duration,
                'db_prune_max_memory': db_prune_max_memory,
                'db_compact_duration': db_compact_duration,
                'db_compact_max_memory': db_compact_max_memory,
            })
            
        except Exception as e:
            # Update log entry with error
            finished_at = datetime.now(timezone.utc)
            self._update_log_entry(log_entry_id, finished_at, 'failed', error_message=str(e))
            
            job_logger.error(f"Backup job failed: {job_name} - {str(e)}")
            
            # Send failure notification
            self._send_failure_notification(job, started_at, str(e))
            
            raise

    def _validate_job_config(self, job, logger):
        """Validate that a job configuration has all required fields."""
        required_fields = {
            'id': int,
            'name': str,
            'compression': str,
            'source_directories': list,
            'keep_daily': int,
            'keep_monthly': int,
            'keep_yearly': int
        }
        
        errors = []
        
        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in job:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(job[field], expected_type):
                errors.append(f"Field '{field}' has wrong type: expected {expected_type.__name__}, got {type(job[field]).__name__}")
        
        # Check source directories
        if 'source_directories' in job and job['source_directories']:
            for source_dir in job['source_directories']:
                if not isinstance(source_dir, str) or not source_dir.strip():
                    errors.append(f"Invalid source directory: {source_dir}")
        else:
            errors.append("Job must have at least one source directory")
        
        # Check compression is valid
        if 'compression' in job:
            valid_compressions = ['none', 'lz4', 'zstd', 'zlib', 'lzma']
            if job['compression'] not in valid_compressions:
                errors.append(f"Invalid compression type: {job['compression']}. Must be one of: {', '.join(valid_compressions)}")
        
        # Check retention policy values are positive
        for field in ['keep_daily', 'keep_monthly', 'keep_yearly']:
            if field in job and job[field] < 0:
                errors.append(f"Field '{field}' must be non-negative, got: {job[field]}")
        
        # Check passphrase - must be available either in job config or environment
        passphrase = job.get('repository_passphrase') or self._get_env('BORG_PASSPHRASE')
        if not passphrase:
            errors.append("No repository passphrase provided. Set 'repository_passphrase' in job config or BORG_PASSPHRASE environment variable")
        
        if errors:
            error_msg = "Job validation failed:\n  - " + "\n  - ".join(errors)
            raise ValueError(error_msg)
        
        logger.debug(f"Job configuration validated successfully for job: {job['name']}")

    def _setup_job_logger(self, job_name):
        """Set up a logger for a specific job."""
        logger = logging.getLogger(f'BackupJob_{job_name}')
        
        # Remove any existing handlers to avoid duplicates on repeated runs
        logger.handlers.clear()
        
        # Create file handler for this job
        log_file = os.path.join(self.log_dir, f'{job_name}.log')
        
        try:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        except Exception as e:
            self.logger.warning(f"Failed to create log file handler for {job_name}: {e}")
            # Fall back to console only
        
        logger.setLevel(logging.INFO)
        return logger

    def _create_log_entry(self, job_id, started_at):
        """Create a log entry in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO job_logs (job_id, started_at, status)
            VALUES (?, ?, 'running')
            ''', (job_id, started_at.isoformat()))
            
            log_entry_id = cursor.lastrowid
            conn.commit()
            return log_entry_id
            
        finally:
            conn.close()

    def _update_log_entry(self, log_entry_id, finished_at, status,
                         create_duration=None, create_max_memory=None,
                         prune_duration=None, prune_max_memory=None,
                         compact_duration=None, compact_max_memory=None,
                         db_dump_duration=None, db_dump_max_memory=None,
                         db_archive_duration=None, db_archive_max_memory=None,
                         db_prune_duration=None, db_prune_max_memory=None,
                         db_compact_duration=None, db_compact_max_memory=None,
                         error_message=None):
        """Update a log entry with completion details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE job_logs SET
                finished_at = ?,
                status = ?,
                create_duration = ?,
                create_max_memory = ?,
                prune_duration = ?,
                prune_max_memory = ?,
                compact_duration = ?,
                compact_max_memory = ?,
                db_dump_duration = ?,
                db_dump_max_memory = ?,
                db_archive_duration = ?,
                db_archive_max_memory = ?,
                db_prune_duration = ?,
                db_prune_max_memory = ?,
                db_compact_duration = ?,
                db_compact_max_memory = ?,
                error_message = ?
            WHERE id = ?
            ''', (
                finished_at.isoformat(), status,
                create_duration, create_max_memory,
                prune_duration, prune_max_memory,
                compact_duration, compact_max_memory,
                db_dump_duration, db_dump_max_memory,
                db_archive_duration, db_archive_max_memory,
                db_prune_duration, db_prune_max_memory,
                db_compact_duration, db_compact_max_memory,
                error_message, log_entry_id
            ))
            
            conn.commit()
            
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                # Database schema is outdated, fall back to basic update
                self.logger.error(f"Database schema outdated: {e}. Please run database migration.")
                cursor.execute('''
                UPDATE job_logs SET
                    finished_at = ?,
                    status = ?,
                    create_duration = ?,
                    create_max_memory = ?,
                    prune_duration = ?,
                    prune_max_memory = ?,
                    compact_duration = ?,
                    compact_max_memory = ?,
                    error_message = ?
                WHERE id = ?
                ''', (
                    finished_at.isoformat(), status,
                    create_duration, create_max_memory,
                    prune_duration, prune_max_memory,
                    compact_duration, compact_max_memory,
                    error_message, log_entry_id
                ))
                conn.commit()
            else:
                raise
        finally:
            conn.close()

    def _init_repository(self, repo_path, passphrase, logger):
        """Initialize a new Borg repository."""
        if not passphrase:
            raise Exception("Could not initialize repository: Passphrase is required but not provided. Please set 'repository_passphrase' when creating the backup job.")
        
        logger.info(f"Initializing new repository: {repo_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(repo_path, exist_ok=True)
        
        # Initialize with encryption
        cmd = ['borg', 'init', '--encryption=repokey', repo_path]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=self._get_borg_env(passphrase)
        )
        
        if result.returncode != 0:
            error_msg = result.stderr
            # Check for specific passphrase-related errors
            if 'passphrase' in error_msg.lower():
                raise Exception(f"Repository initialization failed - passphrase error: {error_msg}")
            else:
                raise Exception(f"Failed to initialize repository: {error_msg}")
        
        logger.info("Repository initialized successfully")

    def _execute_borg_create(self, job, repo_path, started_at, logger):
        """Execute borg create command with time/memory monitoring."""
        archive_name = f"{job['name']}_{started_at.strftime('%Y%m%d%H%MZ')}"
        
        logger.info(f"Creating archive: {archive_name}")
        
        # Build borg create command
        borg_cmd = [
            'borg', 'create',
            '--compression', job['compression'],
            '--stats',
            f'{repo_path}::{archive_name}'
        ]
        
        # Add source directories
        borg_cmd.extend(job['source_directories'])
        
        # Add exclude patterns
        for pattern in job.get('exclude_patterns', []):
            if pattern.strip():
                borg_cmd.extend(['--exclude', pattern.strip()])
        
        # Wrap with time command for precise measurement
        cmd = ['/usr/bin/time', '-v'] + borg_cmd
        
        # Execute with time monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Borg create failed: {stdout} {stderr}")
        
        # Parse time output for duration and memory
        duration, max_memory = self._parse_time_output(stderr, logger)
        
        logger.info(f"Archive created successfully in {duration}s, max memory: {max_memory:.1f}MB")
        logger.debug(f"Borg create output: {stdout}")
        
        return duration, int(max_memory)

    def _execute_borg_prune(self, job, repo_path, logger):
        """Execute borg prune command with time/memory monitoring."""
        logger.info("Pruning old archives")
        
        borg_cmd = [
            'borg', 'prune',
            '--list',
            '--glob-archives', f"{job['name']}_*",
            f'--keep-daily={job["keep_daily"]}',
            f'--keep-monthly={job["keep_monthly"]}',
            f'--keep-yearly={job["keep_yearly"]}',
            repo_path
        ]
        
        # Wrap with time command for precise measurement
        cmd = ['/usr/bin/time', '-v'] + borg_cmd
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Borg prune failed: {stdout} {stderr}")
        
        # Parse time output for duration and memory
        duration, max_memory = self._parse_time_output(stderr, logger)
        
        logger.info(f"Pruning completed in {duration}s, max memory: {max_memory:.1f}MB")
        logger.debug(f"Borg prune output: {stdout}")
        
        return duration, int(max_memory)

    def _execute_borg_compact(self, job, repo_path, logger):
        """Execute borg compact command with time/memory monitoring."""
        logger.info("Compacting repository")
        
        borg_cmd = ['borg', 'compact', repo_path]
        
        # Wrap with time command for precise measurement
        cmd = ['/usr/bin/time', '-v'] + borg_cmd
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Borg compact failed: {stdout} {stderr}")
        
        # Parse time output for duration and memory
        duration, max_memory = self._parse_time_output(stderr, logger)
        
        logger.info(f"Compacting completed in {duration}s, max memory: {max_memory:.1f}MB")
        logger.debug(f"Borg compact output: {stdout}")
        
        return duration, int(max_memory)

    def _execute_db_backup(self, job, repo_path, started_at, logger):
        """Execute database backup with separate step tracking."""
        logger.info("Starting database backup")
        
        db_config = job['db_config']
        
        # Step 1: Create database dumps
        import time
        dump_start = time.time()
        dump_files = self.db_dumper.create_dumps(db_config, logger)
        dump_duration = int(time.time() - dump_start)
        
        if not dump_files:
            return None, None, None, None, None, None, None, None
        
        logger.info(f"Database dump completed in {dump_duration}s")
        
        # Step 2: Create database archive  
        try:
            archive_name = f"{job['name']}_db_{started_at.strftime('%Y%m%d%H%MZ')}"
            
            borg_cmd = [
                'borg', 'create',
                '--compression', job['compression'],
                '--stats',
                f'{repo_path}::{archive_name}'
            ]
            borg_cmd.extend(dump_files)
            
            # Wrap with time command for precise measurement
            cmd = ['/usr/bin/time', '-v'] + borg_cmd
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._get_borg_env(job['repository_passphrase'])
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Database archive creation failed: {stdout} {stderr}")
            
            # Parse time output for duration and memory
            archive_duration, archive_max_memory = self._parse_time_output(stderr, logger)
            
            logger.info(f"Database archive created in {archive_duration}s, max memory: {archive_max_memory:.1f}MB")
            
            # Step 3: Prune database archives
            prune_duration, prune_max_memory = self._prune_db_archives_timed(job, repo_path, logger)
            
            # Step 4: Compact database repository
            compact_duration, compact_max_memory = self._execute_db_compact_timed(job, repo_path, logger)
            
            return (dump_duration, 1, archive_duration, int(archive_max_memory), 
                   prune_duration, prune_max_memory, compact_duration, compact_max_memory)
            
        finally:
            # Clean up dump files
            for dump_file in dump_files:
                try:
                    os.remove(dump_file)
                except Exception as e:
                    logger.warning(f"Failed to remove dump file {dump_file}: {e}")

    def _prune_db_archives(self, job, repo_path, logger):
        """Prune database archives separately."""
        cmd = [
            'borg', 'prune',
            '--list',
            '--glob-archives', f"{job['name']}_db_*",
            f'--keep-daily={job["keep_daily"]}',
            f'--keep-monthly={job["keep_monthly"]}',
            f'--keep-yearly={job["keep_yearly"]}',
            repo_path
        ]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        if process.returncode != 0:
            logger.warning(f"Database archive pruning failed: {process.stderr}")

    def _prune_db_archives_timed(self, job, repo_path, logger):
        """Prune database archives with time/memory tracking."""
        logger.info("Pruning database archives")
        
        borg_cmd = [
            'borg', 'prune',
            '--list',
            '--glob-archives', f"{job['name']}_db_*",
            f'--keep-daily={job["keep_daily"]}',
            f'--keep-monthly={job["keep_monthly"]}',
            f'--keep-yearly={job["keep_yearly"]}',
            repo_path
        ]
        
        # Wrap with time command for precise measurement
        cmd = ['/usr/bin/time', '-v'] + borg_cmd
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Database archive pruning failed: {stdout} {stderr}")
            return 0, 1  # Return minimal values on failure
        
        # Parse time output for duration and memory
        duration, max_memory = self._parse_time_output(stderr, logger)
        
        logger.info(f"Database archive pruning completed in {duration}s, max memory: {max_memory:.1f}MB")
        
        return duration, int(max_memory)

    def _execute_db_compact_timed(self, job, repo_path, logger):
        """Compact database repository with time/memory tracking."""
        logger.info("Compacting database repository")
        
        borg_cmd = ['borg', 'compact', repo_path]
        
        # Wrap with time command for precise measurement
        cmd = ['/usr/bin/time', '-v'] + borg_cmd
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._get_borg_env(job['repository_passphrase'])
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Database repository compacting failed: {stdout} {stderr}")
            return 0, 1  # Return minimal values on failure
        
        # Parse time output for duration and memory
        duration, max_memory = self._parse_time_output(stderr, logger)
        
        logger.info(f"Database repository compacting completed in {duration}s, max memory: {max_memory:.1f}MB")
        
        return duration, int(max_memory)

    def _execute_s3_sync(self, job, repo_path, logger):
        """Sync repository to S3."""
        logger.info("Starting S3 sync")
        
        try:
            self.s3_syncer.sync_repository(job['s3_config'], repo_path, logger)
            logger.info("S3 sync completed successfully")
        except Exception as e:
            logger.error(f"S3 sync failed: {e}")
            # Re-raise exception so backup job is marked as failed
            raise Exception(f"S3 sync failed: {e}")

    def _execute_command(self, command, logger):
        """Execute a shell command."""
        try:
            # For Docker commands, ensure we have proper socket access
            # if command.strip().startswith('docker') and os.path.exists('/var/run/docker.sock'):
            #     command = self._wrap_docker_command(command, logger)
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"Command returned non-zero exit code {result.returncode}: {result.stderr}")
            else:
                logger.info("Command executed successfully")
                
            if result.stdout:
                logger.debug(f"Command output: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out after 5 minutes")
            raise Exception("Command execution timed out")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

    def _wrap_docker_command(self, command, logger):
        """Wrap docker commands to ensure proper socket access."""
        try:
            # Get docker socket group ID
            socket_stat = os.stat('/var/run/docker.sock')
            docker_gid = socket_stat.st_gid
            
            # Use sg command to run with correct group permissions
            wrapped_command = f"sg {docker_gid} -c '{command}'"
            logger.debug(f"Wrapping docker command with group {docker_gid}: {wrapped_command}")
            return wrapped_command
            
        except Exception as e:
            logger.warning(f"Failed to wrap docker command, running as-is: {e}")
            return command

    def _parse_time_output(self, time_stderr, logger):
        """Parse time -v output to extract duration and memory usage."""
        duration = 0
        max_memory = 1.0  # Default fallback in MB
        
        try:
            for line in time_stderr.split('\n'):
                line = line.strip()
                
                # Parse elapsed time (format: "Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.23")
                if 'Elapsed (wall clock) time' in line:
                    time_part = line.split(': ')[-1]
                    if ':' in time_part:
                        parts = time_part.split(':')
                        if len(parts) == 2:  # mm:ss.ss
                            duration = int(float(parts[0]) * 60 + float(parts[1]))
                        elif len(parts) == 3:  # h:mm:ss.ss
                            duration = int(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]))
                    else:
                        # Just seconds
                        duration = int(float(time_part))
                
                # Parse maximum memory usage (format: "Maximum resident set size (kbytes): 123456")
                elif 'Maximum resident set size (kbytes)' in line:
                    kb_value = line.split(': ')[-1]
                    max_memory = float(kb_value) / 1024.0  # Convert KB to MB
        
        except Exception as e:
            logger.debug(f"Failed to parse time output: {e}")
            duration = 0
            max_memory = 1.0
        
        return duration, max_memory

    def _send_success_notification(self, job, started_at, finished_at, stats):
        """Send success notification."""
        duration = finished_at - started_at
        
        message = f"""
Backup job '{job['name']}' completed successfully.

Started: {started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Finished: {finished_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Duration: {duration}

Statistics:
- Create: {stats['create_duration']}s, {stats['create_max_memory']}MB
- Prune: {stats['prune_duration']}s, {stats['prune_max_memory']}MB  
- Compact: {stats['compact_duration']}s, {stats['compact_max_memory']}MB
"""
        
        # Include database backup stats if they exist and are not None
        if (stats.get('db_dump_duration') is not None and 
            stats.get('db_archive_duration') is not None and 
            stats.get('db_prune_duration') is not None and
            stats.get('db_compact_duration') is not None):
            message += f"- DB Dump: {stats['db_dump_duration']}s, {stats['db_dump_max_memory']}MB\n"
            message += f"- DB Archive: {stats['db_archive_duration']}s, {stats['db_archive_max_memory']}MB\n"
            message += f"- DB Prune: {stats['db_prune_duration']}s, {stats['db_prune_max_memory']}MB\n"
            message += f"- DB Compact: {stats['db_compact_duration']}s, {stats['db_compact_max_memory']}MB\n"
        
        try:
            self.notification_service.send_notification(
                subject=f"Backup completed: {job['name']}",
                message=message.strip(),
                is_error=False
            )
        except Exception as e:
            self.logger.error(f"Failed to send success notification: {e}")

    def _send_failure_notification(self, job, started_at, error_message):
        """Send failure notification."""
        message = f"""
Backup job '{job['name']}' failed.

Started: {started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Error: {error_message}
"""
        
        try:
            self.notification_service.send_notification(
                subject=f"Backup failed: {job['name']}",
                message=message.strip(),
                is_error=True
            )
        except Exception as e:
            self.logger.error(f"Failed to send failure notification: {e}")

if __name__ == '__main__':
    # This can be used for testing individual backup execution
    pass
