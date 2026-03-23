#!/bin/bash
# Stop DevAssist Daemon

CONFIG_DIR="$HOME/.devassist"
PID_FILE="$CONFIG_DIR/daemon.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping daemon (PID: $PID)..."
        kill "$PID"
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Force killing..."
            kill -9 "$PID"
        fi
        rm "$PID_FILE"
        echo -e "${GREEN}✓ Daemon stopped${NC}"
    else
        echo -e "${RED}Daemon not running (stale PID file)${NC}"
        rm "$PID_FILE"
    fi
else
    echo -e "${RED}Daemon not running (no PID file)${NC}"
fi
