# Schedulers - Automated Training Workflows

This module provides scheduled tasks for automated model training and maintenance.

## Components

### `daily_training.py`
Main scheduler script that runs daily model retraining workflow.

**Features:**
- Trains ARIMA, Prophet, and XGBoost models for all active sensors
- Uses last 30 days of data for training
- Automatically deploys models that perform better than existing ones
- Runs drift detection to identify model degradation
- Logs comprehensive training reports

**Usage:**
```bash
# Run manually (for testing)
python ksys_app/schedulers/daily_training.py

# Run inside Docker container
docker exec reflex-ksys-app python ksys_app/schedulers/daily_training.py
```

### `setup_cron.sh`
Shell script to install cron job for daily execution.

**Setup:**
```bash
# Inside Docker container
bash ksys_app/schedulers/setup_cron.sh

# Verify installation
crontab -l

# View logs
tail -f logs/daily_training.log
```

## Docker Integration

### Method 1: Cron Job (Recommended for Production)

Add to `Dockerfile`:
```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron

# Copy cron setup script
COPY ksys_app/schedulers/setup_cron.sh /app/setup_cron.sh
RUN chmod +x /app/setup_cron.sh

# Create logs directory
RUN mkdir -p /app/logs

# Setup cron job
RUN /app/setup_cron.sh

# Start cron service
CMD service cron start && reflex run
```

### Method 2: Python Schedule Library (Alternative)

For environments where cron is not available:

```python
# ksys_app/schedulers/scheduler_runner.py
import schedule
import time
from daily_training import main

def job():
    asyncio.run(main())

# Run every day at 2 AM
schedule.every().day.at("02:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Add to `requirements.txt`:
```
schedule>=1.2.0
```

## Configuration

Environment variables for customization:

```bash
# Training configuration
TRAINING_DAYS=30                  # Days of data for training
MIN_DATA_POINTS=1000              # Minimum data points required
ENABLE_DRIFT_CHECK=true           # Enable drift detection

# Schedule configuration
TRAINING_SCHEDULE="0 2 * * *"     # Cron schedule (default: 2 AM daily)
```

## Monitoring

### Logs

All training runs are logged to:
- `logs/daily_training.log` - Cron job output
- Application logs (via Python logging)

Example log output:
```
================================================================================
STARTING DAILY MODEL TRAINING
Timestamp: 2025-10-08T02:00:00
================================================================================
Found 50 active sensors
Training models for D100_INLET_PRESSURE
✅ ARIMA model deployed for D100_INLET_PRESSURE (MAE: 0.1234)
✅ Prophet model deployed for D100_INLET_PRESSURE (MAE: 0.1156)
⏭️ XGBoost model not deployed for D100_INLET_PRESSURE (existing model is better)
...
================================================================================
DAILY TRAINING SUMMARY
Total sensors: 50
Successful: 48
Failed: 1
Skipped: 1
Duration: 1234.56s
================================================================================
```

### Database Monitoring

Check `model_registry` table for newly trained models:

```sql
SELECT
    tag_name,
    model_type,
    version,
    mae,
    created_at
FROM model_registry
WHERE created_at >= CURRENT_DATE
ORDER BY created_at DESC;
```

## Troubleshooting

### Cron job not running

```bash
# Check if cron is running
service cron status

# Check crontab
crontab -l

# Test script manually
python ksys_app/schedulers/daily_training.py

# Check cron logs
grep CRON /var/log/syslog
```

### Training failures

Common issues:
- **Insufficient data**: Increase `TRAINING_DAYS` or lower `MIN_DATA_POINTS`
- **Memory issues**: Reduce number of sensors or train in batches
- **Database connection**: Check `TS_DSN` environment variable

### Performance optimization

For large deployments:
```python
# Parallelize training across sensors
async def train_batch(sensors, batch_size=10):
    for i in range(0, len(sensors), batch_size):
        batch = sensors[i:i+batch_size]
        await asyncio.gather(*[
            train_sensor_models(session, sensor)
            for sensor in batch
        ])
```

## Testing

### Manual test run
```bash
# Run training for specific sensor
python -c "
from ksys_app.schedulers.daily_training import DailyTrainingScheduler
import asyncio

async def test():
    scheduler = DailyTrainingScheduler(training_days=7)
    await scheduler.run_daily_training()

asyncio.run(test())
"
```

### Dry run (no deployment)
Modify `_should_deploy_model()` to always return `False` for testing.

## Best Practices

1. **Monitor disk space**: Model files accumulate over time
2. **Archive old models**: Keep only last N versions per sensor
3. **Alert on failures**: Integrate with monitoring system
4. **Gradual rollout**: Test with subset of sensors first
5. **Backup before deployment**: Save model_registry before updates

## Integration with Other Systems

### Dagster (Future Enhancement)
```python
# dagster/jobs/daily_training_job.py
from dagster import job, op
from ksys_app.schedulers.daily_training import main

@op
def run_training():
    asyncio.run(main())

@job
def daily_training_job():
    run_training()
```

### Alerting
```python
# Add to daily_training.py
from ksys_app.utils.notifications import send_slack_message

if summary['failed'] > 0:
    send_slack_message(
        f"⚠️ {summary['failed']} sensors failed training"
    )
```
