#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import logging
import stat
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import time
import subprocess
import threading
import hashlib
import secrets
from croniter import croniter

# Add project root to Python path
sys.path.append('/app')

from scripts.notification_service import NotificationService
from scripts.database_dumper import DatabaseDumper
from scripts.memory_monitor import memory_stats
from scripts.s3_sync import S3Syncer
from scripts.backup_executor import BackupExecutor
from scripts.init_gpg import encrypt_data, decrypt_data

# Load the credentials from environment variables
# Strip whitespace and carriage returns from credentials
JOGOBORG_WEB_USERNAME = os.environ.get('JOGOBORG_WEB_USERNAME', 'admin').strip()
JOGOBORG_WEB_PASSWORD = os.environ.get('JOGOBORG_WEB_PASSWORD', '').strip()

# Debug: Show raw environment variable details
_raw_password = os.environ.get('JOGOBORG_WEB_PASSWORD', '')
_raw_username = os.environ.get('JOGOBORG_WEB_USERNAME', '')


from logging.handlers import RotatingFileHandler
log_dir = os.environ.get('JOGOBORG_LOG_DIR', '/log')
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Module-level (shared across HTTP handler instances) cache for archive
# browsing: (repo_path, archive) -> {'base', 'ts', 'dirs': {path: [items]}}.
# BaseHTTPRequestHandler is instantiated per request, so this must not live on
# the instance.
_ARCHIVE_BROWSE_CACHE = {}
_ARCHIVE_BROWSE_TTL = 1800
_ARCHIVE_BROWSE_MAX_DIRS = 10000

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
            elif path == '/api/job-logs':
                self._handle_get_job_logs_timeline(parsed_path.query)
            elif path == '/api/system/memory':
                self._handle_get_system_memory()
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
            elif path == '/api/repositories':
                self._handle_create_repository(data)
            elif path == '/api/sources/browse':
                self._handle_browse_sources(data)
            elif path == '/api/sources/size':
                self._handle_calculate_size(data)
            elif path.startswith('/api/repositories/') and path.endswith('/unlock'):
                repo_id = path.split('/')[-2]
                self._handle_unlock_repository(repo_id, data)
            elif path.startswith('/api/repositories/') and path.endswith('/browse'):
                parts = path.split('/')
                # ['', 'api', 'repositories', <id>, 'archives', <archive>, 'browse']
                if len(parts) == 7:
                    self._handle_browse_archive(parts[3], parts[5], data)
                else:
                    self._send_error(404, "Not found")
            elif path == '/api/notifications/test/smtp':
                self._handle_test_smtp(data)
            elif path == '/api/notifications/test/webhook':
                self._handle_test_webhook(data)
            elif path == '/api/database/test':
                self._handle_test_database(data)
            elif path == '/api/s3/test':
                self._handle_test_s3(data)
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
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        # Detailed debugging
        logger.debug(f"=== LOGIN ATTEMPT ===")
        logger.debug(f"Username match: {username == JOGOBORG_WEB_USERNAME}")
        logger.debug(f"Password match: {password == JOGOBORG_WEB_PASSWORD}")
        logger.debug(f"=== END LOGIN ATTEMPT ===")
        
        if username == JOGOBORG_WEB_USERNAME and password == JOGOBORG_WEB_PASSWORD:
            logger.info(f"Successful login for user: {username}")
            # Generate a token (in the future, we will use a proper JWT or session system)
            token = hashlib.sha256(f"{username}:{password}".encode()).hexdigest()

            self._send_json_response({
                'token': token,
                'message': 'Login successful'
            })
        else:
            logger.warning(f"Failed login attempt for user: {username}")
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
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.wfile.write(json.dumps(response).encode())

    def _handle_get_repositories(self):
        """Get list of repositories in borgspace."""
        try:
            repositories = []
            borgspace_path = os.environ.get('JOGOBORG_BORGSPACE_DIR', '/borgspace')

            # Paths for which we have a stored (encrypted) passphrase, so the
            # UI can auto-unlock them.
            stored = set()
            try:
                conn = sqlite3.connect(self.db_path)
                stored = {
                    row[0]
                    for row in conn.execute(
                        "SELECT path FROM repositories "
                        "WHERE encrypted_passphrase IS NOT NULL AND encrypted_passphrase != ''"
                    )
                }
                conn.close()
            except Exception:
                stored = set()

            if os.path.exists(borgspace_path):
                for item in os.listdir(borgspace_path):
                    repo_path = os.path.join(borgspace_path, item)
                    if os.path.isdir(repo_path):
                        # Check if it's a valid Borg repository
                        config_file = os.path.join(repo_path, 'config')
                        if os.path.exists(config_file):
                            has_key = repo_path in stored
                            key = self._stored_passphrase(repo_path) if has_key else None
                            repositories.append({
                                'id': hash(item) % 10000,
                                'name': item,
                                'path': repo_path,
                                'created_at': datetime.fromtimestamp(os.path.getctime(repo_path)).isoformat(),
                                'archives_count': self._count_archives(repo_path, key),
                                'has_stored_key': has_key,
                            })
            
            self._send_json_response({'repositories': repositories})
            
        except Exception as e:
            logger.error(f"Error getting repositories: {e}")
            self._send_error(500, "Failed to get repositories")

    def _count_archives(self, repo_path, passphrase):
        """Number of archives in a repository, or None if it can't be read
        (e.g. no stored passphrase, so the encrypted repository can't be
        listed)."""
        if not passphrase:
            return None
        try:
            result = subprocess.run(
                ['borg', 'list', '--short', repo_path],
                capture_output=True,
                text=True,
                env=dict(os.environ, BORG_PASSPHRASE=passphrase),
                timeout=60,
            )
            if result.returncode != 0:
                return None
            return len([line for line in result.stdout.strip().split('\n') if line.strip()])
        except Exception:
            return None

    def _handle_create_repository(self, data):
        """Create a new Borg repository and remember its passphrase."""
        try:
            name = data.get('name') or ''
            passphrase = data.get('passphrase') or ''
            executor = BackupExecutor()
            try:
                repo_path = executor.create_repository(name, passphrase, logger)
            except ValueError as e:
                self._send_error(400, str(e))
                return

            # Remember the passphrase (encrypted) for automatic unlock.
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO repositories (path, name, encrypted_passphrase)
                    VALUES (?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        name = excluded.name,
                        encrypted_passphrase = excluded.encrypted_passphrase
                ''', (repo_path, name, encrypt_data(passphrase)))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to store repository passphrase: {e}")

            self._send_json_response({
                'message': 'Repository created successfully',
                'repository': {'name': name, 'path': repo_path},
            })
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            self._send_error(500, "Failed to create repository")

    def _find_repository(self, repo_id):
        """Locate a repository in borgspace by its (hash-derived) id.
        Returns (repo_path, repo_name) or (None, None)."""
        borgspace = os.environ.get('JOGOBORG_BORGSPACE_DIR', '/borgspace')
        try:
            repo_id = int(repo_id)
        except (TypeError, ValueError):
            return None, None
        if os.path.isdir(borgspace):
            for item in os.listdir(borgspace):
                if hash(item) % 10000 == repo_id:
                    return os.path.join(borgspace, item), item
        return None, None

    def _stored_passphrase(self, repo_path):
        """Return the decrypted stored passphrase for a repo path, or None."""
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT encrypted_passphrase FROM repositories WHERE path = ?",
                (repo_path,),
            ).fetchone()
            conn.close()
            if row and row[0]:
                return decrypt_data(row[0])
        except Exception as e:
            logger.error(f"Failed to read stored passphrase for {repo_path}: {e}")
        return None

    def _resolve_key(self, repo_path, provided):
        """A usable encryption key: the provided one, else the stored
        (decrypted) passphrase, else None."""
        if provided:
            return provided
        return self._stored_passphrase(repo_path)

    # --- archive browsing -------------------------------------------------

    def _borg_list(self, repo_path, archive, key, subpath=None):
        """Run `borg list --json-lines` and return the parsed entries, or
        None on failure."""
        cmd = ['borg', 'list', '--json-lines', f'{repo_path}::{archive}']
        if subpath:
            cmd.append(subpath)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=dict(os.environ, BORG_PASSPHRASE=key),
            timeout=300,
        )
        if result.returncode != 0:
            return None
        entries = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    @staticmethod
    def _archive_base(entries):
        """Common path prefix of all archive entries.

        Borg stores paths relative to the archive root but prefixed by the
        source path given to `borg create`, including that source directory
        itself as a 'd' entry. We take the deepest path that all entries share
        so the browser starts at the source directory's contents rather than
        the host path. If that common path is itself a single file, collapse
        it to its parent so the file shows as a root child."""
        paths = [e.get('path', '').replace('\\', '/') for e in entries]
        paths = [p for p in paths if p]
        if not paths:
            return ''
        base = os.path.commonpath(paths).replace('\\', '/')
        files = {e.get('path', '').replace('\\', '/') for e in entries if e.get('type') != 'd'}
        if base in files and os.path.dirname(base):
            base = os.path.dirname(base)
        return base

    @staticmethod
    def _archive_children(entries, base, display_path):
        """First-level children of display_path from a borg listing."""
        seg = display_path.strip('/').replace('\\', '/')
        base_part = base.strip('/')
        real = base_part + ('/' + seg if seg else '')
        prefix = real.rstrip('/')
        prefix_full = (prefix + '/') if prefix else ''
        items = []
        for e in entries:
            p = e.get('path', '').replace('\\', '/').lstrip('/')
            if prefix and not p.startswith(prefix):
                continue
            if prefix_full:
                if not p.startswith(prefix_full):
                    continue
                rel = p[len(prefix_full):]
            else:
                rel = p
            if not rel or '/' in rel:
                continue
            is_dir = e.get('type') == 'd'
            items.append({
                'name': rel,
                'is_directory': is_dir,
                'size': e.get('size') if not is_dir else None,
                'mtime': e.get('mtime'),
            })
        items.sort(key=lambda i: (not i['is_directory'], i['name'].lower()))
        return items

    def _archive_dir_items(self, repo_path, archive, key, display_path,
                           repo_name):
        """Return the children items of display_path (cached), or None if the
        archive/path cannot be listed."""
        cache_key = (repo_path, archive)
        now = time.time()
        entry = _ARCHIVE_BROWSE_CACHE.get(cache_key)
        if entry is None or now - entry['ts'] > _ARCHIVE_BROWSE_TTL:
            entries = self._borg_list(repo_path, archive, key)
            if entries is None:
                return None
            entry = {'base': self._archive_base(entries), 'ts': now, 'dirs': {}}
            _ARCHIVE_BROWSE_CACHE[cache_key] = entry
        base = entry['base']
        if base is None:
            return []

        if display_path in entry['dirs']:
            entry['ts'] = now
            return entry['dirs'][display_path]

        # Limit a per-directory borg query to that subtree. Borg stores paths
        # relative (no leading slash), so build the real path from the base.
        seg = display_path.strip('/').replace('\\', '/')
        real = '/'.join(part for part in [base.strip('/'), seg] if part)
        entries = self._borg_list(repo_path, archive, key, real or None)
        if entries is None:
            return None
        items = self._archive_children(entries, base, display_path)

        # Cache with a simple cap (evict oldest entry by ts).
        if len(entry['dirs']) >= _ARCHIVE_BROWSE_MAX_DIRS:
            oldest = min(entry['dirs'], key=lambda k: (_ARCHIVE_BROWSE_CACHE.get(cache_key) or {}).get('ts', now))
            entry['dirs'].pop(oldest, None)
        entry['dirs'][display_path] = items
        return items

    def _handle_browse_archive(self, repo_id, archive, data):
        """Return the immediate children of a path inside an archive."""
        try:
            repo_path, repo_name = self._find_repository(repo_id)
            if not repo_path or not repo_name:
                self._send_error(404, "Repository not found")
                return

            if (
                not archive
                or archive in ('.', '..')
                or re.fullmatch(r'[A-Za-z0-9_.-]+', archive) is None
            ):
                self._send_error(400, "Invalid archive name")
                return

            key = self._resolve_key(repo_path, data.get('encryption_key'))
            if not key:
                self._send_error(400, "Encryption key required")
                return

            path = (data.get('path') or '/')
            if not path.startswith('/') or '..' in path.split('/'):
                self._send_error(400, "Invalid path")
                return

            items = self._archive_dir_items(
                repo_path, archive, key, path, repo_name
            )
            if items is None:
                self._send_error(404, "Path not found in archive")
                return
            self._send_json_response({'path': path, 'items': items})
        except Exception as e:
            logger.error(f"Error browsing archive: {e}")
            self._send_error(500, "Failed to browse archive")

    def _handle_unlock_repository(self, repo_id, data):
        """Unlock repository and list archives."""
        try:
            encryption_key = data.get('encryption_key')

            repo_path, repo_name = self._find_repository(repo_id)
            if not repo_path or not repo_name:
                self._send_error(404, "Repository not found")
                return

            encryption_key = self._resolve_key(repo_path, encryption_key)
            
            if not encryption_key:
                self._send_error(400, "Encryption key required")
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
            SELECT id, name, repository, schedule, compression, exclude_patterns,
                   keep_daily, keep_monthly, keep_yearly, source_directories,
                   pre_command, post_command, s3_config, db_config,
                   repository_passphrase, created_at, updated_at
            FROM backup_jobs
            ORDER BY created_at DESC
            ''')
            
            jobs = []
            for row in cursor.fetchall():
                job_id, name, repository, schedule, compression, exclude_patterns, \
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
                    'repository': repository,
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
            
            # Validate cron schedule
            if not self._validate_cron_schedule(data['schedule']):
                self._send_error(400, f"Invalid cron schedule: {data['schedule']}. Must be a valid 5-field cron expression (minute hour day month day_of_week)")
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
                    name, repository, schedule, compression, exclude_patterns,
                    keep_daily, keep_monthly, keep_yearly, source_directories,
                    pre_command, post_command, s3_config, db_config, repository_passphrase
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['name'],
                    data.get('repository') or data['name'],
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
            # Validate cron schedule if provided
            if data.get('schedule') and not self._validate_cron_schedule(data['schedule']):
                self._send_error(400, f"Invalid cron schedule: {data['schedule']}. Must be a valid 5-field cron expression (minute hour day month day_of_week)")
                return
            
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
                
                # Update all fields except repository_passphrase. The passphrase
                # is only touched when a non-empty one is supplied, so an edit
                # that doesn't change it preserves the stored (encrypted) one
                # instead of wiping it.
                cursor.execute('''
                UPDATE backup_jobs SET
                    name = ?, schedule = ?, compression = ?, exclude_patterns = ?,
                    keep_daily = ?, keep_monthly = ?, keep_yearly = ?,
                    source_directories = ?, pre_command = ?, post_command = ?,
                    s3_config = ?, db_config = ?
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
                    job_id
                ))

                if data.get('repository_passphrase'):
                    cursor.execute('''
                    UPDATE backup_jobs SET repository_passphrase = ? WHERE id = ?
                    ''', (repository_passphrase_encrypted, job_id))

                if data.get('repository'):
                    cursor.execute('''
                    UPDATE backup_jobs SET repository = ? WHERE id = ?
                    ''', (data['repository'], job_id))

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

    def _handle_get_job_logs_timeline(self, query_string):
        """Return all job runs within [since, until] plus the container memory
        limit, for the scheduling Gantt."""
        params = parse_qs(query_string)
        try:
            since = params.get('since', [None])[0]
            until = params.get('until', [None])[0]
            now = datetime.now(timezone.utc)
            if not until:
                until = now.isoformat()
            if not since:
                since = (now - timedelta(days=7)).isoformat()

            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.id, l.job_id, j.name, l.started_at, l.finished_at,
                           l.status, l.create_max_memory, l.prune_max_memory,
                           l.compact_max_memory, l.db_dump_max_memory,
                           l.db_archive_max_memory, l.db_prune_max_memory,
                           l.db_compact_max_memory
                    FROM job_logs l
                    LEFT JOIN backup_jobs j ON l.job_id = j.id
                    WHERE l.started_at >= ? AND l.started_at <= ?
                    ORDER BY l.started_at ASC
                ''', (since, until))
                logs = []
                for row in cursor.fetchall():
                    mems = [m for m in row[6:] if m is not None]
                    logs.append({
                        'id': row[0],
                        'job_id': row[1],
                        'job_name': row[2] if row[2] else f"job-{row[1]}",
                        'started_at': row[3],
                        'finished_at': row[4],
                        'status': row[5],
                        'peak_memory_mb': max(mems) if mems else None,
                    })
            finally:
                conn.close()

            stats = memory_stats()
            self._send_json_response({
                'logs': logs,
                'memory_limit_mb': stats['limit_mb'] if stats else None,
            })
        except Exception as e:
            logger.error(f"Error getting job logs timeline: {e}")
            self._send_error(500, "Failed to get job logs")

    def _handle_get_system_memory(self):
        """Return container memory limit/usage (may be null outside a container)."""
        stats = memory_stats()
        self._send_json_response(
            stats if stats else {'limit_mb': None, 'current_mb': None}
        )

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

    def _handle_test_s3(self, data):
        """Test S3 configuration."""
        try:
            success, message = self.s3_syncer.test_s3_connection(data)
            
            if success:
                self._send_json_response({'message': message})
            else:
                self._send_error(400, message)
                
        except Exception as e:
            logger.error(f"Error testing S3 connection: {e}")
            self._send_error(500, "S3 test failed")

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
        elif file_path.endswith('.mjs'):
            return 'application/javascript'
        elif file_path.endswith('.wasm'):
            return 'application/wasm'
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

    def _validate_cron_schedule(self, schedule):
        """Validate that schedule is a valid cron expression."""
        try:
            # Try to create a croniter object - if it works, it's valid
            croniter(schedule, datetime.now())
            return True
        except Exception:
            return False

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
        logger.warning("JOGOBORG_WEB_PASSWORD environment variable not set or empty. Authentication will not work.")

    # Ensure the database schema exists/is up to date so a restart that skips
    # the standalone init_db step still works (schema/migration is idempotent).
    try:
        from scripts.init_db import init_database
        init_database()
        logger.info("Database schema checked / migrated")
    except Exception as e:
        logger.error(f"Database init/migration failed at startup: {e}")

    server = HTTPServer(('0.0.0.0', port), JogoborgHTTPHandler)
    logger.info(f"Starting Jogoborg web server on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down web server")
        server.shutdown()

if __name__ == '__main__':
    run_server()
