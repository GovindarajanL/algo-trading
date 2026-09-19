# Swing Trading Deployment Guide - FREE Forever!

Complete guide for deploying the trading system optimized for **swing trading** on **GCP Free Tier** with **Angel One IP whitelisting**.

---

## Why This Works for Swing Trading

### Resource Requirements Comparison

| Requirement | Intraday Trading | Swing Trading | f1-micro Capable? |
|-------------|------------------|---------------|-------------------|
| **Position checks** | Every 1-5 seconds | Every 5-10 minutes | ✅ Yes |
| **WebSocket** | Required (real-time ticks) | Optional (REST API) | ✅ Yes |
| **Order frequency** | 10-50 orders/day | 1-5 orders/week | ✅ Yes |
| **Memory usage** | 2-4 GB | 0.5-1 GB | ✅ Yes |
| **CPU usage** | Continuous | Periodic bursts | ✅ Yes |
| **Greeks calculation** | Real-time | Every 15-30 min | ✅ Yes |

**Verdict:** f1-micro (0.6GB RAM, 0.2 vCPU) is **perfect** for swing trading!

---

## Cost Breakdown: FREE FOREVER!

### GCP Always Free Tier

| Resource | Free Tier | Our Usage | Cost |
|----------|-----------|-----------|------|
| **VM (f1-micro)** | 1 instance/month | 1 instance | **$0** ✅ |
| **Storage** | 30 GB Standard PD | 20 GB | **$0** ✅ |
| **Network egress** | 1 GB/month | ~0.5 GB | **$0** ✅ |
| **Static IP** | $0.01/hour when in use | 130 hrs/month | **$1.30** ⚠️ |
| **Total** | | | **$1.30/month** |

### Cost Optimization for Static IP

**Option 1: Stop VM when not trading** (Recommended)
```bash
# Static IP cost only when VM is running
# Cost: $0.01/hour × 130 hours = $1.30/month
```

**Option 2: Keep VM running 24/7**
```bash
# Static IP cost: $0.01/hour × 730 hours = $7.30/month
# BUT: VM is still FREE (f1-micro always free tier)
```

**Option 3: Release IP when not needed** (NOT recommended)
```bash
# Cost: $0/month
# Problem: IP changes, need to re-whitelist in Angel One
```

**Recommended:** Option 1 - **Total cost: ~$1.30/month** (95% cheaper than e2-medium!)

---

## Deployment Steps

### Step 1: Setup Static IP (REQUIRED for Angel One)

```bash
# Run the static IP setup script
chmod +x scripts/setup_static_ip.sh
./scripts/setup_static_ip.sh YOUR_PROJECT_ID

# This will:
# 1. Reserve a static external IP
# 2. Create/update VM with static IP
# 3. Display the IP to whitelist
```

**Important:** Save the static IP address displayed!

---

### Step 2: Whitelist IP in Angel One

1. **Login** to Angel One SmartAPI Portal:
   https://smartapi.angelbroking.com/publisher-login

2. **Navigate** to: My API > IP Whitelisting

3. **Add IP address** (from Step 1 output)

4. **Save** and wait 5-10 minutes for propagation

**Note:** You can add multiple IPs (home IP for testing, VM IP for production)

---

### Step 3: Deploy with f1-micro (FREE Tier)

Update the deployment script to use f1-micro:

```bash
# Edit deploy script to use f1-micro
./scripts/deploy_to_gcp.sh

# When prompted:
# VM Name: algo-trading-vm
# Zone: us-central1-a (or us-west1-b, us-east1-b)
# Machine Type: f1-micro  <-- IMPORTANT
# Disk Size: 30 GB
```

Or manually create:

```bash
gcloud compute instances create algo-trading-vm \
    --zone=us-central1-a \
    --machine-type=f1-micro \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --address=STATIC_IP_NAME \
    --scopes=cloud-platform \
    --tags=trading-system
```

---

### Step 4: Setup VM Environment

```bash
# SSH into VM
gcloud compute ssh algo-trading-vm --zone=us-central1-a

# Run setup script
cd /opt/algo-trading
./scripts/setup_vm.sh
```

---

### Step 5: Optimize for Swing Trading

```bash
# Run optimization script
cd /opt/algo-trading
python3 scripts/optimize_for_swing.py

# This configures:
# - Position checks every 5 minutes (vs real-time)
# - REST API polling (vs WebSocket)
# - Greeks updates every 15 minutes
# - Single-threaded execution (low CPU)
# - Memory-optimized settings
```

---

### Step 6: Configure Angel One Credentials

```bash
# Option A: Secret Manager (Recommended)
./scripts/configure_secrets.sh

# Option B: .env file
nano /opt/algo-trading/.env
```

Add credentials:
```bash
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
```

---

### Step 7: Test Angel One Connection

```bash
# Verify IP is whitelisted
cd /opt/algo-trading
source venv/bin/activate
source scripts/load_secrets.sh

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
    print('✅ Connected to Angel One successfully!')
    print('✅ IP whitelisting working!')
else:
    print('❌ Connection failed - check IP whitelisting')
"
```

**Expected output:**
```
✅ Connected to Angel One successfully!
✅ IP whitelisting working!
```

**If failed:**
- Check IP is correctly whitelisted in Angel One portal
- Wait 10 minutes for IP whitelist to propagate
- Verify static IP matches VM's external IP: `curl ifconfig.me`

---

### Step 8: Start Trading System

```bash
# Test manually first
python src/main.py --mode paper

# If successful, start as service
sudo systemctl start algo-trading.service
sudo systemctl status algo-trading.service

# View logs
tail -f logs/trading.log
```

---

## Swing Trading Configuration

### Optimized Settings for f1-micro

```yaml
# config/config.yaml - Optimized for swing trading

data:
  enable_cache: true
  cache_ttl_seconds: 300  # 5 minutes
  use_websocket: false    # Disable WebSocket, use REST API
  polling_interval: 300   # Check prices every 5 minutes

monitoring:
  check_interval: 300     # Monitor positions every 5 minutes
  update_greeks: true
  greeks_interval: 900    # Update Greeks every 15 minutes

strategies:
  iron_condor:
    enabled: true
    check_interval: 600   # Check entry conditions every 10 minutes
    max_positions: 2      # Limit concurrent positions
    
risk_limits:
  max_positions: 3        # Maximum 3 concurrent positions
  position_size_pct: 0.05 # 5% of capital per position

execution:
  order_type: LIMIT       # Use limit orders (not market)
  max_retry: 3
  retry_delay: 30

performance:
  batch_size: 10
  max_workers: 1          # Single thread (low CPU usage)
  db_connection_pool: 1   # Single DB connection
```

---

## Automated Schedule (Optimized)

### Modified Systemd Service for Low Resources

Edit `/etc/systemd/system/algo-trading.service`:

```ini
[Unit]
Description=Algorithmic Options Trading System (Swing Trading)
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/algo-trading
Environment="PATH=/opt/algo-trading/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStartPre=/bin/bash /opt/algo-trading/scripts/load_secrets.sh
ExecStart=/opt/algo-trading/venv/bin/python src/main.py --mode paper
Restart=on-failure
RestartSec=60
StandardOutput=append:/opt/algo-trading/logs/trading.log
StandardError=append:/opt/algo-trading/logs/trading.error.log

# Resource limits for f1-micro
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart algo-trading.service
```

---

## Monitoring & Performance

### Check Resource Usage

```bash
# Memory usage
free -h

# CPU usage
top -bn1 | head -20

# Disk usage
df -h

# Trading system process
ps aux | grep "src/main.py"
```

### Expected Resource Usage (Swing Trading)

| Resource | Usage | f1-micro Limit | Safe? |
|----------|-------|----------------|-------|
| **Memory** | 200-400 MB | 600 MB | ✅ Yes |
| **CPU** | 5-15% average | 20% burst to 60% | ✅ Yes |
| **Disk I/O** | Low | Standard PD | ✅ Yes |
| **Network** | <1 MB/hour | Unlimited | ✅ Yes |

---

## Static IP Management

### Check Current IP

```bash
# From VM
curl ifconfig.me

# From local machine
gcloud compute addresses list
```

### Change IP (If Needed)

```bash
# Release current static IP
gcloud compute addresses delete algo-trading-static-ip --region=us-central1

# Create new static IP
gcloud compute addresses create algo-trading-static-ip --region=us-central1

# Reassign to VM
./scripts/setup_static_ip.sh
```

**Important:** After changing IP, update Angel One whitelist!

---

## Troubleshooting

### Issue: Angel One Connection Refused

**Symptom:**
```
Error: IP not whitelisted
Connection refused
```

**Solution:**
1. Check VM's external IP:
   ```bash
   curl ifconfig.me
   ```

2. Verify this IP is whitelisted in Angel One portal

3. Wait 10 minutes after whitelisting

4. Try connecting again

### Issue: Out of Memory

**Symptom:**
```
MemoryError: Unable to allocate array
Killed (OOM)
```

**Solution:**
1. Reduce max concurrent positions in config:
   ```yaml
   risk_limits:
     max_positions: 2  # Reduce to 2
   ```

2. Increase check intervals:
   ```yaml
   monitoring:
     check_interval: 600  # 10 minutes
   ```

3. Disable unused strategies

4. Restart service:
   ```bash
   sudo systemctl restart algo-trading.service
   ```

### Issue: High CPU Usage

**Symptom:**
```
CPU usage: 95-100%
System slow/unresponsive
```

**Solution:**
1. Increase polling intervals:
   ```yaml
   data:
     polling_interval: 600  # 10 minutes
   ```

2. Disable real-time Greeks:
   ```yaml
   monitoring:
     update_greeks: false
   ```

3. Reduce concurrent operations:
   ```yaml
   performance:
     max_workers: 1
     batch_size: 5
   ```

---

## Cost Comparison

### f1-micro (Free Tier) vs e2-medium

| Configuration | Monthly Cost | Annual Cost |
|---------------|--------------|-------------|
| **f1-micro + Static IP** | **$1.30** | **$15.60** |
| e2-medium (us-central1) | $5.28 | $63.36 |
| **Savings** | **-$3.98** | **-$47.76** |

**Savings: 75% cheaper!**

### ROI Calculation

**Monthly cost:** $1.30 (~₹108 at ₹83/$)

**If 1 profitable trade/month:** ₹500 profit  
**ROI:** 463% per month! 🚀

---

## Best Practices

### DO ✅

- ✅ Use f1-micro for swing trading
- ✅ Setup static IP before whitelisting
- ✅ Keep static IP even when VM is stopped
- ✅ Monitor positions every 5-10 minutes
- ✅ Use REST API (not WebSocket)
- ✅ Limit concurrent positions to 2-3
- ✅ Run paper trading for 90 days
- ✅ Check resource usage weekly

### DON'T ❌

- ❌ Use f1-micro for intraday/HFT trading
- ❌ Enable WebSocket (too resource-intensive)
- ❌ Delete static IP (breaks Angel One whitelist)
- ❌ Run 10+ concurrent positions
- ❌ Check positions every second
- ❌ Skip paper trading validation
- ❌ Upgrade to paid machine without testing

---

## Summary

### Perfect Setup for Swing Trading

| Component | Configuration | Cost | Status |
|-----------|---------------|------|--------|
| **VM** | f1-micro | $0 | ✅ Free Tier |
| **Storage** | 30 GB Standard | $0 | ✅ Free Tier |
| **Network** | 1 GB egress | $0 | ✅ Free Tier |
| **Static IP** | Reserved | $1.30/month | ⚠️ Only cost |
| **Total** | | **$1.30/month** | ✅ |

### Annual Cost: $15.60 (vs $63.36 with e2-medium)

**Savings: 75% cheaper, runs forever on free tier!**

---

## Quick Start Commands

```bash
# 1. Setup static IP
./scripts/setup_static_ip.sh YOUR_PROJECT_ID

# 2. Whitelist IP in Angel One portal
# (Use IP from step 1 output)

# 3. Deploy f1-micro VM
./scripts/deploy_to_gcp.sh
# Machine type: f1-micro

# 4. SSH and setup
gcloud compute ssh algo-trading-vm --zone=us-central1-a
./scripts/setup_vm.sh

# 5. Optimize for swing trading
python3 scripts/optimize_for_swing.py

# 6. Configure credentials
./scripts/configure_secrets.sh

# 7. Test connection
python src/main.py --mode paper

# 8. Start service
sudo systemctl start algo-trading.service
```

---

**Ready to deploy for FREE? Let's go!** 🚀
