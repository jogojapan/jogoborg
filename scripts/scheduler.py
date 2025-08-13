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

class BackupScheduler:
    def __init__(self):
        self.db_path = '/config/jogoborg.db'
        self.log_dir = '/log'
        self.running = True
        self.executor = BackupExecutor()
        self.notification_service = NotificationService()
        
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
                   pre_command, post_command, s3_config, db_config
            FROM backup_jobs
            ''')
            
            jobs = cursor.fetchall()
            pending_jobs = []
            
            for job in jobs:
                job_id, name, schedule, compression, exclude_patterns, \
                keep_daily, keep_monthly, keep_yearly, source_directories, \
                pre_command, post_command, s3_config, db_config = job
                
                # Check if job should run now
                if self.should_run_job(schedule, current_time, job_id):
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
                        's3_config': json.loads(s3_config) if s3_config else None,
                        'db_config': json.loads(db_config) if db_config else None,
                    })
            
            return pending_jobs
            
        finally:
            conn.close()

    def should_run_job(self, schedule, current_time, job_id):
        """Check if a job should run based on its schedule."""
        try:
            # Only accept schedules that start at quarter hours (0, 15, 30, 45 minutes)
            cron = croniter(schedule, current_time)
            
            # Get the last time this job should have run
            last_run_time = cron.get_prev(datetime)
            
            # Check if we've already run this job at this time
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) FROM job_logs 
            WHERE job_id = ? AND started_at >= ? AND started_at < ?
            ''', (job_id, last_run_time, current_time))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            # Return True if we haven't run this job at this scheduled time yet
            return count == 0
            
        except Exception as e:
            self.logger.error(f"Error checking job schedule: {e}")
            return False

    def validate_schedule(self, schedule):
        """Validate that schedule only allows quarter-hour starts."""
        try:
            # Parse the cron expression
            parts = schedule.strip().split()
            if len(parts) != 5:
                return False
            
            minute_part = parts[0]
            
            # Check if minute is one of: 0, 15, 30, 45, or */15
            valid_minutes = ['0', '15', '30', '45', '*/15']
            
            if minute_part in valid_minutes:
                return True
            
            # Check for comma-separated values
            if ',' in minute_part:
                minutes = minute_part.split(',')
                return all(m.strip() in ['0', '15', '30', '45'] for m in minutes)
            
            return False
            
        except Exception:
            return False

    def get_next_quarter_hour(self, current_time):
        """Get the next quarter hour (0, 15, 30, or 45 minutes)."""
        minute = current_time.minute
        
        if minute < 15:
            next_minute = 15
        elif minute < 30:
            next_minute = 30
        elif minute < 45:
            next_minute = 45
        else:
            next_minute = 0
            current_time = current_time + timedelta(hours=1)
        
        return current_time.replace(minute=next_minute, second=0, microsecond=0)

    def run(self):
        """Main scheduler loop."""
        self.logger.info("Backup scheduler started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Round to the current quarter hour
                if current_time.minute not in [0, 15, 30, 45]:
                    # Sleep until next quarter hour
                    next_quarter = self.get_next_quarter_hour(current_time)
                    sleep_seconds = (next_quarter - current_time).total_seconds()
                    self.logger.info(f"Sleeping for {sleep_seconds} seconds until next quarter hour")
                    time.sleep(sleep_seconds)
                    continue
                
                # Get jobs that should run now
                pending_jobs = self.get_pending_jobs(current_time)
                
                if pending_jobs:
                    self.logger.info(f"Found {len(pending_jobs)} pending jobs")
                    
                    # Run jobs sequentially
                    for job in pending_jobs:
                        if not self.running:
                            break
                        
                        self.logger.info(f"Starting backup job: {job['name']}")
                        
                        try:
                            # Execute the backup job
                            self.executor.execute_job(job)
                            self.logger.info(f"Completed backup job: {job['name']}")
                        except Exception as e:
                            self.logger.error(f"Failed to execute job {job['name']}: {e}")
                            
                            # Send failure notification
                            try:
                                self.notification_service.send_notification(
                                    subject=f"Backup job failed: {job['name']}",
                                    message=f"Job {job['name']} failed with error: {str(e)}",
                                    is_error=True
                                )
                            except Exception as notify_error:
                                self.logger.error(f"Failed to send notification: {notify_error}")
                
                # Sleep for the remainder of the current minute
                next_quarter = self.get_next_quarter_hour(current_time)
                if next_quarter <= current_time:
                    next_quarter = self.get_next_quarter_hour(current_time + timedelta(minutes=15))
                
                sleep_seconds = (next_quarter - datetime.now()).total_seconds()
                if sleep_seconds > 0:
                    self.logger.debug(f"Sleeping for {sleep_seconds} seconds until next check")
                    time.sleep(min(sleep_seconds, 60))  # Check at least every minute
                
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