# Jogoborg Local Testing Guide

This guide provides detailed testing procedures and scenarios for developing and validating Jogoborg functionality.

## Table of Contents

1. [Setup](#setup)
2. [Basic Testing](#basic-testing)
3. [Advanced Testing](#advanced-testing)
4. [Troubleshooting](#troubleshooting)
5. [Performance Testing](#performance-testing)
6. [Integration Testing](#integration-testing)

---

## Setup

### Prerequisites

```bash
# Check Python version
python3 --version  # Should be 3.7+

# Check required tools
which sqlite3
which borg
which gpg
```

### Flutter Web Build Setup (Optional but Recommended)

For testing with the actual Flutter UI, you'll need to build the web app. This is highly recommended for proper integration testing.

#### Install Flutter

```bash
# Install Flutter SDK (if not already installed)
# Official docs: https://docs.flutter.dev/get-started/install

# For Linux:
cd ~/
git clone https://github.com/flutter/flutter.git -b stable
export PATH="$PATH:$HOME/flutter/bin"

# Verify installation
flutter --version
```

#### Build Flutter Web

```bash
# From project root (not local_test)
cd /path/to/jogoborg

# Get dependencies
flutter pub get

# Build for web (this creates build/web/)
# Use debug build for faster iteration during development
flutter build web

# Verify build output
ls -la build/web/index.html
```

**Build Time**: Debug build takes 1-2 minutes. First build may take longer as dependencies are compiled.

**Release vs Debug Builds**:
- **Debug build** (default, recommended for local testing):
  - Faster compilation (~1-2 minutes)
  - Includes sourcemaps for debugging
  - Better for UI development and iteration
- **Release build** (use when validating for production):
  ```bash
  flutter build web --release
  ```
  - Slower compilation (~5-10 minutes)
  - Optimized performance and smaller bundle
  - Use before deployment to test production behavior

#### Using the Built Web App

The local test setup will automatically detect and serve the Flutter web build if it exists:

```bash
cd local_test
./run_local.sh
# The web interface will be at http://localhost:8080 with the real Flutter UI
```

If no Flutter build is found, the server falls back to a development API testing interface at `index-dev.html`.

### Borg Repo

For testing, you'll need a Borg repository in the local_test/borgspace directory.
Make sure you have "borg" installed on your system. Then, initialize the repo:

```bash
cd local_test
borg init --encryption=repokey borgspace/test
```

You'll need to enter a passphrase, which you should store in a safe place.
Once the repo has been created, make sure you also store the key in a safe place:

```bash
borg key export borgspace/test test.borgkey
```

This will store the key in binary format in a file named `test.borgkey'. The standard
.gitignore is set up to ignore a Borg repo named "test" and that key file.


### Initial Setup

```bash
cd local_test

# One-time setup
./setup.sh

# Verify setup
make info
```

### Start Services

```bash
# Start all services
make start

# Verify services are running
make status
```

---

## Basic Testing

### Test 1: Web Interface Access

**Objective**: Verify web UI is accessible and authentication works

**Steps**:
1. Start services: `make start`
2. Open browser: http://localhost:8080
3. Login with credentials from `env.local`
4. Verify dashboard loads

**Expected Result**: Dashboard displays with no errors

**Verification**:
```bash
make api-health
```

### Test 2: Create Backup Job

**Objective**: Create a backup job via web UI

**Steps**:
1. Access web UI at http://localhost:8080
2. Click "New Job"
3. Fill in form:
   - **Name**: `test-backup-1`
   - **Schedule**: `0 * * * *` (every hour)
   - **Source**: Select `sourcespace/sample_data`
   - **Compression**: `lz4`
4. Click "Create"

**Expected Result**: Job appears in job list

**Verification**:
```bash
make db-jobs
```

### Test 3: Manual Job Execution

**Objective**: Manually trigger a backup job

**Steps**:
1. Create a backup job (see Test 2)
2. Click "Run Now" button
3. Wait for execution to complete
4. Check logs

**Expected Result**: Job completes successfully

**Verification**:
```bash
# Check logs
make logs-scheduler

# Check database
make db-logs

# Check repository created
make repos
```

### Test 4: View Job Logs

**Objective**: Verify job execution logs are recorded

**Steps**:
1. Execute a backup job (see Test 3)
2. Click on job name to view details
3. Check "Execution Logs" tab

**Expected Result**: Logs show job execution details

**Verification**:
```bash
# View logs in database
sqlite3 config/jogoborg.db "SELECT * FROM job_logs LIMIT 1;"

# View log files
cat logs/scheduler.log | tail -20
```

### Test 5: Repository Browsing

**Objective**: Browse backup repository contents

**Steps**:
1. Create and execute a backup job
2. Click on repository name
3. Browse archive contents

**Expected Result**: Can view files in backup

**Verification**:
```bash
# List repositories
make repos

# Check repository size
make repos-size

# List repository contents
borg list borgspace/test-backup-1
```

---

## Advanced Testing

### Test 6: Multiple Concurrent Jobs

**Objective**: Test scheduler handling multiple jobs

**Steps**:
1. Create 3 backup jobs with different schedules:
   - Job 1: `*/5 * * * *` (every 5 minutes)
   - Job 2: `*/10 * * * *` (every 10 minutes)
   - Job 3: `*/15 * * * *` (every 15 minutes)
2. Wait for scheduler to execute jobs
3. Monitor logs

**Expected Result**: Jobs execute at correct times without conflicts

**Verification**:
```bash
# Watch scheduler logs
make logs-scheduler

# Check job execution history
make db-logs

# Verify all repositories created
make repos
```

### Test 7: Job with Pre/Post Commands

**Objective**: Test pre and post command execution

**Steps**:
1. Create backup job with:
   - **Pre-command**: `echo "Starting backup" > /tmp/pre_command.txt`
   - **Post-command**: `echo "Backup complete" > /tmp/post_command.txt`
2. Execute job
3. Check if files were created

**Expected Result**: Pre and post commands execute successfully

**Verification**:
```bash
# Check if files exist
ls -la /tmp/pre_command.txt /tmp/post_command.txt

# Check logs for command execution
grep -i "pre-command\|post-command" logs/scheduler.log
```

### Test 8: Exclude Patterns

**Objective**: Test file exclusion patterns

**Steps**:
1. Add test files to source data:
   ```bash
   make test-file SIZE=1M
   touch sourcespace/sample_data/.exclude_me
   touch sourcespace/sample_data/temp.tmp
   ```
2. Create backup job with exclude patterns:
   - `.*` (hidden files)
   - `*.tmp` (temp files)
3. Execute job
4. Browse backup contents

**Expected Result**: Excluded files not in backup

**Verification**:
```bash
# List backup contents
borg list borgspace/test-backup-1 --short

# Verify excluded files not present
borg list borgspace/test-backup-1 | grep -E "\.exclude_me|\.tmp"
```

### Test 9: Compression Settings

**Objective**: Test different compression algorithms

**Steps**:
1. Create 3 backup jobs with different compression:
   - Job 1: `none`
   - Job 2: `lz4`
   - Job 3: `zstd`
2. Execute each job
3. Compare repository sizes

**Expected Result**: Different compression levels produce different sizes

**Verification**:
```bash
# Compare repository sizes
make repos-size

# Check compression in logs
grep -i "compression" logs/scheduler.log
```

### Test 10: Retention Policies

**Objective**: Test backup retention (keep_daily, keep_monthly, keep_yearly)

**Steps**:
1. Create backup job with:
   - **Keep Daily**: 3
   - **Keep Monthly**: 2
   - **Keep Yearly**: 1
2. Execute job multiple times
3. Check pruning behavior

**Expected Result**: Old backups are pruned according to policy

**Verification**:
```bash
# List archives in repository
borg list borgspace/test-backup-1

# Check prune logs
grep -i "prune" logs/scheduler.log
```

### Test 11: Large File Handling

**Objective**: Test backup of large files

**Steps**:
1. Add large test file:
   ```bash
   make test-file SIZE=500M
   ```
2. Create backup job
3. Execute job
4. Monitor memory usage

**Expected Result**: Large file backed up successfully

**Verification**:
```bash
# Check backup size
make repos-size

# Check memory usage in logs
grep -i "memory" logs/scheduler.log

# Verify file in backup
borg list borgspace/test-backup-1 | grep "large_file"
```

### Test 12: Error Handling

**Objective**: Test error handling and recovery

**Steps**:
1. Create backup job with invalid source directory
2. Execute job
3. Check error handling

**Expected Result**: Error is logged and handled gracefully

**Verification**:
```bash
# Check error logs
grep -i "error" logs/scheduler.log

# Check database error status
sqlite3 config/jogoborg.db "SELECT status, error_message FROM job_logs WHERE status='failed';"
```

### Test 13: Database State Consistency

**Objective**: Verify database state remains consistent

**Steps**:
1. Create multiple jobs
2. Execute jobs
3. Query database
4. Verify data integrity

**Expected Result**: Database state is consistent

**Verification**:
```bash
# Check database integrity
sqlite3 config/jogoborg.db "PRAGMA integrity_check;"

# Verify foreign key constraints
sqlite3 config/jogoborg.db "SELECT COUNT(*) FROM job_logs WHERE job_id NOT IN (SELECT id FROM backup_jobs);"
```

### Test 14: Configuration Persistence

**Objective**: Verify job configuration persists across restarts

**Steps**:
1. Create backup job
2. Stop services: `make stop`
3. Start services: `make start`
4. Verify job still exists

**Expected Result**: Job configuration persists

**Verification**:
```bash
# List jobs before restart
make db-jobs

# Restart
make restart

# List jobs after restart
make db-jobs
```

### Test 15: Credential Encryption

**Objective**: Verify credentials are encrypted in database

**Steps**:
1. Create backup job with repository passphrase
2. Query database directly
3. Verify passphrase is encrypted

**Expected Result**: Passphrase is encrypted, not plaintext

**Verification**:
```bash
# Query database
sqlite3 config/jogoborg.db "SELECT repository_passphrase FROM backup_jobs LIMIT 1;"

# Should show encrypted data, not plaintext
```

---

## Troubleshooting

### Services Won't Start

**Symptoms**: `./run_local.sh` fails or services don't start

**Diagnosis**:
```bash
# Check Python
python3 --version

# Check dependencies
make check-deps

# Check port availability
lsof -i :8080
```

**Solutions**:
```bash
# Install dependencies
make install-deps

# Change port in env.local
JOGOBORG_WEB_PORT=8081

# Kill process using port
lsof -i :8080 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### Database Errors

**Symptoms**: "database is locked" or similar errors

**Diagnosis**:
```bash
# Check database integrity
sqlite3 config/jogoborg.db "PRAGMA integrity_check;"

# Check for open connections
lsof config/jogoborg.db
```

**Solutions**:
```bash
# Stop services
make stop

# Wait a moment
sleep 2

# Start services
make start

# Or reset database
make reset
```

### Backup Job Fails

**Symptoms**: Job execution fails or produces errors

**Diagnosis**:
```bash
# Check logs
make logs-scheduler

# Check database error
make db-logs

# Check source data
make source-data
```

**Solutions**:
```bash
# Verify source directory exists
ls -la sourcespace/sample_data

# Check Borg installation
borg --version

# Check disk space
df -h borgspace/
```

### API Not Responding

**Symptoms**: Web UI shows errors or API calls fail

**Diagnosis**:
```bash
# Check API health
make api-health

# Check web server logs
make logs-show-web

# Check if service is running
make status
```

**Solutions**:
```bash
# Restart web server
make restart

# Check port
lsof -i :8080

# Check logs for errors
grep -i "error" logs/web_server.log
```

---

## Performance Testing

### Test P1: Backup Speed

**Objective**: Measure backup performance

**Steps**:
1. Create test data of known size:
   ```bash
   make test-file SIZE=100M
   ```
2. Create backup job
3. Execute and measure time
4. Check logs for duration

**Measurement**:
```bash
# Check backup duration
grep -i "duration" logs/scheduler.log

# Calculate throughput
# Size / Duration = MB/s
```

### Test P2: Memory Usage

**Objective**: Monitor memory usage during backup

**Steps**:
1. Create large test data
2. Execute backup
3. Monitor memory in logs

**Measurement**:
```bash
# Check max memory usage
grep -i "max_memory" logs/scheduler.log

# Monitor in real-time
watch -n 1 'ps aux | grep python3'
```

### Test P3: Concurrent Job Performance

**Objective**: Test performance with multiple concurrent jobs

**Steps**:
1. Create 5 backup jobs
2. Trigger all simultaneously
3. Monitor performance

**Measurement**:
```bash
# Check execution times
grep -i "duration" logs/scheduler.log

# Monitor system resources
top -b -n 1 | head -20
```

### Test P4: Repository Size Growth

**Objective**: Monitor repository size over time

**Steps**:
1. Execute backup multiple times
2. Track repository size
3. Verify deduplication

**Measurement**:
```bash
# Check repository size after each backup
make repos-size

# Calculate deduplication ratio
# (Total data backed up) / (Repository size)
```

---

## Integration Testing

### Test I1: Full Workflow

**Objective**: Complete end-to-end workflow

**Steps**:
1. Setup environment: `make setup`
2. Start services: `make start`
3. Create backup job
4. Execute backup
5. Browse repository
6. View logs
7. Stop services: `make stop`

**Expected Result**: All steps complete successfully

### Test I2: State Reset

**Objective**: Verify clean state reset

**Steps**:
1. Create multiple jobs and execute
2. Reset environment: `make reset`
3. Verify clean state

**Expected Result**: All data cleared, ready for fresh start

### Test I3: Configuration Reload

**Objective**: Test configuration changes

**Steps**:
1. Start services
2. Modify `env.local`
3. Restart services
4. Verify new configuration applied

**Expected Result**: Configuration changes take effect

### Test I4: Log Rotation

**Objective**: Test log file management

**Steps**:
1. Execute many jobs
2. Monitor log file sizes
3. Verify logs don't grow unbounded

**Expected Result**: Logs are managed properly

---

## Automated Testing

### Run All Tests

```bash
# Create test script
cat > run_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "Running Jogoborg Tests..."

# Setup
make setup
make start

# Basic tests
echo "Test 1: API Health"
make api-health

echo "Test 2: Database"
make db-count

# Cleanup
make stop

echo "All tests passed!"
EOF

chmod +x run_tests.sh
./run_tests.sh
```

### Continuous Testing

```bash
# Watch for changes and run tests
while true; do
    make stop
    make reset
    make setup
    make start
    make api-health
    sleep 60
done
```

---

## Test Checklist

- [ ] Web UI accessible
- [ ] Authentication works
- [ ] Create backup job
- [ ] Execute backup job
- [ ] View job logs
- [ ] Browse repository
- [ ] Multiple concurrent jobs
- [ ] Pre/post commands
- [ ] Exclude patterns
- [ ] Different compression
- [ ] Retention policies
- [ ] Large files
- [ ] Error handling
- [ ] Database consistency
- [ ] Configuration persistence
- [ ] Credential encryption
- [ ] Performance acceptable
- [ ] Logs complete
- [ ] State reset works
- [ ] Full workflow succeeds

---

## Next Steps

1. Run basic tests (Test 1-5)
2. Run advanced tests (Test 6-15)
3. Run performance tests (Test P1-P4)
4. Run integration tests (Test I1-I4)
5. Document any issues
6. Fix issues and re-test
7. Deploy to Docker

