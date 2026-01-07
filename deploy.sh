#!/bin/bash

# Honey-Token Auditing System - AWS EC2 Deployment Script
# This script automates the deployment of the honey-token system on AWS EC2

set -e  # Exit on any error

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
PYTHON_VERSION="3.8"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_system_requirements() {
    print_status "Checking system requirements..."
    
    # Check if running on Ubuntu
    if ! grep -q "Ubuntu" /etc/os-release; then
        print_warning "This script is designed for Ubuntu. Proceeding anyway..."
    fi
    
    # Check if running as ubuntu user
    if [ "$USER" != "ubuntu" ]; then
        print_warning "Script should be run as 'ubuntu' user. Current user: $USER"
    fi
    
    # Check available disk space (minimum 1GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then
        print_error "Insufficient disk space. At least 1GB required."
        exit 1
    fi
    
    print_success "System requirements check completed"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt-get update -y
    
    # Install Python and pip if not present
    if ! command_exists python3; then
        print_status "Installing Python 3..."
        sudo apt-get install -y python3 python3-pip python3-venv
    else
        print_success "Python 3 already installed"
    fi
    
    # Install additional system packages
    sudo apt-get install -y \
        curl \
        wget \
        git \
        htop \
        logrotate \
        systemd \
        cron
    
    print_success "System dependencies installed"
}

# Function to create project directory structure
create_project_structure() {
    print_status "Creating project directory structure..."
    
    # Create main project directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Create subdirectories
    mkdir -p honey_tokens
    mkdir -p logs
    mkdir -p static
    mkdir -p templates
    mkdir -p scripts
    mkdir -p config
    
    # Set proper permissions
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR/honey_tokens"
    chmod 755 "$INSTALL_DIR/logs"
    
    print_success "Project directory structure created"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    pip install Flask==2.3.3
    pip install Werkzeug==2.3.7
    pip install watchdog==3.0.0
    pip install psutil==5.9.6
    pip install python-dotenv==1.0.0
    
    # Create requirements.txt for reference
    pip freeze > requirements.txt
    
    print_success "Python dependencies installed"
}

# Function to copy application files
copy_application_files() {
    print_status "Copying application files..."
    
    # Note: In a real deployment, these files would be copied from the source
    # For this script, we assume they're already present or will be uploaded separately
    
    if [ ! -f "$INSTALL_DIR/app.py" ]; then
        print_warning "Application files not found. Please upload the following files to $INSTALL_DIR:"
        echo "  - app.py"
        echo "  - monitor_service.py"
        echo "  - honey_token_manager.py"
        echo "  - audit_logger.py"
        echo "  - templates/dashboard.html"
        echo "  - static/dashboard.css"
        echo "  - static/dashboard.js"
    else
        print_success "Application files found"
    fi
}

# Function to create systemd service files
create_systemd_services() {
    print_status "Creating systemd service files..."
    
    # Create honey-token monitoring service
    sudo tee /etc/systemd/system/honey-token-monitor.service > /dev/null <<EOF
[Unit]
Description=Honey Token Monitoring Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python monitor_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=honey-token-monitor

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create web dashboard service
    sudo tee /etc/systemd/system/honey-token-dashboard.service > /dev/null <<EOF
[Unit]
Description=Honey Token Web Dashboard
After=network.target honey-token-monitor.service
Wants=network.target
Requires=honey-token-monitor.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
Environment=FLASK_ENV=production
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=honey-token-dashboard

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload
    
    print_success "Systemd service files created"
}

# Function to setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/honey-token-auditing > /dev/null <<EOF
$INSTALL_DIR/logs/*.json {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload honey-token-monitor.service > /dev/null 2>&1 || true
        systemctl reload honey-token-dashboard.service > /dev/null 2>&1 || true
    endscript
}

/var/log/honey-token-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
}
EOF

    print_success "Log rotation configured"
}

# Function to create environment configuration
create_environment_config() {
    print_status "Creating environment configuration..."
    
    cd "$INSTALL_DIR"
    
    # Get EC2 instance metadata
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")
    PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "127.0.0.1")
    
    # Create .env file
    cat > .env <<EOF
# AWS EC2 Instance Configuration
AWS_EC2_INSTANCE_ID=$INSTANCE_ID
AWS_EC2_PUBLIC_IP=$PUBLIC_IP
AWS_EC2_PRIVATE_IP=$PRIVATE_IP
AWS_EC2_USER=ubuntu

# Application Settings
FLASK_PORT=5000
FLASK_ENV=production
MONITOR_INTERVAL=1
LOG_LEVEL=INFO

# Installation Paths
INSTALL_DIR=$INSTALL_DIR
HONEY_TOKENS_DIR=$INSTALL_DIR/honey_tokens
LOGS_DIR=$INSTALL_DIR/logs

# Service Configuration
SERVICE_USER=$SERVICE_USER
PYTHON_PATH=$INSTALL_DIR/venv/bin/python
EOF

    chmod 600 .env
    
    print_success "Environment configuration created"
}

# Function to initialize honey tokens
initialize_honey_tokens() {
    print_status "Initializing honey tokens..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Run honey token initialization
    if [ -f "honey_token_manager.py" ]; then
        python honey_token_manager.py
        print_success "Honey tokens initialized"
    else
        print_warning "honey_token_manager.py not found. Honey tokens will be created on first run."
    fi
}

# Function to setup firewall rules
setup_firewall() {
    print_status "Setting up firewall rules..."
    
    # Check if ufw is available
    if command_exists ufw; then
        # Allow SSH (port 22)
        sudo ufw allow 22/tcp
        
        # Allow HTTP (port 5000 for Flask)
        sudo ufw allow 5000/tcp
        
        # Enable firewall if not already enabled
        sudo ufw --force enable
        
        print_success "Firewall rules configured"
    else
        print_warning "UFW not available. Please configure firewall manually."
        print_warning "Required ports: 22 (SSH), 5000 (HTTP)"
    fi
}

# Function to create startup script
create_startup_script() {
    print_status "Creating startup script..."
    
    cat > "$INSTALL_DIR/scripts/start_services.sh" <<'EOF'
#!/bin/bash

# Honey-Token Auditing System - Service Startup Script

INSTALL_DIR="/home/ubuntu/honey-token-auditing"
cd "$INSTALL_DIR"

echo "Starting Honey-Token Auditing System..."

# Enable and start services
sudo systemctl enable honey-token-monitor.service
sudo systemctl enable honey-token-dashboard.service

sudo systemctl start honey-token-monitor.service
sudo systemctl start honey-token-dashboard.service

# Check service status
echo "Service Status:"
sudo systemctl status honey-token-monitor.service --no-pager -l
sudo systemctl status honey-token-dashboard.service --no-pager -l

echo "Services started. Dashboard available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
EOF

    chmod +x "$INSTALL_DIR/scripts/start_services.sh"
    
    print_success "Startup script created"
}

# Function to create monitoring script
create_monitoring_script() {
    print_status "Creating system monitoring script..."
    
    cat > "$INSTALL_DIR/scripts/monitor_system.sh" <<'EOF'
#!/bin/bash

# System Health Monitoring Script for Honey-Token Auditing System

INSTALL_DIR="/home/ubuntu/honey-token-auditing"
LOG_FILE="/var/log/honey-token-health.log"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check service status
check_services() {
    if ! systemctl is-active --quiet honey-token-monitor.service; then
        log_message "WARNING: honey-token-monitor.service is not running"
        sudo systemctl restart honey-token-monitor.service
        log_message "INFO: Restarted honey-token-monitor.service"
    fi
    
    if ! systemctl is-active --quiet honey-token-dashboard.service; then
        log_message "WARNING: honey-token-dashboard.service is not running"
        sudo systemctl restart honey-token-dashboard.service
        log_message "INFO: Restarted honey-token-dashboard.service"
    fi
}

# Check disk space
check_disk_space() {
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        log_message "WARNING: Disk usage is ${DISK_USAGE}%"
        # Clean old logs
        find "$INSTALL_DIR/logs" -name "*.json.gz" -mtime +30 -delete
        log_message "INFO: Cleaned old log files"
    fi
}

# Check honey token files
check_honey_tokens() {
    cd "$INSTALL_DIR"
    if [ -f "honey_token_manager.py" ]; then
        source venv/bin/activate
        python -c "
from honey_token_manager import HoneyTokenManager
manager = HoneyTokenManager()
results = manager.verify_tokens()
missing = [name for name, exists in results.items() if not exists]
if missing:
    print('Missing honey tokens:', missing)
    manager.create_honey_tokens()
    print('Recreated missing tokens')
"
    fi
}

# Main monitoring function
main() {
    log_message "INFO: Starting system health check"
    check_services
    check_disk_space
    check_honey_tokens
    log_message "INFO: System health check completed"
}

main
EOF

    chmod +x "$INSTALL_DIR/scripts/monitor_system.sh"
    
    # Add to crontab for regular monitoring
    (crontab -l 2>/dev/null; echo "*/5 * * * * $INSTALL_DIR/scripts/monitor_system.sh") | crontab -
    
    print_success "System monitoring script created and scheduled"
}

# Function to validate installation
validate_installation() {
    print_status "Validating installation..."
    
    local errors=0
    
    # Check if project directory exists
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Project directory not found: $INSTALL_DIR"
        ((errors++))
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        print_error "Virtual environment not found"
        ((errors++))
    fi
    
    # Check if Python packages are installed
    cd "$INSTALL_DIR"
    source venv/bin/activate 2>/dev/null || {
        print_error "Cannot activate virtual environment"
        ((errors++))
    }
    
    # Check required Python packages
    for package in flask watchdog psutil python-dotenv; do
        if ! pip show "$package" >/dev/null 2>&1; then
            print_error "Python package not installed: $package"
            ((errors++))
        fi
    done
    
    # Check systemd service files
    if [ ! -f "/etc/systemd/system/honey-token-monitor.service" ]; then
        print_error "Monitor service file not found"
        ((errors++))
    fi
    
    if [ ! -f "/etc/systemd/system/honey-token-dashboard.service" ]; then
        print_error "Dashboard service file not found"
        ((errors++))
    fi
    
    # Check log rotation configuration
    if [ ! -f "/etc/logrotate.d/honey-token-auditing" ]; then
        print_error "Log rotation configuration not found"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        print_success "Installation validation passed"
        return 0
    else
        print_error "Installation validation failed with $errors errors"
        return 1
    fi
}

# Function to display post-installation instructions
show_post_install_instructions() {
    print_success "Deployment completed successfully!"
    echo
    echo "=== POST-INSTALLATION INSTRUCTIONS ==="
    echo
    echo "1. Upload your application files to: $INSTALL_DIR"
    echo "   Required files:"
    echo "   - app.py"
    echo "   - monitor_service.py"
    echo "   - honey_token_manager.py"
    echo "   - audit_logger.py"
    echo "   - templates/dashboard.html"
    echo "   - static/dashboard.css"
    echo "   - static/dashboard.js"
    echo
    echo "2. Start the services:"
    echo "   sudo systemctl start honey-token-monitor.service"
    echo "   sudo systemctl start honey-token-dashboard.service"
    echo
    echo "3. Enable services for auto-start:"
    echo "   sudo systemctl enable honey-token-monitor.service"
    echo "   sudo systemctl enable honey-token-dashboard.service"
    echo
    echo "4. Check service status:"
    echo "   sudo systemctl status honey-token-monitor.service"
    echo "   sudo systemctl status honey-token-dashboard.service"
    echo
    echo "5. Access the dashboard:"
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_PUBLIC_IP")
    echo "   http://$PUBLIC_IP:5000"
    echo
    echo "6. View logs:"
    echo "   sudo journalctl -u honey-token-monitor.service -f"
    echo "   sudo journalctl -u honey-token-dashboard.service -f"
    echo
    echo "=== SECURITY NOTES ==="
    echo "- Ensure your EC2 Security Group allows inbound traffic on port 5000"
    echo "- Consider setting up HTTPS with SSL certificates for production"
    echo "- Regularly monitor the system logs and health status"
    echo "- The system monitoring script runs every 5 minutes via cron"
    echo
}

# Main deployment function
main() {
    echo "========================================"
    echo "  Honey-Token Auditing System Deployment"
    echo "========================================"
    echo
    
    check_system_requirements
    install_system_dependencies
    create_project_structure
    install_python_dependencies
    copy_application_files
    create_systemd_services
    setup_log_rotation
    create_environment_config
    initialize_honey_tokens
    setup_firewall
    create_startup_script
    create_monitoring_script
    
    if validate_installation; then
        show_post_install_instructions
    else
        print_error "Deployment completed with errors. Please review the output above."
        exit 1
    fi
}

# Run main function
main "$@"