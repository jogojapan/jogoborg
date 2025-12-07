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

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	@cd .. && docker build -t jogoborg:latest .

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

install-deps: ## Install Python dependencies
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	@pip3 install cryptography croniter requests

# ============================================================================
# Documentation
# ============================================================================

docs: ## Show documentation
	@less README.md

docs-testing: ## Show testing approach documentation
	@less ../TESTING_APPROACH.md
