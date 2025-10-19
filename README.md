# Reflex-KSys Application Deployment

Production-ready deployment package for Reflex-KSys SCADA + AI Forecasting system.

## 📦 Contents

- **ksys_app/**: Main application code
  - states/: Reflex state management
  - pages/: UI pages
  - services/: Business logic layer
  - ml/: Machine learning pipeline
  - schedulers/: Background job schedulers
  - components/: Reusable UI components

- **Dockerfile**: Main application container
- **docker-compose.yml**: Multi-container orchestration
- **requirements.txt**: Python dependencies
- **rxconfig.py**: Reflex configuration

## 🚀 Quick Start

### Prerequisites

1. **TimescaleDB Instance** - See [reflex-ksys-db](https://github.com/grandbelly/reflex-ksys-db) for database deployment
2. **Docker & Docker Compose** installed
3. **Network access** to TimescaleDB database

### 1. Configure Database Connection

Edit `docker-compose.yml` and update database connection strings:

```yaml
environment:
  - TS_DSN=postgresql://user:password@your-db-host:5432/ecoanp?sslmode=disable
  - POSTGRES_CONNECTION_STRING=postgresql://user:password@your-db-host:5432/ecoanp?sslmode=disable
```

Or create `.env` file:

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 2. Build and Start Services

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access Application

- **Frontend**: http://localhost:13000
- **Backend API**: http://localhost:13001

## 🏗️ Architecture

### Services

**reflex-app** (Main Application)
- Reflex web framework (Python + Chakra UI)
- Real-time dashboard with 2-second refresh
- ML training wizard
- Alarm management
- Trend analysis
- Ports: 13000 (frontend), 13001 (backend)

**forecast-scheduler** (Background Schedulers)
- ForecastScheduler: Generates predictions every 5 minutes
- ActualValueUpdater: Backfills actual values every 10 minutes
- PerformanceAggregator: Calculates metrics every 1 hour

**data-injector** (Optional - Testing Only)
- Injects random sensor data every 5 minutes
- Comment out in production when using real hardware

### Network

All services connect via `reflex-network` bridge network.

## 📊 System Requirements

### Hardware

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB minimum for application + logs

### Software

- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **TimescaleDB**: 17+ (deployed separately)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TS_DSN` | TimescaleDB connection string | Required |
| `POSTGRES_CONNECTION_STRING` | Same as TS_DSN | Required |
| `APP_ENV` | Environment (development/production) | development |
| `TZ` | Timezone | Asia/Seoul |
| `ENABLE_AI_FEATURES` | Enable AI chat/insights | true |
| `VERSION_TYPE` | Version (FULL/LITE) | FULL |

### Ports

- **13000**: Frontend (React/Chakra UI)
- **13001**: Backend (Reflex WebSocket + HTTP)

### Volumes

- `./ksys_app`: Application code (hot-reload enabled)
- `./logs`: Application logs
- `./saved_models`: ML model artifacts
- `./rxconfig.py`: Reflex configuration

## 📝 Application Features

### 1. Real-time Dashboard
- Live sensor monitoring (2-second refresh)
- Mini sparkline charts
- QC rule-based status indicators
- Communication quality tracking

### 2. Alarm System
- Rule-based alarms (QC thresholds)
- ISA-18.2 compliant levels (1-5)
- Real-time and historical views

### 3. Trend Analysis
- Time-series visualization
- Multiple aggregation levels (1m, 10m, 1h, 1d)
- Technical indicators (SMA, Bollinger Bands)

### 4. ML Forecasting
- Wizard-based training interface
- Multiple model types (AutoARIMA, ETS, XGBoost, Prophet)
- Automated online predictions (5-min intervals)
- Performance monitoring (MAPE, RMSE, MAE)

### 5. AI Chat (Optional)
- RAG-based knowledge queries
- 5W1H analysis for alarms
- Toggle via `ENABLE_AI_FEATURES` env var

## 🛠️ Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs reflex-ksys-app -f
docker logs forecast-scheduler -f
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart reflex-app
docker-compose restart forecast-scheduler
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## 🐛 Troubleshooting

### Application Won't Start

```bash
# Check container status
docker ps -a

# View startup logs
docker logs reflex-ksys-app --tail 100

# Common issues:
# 1. Database connection failed - verify TS_DSN
# 2. Port conflict - check if 13000/13001 are in use
# 3. Missing dependencies - rebuild with --no-cache
```

### Database Connection Errors

```bash
# Test database connection
docker exec reflex-ksys-app python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    pool = await get_pool()
    print('Connection successful!')
asyncio.run(test())
"
```

### Scheduler Not Running

```bash
# Check scheduler logs
docker logs forecast-scheduler -f | grep "SCHEDULER"

# Verify deployed models
docker exec reflex-ksys-app python -c "
import asyncio
from ksys_app.db_orm import get_async_session
from sqlalchemy import text
async def check():
    async with get_async_session() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM deployed_models WHERE is_active = true'))
        print(f'Active models: {result.scalar()}')
asyncio.run(check())
"
```

### Performance Issues

```bash
# Check container resources
docker stats reflex-ksys-app

# Increase resource limits in docker-compose.yml
services:
  reflex-app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## 🔒 Production Deployment

### Security Checklist

- [ ] Change database passwords (don't use default `postgres:postgres`)
- [ ] Enable SSL/TLS for database connections
- [ ] Set `APP_ENV=production`
- [ ] Disable `data-injector` service
- [ ] Configure firewall rules (restrict ports 13000-13001)
- [ ] Set up HTTPS reverse proxy (nginx/traefik)
- [ ] Enable application logging to external service
- [ ] Set up monitoring and alerting

### Performance Tuning

1. **Database Connection Pool**
   - Increase `max_size` in `ksys_app/db.py` (default: 20)
   - Monitor with: `SELECT count(*) FROM pg_stat_activity WHERE datname = 'ecoanp'`

2. **Reflex Backend Workers**
   - Increase workers in `rxconfig.py`: `backend_port=13001, workers=4`

3. **TimescaleDB Tuning**
   - Enable compression on hypertables
   - Adjust retention policies
   - Optimize continuous aggregates

### Monitoring

Set up monitoring for:
- Container health (Docker healthchecks)
- Application errors (check logs/)
- Database connections
- Scheduler execution (cron.job_run_details)
- API response times
- ML prediction latency

## 📚 Documentation

- **Project Repository**: https://github.com/grandbelly/reflex-ksys-refactor
- **Database Deployment**: https://github.com/grandbelly/reflex-ksys-db
- **Reflex Framework**: https://reflex.dev/docs/
- **TimescaleDB**: https://docs.timescale.com/

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. View application logs: `docker logs reflex-ksys-app -f`
3. Check database logs: `docker logs pgai-db -f`
4. Review project documentation in main repository

## 📄 License

Part of Reflex-KSys SCADA system.
