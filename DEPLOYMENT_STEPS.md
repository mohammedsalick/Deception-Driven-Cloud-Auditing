# 🚀 EC2 Deployment Steps - Quick Guide

## Current Status
✅ EC2 Instance Created (t2g.micro, Ubuntu)  
✅ SSH Access Configured (.pem file ready)  
⏳ Project Deployment (Next Step)

---

## Recommended Approach: **GitHub + Direct Upload (Hybrid)**

### Why GitHub?
- ✅ Version control and easy updates
- ✅ Professional deployment practice
- ✅ Easy rollback if needed
- ✅ Can share with team/collaborators

### Why Also Direct Upload?
- ✅ Faster initial setup
- ✅ No need to set up Git on EC2 initially
- ✅ Can test immediately

---

## Option 1: GitHub Deployment (Recommended for Production)

### Step 1: Initialize Git Repository (Local)
```bash
# In your project directory
git init
git add .
git commit -m "Initial commit - Honey Token Auditing System"
```

### Step 2: Create GitHub Repository
1. Go to GitHub.com
2. Create a new repository (name it `honey-token-auditing` or similar)
3. **DO NOT** initialize with README (you already have files)

### Step 3: Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/honey-token-auditing.git
git branch -M main
git push -u origin main
```

### Step 4: Clone on EC2
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# On EC2, install Git
sudo apt update
sudo apt install git -y

# Clone your repository
cd ~
git clone https://github.com/YOUR_USERNAME/honey-token-auditing.git
cd honey-token-auditing
```

### Step 5: Run Deployment Script
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment (this will install everything)
./deploy.sh
```

---

## Option 2: Direct SCP Upload (Faster for Testing)

### Step 1: Upload Project Files to EC2
```bash
# From your local machine (Windows PowerShell)
# Navigate to your project directory first
cd C:\Users\mhmmd\OneDrive\Desktop\Projectss\ISM

# Upload entire project (excluding __pycache__)
scp -i your-key.pem -r ^
    --exclude=__pycache__ ^
    --exclude=*.pyc ^
    . ubuntu@YOUR_EC2_IP:~/honey-token-auditing/
```

**Or use WinSCP/Rsync for easier file transfer on Windows**

### Step 2: SSH into EC2 and Deploy
```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Navigate to project
cd ~/honey-token-auditing

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

---

## Option 3: Manual Setup (If deploy.sh doesn't work)

### Step 1: Install System Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl wget
```

### Step 2: Create Virtual Environment
```bash
cd ~/honey-token-auditing
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Create .env File
```bash
# Create .env file
cat > .env <<EOF
# AWS EC2 Instance Configuration
AWS_EC2_PUBLIC_IP=YOUR_EC2_PUBLIC_IP
AWS_EC2_USER=ubuntu

# Application Settings
FLASK_PORT=5000
FLASK_ENV=production
MONITOR_INTERVAL=1
LOG_LEVEL=INFO
EOF

chmod 600 .env
```

### Step 5: Initialize Honey Tokens
```bash
python honey_token_manager.py
```

### Step 6: Test Run
```bash
# Test the application
python app.py
```

---

## Configure EC2 Security Group

**IMPORTANT:** Before accessing the dashboard, configure your EC2 Security Group:

1. Go to AWS Console → EC2 → Security Groups
2. Select your instance's security group
3. Add Inbound Rule:
   - **Type:** Custom TCP
   - **Port:** 5000
   - **Source:** Your IP address (or 0.0.0.0/0 for testing - **NOT recommended for production**)
   - **Description:** Flask Dashboard

---

## Start the Services

### Option A: Run Manually (For Testing)
```bash
cd ~/honey-token-auditing
source venv/bin/activate
python app.py
```

### Option B: Use Systemd Services (For Production)
```bash
# Copy service files
sudo cp systemd/honey-token-monitor.service /etc/systemd/system/
sudo cp systemd/honey-token-dashboard.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable honey-token-monitor.service
sudo systemctl enable honey-token-dashboard.service
sudo systemctl start honey-token-monitor.service
sudo systemctl start honey-token-dashboard.service

# Check status
sudo systemctl status honey-token-dashboard.service
```

---

## Access Your Dashboard

1. Get your EC2 public IP:
   ```bash
   curl http://169.254.169.254/latest/meta-data/public-ipv4
   ```

2. Open in browser:
   ```
   http://YOUR_EC2_PUBLIC_IP:5000
   ```

---

## Verify Installation

```bash
# Check if services are running
sudo systemctl status honey-token-dashboard.service
sudo systemctl status honey-token-monitor.service

# Check logs
sudo journalctl -u honey-token-dashboard.service -f
sudo journalctl -u honey-token-monitor.service -f

# Test honey tokens exist
ls -la ~/honey-token-auditing/honey_tokens/

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000
```

---

## Troubleshooting

### Port 5000 Not Accessible
- Check Security Group rules
- Check if service is running: `sudo systemctl status honey-token-dashboard.service`
- Check firewall: `sudo ufw status`

### Service Won't Start
- Check logs: `sudo journalctl -u honey-token-dashboard.service -l`
- Verify Python dependencies: `pip list`
- Check file permissions: `ls -la ~/honey-token-auditing/`

### Module Not Found Errors
```bash
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

---

## Next Steps After Deployment

1. ✅ Test the dashboard at `http://YOUR_EC2_IP:5000`
2. ✅ Test "Simulate Attack" feature
3. ✅ Verify attack detection works
4. ✅ Set up log monitoring
5. ✅ Configure automated backups (optional)
6. ✅ Set up CloudWatch alarms (optional)

---

## Security Recommendations

1. **Restrict Security Group:** Only allow your IP address
2. **Use HTTPS:** Set up SSL certificate (Let's Encrypt) for production
3. **Regular Updates:** `sudo apt update && sudo apt upgrade`
4. **Monitor Logs:** Regularly check attack logs
5. **Backup Configuration:** Backup `.env` and important files

---

## Quick Reference Commands

```bash
# Restart services
sudo systemctl restart honey-token-dashboard.service
sudo systemctl restart honey-token-monitor.service

# View logs
sudo journalctl -u honey-token-dashboard.service -f
sudo journalctl -u honey-token-monitor.service -f

# Stop services
sudo systemctl stop honey-token-dashboard.service
sudo systemctl stop honey-token-monitor.service

# Check service status
sudo systemctl status honey-token-dashboard.service
```

---

**Need Help?** Check `DEPLOYMENT.md` for detailed instructions.

