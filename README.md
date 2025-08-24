# Jogoborg - Borg Backup Management System

Jogoborg is a comprehensive Docker-based backup solution using BorgBackup with a modern Flutter web interface. It provides automated backup scheduling, S3 integration, database dumps, and notification capabilities.

## Features

- **Automated Backup Scheduling**: Quarter-hour precision scheduling with cron-style configuration
- **Borg Repository Management**: Create, manage, and browse Borg backup repositories
- **Source Directory Browser**: Interactive file tree browser with permissions and size information
- **Database Integration**: Automated PostgreSQL and MariaDB/MySQL database dumps
- **S3/MinIO Sync**: Automatic repository synchronization to S3-compatible storage
- **Memory Monitoring**: Real-time memory usage tracking during backup operations
- **Notification System**: SMTP email and webhook (Gotify) notifications
- **Web Interface**: Modern Flutter web UI with authentication
- **Secure Configuration**: GPG-encrypted credential storage

## Quick Start

### Environment Variables

All Jogoborg environment variables are prefixed with `JOGOBORG_` to avoid conflicts with other containers.

#### Required
- `JOGOBORG_WEB_USERNAME`: Web interface username (default: admin)
- `JOGOBORG_WEB_PASSWORD`: Web interface password (default: changeme)
- `JOGOBORG_GPG_PASSPHRASE`: Encryption passphrase for credentials (default: changeme)

#### Optional
- `JOGOBORG_WEB_PORT`: Web interface port (default: 8080)

#### Legacy Support
For backward compatibility, the old unprefixed variables (`WEB_USERNAME`, `WEB_PASSWORD`, etc.) are still supported but will show deprecation warnings. Use the `JOGOBORG_` prefixed versions for new deployments.

### Docker Compose Example

```yaml
version: '3.8'

services:
  jogoborg:
    image: jogoborg:latest
    container_name: jogoborg
    ports:
      - "8080:8080"  # Change to "host_port:container_port" as needed
    volumes:
      # Source directories to backup (read-only recommended)
      - /path/to/source1:/sourcespace/source1:ro
      - /path/to/source2:/sourcespace/source2:ro
      
      # Borg repositories storage
      - /path/to/borg/repos:/borgspace
      
      # Configuration and database
      - jogoborg_config:/config
      
      # Logs
      - jogoborg_logs:/log
    environment:
      - WEB_USERNAME=admin
      - WEB_PASSWORD=your_secure_password
      - GPG_PASSPHRASE=your_encryption_key
      - WEB_PORT=8080
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  jogoborg_config:
  jogoborg_logs:
```

### Docker Run Example

```bash
docker run -d \
  --name jogoborg \
  -p 8080:8080 \
  -v /path/to/source:/sourcespace/source:ro \
  -v /path/to/borg/repos:/borgspace \
  -v jogoborg_config:/config \
  -v jogoborg_logs:/log \
  -e JOGOBORG_WEB_USERNAME=admin \
  -e JOGOBORG_WEB_PASSWORD=your_secure_password \
  -e JOGOBORG_GPG_PASSPHRASE=your_encryption_key \
  jogoborg:latest
```

**For SELinux systems (RHEL, CentOS, Fedora), add `:Z` to volume mounts:**

```bash
docker run -d \
  --name jogoborg \
  -p 8080:8080 \
  -v /path/to/source:/sourcespace/source:ro,z \
  -v /path/to/borg/repos:/borgspace:Z \
  -v jogoborg_config:/config:Z \
  -v jogoborg_logs:/log:Z \
  -e JOGOBORG_WEB_USERNAME=admin \
  -e JOGOBORG_WEB_PASSWORD=your_secure_password \
  -e JOGOBORG_GPG_PASSPHRASE=your_encryption_key \
  jogoborg:latest
```

## Building the Image

```bash
git clone <repository-url> jogoborg
cd jogoborg
docker build -t jogoborg:latest .
```

## Directory Structure

### Container Directories

- `/sourcespace`: Mount your source directories here for backup
- `/borgspace`: Borg repositories are stored here
- `/config`: Configuration files, database, and encrypted settings
- `/log`: Application and job logs

### Host Volume Recommendations

- **Source directories**: Mount as read-only (`:ro`) for security
- **Borg repositories**: Use a dedicated volume or directory with adequate space
- **Config/Logs**: Use named volumes for persistence

## Configuration

### Web Interface

1. Access the web interface at `http://your-host:8080`
2. Login with your configured username and password
3. Navigate through the sections:
   - **Repositories**: View and manage Borg repositories
   - **Source Directories**: Browse source file tree
   - **Backup Jobs**: Configure and monitor backup jobs
   - **Notifications**: Setup SMTP and webhook notifications

### Backup Job Configuration

#### Basic Settings
- **Name**: Unique identifier for the job
- **Schedule**: Cron expression (must start at quarter hours: 0, 15, 30, 45)
- **Compression**: Borg compression algorithm (default: lz4)
- **Exclude Patterns**: File patterns to exclude (one per line)
- **Retention**: Keep daily/monthly/yearly archive counts

#### Advanced Features

##### S3 Synchronization
Configure automatic repository sync to S3-compatible storage:
- **Amazon S3**: Specify access key, secret key, and storage class
- **MinIO**: Specify custom endpoint, access credentials

##### Database Dumps
Include database dumps in your backups:
- **PostgreSQL**: Host, port, credentials, specific tables
- **MariaDB/MySQL**: Host, port, credentials, specific tables
- Built-in connection testing

##### Pre/Post Commands
Execute custom commands before and after backups:
- **Pre-Command**: Runs before backup starts (e.g., `docker stop myservice`)
- **Post-Command**: Runs after backup completes (success or failure, e.g., `docker start myservice`)
- **Docker Support**: Docker CLI is available for container management
- **Timeout**: Commands timeout after 5 minutes
- **Error Handling**: Non-zero exit codes are logged as warnings but don't fail the backup

**Docker Commands**: The container includes Docker CLI and mounts the Docker socket, allowing commands like:
- `docker stop mycontainer`
- `docker exec mycontainer /app/maintenance.sh`
- `docker-compose -f /path/to/compose.yml stop service`

This will only work if the container has access to /var/run/docker.sock and is a member of the docker Linux group. If the host is running SELinux, you also need to the `label=type:container_runtime_t` security option. See `docker-compose.yml` (entries for `group_add`, `security_opt` and `/var/run/docker.sock`) for examples of how to make this work).

### Schedule Format

Backup jobs use cron syntax but are restricted to quarter-hour starts:

**Valid minute values**: `0`, `15`, `30`, `45`, `*/15`

**Examples**:
- `0 2 * * *` - Daily at 2:00 AM
- `30 */6 * * *` - Every 6 hours at 30 minutes past
- `*/15 * * * *` - Every 15 minutes

**Invalid examples**:
- `5 2 * * *` - Invalid (minute 5 not allowed)
- `*/10 * * * *` - Invalid (10-minute intervals not supported)

## Notification Configuration

### SMTP Email
- **Host**: SMTP server hostname
- **Port**: SMTP port (587 for STARTTLS, 465 for SSL)
- **Security**: STARTTLS, SSL/TLS, or None
- **Username/Password**: SMTP authentication
- **Sender Email**: Email address to send notifications from
- **Recipient Email**: Email address to receive notifications (optional, defaults to sender)

### Webhook (Gotify)
- **URL**: Gotify message endpoint
- **Token**: Application token
- **Priority Levels**: Different priorities for success/error messages

## Security Considerations

### Credential Storage
- All sensitive credentials are encrypted using GPG with your passphrase
- Database credentials, S3 keys, and SMTP passwords are encrypted at rest
- Encryption key is derived from the `GPG_PASSPHRASE` environment variable

### Repository Access
- Borg repositories use encryption (repokey mode)
- Default passphrase is 'changeme' - **change this in production**
- Repository keys are entered through the web interface

### Network Security
- Web interface requires authentication
- Consider using reverse proxy with HTTPS in production
- Restrict network access to the container

## Backup Process

### Execution Flow
1. **Pre-command**: Optional command execution
2. **Memory monitoring**: Start tracking memory usage
3. **Borg create**: Create archive with specified compression and exclusions
4. **Borg prune**: Remove old archives based on retention policy
5. **Borg compact**: Compact repository to reclaim space
6. **Database dumps**: Create and backup database dumps (if configured)
7. **S3 sync**: Synchronize repository to S3 (if configured)
8. **Post-command**: Optional command execution
9. **Logging**: Record duration, memory usage, and status
10. **Notifications**: Send success/failure notifications

### Memory Monitoring
- Real-time tracking of Borg process memory usage
- Maximum memory consumption logged for each operation
- Helps with resource planning and optimization

### Logging
- Separate log file for each backup job
- Centralized scheduler and web server logs
- Includes timestamps, durations, memory usage, and error details

## Monitoring and Health Checks

### Health Check Endpoint
- `GET /health`: Returns service status
- Used by Docker health checks
- Monitor service availability

### Log Monitoring
- Job-specific logs in `/log/<job-name>.log`
- Scheduler log in `/log/scheduler.log`
- Web server log in `/log/web_server.log`

### Metrics Available
- Backup duration and memory usage
- Success/failure rates
- Repository sizes and archive counts

## Troubleshooting

### Common Issues

#### Backup Job Not Running
1. Check job schedule format (must use quarter-hour minutes)
2. Verify source directories are accessible
3. Check scheduler logs: `docker logs jogoborg | grep scheduler`

#### Repository Access Errors
1. Verify correct encryption passphrase
2. Check repository permissions in `/borgspace`
3. Ensure repository was properly initialized

#### S3 Sync Failures
1. Verify S3 credentials and permissions
2. Check network connectivity
3. Review rclone configuration in logs

#### Database Connection Issues
1. Use the "Test Connection" button in the web interface
2. Verify database host accessibility from container
3. Check database user permissions

#### Notification Failures
1. Test SMTP/webhook configuration in web interface
2. Check network connectivity
3. Verify credentials and server settings

#### Missing Database Migration
Should you get errors about missing or incomplete database migrations
in the docker log, you may want to run a DB migration in the container
manually:

``` bash
docker-compose exec jogoborg python3 scripts/init_db.py
```

(Replace `jogoborg` with the name you are using for the container.)

### Log Locations
- Application logs: `/log/` directory in container
- Access via: `docker exec jogoborg tail -f /log/scheduler.log`

### Recovery Procedures

#### Repository Recovery
1. Use standard Borg commands to recover repositories
2. Mount repository volume to another container if needed
3. S3 sync allows repository restoration from cloud storage

#### Configuration Recovery
1. Configuration is stored in `/config` volume
2. Database schema is automatically recreated if missing
3. GPG key is regenerated if not present

## Performance Optimization

### Resource Usage
- Memory usage varies with repository size and compression
- Monitor maximum memory consumption in job logs
- Adjust container memory limits based on usage patterns

### Scheduling Optimization
- Stagger backup jobs to avoid resource conflicts
- Consider off-peak hours for large backups
- Use appropriate compression algorithms for your data

### Storage Optimization
- Configure appropriate retention policies
- Use Borg's deduplication capabilities
- Regular repository compaction reduces storage usage

## Advanced Configuration

### Custom Borg Options
- Modify compression settings per job
- Use exclude patterns for fine-grained control
- Leverage Borg's built-in deduplication

### Integration with Other Systems
- Use pre/post commands for complex workflows
- Integrate with monitoring systems via webhooks
- Coordinate with other containers using Docker networks

### Backup Validation
- Regular restore testing recommended
- Use Borg's verification features
- Monitor backup sizes and file counts for anomalies

## Migration from Other Backup Systems

### From rsync/tar
1. Create new backup jobs with same source directories
2. Gradually phase out old backup methods
3. Leverage Borg's superior compression and deduplication

### From other Borg setups
1. Copy existing repositories to `/borgspace`
2. Configure jobs to match existing schedules
3. Update repository passphrases in web interface

## Contributing

This project is designed to be extensible:
- Flutter web interface for additional features
- Python backend services for new integrations
- Docker-based deployment for easy updates

## License

MIT License. See LICENSE file.

## Support

For issues and feature requests:
1. Check troubleshooting section
2. Review logs for error details
3. Consult Borg documentation for backup-specific issues
