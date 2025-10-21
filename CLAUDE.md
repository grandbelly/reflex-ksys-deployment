# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Reflex-KSys Deployment** is a production-ready SCADA system with AI forecasting capabilities built on:
- **Frontend/Backend**: Reflex (Python web framework with Chakra UI)
- **Database**: TimescaleDB (time-series PostgreSQL)
- **ML Pipeline**: Multiple forecasting models (AutoARIMA, ETS, XGBoost, Prophet)
- **Architecture**: Microservices (Reflex app + separate scheduler service)

## Architecture

### Core Components

1. **`ksys_app/`** - Main application package
   - **`states/`** - Reflex state management (client-server reactive state)
     - `base_state.py`: Base class with common patterns (polling, sidebar, theme)
     - One state class per feature (dashboard, alarms, training, etc.)
   - **`pages/`** - Route handlers and page definitions
   - **`services/`** - Business logic layer with database queries
     - Inherit from `BaseService` which provides async session management
     - Handle all DB operations via `execute_query()` method
   - **`components/`** - Reusable UI components (charts, cards, tables)
   - **`queries/`** - Raw SQL queries and helper functions for specific domains
   - **`models/`** - SQLAlchemy ORM definitions and Pydantic schemas
   - **`ml/`** - Machine learning pipeline (training, forecasting, ensemble)
   - **`ai_engine/`** - RAG and AI chat features
   - **`schedulers/`** - Background job coordination (runs in separate container)
   - **`db.py`** - Database connection pool (asyncpg)

2. **`schedulers/`** - Separate microservice for background jobs
   - Built from `schedulers/Dockerfile`
   - Runs `run_schedulers.py` which manages three scheduler types:
     - **ForecastScheduler**: Generates predictions every 5 minutes
     - **ActualValueUpdater**: Backfills actual sensor values every 10 minutes
     - **PerformanceAggregator**: Calculates metrics every 1 hour

3. **Containers** (via docker-compose.yml):
   - `reflex-app`: Main application (ports 13000/13001)
   - `forecast-scheduler`: Background schedulers
   - `data-injector`: Test data generator (development only)

### Key Patterns

**State Management**:
- All states extend `rx.State` or `BaseState`
- States automatically sync between client/server
- Use `@rx.event` decorator for event handlers
- Events can run in background with `background=True`
- Polling implemented via `start_polling()` from BaseState

**Service Layer**:
- All services accept `AsyncSession` in `__init__`
- Use `execute_query(text_query, params, timeout)` for database access
- Return `List[Dict]` from queries
- All operations are async

**Database Access**:
- Using SQLAlchemy 2.0 async (not sync)
- Connection pool managed by `db.py` (min=5, max=20)
- Each request gets a session via Reflex's dependency injection

**ML Pipeline**:
- `training_pipeline.py`: Handles model training workflow
- `forecast_pipeline.py`: Generates real-time predictions
- Models stored in `saved_models/` volume
- Supports multiple model types via model registry

## Common Development Tasks

### Running the Application

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f reflex-app       # Main app
docker-compose logs -f forecast-scheduler # Schedulers

# Restart specific service
docker-compose restart reflex-app
```

### Development Workflow

```bash
# Changes to ksys_app/ auto-reload (mounted as volume)
# Edit files and refresh browser to see changes

# For scheduler changes, rebuild and restart
docker-compose restart forecast-scheduler

# Access container for debugging
docker exec -it reflex-ksys-app /bin/bash
docker exec -it forecast-scheduler /bin/bash
```

### Testing Database Connection

```bash
# From inside container
docker exec reflex-ksys-app python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    pool = await get_pool()
    print('Connection successful!')
asyncio.run(test())
"
```

### Checking Active Models

```bash
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

### Viewing Scheduler Details

```bash
# Check scheduler status in database
docker exec reflex-ksys-app python -c "
import asyncio
from ksys_app.db_orm import get_async_session
from sqlalchemy import text
async def check():
    async with get_async_session() as session:
        result = await session.execute(text('SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5'))
        for row in result:
            print(row)
asyncio.run(check())
"
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `TS_DSN` | TimescaleDB connection string | Required |
| `POSTGRES_CONNECTION_STRING` | Same as TS_DSN | Required |
| `APP_ENV` | Environment mode | development |
| `TZ` | Timezone | Asia/Seoul |
| `ENABLE_AI_FEATURES` | Enable AI chat/insights | true |
| `VERSION_TYPE` | Feature set (FULL/LITE) | FULL |

Set in `docker-compose.yml` environment sections or `.env` file.

## File Organization Tips

- **New feature pages**: Create in `ksys_app/pages/`
- **Feature-specific state**: Create in `ksys_app/states/` (extend BaseState)
- **Database queries**: Create service in `ksys_app/services/` (extend BaseService)
- **Reusable UI**: Create component in `ksys_app/components/`
- **Domain-specific queries**: Add to appropriate file in `ksys_app/queries/`
- **ML model changes**: Update `ksys_app/ml/` files and rebuild containers
- **Scheduler changes**: Rebuild `forecast-scheduler` container after changes

## Important Configuration Files

- `rxconfig.py`: Reflex framework configuration (ports, plugins, CORS)
- `requirements.txt`: Python dependencies (main app)
- `schedulers/requirements.txt`: Scheduler dependencies
- `docker-compose.yml`: Service orchestration and environment setup
- `Dockerfile`: Main application image
- `schedulers/Dockerfile`: Scheduler service image

## Troubleshooting

**App won't start**: Check database connection in logs with `docker logs reflex-ksys-app`

**Port conflicts**: Ensure ports 13000/13001 are available; adjust in `rxconfig.py` and `docker-compose.yml`

**Scheduler not running**: Check logs via `docker logs forecast-scheduler -f` and verify deployed models exist

**Database connection errors**: Verify `TS_DSN` environment variable is set correctly and database is accessible

**ML model not predicting**: Ensure model is deployed and active in database via model config UI

## Database Schema

Key tables (managed by migrations):
- `sensors`: Physical/virtual sensor definitions
- `sensor_readings`: Raw time-series data
- `deployed_models`: Active forecasting models
- `forecast_results`: Generated predictions
- `model_performance_metrics`: Accuracy metrics (MAPE, RMSE)
- `alarms`: Rule-based alerts and notifications
- `cron.job`: Scheduler job definitions
- `cron.job_run_details`: Scheduler execution history

## Performance Considerations

- **Database pool**: Default 20 connections (adjust in `ksys_app/db.py` if needed)
- **Reflex workers**: Currently 1 backend worker (increase in `rxconfig.py` for load)
- **Data refresh**: Dashboard updates every 2 seconds (configured in state)
- **ML predictions**: Generated every 5 minutes (ForecastScheduler)
- **Query timeouts**: Default 10 seconds per query (adjust in BaseService)

## Deployment Notes

For production deployment, refer to README.md Security Checklist:
- Change database credentials
- Enable SSL/TLS for database
- Set `APP_ENV=production`
- Disable data-injector service
- Configure HTTPS reverse proxy
- Set up monitoring for container health and API response times
