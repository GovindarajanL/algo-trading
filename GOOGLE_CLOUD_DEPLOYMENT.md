# Google Cloud Deployment Guide

Complete guide to deploy the Algorithmic Options Trading System on Google Cloud Platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Architecture](#deployment-architecture)
3. [Option 1: Compute Engine VM (Recommended)](#option-1-compute-engine-vm-recommended)
4. [Option 2: Cloud Run (Alternative)](#option-2-cloud-run-alternative)
5. [Security Configuration](#security-configuration)
6. [Database Setup](#database-setup)
7. [Automated Scheduling](#automated-scheduling)
8. [Monitoring & Logging](#monitoring--logging)
9. [Cost Optimization](#cost-optimization)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Google Cloud Account Setup

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize gcloud
gcloud init

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
# Enable necessary Google Cloud APIs
gcloud services enable compute.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 3. Required Credentials

- **Angel One API Credentials**:
  - API Key
  - Client Code
  - Password
  - TOTP Secret (for 2FA)

- **Telegram Bot Token** (optional for notifications)

---

## Deployment Architecture

### Recommended Setup

```
┌─────────────────────────────────────────────────┐
│        Google Compute Engine VM (e2-medium)     │
│  ┌───────────────────────────────────────────┐  │
│  │  Trading System (Python 3.9+)             │  │
│  │  - Runs during market hours (9:00-15:30) │  │
│  │  - Auto-shutdown after hours              │  │
│  ├───────────────────────────────────────────┤  │
│  │  SQLite Database (persistent disk)        │  │
│  ├───────────────────────────────────────────┤  │
│  │  Logs → Cloud Logging                     │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         ↓                              ↑
    Angel One API              Cloud Scheduler
    (Market Data)           (Start/Stop VM)
```

### Why Compute Engine?

- **Long-running processes**: Trading system needs to run continuously during market hours
- **WebSocket connections**: Requires persistent connections
- **State management**: Maintains position monitoring state
- **Cost-effective**: Pay only when VM is running (9:00-15:30 IST = ~6.5 hours/day)

---

## Option 1: Compute Engine VM (Recommended)

### Step 1: Create VM Instance

```bash
# Create a VM optimized for trading
gcloud compute instances create algo-trading-vm \
    --zone=asia-south1-a \
    --machine-type=e2-medium \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --scopes=cloud-platform \
    --tags=trading-system \
    --metadata=startup-script='#!/bin/bash
# Will be configured in Step 3
'
```

**Machine Type Selection**:
- `e2-micro` (0.25-2 vCPU, 1GB RAM): Testing only - **NOT recommended**
- `e2-small` (0.5-2 vCPU, 2GB RAM): Minimal paper trading
- **`e2-medium` (1-2 vCPU, 4GB RAM): Recommended** - Good balance
- `e2-standard-2` (2 vCPU, 8GB RAM): Live trading with multiple strategies

**Cost Estimate** (e2-medium in asia-south1):
- ~$0.0335/hour × 6.5 hours/day × 20 trading days = ~$4.36/month

### Step 2: SSH into VM

```bash
# Connect to VM
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
```

### Step 3: Setup Trading Environment

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.9+
sudo apt-get install -y python3.9 python3.9-venv python3-pip git

# Create application directory
sudo mkdir -p /opt/algo-trading
sudo chown $USER:$USER /opt/algo-trading
cd /opt/algo-trading

# Clone repository
git clone https://github.com/GovindarajanL/algo-trading.git .
git checkout claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs database backups
```

### Step 4: Configure Credentials Securely

**Option A: Google Secret Manager (Recommended for Production)**

```bash
# Store secrets in Google Secret Manager
echo -n "YOUR_API_KEY" | gcloud secrets create angel-one-api-key --data-file=-
echo -n "YOUR_CLIENT_CODE" | gcloud secrets create angel-one-client-code --data-file=-
echo -n "YOUR_PASSWORD" | gcloud secrets create angel-one-password --data-file=-
echo -n "YOUR_TOTP_SECRET" | gcloud secrets create angel-one-totp-secret --data-file=-
echo -n "YOUR_TELEGRAM_TOKEN" | gcloud secrets create telegram-bot-token --data-file=-

# Grant VM access to secrets
gcloud secrets add-iam-policy-binding angel-one-api-key \
    --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Repeat for all secrets
```

Create `/opt/algo-trading/scripts/load_secrets.sh`:

```bash
#!/bin/bash
# Load secrets from Google Secret Manager

export ANGEL_ONE_API_KEY=$(gcloud secrets versions access latest --secret="angel-one-api-key")
export ANGEL_ONE_CLIENT_CODE=$(gcloud secrets versions access latest --secret="angel-one-client-code")
export ANGEL_ONE_PASSWORD=$(gcloud secrets versions access latest --secret="angel-one-password")
export ANGEL_ONE_TOTP_SECRET=$(gcloud secrets versions access latest --secret="angel-one-totp-secret")
export TELEGRAM_BOT_TOKEN=$(gcloud secrets versions access latest --secret="telegram-bot-token")
export TELEGRAM_CHAT_ID=$(gcloud secrets versions access latest --secret="telegram-chat-id")
```

**Option B: Environment File (For Testing)**

```bash
# Create .env file (less secure, use only for testing)
cat > /opt/algo-trading/.env << EOF
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
EOF

# Secure the file
chmod 600 /opt/algo-trading/.env
```

### Step 5: Create Systemd Service

Create `/etc/systemd/system/algo-trading.service`:

```ini
[Unit]
Description=Algorithmic Options Trading System
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/algo-trading
Environment="PATH=/opt/algo-trading/venv/bin"
ExecStartPre=/bin/bash /opt/algo-trading/scripts/load_secrets.sh
ExecStart=/opt/algo-trading/venv/bin/python src/main.py --mode paper
Restart=on-failure
RestartSec=30
StandardOutput=append:/opt/algo-trading/logs/trading.log
StandardError=append:/opt/algo-trading/logs/trading.error.log

# Resource limits
MemoryLimit=2G
CPUQuota=150%

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable algo-trading.service
sudo systemctl start algo-trading.service

# Check status
sudo systemctl status algo-trading.service

# View logs
sudo journalctl -u algo-trading.service -f
```

### Step 6: Configure Automated Startup Script

Create `/opt/algo-trading/scripts/startup.sh`:

```bash
#!/bin/bash
set -e

echo "=== Algo Trading System Startup ==="
date

# Load secrets
source /opt/algo-trading/scripts/load_secrets.sh

# Activate virtual environment
cd /opt/algo-trading
source venv/bin/activate

# Pull latest code (optional - be careful with auto-updates)
# git pull origin claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6

# Run database migrations if any
# python scripts/migrate_database.py

# Start trading system
echo "Starting trading system at $(date)"
python src/main.py --mode paper 2>&1 | tee -a logs/trading_$(date +%Y%m%d).log
```

Make it executable:

```bash
chmod +x /opt/algo-trading/scripts/startup.sh
```

### Step 7: Configure Auto-Shutdown

Create `/opt/algo-trading/scripts/shutdown.sh`:

```bash
#!/bin/bash
set -e

echo "=== Graceful Shutdown Started ==="
date

# Send notification
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=🔴 Trading system shutting down at $(date)"

# Stop trading service gracefully
sudo systemctl stop algo-trading.service

# Backup database
BACKUP_DIR="/opt/algo-trading/backups"
mkdir -p $BACKUP_DIR
cp /opt/algo-trading/data/trading.db "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db"

# Upload backup to Google Cloud Storage (optional)
# gsutil cp "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db" gs://YOUR_BUCKET/backups/

# Shutdown VM
echo "Shutting down VM..."
sudo shutdown -h now
```

Make it executable:

```bash
chmod +x /opt/algo-trading/scripts/shutdown.sh
```

### Step 8: Setup Cron for Auto-Shutdown

```bash
# Edit crontab
crontab -e

# Add this line to shutdown at 3:30 PM IST every trading day
30 15 * * 1-5 /opt/algo-trading/scripts/shutdown.sh
```

---

## Option 2: Cloud Run (Alternative)

**Note**: Cloud Run is better suited for stateless, request-driven applications. For this trading system, **Compute Engine is strongly recommended**. However, if you need Cloud Run:

### Limitations

- ❌ No persistent WebSocket connections
- ❌ Stateless - positions tracked in external database required
- ❌ 60-minute request timeout
- ✅ Auto-scaling (but not needed for single-instance trading)
- ✅ Pay per request (but trading runs continuously)

### Deployment (If Needed)

```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/main.py", "--mode", "paper"]
EOF

# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/algo-trading
gcloud run deploy algo-trading \
    --image gcr.io/YOUR_PROJECT_ID/algo-trading \
    --platform managed \
    --region asia-south1 \
    --memory 2Gi \
    --timeout 3600 \
    --no-allow-unauthenticated
```

---

## Security Configuration

### 1. Firewall Rules

```bash
# Create firewall rule (if needed for external access)
gcloud compute firewall-rules create allow-trading-system \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=YOUR_IP_ADDRESS/32 \
    --target-tags=trading-system
```

### 2. Secure API Credentials

**Never** commit API credentials to git. Use one of:

1. **Google Secret Manager** (Recommended)
2. **Environment variables** loaded at runtime
3. **Config file** with restricted permissions (chmod 600)

### 3. Enable OS Login

```bash
# Use OS Login for secure SSH access
gcloud compute instances add-metadata algo-trading-vm \
    --zone=asia-south1-a \
    --metadata enable-oslogin=TRUE
```

---

## Database Setup

### Option A: SQLite on VM (Recommended for Start)

```bash
# Database location
/opt/algo-trading/data/trading.db

# Automated backups
cat > /opt/algo-trading/scripts/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/algo-trading/backups"
mkdir -p $BACKUP_DIR

# Local backup
cp /opt/algo-trading/data/trading.db \
   "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db"

# Upload to Cloud Storage
gsutil cp "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db" \
   gs://YOUR_BUCKET/backups/

# Keep only last 30 days locally
find $BACKUP_DIR -name "trading_*.db" -mtime +30 -delete
EOF

chmod +x /opt/algo-trading/scripts/backup_db.sh

# Add to crontab - backup every hour during trading
0 9-15 * * 1-5 /opt/algo-trading/scripts/backup_db.sh
```

### Option B: Cloud SQL (For Production/Scale)

```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create algo-trading-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=asia-south1 \
    --backup \
    --backup-start-time=16:00

# Create database
gcloud sql databases create trading \
    --instance=algo-trading-db

# Update config.yaml to use PostgreSQL
# database:
#   type: postgresql
#   host: CLOUD_SQL_IP
#   port: 5432
#   database: trading
#   user: postgres
#   password: stored_in_secret_manager
```

---

## Automated Scheduling

### Cloud Scheduler for VM Management

```bash
# Create service account for scheduler
gcloud iam service-accounts create vm-scheduler \
    --display-name="VM Scheduler Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:vm-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"

# Schedule VM startup (8:45 AM IST = 3:15 AM UTC)
gcloud scheduler jobs create http start-trading-vm \
    --schedule="15 3 * * 1-5" \
    --time-zone="Asia/Kolkata" \
    --uri="https://compute.googleapis.com/compute/v1/projects/YOUR_PROJECT_ID/zones/asia-south1-a/instances/algo-trading-vm/start" \
    --http-method=POST \
    --oauth-service-account-email=vm-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com

# The shutdown is handled by cron inside the VM (Step 7)
```

**Explanation**:
- VM starts at **8:45 AM IST** (15 minutes before market opens)
- Trading system starts automatically via systemd service
- VM shuts down at **3:30 PM IST** via cron job inside VM

---

## Monitoring & Logging

### 1. Cloud Logging

```bash
# Install logging agent (if not using systemd journal)
curl -sSO https://dl.google.com/cloudagents/add-logging-agent-repo.sh
sudo bash add-logging-agent-repo.sh
sudo apt-get update
sudo apt-get install google-fluentd
```

### 2. Custom Metrics

Create `/opt/algo-trading/scripts/send_metrics.sh`:

```bash
#!/bin/bash
# Send custom metrics to Cloud Monitoring

METRIC_VALUE=$(python -c "
import sqlite3
conn = sqlite3.connect('/opt/algo-trading/data/trading.db')
cursor = conn.execute('SELECT COUNT(*) FROM positions WHERE status=\"OPEN\"')
print(cursor.fetchone()[0])
conn.close()
")

gcloud monitoring time-series create \
    --project=YOUR_PROJECT_ID \
    --metric-kind=GAUGE \
    --value-type=INT64 \
    metric.type="custom.googleapis.com/trading/open_positions" \
    --metric-value=$METRIC_VALUE
```

### 3. Alerting

```bash
# Create alert for system errors
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_NOTIFICATION_CHANNEL_ID \
    --display-name="Trading System Errors" \
    --condition-display-name="High Error Rate" \
    --condition-threshold-value=5 \
    --condition-threshold-duration=300s
```

### 4. Telegram Integration

The system already has Telegram notifications built-in. Ensure:

```yaml
# config.yaml
notifications:
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}  # Loaded from Secret Manager
    chat_id: ${TELEGRAM_CHAT_ID}
    
  events:
    - position_opened
    - position_closed
    - circuit_breaker_triggered
    - daily_summary
    - system_errors
```

---

## Cost Optimization

### Monthly Cost Estimate (Paper Trading)

| Resource | Configuration | Hours/Month | Cost/Month |
|----------|--------------|-------------|------------|
| **Compute Engine** | e2-medium | 130 (6.5h × 20 days) | $4.36 |
| **Persistent Disk** | 20GB Standard | 730 | $0.80 |
| **Cloud Logging** | 5GB/month | - | $0.50 |
| **Secret Manager** | 5 secrets | - | $0.18 |
| **Cloud Scheduler** | 2 jobs | - | $0.20 |
| **Network Egress** | 1GB | - | $0.12 |
| **Total** | | | **~$6.16/month** |

### Cost Saving Tips

1. **Use Preemptible VMs** (for testing only):
   ```bash
   --preemptible --maintenance-policy=TERMINATE
   # Saves ~70% but VM can be shut down anytime
   ```

2. **Committed Use Discounts**:
   - 1-year commitment: 37% discount
   - 3-year commitment: 55% discount

3. **Right-size Machine Type**:
   - Start with `e2-small` for paper trading
   - Upgrade to `e2-medium` only if needed

4. **Automatic Shutdown**:
   - Ensure cron job works correctly
   - VM should only run 6.5 hours/day

5. **Clean Up Logs**:
   ```bash
   # Delete logs older than 30 days
   find /opt/algo-trading/logs -name "*.log" -mtime +30 -delete
   ```

---

## Deployment Checklist

Before going live, ensure:

### ✅ Pre-Deployment

- [ ] Google Cloud project created and billing enabled
- [ ] VM instance created and accessible via SSH
- [ ] All APIs enabled (Compute, Logging, Scheduler, Secrets)
- [ ] Angel One API credentials obtained and tested locally
- [ ] Telegram bot created and chat ID obtained

### ✅ Configuration

- [ ] Code cloned to `/opt/algo-trading`
- [ ] Virtual environment created and dependencies installed
- [ ] Secrets stored in Secret Manager or `.env` file
- [ ] `config.yaml` updated with correct settings
- [ ] Database initialized: `python scripts/init_database.py`

### ✅ Testing

- [ ] Run paper trading locally: `python src/main.py --mode paper`
- [ ] Verify Angel One connection works
- [ ] Test WebSocket connection
- [ ] Confirm Telegram notifications work
- [ ] Run test suite: `pytest tests/ -v`

### ✅ Automation

- [ ] Systemd service created and enabled
- [ ] Startup script configured
- [ ] Shutdown script configured and added to crontab
- [ ] Cloud Scheduler jobs created for VM start
- [ ] Database backup script configured

### ✅ Monitoring

- [ ] Cloud Logging configured
- [ ] Alerts configured (errors, circuit breakers)
- [ ] Daily summary emails/Telegram messages enabled
- [ ] Manual monitoring plan for first week

### ✅ Security

- [ ] Firewall rules configured (minimal access)
- [ ] Secrets not committed to git
- [ ] SSH access restricted to your IP
- [ ] OS Login enabled (optional but recommended)
- [ ] File permissions set correctly (chmod 600 for sensitive files)

---

## Testing the Deployment

### 1. Manual Test Run

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=asia-south1-a

# Activate environment
cd /opt/algo-trading
source venv/bin/activate

# Load secrets
source scripts/load_secrets.sh

# Run in paper mode
python src/main.py --mode paper

# Expected output:
# ✅ System initialized successfully
# ✅ Connected to Angel One (Paper Mode)
# ✅ Market data feed active
# ✅ Risk management systems armed
# 📊 Monitoring positions...
```

### 2. Test Automatic Startup

```bash
# Reboot VM to test systemd service
sudo reboot

# After reboot, check service status
sudo systemctl status algo-trading.service

# Should show "active (running)"
```

### 3. Test Scheduled Start/Stop

```bash
# Manually trigger Cloud Scheduler
gcloud scheduler jobs run start-trading-vm

# Check VM started
gcloud compute instances describe algo-trading-vm \
    --zone=asia-south1-a \
    --format="get(status)"
# Should return "RUNNING"
```

---

## Troubleshooting

### Issue: VM Won't Start

```bash
# Check VM status
gcloud compute instances describe algo-trading-vm \
    --zone=asia-south1-a

# View serial console output
gcloud compute instances get-serial-port-output algo-trading-vm \
    --zone=asia-south1-a

# Common fix: Increase boot disk size
gcloud compute disks resize algo-trading-vm \
    --size=30GB \
    --zone=asia-south1-a
```

### Issue: Trading System Not Starting

```bash
# Check systemd service status
sudo systemctl status algo-trading.service

# View detailed logs
sudo journalctl -u algo-trading.service -n 100 --no-pager

# Check application logs
tail -f /opt/algo-trading/logs/trading.log
tail -f /opt/algo-trading/logs/trading.error.log

# Common fixes:
# 1. Verify secrets loaded: echo $ANGEL_ONE_API_KEY
# 2. Check permissions: ls -la /opt/algo-trading
# 3. Test Python: source venv/bin/activate && python src/main.py --mode paper
```

### Issue: Angel One Connection Fails

```bash
# Test credentials manually
python << EOF
from src.broker.angel_one import AngelOneBroker
import os

config = {
    'api_credentials': {
        'api_key': os.getenv('ANGEL_ONE_API_KEY'),
        'client_code': os.getenv('ANGEL_ONE_CLIENT_CODE'),
        'password': os.getenv('ANGEL_ONE_PASSWORD'),
        'totp_secret': os.getenv('ANGEL_ONE_TOTP_SECRET')
    }
}

broker = AngelOneBroker(config)
result = broker.connect()
print(f"Connection: {result}")
EOF

# Common issues:
# 1. TOTP secret incorrect - verify in Angel One app
# 2. API key expired - regenerate in Angel One portal
# 3. IP not whitelisted - add VM's external IP to Angel One
```

### Issue: Database Lock Errors

```bash
# Check database access
sqlite3 /opt/algo-trading/data/trading.db "PRAGMA integrity_check;"

# If locked, find process
lsof /opt/algo-trading/data/trading.db

# Fix: Ensure only one instance running
ps aux | grep "src/main.py"
```

### Issue: High Memory Usage

```bash
# Check memory
free -h

# Check top processes
top -o %MEM

# Restart service
sudo systemctl restart algo-trading.service

# If persistent, upgrade VM:
gcloud compute instances stop algo-trading-vm --zone=asia-south1-a
gcloud compute instances set-machine-type algo-trading-vm \
    --machine-type=e2-standard-2 \
    --zone=asia-south1-a
gcloud compute instances start algo-trading-vm --zone=asia-south1-a
```

---

## Next Steps

1. **Week 1: Testing Phase**
   - Run paper trading daily
   - Monitor all logs
   - Verify automated start/stop
   - Check Telegram notifications
   - Review daily summaries

2. **Month 1-6: Paper Trading Validation**
   - Run for 90+ trading days
   - Execute validation: `python scripts/validate_paper_trading.py`
   - Achieve validation criteria (see `PAPER_TRADING_VALIDATION.md`)
   - Document all issues and fixes

3. **Before Live Trading**
   - **MANDATORY**: Complete 90-day validation
   - Review all circuit breaker triggers
   - Verify risk management worked correctly
   - Practice manual emergency shutdown
   - Start with minimal capital

4. **Live Trading Phase**
   - Change `--mode paper` to `--mode live` in systemd service
   - Start with 1 strategy only
   - Monitor extremely closely for first week
   - Gradually enable more strategies

---

## Support & Resources

- **Angel One API Docs**: https://smartapi.angelbroking.com/docs
- **Google Cloud Docs**: https://cloud.google.com/docs
- **Project Repository**: https://github.com/GovindarajanL/algo-trading
- **Branch**: claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6

## Emergency Contacts

- Angel One Support: 1800-209-9191
- Google Cloud Support: Create ticket in Cloud Console

---

**⚠️ DISCLAIMER**: Trading involves risk. This system is provided as-is. Always:
- Start with paper trading
- Complete 90-day validation
- Never risk more than you can afford to lose
- Monitor positions manually during first weeks
- Have emergency shutdown procedures ready
