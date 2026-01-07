# ⚡ Quick Start Guide - Deploy to EC2 in 5 Minutes

## Prerequisites Checklist
- [x] EC2 instance running (t2g.micro, Ubuntu)
- [x] .pem file downloaded
- [x] Know how to SSH into EC2

---

## 🎯 Fastest Method: Direct Upload + Deploy Script

### Step 1: Upload Project to EC2 (2 minutes)

**On Windows PowerShell:**
```powershell
# Navigate to your project folder
cd C:\Users\mhmmd\OneDrive\Desktop\Projectss\ISM

# Upload project (replace YOUR_EC2_IP and path to .pem)
scp -i "C:\path\to\your-key.pem" -r * ubuntu@YOUR_EC2_IP:~/honey-token-auditing/
```

**Alternative: Use WinSCP (GUI tool)**
1. Download WinSCP: https://winscp.net/
2. Connect using your .pem file
3. Drag and drop project folder to `/home/ubuntu/honey-token-auditing/`

### Step 2: SSH and Deploy (3 minutes)

```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Navigate to project
cd ~/honey-token-auditing

# Make deploy script executable
chmod +x deploy.sh

# Run automated deployment
./deploy.sh
```

The deploy script will:
- ✅ Install Python and dependencies
- ✅ Create virtual environment
- ✅ Install all required packages
- ✅ Set up systemd services
- ✅ Configure log rotation
- ✅ Create .env file automatically

### Step 3: Start Services

```bash
# Start the services
sudo systemctl start honey-token-monitor.service
sudo systemctl start honey-token-dashboard.service

# Enable auto-start on boot
sudo systemctl enable honey-token-monitor.service
sudo systemctl enable honey-token-dashboard.service

# Check status
sudo systemctl status honey-token-dashboard.service
```

### Step 4: Configure Security Group

1. AWS Console → EC2 → Security Groups
2. Select your instance's security group
3. **Add Inbound Rule:**
   - Type: Custom TCP
   - Port: 5000
   - Source: Your IP (or 0.0.0.0/0 for testing)
   - Save

### Step 5: Access Dashboard

```bash
# Get your EC2 public IP
curl http://169.254.169.254/latest/meta-data/public-ipv4
```

Open browser: `http://YOUR_EC2_IP:5000`

---

## 🐛 Troubleshooting

### "Permission denied" when uploading
```bash
# Fix .pem file permissions (on Windows, use Git Bash or WSL)
chmod 400 your-key.pem
```

### "deploy.sh: command not found"
```bash
# Make sure you're in the right directory
cd ~/honey-token-auditing
ls -la deploy.sh

# Make it executable
chmod +x deploy.sh
```

### Dashboard not accessible
```bash
# Check if service is running
sudo systemctl status honey-token-dashboard.service

# Check if port is open
sudo netstat -tlnp | grep 5000

# Check Security Group in AWS Console
```

### Service fails to start
```bash
# Check logs
sudo journalctl -u honey-token-dashboard.service -l

# Common fix: Reinstall dependencies
cd ~/honey-token-auditing
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

---

## 📋 Manual Setup (If deploy.sh fails)

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 2. Create virtual environment
cd ~/honey-token-auditing
python3 -m venv venv
source venv/bin/activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Create .env (optional - app works without it)
cat > .env <<EOF
FLASK_PORT=5000
FLASK_ENV=production
EOF

# 5. Initialize honey tokens
python honey_token_manager.py

# 6. Run app
python app.py
```

---

## ✅ Verification Checklist

- [ ] Can SSH into EC2
- [ ] Project files uploaded
- [ ] Deploy script ran successfully
- [ ] Services are running (`sudo systemctl status`)
- [ ] Security Group allows port 5000
- [ ] Dashboard accessible at `http://EC2_IP:5000`
- [ ] Can see "SAFE" status on dashboard
- [ ] "Simulate Attack" button works

---

## 🎉 You're Done!

Your Honey-Token Auditing System is now running on EC2!

**Next Steps:**
1. Test the attack simulation
2. Monitor the logs
3. Set up regular backups
4. Consider using GitHub for version control

---

**Need more details?** See `DEPLOYMENT_STEPS.md` for comprehensive guide.

