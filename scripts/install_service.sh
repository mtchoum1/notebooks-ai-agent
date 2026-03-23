#!/bin/bash
# Install DevAssist as a macOS Launch Agent (runs at login)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.devassist.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Installing DevAssist as macOS Launch Agent...${NC}"

# Create LaunchAgents directory if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Create the plist file
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/.venv/bin/python</string>
        <string>$SCRIPT_DIR/devassist_daemon.py</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$HOME/.devassist/daemon_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HOME/.devassist/daemon_stderr.log</string>
    
    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF

echo -e "${GREEN}✓ Created $PLIST_PATH${NC}"

# Load the service
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo -e "${GREEN}✓ Service installed and started${NC}"
echo ""
echo "The daemon will now:"
echo "  - Start automatically when you log in"
echo "  - Generate briefs at 8 AM, 1 PM, and 5 PM"
echo "  - Save briefs to ~/.devassist/briefs/"
echo ""
echo "Commands:"
echo "  Stop:    launchctl unload $PLIST_PATH"
echo "  Start:   launchctl load $PLIST_PATH"
echo "  Status:  launchctl list | grep devassist"
echo "  Logs:    tail -f ~/.devassist/daemon.log"
echo ""
echo -e "${YELLOW}Note: Make sure to run setup_credentials.sh first!${NC}"
