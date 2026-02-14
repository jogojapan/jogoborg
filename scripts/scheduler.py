#!/usr/bin/env python3
import os
import sys
import time
import sqlite3
import json
import logging
import threading
from datetime import datetime, timedelta
from croniter import croniter

# Add project root to Python path
sys.path.append('/app')

from scripts.backup_executor import BackupExecutor
from scripts.notification_service import NotificationService
from scripts.init_gpg import decrypt_data

class BackupScheduler:
    def __init__(self):
        config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
        self.db_path = os.path.join(config_dir, 'jogoborg.db')
        self.log_dir = os.environ.get('JOGOBORG_LOG_DIR', '/log')
        self.running = True
        self.executor = BackupExecutor()
        self.notification_service = NotificationService()
        
        # Track running jobs to prevent duplicate simultaneous execution
        self.running_jobs = set()
        self.jobs_lock = threading.Lock()
        
        # Set up logging
        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{self.log_dir}/scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('BackupScheduler')

    def get_pending_jobs(self, current_time):
        """Get jobs that should run at the current time."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT id, name, schedule, compression, exclude_patterns, 
                   keep_daily, keep_monthly, keep_yearly, source_directories,
                   pre_command, post_command, s3_config, db_config, repository_passphrase
            FROM backup_jobs
            ''')
            
            jobs = cursor.fetchall()
            pending_jobs = []
            
            for job in jobs:
                job_id, name, schedule, compression, exclude_patterns, \
                keep_daily, keep_monthly, keep_yearly, source_directories, \
                pre_command, post_command, s3_config, db_config, repository_passphrase = job
                
                # Check if job should run now
                if self.should_run_job(schedule, current_time, job_id):
                    # Decrypt sensitive configurations
                    decrypted_passphrase = None
                    decrypted_s3_config = None
                    decrypted_db_config = None
                    
                    if repository_passphrase:
                        try:
                            decrypted_passphrase = decrypt_data(repository_passphrase)
                        except Exception as e:
                            self.logger.error(f"Failed to decrypt repository passphrase for job {name}: {e}")
                            continue  # Skip this job if passphrase can't be decrypted
                    
                    if s3_config:
                        try:
                            decrypted_s3_config = json.loads(decrypt_data(s3_config))
                        except Exception as e:
                            self.logger.error(f"Failed to decrypt S3 config for job {name}: {e}")
                            # Don't skip job, just set to None
                    
                    if db_config:
                        try:
                            decrypted_db_config = json.loads(decrypt_data(db_config))
                        except Exception as e:
                            self.logger.error(f"Failed to decrypt DB config for job {name}: {e}")
                            # Don't skip job, just set to None
                    
                    pending_jobs.append({
                        'id': job_id,
                        'name': name,
                        'schedule': schedule,
                        'compression': compression or 'lz4',
                        'exclude_patterns': exclude_patterns.split('\n') if exclude_patterns else [],
                        'keep_daily': keep_daily or 7,
                        'keep_monthly': keep_monthly or 6,
                        'keep_yearly': keep_yearly or 1,
                        'source_directories': json.loads(source_directories),
                        'pre_command': pre_command,
                        'post_command': post_command,
                        's3_config': decrypted_s3_config,
                        'db_config': decrypted_db_config,
                        'repository_passphrase': decrypted_passphrase,
                    })
            
            return pending_jobs
            
        finally:
            conn.close()

    def should_run_job(self, schedule, current_time, job_id):
        """Check if a job should run based on its schedule."""
        try:
            # First check if this job is already running
            with self.jobs_lock:
                if job_id in self.running_jobs:
                    self.logger.debug(f"Job {job_id} is already running, skipping duplicate execution")
                    return False
            
            # Create croniter object  
            cron = croniter(schedule, current_time)
            
            # Get the next scheduled time
            next_run_time = cron.get_next(datetime)
            
            # Get the previous scheduled time
            prev_run_time = cron.get_prev(datetime)
            
            # Check if current_time is within one minute AFTER a scheduled time
            # (accounts for the fact that we check every 30 seconds)
            time_since_last_schedule = (current_time - prev_run_time).total_seconds()
            
            # If more than 61 seconds have passed since the last scheduled time,
            # the current time is NOT the scheduled time window - don't run
            if time_since_last_schedule > 61:
                return False
            
            # Now check if we've already run this job at this scheduled time
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                SELECT COUNT(*) FROM job_logs 
                WHERE job_id = ? AND started_at >= ? AND started_at < ?
                ''', (job_id, prev_run_time.isoformat(), current_time.isoformat()))
                
                count = cursor.fetchone()[0]
                
                # Return True if we haven't run this job at this scheduled time yet
                return count == 0
                
            finally:
                conn.close()
            
        except Exception as e:
            self.logger.error(f"Error checking job schedule: {e}")
            return False

    def validate_schedule(self, schedule):
        """Validate that schedule is a valid cron expression."""
        try:
            # Parse the cron expression
            parts = schedule.strip().split()
            if len(parts) != 5:
                return False
            
            # Try to create a croniter object - if it works, it's valid
            croniter(schedule, datetime.now())
            return True
            
        except Exception:
            return False

    def _execute_job_in_thread(self, job):
        """Execute a job in a background thread, handling cleanup."""
        job_id = job['id']
        job_name = job['name']
        
        try:
            # Mark job as running
            with self.jobs_lock:
                self.running_jobs.add(job_id)
            
            self.logger.info(f"Starting backup job in thread: {job_name}")
            
            # Execute the backup job
            self.executor.execute_job(job)
            self.logger.info(f"Completed backup job: {job_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute job {job_name}: {e}")
            
            # Send failure notification
            try:
                self.notification_service.send_notification(
                    subject=f"Backup job failed: {job_name}",
                    message=f"Job {job_name} failed with error: {str(e)}",
                    is_error=True
                )
            except Exception as notify_error:
                self.logger.error(f"Failed to send notification: {notify_error}")
        
        finally:
            # Remove job from running set when complete
            with self.jobs_lock:
                self.running_jobs.discard(job_id)
            self.logger.debug(f"Job {job_name} thread completed, removed from running jobs")

    def run(self):
        """Main scheduler loop."""
        self.logger.info("Backup scheduler started")
        last_checked_minute = None
        
        while self.running:
            try:
                current_time = datetime.now()
                current_minute = current_time.replace(second=0, microsecond=0)
                
                # Check if we've already checked this minute (avoid duplicate checks)
                if last_checked_minute != current_minute:
                    last_checked_minute = current_minute
                    
                    # Get jobs that should run now
                    pending_jobs = self.get_pending_jobs(current_time)
                    
                    if pending_jobs:
                        self.logger.info(f"Found {len(pending_jobs)} pending jobs at {current_time.strftime('%H:%M')}")
                        
                        # Run jobs in parallel using threads
                        for job in pending_jobs:
                            if not self.running:
                                break
                            
                            # Create and start a thread for this job
                            job_thread = threading.Thread(
                                target=self._execute_job_in_thread,
                                args=(job,),
                                daemon=False
                            )
                            job_thread.start()
                
                # Sleep for a bit before checking again
                # We check every 30 seconds to be responsive to minute boundaries
                time.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping backup scheduler")
        self.running = False

def main():
    scheduler = BackupScheduler()
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()
    except Exception as e:
        logging.error(f"Scheduler crashed: {e}")
        raise

if __name__ == '__main__':
    main()