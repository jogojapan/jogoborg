#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import logging
import stat
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess
import threading
import hashlib
import secrets

# Add project root to Python path
sys.path.append('/app')

from scripts.notification_service import NotificationService
from scripts.database_dumper import DatabaseDumper
from scripts.s3_sync import S3Syncer
from scripts.backup_executor import BackupExecutor
from scripts.init_gpg import encrypt_data, decrypt_data

# Load the credentials from environment variables
JOGOBORG_WEB_USERNAME = os.environ.get('JOGOBORG_WEB_USERNAME', 'admin')
JOGOBORG_WEB_PASSWORD = os.environ.get('JOGOBORG_WEB_PASSWORD', '')


from logging.handlers import RotatingFileHandler
log_dir = os.environ.get('JOGOBORG_LOG_DIR', '/log')
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(
    os.path.join(log_dir, 'web_server.log'),
    maxBytes    = 5 * 1024 * 1024,  # 5 MB
    backupCount = 3  # Keep up to 3 old log files
)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class JogoborgHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        config_dir = os.environ.get('JOGOBORG_CONFIG_DIR', '/config')
        self.db_path = os.path.join(config_dir, 'jogoborg.db')
        self.notification_service = NotificationService()
        self.database_dumper = DatabaseDumper()
        self.s3_syncer = S3Syncer()
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            # Check authentication for protected endpoints
            if self._is_protected_endpoint(path, "GET") and not self._is_authenticated():
                self._send_error(401, "Unauthorized")
                return

            if path == '/health':
                self._handle_health_check()
            elif path == '/api/repositories':
                self._handle_get_repositories()
            elif path == '/api/jobs':
                self._handle_get_jobs()
            elif path.startswith('/api/jobs/') and path.endswith('/logs'):
                job_id = path.split('/')[-2]
                self._handle_get_job_logs(job_id, parsed_path.query)
            elif path == '/api/notifications':
                self._handle_get_notifications()
            elif path == '/api/notifications/edit':
                self._handle_get_notifications_for_edit()
            elif path.startswith('/'):
                self._serve_static_file(path)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logger.error(f"GET request error: {e}")
            self._send_error(500, "Internal server error")

    def do_POST(self):
        """Handle POST requests."""
        try:
            
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            # Handle login specially (no auth required)
            if path == '/api/login':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                try:
                    data = json.loads(post_data) if post_data else {}
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {post_data}")
                    self._send_error(400, "Invalid JSON")
                    return
                self._handle_login(data)
                return

            # Check authentication for all other POST endpoints
            if self._is_protected_endpoint(path, "POST") and not self._is_authenticated():
                self._send_error(401, "Unauthorized")
                return

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data) if post_data else {}
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON")
                return
            
            if path == '/api/jobs':
                self._handle_create_job(data)
            elif path == '/api/sources/browse':
                self._handle_browse_sources(data)
            elif path == '/api/sources/size':
                self._handle_calculate_size(data)
            elif path.startswith('/api/repositories/') and path.endswith('/unlock'):
                repo_id = path.split('/')[-2]
                self._handle_unlock_repository(repo_id, data)
            elif path == '/api/notifications/test/smtp':
                self._handle_test_smtp(data)
            elif path == '/api/notifications/test/webhook':
                self._handle_test_webhook(data)
            elif path == '/api/database/test':
                self._handle_test_database(data)
            elif path.startswith('/api/jobs/') and path.endswith('/trigger'):
                job_id = path.split('/')[-2]
                self._handle_trigger_job(job_id)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logger.error(f"POST request error: {e}")
            self._send_error(500, "Internal server error")

    def do_PUT(self):
        """Handle PUT requests."""
        try:
            # Check authentication for all PUT endpoints
            if not self._is_authenticated():
                self._send_error(401, "Unauthorized")
                return

            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data) if post_data else {}
            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON")
                return
            
            if path.startswith('/api/jobs/'):
                job_id = path.split('/')[-1]
                self._handle_update_job(job_id, data)
            elif path == '/api/notifications':
                self._handle_update_notifications(data)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logger.error(f"PUT request error: {e}")
            self._send_error(500, "Internal server error")

    def do_DELETE(self):
        """Handle DELETE requests."""
        try:
            # Check authentication for all DELETE endpoints
            if not self._is_authenticated():
                self._send_error(401, "Unauthorized")
                return

            path = urlparse(self.path).path
            
            if path.startswith('/api/jobs/'):
                job_id = path.split('/')[-1]
                self._handle_delete_job(job_id)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logger.error(f"DELETE request error: {e}")
            self._send_error(500, "Internal server error")

    def _is_protected_endpoint(self, path, method):
        """Determine if an endpoint requires authentication."""
        # Login endpoint doesn't require auth
        if path == '/api/login':
            return False

        # All API endpoints except login require auth
        if path.startswith('/api/'):
            return True

        # All non-API endpoints (static files) don't require auth
        return False

    def _is_authenticated(self):
        """Check if the request has a valid authentication token."""
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False

        token = auth_header[7:]  # Remove "Bearer " prefix

        # For now, we'll regenerate the expected token each time. We
        # will store this in a database in the future.
        expected_token = hashlib.sha256(f"{JOGOBORG_WEB_USERNAME}:{JOGOBORG_WEB_PASSWORD}".encode()).hexdigest()

        return secrets.compare_digest(token, expected_token)

    def _handle_login(self, data):
        """Handle login requests."""
        username = data.get('username')
        password = data.get('password')

        # Check against configured credentials
        logger.debug(f"Checking user name '{username}', pw <hidden>.")
        if username == JOGOBORG_WEB_USERNAME and password == JOGOBORG_WEB_PASSWORD:
            logger.debug("User name and password are correct.")
            # Generate a token (in the future, we will use a proper JWT or session system)
            token = hashlib.sha256(f"{username}:{password}".encode()).hexdigest()

            self._send_json_response({
                'token': token,
                'message': 'Login successful'
            })
        else:
            logger.debug("User name or password incorrect.")
            self._send_error(401, "Invalid credentials")

    def _set_cors_headers(self):
        """Set CORS headers for web requests."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _handle_health_check(self):
        """Handle health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        response = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.wfile.write(json.dumps(response).encode())

    def _handle_get_repositories(self):
        """Get list of repositories in borgspace."""
        try:
            repositories = []
            borgspace_path = os.environ.get('JOGOBORG_BORGSPACE_DIR', '/borgspace')
            
            if os.path.exists(borgspace_path):
                for item in os.listdir(borgspace_path):
                    repo_path = os.path.join(borgspace_path, item)
                    if os.path.isdir(repo_path):
                        # Check if it's a valid Borg repository
                        config_file = os.path.join(repo_path, 'config')
                        if os.path.exists(config_file):
                            repositories.append({
                                'id': hash(item) % 10000,
                                'name': item,
                                'path': repo_path,
                                'created_at': datetime.fromtimestamp(os.path.getctime(repo_path)).isoformat(),
                                'archives_count': self._count_archives(repo_path)
                            })
            
            self._send_json_response({'repositories': repositories})
            
        except Exception as e:
            logger.error(f"Error getting repositories: {e}")
            self._send_error(500, "Failed to get repositories")

    def _count_archives(self, repo_path):
        """Count archives in a repository."""
        try:
            # Try to list archives using borg list
            result = subprocess.run(
                ['borg', 'list', '--short', repo_path],
                capture_output=True,
                text=True,
                env=dict(os.environ, BORG_PASSPHRASE='changeme'),
                timeout=10
            )
            
            if result.returncode == 0:
                return len([line for line in result.stdout.strip().split('\n') if line.strip()])
            else:
                return 0
                
        except Exception:
            return 0

    def _handle_unlock_repository(self, repo_id, data):
        """Unlock repository and list archives."""
        try:
            encryption_key = data.get('encryption_key')
            if not encryption_key:
                self._send_error(400, "Encryption key required")
                return
            
            # Find repository by ID
            repo_path = None
            borgspace_path = '/borgspace'
            
            for item in os.listdir(borgspace_path):
                if hash(item) % 10000 == int(repo_id):
                    repo_path = os.path.join(borgspace_path, item)
                    break
            
            if not repo_path:
                self._send_error(404, "Repository not found")
                return
            
            # List archives using the provided key
            result = subprocess.run(
                ['borg', 'list', '--json', repo_path],
                capture_output=True,
                text=True,
                env=dict(os.environ, BORG_PASSPHRASE=encryption_key),
                timeout=30
            )
            
            if result.returncode != 0:
                self._send_error(400, "Invalid encryption key or repository error")
                return
            
            # Parse archive list
            archives_data = json.loads(result.stdout)
            archives = []
            
            for archive in archives_data.get('archives', []):
                archives.append({
                    'name': archive['name'],
                    'created_at': archive['start'],
                    'size': archive.get('stats', {}).get('deduplicated_size'),
                    'files_count': archive.get('stats', {}).get('nfiles')
                })
            
            # Sort by creation time (newest first)
            archives.sort(key=lambda x: x['created_at'], reverse=True)
            
            self._send_json_response({'archives': archives})
            
        except Exception as e:
            logger.error(f"Error unlocking repository: {e}")
            self._send_error(500, "Failed to unlock repository")

    def _handle_get_jobs(self):
        """Get list of backup jobs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            SELECT id, name, schedule, compression, exclude_patterns,
                   keep_daily, keep_monthly, keep_yearly, source_directories,
                   pre_command, post_command, s3_config, db_config,
                   repository_passphrase, created_at, updated_at
            FROM backup_jobs
            ORDER BY created_at DESC
            ''')
            
            jobs = []
            for row in cursor.fetchall():
                job_id, name, schedule, compression, exclude_patterns, \
                keep_daily, keep_monthly, keep_yearly, source_directories, \
                pre_command, post_command, s3_config, db_config, \
                repository_passphrase, created_at, updated_at = row
                
                # Parse JSON fields safely
                try:
                    source_dirs = json.loads(source_directories) if source_directories else []
                except (json.JSONDecodeError, TypeError):
                    source_dirs = []
                
                # Decrypt configurations safely
                s3_config_data = None
                db_config_data = None
                
                if s3_config:
                    try:
                        s3_config_data = json.loads(decrypt_data(s3_config))
                    except Exception:
                        # If decryption fails, just set to None
                        s3_config_data = None
                
                if db_config:
                    try:
                        db_config_data = json.loads(decrypt_data(db_config))
                    except Exception:
                        # If decryption fails, just set to None
                        db_config_data = None
                
                jobs.append({
                    'id': job_id,
                    'name': name,
                    'schedule': schedule,
                    'compression': compression,
                    'exclude_patterns': exclude_patterns,
                    'keep_daily': keep_daily,
                    'keep_monthly': keep_monthly,
                    'keep_yearly': keep_yearly,
                    'source_directories': source_dirs,
                    'pre_command': pre_command,
                    'post_command': post_command,
                    's3_config': s3_config_data,
                    'db_config': db_config_data,
                    'created_at': created_at,
                    'updated_at': updated_at
                    # Note: repository_passphrase is intentionally not included for security
                })
            
            self._send_json_response({'jobs': jobs})
            
        finally:
            conn.close()

    def _handle_create_job(self, data):
        """Create a new backup job."""
        try:
            # Validate required fields
            required_fields = ['name', 'schedule', 'source_directories', 'repository_passphrase']
            for field in required_fields:
                if not data.get(field):
                    self._send_error(400, f"Missing required field: {field}")
                    return
            
            logger.debug(f"Creating job: {data.get('name')}, has passphrase: {bool(data.get('repository_passphrase'))}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Encrypt sensitive configurations
                s3_config_encrypted = None
                db_config_encrypted = None
                repository_passphrase_encrypted = None
                
                if data.get('s3_config'):
                    s3_json = json.dumps(data['s3_config'])
                    s3_config_encrypted = encrypt_data(s3_json)
                
                if data.get('db_config'):
                    db_json = json.dumps(data['db_config'])
                    db_config_encrypted = encrypt_data(db_json)
                
                if data.get('repository_passphrase'):
                    repository_passphrase_encrypted = encrypt_data(data['repository_passphrase'])
                    logger.debug(f"Encrypted passphrase: {repository_passphrase_encrypted is not None}")
                else:
                    logger.warning(f"No repository_passphrase in request data for job {data.get('name')}")
                
                cursor.execute('''
                INSERT INTO backup_jobs (
                    name, schedule, compression, exclude_patterns,
                    keep_daily, keep_monthly, keep_yearly, source_directories,
                    pre_command, post_command, s3_config, db_config, repository_passphrase
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['name'],
                    data['schedule'],
                    data.get('compression', 'lz4'),
                    data.get('exclude_patterns', ''),
                    data.get('keep_daily', 7),
                    data.get('keep_monthly', 6),
                    data.get('keep_yearly', 1),
                    json.dumps(data['source_directories']),
                    data.get('pre_command'),
                    data.get('post_command'),
                    s3_config_encrypted,
                    db_config_encrypted,
                    repository_passphrase_encrypted
                ))
                
                conn.commit()
                job_id = cursor.lastrowid
                
                self._send_json_response({
                    'message': 'Job created successfully',
                    'job_id': job_id
                })
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            self._send_error(500, "Failed to create job")

    def _handle_update_job(self, job_id, data):
        """Update an existing backup job."""
        try:
            logger.debug(f"Updating job {job_id}: {data.get('name')}, has passphrase: {bool(data.get('repository_passphrase'))}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Encrypt sensitive configurations
                s3_config_encrypted = None
                db_config_encrypted = None
                repository_passphrase_encrypted = None
                
                if data.get('s3_config'):
                    s3_json = json.dumps(data['s3_config'])
                    s3_config_encrypted = encrypt_data(s3_json)
                
                if data.get('db_config'):
                    db_json = json.dumps(data['db_config'])
                    db_config_encrypted = encrypt_data(db_json)
                
                if data.get('repository_passphrase'):
                    repository_passphrase_encrypted = encrypt_data(data['repository_passphrase'])
                    logger.debug(f"Encrypted passphrase for update: {repository_passphrase_encrypted is not None}")
                else:
                    logger.warning(f"No repository_passphrase in update request for job {job_id}")
                
                cursor.execute('''
                UPDATE backup_jobs SET
                    name = ?, schedule = ?, compression = ?, exclude_patterns = ?,
                    keep_daily = ?, keep_monthly = ?, keep_yearly = ?,
                    source_directories = ?, pre_command = ?, post_command = ?,
                    s3_config = ?, db_config = ?, repository_passphrase = ?
                WHERE id = ?
                ''', (
                    data['name'],
                    data['schedule'],
                    data.get('compression', 'lz4'),
                    data.get('exclude_patterns', ''),
                    data.get('keep_daily', 7),
                    data.get('keep_monthly', 6),
                    data.get('keep_yearly', 1),
                    json.dumps(data['source_directories']),
                    data.get('pre_command'),
                    data.get('post_command'),
                    s3_config_encrypted,
                    db_config_encrypted,
                    repository_passphrase_encrypted,
                    job_id
                ))
                
                conn.commit()
                
                if cursor.rowcount == 0:
                    self._send_error(404, "Job not found")
                else:
                    self._send_json_response({'message': 'Job updated successfully'})
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error updating job: {e}")
            self._send_error(500, "Failed to update job")

    def _handle_delete_job(self, job_id):
        """Delete a backup job."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('DELETE FROM backup_jobs WHERE id = ?', (job_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    self._send_error(404, "Job not found")
                else:
                    self._send_json_response({'message': 'Job deleted successfully'})
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error deleting job: {e}")
            self._send_error(500, "Failed to delete job")

    def _handle_trigger_job(self, job_id):
        """Trigger a backup job to run immediately."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Get the job details
                cursor.execute('SELECT * FROM backup_jobs WHERE id = ?', (job_id,))
                row = cursor.fetchone()
                
                if not row:
                    self._send_error(404, "Job not found")
                    return
                
                # Convert row to dictionary
                columns = [desc[0] for desc in cursor.description]
                job = dict(zip(columns, row))
                
                logger.debug(f"Job loaded from DB: {job['name']}, has passphrase: {job.get('repository_passphrase') is not None}")
                
                # Decrypt encrypted fields if they exist
                if job['s3_config']:
                    try:
                        job['s3_config'] = json.loads(decrypt_data(job['s3_config']))
                    except Exception:
                        job['s3_config'] = None
                
                if job['db_config']:
                    try:
                        job['db_config'] = json.loads(decrypt_data(job['db_config']))
                    except Exception:
                        job['db_config'] = None
                
                if job['repository_passphrase']:
                    try:
                        decrypted = decrypt_data(job['repository_passphrase'])
                        logger.debug(f"Passphrase decrypted successfully: {decrypted is not None}")
                        job['repository_passphrase'] = decrypted
                    except Exception as e:
                        logger.error(f"Failed to decrypt repository passphrase: {e}")
                        self._send_error(500, "Failed to decrypt repository passphrase")
                        return
                else:
                    logger.warning(f"Job {job['name']} has no repository_passphrase in database")
                
                # Convert source_directories from JSON string to list if needed
                if isinstance(job['source_directories'], str):
                    try:
                        job['source_directories'] = json.loads(job['source_directories'])
                    except json.JSONDecodeError:
                        # Fallback to comma-separated string parsing for backwards compatibility
                        job['source_directories'] = [d.strip() for d in job['source_directories'].split(',')]
                
            finally:
                conn.close()
            
            # Execute the job in a background thread to avoid blocking the web server
            def run_job():
                try:
                    executor = BackupExecutor()
                    executor.execute_job(job)
                    logger.info(f"Manual job trigger completed successfully for job: {job['name']}")
                except Exception as e:
                    logger.error(f"Manual job trigger failed for job {job['name']}: {e}")
            
            # Start the job in a separate thread
            job_thread = threading.Thread(target=run_job, daemon=True)
            job_thread.start()
            
            self._send_json_response({
                'message': f'Job "{job["name"]}" has been triggered and is running in the background'
            })
            
        except Exception as e:
            logger.error(f"Error triggering job: {e}")
            self._send_error(500, "Failed to trigger job")

    def _handle_get_job_logs(self, job_id, query_string):
        """Get logs for a specific job."""
        try:
            # Parse query parameters
            params = parse_qs(query_string)
            limit = int(params.get('limit', ['10'])[0])
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                SELECT started_at, finished_at, status, create_duration,
                       create_max_memory, prune_duration, prune_max_memory,
                       compact_duration, compact_max_memory, db_dump_duration,
                       db_dump_max_memory, error_message
                FROM job_logs
                WHERE job_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                ''', (job_id, limit))
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        'started_at': row[0],
                        'finished_at': row[1],
                        'status': row[2],
                        'create_duration': row[3],
                        'create_max_memory': row[4],
                        'prune_duration': row[5],
                        'prune_max_memory': row[6],
                        'compact_duration': row[7],
                        'compact_max_memory': row[8],
                        'db_dump_duration': row[9],
                        'db_dump_max_memory': row[10],
                        'error_message': row[11]
                    })
                
                self._send_json_response({'logs': logs})
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error getting job logs: {e}")
            self._send_error(500, "Failed to get job logs")

    def _handle_browse_sources(self, data):
        """Browse source directory structure."""
        try:
            sourcespace_base = os.environ.get('JOGOBORG_SOURCESPACE_DIR', '/sourcespace')
            requested_path = data.get('path', sourcespace_base)
            
            # If the requested path is the default '/sourcespace', use sourcespace_base instead
            if requested_path == '/sourcespace':
                requested_path = sourcespace_base
            
            # Normalize path and ensure it's within sourcespace
            requested_path = os.path.normpath(requested_path)
            sourcespace_base = os.path.normpath(sourcespace_base)
            
            # Convert to absolute path if needed
            if not os.path.isabs(requested_path):
                requested_path = os.path.join(sourcespace_base, requested_path.lstrip('/'))
            
            # Ensure the path is within sourcespace
            try:
                real_requested = os.path.realpath(requested_path)
                real_sourcespace = os.path.realpath(sourcespace_base)
                
                # Allow the path if it's within sourcespace OR if it equals sourcespace
                if not (real_requested.startswith(real_sourcespace) or real_requested == real_sourcespace):
                    self._send_error(400, "Access denied: path must be within sourcespace")
                    return
            except (OSError, ValueError):
                self._send_error(400, "Invalid path")
                return
            
            if not os.path.exists(requested_path):
                self._send_error(404, "Path not found")
                return
            
            items = []
            
            try:
                for item_name in sorted(os.listdir(requested_path)):
                    item_path = os.path.join(requested_path, item_name)
                    
                    try:
                        stat_info = os.stat(item_path)
                        is_directory = stat.S_ISDIR(stat_info.st_mode)
                        
                        items.append({
                            'name': item_name,
                            'path': item_path,
                            'is_directory': is_directory,
                            'size': stat_info.st_size if not is_directory else None,
                            'permissions': oct(stat_info.st_mode)[-3:],
                            'last_modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                        })
                    except (OSError, PermissionError):
                        # Skip items we can't access
                        continue
                        
            except PermissionError:
                self._send_error(403, "Permission denied")
                return
            
            self._send_json_response({'items': items})
            
        except Exception as e:
            logger.error(f"Error browsing sources: {e}")
            self._send_error(500, "Failed to browse directory")

    def _handle_calculate_size(self, data):
        """Calculate directory size recursively."""
        try:
            sourcespace_base = os.environ.get('JOGOBORG_SOURCESPACE_DIR', '/sourcespace')
            requested_path = data.get('path')
            
            if not requested_path:
                self._send_error(400, "Path is required")
                return
            
            # If the requested path is the default '/sourcespace', use sourcespace_base instead
            if requested_path == '/sourcespace':
                requested_path = sourcespace_base
            
            # Normalize path and ensure it's within sourcespace
            requested_path = os.path.normpath(requested_path)
            sourcespace_base = os.path.normpath(sourcespace_base)
            
            # Convert to absolute path if needed
            if not os.path.isabs(requested_path):
                requested_path = os.path.join(sourcespace_base, requested_path.lstrip('/'))
            
            # Ensure the path is within sourcespace
            try:
                real_requested = os.path.realpath(requested_path)
                real_sourcespace = os.path.realpath(sourcespace_base)
                
                # Allow the path if it's within sourcespace OR if it equals sourcespace
                if not (real_requested.startswith(real_sourcespace) or real_requested == real_sourcespace):
                    self._send_error(400, "Access denied: path must be within sourcespace")
                    return
            except (OSError, ValueError):
                self._send_error(400, "Invalid path")
                return
            
            if not os.path.exists(requested_path):
                self._send_error(404, "Path not found")
                return
            
            def get_size(start_path):
                total_size = 0
                try:
                    if os.path.isfile(start_path):
                        return os.path.getsize(start_path)
                    
                    for dirpath, dirnames, filenames in os.walk(start_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            try:
                                total_size += os.path.getsize(filepath)
                            except (OSError, PermissionError):
                                continue
                except (OSError, PermissionError):
                    pass
                return total_size
            
            # Run size calculation in a thread to avoid blocking
            size = get_size(requested_path)
            self._send_json_response({'size': size})
            
        except Exception as e:
            logger.error(f"Error calculating size: {e}")
            self._send_error(500, "Failed to calculate size")

    def _handle_get_notifications(self):
        """Get notification settings (with masked sensitive data)."""
        try:
            settings = self.notification_service.get_notification_settings(mask_sensitive=True)
            self._send_json_response({'settings': settings})
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            self._send_error(500, "Failed to get notification settings")

    def _handle_get_notifications_for_edit(self):
        """Get full notification settings for editing (includes sensitive data)."""
        try:
            settings = self.notification_service.get_notification_settings(mask_sensitive=False)
            self._send_json_response({'settings': settings})
            
        except Exception as e:
            logger.error(f"Error getting notifications for edit: {e}")
            self._send_error(500, "Failed to get notification settings for editing")

    def _handle_update_notifications(self, data):
        """Update notification settings."""
        try:
            smtp_config = data.get('smtp_config')
            webhook_config = data.get('webhook_config')
            
            self.notification_service.save_notification_settings(
                smtp_config, webhook_config
            )
            
            self._send_json_response({'message': 'Notification settings updated successfully'})
            
        except Exception as e:
            logger.error(f"Error updating notifications: {e}")
            self._send_error(500, "Failed to update notification settings")

    def _handle_test_smtp(self, data):
        """Test SMTP configuration."""
        try:
            success, message = self.notification_service.test_smtp_configuration(data)
            
            if success:
                self._send_json_response({'message': message})
            else:
                self._send_error(400, message)
                
        except Exception as e:
            logger.error(f"Error testing SMTP: {e}")
            self._send_error(500, "SMTP test failed")

    def _handle_test_webhook(self, data):
        """Test webhook configuration."""
        try:
            success, message = self.notification_service.test_webhook_configuration(data)
            
            if success:
                self._send_json_response({'message': message})
            else:
                self._send_error(400, message)
                
        except Exception as e:
            logger.error(f"Error testing webhook: {e}")
            self._send_error(500, "Webhook test failed")

    def _handle_test_database(self, data):
        """Test database configuration."""
        try:
            success, message = self.database_dumper.test_connection(data)
            
            if success:
                self._send_json_response({'message': message})
            else:
                self._send_error(400, message)
                
        except Exception as e:
            logger.error(f"Error testing database: {e}")
            self._send_error(500, "Database test failed")

    def _serve_static_file(self, path):
        """Serve static files from Flutter web build."""
        # Remove leading slash and handle index
        if path == '/' or path == '':
            path = '/index.html'
        
        web_dir = os.environ.get('JOGOBORG_WEB_DIR', '/app/build/web')
        file_path = os.path.join(web_dir, path.lstrip('/'))
        
        # If file doesn't exist, handle fallback logic
        if not os.path.exists(file_path):
            # For index.html, try index-dev.html as fallback
            if path.endswith('index.html') or path == '/index.html':
                dev_index_path = os.path.join(web_dir, 'index-dev.html')
                if os.path.exists(dev_index_path):
                    file_path = dev_index_path
                    logger.info("Serving development index page")
                else:
                    # Neither index.html nor index-dev.html exist
                    logger.error(f"Static file not found: {file_path}")
                    self._send_error(404, "File not found")
                    return
            else:
                # For non-index requests, don't serve index.html
                # This preserves client-side routing but doesn't serve HTML for asset files
                file_extension = os.path.splitext(path)[1].lower()
                
                # Only serve index.html for routes that look like SPA routes (no extension)
                if file_extension in ['', '.html']:
                    # SPA route - serve index.html for client-side routing
                    index_path = os.path.join(web_dir, 'index.html')
                    if os.path.exists(index_path):
                        file_path = index_path
                    else:
                        dev_index_path = os.path.join(web_dir, 'index-dev.html')
                        if os.path.exists(dev_index_path):
                            file_path = dev_index_path
                        else:
                            logger.error(f"Static file not found: {file_path}")
                            self._send_error(404, "File not found")
                            return
                else:
                    # Asset file (js, css, json, wasm, etc.) - don't fallback to index.html
                    logger.error(f"Static file not found: {file_path}")
                    self._send_error(404, "File not found")
                    return
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Set content type based on file extension
            content_type = self._get_content_type(file_path)
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            logger.error(f"Error serving static file {file_path}: {e}")
            self._send_error(404, "File not found")

    def _get_content_type(self, file_path):
        """Get content type based on file extension."""
        if file_path.endswith('.html'):
            return 'text/html'
        elif file_path.endswith('.css'):
            return 'text/css'
        elif file_path.endswith('.js'):
            return 'application/javascript'
        elif file_path.endswith('.json'):
            return 'application/json'
        elif file_path.endswith('.png'):
            return 'image/png'
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            return 'image/jpeg'
        elif file_path.endswith('.ico'):
            return 'image/x-icon'
        else:
            return 'application/octet-stream'

    def _send_json_response(self, data, status_code=200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        response_json = json.dumps(data, indent=2)
        self.wfile.write(response_json.encode())

    def _send_error(self, status_code, message):
        """Send error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        error_response = {
            'error': message,
            'status_code': status_code
        }
        
        self.wfile.write(json.dumps(error_response).encode())

def run_server():
    """Run the HTTP server."""
    port = int(os.environ.get('JOGOBORG_WEB_PORT', os.environ.get('WEB_PORT', 8080)))

    # Check if password is set
    if not JOGOBORG_WEB_PASSWORD:
        logger.warning("JOGOBORG_WEB_PASSWORD environment variable not set. Authentication will not work.")

    server = HTTPServer(('0.0.0.0', port), JogoborgHTTPHandler)
    logger.info(f"Starting Jogoborg web server on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down web server")
        server.shutdown()

if __name__ == '__main__':
    run_server()
