# Jogoborg Local Testing - Quick Reference

## One-Liner Quick Start

```bash
cd local_test && ./setup.sh && ./run_local.sh
# Then open http://localhost:8080
```

## Essential Commands

### Service Management
```bash
make setup          # Initialize environment (one-time)
make start          # Start services
make stop           # Stop services
make restart        # Restart services
make status         # Show status
make reset          # Reset to clean state
```

### Logs
```bash
make logs           # Follow all logs
make logs-web       # Follow web server logs
make logs-scheduler # Follow scheduler logs
make logs-clear     # Clear all logs
```

### Database
```bash
make db-jobs        # List backup jobs
make db-logs        # List job execution logs
make db-count       # Show statistics
make db-shell       # Open SQLite shell
```

### Repositories & Data
```bash
make repos          # List borg repositories
make repos-size     # Show repository sizes
make source-data    # List source data files
make source-size    # Show source data size
make test-file      # Add test file (SIZE=100M)
```

### API
```bash
make api-health     # Check API health
make api-jobs       # List jobs via API
make api-repos      # List repositories via API
```

## Directory Structure

```
local_test/
├── config/          # Database and GPG key
├── borgspace/       # Borg repositories
├── logs/            # Application logs
├── sourcespace/     # Source data to backup
├── env.local        # Configuration (edit this!)
├── setup.sh         # Initialize
├── run_local.sh     # Start services
├── stop_local.sh    # Stop services
└── Makefile         # Make commands
```

## Configuration

Edit `env.local`:
```bash
JOGOBORG_WEB_PORT=8080              # Web server port
JOGOBORG_WEB_USERNAME=testuser      # Login username
JOGOBORG_WEB_PASSWORD=testpass123   # Login password
JOGOBORG_GPG_PASSPHRASE=test_key    # Encryption key
JOGOBORG_URL=http://localhost:8080  # Service URL
```

## Web UI Access

- **URL**: http://localhost:8080
- **Username**: From `env.local` (default: testuser)
- **Password**: From `env.local` (default: testpass123)

## Common Workflows

### Create and Run a Backup Job

```bash
# 1. Start services
make start

# 2. Open http://localhost:8080 and login

# 3. Create new job:
#    - Name: test-backup
#    - Schedule: 0 * * * *
#    - Source: sourcespace/sample_data
#    - Click "Create"

# 4. Click "Run Now" to execute

# 5. Watch logs
make logs-scheduler

# 6. Check results
make db-logs
make repos
```

### Test Multiple Jobs

```bash
# Create 3 jobs with different schedules
# Job 1: */5 * * * * (every 5 min)
# Job 2: */10 * * * * (every 10 min)
# Job 3: */15 * * * * (every 15 min)

# Watch scheduler
make logs-scheduler

# Check execution
make db-logs
```

### Add Large Test File

```bash
make test-file SIZE=500M
# Then create backup job pointing to sourcespace/sample_data
```

### Reset Everything

```bash
make stop
make reset
make setup
make start
```

## Troubleshooting

### Services won't start
```bash
make check-deps      # Check dependencies
make install-deps    # Install missing packages
lsof -i :8080        # Check port in use
```

### Database locked
```bash
make stop
sleep 2
make start
```

### API not responding
```bash
make api-health      # Check health
make logs-web        # Check web logs
make restart         # Restart services
```

### View detailed logs
```bash
tail -f logs/web_server.log
tail -f logs/scheduler.log
sqlite3 config/jogoborg.db "SELECT * FROM job_logs LIMIT 5;"
```

## Development Tips

### Make Code Changes

**Python changes** (scripts/):
```bash
make stop
# Edit scripts/
make start
```

**Flutter changes** (lib/):
```bash
cd ..
flutter build web --release
cd local_test
# Refresh browser
```

### Debug Database

```bash
# Open SQLite shell
make db-shell

# Common queries
SELECT * FROM backup_jobs;
SELECT * FROM job_logs ORDER BY started_at DESC LIMIT 10;
SELECT COUNT(*) FROM backup_jobs;
```

### Monitor in Real-Time

```bash
# Terminal 1: Follow logs
make logs

# Terminal 2: Check status
watch -n 1 'make status'

# Terminal 3: Monitor database
watch -n 1 'make db-count'
```

## Performance Checks

```bash
# Backup speed
grep "duration" logs/scheduler.log

# Memory usage
grep "max_memory" logs/scheduler.log

# Repository size
make repos-size

# Source data size
make source-size
```

## Environment Variables

```bash
# Web Interface
JOGOBORG_WEB_PORT              # Port (default: 8080)
JOGOBORG_WEB_USERNAME          # Username (default: testuser)
JOGOBORG_WEB_PASSWORD          # Password (default: testpass123)
JOGOBORG_GPG_PASSPHRASE        # Encryption key
JOGOBORG_URL                   # Service URL

# Directories (relative to local_test/)
JOGOBORG_CONFIG_DIR            # Config directory
JOGOBORG_BORGSPACE_DIR         # Borg repos directory
JOGOBORG_LOG_DIR               # Logs directory
JOGOBORG_SOURCESPACE_DIR       # Source data directory

# Optional
JOGOBORG_LOG_LEVEL             # DEBUG, INFO, WARNING, ERROR
JOGOBORG_DEV_AUTO_RELOAD       # Auto-reload on changes
JOGOBORG_DEV_VERBOSE           # Verbose output
```

## File Locations

```
config/jogoborg.db             # SQLite database
config/jogoborg.gpg            # GPG encryption key
borgspace/*/                   # Borg repositories
logs/web_server.log            # Web server logs
logs/scheduler.log             # Scheduler logs
sourcespace/sample_data/       # Sample source data
```

## Useful Commands

```bash
# List all make targets
make help

# Show environment info
make info

# Check dependencies
make check-deps

# Install Python dependencies
make install-deps

# Open documentation
make docs

# Open testing guide
make docs-testing

# Show development helpers
make dev-help
```

## Docker Integration

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run

# Stop Docker container
make docker-stop

# View Docker logs
make docker-logs
```

## Testing Scenarios

### Scenario 1: Basic Backup
```bash
make start
# Create job → Run Now → Check logs
make logs-scheduler
```

### Scenario 2: Multiple Jobs
```bash
make start
# Create 3 jobs with different schedules
# Wait for execution
make db-logs
```

### Scenario 3: Large Files
```bash
make test-file SIZE=500M
make start
# Create job → Run Now
make repos-size
```

### Scenario 4: Error Handling
```bash
make start
# Create job with invalid source
# Run Now → Check error logs
grep -i error logs/scheduler.log
```

## Performance Baseline

Expected performance (varies by system):
- Small backup (10MB): < 5 seconds
- Medium backup (100MB): < 30 seconds
- Large backup (1GB): < 5 minutes
- Memory usage: < 500MB for typical jobs

## Next Steps

1. `make setup` - Initialize
2. `make start` - Start services
3. Open http://localhost:8080
4. Create backup job
5. Click "Run Now"
6. `make logs` - Watch execution
7. `make db-logs` - Check results
8. `make stop` - Stop services

## Help & Documentation

```bash
make help              # Show all make commands
make dev-help          # Show development helpers
make docs              # Show README
make docs-testing      # Show testing guide
cat QUICK_REFERENCE.md # This file
```

## Support

- **Logs**: `make logs`
- **Status**: `make status`
- **Database**: `make db-shell`
- **API**: `make api-health`
- **Dependencies**: `make check-deps`

---

**Last Updated**: 2025-12-07
**Version**: 1.0
