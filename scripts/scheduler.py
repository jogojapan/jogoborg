#!/usr/bin/env python3
import os
import sys
import time
import sqlite3
import json
import logging
import threading
import signal
from datetime import datetime, timedelta
from croniter import croniter

# Add project root to Python path
sys.path.append('/app')

from scripts.backup_executor import BackupExecutor
from scripts.notification_service import NotificationService
from scripts.init_gpg import decrypt_data
from scripts.memory_monitor import memory_stats

class BackupScheduler:
    def __init__(self):
        config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
        self.db_path = os.path.join(config_dir, 'jogoborg.db')
        self.log_dir = os.environ.get('JOGOBORG_LOG_DIR', '/log')
        self.running = True
        self.executor = BackupExecutor()
        self.notification_service = NotificationService()

        # Concurrency + memory-gate configuration (env-tunable).
        self.max_parallel = int(os.environ.get('JOGOBORG_MAX_PARALLEL_JOBS', '4') or 4)
        self.mem_delay_seconds = int(os.environ.get('JOGOBORG_MEMORY_DELAY_SECONDS', '3600') or 3600)
        self.mem_delay_threshold = float(os.environ.get('JOGOBORG_MEMORY_DELAY_THRESHOLD', '0.75') or 0.75)
        self.mem_resume_threshold = float(os.environ.get('JOGOBORG_MEMORY_RESUME_THRESHOLD', '0.70') or 0.70)
        self.max_parallel = max(1, self.max_parallel)

        # Scheduler runtime state.
        self._active_job_ids = set()  # job ids currently running in threads
        self._delayed = {}            # job_id -> {job, reason, next_check, notified}
        self._job_threads = set()     # running job threads
        self._running_jobs = {}       # job_id -> job (for interruption handling)
        self.shutdown_grace = int(os.environ.get('JOGOBORG_SHUTDOWN_GRACE', '300') or 300)
        
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
SELECT id, name, repository, schedule, compression, exclude_patterns,
                   keep_daily, keep_monthly, keep_yearly, source_directories,
                   pre_command, post_command, s3_config, db_config, repository_passphrase
            FROM backup_jobs
            ''')
            
            jobs = cursor.fetchall()
            pending_jobs = []
            
            for job in jobs:
                job_id, name, repository, schedule, compression, exclude_patterns, \
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
                        'repository': repository,
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

    def _memory_pressure_pct(self):
        """Return (gated, usage_percent). gated True if container memory usage
        is at/above the delay threshold. Disabled (False, None) when no limit
        is available (e.g. local dev, no explicit Docker limit)."""
        stats = memory_stats()
        if not stats or not stats['limit_mb'] or stats['current_mb'] is None:
            return False, None
        pct = stats['current_mb'] / stats['limit_mb']
        return pct >= self.mem_delay_threshold, pct

    def _dispatch_job(self, job):
        """Run a job in its own thread; concurrency is bounded by max_parallel."""
        job_id = job['id']
        self._active_job_ids.add(job_id)
        self._delayed.pop(job_id, None)
        self._running_jobs[job_id] = job
        self.logger.info(f"Starting backup job: {job['name']}")

        def run_job():
            try:
                self.executor.execute_job(job)
                self.logger.info(f"Completed backup job: {job['name']}")
            except Exception as e:
                self.logger.error(f"Failed to execute job {job['name']}: {e}")
                try:
                    self.notification_service.send_notification(
                        subject=f"Backup job failed: {job['name']}",
                        message=f"Job {job['name']} failed with error: {str(e)}",
                        is_error=True,
                    )
                except Exception as notify_error:
                    self.logger.error(f"Failed to send notification: {notify_error}")
            finally:
                self._active_job_ids.discard(job_id)
                self._running_jobs.pop(job_id, None)
                self._job_threads.discard(threading.current_thread())

        thread = threading.Thread(target=run_job, daemon=True)
        self._job_threads.add(thread)
        thread.start()

    def _delay_for_memory(self, job, now, pct):
        """Hold a job because container memory is near its limit; notify once
        per delay episode with the delay length and current usage."""
        job_id = job['id']
        previous = self._delayed.get(job_id)
        delay_minutes = int(self.mem_delay_seconds / 60)
        self._delayed[job_id] = {
            'job': job,
            'reason': 'memory',
            'next_check': now + timedelta(seconds=self.mem_delay_seconds),
            'notified': True,
        }
        # Notify on the first delay and again each time the delay elapses
        # while still gated; suppress repeats within the same delay interval.
        if previous is None or now >= previous.get('next_check', now):
            try:
                self.notification_service.send_notification(
                    subject=f"Backup job delayed: {job['name']}",
                    message=(
                        f"Job '{job['name']}' was due but container memory is "
                        f"high ({pct * 100:.0f}% of limit). It will be delayed "
                        f"by {delay_minutes} minutes and checked again then."
                    ),
                    is_error=False,
                )
            except Exception as notify_error:
                self.logger.error(f"Failed to send delay notification: {notify_error}")

    def _process_due(self, pending_jobs, now):
        """Dispatch jobs that are due (parallel), honouring the concurrency
        cap and the memory gate. Blocked jobs move to the delayed set."""
        for job in pending_jobs:
            if not self.running:
                break
            job_id = job['id']
            if job_id in self._active_job_ids or job_id in self._delayed:
                continue  # already running or already being delayed

            if len(self._active_job_ids) >= self.max_parallel:
                self.logger.info(
                    f"At max parallel jobs ({self.max_parallel}); holding {job['name']} for a slot"
                )
                self._delayed[job_id] = {
                    'job': job,
                    'reason': 'capacity',
                    'next_check': now,
                    'notified': False,
                }
                continue

            gated, pct = self._memory_pressure_pct()
            if gated:
                self.logger.info(
                    f"Memory pressure {pct * 100:.0f}%; delaying {job['name']}"
                )
                self._delay_for_memory(job, now, pct)
                continue

            self._dispatch_job(job)

    def _process_delayed(self, now):
        """Start held jobs when a slot is free and memory has room (or after a
        delay elapses). Memory-delayed jobs notify again on each elapsed delay."""
        for job_id in list(self._delayed):
            if job_id in self._active_job_ids:
                continue
            entry = self._delayed[job_id]
            job = entry['job']

            if entry['reason'] == 'capacity':
                if len(self._active_job_ids) < self.max_parallel:
                    self._dispatch_job(job)
                continue

            # memory-gated
            if len(self._active_job_ids) >= self.max_parallel:
                continue
            gated, pct = self._memory_pressure_pct()
            if gated is not None and pct is not None and pct < self.mem_resume_threshold:
                # memory freed up; start early
                self._dispatch_job(job)
            elif now >= entry['next_check']:
                # delay elapsed but still gated -> extend and re-notify
                self._delay_for_memory(job, now, pct if pct is not None else 1.0)

    def _recover_interrupted(self):
        """Mark job_logs left 'running' by an unclean stop as 'interrupted' and
        notify, so the UI shows no phantom running jobs."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            rows = cur.execute(
                "SELECT l.id, l.job_id, j.name FROM job_logs l "
                "LEFT JOIN backup_jobs j ON l.job_id = j.id "
                "WHERE l.status = 'running'"
            ).fetchall()
            for log_id, job_id, name in rows:
                label = name or f"job-{job_id}"
                cur.execute(
                    "UPDATE job_logs SET status='interrupted', error_message=? WHERE id=?",
                    ("Interrupted by service shutdown", log_id),
                )
                try:
                    self.notification_service.send_notification(
                        subject=f"Backup job interrupted: {label}",
                        message=(f"Backup job '{label}' was interrupted by an unclean "
                                 f"service shutdown (phase unknown). If needed, check the "
                                 f"repository with `borg check --repair`."),
                        is_error=True,
                    )
                except Exception as e:
                    self.logger.error(f"Failed to send interruption notification: {e}")
            conn.commit()
            conn.close()
            if rows:
                self.logger.info(
                    f"Marked {len(rows)} interrupted job log(s) from a previous shutdown"
                )
        except Exception as e:
            self.logger.error(f"Failed to recover interrupted job logs: {e}")

    def _handle_signal(self, signum, frame):
        """Graceful shutdown: stop dispatching, drain in-flight jobs up to the
        grace period, then SIGINT any still-running borg and notify."""
        self.logger.info("Received termination signal; stopping new dispatches")
        self.running = False
        deadline = time.time() + self.shutdown_grace
        while self._job_threads and time.time() < deadline:
            self._job_threads = {t for t in self._job_threads if t.is_alive()}
            if not self._job_threads:
                break
            time.sleep(0.2)
        if self._job_threads:
            self.logger.warning(
                f"Shutdown grace elapsed with {len(self._job_threads)} job(s) "
                f"still running; aborting"
            )
            self._abort_and_notify()
            deadline2 = time.time() + 15
            while self._job_threads and time.time() < deadline2:
                self._job_threads = {t for t in self._job_threads if t.is_alive()}
                time.sleep(0.2)
        self.logger.info("Shutdown complete")

    def _abort_and_notify(self):
        """SIGINT in-flight borg subprocesses (clean abort) and notify which
        jobs were interrupted and in which phase."""
        for job_id, job in list(self._running_jobs.items()):
            phase = self.executor.current_phase(job_id) or 'unknown'
            pid = self.executor.current_pid(job_id)
            self.logger.warning(f"Interrupting job '{job['name']}' (phase: {phase})")
            if pid:
                try:
                    os.kill(pid, signal.SIGINT)
                except Exception as e:
                    self.logger.warning(f"Failed to SIGINT pid {pid}: {e}")
            try:
                self.notification_service.send_notification(
                    subject=f"Backup job interrupted: {job['name']}",
                    message=(f"Backup job '{job['name']}' was interrupted by a service "
                             f"shutdown while it was in phase '{phase}'."),
                    is_error=True,
                )
            except Exception as e:
                self.logger.error(f"Failed to send interruption notification: {e}")

    def run(self):
        """Main scheduler loop: dispatch due jobs in parallel, bounded by the
        concurrency cap and memory gate."""
        self.logger.info("Backup scheduler started")
        self._recover_interrupted()
        self.logger.info(
            f"Max parallel jobs: {self.max_parallel}; memory delay threshold: "
            f"{self.mem_delay_threshold * 100:.0f}%, resume: "
            f"{self.mem_resume_threshold * 100:.0f}%"
        )

        while self.running:
            try:
                current_time = datetime.now()

                pending_jobs = self.get_pending_jobs(current_time)
                if pending_jobs:
                    self.logger.info(
                        f"Found {len(pending_jobs)} pending jobs at "
                        f"{current_time.strftime('%H:%M')}"
                    )
                self._process_due(pending_jobs, current_time)
                self._process_delayed(current_time)

                # We check every 30 seconds to be responsive to minute
                # boundaries and to pick up freed memory more quickly.
                time.sleep(30)

            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping backup scheduler")
        self.running = False

def main():
    # Ensure the schema exists/up to date so a restart that skips the standalone
    # init_db step still works (idempotent).
    try:
        from scripts.init_db import init_database
        init_database()
    except Exception as e:
        logging.error(f"Database init/migration failed at startup: {e}")

    scheduler = BackupScheduler()

    signal.signal(signal.SIGTERM, scheduler._handle_signal)
    signal.signal(signal.SIGINT, scheduler._handle_signal)

    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()
    except Exception as e:
        logging.error(f"Scheduler crashed: {e}")
        raise

if __name__ == '__main__':
    main()