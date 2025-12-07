#!/bin/bash
# Jogoborg Development Helper Functions
# Source this file to use helper functions: source dev_helpers.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment
if [ -f "$SCRIPT_DIR/env.local" ]; then
    source "$SCRIPT_DIR/env.local"
fi

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo "ℹ️  $*"
}

log_success() {
    echo "✓ $*"
}

log_error() {
    echo "❌ $*" >&2
}

log_warning() {
    echo "⚠️  $*"
}

# ============================================================================
# Service Management
# ============================================================================

is_service_running() {
    local service=$1
    local pid_file="$SCRIPT_DIR/.${service}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_service_pid() {
    local service=$1
    local pid_file="$SCRIPT_DIR/.${service}.pid"
    
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    fi
}

# ============================================================================
# Database Functions
# ============================================================================

db_query() {
    local query=$1
    sqlite3 "$SCRIPT_DIR/config/jogoborg.db" "$query"
}

db_list_jobs() {
    log_info "Backup Jobs:"
    db_query "SELECT id, name, schedule, created_at FROM backup_jobs;"
}

db_list_job_logs() {
    local job_id=${1:-1}
    log_info "Job Logs for Job ID $job_id:"
    db_query "SELECT id, started_at, status, error_message FROM job_logs WHERE job_id = $job_id ORDER BY started_at DESC LIMIT 10;"
}

db_count_jobs() {
    db_query "SELECT COUNT(*) FROM backup_jobs;"
}

db_count_logs() {
    db_query "SELECT COUNT(*) FROM job_logs;"
}

db_clear_logs() {
    log_warning "Clearing all job logs..."
    db_query "DELETE FROM job_logs;"
    log_success "Job logs cleared"
}

db_clear_jobs() {
    log_warning "Clearing all backup jobs..."
    db_query "DELETE FROM backup_jobs;"
    log_success "Backup jobs cleared"
}

# ============================================================================
# Log Functions
# ============================================================================

tail_web_logs() {
    tail -f "$SCRIPT_DIR/logs/web_server.log"
}

tail_scheduler_logs() {
    tail -f "$SCRIPT_DIR/logs/scheduler.log"
}

tail_all_logs() {
    tail -f "$SCRIPT_DIR/logs"/*.log
}

show_web_logs() {
    cat "$SCRIPT_DIR/logs/web_server.log"
}

show_scheduler_logs() {
    cat "$SCRIPT_DIR/logs/scheduler.log"
}

clear_logs() {
    log_warning "Clearing all logs..."
    rm -f "$SCRIPT_DIR/logs"/*.log
    touch "$SCRIPT_DIR/logs/.gitkeep"
    log_success "Logs cleared"
}

# ============================================================================
# Repository Functions
# ============================================================================

list_repositories() {
    log_info "Borg Repositories:"
    ls -lh "$SCRIPT_DIR/borgspace/" | grep -v "^total" | grep -v "^d.*\.$"
}

show_repo_size() {
    log_info "Repository Sizes:"
    du -sh "$SCRIPT_DIR/borgspace"/*
}

# ============================================================================
# Source Data Functions
# ============================================================================

add_test_file() {
    local filename=${1:-"test_$(date +%s).txt"}
    local size=${2:-"1M"}
    
    log_info "Adding test file: $filename ($size)"
    dd if=/dev/zero of="$SCRIPT_DIR/sourcespace/sample_data/$filename" bs=1 count="$size" 2>/dev/null
    log_success "Test file added"
}

list_source_data() {
    log_info "Source Data:"
    find "$SCRIPT_DIR/sourcespace" -type f -exec ls -lh {} \;
}

show_source_size() {
    log_info "Source Data Size:"
    du -sh "$SCRIPT_DIR/sourcespace"
}

# ============================================================================
# API Functions
# ============================================================================

api_health() {
    log_info "Checking API health..."
    curl -s http://localhost:$JOGOBORG_WEB_PORT/health | jq . || echo "API not responding"
}

api_list_jobs() {
    log_info "Fetching jobs from API..."
    curl -s http://localhost:$JOGOBORG_WEB_PORT/api/jobs | jq . || echo "API not responding"
}

api_list_repos() {
    log_info "Fetching repositories from API..."
    curl -s http://localhost:$JOGOBORG_WEB_PORT/api/repositories | jq . || echo "API not responding"
}

# ============================================================================
# Status Functions
# ============================================================================

status() {
    echo ""
    echo "=========================================="
    echo "Jogoborg Local Testing - Status"
    echo "=========================================="
    echo ""
    
    echo "Services:"
    if is_service_running "web_server"; then
        log_success "Web Server running (PID: $(get_service_pid web_server))"
    else
        log_error "Web Server not running"
    fi
    
    if is_service_running "scheduler"; then
        log_success "Scheduler running (PID: $(get_service_pid scheduler))"
    else
        log_error "Scheduler not running"
    fi
    
    echo ""
    echo "Database:"
    log_info "Backup Jobs: $(db_count_jobs)"
    log_info "Job Logs: $(db_count_logs)"
    
    echo ""
    echo "Storage:"
    log_info "Source Data: $(du -sh "$SCRIPT_DIR/sourcespace" | cut -f1)"
    log_info "Repositories: $(du -sh "$SCRIPT_DIR/borgspace" | cut -f1)"
    
    echo ""
    echo "Web Interface:"
    log_info "URL: $JOGOBORG_URL"
    log_info "Username: $JOGOBORG_WEB_USERNAME"
    
    echo ""
}

# ============================================================================
# Quick Commands
# ============================================================================

quick_start() {
    log_info "Starting Jogoborg..."
    cd "$SCRIPT_DIR"
    ./run_local.sh
}

quick_stop() {
    log_info "Stopping Jogoborg..."
    cd "$SCRIPT_DIR"
    ./stop_local.sh
}

quick_restart() {
    log_info "Restarting Jogoborg..."
    cd "$SCRIPT_DIR"
    ./stop_local.sh
    sleep 2
    ./run_local.sh
}

quick_reset() {
    log_warning "Resetting test environment..."
    cd "$SCRIPT_DIR"
    ./stop_local.sh
    ./reset_test_data.sh
    ./setup.sh
}

# ============================================================================
# Help
# ============================================================================

dev_help() {
    cat << 'EOF'
Jogoborg Development Helper Functions

Service Management:
  is_service_running <service>    Check if service is running
  get_service_pid <service>       Get service PID
  quick_start                     Start services
  quick_stop                      Stop services
  quick_restart                   Restart services
  quick_reset                     Reset everything
  status                          Show overall status

Database:
  db_query <sql>                  Execute SQL query
  db_list_jobs                    List all backup jobs
  db_list_job_logs [job_id]       List job logs
  db_count_jobs                   Count backup jobs
  db_count_logs                   Count job logs
  db_clear_logs                   Clear all job logs
  db_clear_jobs                   Clear all backup jobs

Logs:
  tail_web_logs                   Follow web server logs
  tail_scheduler_logs             Follow scheduler logs
  tail_all_logs                   Follow all logs
  show_web_logs                   Show web server logs
  show_scheduler_logs             Show scheduler logs
  clear_logs                      Clear all logs

Repositories:
  list_repositories               List borg repositories
  show_repo_size                  Show repository sizes

Source Data:
  add_test_file [name] [size]     Add test file to source data
  list_source_data                List source data files
  show_source_size                Show source data size

API:
  api_health                      Check API health
  api_list_jobs                   List jobs via API
  api_list_repos                  List repositories via API

Logging:
  log_info <msg>                  Print info message
  log_success <msg>               Print success message
  log_error <msg>                 Print error message
  log_warning <msg>               Print warning message

Examples:
  source dev_helpers.sh
  status
  db_list_jobs
  tail_all_logs
  quick_restart
  add_test_file "large_file.bin" "100M"

EOF
}

# Print help if requested
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    dev_help
fi
