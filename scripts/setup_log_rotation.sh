#!/bin/bash

# Log Rotation and Disk Space Management Setup Script
# This script configures log rotation and disk space monitoring for the honey-token system

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="honey-token-auditing"
INSTALL_DIR="/home/ubuntu/$PROJECT_NAME"
SERVICE_USER="ubuntu"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to setup logrotate configuration
setup_logrotate() {
    print_status "Setting up log rotation configuration..."
    
    # Create logrotate configuration for application logs
    sudo tee /etc/logrotate.d/honey-token-auditing > /dev/null <<EOF
# Honey-Token Auditing System Log Rotation Configuration

# Application JSON logs
$INSTALL_DIR/logs/*.json {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    copytruncate
    postrotate
        # Signal services to reopen log files if needed
        systemctl reload honey-token-monitor.service > /dev/null 2>&1 || true
        systemctl reload honey-token-dashboard.service > /dev/null 2>&1 || true
    endscript
}

# System logs for honey-token services
/var/log/honey-token-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    sharedscripts
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}

# Archive old compressed logs
$INSTALL_DIR/logs/*.json.*.gz {
    monthly
    rotate 12
    missingok
    notifempty
}
EOF

    # Test logrotate configuration
    if sudo logrotate -d /etc/logrotate.d/honey-token-auditing >/dev/null 2>&1; then
        print_success "Log rotation configuration created and validated"
    else
        print_error "Log rotation configuration validation failed"
        return 1
    fi
}

# Function to create disk space monitoring script
create_disk_monitor() {
    print_status "Creating disk space monitoring script..."
    
    cat > "$INSTALL_DIR/scripts/disk_space_monitor.sh" <<'EOF'
#!/bin/bash

# Disk Space Monitoring Script for Honey-Token Auditing System
# This script monitors disk usage and cleans up old files when space is low

# Configuration
INSTALL_DIR="/home/ubuntu/honey-token-auditing"
LOG_FILE="/var/log/honey-token-disk-monitor.log"
DISK_THRESHOLD=85  # Percentage threshold for cleanup
CRITICAL_THRESHOLD=95  # Critical threshold for emergency cleanup

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to get disk usage percentage
get_disk_usage() {
    df / | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Function to get directory size in MB
get_dir_size() {
    du -sm "$1" 2>/dev/null | cut -f1
}

# Function to clean old log files
clean_old_logs() {
    local days_old="$1"
    local cleaned_files=0
    
    log_message "INFO: Cleaning log files older than $days_old days"
    
    # Clean compressed JSON logs
    if [ -d "$INSTALL_DIR/logs" ]; then
        find "$INSTALL_DIR/logs" -name "*.json.*.gz" -mtime +$days_old -type f | while read -r file; do
            if [ -f "$file" ]; then
                rm -f "$file"
                log_message "INFO: Removed old log file: $(basename "$file")"
                ((cleaned_files++))
            fi
        done
    fi
    
    # Clean old system logs
    find /var/log -name "honey-token-*.log.*" -mtime +$days_old -type f 2>/dev/null | while read -r file; do
        if [ -f "$file" ]; then
            sudo rm -f "$file"
            log_message "INFO: Removed old system log: $(basename "$file")"
            ((cleaned_files++))
        fi
    done
    
    log_message "INFO: Cleaned $cleaned_files old log files"
}

# Function to clean large log files
clean_large_logs() {
    log_message "INFO: Checking for large log files"
    
    # Find and truncate large JSON files (>100MB)
    find "$INSTALL_DIR/logs" -name "*.json" -size +100M -type f | while read -r file; do
        if [ -f "$file" ]; then
            # Keep last 1000 lines
            tail -n 1000 "$file" > "${file}.tmp"
            mv "${file}.tmp" "$file"
            log_message "WARNING: Truncated large log file: $(basename "$file")"
        fi
    done
}

# Function to perform emergency cleanup
emergency_cleanup() {
    log_message "CRITICAL: Performing emergency disk cleanup"
    
    # Clean very old logs (7+ days)
    clean_old_logs 7
    
    # Clean large logs
    clean_large_logs
    
    # Clean temporary files
    find /tmp -name "*honey*" -mtime +1 -type f -delete 2>/dev/null || true
    
    # Clean Python cache
    find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR" -name "*.pyc" -type f -delete 2>/dev/null || true
    
    log_message "CRITICAL: Emergency cleanup completed"
}

# Function to send alert (placeholder for future notification system)
send_alert() {
    local message="$1"
    local level="$2"
    
    log_message "$level: ALERT - $message"
    
    # Future: Send email, Slack notification, etc.
    # For now, just log to syslog
    logger -t honey-token-disk-monitor "$level: $message"
}

# Main monitoring function
main() {
    local disk_usage
    disk_usage=$(get_disk_usage)
    
    log_message "INFO: Current disk usage: ${disk_usage}%"
    
    # Check if we need to take action
    if [ "$disk_usage" -ge "$CRITICAL_THRESHOLD" ]; then
        send_alert "Critical disk usage: ${disk_usage}%" "CRITICAL"
        emergency_cleanup
        
        # Check again after cleanup
        disk_usage=$(get_disk_usage)
        if [ "$disk_usage" -ge "$CRITICAL_THRESHOLD" ]; then
            send_alert "Disk usage still critical after cleanup: ${disk_usage}%" "CRITICAL"
        else
            log_message "INFO: Disk usage after emergency cleanup: ${disk_usage}%"
        fi
        
    elif [ "$disk_usage" -ge "$DISK_THRESHOLD" ]; then
        send_alert "High disk usage: ${disk_usage}%" "WARNING"
        
        # Perform standard cleanup
        clean_old_logs 30
        
        # Check again after cleanup
        disk_usage=$(get_disk_usage)
        log_message "INFO: Disk usage after cleanup: ${disk_usage}%"
        
    else
        log_message "INFO: Disk usage is normal: ${disk_usage}%"
    fi
    
    # Log directory sizes for monitoring
    if [ -d "$INSTALL_DIR/logs" ]; then
        logs_size=$(get_dir_size "$INSTALL_DIR/logs")
        log_message "INFO: Logs directory size: ${logs_size}MB"
    fi
    
    # Rotate our own log file if it gets too large
    if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt 10485760 ]; then
        # Keep last 100 lines if log file > 10MB
        tail -n 100 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        log_message "INFO: Rotated disk monitor log file"
    fi
}

# Run main function
main "$@"
EOF

    chmod +x "$INSTALL_DIR/scripts/disk_space_monitor.sh"
    print_success "Disk space monitoring script created"
}

# Function to create log analysis script
create_log_analyzer() {
    print_status "Creating log analysis script..."
    
    cat > "$INSTALL_DIR/scripts/analyze_logs.sh" <<'EOF'
#!/bin/bash

# Log Analysis Script for Honey-Token Auditing System
# This script provides analysis and statistics for system logs

INSTALL_DIR="/home/ubuntu/honey-token-auditing"

# Function to analyze attack logs
analyze_attacks() {
    local attacks_file="$INSTALL_DIR/logs/attacks.json"
    
    if [ ! -f "$attacks_file" ]; then
        echo "No attack logs found"
        return
    fi
    
    echo "=== ATTACK LOG ANALYSIS ==="
    
    # Total attacks
    local total_attacks
    total_attacks=$(jq '. | length' "$attacks_file" 2>/dev/null || echo "0")
    echo "Total attacks recorded: $total_attacks"
    
    if [ "$total_attacks" -gt 0 ]; then
        # Most targeted files
        echo
        echo "Most targeted files:"
        jq -r '.[].filename' "$attacks_file" 2>/dev/null | sort | uniq -c | sort -nr | head -5
        
        # Attack types
        echo
        echo "Attack types:"
        jq -r '.[].event_type' "$attacks_file" 2>/dev/null | sort | uniq -c | sort -nr
        
        # Recent attacks (last 24 hours)
        echo
        echo "Recent attacks (last 24 hours):"
        local yesterday
        yesterday=$(date -d '1 day ago' -u +%Y-%m-%dT%H:%M:%S)
        jq --arg since "$yesterday" '[.[] | select(.timestamp > $since)] | length' "$attacks_file" 2>/dev/null || echo "0"
        
        # Top processes
        echo
        echo "Top attacking processes:"
        jq -r '.[].process_name' "$attacks_file" 2>/dev/null | sort | uniq -c | sort -nr | head -5
    fi
    
    echo
}

# Function to analyze system status
analyze_system_status() {
    local status_file="$INSTALL_DIR/logs/system_status.json"
    
    if [ ! -f "$status_file" ]; then
        echo "No system status found"
        return
    fi
    
    echo "=== SYSTEM STATUS ANALYSIS ==="
    
    # Current status
    local current_status
    current_status=$(jq -r '.status' "$status_file" 2>/dev/null || echo "Unknown")
    echo "Current status: $current_status"
    
    # Total attacks
    local total_attacks
    total_attacks=$(jq -r '.total_attacks' "$status_file" 2>/dev/null || echo "0")
    echo "Total attacks: $total_attacks"
    
    # Uptime
    local uptime_seconds
    uptime_seconds=$(jq -r '.uptime_seconds' "$status_file" 2>/dev/null || echo "0")
    local uptime_hours=$((uptime_seconds / 3600))
    local uptime_days=$((uptime_hours / 24))
    echo "System uptime: ${uptime_days} days, $((uptime_hours % 24)) hours"
    
    # Monitoring status
    local monitoring_active
    monitoring_active=$(jq -r '.monitoring_active' "$status_file" 2>/dev/null || echo "false")
    echo "Monitoring active: $monitoring_active"
    
    # Last attack
    local last_attack
    last_attack=$(jq -r '.last_attack' "$status_file" 2>/dev/null || echo "null")
    if [ "$last_attack" != "null" ]; then
        echo "Last attack: $last_attack"
    else
        echo "Last attack: None"
    fi
    
    echo
}

# Function to analyze service logs
analyze_service_logs() {
    echo "=== SERVICE LOG ANALYSIS ==="
    
    # Monitor service errors
    echo "Monitor service errors (last 24 hours):"
    journalctl -u honey-token-monitor.service --since "24 hours ago" --no-pager | grep -i error | wc -l
    
    # Dashboard service errors
    echo "Dashboard service errors (last 24 hours):"
    journalctl -u honey-token-dashboard.service --since "24 hours ago" --no-pager | grep -i error | wc -l
    
    # Service restarts
    echo "Monitor service restarts (last 7 days):"
    journalctl -u honey-token-monitor.service --since "7 days ago" --no-pager | grep -i "started\|stopped" | wc -l
    
    echo "Dashboard service restarts (last 7 days):"
    journalctl -u honey-token-dashboard.service --since "7 days ago" --no-pager | grep -i "started\|stopped" | wc -l
    
    echo
}

# Function to show disk usage
show_disk_usage() {
    echo "=== DISK USAGE ANALYSIS ==="
    
    # Overall disk usage
    echo "Overall disk usage:"
    df -h /
    
    echo
    echo "Project directory usage:"
    du -sh "$INSTALL_DIR" 2>/dev/null || echo "Cannot access project directory"
    
    if [ -d "$INSTALL_DIR/logs" ]; then
        echo
        echo "Logs directory breakdown:"
        du -sh "$INSTALL_DIR/logs"/* 2>/dev/null | sort -hr || echo "No log files found"
    fi
    
    echo
}

# Main function
main() {
    echo "========================================"
    echo "  Honey-Token System Log Analysis"
    echo "========================================"
    echo "Generated: $(date)"
    echo
    
    analyze_system_status
    analyze_attacks
    analyze_service_logs
    show_disk_usage
    
    echo "========================================"
}

# Check if jq is available
if ! command -v jq >/dev/null 2>&1; then
    echo "Warning: jq not found. Installing jq for JSON analysis..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# Run main function
main "$@"
EOF

    chmod +x "$INSTALL_DIR/scripts/analyze_logs.sh"
    print_success "Log analysis script created"
}

# Function to setup cron jobs
setup_cron_jobs() {
    print_status "Setting up cron jobs for automated maintenance..."
    
    # Create temporary cron file
    local temp_cron="/tmp/honey-token-cron"
    
    # Get existing crontab (if any)
    crontab -l 2>/dev/null > "$temp_cron" || echo "# Honey-Token Auditing System Cron Jobs" > "$temp_cron"
    
    # Remove any existing honey-token cron jobs
    grep -v "honey-token" "$temp_cron" > "${temp_cron}.clean" || true
    mv "${temp_cron}.clean" "$temp_cron"
    
    # Add new cron jobs
    cat >> "$temp_cron" <<EOF

# Honey-Token Auditing System Maintenance Jobs
# Disk space monitoring - every 15 minutes
*/15 * * * * $INSTALL_DIR/scripts/disk_space_monitor.sh >/dev/null 2>&1

# System health check - every 5 minutes
*/5 * * * * $INSTALL_DIR/scripts/monitor_system.sh >/dev/null 2>&1

# Log analysis report - daily at 6 AM
0 6 * * * $INSTALL_DIR/scripts/analyze_logs.sh > /var/log/honey-token-daily-report.log 2>&1

# Force log rotation - weekly on Sunday at 2 AM
0 2 * * 0 /usr/sbin/logrotate -f /etc/logrotate.d/honey-token-auditing >/dev/null 2>&1
EOF

    # Install the new crontab
    crontab "$temp_cron"
    rm -f "$temp_cron"
    
    print_success "Cron jobs configured for automated maintenance"
}

# Function to create log management configuration
create_log_config() {
    print_status "Creating log management configuration..."
    
    # Create rsyslog configuration for honey-token logs
    sudo tee /etc/rsyslog.d/50-honey-token.conf > /dev/null <<EOF
# Honey-Token Auditing System Log Configuration

# Separate honey-token service logs
:programname, isequal, "honey-token-monitor" /var/log/honey-token-monitor.log
:programname, isequal, "honey-token-dashboard" /var/log/honey-token-dashboard.log
:programname, isequal, "honey-token-disk-monitor" /var/log/honey-token-disk-monitor.log

# Stop processing these messages
:programname, isequal, "honey-token-monitor" stop
:programname, isequal, "honey-token-dashboard" stop
:programname, isequal, "honey-token-disk-monitor" stop
EOF

    # Restart rsyslog to apply configuration
    sudo systemctl restart rsyslog
    
    print_success "Log management configuration created"
}

# Function to test log rotation
test_log_rotation() {
    print_status "Testing log rotation configuration..."
    
    # Create test log files if they don't exist
    mkdir -p "$INSTALL_DIR/logs"
    
    # Create dummy log files for testing
    echo '{"test": "log entry", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > "$INSTALL_DIR/logs/test_attacks.json"
    echo "Test log entry $(date)" > /var/log/honey-token-test.log
    
    # Test logrotate configuration
    if sudo logrotate -d /etc/logrotate.d/honey-token-auditing; then
        print_success "Log rotation configuration test passed"
        
        # Clean up test files
        rm -f "$INSTALL_DIR/logs/test_attacks.json"
        sudo rm -f /var/log/honey-token-test.log
    else
        print_error "Log rotation configuration test failed"
        return 1
    fi
}

# Main function
main() {
    echo "========================================"
    echo "  Log Rotation & Disk Management Setup"
    echo "========================================"
    echo
    
    # Check if running as correct user
    if [ "$USER" != "ubuntu" ]; then
        print_warning "Script should be run as 'ubuntu' user for proper permissions"
    fi
    
    # Check if project directory exists
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Project directory not found: $INSTALL_DIR"
        print_error "Please run the main deployment script first"
        exit 1
    fi
    
    setup_logrotate
    create_disk_monitor
    create_log_analyzer
    setup_cron_jobs
    create_log_config
    test_log_rotation
    
    print_success "Log rotation and disk management setup completed!"
    echo
    echo "=== SUMMARY ==="
    echo "- Log rotation configured for daily rotation with 30-day retention"
    echo "- Disk space monitoring runs every 15 minutes"
    echo "- System health checks run every 5 minutes"
    echo "- Daily log analysis reports generated at 6 AM"
    echo "- Emergency cleanup triggers at 95% disk usage"
    echo "- Standard cleanup triggers at 85% disk usage"
    echo
    echo "Log files locations:"
    echo "- Application logs: $INSTALL_DIR/logs/"
    echo "- System logs: /var/log/honey-token-*.log"
    echo "- Disk monitor log: /var/log/honey-token-disk-monitor.log"
    echo
    echo "Manual commands:"
    echo "- Analyze logs: $INSTALL_DIR/scripts/analyze_logs.sh"
    echo "- Check disk space: $INSTALL_DIR/scripts/disk_space_monitor.sh"
    echo "- Force log rotation: sudo logrotate -f /etc/logrotate.d/honey-token-auditing"
}

# Run main function
main "$@"