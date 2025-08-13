#!/usr/bin/env python3
import sqlite3
import os

def init_database():
    """Initialize SQLite database with required tables."""
    db_path = '/config/jogoborg.db'
    
    # Ensure config directory exists
    os.makedirs('/config', exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create backup jobs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS backup_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        schedule TEXT NOT NULL,
        compression TEXT DEFAULT 'lz4',
        exclude_patterns TEXT,
        keep_daily INTEGER DEFAULT 7,
        keep_monthly INTEGER DEFAULT 6,
        keep_yearly INTEGER DEFAULT 1,
        source_directories TEXT NOT NULL,
        pre_command TEXT,
        post_command TEXT,
        s3_config TEXT,
        db_config TEXT,
        repository_passphrase TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create job execution logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        started_at TIMESTAMP NOT NULL,
        finished_at TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'running',
        create_duration INTEGER,
        create_max_memory INTEGER,
        prune_duration INTEGER,
        prune_max_memory INTEGER,
        compact_duration INTEGER,
        compact_max_memory INTEGER,
        db_dump_duration INTEGER,
        db_dump_max_memory INTEGER,
        error_message TEXT,
        FOREIGN KEY (job_id) REFERENCES backup_jobs (id)
    )
    ''')
    
    # Create repositories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        encryption_key_hint TEXT,
        last_accessed TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create archives table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        size INTEGER,
        files_count INTEGER,
        FOREIGN KEY (repository_id) REFERENCES repositories (id)
    )
    ''')
    
    # Create notification settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notification_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        smtp_config TEXT,
        webhook_config TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert default notification settings record
    cursor.execute('''
    INSERT OR IGNORE INTO notification_settings (id) VALUES (1)
    ''')
    
    # Create indexes for better performance
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_job_logs_started_at ON job_logs(started_at)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_archives_repository_id ON archives(repository_id)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_archives_created_at ON archives(created_at)
    ''')
    
    # Create trigger to update updated_at timestamp
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_backup_jobs_updated_at
    AFTER UPDATE ON backup_jobs
    FOR EACH ROW
    BEGIN
        UPDATE backup_jobs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    ''')
    
    cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_notification_settings_updated_at
    AFTER UPDATE ON notification_settings
    FOR EACH ROW
    BEGIN
        UPDATE notification_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
    ''')
    
    # Handle database migrations for existing databases
    _migrate_database(cursor)
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully.")

def _migrate_database(cursor):
    """Handle database migrations for existing databases."""
    
    # Check if repository_passphrase column exists, add it if it doesn't
    cursor.execute("PRAGMA table_info(backup_jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'repository_passphrase' not in columns:
        print("Adding repository_passphrase column to backup_jobs table...")
        cursor.execute("ALTER TABLE backup_jobs ADD COLUMN repository_passphrase TEXT")
        print("Migration completed: repository_passphrase column added.")

if __name__ == '__main__':
    init_database()