# Raspberry Pi Production Deployment Guide

## Overview
This guide will help you deploy the Reflex-KSYS application on a Raspberry Pi using Docker.

## Prerequisites

### 1. Raspberry Pi Setup
- Raspberry Pi 4 or later (recommended: 4GB+ RAM)
- Raspberry Pi OS (64-bit recommended)
- Docker and Docker Compose installed
- Stable internet connection

### 2. Install Docker on RPI
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Logout and login again for group changes to take effect
```

## Deployment Steps

### Step 1: Clone Repository
```bash
# Clone from GitHub
git clone https://github.com/grandbelly/reflex-ksys-deployment.git
cd reflex-ksys-deployment

# Verify files
ls -la
```

### Step 2: Configure Environment
```bash
# Make scripts executable
chmod +x manage.sh start-prod.sh

# Review and update environment variables if needed
# Edit docker-compose.prod.yml to adjust database connection, ports, etc.
nano docker-compose.prod.yml
```

### Step 3: Set Database Connection
Update the `TS_DSN` environment variable in [docker-compose.prod.yml](docker-compose.prod.yml):

```yaml
environment:
  - TS_DSN=postgresql://username:password@your-db-host:5432/database?sslmode=disable
```

### Step 4: Build and Deploy

#### Option A: Using Management Script (Recommended)
```bash
# Build production images
./manage.sh build

# Start production services
./manage.sh start

# Check status
./manage.sh status

# View logs
./manage.sh logs
```

#### Option B: Using Docker Compose Directly
```bash
# Build images (this may take 15-30 minutes on RPI)
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Step 5: Verify Deployment
```bash
# Wait for containers to be healthy (30-60 seconds)
docker ps

# Check if services are running
curl http://localhost:14000

# Or access from browser on your network
# http://<rpi-ip-address>:14000
```

## Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 14000 | Web application UI |
| Backend | 14001 | API endpoints |
| Database | 6543 | PostgreSQL (if using included DB) |

## Management Commands

### Using manage.sh
```bash
# Build production images
./manage.sh build

# Start services
./manage.sh start

# Stop services
./manage.sh stop

# Restart services
./manage.sh restart

# View status
./manage.sh status

# View logs
./manage.sh logs

# Clean up (stops and removes containers)
./manage.sh clean
```

### Manual Docker Commands
```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Check logs for specific service
docker logs reflex-ksys-app-prod
docker logs forecast-scheduler-prod

# Enter container shell
docker exec -it reflex-ksys-app-prod /bin/bash

# Restart a service
docker restart reflex-ksys-app-prod

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes
docker compose -f docker-compose.prod.yml down -v
```

## Troubleshooting

### Build Takes Too Long
Building on RPI can take 20-30 minutes. This is normal.
```bash
# Monitor build progress
docker compose -f docker-compose.prod.yml build --progress=plain
```

### Out of Memory During Build
```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE to 2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Container Keeps Restarting
```bash
# Check logs
docker logs reflex-ksys-app-prod --tail 100

# Common issues:
# 1. Database connection - verify TS_DSN
# 2. Missing dependencies - rebuild image
# 3. Port conflicts - check if ports are already in use
```

### Port Already in Use
```bash
# Find process using port
sudo lsof -i :14000

# Kill process if needed
sudo kill -9 <PID>
```

### Database Connection Issues
```bash
# Verify database is accessible
docker exec reflex-ksys-app-prod ping pgai-db

# Check database logs
docker logs pgai-db

# Test connection
docker exec reflex-ksys-app-prod curl http://pgai-db:5432
```

## Performance Optimization for RPI

### 1. Reduce Build Layers
The production Dockerfile is already optimized with multi-stage builds.

### 2. Limit Container Resources
Add to docker-compose.prod.yml:
```yaml
services:
  reflex-app-prod:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
```

### 3. Use External Database
For better performance, use an external PostgreSQL database instead of running it on the RPI.

## Monitoring

### Health Checks
```bash
# Check container health
docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}'

# Should return: healthy
```

### Resource Usage
```bash
# Monitor resource usage
docker stats

# View specific container stats
docker stats reflex-ksys-app-prod
```

## Updating Deployment

### Pull Latest Changes
```bash
cd reflex-ksys-deployment

# Stop services
./manage.sh stop

# Pull latest code
git pull origin master

# Rebuild and start
./manage.sh build
./manage.sh start
```

### Rollback to Previous Version
```bash
# Stop current deployment
./manage.sh stop

# Checkout previous commit
git log --oneline -5
git checkout <previous-commit-hash>

# Rebuild and deploy
./manage.sh build
./manage.sh start
```

## Security Considerations

### 1. Firewall Configuration
```bash
# Install ufw if not present
sudo apt-get install ufw

# Allow SSH
sudo ufw allow ssh

# Allow application ports
sudo ufw allow 14000/tcp
sudo ufw allow 14001/tcp

# Enable firewall
sudo ufw enable
```

### 2. Change Default Passwords
- Update database passwords in docker-compose.prod.yml
- Use strong passwords
- Consider using Docker secrets for sensitive data

### 3. HTTPS/SSL
For production use, consider setting up reverse proxy with SSL:
```bash
# Install nginx
sudo apt-get install nginx

# Configure as reverse proxy with Let's Encrypt
# See: https://certbot.eff.org/
```

## Backup and Recovery

### Backup Application Data
```bash
# Backup volumes
docker run --rm \
  -v reflex-ksys-deployment_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore from Backup
```bash
# Stop services
./manage.sh stop

# Restore volume
docker run --rm \
  -v reflex-ksys-deployment_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup-YYYYMMDD.tar.gz -C /

# Start services
./manage.sh start
```

## Auto-start on Boot

### Enable Docker Services on Boot
```bash
# Create systemd service
sudo nano /etc/systemd/system/reflex-ksys-prod.service
```

Add the following content:
```ini
[Unit]
Description=Reflex KSYS Production
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/reflex-ksys-deployment
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable reflex-ksys-prod
sudo systemctl start reflex-ksys-prod

# Check status
sudo systemctl status reflex-ksys-prod
```

## Support

For issues or questions:
1. Check logs: `./manage.sh logs`
2. Review this guide
3. Check GitHub issues: https://github.com/grandbelly/reflex-ksys-deployment/issues

## Summary

✅ Production deployment ready for RPI
✅ Python 3.11 for RPI compatibility
✅ Multi-stage Docker build
✅ Health checks enabled
✅ Management scripts provided
✅ Tested and verified

Happy deploying! 🚀
