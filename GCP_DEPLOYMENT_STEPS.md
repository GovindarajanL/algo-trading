# Step-by-Step GCP Deployment Guide

Complete walkthrough to deploy your trading system on Google Cloud Platform.

**Configuration:** Option 1 (Auto-shutdown)
**Cost:** $1.30/month
**VM:** f1-micro (FREE tier)
**Static IP:** Required for Angel One

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Google account
- [ ] Credit/debit card (for GCP verification, won't be charged)
- [ ] Angel One trading account
- [ ] Angel One API credentials:
  - API Key
  - Client Code
  - Password
  - TOTP Secret
- [ ] Terminal/Command Prompt access

---

## Part 1: Google Cloud Setup (10 minutes)

### Step 1: Create Google Cloud Account

1. **Go to:** https://cloud.google.com/free
2. **Click:** "Get started for free"
3. **Sign in** with your Google account
4. **Fill in:**
   - Country: India
   - Terms: Check "I agree"
5. **Click:** Continue

### Step 2: Setup Billing (Required but won't charge)

1. **Account type:** Individual
2. **Name:** Your name
3. **Address:** Your address
4. **Payment method:** Add credit/debit card
   - Don't worry: Won't auto-charge
   - Only for verification
   - $300 free credit applied automatically
5. **Click:** Start my free trial

**Result:** ✅ You now have $300 credit for 90 days

### Step 3: Create Project

1. **Go to:** https://console.cloud.google.com
2. **Click:** Project dropdown (top left, next to "Google Cloud")
3. **Click:** "New Project"
4. **Project name:** `algo-trading` (or any name you prefer)
5. **Click:** Create
6. **Wait:** 10-20 seconds for project to be created
7. **Click:** Select this project (from notification or dropdown)

**Copy your Project ID** (looks like: `algo-trading-123456`)
You'll need this later!

---

## Part 2: Install Google Cloud SDK (5 minutes)

### For Windows:

1. **Download:** https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
2. **Run installer**
3. **Follow wizard:** Click Next > Next > Install
4. **Check:** "Run 'gcloud init'" at end
5. **Click:** Finish

### For Mac:

```bash
# In Terminal
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### For Linux:

```bash
# In Terminal
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Step 4: Initialize gcloud

```bash
# In terminal/command prompt
gcloud init

# Follow prompts:
# 1. Login: Choose your Google account
# 2. Project: Select your project (algo-trading-123456)
# 3. Default region: 17 (us-central1-a)
```

**Verify installation:**
```bash
gcloud --version
# Should show: Google Cloud SDK XXX
```

---

## Part 3: Enable Required APIs (2 minutes)

Copy and paste these commands one by one:

```bash
# Set your project (replace YOUR_PROJECT_ID)
gcloud config set project YOUR_PROJECT_ID

# Enable Compute Engine API
gcloud services enable compute.googleapis.com

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Enable Cloud Scheduler API
gcloud services enable cloudscheduler.googleapis.com

# Enable Logging API
gcloud services enable logging.googleapis.com
```

**Wait:** 30-60 seconds for APIs to enable

---

## Part 4: Clone Repository (2 minutes)

### Option A: If you have git installed

```bash
# Clone the repository
git clone https://github.com/GovindarajanL/algo-trading.git

# Go to directory
cd algo-trading

# Checkout the branch
git checkout claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6
```

### Option B: Download as ZIP

1. **Go to:** https://github.com/GovindarajanL/algo-trading
2. **Click:** Code > Download ZIP
3. **Extract** the ZIP file
4. **Open terminal** in that folder

---

## Part 5: Setup Static IP (3 minutes)

```bash
# Make script executable
chmod +x scripts/setup_static_ip.sh

# Run the setup (replace YOUR_PROJECT_ID)
./scripts/setup_static_ip.sh YOUR_PROJECT_ID

# When prompted:
# Region: us-central1 (press Enter)
# VM Name: algo-trading-vm (press Enter)  
# Zone: us-central1-a (press Enter)
```

**Wait:** 1-2 minutes for VM creation

**IMPORTANT:** Copy the Static IP shown!
It will look like: `Static IP Reserved: 34.123.45.67`

**Save this IP - you'll need it for Angel One!**

---

## Part 6: Whitelist IP in Angel One (5 minutes)

### Step 1: Login to Angel One SmartAPI

1. **Go to:** https://smartapi.angelbroking.com/publisher-login
2. **Login** with your Angel One credentials
3. **Go to:** My API > IP Whitelisting

### Step 2: Add Your Static IP

1. **Click:** Add IP
2. **Enter IP:** The static IP from Part 5 (e.g., 34.123.45.67)
3. **Description:** GCP Trading VM
4. **Click:** Save

### Step 3: Wait for Propagation

**Wait 5-10 minutes** for IP whitelist to activate.

Meanwhile, continue with next steps...

---

## Part 7: SSH into VM and Setup (10 minutes)

### Step 1: Connect to VM

```bash
# SSH into the VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# If prompted "Do you want to continue?": Type Y and press Enter
# If asked to create SSH keys: Press Enter for all prompts
```

**You're now inside the VM!** The prompt will change to show `user@algo-trading-vm`.

### Step 2: Clone Repository (Inside VM)

```bash
# Create directory
sudo mkdir -p /opt/algo-trading
sudo chown $USER:$USER /opt/algo-trading
cd /opt/algo-trading

# Clone repository
git clone https://github.com/GovindarajanL/algo-trading.git .

# Checkout branch
git checkout claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6
```

### Step 3: Run Setup Script

```bash
# Make script executable
chmod +x scripts/setup_vm.sh

# Run setup (this takes 5-10 minutes)
./scripts/setup_vm.sh
```

**What this does:**
- Installs Python 3.9
- Creates virtual environment
- Installs all dependencies
- Sets up systemd service
- Configures auto-shutdown at 3:30 PM IST
- Sets up database backups

**Wait** for "Setup complete!" message.

### Step 4: Optimize for Swing Trading

```bash
# Run optimization
python3 scripts/optimize_for_swing.py
```

**This configures:**
- Position checks every 5 minutes
- REST API (no WebSocket)
- Low memory/CPU usage
- Perfect for f1-micro

---

## Part 8: Configure Angel One Credentials (3 minutes)

### Option A: Using Google Secret Manager (Recommended)

```bash
# Run configuration script
./scripts/configure_secrets.sh

# Enter when prompted:
# 1. Angel One API Key: [paste your API key]
# 2. Client Code: [paste your client code]
# 3. Password: [type your password]
# 4. TOTP Secret: [paste your TOTP secret]
# 5. Telegram Bot Token: [optional, press Enter to skip]
# 6. Telegram Chat ID: [optional, press Enter to skip]
```

### Option B: Using .env File (Simpler)

```bash
# Create .env file
nano /opt/algo-trading/.env

# Press Ctrl+Shift+V or right-click to paste:
ANGEL_ONE_API_KEY=your_api_key_here
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret

# Press Ctrl+X, then Y, then Enter to save

# Secure the file
chmod 600 /opt/algo-trading/.env
```

---

## Part 9: Test Angel One Connection (2 minutes)

```bash
# Activate virtual environment
cd /opt/algo-trading
source venv/bin/activate

# Load secrets
source scripts/load_secrets.sh

# Test connection
python -c "
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
if result:
    print('✅ SUCCESS: Connected to Angel One!')
    print('✅ IP whitelisting is working!')
else:
    print('❌ FAILED: Connection refused')
    print('   Wait 5-10 minutes for IP whitelist to activate')
"
```

**Expected Output:**
```
✅ SUCCESS: Connected to Angel One!
✅ IP whitelisting is working!
```

**If failed:**
- Wait 10 minutes and try again
- Verify IP is correctly whitelisted in Angel One portal
- Check credentials are correct

---

## Part 10: Start Trading System (2 minutes)

### Step 1: Test Manually First

```bash
# Test run (Ctrl+C to stop)
cd /opt/algo-trading
source venv/bin/activate
python src/main.py --mode paper
```

**Expected output:**
```
✅ System initialized successfully
✅ Connected to Angel One (Paper Mode)
✅ Market data feed active
✅ Risk management systems armed
📊 Monitoring positions...
```

Press **Ctrl+C** to stop.

### Step 2: Start as Service

```bash
# Start the service
sudo systemctl start algo-trading.service

# Check status
sudo systemctl status algo-trading.service
```

**Should show:** `Active: active (running)`

### Step 3: View Logs

```bash
# Real-time logs
tail -f /opt/algo-trading/logs/trading.log

# Or service logs
sudo journalctl -u algo-trading.service -f
```

Press **Ctrl+C** to exit log view.

---

## Part 11: Setup Auto-Shutdown (Already Done!)

The setup script already configured:

**Cron job:** Shutdown at 3:30 PM IST daily

**Verify:**
```bash
crontab -l
```

**Should show:**
```
30 15 * * 1-5 /opt/algo-trading/scripts/shutdown.sh
```

**What happens:**
1. 8:45 AM IST: Cloud Scheduler starts VM
2. 8:45 AM IST: Trading system auto-starts (systemd)
3. 9:00 AM IST: Market opens, trading begins
4. 3:00 PM IST: Market closes, positions closed
5. 3:30 PM IST: VM auto-shuts down

**Cost:** Only charged for 6.5 hours/day = $1.30/month!

---

## Part 12: Setup Cloud Scheduler (5 minutes)

**Exit SSH first:**
```bash
exit
```

**Now on your local machine:**

```bash
# Create service account
gcloud iam service-accounts create vm-scheduler \
    --display-name="VM Scheduler"

# Grant permissions (replace YOUR_PROJECT_ID)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:vm-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1"

# Create scheduler job (8:45 AM IST = 3:15 AM UTC)
gcloud scheduler jobs create http start-trading-vm \
    --schedule="15 3 * * 1-5" \
    --time-zone="Asia/Kolkata" \
    --uri="https://compute.googleapis.com/compute/v1/projects/YOUR_PROJECT_ID/zones/us-central1-a/instances/algo-trading-vm/start" \
    --http-method=POST \
    --oauth-service-account-email=vm-scheduler@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**Verify:**
```bash
gcloud scheduler jobs list
```

**Should show:** Job `start-trading-vm` with schedule `15 3 * * 1-5`

---

## Part 13: Test Complete Workflow (Optional)

### Test Automated Start

```bash
# Manually trigger scheduler
gcloud scheduler jobs run start-trading-vm

# Wait 30 seconds, then check if VM started
gcloud compute instances list

# Should show: algo-trading-vm    RUNNING
```

### Test Auto-Shutdown

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# Manually trigger shutdown
/opt/algo-trading/scripts/shutdown.sh
```

**VM will shutdown in 10 seconds.**

---

## ✅ Deployment Complete!

### Verification Checklist

- [ ] VM created with f1-micro (FREE tier)
- [ ] Static IP reserved and assigned
- [ ] IP whitelisted in Angel One portal
- [ ] Angel One connection successful
- [ ] Trading system running
- [ ] Auto-shutdown configured (3:30 PM IST)
- [ ] Cloud Scheduler configured (8:45 AM IST)
- [ ] Logs accessible

### What Happens Now?

**Daily Schedule (Automatic):**
- **8:45 AM IST:** Cloud Scheduler starts VM
- **8:45 AM IST:** Trading system auto-starts
- **9:00 AM IST:** Market opens, monitoring begins
- **3:00 PM IST:** Market closes, positions close
- **3:30 PM IST:** VM auto-shuts down

**No manual intervention needed!**

---

## Monthly Costs

| Item | Cost |
|------|------|
| f1-micro VM | $0 (FREE tier) ✅ |
| Storage (30GB) | $0 (FREE tier) ✅ |
| Network | $0 (FREE tier) ✅ |
| Static IP | $1.30 (130 hrs/month) |
| **Total** | **$1.30/month** |

**Annual:** $15.60

---

## Monitoring Your System

### View Logs

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# View logs
tail -f /opt/algo-trading/logs/trading.log
```

### Check VM Status

```bash
# From local machine
gcloud compute instances list

# Should show:
# NAME              ZONE           STATUS
# algo-trading-vm   us-central1-a  RUNNING (or TERMINATED)
```

### Check Today's P&L

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# Check P&L
cd /opt/algo-trading
source venv/bin/activate
python -c "
import sqlite3
from datetime import date
conn = sqlite3.connect('data/trading.db')
cursor = conn.execute(
    'SELECT SUM(realized_pnl) FROM trades WHERE DATE(exit_time) = DATE(?)',
    (str(date.today()),)
)
pnl = cursor.fetchone()[0] or 0
print(f'Today P&L: ₹{pnl:.2f}')
conn.close()
"
```

---

## Troubleshooting

### Issue: VM Won't Start

```bash
# Check VM status
gcloud compute instances describe algo-trading-vm --zone=us-central1-a

# View startup logs
gcloud compute instances get-serial-port-output algo-trading-vm --zone=us-central1-a
```

### Issue: Angel One Connection Failed

1. Verify IP is whitelisted in Angel One portal
2. Wait 10 minutes after whitelisting
3. Check credentials are correct
4. Test again

### Issue: Service Not Running

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# Check service status
sudo systemctl status algo-trading.service

# View logs
sudo journalctl -u algo-trading.service -n 50

# Restart service
sudo systemctl restart algo-trading.service
```

---

## Next Steps

### Week 1: Testing
- Monitor logs daily
- Verify automated start/stop works
- Check positions are tracked correctly
- Review daily summaries

### Month 1-6: Paper Trading
- Run for 90+ trading days
- Track performance metrics
- Document any issues
- Optimize strategies

### Before Live Trading
1. Complete 90-day validation:
   ```bash
   python scripts/validate_paper_trading.py
   ```
2. Review all metrics
3. Pass validation criteria
4. Switch to live mode (if desired)

---

## Support

**Documentation:**
- `SWING_TRADING_DEPLOYMENT.md` - Full guide
- `GCP_DEPLOYMENT_STEPS.md` - This file
- `GOOGLE_CLOUD_DEPLOYMENT.md` - Detailed reference

**Repository:**
https://github.com/GovindarajanL/algo-trading

**Branch:**
`claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6`

---

## Summary

✅ **Deployed** on f1-micro (FREE tier)  
✅ **Static IP** configured for Angel One  
✅ **Auto-shutdown** enabled (saves $6/month)  
✅ **Cloud Scheduler** configured (auto-start at 8:45 AM)  
✅ **Total cost:** $1.30/month  

**System is running autonomously!** 🎉

No daily intervention needed - just monitor logs and performance.
