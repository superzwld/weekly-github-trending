#!/bin/bash
# GitHub Weekly Trending Report — WSL entry point
# Called by Windows Task Scheduler every Monday 8:00 AM CST

PROJECT_DIR="/home/laomeo/weekly_github"
LOG_FILE="$PROJECT_DIR/cron.log"

cd "$PROJECT_DIR"

{
    echo "============================================"
    echo "Run started: $(date '+%Y-%m-%d %H:%M:%S %Z')"

    # 等待网络就绪：最多重试 20 次（共约 100 秒），每次间隔 5 秒
    MAX_RETRIES=20
    RETRY_INTERVAL=5
    attempt=1
    while [ $attempt -le $MAX_RETRIES ]; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
            "https://api.github.com" 2>/dev/null)

        if [ "$HTTP_CODE" = "200" ]; then
            echo "网络连通 (HTTP $HTTP_CODE)，开始执行周报生成"
            break
        fi

        echo "等待网络就绪 (尝试 $attempt/$MAX_RETRIES, HTTP $HTTP_CODE)..."
        sleep $RETRY_INTERVAL
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $MAX_RETRIES ]; then
        echo "错误：无法连接 GitHub API，请检查网络"
        echo "Run failed: $(date '+%Y-%m-%d %H:%M:%S %Z')"
        echo ""
        exit 1
    fi

    /usr/bin/python3 main.py
    echo "Exit code: $?"
    echo "Run finished: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""
} >> "$LOG_FILE" 2>&1
