#!/bin/bash

# System Health Monitoring Script for Honey-Token Auditing System
# This script performs comprehensive health checks and automatic recovery

set -e

# Configuration
INSTALL_DIR="/home/ubuntu/honey-token-auditing"
LOG_FILE="/var/log/honey-token-health.log"
MAX_LOG_SIZE=10485760  # 10MB
DISK_THRESHOLD=90      # Percentage
MEMORY_THRESHOLD=90    # Percentage

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Also output to console if running interactively
    if [ -t 1 ]; then
        case "$level" in
            "ERROR")   echo -e "${RED}[ERROR]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}[WARNING]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
            "INFO")    echo -e "${BLUE}[INFO]${NC} $message" ;;
            *)         echo "[$level] $message" ;;
        esac
    fi
}

# Function to rotate log file if too large
rotate_log_file() {
    if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
        # Keep last 500 lines
        tail -n 500 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        log_message "INFO" "Rotated health monitoring log file"
    fi
}

# Function to check service status
check_service_status() {
    local service_name="$1"
    local restart_attempted=false
    
    log_message "INFO" "Checking service: $service_name"
    
    if ! systemctl is-active --quiet "$service_name"; then
        log_message "WARNING" "$service_name is not running"
        
        # Attempt to restart the service
        log_message "INFO" "Attempting to restart $service_name"
        if sudo systemctl restart "$service_name"; then
            sleep 5  # Wait for service to start
            
            if systemctl is-active --quiet "$service_name"; then
                log_message "SUCCESS" "Successfully restarted $service_name"
                restart_attempted=true
            else
                log_message "ERROR" "Failed to restart $service_name"
                return 1
            fi
        else
            log_message "ERROR" "Failed to restart $service_name"
            return 1
        fi
    else
        log_message "INFO" "$service_name is running normally"
    fi
    
    # Check for recent errors in service logs
    local error_count
    error_count=$(journalctl -u "$service_name" --since "5 minutes ago" --no-pager | grep -i error | wc -l)
    
    if [ "$error_count" -gt 0 ]; then
        log_message "WARNING" "$service_name has $error_count recent errors"
        
        # Log the actual errors for debugging
        journalctl -u "$service_name" --since "5 minutes ago" --no-pager | grep -i error | tail -3 | while read -r line; do
            log_message "ERROR" "$service_name error: $line"
        done
    fi
    
    return 0
}

# Function to check system resources
check_system_resources() {
    log_message "INFO" "Checking system resources"
    
    # Check disk space
    local disk_usage
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt "$DISK_THRESHOLD" ]; then
        log_message "WARNING" "High disk usage: ${disk_usage}%"
        
        # Try to clean up old logs
        if [ -d "$INSTALL_DIR/logs" ]; then
            find "$INSTALL_DIR/logs" -name "*.json.*.gz" -mtime +7 -delete 2>/dev/null || true
            log_message "INFO" "Cleaned old compressed log files"
        fi
        
        # Clean old system logs
        find /var/log -name "honey-token-*.log.*" -mtime +7 -delete 2>/dev/null || true
        
        # Check disk usage again
        disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
        log_message "INFO" "Disk usage after cleanup: ${disk_usage}%"
    else
        log_message "INFO" "Disk usage is normal: ${disk_usage}%"
    fi
    
    # Check memory usage
    local memory_usage
    memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$memory_usage" -gt "$MEMORY_THRESHOLD" ]; then
        log_message "WARNING" "High memory usage: ${memory_usage}%"
        
        # Log top memory consumers
        ps aux --sort=-%mem | head -5 | while read -r line; do
            log_message "INFO" "Memory usage: $line"
        done
    else
        log_message "INFO" "Memory usage is normal: ${memory_usage}%"
    fi
    
    # Check load average
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_count
    cpu_count=$(nproc)
    
    # Convert load average to percentage (approximate)
    local load_percentage
    load_percentage=$(echo "$load_avg $cpu_count" | awk '{printf "%.0f", ($1/$2)*100}')
    
    if [ "$load_percentage" -gt 80 ]; then
        log_message "WARNING" "High system load: ${load_avg} (${load_percentage}% of capacity)"
    else
        log_message "INFO" "System load is normal: ${load_avg}"
    fi
}

# Function to check honey token files
check_honey_tokens() {
    log_message "INFO" "Checking honey token files"
    
    if [ ! -d "$INSTALL_DIR" ]; then
        log_message "ERROR" "Project directory not found: $INSTALL_DIR"
        return 1
    fi
    
    cd "$INSTALL_DIR"
    
    # Check if honey token manager exists
    if [ ! -f "honey_token_manager.py" ]; then
        log_message "ERROR" "honey_token_manager.py not found"
        return 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_message "ERROR" "Virtual environment not found"
        return 1
    fi
    
    # Activate virtual environment and check honey tokens
    source venv/bin/activate 2>/dev/null || {
        log_message "ERROR" "Cannot activate virtual environment"
        return 1
    }
    
    # Run honey token verification
    local verification_output
    verification_output=$(python -c "
from honey_token_manager import HoneyTokenManager
import sys
try:
    manager = HoneyTokenManager()
    results = manager.verify_tokens()
    missing = [name for name, exists in results.items() if not exists]
    if missing:
        print('MISSING:' + ','.join(missing))
        manager.create_honey_tokens()
        print('RECREATED')
    else:
        print('OK')
except Exception as e:
    print('ERROR:' + str(e))
    sys.exit(1)
" 2>&1)
    
    if echo "$verification_output" | grep -q "ERROR:"; then
        local error_msg=$(echo "$verification_output" | grep "ERROR:" | sed 's/ERROR://')
        log_message "ERROR" "Honey token verification failed: $error_msg"
        return 1
    elif echo "$verification_output" | grep -q "MISSING:"; then
        local missing_tokens=$(echo "$verification_output" | grep "MISSING:" | sed 's/MISSING://')
        log_message "WARNING" "Missing honey tokens: $missing_tokens"
        
        if echo "$verification_output" | grep -q "RECREATED"; then
            log_message "SUCCESS" "Recreated missing honey tokens"
        else
            log_message "ERROR" "Failed to recreate missing honey tokens"
            return 1
        fi
    else
        log_message "INFO" "All honey tokens are present"
    fi
    
    return 0
}

# Function to check network connectivity
check_network_connectivity() {
    log_message "INFO" "Checking network connectivity"
    
    # Check if dashboard port is accessible locally
    if netstat -tuln 2>/dev/null | grep -q ":5000 "; then
        log_message "INFO" "Dashboard port 5000 is listening"
    else
        log_message "WARNING" "Dashboard port 5000 is not listening"
    fi
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_message "INFO" "Internet connectivity is working"
    else
        log_message "WARNING" "Internet connectivity issues detected"
    fi
    
    # Check EC2 metadata service (if on EC2)
    if curl -s --max-time 2 http://169.254.169.254/latest/meta-data/instance-id >/dev/null 2>&1; then
        log_message "INFO" "EC2 metadata service is accessible"
    else
        log_message "INFO" "Not running on EC2 or metadata service not accessible"
    fi
}

# Function to check application health
check_application_health() {
    log_message "INFO" "Checking application health"
    
    # Check if dashboard is responding
    local dashboard_status
    dashboard_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/status 2>/dev/null || echo "000")
    
    if [ "$dashboard_status" = "200" ]; then
        log_message "SUCCESS" "Dashboard API is responding normally"
    elif [ "$dashboard_status" = "000" ]; then
        log_message "ERROR" "Dashboard API is not accessible"
    else
        log_message "WARNING" "Dashboard API returned status code: $dashboard_status"
    fi
    
    # Check log files
    if [ -d "$INSTALL_DIR/logs" ]; then
        local log_count
        log_count=$(find "$INSTALL_DIR/logs" -name "*.json" -type f | wc -l)
        log_message "INFO" "Found $log_count application log files"
        
        # Check if logs are being written recently
        local recent_logs
        recent_logs=$(find "$INSTALL_DIR/logs" -name "*.json" -type f -mmin -60 | wc -l)
        
        if [ "$recent_logs" -gt 0 ]; then
            log_message "INFO" "Application logs are being updated recently"
        else
            log_message "WARNING" "No recent log updates in the last hour"
        fi
    else
        log_message "WARNING" "Application logs directory not found"
    fi
}

# Function to perform automatic recovery actions
perform_recovery_actions() {
    log_message "INFO" "Performing recovery actions"
    
    local recovery_needed=false
    
    # Check if both services are running
    if ! systemctl is-active --quiet honey-token-monitor.service; then
        log_message "WARNING" "Monitor service is down, attempting recovery"
        recovery_needed=true
    fi
    
    if ! systemctl is-active --quiet honey-token-dashboard.service; then
        log_message "WARNING" "Dashboard service is down, attempting recovery"
        recovery_needed=true
    fi
    
    if [ "$recovery_needed" = true ]; then
        # Wait a moment before recovery
        sleep 2
        
        # Restart services in order
        log_message "INFO" "Starting recovery sequence"
        
        sudo systemctl restart honey-token-monitor.service
        sleep 3
        
        sudo systemctl restart honey-token-dashboard.service
        sleep 3
        
        # Verify recovery
        if systemctl is-active --quiet honey-token-monitor.service && systemctl is-active --quiet honey-token-dashboard.service; then
            log_message "SUCCESS" "Recovery completed successfully"
        else
            log_message "ERROR" "Recovery failed - manual intervention required"
        fi
    fi
}

# Function to generate health summary
generate_health_summary() {
    local summary_file="/tmp/honey-token-health-summary.txt"
    
    {
        echo "Honey-Token System Health Summary"
        echo "Generated: $(date)"
        echo "================================"
        echo
        
        echo "Service Status:"
        systemctl is-active honey-token-monitor.service && echo "  Monitor Service: RUNNING" || echo "  Monitor Service: STOPPED"
        systemctl is-active honey-token-dashboard.service && echo "  Dashboard Service: RUNNING" || echo "  Dashboard Service: STOPPED"
        echo
        
        echo "System Resources:"
        echo "  Disk Usage: $(df / | awk 'NR==2 {print $5}')"
        echo "  Memory Usage: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
        echo "  Load Average: $(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')"
        echo
        
        echo "Application Status:"
        if [ -d "$INSTALL_DIR/logs" ]; then
            echo "  Log Files: $(find "$INSTALL_DIR/logs" -name "*.json" -type f | wc -l)"
            echo "  Recent Activity: $(find "$INSTALL_DIR/logs" -name "*.json" -type f -mmin -60 | wc -l) files updated in last hour"
        fi
        
        if [ -d "$INSTALL_DIR/honey_tokens" ]; then
            echo "  Honey Tokens: $(find "$INSTALL_DIR/honey_tokens" -type f | wc -l) files"
        fi
        echo
        
        echo "Recent Issues (last 24 hours):"
        if [ -f "$LOG_FILE" ]; then
            grep "$(date -d '1 day ago' '+%Y-%m-%d')\|$(date '+%Y-%m-%d')" "$LOG_FILE" | grep -E "WARNING|ERROR" | tail -5 || echo "  No recent issues found"
        else
            echo "  No health log found"
        fi
        
    } > "$summary_file"
    
    # If running interactively, display summary
    if [ -t 1 ]; then
        cat "$summary_file"
    fi
    
    log_message "INFO" "Health summary generated: $summary_file"
}

# Main monitoring function
main() {
    # Rotate log file if needed
    rotate_log_file
    
    log_message "INFO" "Starting system health check"
    
    local overall_status="HEALTHY"
    local issues_found=0
    
    # Perform all health checks
    if ! check_service_status "honey-token-monitor.service"; then
        overall_status="DEGRADED"
        ((issues_found++))
    fi
    
    if ! check_service_status "honey-token-dashboard.service"; then
        overall_status="DEGRADED"
        ((issues_found++))
    fi
    
    check_system_resources
    
    if ! check_honey_tokens; then
        overall_status="DEGRADED"
        ((issues_found++))
    fi
    
    check_network_connectivity
    check_application_health
    
    # Perform recovery if needed
    if [ "$issues_found" -gt 0 ]; then
        perform_recovery_actions
    fi
    
    # Generate summary if running interactively or if there are issues
    if [ -t 1 ] || [ "$issues_found" -gt 0 ]; then
        generate_health_summary
    fi
    
    log_message "INFO" "System health check completed - Status: $overall_status ($issues_found issues found)"
    
    # Exit with appropriate code
    if [ "$overall_status" = "HEALTHY" ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --summary)
        generate_health_summary
        exit 0
        ;;
    --help)
        echo "Usage: $0 [--summary|--help]"
        echo "  --summary  Generate and display health summary only"
        echo "  --help     Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac