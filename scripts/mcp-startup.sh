#!/bin/bash
# MCP Startup Script
#
# Auto-start MCP daemons on session start.
# Called by SessionStart hook.
#
# Exit codes:
#   0 = Success (all daemons started or not needed)
#   1 = Warning (some daemons failed to start)
#   2 = Error (critical daemon failed)

# Check if Serena daemon should be started
check_serena() {
    # Look for Serena MCP in config
    if command -v serena &> /dev/null; then
        if ! pgrep -f "serena" > /dev/null 2>&1; then
            echo "MCP_STARTUP: Starting Serena daemon..."
            # Start in background
            nohup serena --daemon > /dev/null 2>&1 &
            sleep 2
            if pgrep -f "serena" > /dev/null 2>&1; then
                echo "MCP_STARTUP: Serena started successfully"
            else
                echo "MCP_STARTUP: Warning - Serena failed to start"
                return 1
            fi
        else
            echo "MCP_STARTUP: Serena already running"
        fi
    fi
    return 0
}

# Main
main() {
    local warnings=0

    # Start configured MCP daemons
    check_serena || ((warnings++))

    # Add more daemon checks as needed
    # check_playwright || ((warnings++))
    # check_custom_mcp || ((warnings++))

    if [ $warnings -gt 0 ]; then
        echo "MCP_STARTUP: Completed with $warnings warnings"
        exit 1
    fi

    exit 0
}

main "$@"
