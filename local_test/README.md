# Jogoborg Local Testing Environment

This directory contains everything needed to run Jogoborg services locally for development and testing, without requiring Docker.

## Quick Start

### 1. Initial Setup (One-time)

```bash
cd local_test
./setup.sh
```

This will:
- Create necessary directories (`config/`, `borgspace/`, `logs/`, `sourcespace/`)
- Initialize the SQLite database
- Generate GPG encryption keys
- Create sample test data
- Copy environment configuration template

### 2. Configure Environment

Edit `env.local` to customize settings:

```bash
nano env.local
```

Key settings:
- `JOGOBORG_WEB_PORT`: Web server port (default: 8080)
- `JOGOBORG_WEB_USERNAME`: Login username (default: testuser)
- `JOGOBORG_WEB_PASSWORD`: Login password (default: testpass123)
- `JOGOBORG_GPG_PASSPHRASE`: Encryption key for credentials

### 3. Start Services

```bash
./run_local.sh
```

This will start:
- **Web Server**: HTTP API and static file serving (port 8080)
- **Scheduler**: Background job scheduler

Services run in the background. Access the web UI at: **http://localhost:8080**

### 4. Stop Services

```bash
./stop_local.sh
```

## Directory Structure

```
local_test/
├── config/                  # Configuration and database
│   ├── jogoborg.db         # SQLite database
│   └── jogoborg.gpg        # GPG encryption key
├── borgspace/              # Borg backup repositories
├── logs/                   # Application logs
│   ├── web_server.log
│   └── scheduler.log
├── sourcespace/            # Source data to backup
│   └── sample_data/        # Sample files for testing
├── env.local               # Local environment configuration
├── setup.sh                # Initialize environment
├── run_local.sh            # Start services
├── stop_local.sh           # Stop services
└── reset_test_data.sh      # Reset to clean state
```

## Common Tasks

### View Logs in Real-Time

```bash
# Web server logs
tail -f logs/web_server.log

# Scheduler logs
tail -f logs/scheduler.log

# Both logs
tail -f logs/*.log
```

### Create a Test Backup Job

1. Open http://localhost:8080 in your browser
2. Login with credentials from `env.local`
3. Click "New Job"
4. Configure:
   - **Name**: e.g., "test-backup"
   - **Schedule**: e.g., "0 * * * *" (every hour)
   - **Source**: Select `sourcespace/sample_data`
   - **Compression**: lz4 (default)
5. Click "Create"
6. Click "Run Now" to execute immediately

### Manually Trigger a Backup Job

```bash
# Via web UI: Click "Run Now" button

# Via API:
curl -X POST http://localhost:8080/api/jobs/1/run \
  -H "Authorization: Bearer <token>"
```

### Reset Everything to Clean State

```bash
./stop_local.sh
./reset_test_data.sh
./setup.sh
./run_local.sh
```

### Test with Sample Data

Sample data is automatically created in `sourcespace/sample_data/`:
- `file1.txt` - Small text file
- `file2.txt` - Small text file
- `nested/file3.txt` - File in subdirectory
- `large_file.bin` - 10MB binary file for realistic testing

Add more files to `sourcespace/` to test with different data.

## Development Workflow

### Making Changes to Python Code

1. Edit files in `../scripts/`
2. Stop services: `./stop_local.sh`
3. Start services: `./run_local.sh`
4. Changes take effect immediately

### Making Changes to Flutter UI

1. Edit files in `../lib/`
2. Rebuild web app:
   ```bash
   cd ..
   flutter build web --release
   cd local_test
   ```
3. Refresh browser (Ctrl+R or Cmd+R)

### Debugging

**Check if services are running:**
```bash
ps aux | grep python3
```

**Check for port conflicts:**
```bash
lsof -i :8080
```

**View database contents:**
```bash
sqlite3 config/jogoborg.db
sqlite> .tables
sqlite> SELECT * FROM backup_jobs;
```

**Check Borg repositories:**
```bash
ls -la borgspace/
```

## Testing Scenarios

### Scenario 1: Basic Backup Job

1. Start services: `./run_local.sh`
2. Create backup job pointing to `sourcespace/sample_data`
3. Click "Run Now"
4. Check logs: `tail -f logs/scheduler.log`
5. Verify backup created: `ls -la borgspace/`

### Scenario 2: Scheduled Execution

1. Create job with schedule: `*/5 * * * *` (every 5 minutes)
2. Wait for scheduler to execute
3. Check logs for execution

### Scenario 3: Multiple Jobs

1. Create 3-4 backup jobs with different schedules
2. Observe scheduler managing multiple jobs
3. Check logs for concurrent execution

### Scenario 4: Error Handling

1. Create job with invalid source directory
2. Trigger execution
3. Verify error is logged and handled gracefully

### Scenario 5: Database State

1. Create multiple jobs
2. Execute some jobs
3. Query database: `sqlite3 config/jogoborg.db "SELECT * FROM job_logs;"`
4. Verify job history is recorded

## Troubleshooting

### Services Won't Start

**Check Python installation:**
```bash
python3 --version
pip3 list | grep -E "cryptography|croniter"
```

**Install missing dependencies:**
```bash
pip3 install cryptography croniter requests
```

### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or change port in env.local
JOGOBORG_WEB_PORT=8081
```

### Database Locked Error

```bash
# Stop services
./stop_local.sh

# Wait a moment
sleep 2

# Start again
./run_local.sh
```

### Permission Denied on Scripts

```bash
chmod +x *.sh
```

### GPG Key Issues

```bash
# Remove and regenerate
rm config/jogoborg.gpg

# Restart services
./stop_local.sh
./run_local.sh
```

## Environment Variables

All environment variables are loaded from `env.local`. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `JOGOBORG_WEB_PORT` | 8080 | Web server port |
| `JOGOBORG_WEB_USERNAME` | testuser | Login username |
| `JOGOBORG_WEB_PASSWORD` | testpass123 | Login password |
| `JOGOBORG_GPG_PASSPHRASE` | test_encryption_key_change_me | Encryption key |
| `JOGOBORG_URL` | http://localhost:8080 | Service URL |
| `JOGOBORG_CONFIG_DIR` | ./config | Config directory |
| `JOGOBORG_BORGSPACE_DIR` | ./borgspace | Borg repos directory |
| `JOGOBORG_LOG_DIR` | ./logs | Logs directory |
| `JOGOBORG_SOURCESPACE_DIR` | ./sourcespace | Source data directory |

## Performance Considerations

- **First backup**: May take longer due to repository initialization
- **Large files**: Test with `sourcespace/sample_data/large_file.bin` (10MB)
- **Multiple jobs**: Scheduler handles concurrent execution
- **Database size**: SQLite is suitable for development; consider PostgreSQL for production

## Differences from Docker Deployment

| Aspect | Local Testing | Docker |
|--------|---------------|--------|
| **Setup** | Manual scripts | Docker Compose |
| **Isolation** | Shared system | Containerized |
| **Dependencies** | System-wide | Container-bundled |
| **Paths** | `local_test/` | `/config`, `/borgspace`, etc. |
| **Logs** | `local_test/logs/` | Docker volumes |
| **Debugging** | Direct access | Docker exec |

## Next Steps

1. ✅ Run `./setup.sh` to initialize
2. ✅ Review `env.local` configuration
3. ✅ Run `./run_local.sh` to start services
4. ✅ Access http://localhost:8080
5. ✅ Create and test backup jobs
6. ✅ Review logs and database
7. ✅ Make code changes and test
8. ✅ Run `./stop_local.sh` when done

## Support

For issues or questions:
1. Check logs: `tail -f logs/*.log`
2. Review configuration: `cat env.local`
3. Check database: `sqlite3 config/jogoborg.db`
4. See troubleshooting section above

## Integration with Docker

This local testing environment **complements** Docker deployment:

- **Local**: Fast development iteration
- **Docker**: Production-ready deployment

Both use the same codebase with minimal configuration differences.

