#!/bin/bash
# VM Setup Script - Run this inside the GCP VM
# This script sets up the complete trading environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}VM Setup for Algo Trading${NC}"
echo -e "${GREEN}================================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please run as regular user, not root${NC}"
   exit 1
fi

# Update system
echo -e "\n${GREEN}Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
echo -e "\n${GREEN}Installing dependencies...${NC}"
sudo apt-get install -y \
    python3.9 \
    python3.9-venv \
    python3-pip \
    git \
    sqlite3 \
    curl \
    wget \
    htop \
    vim

# Create application directory
echo -e "\n${GREEN}Creating application directory...${NC}"
sudo mkdir -p /opt/algo-trading
sudo chown $USER:$USER /opt/algo-trading
cd /opt/algo-trading

# Clone repository
echo -e "\n${GREEN}Cloning repository...${NC}"
if [ -d ".git" ]; then
    echo "Repository already exists, pulling latest changes..."
    git pull origin claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6
else
    git clone https://github.com/GovindarajanL/algo-trading.git .
    git checkout claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6
fi

# Create virtual environment
echo -e "\n${GREEN}Creating Python virtual environment...${NC}"
python3.9 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo -e "\n${GREEN}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Create necessary directories
echo -e "\n${GREEN}Creating directories...${NC}"
mkdir -p data logs database backups scripts

# Initialize database
echo -e "\n${GREEN}Initializing database...${NC}"
if [ -f "scripts/init_database.py" ]; then
    python scripts/init_database.py
else
    echo -e "${YELLOW}Warning: Database initialization script not found${NC}"
fi

# Create load_secrets.sh script
echo -e "\n${GREEN}Creating secrets loader script...${NC}"
cat > scripts/load_secrets.sh << 'EOF'
#!/bin/bash
# Load secrets from Google Secret Manager

# Check if running in GCP
if command -v gcloud &> /dev/null; then
    # Try to load from Secret Manager
    export ANGEL_ONE_API_KEY=$(gcloud secrets versions access latest --secret="angel-one-api-key" 2>/dev/null || echo "")
    export ANGEL_ONE_CLIENT_CODE=$(gcloud secrets versions access latest --secret="angel-one-client-code" 2>/dev/null || echo "")
    export ANGEL_ONE_PASSWORD=$(gcloud secrets versions access latest --secret="angel-one-password" 2>/dev/null || echo "")
    export ANGEL_ONE_TOTP_SECRET=$(gcloud secrets versions access latest --secret="angel-one-totp-secret" 2>/dev/null || echo "")
    export TELEGRAM_BOT_TOKEN=$(gcloud secrets versions access latest --secret="telegram-bot-token" 2>/dev/null || echo "")
    export TELEGRAM_CHAT_ID=$(gcloud secrets versions access latest --secret="telegram-chat-id" 2>/dev/null || echo "")

    if [ -z "$ANGEL_ONE_API_KEY" ]; then
        echo "Warning: Secrets not found in Secret Manager, checking .env file..."
    fi
fi

# Fallback to .env file
if [ -f "/opt/algo-trading/.env" ]; then
    source /opt/algo-trading/.env
fi

# Verify secrets are loaded
if [ -z "$ANGEL_ONE_API_KEY" ]; then
    echo "ERROR: ANGEL_ONE_API_KEY not set!"
    exit 1
fi
EOF
chmod +x scripts/load_secrets.sh

# Create startup.sh script
echo -e "\n${GREEN}Creating startup script...${NC}"
cat > scripts/startup.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Algo Trading System Startup ==="
date

# Load secrets
source /opt/algo-trading/scripts/load_secrets.sh

# Activate virtual environment
cd /opt/algo-trading
source venv/bin/activate

# Pull latest code (optional - commented out for safety)
# git pull origin claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6

# Backup previous day's database
if [ -f "data/trading.db" ]; then
    cp data/trading.db "backups/trading_$(date +%Y%m%d_%H%M%S).db"
fi

# Start trading system
echo "Starting trading system at $(date)"
python src/main.py --mode paper 2>&1 | tee -a logs/trading_$(date +%Y%m%d).log
EOF
chmod +x scripts/startup.sh

# Create shutdown.sh script
echo -e "\n${GREEN}Creating shutdown script...${NC}"
cat > scripts/shutdown.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Graceful Shutdown Started ==="
date

# Load secrets for Telegram notification
source /opt/algo-trading/scripts/load_secrets.sh

# Send Telegram notification
if [ ! -z "$TELEGRAM_BOT_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=🔴 Trading system shutting down at $(date)" \
        2>/dev/null || true
fi

# Stop trading service gracefully
sudo systemctl stop algo-trading.service || true

# Backup database
BACKUP_DIR="/opt/algo-trading/backups"
mkdir -p $BACKUP_DIR
if [ -f "/opt/algo-trading/data/trading.db" ]; then
    cp /opt/algo-trading/data/trading.db "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db"
    echo "Database backed up"
fi

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "trading_*.db" -mtime +30 -delete 2>/dev/null || true

# Clean old logs (keep last 30 days)
find /opt/algo-trading/logs -name "*.log" -mtime +30 -delete 2>/dev/null || true

echo "Shutdown complete. VM will power off in 10 seconds..."
sleep 10

# Shutdown VM
sudo shutdown -h now
EOF
chmod +x scripts/shutdown.sh

# Create backup script
echo -e "\n${GREEN}Creating backup script...${NC}"
cat > scripts/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/algo-trading/backups"
mkdir -p $BACKUP_DIR

# Local backup
if [ -f "/opt/algo-trading/data/trading.db" ]; then
    cp /opt/algo-trading/data/trading.db \
       "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db"
    echo "Database backed up at $(date)"
fi

# Optional: Upload to Cloud Storage
# Uncomment and configure after creating bucket
# gsutil cp "$BACKUP_DIR/trading_$(date +%Y%m%d_%H%M%S).db" \
#    gs://YOUR_BUCKET/backups/

# Keep only last 30 days locally
find $BACKUP_DIR -name "trading_*.db" -mtime +30 -delete 2>/dev/null || true
EOF
chmod +x scripts/backup_db.sh

# Create systemd service
echo -e "\n${GREEN}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/algo-trading.service > /dev/null << EOF
[Unit]
Description=Algorithmic Options Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/algo-trading
Environment="PATH=/opt/algo-trading/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
EOF

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable algo-trading.service

# Setup cron jobs
echo -e "\n${GREEN}Setting up cron jobs...${NC}"
(crontab -l 2>/dev/null; echo "# Trading system auto-shutdown at 3:30 PM IST") | crontab -
(crontab -l 2>/dev/null; echo "30 15 * * 1-5 /opt/algo-trading/scripts/shutdown.sh") | crontab -
(crontab -l 2>/dev/null; echo "") | crontab -
(crontab -l 2>/dev/null; echo "# Database backup every hour during trading hours") | crontab -
(crontab -l 2>/dev/null; echo "0 9-15 * * 1-5 /opt/algo-trading/scripts/backup_db.sh") | crontab -

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}VM Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Configure Angel One credentials:"
echo "   Option A (Recommended): Use Secret Manager"
echo -e "      ${GREEN}Run: ./scripts/configure_secrets.sh${NC}"
echo ""
echo "   Option B: Create .env file"
echo -e "      ${GREEN}nano /opt/algo-trading/.env${NC}"
echo "      Add your credentials (see .env.example)"
echo ""
echo "2. Test the secrets:"
echo -e "   ${GREEN}source scripts/load_secrets.sh${NC}"
echo -e "   ${GREEN}echo \$ANGEL_ONE_API_KEY${NC}"
echo ""
echo "3. Test the trading system manually:"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "   ${GREEN}python src/main.py --mode paper${NC}"
echo ""
echo "4. If successful, start the service:"
echo -e "   ${GREEN}sudo systemctl start algo-trading.service${NC}"
echo -e "   ${GREEN}sudo systemctl status algo-trading.service${NC}"
echo ""
echo "5. View logs:"
echo -e "   ${GREEN}sudo journalctl -u algo-trading.service -f${NC}"
echo "   or"
echo -e "   ${GREEN}tail -f logs/trading.log${NC}"
echo ""
echo -e "${YELLOW}Scheduled Tasks:${NC}"
echo "• Auto-shutdown: 3:30 PM IST (weekdays)"
echo "• Database backup: Every hour 9 AM - 3 PM (weekdays)"
echo "• VM auto-start: Configured in Cloud Scheduler"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
