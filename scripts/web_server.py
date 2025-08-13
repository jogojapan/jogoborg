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

# Add project root to Python path
sys.path.append('/app')

from scripts.notification_service import NotificationService
from scripts.database_dumper import DatabaseDumper
from scripts.s3_sync import S3Syncer
from scripts.init_gpg import encrypt_data, decrypt_data

class JogoborgHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db_path = '/config/jogoborg.db'
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
            logging.error(f"GET request error: {e}")
            self._send_error(500, "Internal server error")

    def do_POST(self):
        """Handle POST requests."""
        try:
            
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
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
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logging.error(f"POST request error: {e}")
            self._send_error(500, "Internal server error")

    def do_PUT(self):
        """Handle PUT requests."""
        try:
            
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
            logging.error(f"PUT request error: {e}")
            self._send_error(500, "Internal server error")

    def do_DELETE(self):
        """Handle DELETE requests."""
        try:
            
            path = urlparse(self.path).path
            
            if path.startswith('/api/jobs/'):
                job_id = path.split('/')[-1]
                self._handle_delete_job(job_id)
            else:
                self._send_error(404, "Not found")
                
        except Exception as e:
            logging.error(f"DELETE request error: {e}")
            self._send_error(500, "Internal server error")

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
        """Get list of repositories in /borgspace."""
        try:
            repositories = []
            borgspace_path = '/borgspace'
            
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
            logging.error(f"Error getting repositories: {e}")
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
            logging.error(f"Error unlocking repository: {e}")
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
            logging.error(f"Error creating job: {e}")
            self._send_error(500, "Failed to create job")

    def _handle_update_job(self, job_id, data):
        """Update an existing backup job."""
        try:
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
            logging.error(f"Error updating job: {e}")
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
            logging.error(f"Error deleting job: {e}")
            self._send_error(500, "Failed to delete job")

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
            logging.error(f"Error getting job logs: {e}")
            self._send_error(500, "Failed to get job logs")

    def _handle_browse_sources(self, data):
        """Browse source directory structure."""
        try:
            path = data.get('path', '/sourcespace')
            
            if not path.startswith('/sourcespace'):
                self._send_error(400, "Access denied: path must be within /sourcespace")
                return
            
            if not os.path.exists(path):
                self._send_error(404, "Path not found")
                return
            
            items = []
            
            try:
                for item_name in sorted(os.listdir(path)):
                    item_path = os.path.join(path, item_name)
                    
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
            logging.error(f"Error browsing sources: {e}")
            self._send_error(500, "Failed to browse directory")

    def _handle_calculate_size(self, data):
        """Calculate directory size recursively."""
        try:
            path = data.get('path')
            
            if not path or not path.startswith('/sourcespace'):
                self._send_error(400, "Invalid path")
                return
            
            if not os.path.exists(path):
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
            size = get_size(path)
            self._send_json_response({'size': size})
            
        except Exception as e:
            logging.error(f"Error calculating size: {e}")
            self._send_error(500, "Failed to calculate size")

    def _handle_get_notifications(self):
        """Get notification settings (with masked sensitive data)."""
        try:
            settings = self.notification_service.get_notification_settings(mask_sensitive=True)
            self._send_json_response({'settings': settings})
            
        except Exception as e:
            logging.error(f"Error getting notifications: {e}")
            self._send_error(500, "Failed to get notification settings")

    def _handle_get_notifications_for_edit(self):
        """Get full notification settings for editing (includes sensitive data)."""
        try:
            settings = self.notification_service.get_notification_settings(mask_sensitive=False)
            self._send_json_response({'settings': settings})
            
        except Exception as e:
            logging.error(f"Error getting notifications for edit: {e}")
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
            logging.error(f"Error updating notifications: {e}")
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
            logging.error(f"Error testing SMTP: {e}")
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
            logging.error(f"Error testing webhook: {e}")
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
            logging.error(f"Error testing database: {e}")
            self._send_error(500, "Database test failed")

    def _serve_static_file(self, path):
        """Serve static files from Flutter web build."""
        # Remove leading slash and handle index
        if path == '/' or path == '':
            path = '/index.html'
        
        file_path = '/app/build/web' + path
        
        if not os.path.exists(file_path):
            # Try adding .html extension
            html_path = file_path + '.html'
            if os.path.exists(html_path):
                file_path = html_path
            else:
                # Serve index.html for client-side routing
                file_path = '/app/build/web/index.html'
        
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
            logging.error(f"Error serving static file {file_path}: {e}")
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
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/log/web_server.log'),
            logging.StreamHandler()
        ]
    )
    
    server = HTTPServer(('0.0.0.0', port), JogoborgHTTPHandler)
    
    logging.info(f"Starting Jogoborg web server on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down web server")
        server.shutdown()

if __name__ == '__main__':
    run_server()