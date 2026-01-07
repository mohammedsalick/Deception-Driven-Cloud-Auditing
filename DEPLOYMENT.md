# Honey-Token Auditing System - AWS EC2 Deployment Guide

This guide provides complete instructions for deploying the Honey-Token Auditing System on AWS EC2.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS EC2 Setup](#aws-ec2-setup)
3. [Deployment Process](#deployment-process)
4. [Service Configuration](#service-configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

## Prerequisites

### AWS Account Requirements
- Active AWS account with EC2 access
- Basic understanding of AWS EC2 and Security Groups
- SSH key pair for EC2 access

### Local Requirements
- SSH client (Terminal on macOS/Linux, PuTTY on Windows)
- Basic command line knowledge

## AWS EC2 Setup

### Step 1: Launch EC2 Instance

1. **Login to AWS Console**
   - Navigate to EC2 Dashboard
   - Click "Launch Instance"

2. **Choose AMI**
   - Select "Ubuntu Server 20.04 LTS (HVM), SSD Volume Type"
   - Architecture: 64-bit (x86)

3. **Choose Instance Type**
   - Recommended: t2.micro (Free Tier eligible)
   - Minimum: 1 vCPU, 1 GB RAM
   - For production: t3.small or larger

4. **Configure Instance**
   - Number of instances: 1
   - Network: Default VPC
   - Subnet: Default subnet
   - Auto-assign Public IP: Enable
   - Storage: 8 GB GP2 (minimum)

5. **Configure Security Group**
   - Create new security group: "honey-token-sg"
   - Add rules:
     ```
     SSH (22)    - Source: Your IP address
     Custom TCP (5000) - Source: Your IP address (or 0.0.0.0/0 for public access)
     ```

6. **Launch Instance**
   - Select existing key pair or create new one
   - Download key pair (.pem file) if creating new
   - Launch instance

### Step 2: Connect to Instance

1. **Set Key Permissions** (Linux/macOS)
   ```bash
   chmod 400 your-key.pem
   ```

2. **Connect via SSH**
   ```bash
   ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
   ```

3. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Deployment Process

### Method 1: Automated Deployment (Recommended)

1. **Upload Deployment Script**
   ```bash
   # On your local machine
   scp -i your-key.pem deploy.sh ubuntu@YOUR_EC2_PUBLIC_IP:~/
   ```

2. **Run Deployment Script**
   ```bash
   # On EC2 instance
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Upload Application Files**
   ```bash
   # On your local machine - upload all project files
   scp -i your-key.pem -r * ubuntu@YOUR_EC2_PUBLIC_IP:~/honey-token-auditing/
   ```

### Method 2: Manual Deployment

1. **Create Project Structure**
   ```bash
   mkdir -p ~/honey-token-auditing/{honey_tokens,logs,static,templates,scripts}
   cd ~/honey-token-auditing
   ```

2. **Install System Dependencies**
   ```bash
   sudo apt install -y python3 python3-pip python3-venv curl wget git
   ```

3. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   ```

4. **Install Python Dependencies**
   ```bash
   pip install Flask==2.3.3 Werkzeug==2.3.7 watchdog==3.0.0 psutil==5.9.6 python-dotenv==1.0.0
   ```

5. **Upload Application Files**
   - Upload all Python files, templates, and static files to the project directory

## Service Configuration

### Step 1: Create Systemd Services

1. **Copy Service Files**
   ```bash
   sudo cp systemd/honey-token-monitor.service /etc/systemd/system/
   sudo cp systemd/honey-token-dashboard.service /etc/systemd/system/
   ```

2. **Reload Systemd**
   ```bash
   sudo systemctl daemon-reload
   ```

### Step 2: Configure Environment

1. **Create Environment File**
   ```bash
   # File: .env
   AWS_EC2_PUBLIC_IP=YOUR_EC2_PUBLIC_IP
   AWS_EC2_USER=ubuntu
   FLASK_PORT=5000
   FLASK_ENV=production
   ```

### Step 3: Setup Log Rotation

1. **Run Log Setup Script**
   ```bash
   chmod +x scripts/setup_log_rotation.sh
   ./scripts/setup_log_rotation.sh
   ```

## Starting Services

### Step 1: Enable Services
```bash
sudo systemctl enable honey-token-monitor.service
sudo systemctl enable honey-token-dashboard.service
```

### Step 2: Start Services
```bash
sudo systemctl start honey-token-monitor.service
sudo systemctl start honey-token-dashboard.service
```

### Step 3: Check Status
```bash
sudo systemctl status honey-token-monitor.service
sudo systemctl status honey-token-dashboard.service
```

## Verification

### Step 1: Run Validation Script
```bash
chmod +x scripts/validate_installation.sh
./scripts/validate_installation.sh
```

### Step 2: Check Service Logs
```bash
# Monitor service logs
sudo journalctl -u honey-token-monitor.service -f

# Dashboard service logs
sudo journalctl -u honey-token-dashboard.service -f
```

### Step 3: Access Dashboard
1. Open browser and navigate to: `http://YOUR_EC2_PUBLIC_IP:5000`
2. Verify dashboard loads and shows "SAFE" status
3. Test "Simulate Attack" functionality
4. Check that attacks are detected and logged

### Step 4: Test Honey Tokens
```bash
# Test file access detection
cat honey_tokens/passwords.txt

# Check if attack was logged
tail -f logs/attacks.json
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start
```bash
# Check service status
sudo systemctl status honey-token-monitor.service

# Check logs for errors
sudo journalctl -u honey-token-monitor.service --no-pager -l

# Common fixes:
# - Check file permissions
# - Verify Python dependencies
# - Check virtual environment path
```

#### 2. Dashboard Not Accessible
```bash
# Check if service is running
sudo systemctl status honey-token-dashboard.service

# Check if port is open
sudo netstat -tlnp | grep :5000

# Check Security Group settings in AWS Console
# Ensure port 5000 is allowed from your IP
```

#### 3. Honey Tokens Not Created
```bash
# Manually create honey tokens
cd ~/honey-token-auditing
source venv/bin/activate
python honey_token_manager.py

# Check permissions
ls -la honey_tokens/
```

#### 4. File Monitoring Not Working
```bash
# Check if watchdog is installed
pip show watchdog

# Test file monitoring manually
python monitor_service.py

# Check file permissions
ls -la honey_tokens/
```

### Log Locations
- Application logs: `~/honey-token-auditing/logs/`
- System logs: `/var/log/honey-token-*.log`
- Service logs: `sudo journalctl -u honey-token-*`

## Maintenance

### Daily Tasks
- Check dashboard status
- Review attack logs
- Monitor disk space

### Weekly Tasks
- Review service logs for errors
- Check system resource usage
- Verify honey tokens exist

### Monthly Tasks
- Update system packages
- Review and archive old logs
- Check security group settings

### Automated Maintenance
The system includes automated maintenance scripts:

1. **Disk Space Monitoring** (every 15 minutes)
   - Monitors disk usage
   - Cleans old logs when space is low
   - Sends alerts for critical usage

2. **Health Checks** (every 5 minutes)
   - Monitors service status
   - Restarts failed services
   - Verifies honey tokens

3. **Log Rotation** (daily)
   - Rotates application logs
   - Compresses old logs
   - Maintains 30-day retention

### Manual Commands

```bash
# Analyze system logs
~/honey-token-auditing/scripts/analyze_logs.sh

# Check disk space
~/honey-token-auditing/scripts/disk_space_monitor.sh

# Restart services
sudo systemctl restart honey-token-monitor.service
sudo systemctl restart honey-token-dashboard.service

# View real-time logs
sudo journalctl -u honey-token-monitor.service -f

# Force log rotation
sudo logrotate -f /etc/logrotate.d/honey-token-auditing
```

## Security Considerations

### Network Security
- Restrict Security Group access to your IP only
- Consider using VPN for production access
- Enable AWS CloudTrail for audit logging

### System Security
- Keep system packages updated
- Monitor for unauthorized access
- Use strong SSH keys
- Consider disabling password authentication

### Application Security
- Monitor honey token access patterns
- Review attack logs regularly
- Set up alerting for critical events
- Backup configuration and logs

## Performance Optimization

### For Production Use
1. **Upgrade Instance Type**
   - Use t3.small or larger
   - Add more storage if needed

2. **Database Backend**
   - Consider using RDS for log storage
   - Implement log aggregation

3. **Load Balancing**
   - Use Application Load Balancer
   - Deploy multiple instances

4. **Monitoring**
   - Set up CloudWatch monitoring
   - Configure SNS alerts

## Backup and Recovery

### Backup Strategy
```bash
# Backup configuration and logs
tar -czf honey-token-backup-$(date +%Y%m%d).tar.gz \
  ~/honey-token-auditing/{.env,logs/,honey_tokens/}

# Upload to S3 (optional)
aws s3 cp honey-token-backup-*.tar.gz s3://your-backup-bucket/
```

### Recovery Process
1. Launch new EC2 instance
2. Run deployment script
3. Restore configuration and logs from backup
4. Start services

## Support and Documentation

### Additional Resources
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Watchdog Documentation](https://python-watchdog.readthedocs.io/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)

### Getting Help
- Check service logs first
- Run validation script
- Review this documentation
- Check AWS EC2 console for instance health

---

**Note**: This deployment guide assumes basic familiarity with AWS EC2 and Linux command line. For production deployments, consider additional security hardening and monitoring solutions.