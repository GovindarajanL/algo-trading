# Deployment Guide

## Algorithmic Options Trading System

### Overview

This guide covers deploying the trading system for both paper trading and live trading environments.

## Pre-Deployment Checklist

### ⚠️ Critical Requirements

- [ ] Completed minimum 6 months successful paper trading
- [ ] Positive risk-adjusted returns demonstrated
- [ ] Sharpe ratio > 1.0
- [ ] Maximum drawdown < 30%
- [ ] Zero system failures in last month
- [ ] All tests passing
- [ ] Configuration validated
- [ ] Emergency procedures tested

### System Requirements

**Hardware**:
- Minimum: 4GB RAM, 2 CPU cores, 20GB storage
- Recommended: 8GB RAM, 4 CPU cores, 50GB storage
- VPS in Mumbai region (low latency to NSE)

**Software**:
- Python 3.8 or higher
- Ubuntu 20.04 LTS or equivalent
- PostgreSQL 12+ (recommended for production)

**Network**:
- Stable internet connection
- < 100ms latency to Angel One API
- Backup connection recommended

## Development Environment

### Local Setup

```bash
# Clone repository
git clone <repository-url>
cd algo-trading

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/.env.example config/.env
# Edit config/.env with credentials

# Verify setup
python -c "from src.utils.config_loader import ConfigLoader; c=ConfigLoader(); print('✅ Setup OK')"
```

### Configuration

Edit `config/.env`:
```bash
API_KEY=your_api_key
CLIENT_ID=your_client_id
PASSWORD=your_password
TOTP_SECRET=your_totp_secret
TRADING_MODE=paper  # IMPORTANT: Start with paper
```

Edit `config/risk_limits.yaml`:
```yaml
total_capital: 50000         # Your trading capital
max_loss_per_trade: 1000     # Maximum loss per trade
max_daily_loss: 5000         # Daily loss limit
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Test configuration
python -m src.utils.config_loader

# Test risk validation
pytest tests/test_risk.py -v
```

## Paper Trading Deployment

### Purpose
- Strategy validation
- System reliability testing
- Risk management verification
- No real money risk

### Setup

```bash
# Ensure paper mode
echo "TRADING_MODE=paper" >> config/.env

# Start paper trading
python src/main.py --mode paper
```

### Monitoring

Monitor these metrics daily:
- Win/loss ratio
- Average P&L per trade
- Maximum drawdown
- Sharpe ratio
- System uptime
- Error rate

### Success Criteria

Continue paper trading until:
- ✅ 6 months of consistent profitability
- ✅ Sharpe ratio > 1.0
- ✅ Win rate > 50%
- ✅ Max drawdown < 30%
- ✅ No missed exits
- ✅ No system crashes
- ✅ Risk limits never breached

## Production (Live Trading) Deployment

### ⚠️ WARNING

**Live trading risks real money. Do not proceed unless:**
- Paper trading successful for 6+ months
- All team members agree
- Capital allocation decided
- Emergency procedures tested
- Backup systems in place

### VPS Setup (Recommended: AWS EC2 / DigitalOcean)

#### 1. Create VPS

```bash
# Recommended: Ubuntu 20.04 LTS
# Region: Mumbai (ap-south-1 for AWS)
# Size: 4GB RAM, 2 CPUs minimum

# Connect to VPS
ssh user@your-vps-ip
```

#### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.8 python3.8-venv python3-pip -y

# Install PostgreSQL (optional but recommended)
sudo apt install postgresql postgresql-contrib -y

# Install monitoring tools
sudo apt install htop iotop -y
```

#### 3. Setup Application

```bash
# Create application directory
mkdir -p ~/algo-trading
cd ~/algo-trading

# Clone repository
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Configure Production

```bash
# Copy configuration
cp config/.env.example config/.env

# IMPORTANT: Use live mode
nano config/.env
```

Set in `.env`:
```bash
TRADING_MODE=live  # ⚠️  LIVE TRADING MODE
API_KEY=your_production_api_key
CLIENT_ID=your_production_client_id
# ... other credentials
```

Edit risk limits for production:
```bash
nano config/risk_limits.yaml
```

#### 5. Setup Database

```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE algo_trading;
CREATE USER trading_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE algo_trading TO trading_user;
\q

# Update .env with database credentials
nano config/.env
# Add: DATABASE_TYPE=postgresql
# Add: DATABASE_HOST=localhost
# Add: DATABASE_NAME=algo_trading
# Add: DATABASE_USER=trading_user
# Add: DATABASE_PASSWORD=secure_password
```

#### 6. Setup Systemd Service

Create service file:
```bash
sudo nano /etc/systemd/system/algo-trading.service
```

Content:
```ini
[Unit]
Description=Algorithmic Options Trading System
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/algo-trading
Environment="PATH=/home/ubuntu/algo-trading/venv/bin"
ExecStart=/home/ubuntu/algo-trading/venv/bin/python src/main.py --mode live
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/algo-trading/logs/service.log
StandardError=append:/home/ubuntu/algo-trading/logs/service_error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable algo-trading
sudo systemctl start algo-trading

# Check status
sudo systemctl status algo-trading
```

#### 7. Setup Monitoring

Create monitoring script:
```bash
nano ~/monitor.sh
```

```bash
#!/bin/bash
# Check if trading system is running
if ! systemctl is-active --quiet algo-trading; then
    echo "ALERT: Trading system is down!" | mail -s "Trading System Alert" your@email.com
    sudo systemctl restart algo-trading
fi

# Check disk space
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "ALERT: Disk usage is ${DISK_USAGE}%" | mail -s "Disk Space Alert" your@email.com
fi
```

```bash
chmod +x ~/monitor.sh

# Add to crontab (run every 5 minutes)
crontab -e
# Add: */5 * * * * /home/ubuntu/monitor.sh
```

#### 8. Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/algo-trading
```

```
/home/ubuntu/algo-trading/logs/*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload algo-trading > /dev/null 2>&1 || true
    endscript
}
```

#### 9. Setup Firewall

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow from specific IPs only (recommended)
sudo ufw allow from your.ip.address.here to any port 22

# Check status
sudo ufw status
```

#### 10. Setup Backups

```bash
# Create backup script
nano ~/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y-%m-%d)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump algo_trading > $BACKUP_DIR/db_backup_$DATE.sql

# Backup configuration
cp -r /home/ubuntu/algo-trading/config $BACKUP_DIR/config_$DATE

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /home/ubuntu/algo-trading/logs/

# Remove backups older than 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x ~/backup.sh

# Add to crontab (daily at 4 AM)
crontab -e
# Add: 0 4 * * * /home/ubuntu/backup.sh
```

## Post-Deployment

### Daily Checklist

- [ ] Check system logs
- [ ] Verify positions reconciliation
- [ ] Review P&L
- [ ] Check circuit breaker status
- [ ] Monitor system health
- [ ] Verify backups completed

### Weekly Checklist

- [ ] Review performance metrics
- [ ] Analyze losing trades
- [ ] Check for strategy improvements
- [ ] Update configuration if needed
- [ ] Test emergency procedures
- [ ] Review system alerts

### Monthly Checklist

- [ ] Full system audit
- [ ] Review and rotate logs
- [ ] Update dependencies
- [ ] Backup verification
- [ ] Performance report
- [ ] Strategy evaluation

## Emergency Procedures

### Kill Switch (Stop All Trading)

```bash
# Stop system immediately
sudo systemctl stop algo-trading

# Or from inside the system
pkill -f "python src/main.py"
```

### Emergency Square-Off

```bash
# From system directory
python src/emergency_squareoff.py --confirm
```

### System Restart

```bash
# Restart service
sudo systemctl restart algo-trading

# Check logs
tail -f logs/trading_$(date +%Y-%m-%d).log
```

### Recovery from Failure

1. Check logs: `tail -f logs/*.log`
2. Verify positions with broker
3. Reconcile database with broker data
4. Fix issue
5. Restart system
6. Monitor closely

## Monitoring and Alerts

### Telegram Alerts

Configured in `config/.env`:
- Trade entry/exit
- Circuit breaker triggers
- System errors
- Daily summary

### Email Alerts

Configure SMTP in `config/.env` for critical alerts.

### Dashboard Access

```bash
# Access system dashboard
# (To be implemented)
```

## Troubleshooting

### System Won't Start

```bash
# Check logs
sudo journalctl -u algo-trading -n 50

# Check configuration
python -c "from src.utils.config_loader import ConfigLoader; ConfigLoader()"

# Check permissions
ls -la ~/algo-trading/logs/
```

### API Connection Issues

```bash
# Test API connection
python -c "from src.broker.angel_one import test_connection; test_connection()"

# Check credentials
cat config/.env | grep API_KEY
```

### Database Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Access database
psql -U trading_user -d algo_trading
```

## Security Considerations

- [ ] Credentials stored securely (not in git)
- [ ] Firewall configured
- [ ] SSH key-only authentication
- [ ] Regular security updates
- [ ] Backup encryption
- [ ] Log file permissions
- [ ] API key rotation schedule

## Performance Optimization

### Database
- Index commonly queried fields
- Vacuum regularly
- Monitor query performance

### System
- Monitor CPU/RAM usage
- Optimize data collection
- Cache frequently accessed data

## Support

For deployment issues:
- Check logs first
- Review documentation
- GitHub Issues
- Email: [your-email]

---

**⚠️  FINAL WARNING**: Live trading risks real capital. Ensure you understand all risks and have tested extensively in paper mode before going live. Start with small capital and scale gradually.
