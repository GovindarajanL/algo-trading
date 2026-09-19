#!/bin/bash
# Configure Angel One Credentials in Google Secret Manager
# Run this script inside the GCP VM

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Configure Angel One Secrets${NC}"
echo -e "${GREEN}================================${NC}"

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "This script should be run inside a GCP VM"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo -e "\n${GREEN}Project ID: $PROJECT_ID${NC}"

echo -e "\n${YELLOW}Please enter your Angel One credentials:${NC}"
echo "(These will be securely stored in Google Secret Manager)"
echo ""

# Angel One API Key
read -p "Angel One API Key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo -e "${RED}API Key cannot be empty${NC}"
    exit 1
fi

# Angel One Client Code
read -p "Angel One Client Code: " CLIENT_CODE
if [ -z "$CLIENT_CODE" ]; then
    echo -e "${RED}Client Code cannot be empty${NC}"
    exit 1
fi

# Angel One Password
read -sp "Angel One Password: " PASSWORD
echo ""
if [ -z "$PASSWORD" ]; then
    echo -e "${RED}Password cannot be empty${NC}"
    exit 1
fi

# Angel One TOTP Secret
read -sp "Angel One TOTP Secret: " TOTP_SECRET
echo ""
if [ -z "$TOTP_SECRET" ]; then
    echo -e "${RED}TOTP Secret cannot be empty${NC}"
    exit 1
fi

# Telegram Bot Token (optional)
read -p "Telegram Bot Token (optional, press Enter to skip): " TELEGRAM_TOKEN

# Telegram Chat ID (optional)
if [ ! -z "$TELEGRAM_TOKEN" ]; then
    read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID
fi

echo -e "\n${GREEN}Creating secrets in Google Secret Manager...${NC}"

# Create secrets
echo "$API_KEY" | gcloud secrets create angel-one-api-key --data-file=- 2>/dev/null \
    || (echo "$API_KEY" | gcloud secrets versions add angel-one-api-key --data-file=-)

echo "$CLIENT_CODE" | gcloud secrets create angel-one-client-code --data-file=- 2>/dev/null \
    || (echo "$CLIENT_CODE" | gcloud secrets versions add angel-one-client-code --data-file=-)

echo "$PASSWORD" | gcloud secrets create angel-one-password --data-file=- 2>/dev/null \
    || (echo "$PASSWORD" | gcloud secrets versions add angel-one-password --data-file=-)

echo "$TOTP_SECRET" | gcloud secrets create angel-one-totp-secret --data-file=- 2>/dev/null \
    || (echo "$TOTP_SECRET" | gcloud secrets versions add angel-one-totp-secret --data-file=-)

if [ ! -z "$TELEGRAM_TOKEN" ]; then
    echo "$TELEGRAM_TOKEN" | gcloud secrets create telegram-bot-token --data-file=- 2>/dev/null \
        || (echo "$TELEGRAM_TOKEN" | gcloud secrets versions add telegram-bot-token --data-file=-)

    echo "$TELEGRAM_CHAT_ID" | gcloud secrets create telegram-chat-id --data-file=- 2>/dev/null \
        || (echo "$TELEGRAM_CHAT_ID" | gcloud secrets versions add telegram-chat-id --data-file=-)
fi

echo -e "\n${GREEN}Granting VM access to secrets...${NC}"

# Get compute service account
COMPUTE_SA=$(gcloud iam service-accounts list --filter="displayName:Compute Engine default service account" --format="value(email)")

if [ -z "$COMPUTE_SA" ]; then
    echo -e "${YELLOW}Warning: Could not find default compute service account${NC}"
    echo "You may need to manually grant access to secrets"
else
    # Grant access to secrets
    for SECRET in angel-one-api-key angel-one-client-code angel-one-password angel-one-totp-secret telegram-bot-token telegram-chat-id; do
        gcloud secrets add-iam-policy-binding $SECRET \
            --member="serviceAccount:$COMPUTE_SA" \
            --role="roles/secretmanager.secretAccessor" \
            2>/dev/null || true
    done
fi

echo -e "\n${GREEN}Testing secret access...${NC}"

# Test loading a secret
TEST_KEY=$(gcloud secrets versions access latest --secret="angel-one-api-key" 2>/dev/null)
if [ ! -z "$TEST_KEY" ]; then
    echo -e "${GREEN}✅ Secrets configured successfully!${NC}"
else
    echo -e "${RED}❌ Error: Could not access secrets${NC}"
    echo "Please check IAM permissions"
    exit 1
fi

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Configuration Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Secrets stored in Google Secret Manager:${NC}"
echo "  • angel-one-api-key"
echo "  • angel-one-client-code"
echo "  • angel-one-password"
echo "  • angel-one-totp-secret"
if [ ! -z "$TELEGRAM_TOKEN" ]; then
    echo "  • telegram-bot-token"
    echo "  • telegram-chat-id"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test loading secrets:"
echo -e "   ${GREEN}source /opt/algo-trading/scripts/load_secrets.sh${NC}"
echo -e "   ${GREEN}echo \$ANGEL_ONE_API_KEY${NC}"
echo ""
echo "2. Test the trading system:"
echo -e "   ${GREEN}cd /opt/algo-trading${NC}"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "   ${GREEN}python src/main.py --mode paper${NC}"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
