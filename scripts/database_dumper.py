#!/usr/bin/env python3
import os
import subprocess
import tempfile
import logging
from datetime import datetime, timezone

class DatabaseDumper:
    def __init__(self):
        self.logger = logging.getLogger('DatabaseDumper')
        self.dump_dir = '/tmp/db_dumps'
        
        # Ensure dump directory exists
        os.makedirs(self.dump_dir, exist_ok=True)

    def create_dumps(self, db_config, logger):
        """Create database dumps based on configuration."""
        if not db_config:
            return []
        
        db_type = db_config.get('type', 'postgresql')
        
        try:
            if db_type == 'postgresql':
                return self._dump_postgresql(db_config, logger)
            elif db_type == 'mariadb':
                return self._dump_mariadb(db_config, logger)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
        except Exception as e:
            logger.error(f"Database dump failed: {e}")
            raise

    def _dump_postgresql(self, config, logger):
        """Create PostgreSQL database dumps."""
        logger.info("Creating PostgreSQL database dumps")
        
        host = config['host']
        port = config.get('port', 5432)
        username = config['username']
        password = config['password']
        database = config['database']
        tables = config.get('tables', [])
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ')
        dump_files = []
        
        # Set environment variables for pg_dump
        env = dict(os.environ)
        env['PGPASSWORD'] = password
        
        try:
            if tables:
                # Dump specific tables
                for table in tables:
                    if not table.strip():
                        continue
                        
                    dump_file = os.path.join(
                        self.dump_dir,
                        f"postgresql_{database}_{table}_{timestamp}.sql"
                    )
                    
                    cmd = [
                        'pg_dump',
                        '-h', host,
                        '-p', str(port),
                        '-U', username,
                        '-d', database,
                        '-t', table.strip(),
                        '--no-password',
                        '--verbose',
                        '-f', dump_file
                    ]
                    
                    logger.info(f"Dumping PostgreSQL table: {table}")
                    result = subprocess.run(
                        cmd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout per table
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"pg_dump failed for table {table}: {result.stderr}")
                    
                    dump_files.append(dump_file)
                    logger.info(f"Successfully dumped table {table} to {dump_file}")
            
            else:
                # Dump entire database
                dump_file = os.path.join(
                    self.dump_dir,
                    f"postgresql_{database}_{timestamp}.sql"
                )
                
                cmd = [
                    'pg_dump',
                    '-h', host,
                    '-p', str(port),
                    '-U', username,
                    '-d', database,
                    '--no-password',
                    '--verbose',
                    '-f', dump_file
                ]
                
                logger.info(f"Dumping entire PostgreSQL database: {database}")
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout for full database
                )
                
                if result.returncode != 0:
                    raise Exception(f"pg_dump failed: {result.stderr}")
                
                dump_files.append(dump_file)
                logger.info(f"Successfully dumped database to {dump_file}")
            
            return dump_files
            
        except subprocess.TimeoutExpired:
            logger.error("PostgreSQL dump timed out")
            raise Exception("Database dump timed out")
        except Exception as e:
            # Clean up any partial dump files
            for dump_file in dump_files:
                try:
                    if os.path.exists(dump_file):
                        os.remove(dump_file)
                except Exception:
                    pass
            raise

    def _dump_mariadb(self, config, logger):
        """Create MariaDB/MySQL database dumps."""
        logger.info("Creating MariaDB/MySQL database dumps")
        
        host = config['host']
        port = config.get('port', 3306)
        username = config['username']
        password = config['password']
        database = config['database']
        tables = config.get('tables', [])
        
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ')
        dump_files = []
        
        # Create MySQL credentials file for security
        credentials_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cnf')
        try:
            credentials_file.write(f"""[mysqldump]
host={host}
port={port}
user={username}
password={password}
""")
            credentials_file.close()
            
            # Set secure permissions
            os.chmod(credentials_file.name, 0o600)
            
            if tables:
                # Dump specific tables
                for table in tables:
                    if not table.strip():
                        continue
                        
                    dump_file = os.path.join(
                        self.dump_dir,
                        f"mariadb_{database}_{table}_{timestamp}.sql"
                    )
                    
                    cmd = [
                        'mysqldump',
                        f'--defaults-file={credentials_file.name}',
                        '--single-transaction',
                        '--routines',
                        '--triggers',
                        '--verbose',
                        database,
                        table.strip()
                    ]
                    
                    logger.info(f"Dumping MariaDB table: {table}")
                    
                    with open(dump_file, 'w') as f:
                        result = subprocess.run(
                            cmd,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=300  # 5 minute timeout per table
                        )
                    
                    if result.returncode != 0:
                        raise Exception(f"mysqldump failed for table {table}: {result.stderr}")
                    
                    dump_files.append(dump_file)
                    logger.info(f"Successfully dumped table {table} to {dump_file}")
            
            else:
                # Dump entire database
                dump_file = os.path.join(
                    self.dump_dir,
                    f"mariadb_{database}_{timestamp}.sql"
                )
                
                cmd = [
                    'mysqldump',
                    f'--defaults-file={credentials_file.name}',
                    '--single-transaction',
                    '--routines',
                    '--triggers',
                    '--verbose',
                    database
                ]
                
                logger.info(f"Dumping entire MariaDB database: {database}")
                
                with open(dump_file, 'w') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=600  # 10 minute timeout for full database
                    )
                
                if result.returncode != 0:
                    raise Exception(f"mysqldump failed: {result.stderr}")
                
                dump_files.append(dump_file)
                logger.info(f"Successfully dumped database to {dump_file}")
            
            return dump_files
            
        except subprocess.TimeoutExpired:
            logger.error("MariaDB dump timed out")
            raise Exception("Database dump timed out")
        except Exception as e:
            # Clean up any partial dump files
            for dump_file in dump_files:
                try:
                    if os.path.exists(dump_file):
                        os.remove(dump_file)
                except Exception:
                    pass
            raise
        finally:
            # Clean up credentials file
            try:
                os.unlink(credentials_file.name)
            except Exception:
                pass

    def test_connection(self, config):
        """Test database connection and verify tables exist."""
        db_type = config.get('type', 'postgresql')
        
        try:
            if db_type == 'postgresql':
                return self._test_postgresql_connection(config)
            elif db_type == 'mariadb':
                return self._test_mariadb_connection(config)
            else:
                return False, f"Unsupported database type: {db_type}"
                
        except Exception as e:
            return False, f"Database connection test error: {str(e)}"

    def _test_postgresql_connection(self, config):
        """Test PostgreSQL connection and verify tables."""
        host = config['host']
        port = config.get('port', 5432)
        username = config['username']
        password = config['password']
        database = config['database']
        tables = config.get('tables', [])
        
        env = dict(os.environ)
        env['PGPASSWORD'] = password
        
        # Test basic connection
        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', username,
            '-d', database,
            '-c', 'SELECT version();',
            '--no-password',
            '-t'  # tuples only
        ]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, f"PostgreSQL connection failed: {result.stderr}"
            
            # If specific tables are specified, verify they exist
            if tables:
                for table in tables:
                    if not table.strip():
                        continue
                        
                    table_check_cmd = [
                        'psql',
                        '-h', host,
                        '-p', str(port),
                        '-U', username,
                        '-d', database,
                        '-c', f"SELECT 1 FROM {table.strip()} LIMIT 1;",
                        '--no-password',
                        '-t'
                    ]
                    
                    table_result = subprocess.run(
                        table_check_cmd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if table_result.returncode != 0:
                        return False, f"Table '{table}' not found or not accessible"
            
            return True, "PostgreSQL connection successful"
            
        except subprocess.TimeoutExpired:
            return False, "PostgreSQL connection test timed out"

    def _test_mariadb_connection(self, config):
        """Test MariaDB/MySQL connection and verify tables."""
        host = config['host']
        port = config.get('port', 3306)
        username = config['username']
        password = config['password']
        database = config['database']
        tables = config.get('tables', [])
        
        # Create temporary credentials file
        credentials_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cnf')
        try:
            credentials_file.write(f"""[mysql]
host={host}
port={port}
user={username}
password={password}
""")
            credentials_file.close()
            os.chmod(credentials_file.name, 0o600)
            
            # Test basic connection
            cmd = [
                'mysql',
                f'--defaults-file={credentials_file.name}',
                '-e', 'SELECT VERSION();',
                database
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, f"MariaDB connection failed: {result.stderr}"
            
            # If specific tables are specified, verify they exist
            if tables:
                for table in tables:
                    if not table.strip():
                        continue
                        
                    table_check_cmd = [
                        'mysql',
                        f'--defaults-file={credentials_file.name}',
                        '-e', f'SELECT 1 FROM {table.strip()} LIMIT 1;',
                        database
                    ]
                    
                    table_result = subprocess.run(
                        table_check_cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if table_result.returncode != 0:
                        return False, f"Table '{table}' not found or not accessible"
            
            return True, "MariaDB connection successful"
            
        except subprocess.TimeoutExpired:
            return False, "MariaDB connection test timed out"
        finally:
            # Clean up credentials file
            try:
                os.unlink(credentials_file.name)
            except Exception:
                pass

    def cleanup_old_dumps(self, max_age_hours=24):
        """Clean up old dump files to save disk space."""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            for filename in os.listdir(self.dump_dir):
                filepath = os.path.join(self.dump_dir, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    
                    if file_time < cutoff_time:
                        try:
                            os.remove(filepath)
                            self.logger.info(f"Cleaned up old dump file: {filename}")
                        except Exception as e:
                            self.logger.warning(f"Failed to remove old dump file {filename}: {e}")
                            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old dumps: {e}")

if __name__ == '__main__':
    # This can be used for testing database dump functionality
    pass