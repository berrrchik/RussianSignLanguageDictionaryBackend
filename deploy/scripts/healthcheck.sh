#!/bin/bash
# Healthcheck скрипт для автоматического перезапуска при сбоях

HEALTH_URL="http://localhost:5001/api/v1/sync/check"
MAX_FAILURES=3
FAILURE_COUNT=0
LOG_FILE="/var/log/app/healthcheck.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

while true; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        if [ $FAILURE_COUNT -gt 0 ]; then
            log_message "✅ Service recovered after $FAILURE_COUNT failures"
            FAILURE_COUNT=0
        fi
    else
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        log_message "⚠️ Health check failed ($FAILURE_COUNT/$MAX_FAILURES)"
        
        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            log_message "❌ Health check failed $MAX_FAILURES times. Restarting service..."
            sudo systemctl restart sign-language-backend
            sleep 10
            
            # Проверяем, что сервис запустился
            if sudo systemctl is-active --quiet sign-language-backend; then
                log_message "✅ Service restarted successfully"
            else
                log_message "❌ Failed to restart service"
            fi
            
            FAILURE_COUNT=0
        fi
    fi
    sleep 30
done
