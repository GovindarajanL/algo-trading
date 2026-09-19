# Quick Start Guide - Deploy to Google Cloud

This guide will get your trading system running on Google Cloud in 15 minutes.

## Prerequisites

- Google Cloud account with billing enabled
- Angel One trading account with API access
- Basic familiarity with terminal/command line

---

## Step 1: Local Setup (2 minutes)

```bash
# Clone the repository (if not already done)
git clone https://github.com/GovindarajanL/algo-trading.git
cd algo-trading
git checkout claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6

# Install Google Cloud SDK (if not installed)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

---

## Step 2: Deploy to Google Cloud (5 minutes)

```bash
# Run the automated deployment script
chmod +x scripts/deploy_to_gcp.sh
./scripts/deploy_to_gcp.sh

# Follow the prompts:
# - Enter your GCP Project ID
# - Confirm VM configuration (defaults are good)
# - Wait for deployment to complete
```

**What this does:**
- ✅ Creates a VM instance (e2-medium, ~$4.36/month)
- ✅ Enables required Google Cloud APIs
- ✅ Sets up Cloud Scheduler for automated start/stop
- ✅ Configures firewall rules

---

## Step 3: Setup VM Environment (5 minutes)

```bash
# SSH into your VM
gcloud compute ssh algo-trading-vm --zone=asia-south1-a

# Run the setup script
curl -s https://raw.githubusercontent.com/GovindarajanL/algo-trading/claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6/scripts/setup_vm.sh | bash

# Or if the repository is already cloned:
cd /opt/algo-trading
./scripts/setup_vm.sh
```

**What this does:**
- ✅ Installs Python, dependencies, and required packages
- ✅ Clones the trading system code
- ✅ Creates virtual environment
- ✅ Sets up systemd service
- ✅ Configures automated shutdown at 3:30 PM IST
- ✅ Sets up database backups

---

## Step 4: Configure Angel One Credentials (3 minutes)

Choose one option:

### Option A: Google Secret Manager (Recommended)

```bash
# Inside the VM
cd /opt/algo-trading
./scripts/configure_secrets.sh

# Enter your credentials when prompted:
# - Angel One API Key
# - Client Code
# - Password
# - TOTP Secret
# - Telegram Bot Token (optional)
# - Telegram Chat ID (optional)
```

### Option B: Environment File (Testing Only)

```bash
# Create .env file
nano /opt/algo-trading/.env

# Add your credentials:
ANGEL_ONE_API_KEY=your_api_key_here
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Save and secure the file
chmod 600 /opt/algo-trading/.env
```

---

## Step 5: Start Trading System (1 minute)

```bash
# Test manually first
cd /opt/algo-trading
source venv/bin/activate
source scripts/load_secrets.sh
python src/main.py --mode paper

# If successful, stop with Ctrl+C and start as service
sudo systemctl start algo-trading.service
sudo systemctl status algo-trading.service

# View live logs
sudo journalctl -u algo-trading.service -f
```

**Expected output:**
```
✅ System initialized successfully
✅ Connected to Angel One (Paper Mode)
✅ Market data feed active
✅ Risk management systems armed
📊 Monitoring positions...
```

---

## Verification Checklist

### ✅ Before First Trading Day

- [ ] Paper trading mode is active (not live)
- [ ] Angel One connection successful
- [ ] WebSocket feed connected
- [ ] Telegram notifications working (if configured)
- [ ] Database initialized (check `/opt/algo-trading/data/trading.db`)
- [ ] Logs being written (`/opt/algo-trading/logs/trading.log`)
- [ ] Systemd service starts automatically
- [ ] Auto-shutdown configured (crontab -l)
- [ ] Cloud Scheduler shows start job

### ✅ Test the Automated Schedule

```bash
# Check Cloud Scheduler job
gcloud scheduler jobs list

# Manually trigger VM start (optional test)
gcloud scheduler jobs run start-trading-vm

# Check VM started
gcloud compute instances list

# SSH and verify trading service is running
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
sudo systemctl status algo-trading.service
```

---

## Daily Operation

### Automated Schedule (No Manual Intervention Needed)

| Time (IST) | Action | Trigger |
|------------|--------|---------|
| 8:45 AM | VM starts | Cloud Scheduler |
| 8:45 AM | Trading system starts | Systemd service (auto) |
| 9:00 AM | Market opens | System begins monitoring |
| 3:00 PM | Market closes | System closes all positions |
| 3:30 PM | VM shuts down | Cron job inside VM |

### Manual Operations

```bash
# Start VM manually (if needed)
gcloud compute instances start algo-trading-vm --zone=asia-south1-a

# Stop VM manually (emergency)
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
sudo systemctl stop algo-trading.service
sudo shutdown -h now

# View logs remotely
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
tail -f /opt/algo-trading/logs/trading.log

# Check today's P&L
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
cd /opt/algo-trading
source venv/bin/activate
python -c "
import sqlite3
conn = sqlite3.connect('data/trading.db')
cursor = conn.execute('SELECT SUM(realized_pnl) FROM trades WHERE DATE(exit_time) = DATE(\"now\")')
print(f'Today PnL: ₹{cursor.fetchone()[0] or 0:.2f}')
conn.close()
"
```

---

## Monitoring

### View Logs

```bash
# Real-time logs
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
sudo journalctl -u algo-trading.service -f

# Or application logs
tail -f /opt/algo-trading/logs/trading.log

# Error logs
tail -f /opt/algo-trading/logs/trading.error.log
```

### Telegram Notifications (if configured)

You'll receive notifications for:
- ✅ Position opened
- ✅ Position closed
- ⚠️ Circuit breaker triggered
- ⚠️ Risk limit breached
- 📊 Daily summary
- 🔴 System shutdown

### Google Cloud Console

Monitor from: https://console.cloud.google.com

- **VM Status**: Compute Engine > VM Instances
- **Logs**: Logging > Logs Explorer
- **Costs**: Billing > Overview
- **Scheduler**: Cloud Scheduler > Jobs

---

## Cost Breakdown

### Monthly Estimate (Paper Trading, 20 trading days)

| Service | Cost |
|---------|------|
| Compute Engine (e2-medium, 130 hrs) | $4.36 |
| Persistent Disk (20GB) | $0.80 |
| Cloud Logging (5GB) | $0.50 |
| Secret Manager | $0.18 |
| Cloud Scheduler | $0.20 |
| Network Egress | $0.12 |
| **Total** | **~$6.16/month** |

**Cost Optimization Tips:**
- VM only runs 6.5 hours/day during trading
- Auto-shutdown saves ~$10/month vs 24/7 running
- Start with e2-small ($2.18/month) for testing

---

## Troubleshooting

### VM Won't Start

```bash
# Check VM status
gcloud compute instances describe algo-trading-vm --zone=asia-south1-a

# View startup logs
gcloud compute instances get-serial-port-output algo-trading-vm --zone=asia-south1-a
```

### Trading System Not Starting

```bash
# Check service status
sudo systemctl status algo-trading.service

# View detailed logs
sudo journalctl -u algo-trading.service -n 100

# Check if secrets loaded
source /opt/algo-trading/scripts/load_secrets.sh
echo $ANGEL_ONE_API_KEY
```

### Angel One Connection Failed

```bash
# Test connection manually
cd /opt/algo-trading
source venv/bin/activate
source scripts/load_secrets.sh
python -c "
from src.broker.angel_one import AngelOneBroker
broker = AngelOneBroker({
    'api_credentials': {
        'api_key': '$ANGEL_ONE_API_KEY',
        'client_code': '$ANGEL_ONE_CLIENT_CODE',
        'password': '$ANGEL_ONE_PASSWORD',
        'totp_secret': '$ANGEL_ONE_TOTP_SECRET'
    }
})
print('Connected:', broker.connect())
"
```

### Database Errors

```bash
# Check database integrity
sqlite3 /opt/algo-trading/data/trading.db "PRAGMA integrity_check;"

# Restore from backup
cd /opt/algo-trading/backups
ls -lt trading_*.db | head -1  # Find latest backup
cp trading_YYYYMMDD_HHMMSS.db ../data/trading.db
```

---

## Next Steps

### Week 1: Testing & Validation

1. **Monitor Daily**: Check logs every day
2. **Verify Automation**: Ensure start/stop works
3. **Check Notifications**: Telegram alerts working
4. **Review P&L**: Daily summary emails

### Month 1-6: Paper Trading

1. **Run Continuously**: 90+ trading days required
2. **Weekly Review**: Check performance metrics
3. **Adjust Strategies**: Fine-tune based on results
4. **Document Issues**: Track all problems

### Before Live Trading

1. **Complete Validation**: Run validation script
   ```bash
   cd /opt/algo-trading
   source venv/bin/activate
   python scripts/validate_paper_trading.py
   ```

2. **Pass All Criteria**:
   - ✅ 90+ trading days
   - ✅ 50+ trades
   - ✅ 55%+ win rate
   - ✅ 1.5+ profit factor
   - ✅ 1.0+ Sharpe ratio
   - ✅ <20% max drawdown

3. **Switch to Live Mode**:
   ```bash
   # Edit systemd service
   sudo nano /etc/systemd/system/algo-trading.service
   # Change: --mode paper to --mode live
   
   sudo systemctl daemon-reload
   sudo systemctl restart algo-trading.service
   ```

---

## Support

- **Documentation**: See `GOOGLE_CLOUD_DEPLOYMENT.md` for detailed guide
- **Validation**: See `PAPER_TRADING_VALIDATION.md` for validation criteria
- **Testing**: See `LOCAL_TESTING_GUIDE.md` for local testing
- **Repository**: https://github.com/GovindarajanL/algo-trading

---

## Emergency Procedures

### Emergency Shutdown

```bash
# Stop trading immediately
gcloud compute ssh algo-trading-vm --zone=asia-south1-a
sudo systemctl stop algo-trading.service

# Manually close all positions in Angel One platform

# Shutdown VM
sudo shutdown -h now
```

### Emergency Contact

- Angel One Support: 1800-209-9191
- Your phone/email for Telegram alerts

---

**⚠️ IMPORTANT**: 
- Always start with paper trading
- Complete 90-day validation before live trading
- Monitor closely during first week
- Never risk more than you can afford to lose
- Have emergency procedures ready

**Ready to deploy? Run:**
```bash
./scripts/deploy_to_gcp.sh
```
