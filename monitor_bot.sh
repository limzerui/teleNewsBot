#!/bin/bash
#
# Monitoring Script for Financial News Bot on RPi
#

PROJECT_DIR="/home/zrpi/Documents/teleNewsBot"
SERVICE_NAME="financial-news-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_status() {
    if [ "$2" == "OK" ]; then
        echo -e "${GREEN}✅ $1${NC}"
    elif [ "$2" == "WARNING" ]; then
        echo -e "${YELLOW}⚠️ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
    fi
}

print_header "Financial News Bot - System Status"

# Check service status
print_header "Service Status"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_status "Bot service is running" "OK"
    UPTIME=$(systemctl show "$SERVICE_NAME" --property=ActiveEnterTimestamp --value)
    echo "   Started: $UPTIME"
else
    print_status "Bot service is not running" "ERROR"
fi

# Check PostgreSQL
print_header "Database Status"
if systemctl is-active --quiet postgresql; then
    print_status "PostgreSQL is running" "OK"
    
    # Check database connection
    if PGPASSWORD="your_secure_password" psql -h localhost -U bot_user -d financial_bot -c "SELECT 1;" > /dev/null 2>&1; then
        print_status "Database connection successful" "OK"
        
        # Get subscriber count
        SUBSCRIBER_COUNT=$(PGPASSWORD="your_secure_password" psql -h localhost -U bot_user -d financial_bot -t -c "SELECT COUNT(*) FROM subscribers WHERE active=TRUE;" 2>/dev/null | xargs || echo "0")
        echo "   Active subscribers: $SUBSCRIBER_COUNT"
    else
        print_status "Database connection failed" "ERROR"
    fi
else
    print_status "PostgreSQL is not running" "ERROR"
fi

# Check disk space
print_header "System Resources"
DISK_USAGE=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 85 ]; then
    print_status "Disk usage: ${DISK_USAGE}%" "OK"
elif [ "$DISK_USAGE" -lt 95 ]; then
    print_status "Disk usage: ${DISK_USAGE}%" "WARNING"
else
    print_status "Disk usage: ${DISK_USAGE}%" "ERROR"
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
if (( $(echo "$MEMORY_USAGE < 80" | bc -l) )); then
    print_status "Memory usage: ${MEMORY_USAGE}%" "OK"
elif (( $(echo "$MEMORY_USAGE < 90" | bc -l) )); then
    print_status "Memory usage: ${MEMORY_USAGE}%" "WARNING"
else
    print_status "Memory usage: ${MEMORY_USAGE}%" "ERROR"
fi

# Check recent logs for errors
print_header "Recent Log Status"
ERROR_COUNT=$(sudo journalctl -u "$SERVICE_NAME" --since "1 hour ago" | grep -i error | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_status "No errors in last hour" "OK"
elif [ "$ERROR_COUNT" -lt 5 ]; then
    print_status "$ERROR_COUNT errors in last hour" "WARNING"
else
    print_status "$ERROR_COUNT errors in last hour" "ERROR"
fi

# Check log file size
print_header "Log File Status"
LOG_FILE="$PROJECT_DIR/logs/bot_$(date +%Y-%m-%d).log"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    print_status "Today's log file: $LOG_SIZE" "OK"
else
    print_status "No log file found for today" "WARNING"
fi

print_header "Quick Commands"
echo "• View live logs: sudo journalctl -u $SERVICE_NAME -f"
echo "• Restart service: sudo systemctl restart $SERVICE_NAME"
echo "• Check database: sudo -u postgres psql -d financial_bot"
echo "• Backup database: ./backup_database.sh"
