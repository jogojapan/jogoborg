# Jogoborg Local Testing Approach

## Project Analysis

### Architecture Overview

Jogoborg is a multi-component backup management system with:

1. **Frontend**: Flutter web application (built to `/app/build/web`)
   - Modern UI for backup job configuration
   - Authentication-based access
   - Real-time job monitoring and logs

2. **Backend Services** (Python):
   - **Web Server** (`web_server.py`): HTTP API server on port 8080
     - REST endpoints for job management, repository browsing, logs
     - Authentication handling
     - Static file serving for Flutter web app
   
   - **Scheduler** (`scheduler.py`): Background job scheduler
     - Cron-based job scheduling
     - Monitors database for pending jobs
     - Executes backup jobs at scheduled times
   
   - **Backup Executor** (`backup_executor.py`): Core backup logic
     - Borg backup operations (create, prune, compact)
     - Database dumps (PostgreSQL, MySQL)
     - S3 synchronization
     - Pre/post command execution
   
   - **Supporting Services**:
     - `notification_service.py`: Email and webhook notifications
     - `database_dumper.py`: Database backup integration
     - `s3_sync.py`: S3/MinIO synchronization
     - `init_gpg.py`: GPG encryption for credentials
     - `init_db.py`: SQLite database initialization

3. **Data Storage**:
   - **SQLite Database** (`/config/jogoborg.db`): Job configs, logs, repositories
   - **Borg Repositories** (`/borgspace`): Actual backup data
   - **GPG Key** (`/config/jogoborg.gpg`): Encryption key for credentials
   - **Logs** (`/log`): Application and job logs

4. **External Dependencies**:
   - Borg Backup tool
   - Docker CLI (for Docker-based backups)
   - rclone (for S3 sync)
   - GPG (for encryption)
   - Python 3 with: cryptography, requests, croniter

### Current Testing Limitations

- **Docker-only development**: Must rebuild and redeploy container for each change
- **Slow iteration**: Docker build times slow down development
- **Complex setup**: Multiple services need coordination
- **Data isolation**: Hard to reset state between tests
- **Debugging difficulty**: Limited visibility into running processes

---

## Proposed Local Testing Environment

### Directory Structure

```
jogoborg/
├── local_test/                          # NEW: Local testing environment
│   ├── README.md                        # Setup and usage instructions
│   ├── setup.sh                         # Initialize local test environment
│   ├── teardown.sh                      # Clean up test environment
│   ├── run_local.sh                     # Start all services locally
│   ├── stop_local.sh                    # Stop all services
│   │
│   ├── config/                          # Local config directory (mirrors /config)
│   │   ├── jogoborg.db                  # SQLite database (created on first run)
│   │   └── jogoborg.gpg                 # GPG key (created on first run)
│   │
│   ├── borgspace/                       # Local borg repositories (mirrors /borgspace)
│   │   └── .gitkeep
│   │
│   ├── logs/                            # Local logs (mirrors /log)
│   │   └── .gitkeep
│   │
│   ├── sourcespace/                     # Local source data to backup (mirrors /sourcespace)
│   │   ├── sample_data/
│   │   │   ├── file1.txt
│   │   │   ├── file2.txt
│   │   │   └── nested/
│   │   │       └── file3.txt
│   │   └── .gitkeep
│   │
│   ├── env.local                        # Local environment variables
│   ├── env.local.example                # Template for env.local
│   │
│   └── docker-compose.local.yml         # Docker Compose for local testing
│       (optional: for testing with containers)
│
├── scripts/
│   ├── scheduler.py
│   ├── web_server.py
│   ├── backup_executor.py
│   └── ...
│
└── lib/
    └── ... (Flutter code)
```

### Key Features of Local Testing Setup

#### 1. **Environment Configuration** (`local_test/env.local`)

```bash
# Web Interface
JOGOBORG_WEB_PORT=8080
JOGOBORG_WEB_USERNAME=testuser
JOGOBORG_WEB_PASSWORD=testpass123
JOGOBORG_GPG_PASSPHRASE=test_encryption_key
JOGOBORG_URL=http://localhost:8080

# Paths (relative to local_test directory)
JOGOBORG_CONFIG_DIR=./config
JOGOBORG_BORGSPACE_DIR=./borgspace
JOGOBORG_LOG_DIR=./logs
JOGOBORG_SOURCESPACE_DIR=./sourcespace

# Optional: Database credentials for testing
JOGOBORG_TEST_DB_HOST=localhost
JOGOBORG_TEST_DB_USER=testuser
JOGOBORG_TEST_DB_PASSWORD=testpass
```

#### 2. **Local Startup Script** (`local_test/run_local.sh`)

```bash
#!/bin/bash
# Starts all services locally without Docker

# Load environment
source ./env.local

# Create directories if needed
mkdir -p config borgspace logs sourcespace

# Initialize database if needed
if [ ! -f "config/jogoborg.db" ]; then
    echo "Initializing database..."
    PYTHONPATH=/app python3 ../scripts/init_db.py
fi

# Initialize GPG if needed
if [ ! -f "config/jogoborg.gpg" ]; then
    echo "Initializing GPG..."
    PYTHONPATH=/app python3 ../scripts/init_gpg.py
fi

# Start services in background
echo "Starting web server..."
PYTHONPATH=/app python3 ../scripts/web_server.py &
WEB_PID=$!

echo "Starting scheduler..."
PYTHONPATH=/app python3 ../scripts/scheduler.py &
SCHEDULER_PID=$!

# Save PIDs for cleanup
echo "$WEB_PID" > .web_server.pid
echo "$SCHEDULER_PID" > .scheduler.pid

echo "Services started:"
echo "  Web Server PID: $WEB_PID"
echo "  Scheduler PID: $SCHEDULER_PID"
echo "  Web UI: http://localhost:8080"
echo ""
echo "To stop services, run: ./stop_local.sh"
```

#### 3. **Local Teardown Script** (`local_test/stop_local.sh`)

```bash
#!/bin/bash
# Stops all local services

if [ -f .web_server.pid ]; then
    kill $(cat .web_server.pid) 2>/dev/null || true
    rm .web_server.pid
fi

if [ -f .scheduler.pid ]; then
    kill $(cat .scheduler.pid) 2>/dev/null || true
    rm .scheduler.pid
fi

echo "Services stopped"
```

#### 4. **Setup Script** (`local_test/setup.sh`)

```bash
#!/bin/bash
# One-time setup for local testing environment

echo "Setting up local testing environment..."

# Create directories
mkdir -p config borgspace logs sourcespace

# Copy environment template if it doesn't exist
if [ ! -f env.local ]; then
    cp env.local.example env.local
    echo "Created env.local - please review and update as needed"
fi

# Create sample source data
mkdir -p sourcespace/sample_data/nested
echo "Sample file 1" > sourcespace/sample_data/file1.txt
echo "Sample file 2" > sourcespace/sample_data/file2.txt
echo "Nested sample file" > sourcespace/sample_data/nested/file3.txt

# Make scripts executable
chmod +x run_local.sh stop_local.sh

echo "Setup complete!"
echo "Next steps:"
echo "  1. Review and update local_test/env.local"
echo "  2. Run: ./run_local.sh"
echo "  3. Access web UI at http://localhost:8080"
```

---

## Development Workflow

### Quick Start for Local Development

```bash
# First time setup
cd local_test
./setup.sh

# Start services
./run_local.sh

# Access web UI
# Open http://localhost:8080 in browser

# Make code changes in ../scripts/ or ../lib/

# For Python changes: services auto-reload or restart manually
# For Flutter changes: rebuild web app
cd ..
flutter build web --release
cd local_test

# Stop services
./stop_local.sh
```

### Testing Scenarios

#### Scenario 1: Test Backup Job Creation and Execution
1. Start local services: `./run_local.sh`
2. Access web UI at `http://localhost:8080`
3. Login with credentials from `env.local`
4. Create a backup job pointing to `sourcespace/sample_data`
5. Manually trigger job or wait for scheduled time
6. Check logs in `logs/` directory
7. Verify backup in `borgspace/` directory

#### Scenario 2: Test Database Backup Integration
1. Start a test database (PostgreSQL/MySQL) locally
2. Update `env.local` with database credentials
3. Create backup job with database dump enabled
4. Execute job and verify database dump in backup

#### Scenario 3: Test Notification System
1. Configure SMTP or webhook in web UI
2. Create backup job with notifications enabled
3. Execute job and verify notification delivery

#### Scenario 4: Test S3 Synchronization
1. Configure S3/MinIO credentials in web UI
2. Create backup job with S3 sync enabled
3. Execute job and verify sync to S3

#### Scenario 5: Test Scheduler
1. Create multiple backup jobs with different schedules
2. Observe scheduler logs in `logs/scheduler.log`
3. Verify jobs execute at correct times

---

## Advanced Testing Features

### 1. **Unit Testing Framework**

Create `tests/` directory with unit tests:

```
tests/
├── test_backup_executor.py
├── test_scheduler.py
├── test_notification_service.py
├── test_database_dumper.py
└── conftest.py                  # Pytest fixtures
```

Run tests:
```bash
pytest tests/ -v
```

### 2. **Integration Testing**

Create `tests/integration/` for end-to-end tests:

```
tests/integration/
├── test_full_backup_workflow.py
├── test_job_scheduling.py
└── test_api_endpoints.py
```

### 3. **Mock Services**

For testing without external dependencies:

```python
# tests/mocks/mock_s3.py
class MockS3Syncer:
    def sync(self, *args, **kwargs):
        return {"status": "success", "files_synced": 0}

# tests/mocks/mock_notification.py
class MockNotificationService:
    def send_email(self, *args, **kwargs):
        return True
```

### 4. **Test Data Management**

```bash
local_test/
├── fixtures/
│   ├── sample_backup_job.json
│   ├── sample_database_config.json
│   └── sample_s3_config.json
└── reset_test_data.sh          # Reset to clean state
```

### 5. **Performance Testing**

```bash
local_test/
└── perf_test.sh                # Benchmark backup performance
```

---

## Advantages of This Approach

### For Development
- ✅ **Fast iteration**: No Docker rebuild needed for Python/Flutter changes
- ✅ **Easy debugging**: Direct access to logs and processes
- ✅ **Flexible testing**: Run individual services or combinations
- ✅ **State management**: Easy to reset or inspect database/files

### For Testing
- ✅ **Reproducible**: Consistent environment across developers
- ✅ **Isolated**: Local test data doesn't affect production
- ✅ **Scriptable**: Automate test scenarios
- ✅ **Observable**: Full visibility into all operations

### For CI/CD
- ✅ **Testable**: Can run tests in CI pipeline
- ✅ **Containerizable**: Still use Docker for final deployment
- ✅ **Documented**: Clear setup and teardown procedures

---

## Migration Path

### Phase 1: Basic Local Setup (Week 1)
- Create `local_test/` directory structure
- Implement `setup.sh`, `run_local.sh`, `stop_local.sh`
- Document environment configuration
- Test with simple backup jobs

### Phase 2: Enhanced Testing (Week 2)
- Add unit test framework
- Create mock services
- Add integration tests
- Document test scenarios

### Phase 3: CI/CD Integration (Week 3)
- Add GitHub Actions workflow
- Run tests on every commit
- Build Docker image on release
- Deploy to staging/production

### Phase 4: Advanced Features (Ongoing)
- Performance benchmarking
- Load testing
- Chaos engineering tests
- Security scanning

---

## Compatibility with Docker Deployment

This local testing approach **does not replace** Docker deployment:

- **Local testing**: For development and quick iteration
- **Docker deployment**: For production and consistent environments
- **Both coexist**: Use local for development, Docker for deployment

The same code runs in both environments with minimal changes (mainly path configuration).

---

## Next Steps

1. **Create the directory structure** in `local_test/`
2. **Implement the shell scripts** for setup and execution
3. **Create environment template** (`env.local.example`)
4. **Test the setup** with a simple backup job
5. **Document any issues** and refine the approach
6. **Add to CI/CD** pipeline for automated testing

