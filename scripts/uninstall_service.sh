#!/bin/bash
# Uninstall DevAssist macOS Launch Agent

PLIST_NAME="com.devassist.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo "Uninstalling DevAssist Launch Agent..."

if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null
    rm "$PLIST_PATH"
    echo -e "${GREEN}✓ Service uninstalled${NC}"
else
    echo "Service not installed"
fi
