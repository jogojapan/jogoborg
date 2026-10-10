# Jogoborg — Borg Backup Management System

Jogoborg is a Docker-based backup solution built on [BorgBackup](https://borgbackup.readthedocs.io/) with a modern web interface. It automates scheduled backups, repository management, S3/MinIO sync, database dumps, and notifications.

- **Frontend**: Svelte web app in [`webui/`](webui/) (auth-protected UI)
- **Backend**: Python services (web server, scheduler, backup executor)
- **Storage**: Borg repositories, SQLite config DB, GPG-encrypted credentials

## Features

- **Automated scheduling** — cron-style jobs restricted to quarter-hour starts
- **Borg repository management** — create, manage, and browse repositories
- **Source directory browser** — interactive file tree with permissions and sizes
- **Database dumps** — PostgreSQL and MariaDB/MySQL before backup
- **S3/MinIO sync** — automatic repository sync to S3-compatible storage
- **Pre/post commands** — run custom commands (incl. Docker) around backups
- **Memory monitoring** — peak memory tracked per operation
- **Notifications** — SMTP email and Gotify webhook
- **Secure config** — GPG-encrypted credentials at rest

## Quick Start (Docker)

### Environment Variables

All Jogoborg variables are prefixed with `JOGOBORG_` to avoid clashes with other containers sharing a compose file. Unprefixed legacy equivalents still work but print deprecation warnings.

| Variable | Default | Required | Purpose |
|----------|---------|:---:|---------|
| `JOGOBORG_WEB_USERNAME` | `admin` | | Web UI login username |
| `JOGOBORG_WEB_PASSWORD` | `changeme` | | Web UI login password |
| `JOGOBORG_GPG_PASSPHRASE` | `changeme` | | Encryption passphrase for credentials |
| `JOGOBORG_URL` | | ✓ | Public base URL, e.g. `https://my.domain.tld` (proxy) or `http://localhost:8080`. Frontend serves here; backend at `$JOGOBORG_URL/api`. |
| `JOGOBORG_WEB_PORT` | `8080` | | Port **inside** the container; the host port is set in your compose mapping. |

**Legacy variables** (`WEB_USERNAME`, `WEB_PASSWORD`, `GPG_PASSPHRASE`, `URL`, `WEB_PORT`) are still read but deprecated — prefer the prefixed forms.

### docker-compose.yml

```yaml
services:
  jogoborg:
    image: jogoborg:latest
    container_name: jogoborg
    ports:
      - "8080:8080"          # host_port:container_port
    volumes:
      - /path/to/source1:/sourcespace/source1:ro   # data to back up (read-only recommended)
      - /path/to/borg/repos:/borgspace              # Borg repositories
      - jogoborg_config:/config                     # config DB + encrypted credentials
      - jogoborg_logs:/log
    environment:
      - JOGOBORG_WEB_USERNAME=admin
      - JOGOBORG_WEB_PASSWORD=your_secure_password
      - JOGOBORG_GPG_PASSPHRASE=your_encryption_key
      - JOGOBORG_URL=https://my.domain.tld
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

> **SELinux systems** (RHEL/CentOS/Fedora): append `:Z` to volume mounts, e.g. `-v /path:/sourcespace/source:ro,z`.

### docker run

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

## Building the Image

```bash
git clone <repository-url> jogoborg
cd jogoborg

# Optionally inject the git version (shows in the sidebar instead of vdev/unknown):
docker build \
  --build-arg GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo dev) \
  --build-arg GIT_COMMIT=$(git rev-parse --short=10 HEAD 2>/dev/null || echo unknown) \
  --build-arg BUILD_DATE=$(date -Is) \
  -t jogoborg:latest .
docker build -t jogoborg:latest .   # or without args (falls back to vdev/unknown)
```

Inside `local_test/`, `make docker-build` builds the image with the git version baked in automatically.

## Directories & Volumes

| Path | Purpose | Recommendation |
|------|---------|----------------|
| `/sourcespace` | Mount source directories here for backup | Read-only (`:ro`) |
| `/borgspace` | Borg repositories | Dedicated volume, adequate space |
| `/config` | SQLite DB + encrypted settings | Named volume |
| `/log` | Application and job logs | Named volume |

## Configuration (Web UI)

Open the web interface at `http://your-host:<port>`, log in, then use the sections:

- **Repositories** — view/manage Borg repositories
- **Source Directories** — browse the source file tree
- **Backup Jobs** — configure and monitor jobs
- **Notifications** — SMTP and webhook setup

### Backup Job Settings

**Basic**
- **Name** — unique identifier
- **Schedule** — cron expression (must start at `0/15/30/45`), see below
- **Compression** — Borg algorithm (default `lz4`)
- **Exclude patterns** — one per line
- **Retention** — keep daily/monthly/yearly archive counts

**Advanced**
- **S3 sync** — Amazon S3 (access key, secret key, storage class) or MinIO (custom endpoint)
- **Database dumps** — PostgreSQL or MariaDB/MySQL host, port, credentials, optional table filter; built-in connection test
- **Pre/Post commands** — run before/after the backup (e.g. `docker stop myservice`); 5 min timeout; non-zero exit logged as warning, does **not** fail the backup

> **Docker commands in jobs**: the container ships the Docker CLI and can mount the Docker socket, enabling `docker stop …`, `docker exec …`, or `docker-compose …` — provided the container has `/var/run/docker.sock` and is in the `docker` group. On SELinux you also need the `label=type:container_runtime_t` security option. See `docker-compose.yml` (`group_add`, `security_opt`, socket mount) for the working configuration.

### Schedule Format

Cron syntax restricted to quarter-hour starts.

- **Valid minutes**: `0`, `15`, `30`, `45`, `*/15`
- Valid: `0 2 * * *` (daily 02:00), `30 */6 * * *` (every 6h), `*/15 * * * *` (every 15 min)
- Invalid: `5 2 * * *` (minute 5), `*/10 * * * *` (10-min intervals)

### Notifications

**SMTP**: host, port (`587` STARTTLS / `465` SSL), security mode, user/password, sender email, optional recipient (defaults to sender).
**Webhook (Gotify)**: message endpoint URL, application token, distinct priority levels for success/error.

## Security

- All credentials (DB, S3 keys, SMTP passwords, admin password) are encrypted at rest with GPG; the key is derived from `JOGOBORG_GPG_PASSPHRASE`.
- Borg repositories use encryption (repokey mode); repository keys are entered via the web UI.
- Default passphrases (`changeme`) must be changed in production.
- Web UI requires authentication; use HTTPS via reverse proxy in production.

### Environment Variable Escaping

Special characters (`$`, backtick, `\`) in passwords **must be quoted** to avoid shell expansion.

```yaml
# Wrong — $secure is expanded:
#   - JOGOBORG_WEB_PASSWORD=my$secure@pass
# Correct — single quotes prevent expansion:
  - JOGOBORG_WEB_PASSWORD='my$secure@pass'
```

Same in `.env` files:

```bash
JOGOBORG_WEB_PASSWORD='my$ecure@Pass123'
JOGOBORG_GPG_PASSPHRASE='my$encryption$key'
```

## Backup Process

1. Pre-command (optional) → 2. memory monitoring starts → 3. `borg create` (compression, exclusions) → 4. `borg prune` (retention) → 5. `borg compact` → 6. database dumps → 7. S3 sync → 8. post-command (optional) → 9. duration/memory/status logged → 10. notifications.

Each job gets its own log file; memory usage is tracked live during Borg operations.

## Monitoring & Health

- `GET /health` — returns service status (used by Docker healthcheck)
- Job logs: `/log/<job-name>.log`; scheduler: `/log/scheduler.log`; web server: `/log/web_server.log`
- Metrics: backup duration, peak memory, success/failure, repository sizes, archive counts

## Local Development & Testing

For fast iteration without rebuilding the Docker image, run the same services directly on your machine from `local_test/`. The local environment mirrors the container layout (`config/`, `borgspace/`, `logs/`, `sourcespace/`) and uses the identical codebase.

### Prerequisites

- Python 3.7+, SQLite 3, **borg**, **gpg**, and the Python packages `cryptography`, `croniter`, `requests` (`make install-deps` or `pip install -r requirements.txt`)
- Node.js 18+ and npm for the Svelte frontend (`cd webui && npm install` once)

### Quick Start

```bash
# From the project root — create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

cd local_test
./setup.sh        # one-time: dirs, SQLite DB, GPG key, sample data, env.local
./run_local.sh    # start web server (8080) + scheduler in the background
# Open http://localhost:8080     login: testuser / testpass123 (from env.local)

./stop_local.sh   # stop services when done
```

`setup.sh` warns (but does not block) if you are not in a virtual environment. Reset everything with `./reset_test_data.sh`.

### Make Targets (`local_test/Makefile`)

| Category | Targets |
|----------|---------|
| Venv | `venv`, `venv-activate`, `venv-clean` |
| Services | `setup`, `start`, `stop`, `restart`, `status`, `reset` |
| Logs | `logs-web`, `logs-scheduler`, `logs-all`, `logs-show-web`, `logs-show-scheduler`, `logs-clear` |
| Database | `db-jobs`, `db-logs`, `db-count`, `db-clear-logs`, `db-clear-jobs`, `db-shell` |
| Repositories | `repos`, `repos-size` |
| Source data | `source-data`, `source-size`, `test-file SIZE=500M` |
| API | `api-health`, `api-jobs`, `api-repos` |
| Docker | `docker-build`, `docker-run`, `docker-stop`, `docker-logs` |
| Dev | `dev-help`, `check-deps`, `install-deps`, `info`, `clean`, `test-backup`, `test-scheduler` |

`make help` lists all targets; `make test-file SIZE=100M` adds a large test file to the sample source data.

### Development Helpers

```bash
source local_test/dev_helpers.sh    # then:
status                # service + env status
db_list_jobs          # list backup jobs
db_list_job_logs      # recent job execution logs
tail_all_logs         # follow all logs
api_list_jobs         # jobs via HTTP API
quick_restart         # stop + start
```

### Local Environment Variables (`local_test/env.local`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `JOGOBORG_WEB_PORT` | `8080` | Web server port |
| `JOGOBORG_WEB_USERNAME` | `testuser` | Login username |
| `JOGOBORG_WEB_PASSWORD` | `testpass123` | Login password |
| `JOGOBORG_GPG_PASSPHRASE` | test key | Encryption key |
| `JOGOBORG_URL` | `http://localhost:8080` | Service URL |
| `JOGOBORG_CONFIG_DIR` | `./config` | Config + SQLite DB + GPG |
| `JOGOBORG_BORGSPACE_DIR` | `./borgspace` | Borg repositories |
| `JOGOBORG_LOG_DIR` | `./logs` | Logs |
| `JOGOBORG_SOURCESPACE_DIR` | `./sourcespace` | Source data |
| `JOGOBORG_LOG_LEVEL` | — | `DEBUG/INFO/WARNING/ERROR` |
| `JOGOBORG_DEV_AUTO_RELOAD`, `JOGOBORG_DEV_VERBOSE` | — | Development tuning |

### Development Workflow

- **Python** (`scripts/`): stop → edit → `make start` (changes take effect on restart; `JOGOBORG_DEV_AUTO_RELOAD` enables live reload).
- **Frontend** (`webui/`): for local dev run `npm run dev` (Vite dev server on http://localhost:5173, proxying `/api` to the backend; set `JOGOBORG_API_PROXY` if your backend runs elsewhere). For a production build run `npm run build` — output `webui/dist/` is what `web_server.py` serves as `JOGOBORG_WEB_DIR` in the container. Run `npm run check` to type-check.
- **Verify a backup**: `make start` → create job in the UI → "Run Now" → `make logs-scheduler` + `make db-logs` + `make repos`.

### Local vs Docker

| Aspect | Local | Docker |
|--------|-------|--------|
| Setup | `./setup.sh` | compose up |
| Isolation | shared system | containerized |
| Paths | `local_test/…` | `/config`, `/borgspace`, … |
| Logs | `local_test/logs` | named volumes |
| Iteration | instant | image rebuild |

## Scheduler Concurrency & Memory Limits

Backup jobs run **in parallel** (up to `JOGOBORG_MAX_PARALLEL_JOBS`, default 4). The scheduler checks every 30 seconds and starts each due job in its own thread, so a job scheduled while another is still running starts on time instead of waiting or being skipped.

The **Past Jobs** view (`/gantt`) shows the last 7 days of runs as a Gantt chart: zoom levels from 3h to 92h, a horizontal scrollbar to pan, and bars coloured by peak memory relative to the container limit. The backup-job dialogs include a mini version ("View scheduling activity") to pick a quiet window from past data when choosing a schedule.

Inside Docker the scheduler reads the container memory limit from cgroup and can **delay** a job when memory is near its limit, notifying through the configured channels (SMTP/Gotify) with the delay length and current usage:

| Variable | Default | Purpose |
|----------|---------|---------|
| `JOGOBORG_MAX_PARALLEL_JOBS` | `4` | Max concurrent backup jobs |
| `JOGOBORG_MEMORY_DELAY_THRESHOLD` | `0.75` | Delay a new job when container usage ≥ this fraction of the limit |
| `JOGOBORG_MEMORY_RESUME_THRESHOLD` | `0.70` | Start the delayed job once usage drops below this |
| `JOGOBORG_MEMORY_DELAY_SECONDS` | `3600` | Delay length / re-check interval (seconds) |

Memory limits are only known inside a container; the memory gate is disabled when none is available (e.g. local dev), where jobs simply run in parallel.

## Borg Archive Browsing

The Repositories screen lets you open an archive and browse its file tree (folders and files with human-readable sizes and dates). On the first open of an archive the server runs a single `borg list` over the whole archive and caches the parsed directory tree **in the web server's memory (server-side) — not in the browser**. The client only holds the currently shown directory's items. Subsequent navigation (into folders, up, back to the archive list) is served from that cached tree instantly, with no further borg reads.

The cache is keyed by repository + archive, expires after ~30 minutes, is capped (the oldest entry is evicted when over capacity), and is **freed immediately when you leave a repository** back to the Repositories screen (an explicit release request). Opening an archive again re-scans it once. Borg 1.x has no per-directory listing index, so this single full scan is the unavoidable cost.

While an archive is first being scanned, the explorer shows a **live progress bar** (percentage and items scanned). The scan streams borg's output and reports progress to a `/progress` endpoint; the web server runs threaded so this polling doesn't block browsing or other API calls.

## Stopping & Recovery

- **Graceful stop**: `docker stop` now lets in-flight backups finish. The scheduler stops dispatching new jobs and drains running ones for up to `JOGOBORG_SHUTDOWN_GRACE` (default **300s**; compose sets `stop_grace_period: 330s`). If a job still can't finish in that time, its `borg` subprocess is sent `SIGINT` for a **clean abort** (no repository corruption), and you're **notified via the configured channels** (SMTP/Gotify) with the job name and the phase it was in (`pre_command`, `borg_create`, `borg_prune`, `borg_compact`, `db_dump`, `s3_sync`, `post_command`).
- **Interrupted jobs**: a job left `running` by a stop is marked **`interrupted`** on the next start (and a notification is sent), so the UI shows no phantom running jobs.
- **After an unclean kill** (e.g. `docker kill`, host crash): `borg create` is crash-safe (no partial archive is committed), but an interrupted `prune`/`compact` may need `borg check --repair`. S3 is re-synced on the next run (incremental), and DB dumps are written to a temp file that is renamed only on success, so no partial `.sql` is mistaken for a completed dump (stale temp files are removed by the regular cleanup).

## Troubleshooting

### Deployment

- **Job not running** — check quarter-hour schedule; verify source dirs accessible; `docker logs jogoborg | grep scheduler`.
- **Repository access errors** — verify encryption passphrase, `borgspace` permissions, repo initialized.
- **S3 sync failures** — check credentials/permissions, network, AWS CLI config.
- **Database connection issues** — use the "Test Connection" button; check DB host reachability from the container and DB user grants.
- **Notification failures** — test SMTP/webhook in the UI; check network and credentials.
- **Missing DB migration** — run manually inside the container:
  ```bash
  docker-compose exec jogoborg python3 scripts/init_db.py
  ```
  (replace `jogoborg` with your container name).

### Local Environment

- **Services won't start** — `make check-deps`; ensure Python + `cryptography`/`croniter`/`requests`; check port with `lsof -i :8080`.
- **Port in use** — kill the process or change `JOGOBORG_WEB_PORT` in `env.local`.
- **Database locked** — `make stop`, wait ~2s, `make start`.
- **Permission denied on scripts** — `chmod +x *.sh`.
- **GPG key issues** — remove `config/jogoborg.gpg`, restart; it regenerates.

### Recovery

- **Repositories** — standard Borg recovery; restore from S3 sync.
- **Configuration** — stored in `/config`; schema auto-recreated if missing; GPG key regenerated if absent.

## Performance Notes

- First backup is slower (repo init). Memory varies with repo size and compression; monitor peak usage in job logs.
- Stagger jobs and prefer off-peak hours; use appropriate compression (Borg dedup + periodic compaction saves space).

## Migration

- **From rsync/tar** — create jobs pointing at the same sources; phase out the old method gradually.
- **From another Borg setup** — copy existing repos into `/borgspace`, configure matching schedules, re-enter passphrases in the UI.

## Contributing

See [AGENTS.md](AGENTS.md) for the architecture, code layout, and conventions used by maintainers and automated agents.

## License

MIT — see [LICENSE](LICENSE).