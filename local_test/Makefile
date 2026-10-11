.PHONY: help setup start stop restart reset logs logs-web logs-scheduler logs-all \
        status db-jobs db-logs db-clear-logs db-clear-jobs \
        repos source-data api-health api-jobs api-repos \
        clean test-file

# Default target
.DEFAULT_GOAL := help

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Docker image name:tag for `make docker-build` (override on the command line,
# e.g. `make docker-build IMAGE=jogojapan/jogoborg:0.8.0`).
IMAGE ?= jogoborg:latest

help: ## Show this help message
	@echo "$(GREEN)Jogoborg Local Testing - Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make setup          # Initialize environment"
	@echo "  make start          # Start services"
	@echo "  make status         # Show status"
	@echo "  make logs-all       # Follow all logs"
	@echo "  make db-jobs        # List backup jobs"
	@echo ""

# ============================================================================
# Virtual Environment
# ============================================================================

venv: ## Create Python virtual environment (uv; note: no pip/setuptools seeded)
	@echo "$(GREEN)Creating Python virtual environment (uv)...$(NC)"
	@uv venv venv
	@echo "$(GREEN)Virtual environment created!$(NC)"
	@echo "Activate with: source venv/bin/activate"

venv-activate: ## Show how to activate virtual environment
	@echo "$(GREEN)To activate the virtual environment, run:$(NC)"
	@echo "  source venv/bin/activate  (Linux/macOS)"
	@echo "  venv\\Scripts\\activate     (Windows)"

venv-clean: ## Remove virtual environment
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf venv
	@echo "$(GREEN)Virtual environment removed$(NC)"

# ============================================================================
# Service Management
# ============================================================================

setup: ## Initialize local testing environment
	@echo "$(GREEN)Setting up local testing environment...$(NC)"
	@./setup.sh

start: ## Start all services
	@echo "$(GREEN)Starting services...$(NC)"
	@./run_local.sh

stop: ## Stop all services
	@echo "$(GREEN)Stopping services...$(NC)"
	@./stop_local.sh

restart: stop start ## Restart all services

reset: ## Reset test environment to clean state
	@echo "$(YELLOW)Resetting test environment...$(NC)"
	@./reset_test_data.sh

status: ## Show service and environment status
	@bash -c 'source dev_helpers.sh; status'

# ============================================================================
# Logs
# ============================================================================

logs: logs-all ## Show all logs (alias for logs-all)

logs-web: ## Follow web server logs
	@bash -c 'source dev_helpers.sh; tail_web_logs'

logs-scheduler: ## Follow scheduler logs
	@bash -c 'source dev_helpers.sh; tail_scheduler_logs'

logs-all: ## Follow all logs
	@bash -c 'source dev_helpers.sh; tail_all_logs'

logs-show-web: ## Show web server logs (non-follow)
	@bash -c 'source dev_helpers.sh; show_web_logs'

logs-show-scheduler: ## Show scheduler logs (non-follow)
	@bash -c 'source dev_helpers.sh; show_scheduler_logs'

logs-clear: ## Clear all logs
	@bash -c 'source dev_helpers.sh; clear_logs'

# ============================================================================
# Database
# ============================================================================

db-jobs: ## List all backup jobs
	@bash -c 'source dev_helpers.sh; db_list_jobs'

db-logs: ## List job execution logs
	@bash -c 'source dev_helpers.sh; db_list_job_logs'

db-count: ## Show database statistics
	@bash -c 'source dev_helpers.sh; log_info "Backup Jobs: $$(db_count_jobs)"; log_info "Job Logs: $$(db_count_logs)"'

db-clear-logs: ## Clear all job logs from database
	@bash -c 'source dev_helpers.sh; db_clear_logs'

db-clear-jobs: ## Clear all backup jobs from database
	@bash -c 'source dev_helpers.sh; db_clear_jobs'

db-shell: ## Open SQLite database shell
	@sqlite3 config/jogoborg.db

# ============================================================================
# Repositories
# ============================================================================

repos: ## List borg repositories
	@bash -c 'source dev_helpers.sh; list_repositories'

repos-size: ## Show repository sizes
	@bash -c 'source dev_helpers.sh; show_repo_size'

# ============================================================================
# Source Data
# ============================================================================

source-data: ## List source data files
	@bash -c 'source dev_helpers.sh; list_source_data'

source-size: ## Show source data size
	@bash -c 'source dev_helpers.sh; show_source_size'

test-file: ## Add a test file to source data (use: make test-file SIZE=100M)
	@bash -c 'source dev_helpers.sh; add_test_file "test_$$(date +%s).bin" "$${SIZE:-10M}"'

# ============================================================================
# API
# ============================================================================

api-health: ## Check API health
	@bash -c 'source dev_helpers.sh; api_health'

api-jobs: ## List jobs via API
	@bash -c 'source dev_helpers.sh; api_list_jobs'

api-repos: ## List repositories via API
	@bash -c 'source dev_helpers.sh; api_list_repos'

# ============================================================================
# Development
# ============================================================================

dev-help: ## Show development helper functions
	@bash dev_helpers.sh help

clean: ## Clean up temporary files and logs
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@rm -f .web_server.pid .scheduler.pid
	@bash -c 'source dev_helpers.sh; clear_logs'
	@echo "$(GREEN)Cleanup complete$(NC)"

# ============================================================================
# Quick Workflows
# ============================================================================

quick-start: setup start ## Quick start: setup and start services
	@echo "$(GREEN)Ready to go! Access http://localhost:8080$(NC)"

quick-test: start db-jobs logs-all ## Quick test: start and show logs

quick-reset-all: stop reset setup start ## Complete reset and restart

# ============================================================================
# Docker Integration
# ============================================================================

docker-build: ## Build Docker image (IMAGE overridable; with git version baked in)
	@echo "$(GREEN)Building Docker image $(IMAGE)...$(NC)"
	@cd .. && docker build \
		--build-arg GIT_TAG="$$(git describe --tags --abbrev=0 2>/dev/null || echo dev)" \
		--build-arg GIT_COMMIT="$$(git rev-parse --short=10 HEAD 2>/dev/null || echo unknown)" \
		--build-arg BUILD_DATE="$$(date -Is)" \
		-t "$(IMAGE)" .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	@cd .. && docker-compose up -d

docker-stop: ## Stop Docker container
	@echo "$(GREEN)Stopping Docker container...$(NC)"
	@cd .. && docker-compose down

docker-logs: ## Show Docker logs
	@cd .. && docker-compose logs -f

# ============================================================================
# Info
# ============================================================================

info: ## Show environment information
	@echo "$(GREEN)Jogoborg Local Testing Environment$(NC)"
	@echo ""
	@echo "Configuration:"
	@grep -E "^JOGOBORG_" env.local || echo "env.local not found"
	@echo ""
	@echo "Directories:"
	@echo "  Config: $$(pwd)/config"
	@echo "  Repos: $$(pwd)/borgspace"
	@echo "  Logs: $$(pwd)/logs"
	@echo "  Source: $$(pwd)/sourcespace"
	@echo ""
	@echo "Services:"
	@bash -c 'source dev_helpers.sh; is_service_running web_server && echo "  Web Server: running" || echo "  Web Server: stopped"'
	@bash -c 'source dev_helpers.sh; is_service_running scheduler && echo "  Scheduler: running" || echo "  Scheduler: stopped"'
	@echo ""

# ============================================================================
# Testing
# ============================================================================

test-backup: ## Create and run a test backup job
	@echo "$(GREEN)Creating test backup job...$(NC)"
	@echo "This requires the web UI to be running"
	@echo "1. Open http://localhost:8080"
	@echo "2. Create a new backup job"
	@echo "3. Point to: sourcespace/sample_data"
	@echo "4. Click 'Run Now'"
	@echo "5. Check logs: make logs-all"

test-scheduler: ## Test scheduler with multiple jobs
	@echo "$(GREEN)Testing scheduler...$(NC)"
	@echo "1. Create multiple backup jobs with different schedules"
	@echo "2. Watch scheduler logs: make logs-scheduler"
	@echo "3. Verify jobs execute at correct times"

# ============================================================================
# Maintenance
# ============================================================================

check-deps: ## Check for required dependencies
	@echo "$(GREEN)Checking dependencies...$(NC)"
	@command -v python3 >/dev/null 2>&1 && echo "✓ Python 3" || echo "✗ Python 3 not found"
	@command -v sqlite3 >/dev/null 2>&1 && echo "✓ SQLite 3" || echo "✗ SQLite 3 not found"
	@command -v borg >/dev/null 2>&1 && echo "✓ Borg Backup" || echo "✗ Borg Backup not found"
	@python3 -c "import cryptography" 2>/dev/null && echo "✓ cryptography" || echo "✗ cryptography not found"
	@python3 -c "import croniter" 2>/dev/null && echo "✓ croniter" || echo "✗ croniter not found"

install-deps: ## Install Python dependencies (uv, from pyproject.toml)
	@echo "$(GREEN)Installing Python dependencies (uv)...$(NC)"
	@uv pip install -r ../pyproject.toml

# ============================================================================
# Documentation
# ============================================================================

docs: ## Show documentation
	@less ../README.md

docs-testing: ## Show maintainer/agent documentation
	@less ../AGENTS.md

# ============================================================================
# Security scanning (Phase 1)
# ----------------------------------------------------------------------------
# External scanners run on the host / CI runner — they are NOT installed into
# the published image. Install the binaries on PATH once (see AGENTS.md):
#   osv-scanner, trivy, gitleaks
# Reports are written to SCAN_REPORT_DIR. The image scan requires a locally
# built image (make docker-build, or `docker build -t $(SCAN_IMAGE) .`).
# NOTE: trivy matches Debian/PyPI advisories; it does NOT surface PyPI-ecosystem
# CVEs for apt-installed python packages (e.g. python3-msgpack 1.1.2 -> PYSEC),
# which an osv-scanner pass over an SBOM would. See AGENTS.md.
# ----------------------------------------------------------------------------
SCAN_REPORT_DIR ?= ../scan-reports
SCAN_IMAGE ?= jogoborg:scan
SCAN_TRIVY_SEVERITY ?= HIGH,CRITICAL

.PHONY: scan scan-python scan-frontend scan-secrets scan-image security scan-clean scan-check

scan-check:
	@mkdir -p $(SCAN_REPORT_DIR)
	@for t in osv-scanner trivy gitleaks; do command -v $$t >/dev/null 2>&1 || { echo "Missing tool: $$t (install it; see AGENTS.md 'Security scanning')"; exit 1; }; done

scan: scan-check scan-python scan-frontend scan-secrets scan-image
	@echo "Security scans done. Reports in $(SCAN_REPORT_DIR)."

security: scan

scan-python: scan-check
	@echo "--- osv-scanner: python deps (uv.lock) ---"
	osv-scanner scan -L ../uv.lock --format json --output-file $(SCAN_REPORT_DIR)/osv-python.json 2>/dev/null || echo "  findings present - see osv-python.json"

scan-frontend: scan-check
	@echo "--- osv-scanner: frontend (package-lock.json) ---"
	osv-scanner scan -L ../webui/package-lock.json --format json --output-file $(SCAN_REPORT_DIR)/osv-frontend.json 2>/dev/null || echo "  findings present - see osv-frontend.json"

scan-secrets: scan-check
	@echo "--- gitleaks: secrets ---"
	gitleaks detect --source .. --no-banner --report-path $(SCAN_REPORT_DIR)/gitleaks.json --report-format json --exit-code 1 || { echo "SECRETS FOUND - see gitleaks.json"; exit 1; }
	@echo "  no secrets leaked"

scan-image: scan-check
	@echo "--- trivy: image $(SCAN_IMAGE) at $(SCAN_TRIVY_SEVERITY) ---"
	@docker save $(SCAN_IMAGE) -o $(SCAN_REPORT_DIR)/image.tar >/dev/null 2>&1 || { echo "Build the image first: docker build -t $(SCAN_IMAGE) ."; exit 1; }
	trivy image --scanners vuln --input $(SCAN_REPORT_DIR)/image.tar --severity $(SCAN_TRIVY_SEVERITY) --ignore-unfixed --no-progress --exit-code 1 \
	--format json --output $(SCAN_REPORT_DIR)/trivy-image.json || { echo "IMAGE VULNERABILITIES ($(SCAN_TRIVY_SEVERITY)) - see trivy-image.json"; exit 1; }
	@echo "  image clean at $(SCAN_TRIVY_SEVERITY)"

scan-clean:
	@rm -rf ../scan-reports
