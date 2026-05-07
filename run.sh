#!/bin/bash
# GitHub Weekly Trending Report — WSL entry point
# Called by Windows Task Scheduler every Monday 8:00 AM CST

PROJECT_DIR="/home/laomeo/weekly_github"
LOG_FILE="$PROJECT_DIR/cron.log"

cd "$PROJECT_DIR"

{
    echo "============================================"
    echo "Run started: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    /usr/bin/python3 main.py
    echo "Exit code: $?"
    echo "Run finished: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""
} >> "$LOG_FILE" 2>&1
