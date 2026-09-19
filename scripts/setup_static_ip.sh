#!/bin/bash
# Setup Static IP for Angel One IP Whitelisting
# This ensures the VM always uses the same IP address

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup Static IP for Angel One${NC}"
echo -e "${GREEN}================================${NC}"

# Get configuration
if [ -z "$1" ]; then
    echo -e "\n${YELLOW}Enter your Google Cloud Project ID:${NC}"
    read PROJECT_ID
else
    PROJECT_ID=$1
fi

echo -e "\n${YELLOW}Enter the region [us-central1]:${NC}"
read REGION
REGION=${REGION:-us-central1}

echo -e "\n${YELLOW}Enter the VM name [algo-trading-vm]:${NC}"
read VM_NAME
VM_NAME=${VM_NAME:-algo-trading-vm}

echo -e "\n${YELLOW}Enter the zone [us-central1-a]:${NC}"
read ZONE
ZONE=${ZONE:-us-central1-a}

# Set project
gcloud config set project $PROJECT_ID

echo -e "\n${GREEN}Step 1: Reserve a static external IP${NC}"
echo "This IP will be whitelisted in Angel One portal"

# Reserve static IP
gcloud compute addresses create algo-trading-static-ip \
    --region=$REGION \
    2>&1 | tee /tmp/gcp_ip_output.txt || {
    if grep -q "already exists" /tmp/gcp_ip_output.txt; then
        echo -e "${YELLOW}Static IP already exists, using existing one${NC}"
    else
        echo -e "${RED}Failed to create static IP${NC}"
        exit 1
    fi
}

# Get the static IP address
STATIC_IP=$(gcloud compute addresses describe algo-trading-static-ip \
    --region=$REGION \
    --format="get(address)")

echo -e "\n${GREEN}Static IP Reserved: $STATIC_IP${NC}"

# Check if VM exists
VM_EXISTS=$(gcloud compute instances list --filter="name=$VM_NAME" --format="value(name)" | wc -l)

if [ "$VM_EXISTS" -eq "0" ]; then
    echo -e "\n${YELLOW}VM does not exist yet. Creating with static IP...${NC}"

    # Create VM with static IP
    gcloud compute instances create $VM_NAME \
        --zone=$ZONE \
        --machine-type=f1-micro \
        --boot-disk-size=30GB \
        --boot-disk-type=pd-standard \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --address=$STATIC_IP \
        --scopes=cloud-platform \
        --tags=trading-system

    echo -e "\n${GREEN}VM created with static IP${NC}"
else
    echo -e "\n${YELLOW}VM already exists. Assigning static IP...${NC}"

    # Stop VM
    echo "Stopping VM..."
    gcloud compute instances stop $VM_NAME --zone=$ZONE 2>/dev/null || true
    sleep 5

    # Delete existing access config (ephemeral IP)
    echo "Removing ephemeral IP..."
    gcloud compute instances delete-access-config $VM_NAME \
        --zone=$ZONE \
        --access-config-name="external-nat" \
        2>/dev/null || true

    # Add new access config with static IP
    echo "Assigning static IP..."
    gcloud compute instances add-access-config $VM_NAME \
        --zone=$ZONE \
        --access-config-name="external-nat" \
        --address=$STATIC_IP

    # Start VM
    echo "Starting VM..."
    gcloud compute instances start $VM_NAME --zone=$ZONE

    echo -e "\n${GREEN}Static IP assigned to existing VM${NC}"
fi

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Static IP Configuration Complete${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Your Static IP Address:${NC}"
echo -e "${GREEN}$STATIC_IP${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Login to Angel One SmartAPI Portal:"
echo "   https://smartapi.angelbroking.com/publisher-login"
echo ""
echo "2. Navigate to: My API > IP Whitelisting"
echo ""
echo "3. Add this IP address:"
echo -e "   ${GREEN}$STATIC_IP${NC}"
echo ""
echo "4. Save and wait 5-10 minutes for changes to propagate"
echo ""
echo "5. Test the connection:"
echo "   gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "   cd /opt/algo-trading"
echo "   source venv/bin/activate"
echo "   python src/main.py --mode paper"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "• This IP will NEVER change (static)"
echo "• Cost: $0.01/hour (~$7.30/month when VM is running)"
echo "• Cost: $0.00 when VM is stopped (IP reserved but not in use)"
echo "• With auto-shutdown: ~$0.95/month (130 hours)"
echo ""
echo -e "${GREEN}Static IP setup complete!${NC}"
