# Jogoborg Testing Approach - Executive Summary

## Problem Statement

Your Jogoborg project is currently Docker-only for testing, which creates:
- ❌ Slow iteration cycles (5-10 minutes per Docker rebuild)
- ❌ Complex setup and teardown
- ❌ Difficult debugging and state inspection
- ❌ Hard to test individual components
- ❌ Steep learning curve for new developers

## Solution Provided

A **local testing environment** that runs all Jogoborg services directly on your machine without Docker, enabling:
- ✅ **Instant feedback** - Changes take effect immediately
- ✅ **Fast iteration** - Develop and test in minutes, not hours
- ✅ **Easy debugging** - Direct access to logs, database, and processes
- ✅ **Flexible testing** - Run individual services or combinations
- ✅ **State management** - Easy to reset or inspect data

## What Was Created

### 📁 Directory: `local_test/`

Complete testing infrastructure with:

| File | Purpose |
|------|---------|
| `setup.sh` | Initialize environment (one-time) |
| `run_local.sh` | Start all services |
| `stop_local.sh` | Stop all services |
| `reset_test_data.sh` | Reset to clean state |
| `dev_helpers.sh` | Development helper functions |
| `Makefile` | Convenient make commands |
| `env.local.example` | Configuration template |
| `README.md` | Setup and usage guide |
| `TESTING_GUIDE.md` | 15+ detailed test scenarios |
| `QUICK_REFERENCE.md` | One-page quick reference |

### 📊 Directory Structure

```
local_test/
├── config/              # Database & GPG key
├── borgspace/           # Borg repositories
├── logs/                # Application logs
├── sourcespace/         # Source data for backup
├── env.local            # Configuration
├── setup.sh             # Initialize
├── run_local.sh         # Start services
├── stop_local.sh        # Stop services
├── Makefile             # Make commands
└── Documentation/       # Guides and references
```

## Quick Start

### 5-Minute Setup

```bash
cd local_test
./setup.sh
./run_local.sh
# Open http://localhost:8080
```

### What You Get

- ✅ Web server running on port 8080
- ✅ Scheduler running in background
- ✅ SQLite database initialized
- ✅ GPG encryption configured
- ✅ Sample test data ready
- ✅ All logs accessible

## Key Features

### 1. Service Management

```bash
make start              # Start services
make stop               # Stop services
make restart            # Restart services
make status             # Show status
```

### 2. Logging & Monitoring

```bash
make logs               # Follow all logs
make logs-web           # Follow web server logs
make logs-scheduler     # Follow scheduler logs
make status             # Show overall status
```

### 3. Database Access

```bash
make db-jobs            # List backup jobs
make db-logs            # List job execution logs
make db-shell           # Open SQLite shell
```

### 4. Testing

```bash
make api-health         # Check API health
make api-jobs           # List jobs via API
make test-file SIZE=100M # Add test file
```

### 5. Development Helpers

```bash
source dev_helpers.sh
status                  # Show status
db_list_jobs           # List jobs
tail_all_logs          # Follow logs
quick_restart          # Restart services
```

## Comparison: Local vs Docker

| Aspect | Local Testing | Docker |
|--------|---------------|--------|
| **Setup Time** | 2 minutes | 10+ minutes |
| **Iteration Speed** | Instant | 5-10 minutes |
| **Code Changes** | Immediate | Rebuild required |
| **Debugging** | Direct access | Docker exec |
| **State Reset** | One command | Rebuild image |
| **Log Access** | Direct files | Docker logs |
| **Database Access** | Direct SQLite | Docker exec |
| **Development** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Production** | N/A | ⭐⭐⭐⭐⭐ |

## Testing Scenarios Included

### Basic Testing (5 scenarios)
1. Web interface access
2. Create backup job
3. Manual job execution
4. View job logs
5. Repository browsing

### Advanced Testing (10 scenarios)
6. Multiple concurrent jobs
7. Pre/post commands
8. Exclude patterns
9. Compression settings
10. Retention policies
11. Large file handling
12. Error handling
13. Database consistency
14. Configuration persistence
15. Credential encryption

### Performance Testing (4 scenarios)
- Backup speed measurement
- Memory usage monitoring
- Concurrent job performance
- Repository size growth

### Integration Testing (4 scenarios)
- Full end-to-end workflow
- State reset verification
- Configuration reload
- Log rotation

**Total: 23+ documented test scenarios**

## Development Workflow

### Making Changes

```bash
# Python changes
nano ../scripts/scheduler.py
make stop
make start

# Flutter changes
cd ..
flutter build web --release
cd local_test
# Refresh browser
```

### Testing Changes

```bash
make start
# Create test job via web UI
make logs-scheduler
make db-logs
make stop
```

### Debugging

```bash
# View logs
make logs

# Check database
make db-shell

# Monitor status
make status

# Check API
make api-health
```

## Configuration

Edit `local_test/env.local`:

```bash
JOGOBORG_WEB_PORT=8080
JOGOBORG_WEB_USERNAME=testuser
JOGOBORG_WEB_PASSWORD=testpass123
JOGOBORG_GPG_PASSPHRASE=test_encryption_key
JOGOBORG_URL=http://localhost:8080
```

## Architecture Overview

### Services Running Locally

```
┌─────────────────────────────────────────┐
│         Jogoborg Local Testing          │
├─────────────────────────────────────────┤
│                                         │
│  Web Server (port 8080)                │
│  ├─ HTTP API endpoints                 │
│  ├─ Static file serving                │
│  └─ Authentication                     │
│                                         │
│  Scheduler (background)                │
│  ├─ Cron-based scheduling              │
│  ├─ Job execution                      │
│  └─ Notification handling              │
│                                         │
│  Data Storage                          │
│  ├─ SQLite database (config/)          │
│  ├─ Borg repositories (borgspace/)     │
│  ├─ GPG encryption key (config/)       │
│  └─ Application logs (logs/)           │
│                                         │
└─────────────────────────────────────────┘
```

## Performance Expectations

Typical performance on modern hardware:

| Operation | Time |
|-----------|------|
| Setup | 2-5 minutes |
| Service startup | < 5 seconds |
| Small backup (10MB) | < 5 seconds |
| Medium backup (100MB) | < 30 seconds |
| Large backup (1GB) | < 5 minutes |
| Memory usage | < 500MB |

## Integration with Docker

This local testing environment **complements** Docker deployment:

```
Development Cycle:
┌─────────────────────────────────────────┐
│ 1. Develop locally (local_test/)        │
│ 2. Test locally (make test-*)           │
│ 3. Build Docker (docker build)          │
│ 4. Deploy (docker-compose up)           │
└─────────────────────────────────────────┘
```

Both use the same codebase with minimal configuration differences.

## Files & Documentation

### Main Documentation
- **`LOCAL_TESTING_SETUP.md`** - Complete setup guide (this directory)
- **`TESTING_APPROACH.md`** - Overall testing strategy
- **`local_test/README.md`** - Setup and usage guide
- **`local_test/TESTING_GUIDE.md`** - 23+ test scenarios
- **`local_test/QUICK_REFERENCE.md`** - One-page reference

### Scripts
- **`local_test/setup.sh`** - Initialize environment
- **`local_test/run_local.sh`** - Start services
- **`local_test/stop_local.sh`** - Stop services
- **`local_test/reset_test_data.sh`** - Reset to clean state
- **`local_test/dev_helpers.sh`** - Helper functions

### Configuration
- **`local_test/env.local.example`** - Configuration template
- **`local_test/Makefile`** - Make commands

## Getting Started

### Step 1: Navigate to local_test
```bash
cd local_test
```

### Step 2: Run setup (one-time)
```bash
./setup.sh
```

### Step 3: Start services
```bash
./run_local.sh
```

### Step 4: Access web UI
```
http://localhost:8080
```

### Step 5: Create and test backup jobs
- Login with credentials from `env.local`
- Create new backup job
- Click "Run Now"
- Check logs: `make logs`

## Benefits Summary

### For Developers
- ✅ Fast iteration (instant feedback)
- ✅ Easy debugging (direct access)
- ✅ Flexible testing (run individual services)
- ✅ State management (easy reset)

### For Testing
- ✅ Reproducible (consistent environment)
- ✅ Isolated (local data only)
- ✅ Scriptable (automate scenarios)
- ✅ Observable (full visibility)

### For CI/CD
- ✅ Testable (run in pipeline)
- ✅ Containerizable (still use Docker)
- ✅ Documented (clear procedures)

## Next Steps

### Immediate (Today)
1. Review `LOCAL_TESTING_SETUP.md`
2. Run `cd local_test && ./setup.sh`
3. Run `./run_local.sh`
4. Access http://localhost:8080
5. Create and test a backup job

### This Week
1. Run all basic test scenarios (Test 1-5)
2. Run advanced test scenarios (Test 6-15)
3. Test with your actual backup sources
4. Document any issues

### This Month
1. Integrate with CI/CD
2. Add automated testing
3. Add performance benchmarking
4. Document best practices

## Support

### Quick Help
```bash
make help              # Show all commands
make dev-help          # Show helper functions
make docs              # Show README
make docs-testing      # Show testing guide
```

### Troubleshooting
- Check `local_test/README.md` - Troubleshooting section
- Check `local_test/TESTING_GUIDE.md` - Troubleshooting section
- Run `make check-deps` - Check dependencies
- Run `make status` - Show current status

## Conclusion

You now have a **complete local testing environment** that:

1. **Eliminates Docker overhead** - Instant feedback on changes
2. **Accelerates development** - Develop and test in minutes
3. **Enables comprehensive testing** - 23+ test scenarios
4. **Maintains compatibility** - Same code runs locally and in Docker
5. **Improves debugging** - Direct access to all components
6. **Scales with your project** - Easy to add more scenarios

This approach transforms your development workflow from slow Docker-based iteration to fast, efficient local development.

---

## Quick Reference

```bash
# Setup (one-time)
cd local_test && ./setup.sh

# Start services
./run_local.sh

# Access web UI
# http://localhost:8080

# View logs
make logs

# Check status
make status

# Stop services
./stop_local.sh

# Reset everything
./reset_test_data.sh
```

**Ready to get started? Run `cd local_test && ./setup.sh` now!** 🚀

