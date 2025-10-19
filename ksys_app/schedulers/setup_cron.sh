#!/bin/bash
# Setup cron job for daily model training

# This script sets up a cron job to run daily training at 2 AM
# Usage: bash setup_cron.sh

# Create cron job entry
CRON_SCHEDULE="0 2 * * *"  # Every day at 2 AM
PYTHON_PATH="/usr/local/bin/python"
SCRIPT_PATH="/app/ksys_app/schedulers/daily_training.py"
LOG_PATH="/app/logs/daily_training.log"

# Cron job command
CRON_JOB="$CRON_SCHEDULE cd /app && $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job installed:"
echo "$CRON_JOB"
echo ""
echo "To verify:"
echo "  crontab -l"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_PATH"
