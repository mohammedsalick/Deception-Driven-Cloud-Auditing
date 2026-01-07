#!/bin/bash

# Installation Validation Script for Honey-Token Auditing System
# This script validates that all components are properly installed and configured

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

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNING_CHECKS++))
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

# Function to run a validation check
run_check() {
    local check_name="$1"
    local check_command="$2"
    local error_message="$3"
    
    ((TOTAL_CHECKS++))
    print_status "Checking: $check_name"
    
    if eval "$check_command" >/dev/null 2>&1; then
        print_success "$check_name"
        return 0
    else
        print_error "$check_name - $error_message"
        return 1
    fi
}

# Function to run a validation check with warning
run_check_warn() {
    local check_name="$1"
    local check_command="$2"
    local warning_message="$3"
    
    ((TOTAL_CHECKS++))
    print_status "Checking: $check_name"
    
    if eval "$check_command" >/dev/null 2>&1; then
        print_success "$check_name"
        return 0
    else
        print_warning "$check_name - $warning_message"
        return 1
    fi
}

# System Requirements Validation
validate_system_requirements() {
    echo "=== SYSTEM REQUIREMENTS VALIDATION ==="
    
    # Check operating system
    run_check "Ubuntu Operating System" \
        "grep -q 'Ubuntu' /etc/os-release" \
        "Not running on Ubuntu (may still work)"
    
    # Check user
    run_check_warn "Running as ubuntu user" \
        "[ \"\$USER\" = \"ubuntu\" ]" \
        "Not running as ubuntu user (may cause permission issues)"
    
    # Check disk space (minimum 1GB free)
    run_check "Sufficient disk space (>1GB)" \
        "[ \$(df / | awk 'NR==2 {print \$4}') -gt 1048576 ]" \
        "Less than 1GB free disk space"
    
    # Check memory (minimum 512MB)
    run_check "Sufficient memory (>512MB)" \
        "[ \$(free -m | awk 'NR==2{print \$2}') -gt 512 ]" \
        "Less than 512MB total memory"
    
    echo
}

# System Dependencies Validation
validate_system_dependencies() {
    echo "=== SYSTEM DEPENDENCIES VALIDATION ==="
    
    # Check Python 3
    run_check "Python 3 installed" \
        "command -v python3" \
        "Python 3 not found"
    
    # Check pip
    run_check "pip installed" \
        "command -v pip3 || command -v pip" \
        "pip not found"
    
    # Check systemctl
    run_check "systemctl available" \
        "command -v systemctl" \
        "systemctl not found (systemd required)"
    
    # Check curl
    run_check "curl installed" \
        "command -v curl" \
        "curl not found"
    
    # Check cron
    run_check "cron service available" \
        "systemctl is-enabled cron || systemctl is-enabled crond" \
        "cron service not available"
    
    echo
}

# Project Structure Validation
validate_project_structure() {
    echo "=== PROJECT STRUCTURE VALIDATION ==="
    
    # Check main directory
    run_check "Project directory exists" \
        "[ -d \"$INSTALL_DIR\" ]" \
        "Project directory not found: $INSTALL_DIR"
    
    # Check subdirectories
    for dir in honey_tokens logs static templates scripts; do
        run_check "Directory: $dir" \
            "[ -d \"$INSTALL_DIR/$dir\" ]" \
            "Directory not found: $INSTALL_DIR/$dir"
    done
    
    # Check virtual environment
    run_check "Virtual environment exists" \
        "[ -d \"$INSTALL_DIR/venv\" ]" \
        "Virtual environment not found"
    
    # Check environment file
    run_check "Environment file exists" \
        "[ -f \"$INSTALL_DIR/.env\" ]" \
        "Environment file not found"
    
    echo
}

# Application Files Validation
validate_application_files() {
    echo "=== APPLICATION FILES VALIDATION ==="
    
    # Check main Python files
    for file in app.py monitor_service.py honey_token_manager.py audit_logger.py; do
        run_check "Application file: $file" \
            "[ -f \"$INSTALL_DIR/$file\" ]" \
            "Application file not found: $file"
    done
    
    # Check template files
    run_check "Dashboard template" \
        "[ -f \"$INSTALL_DIR/templates/dashboard.html\" ]" \
        "Dashboard template not found"
    
    # Check static files
    for file in dashboard.css dashboard.js; do
        run_check "Static file: $file" \
            "[ -f \"$INSTALL_DIR/static/$file\" ]" \
            "Static file not found: $file"
    done
    
    # Check requirements file
    run_check "Requirements file" \
        "[ -f \"$INSTALL_DIR/requirements.txt\" ]" \
        "Requirements file not found"
    
    echo
}

# Python Dependencies Validation
validate_python_dependencies() {
    echo "=== PYTHON DEPENDENCIES VALIDATION ==="
    
    # Activate virtual environment
    if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
        cd "$INSTALL_DIR"
        source venv/bin/activate
        
        # Check required packages
        for package in flask watchdog psutil python-dotenv werkzeug; do
            run_check "Python package: $package" \
                "pip show \"$package\"" \
                "Python package not installed: $package"
        done
        
        # Check Python version
        run_check "Python version (>=3.6)" \
            "python -c 'import sys; exit(0 if sys.version_info >= (3, 6) else 1)'" \
            "Python version too old (requires 3.6+)"
        
    else
        print_error "Cannot activate virtual environment"
        ((FAILED_CHECKS++))
    fi
    
    echo
}

# Service Configuration Validation
validate_service_configuration() {
    echo "=== SERVICE CONFIGURATION VALIDATION ==="
    
    # Check systemd service files
    run_check "Monitor service file" \
        "[ -f \"/etc/systemd/system/honey-token-monitor.service\" ]" \
        "Monitor service file not found"
    
    run_check "Dashboard service file" \
        "[ -f \"/etc/systemd/system/honey-token-dashboard.service\" ]" \
        "Dashboard service file not found"
    
    # Check if services are enabled
    run_check_warn "Monitor service enabled" \
        "systemctl is-enabled honey-token-monitor.service" \
        "Monitor service not enabled for auto-start"
    
    run_check_warn "Dashboard service enabled" \
        "systemctl is-enabled honey-token-dashboard.service" \
        "Dashboard service not enabled for auto-start"
    
    # Check log rotation
    run_check "Log rotation configured" \
        "[ -f \"/etc/logrotate.d/honey-token-auditing\" ]" \
        "Log rotation not configured"
    
    echo
}

# Network Configuration Validation
validate_network_configuration() {
    echo "=== NETWORK CONFIGURATION VALIDATION ==="
    
    # Check if port 5000 is available
    run_check_warn "Port 5000 available" \
        "! netstat -tuln 2>/dev/null | grep -q ':5000 '" \
        "Port 5000 may be in use"
    
    # Check firewall status
    if command -v ufw >/dev/null 2>&1; then
        run_check_warn "UFW firewall configured" \
            "ufw status | grep -q '5000'" \
            "Port 5000 not allowed in firewall"
    fi
    
    # Check EC2 metadata access (if on EC2)
    run_check_warn "EC2 metadata accessible" \
        "curl -s --max-time 2 http://169.254.169.254/latest/meta-data/instance-id" \
        "Not running on EC2 or metadata not accessible"
    
    echo
}

# Honey Token Validation
validate_honey_tokens() {
    echo "=== HONEY TOKEN VALIDATION ==="
    
    if [ -f "$INSTALL_DIR/honey_token_manager.py" ] && [ -d "$INSTALL_DIR/venv" ]; then
        cd "$INSTALL_DIR"
        source venv/bin/activate
        
        # Test honey token creation
        run_check "Honey token creation test" \
            "python -c 'from honey_token_manager import HoneyTokenManager; m = HoneyTokenManager(); m.create_honey_tokens()'" \
            "Failed to create honey tokens"
        
        # Check if honey token files exist
        for file in passwords.txt api_keys.json database_backup.sql config.env ssh_keys.txt; do
            run_check "Honey token file: $file" \
                "[ -f \"$INSTALL_DIR/honey_tokens/$file\" ]" \
                "Honey token file not found: $file"
        done
        
    else
        print_error "Cannot test honey tokens - missing files or virtual environment"
        ((FAILED_CHECKS++))
    fi
    
    echo
}

# Service Status Validation
validate_service_status() {
    echo "=== SERVICE STATUS VALIDATION ==="
    
    # Check if services are running
    run_check_warn "Monitor service running" \
        "systemctl is-active --quiet honey-token-monitor.service" \
        "Monitor service not running (use 'sudo systemctl start honey-token-monitor.service')"
    
    run_check_warn "Dashboard service running" \
        "systemctl is-active --quiet honey-token-dashboard.service" \
        "Dashboard service not running (use 'sudo systemctl start honey-token-dashboard.service')"
    
    # Check service logs for errors
    if systemctl is-active --quiet honey-token-monitor.service; then
        run_check_warn "Monitor service healthy" \
            "! journalctl -u honey-token-monitor.service --since '5 minutes ago' | grep -i error" \
            "Recent errors found in monitor service logs"
    fi
    
    if systemctl is-active --quiet honey-token-dashboard.service; then
        run_check_warn "Dashboard service healthy" \
            "! journalctl -u honey-token-dashboard.service --since '5 minutes ago' | grep -i error" \
            "Recent errors found in dashboard service logs"
    fi
    
    echo
}

# Permissions Validation
validate_permissions() {
    echo "=== PERMISSIONS VALIDATION ==="
    
    # Check directory permissions
    run_check "Project directory readable" \
        "[ -r \"$INSTALL_DIR\" ]" \
        "Project directory not readable"
    
    run_check "Project directory writable" \
        "[ -w \"$INSTALL_DIR\" ]" \
        "Project directory not writable"
    
    # Check log directory permissions
    run_check "Logs directory writable" \
        "[ -w \"$INSTALL_DIR/logs\" ]" \
        "Logs directory not writable"
    
    # Check honey tokens directory permissions
    run_check "Honey tokens directory writable" \
        "[ -w \"$INSTALL_DIR/honey_tokens\" ]" \
        "Honey tokens directory not writable"
    
    echo
}

# Generate validation report
generate_report() {
    echo "========================================"
    echo "         VALIDATION REPORT"
    echo "========================================"
    echo
    echo "Total Checks: $TOTAL_CHECKS"
    echo "Passed: $PASSED_CHECKS"
    echo "Warnings: $WARNING_CHECKS"
    echo "Failed: $FAILED_CHECKS"
    echo
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        if [ $WARNING_CHECKS -eq 0 ]; then
            print_success "All validation checks passed!"
            echo
            echo "Your honey-token auditing system is properly installed and configured."
            echo "You can start the services with:"
            echo "  sudo systemctl start honey-token-monitor.service"
            echo "  sudo systemctl start honey-token-dashboard.service"
            echo
            PUBLIC_IP=$(curl -s --max-time 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_PUBLIC_IP")
            echo "Dashboard will be available at: http://$PUBLIC_IP:5000"
        else
            print_warning "Validation completed with $WARNING_CHECKS warnings."
            echo
            echo "The system should work but may have some issues."
            echo "Please review the warnings above."
        fi
        return 0
    else
        print_error "Validation failed with $FAILED_CHECKS critical errors."
        echo
        echo "Please fix the errors above before starting the services."
        return 1
    fi
}

# Main validation function
main() {
    echo "========================================"
    echo "  Honey-Token System Validation"
    echo "========================================"
    echo
    
    validate_system_requirements
    validate_system_dependencies
    validate_project_structure
    validate_application_files
    validate_python_dependencies
    validate_service_configuration
    validate_network_configuration
    validate_honey_tokens
    validate_service_status
    validate_permissions
    
    generate_report
}

# Run main function
main "$@"