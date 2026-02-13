# Jogoborg Local Testing Setup - Complete Guide

## Overview

I've analyzed your Jogoborg project and created a comprehensive local testing environment that makes development significantly faster and easier than Docker-based testing.

### What Was Created

A complete `local_test/` directory with:
- ✅ Setup and teardown scripts
- ✅ Service management (start/stop)
- ✅ Environment configuration
- ✅ Development helper functions
- ✅ Makefile for common tasks
- ✅ Comprehensive documentation
- ✅ Testing guides and scenarios

---

## Quick Start (5 minutes)

```bash
# Create and activate Python virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

cd local_test

# One-time setup
./setup.sh

# Start services
./run_local.sh

# Open browser
# http://localhost:8080
```

That's it! You now have:
- ✅ Web server running on port 8080
- ✅ Scheduler running in background
- ✅ SQLite database initialized
- ✅ GPG encryption configured
- ✅ Sample test data ready

---

## Project Analysis

### Architecture

Your project consists of:

1. **Frontend**: Flutter web application
   - Modern UI for job configuration
   - Real-time monitoring
   - Authentication-based access

2. **Backend Services** (Python):
   - `web_server.py`: HTTP API + static file serving
   - `scheduler.py`: Cron-based job scheduling
   - `backup_executor.py`: Core backup logic
   - Supporting services: notifications, database dumps, S3 sync

3. **Data Storage**:
   - SQLite database: Job configs, logs, repositories
   - Borg repositories: Actual backup data
   - GPG key: Credential encryption
   - Logs: Application and job logs

4. **External Dependencies**:
   - Borg Backup tool
   - Docker CLI (optional)
   - AWS CLI (optional)
   - GPG, Python 3, SQLite

### Current Testing Limitations

- **Docker-only**: Must rebuild container for each change
- **Slow iteration**: Docker build times (5-10 minutes)
- **Complex setup**: Multiple services need coordination
- **Hard to debug**: Limited visibility into processes
- **State management**: Difficult to reset or inspect

---

## Solution: Local Testing Environment

### Key Advantages

| Aspect | Local Testing | Docker |
|--------|---------------|--------|
| **Setup Time** | 2 minutes | 10+ minutes |
| **Iteration Speed** | Instant | 5-10 minutes |
| **Debugging** | Direct access | Docker exec |
| **State Reset** | One command | Rebuild image |
| **Development** | Fast | Slow |
| **Deployment** | N/A | Production-ready |

### Directory Structure

```
local_test/
├── config/                  # Database and GPG key
│   ├── jogoborg.db         # SQLite database
│   └── jogoborg.gpg        # GPG encryption key
├── borgspace/              # Borg backup repositories
├── logs/                   # Application logs
│   ├── web_server.log
│   └── scheduler.log
├── sourcespace/            # Source data to backup
│   └── sample_data/        # Sample files
├── env.local               # Configuration (edit this!)
├── env.local.example       # Configuration template
├── setup.sh                # Initialize environment
├── run_local.sh            # Start services
├── stop_local.sh           # Stop services
├── reset_test_data.sh      # Reset to clean state
├── dev_helpers.sh          # Development helper functions
├── Makefile                # Make commands
├── README.md               # Setup and usage guide
├── TESTING_GUIDE.md        # Detailed testing procedures
└── QUICK_REFERENCE.md      # Quick command reference
```

---

## Usage Guide

### 1. Initial Setup (One-time)

```bash
cd local_test
./setup.sh
```

This:
- Creates directories
- Initializes SQLite database
- Generates GPG encryption key
- Creates sample test data
- Copies environment configuration

### 2. Start Services

```bash
./run_local.sh
```

This:
- Loads environment configuration
- Starts web server (port 8080)
- Starts scheduler (background)
- Creates log files

### 3. Access Web UI

Open browser: **http://localhost:8080**

Login with credentials from `env.local`:
- Username: `testuser` (default)
- Password: `testpass123` (default)

### 4. Create Backup Job

1. Click "New Job"
2. Configure:
   - Name: `test-backup`
   - Schedule: `0 * * * *` (every hour)
   - Source: `sourcespace/sample_data`
   - Compression: `lz4`
3. Click "Create"

### 5. Execute Job

1. Click "Run Now" button
2. Watch logs: `tail -f logs/scheduler.log`
3. Check results: `ls -la borgspace/`

### 6. Stop Services

```bash
./stop_local.sh
```

---

## Make Commands

For convenience, use Make commands:

```bash
# Service management
make setup              # Initialize environment
make start              # Start services
make stop               # Stop services
make restart            # Restart services
make status             # Show status

# Logs
make logs               # Follow all logs
make logs-web           # Follow web server logs
make logs-scheduler     # Follow scheduler logs

# Database
make db-jobs            # List backup jobs
make db-logs            # List job execution logs
make db-count           # Show statistics

# Repositories
make repos              # List borg repositories
make repos-size         # Show repository sizes

# Source data
make source-data        # List source data files
make test-file SIZE=100M # Add test file

# API
make api-health         # Check API health
make api-jobs           # List jobs via API

# Development
make dev-help           # Show helper functions
make check-deps         # Check dependencies
make install-deps       # Install Python packages
```

---

## Development Workflow

### Making Python Changes

```bash
# 1. Edit scripts/
nano ../scripts/scheduler.py

# 2. Stop services
make stop

# 3. Start services (changes take effect)
make start

# 4. Test changes
make logs-scheduler
```

### Making Flutter Changes

```bash
# 1. Edit lib/
nano ../lib/screens/dashboard_screen.dart

# 2. Rebuild web app
cd ..
flutter build web --release
cd local_test

# 3. Refresh browser (Ctrl+R)
```

### Testing Workflow

```bash
# 1. Start services
make start

# 2. Create test job via web UI

# 3. Execute job
# Click "Run Now"

# 4. Monitor execution
make logs-scheduler

# 5. Check results
make db-logs
make repos

# 6. Stop services
make stop
```

---

## Testing Scenarios

### Scenario 1: Basic Backup Job
- Create job pointing to `sourcespace/sample_data`
- Execute and verify backup created
- Check logs and database

### Scenario 2: Multiple Concurrent Jobs
- Create 3 jobs with different schedules
- Observe scheduler managing multiple jobs
- Verify all execute correctly

### Scenario 3: Large File Handling
- Add 500MB test file: `make test-file SIZE=500M`
- Create backup job
- Monitor performance and memory usage

### Scenario 4: Error Handling
- Create job with invalid source directory
- Execute and verify error handling
- Check error logs

### Scenario 5: Retention Policies
- Create job with keep_daily=3, keep_monthly=2
- Execute multiple times
- Verify old backups are pruned

See `local_test/TESTING_GUIDE.md` for 15+ detailed testing scenarios.

---

## Configuration

Edit `local_test/env.local`:

```bash
# Web Interface
JOGOBORG_WEB_PORT=8080
JOGOBORG_WEB_USERNAME=testuser
JOGOBORG_WEB_PASSWORD=testpass123
JOGOBORG_GPG_PASSPHRASE=test_encryption_key_change_me
JOGOBORG_URL=http://localhost:8080

# Directories (relative to local_test/)
JOGOBORG_CONFIG_DIR=./config
JOGOBORG_BORGSPACE_DIR=./borgspace
JOGOBORG_LOG_DIR=./logs
JOGOBORG_SOURCESPACE_DIR=./sourcespace

# Optional: Database credentials for testing
# JOGOBORG_TEST_POSTGRES_HOST=localhost
# JOGOBORG_TEST_POSTGRES_USER=testuser
# JOGOBORG_TEST_POSTGRES_PASSWORD=testpass

# Optional: S3/MinIO configuration
# JOGOBORG_TEST_S3_ENDPOINT=http://localhost:9000
# JOGOBORG_TEST_S3_ACCESS_KEY=minioadmin
# JOGOBORG_TEST_S3_SECRET_KEY=minioadmin
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check Python
python3 --version

# Check dependencies
make check-deps

# Install missing packages
make install-deps

# Check port in use
lsof -i :8080
```

### Database Locked

```bash
make stop
sleep 2
make start
```

### API Not Responding

```bash
make api-health
make logs-web
make restart
```

### View Detailed Logs

```bash
# Web server logs
tail -f logs/web_server.log

# Scheduler logs
tail -f logs/scheduler.log

# Database queries
sqlite3 config/jogoborg.db "SELECT * FROM job_logs LIMIT 5;"
```

---

## Development Helper Functions

Source the helper functions for quick access:

```bash
source dev_helpers.sh

# Then use functions like:
status                  # Show overall status
db_list_jobs           # List backup jobs
db_list_job_logs       # List job execution logs
tail_all_logs          # Follow all logs
list_repositories      # List borg repositories
api_health             # Check API health
quick_restart          # Restart services
```

---

## Integration with Docker

This local testing environment **complements** Docker deployment:

- **Local Testing**: Fast development iteration
- **Docker Deployment**: Production-ready deployment

Both use the same codebase with minimal configuration differences.

### Deployment Workflow

1. **Develop locally**: Use `local_test/` for fast iteration
2. **Test locally**: Run all test scenarios
3. **Build Docker**: `docker build -t jogoborg:latest .`
4. **Deploy**: Use `docker-compose.yml` for production

---

## Files Created

### Scripts
- `setup.sh` - Initialize environment
- `run_local.sh` - Start services
- `stop_local.sh` - Stop services
- `reset_test_data.sh` - Reset to clean state
- `dev_helpers.sh` - Development helper functions

### Configuration
- `env.local.example` - Configuration template
- `env.local` - Local configuration (created by setup.sh)

### Documentation
- `README.md` - Setup and usage guide
- `TESTING_GUIDE.md` - Detailed testing procedures (15+ scenarios)
- `QUICK_REFERENCE.md` - Quick command reference
- `Makefile` - Make commands for common tasks

### Directories (created by setup.sh)
- `config/` - Database and GPG key
- `borgspace/` - Borg repositories
- `logs/` - Application logs
- `sourcespace/` - Source data for backup

---

## Next Steps

### Immediate (Today)
1. ✅ Review this document
2. ✅ Run `cd local_test && ./setup.sh`
3. ✅ Run `./run_local.sh`
4. ✅ Access http://localhost:8080
5. ✅ Create and test a backup job

### Short Term (This Week)
1. Run all basic testing scenarios (Test 1-5 in TESTING_GUIDE.md)
2. Run advanced testing scenarios (Test 6-15)
3. Test with your actual backup sources
4. Document any issues or improvements

### Medium Term (This Month)
1. Integrate with CI/CD pipeline
2. Add automated testing
3. Add performance benchmarking
4. Document best practices

### Long Term (Ongoing)
1. Enhance testing framework
2. Add more test scenarios
3. Improve documentation
4. Optimize performance

---

## Key Benefits

### For Development
- ✅ **Fast iteration**: No Docker rebuild needed
- ✅ **Easy debugging**: Direct access to logs and processes
- ✅ **Flexible testing**: Run individual services or combinations
- ✅ **State management**: Easy to reset or inspect database

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

## Performance Expectations

Typical performance on modern hardware:
- **Setup time**: 2-5 minutes
- **Service startup**: < 5 seconds
- **Small backup (10MB)**: < 5 seconds
- **Medium backup (100MB)**: < 30 seconds
- **Large backup (1GB)**: < 5 minutes
- **Memory usage**: < 500MB for typical jobs

---

## Support & Documentation

### Quick Reference
- `local_test/QUICK_REFERENCE.md` - One-page quick reference

### Detailed Guides
- `local_test/README.md` - Setup and usage
- `local_test/TESTING_GUIDE.md` - Testing procedures
- `TESTING_APPROACH.md` - Overall testing strategy

### Help Commands
```bash
make help              # Show all make commands
make dev-help          # Show helper functions
make docs              # Show README
make docs-testing      # Show testing guide
```

---

## Summary

You now have a complete local testing environment that:

1. **Eliminates Docker rebuild overhead** - Instant feedback on changes
2. **Provides fast iteration** - Develop and test in minutes, not hours
3. **Enables comprehensive testing** - 15+ test scenarios documented
4. **Maintains consistency** - Same code runs locally and in Docker
5. **Improves debugging** - Direct access to logs and database
6. **Scales with your project** - Easily add more test scenarios

This approach significantly accelerates development while maintaining compatibility with Docker deployment.

---

## Getting Started Now

```bash
# Navigate to local_test directory
cd local_test

# Run setup (one-time)
./setup.sh

# Start services
./run_local.sh

# Open browser
# http://localhost:8080

# Create and test backup jobs!
```

Enjoy faster development! 🚀

