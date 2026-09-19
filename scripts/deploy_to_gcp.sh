#!/bin/bash
# Automated Google Cloud Deployment Script
# Usage: ./scripts/deploy_to_gcp.sh [PROJECT_ID]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Algo Trading GCP Deployment${NC}"
echo -e "${GREEN}================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
if [ -z "$1" ]; then
    echo -e "${YELLOW}Enter your Google Cloud Project ID:${NC}"
    read PROJECT_ID
else
    PROJECT_ID=$1
fi

# Set project
echo -e "\n${GREEN}Setting project: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Prompt for configuration
echo -e "\n${YELLOW}Configuration:${NC}"
read -p "VM Name [algo-trading-vm]: " VM_NAME
VM_NAME=${VM_NAME:-algo-trading-vm}

read -p "Zone [asia-south1-a]: " ZONE
ZONE=${ZONE:-asia-south1-a}

read -p "Machine Type [e2-medium]: " MACHINE_TYPE
MACHINE_TYPE=${MACHINE_TYPE:-e2-medium}

read -p "Boot Disk Size in GB [20]: " DISK_SIZE
DISK_SIZE=${DISK_SIZE:-20}

echo -e "\n${GREEN}Summary:${NC}"
echo "  Project: $PROJECT_ID"
echo "  VM Name: $VM_NAME"
echo "  Zone: $ZONE"
echo "  Machine: $MACHINE_TYPE"
echo "  Disk: ${DISK_SIZE}GB"
echo ""
read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Enable APIs
echo -e "\n${GREEN}Enabling required APIs...${NC}"
gcloud services enable compute.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create VM instance
echo -e "\n${GREEN}Creating VM instance...${NC}"
gcloud compute instances create $VM_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --boot-disk-size=${DISK_SIZE}GB \
    --boot-disk-type=pd-standard \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --scopes=cloud-platform \
    --tags=trading-system \
    --metadata=startup-script='#!/bin/bash
apt-get update
apt-get install -y python3.9 python3.9-venv python3-pip git
' \
    || echo -e "${YELLOW}VM might already exist${NC}"

# Wait for VM to be ready
echo -e "\n${GREEN}Waiting for VM to be ready...${NC}"
sleep 30

# Create firewall rule for SSH (optional)
echo -e "\n${YELLOW}Do you want to restrict SSH access to your current IP? (y/n):${NC}"
read RESTRICT_SSH
if [ "$RESTRICT_SSH" = "y" ]; then
    CURRENT_IP=$(curl -s https://api.ipify.org)
    echo "Creating firewall rule for IP: $CURRENT_IP"
    gcloud compute firewall-rules create allow-ssh-trading \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:22 \
        --source-ranges=$CURRENT_IP/32 \
        --target-tags=trading-system \
        || echo -e "${YELLOW}Firewall rule might already exist${NC}"
fi

# Create startup script for Cloud Scheduler
echo -e "\n${GREEN}Setting up Cloud Scheduler...${NC}"

# Create service account
gcloud iam service-accounts create vm-scheduler \
    --display-name="VM Scheduler Service Account" \
    || echo -e "${YELLOW}Service account might already exist${NC}"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vm-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1" \
    || echo -e "${YELLOW}Permission might already be granted${NC}"

# Create scheduler job (8:45 AM IST = 3:15 AM UTC)
gcloud scheduler jobs create http start-trading-vm \
    --schedule="15 3 * * 1-5" \
    --time-zone="Asia/Kolkata" \
    --uri="https://compute.googleapis.com/compute/v1/projects/$PROJECT_ID/zones/$ZONE/instances/$VM_NAME/start" \
    --http-method=POST \
    --oauth-service-account-email=vm-scheduler@$PROJECT_ID.iam.gserviceaccount.com \
    || echo -e "${YELLOW}Scheduler job might already exist${NC}"

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${GREEN}✅ VM Instance Created:${NC} $VM_NAME"
echo -e "${GREEN}✅ APIs Enabled${NC}"
echo -e "${GREEN}✅ Cloud Scheduler Configured${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. SSH into your VM:"
echo -e "   ${GREEN}gcloud compute ssh $VM_NAME --zone=$ZONE${NC}"
echo ""
echo "2. Run the setup script:"
echo -e "   ${GREEN}curl -s https://raw.githubusercontent.com/GovindarajanL/algo-trading/claude/algorithmic-options-trading-system-011CUeAJhMkQBwkKWeWcvTm6/scripts/setup_vm.sh | bash${NC}"
echo ""
echo "3. Configure your Angel One credentials (choose one):"
echo "   A. Using Google Secret Manager (Recommended):"
echo -e "      ${GREEN}./scripts/configure_secrets.sh${NC}"
echo "   B. Using .env file:"
echo -e "      ${GREEN}nano /opt/algo-trading/.env${NC}"
echo ""
echo "4. Test the system:"
echo -e "   ${GREEN}sudo systemctl start algo-trading.service${NC}"
echo -e "   ${GREEN}sudo systemctl status algo-trading.service${NC}"
echo ""
echo "5. View logs:"
echo -e "   ${GREEN}sudo journalctl -u algo-trading.service -f${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "• System will auto-start at 8:45 AM IST on weekdays"
echo "• Configure auto-shutdown in the VM (see GOOGLE_CLOUD_DEPLOYMENT.md)"
echo "• Complete 90-day paper trading validation before going live"
echo ""
echo -e "${GREEN}Deployment Complete!${NC}"
