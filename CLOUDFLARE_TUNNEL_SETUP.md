# Cloudflare Tunnel Setup Guide

## Overview
Cloudflare Tunnel provides secure external access to your application without opening firewall ports or exposing your server's IP address. This guide explains how to set up and manage the Cloudflare Tunnel for the Reflex-KSYS production deployment.

## What is Cloudflare Tunnel?

Cloudflare Tunnel creates an encrypted connection between your server and Cloudflare's edge network. Benefits include:
- ✅ **No port forwarding required** - No need to open ports 14000/14001
- ✅ **HTTPS by default** - Automatic SSL/TLS encryption
- ✅ **DDoS protection** - Built-in protection from Cloudflare
- ✅ **Hide origin IP** - Your server IP remains hidden
- ✅ **Access control** - Optional authentication and authorization
- ✅ **Free tier available** - No cost for basic usage

## Architecture

```
User Browser
    ↓ (HTTPS)
Cloudflare Edge Network
    ↓ (Encrypted Tunnel)
cloudflared container
    ↓ (Local network)
reflex-app-prod container (port 14000)
```

## Quick Start

### Current Configuration
The tunnel is already configured in [docker-compose.prod.yml](docker-compose.prod.yml) with your tunnel token.

### Start with Cloudflare Tunnel
```bash
# Start all services including Cloudflare Tunnel
./manage.sh start

# Or using Docker Compose directly
docker compose -f docker-compose.prod.yml up -d
```

### Check Tunnel Status
```bash
# Check if tunnel is running
docker ps | grep cloudflared

# View tunnel logs
docker logs cloudflared-tunnel-prod

# Check tunnel health
docker inspect cloudflared-tunnel-prod --format='{{.State.Health.Status}}'
```

### Access Your Application
Your application is now accessible via the Cloudflare Tunnel URL configured in your Cloudflare dashboard.

Typical format: `https://your-tunnel-name.your-domain.com`

## Detailed Setup (For New Tunnel)

If you need to create a new tunnel or modify the existing one:

### 1. Create Cloudflare Account
1. Go to https://dash.cloudflare.com
2. Sign up or log in
3. Navigate to "Zero Trust" → "Networks" → "Tunnels"

### 2. Create a New Tunnel
```bash
# Using cloudflared CLI (optional, can use dashboard)
docker run -it cloudflare/cloudflared:latest tunnel login
docker run -it cloudflare/cloudflared:latest tunnel create ksys-reflex-prod
```

Or use the Cloudflare dashboard:
1. Click "Create a tunnel"
2. Choose "Cloudflared" connector
3. Name your tunnel (e.g., "ksys-reflex-prod")
4. Copy the tunnel token

### 3. Configure Public Hostname
In Cloudflare dashboard:
1. Select your tunnel
2. Go to "Public Hostname" tab
3. Add hostname:
   - **Subdomain**: `ksys` (or your choice)
   - **Domain**: Select your domain
   - **Service**: `http://reflex-app-prod:13000`
   - **Path**: `/` (optional)

Example configuration:
- Public hostname: `ksys.yourdomain.com`
- Service URL: `http://reflex-app-prod:13000`

### 4. Update docker-compose.prod.yml
Replace the token in [docker-compose.prod.yml](docker-compose.prod.yml):

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: cloudflared-tunnel-prod
  command: tunnel --no-autoupdate run --token YOUR_NEW_TOKEN_HERE
  networks:
    - reflex-network-prod
  restart: unless-stopped
```

### 5. Restart Services
```bash
./manage.sh restart
```

## Configuration Options

### Environment Variables
You can also use environment variables for the token:

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: cloudflared-tunnel-prod
  command: tunnel --no-autoupdate run
  environment:
    - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
  networks:
    - reflex-network-prod
```

Then create a `.env` file:
```bash
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiMDQwMzY4ZDNlZj...
```

### Multiple Routes
You can route different paths to different services:

In Cloudflare dashboard, add multiple public hostnames:
1. `ksys.yourdomain.com/` → `http://reflex-app-prod:13000`
2. `ksys.yourdomain.com/api` → `http://reflex-app-prod:13001`

### Access Policies
Add authentication and authorization:

1. In Cloudflare dashboard, go to "Access" → "Applications"
2. Add new application
3. Configure authentication (Google, GitHub, email, etc.)
4. Apply to your tunnel hostname

## Monitoring and Management

### View Real-time Logs
```bash
# Follow tunnel logs
docker logs -f cloudflared-tunnel-prod

# Check for connection status
docker logs cloudflared-tunnel-prod | grep "Connection"
```

### Check Tunnel Metrics
In Cloudflare dashboard:
1. Go to your tunnel
2. View "Metrics" tab for:
   - Request rate
   - Response status codes
   - Bandwidth usage

### Restart Tunnel Only
```bash
# Restart only cloudflared container
docker restart cloudflared-tunnel-prod

# Or using Docker Compose
docker compose -f docker-compose.prod.yml restart cloudflared
```

## Troubleshooting

### Tunnel Not Connecting
```bash
# Check logs for errors
docker logs cloudflared-tunnel-prod

# Common issues:
# 1. Invalid token - verify token in docker-compose.prod.yml
# 2. Network connectivity - check internet connection
# 3. Container networking - ensure reflex-network-prod exists
```

### 502 Bad Gateway
This usually means the tunnel is connected but can't reach the application:

```bash
# Check if reflex-app-prod is running
docker ps | grep reflex-app-prod

# Verify network connectivity
docker exec cloudflared-tunnel-prod ping reflex-app-prod

# Check application logs
docker logs reflex-ksys-app-prod
```

### Connection Timeout
```bash
# Increase timeout in Cloudflare dashboard:
# Zero Trust → Networks → Tunnels → Select tunnel → Configure
# Set "Connection timeout" to 300s

# Or restart the tunnel
docker restart cloudflared-tunnel-prod
```

### Token Expired or Invalid
```bash
# Get new token from Cloudflare dashboard
# Update docker-compose.prod.yml
# Restart services
./manage.sh restart
```

## Security Best Practices

### 1. Token Management
- Store token securely (use environment variables or Docker secrets)
- Don't commit token to public repositories
- Rotate tokens periodically

### 2. Access Control
- Enable Cloudflare Access for authentication
- Use IP restrictions if needed
- Enable audit logs

### 3. Rate Limiting
Configure in Cloudflare dashboard:
- Zero Trust → Networks → Tunnels → Your tunnel
- Add rate limiting rules

### 4. SSL/TLS Settings
In Cloudflare dashboard:
- SSL/TLS → Overview → Set to "Full" or "Full (strict)"
- Enable "Always Use HTTPS"
- Enable "Automatic HTTPS Rewrites"

## Advanced Configuration

### Custom Configuration File
Instead of using command-line token, use config file:

Create `cloudflared-config.yml`:
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /etc/cloudflared/credentials.json

ingress:
  - hostname: ksys.yourdomain.com
    service: http://reflex-app-prod:13000
  - hostname: api.yourdomain.com
    service: http://reflex-app-prod:13001
  - service: http_status:404
```

Update docker-compose.prod.yml:
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: cloudflared-tunnel-prod
  command: tunnel --config /etc/cloudflared/config.yml run
  volumes:
    - ./cloudflared-config.yml:/etc/cloudflared/config.yml:ro
    - ./cloudflared-credentials.json:/etc/cloudflared/credentials.json:ro
  networks:
    - reflex-network-prod
```

### Load Balancing
For high availability, run multiple tunnel instances:

```yaml
cloudflared-1:
  image: cloudflare/cloudflared:latest
  command: tunnel --no-autoupdate run --token YOUR_TOKEN
  networks:
    - reflex-network-prod

cloudflared-2:
  image: cloudflare/cloudflared:latest
  command: tunnel --no-autoupdate run --token YOUR_TOKEN
  networks:
    - reflex-network-prod
```

## Raspberry Pi Specific Notes

### Performance
- Cloudflare Tunnel adds minimal CPU overhead (~1-2%)
- Memory usage: ~50-100MB
- No impact on local network performance

### Auto-restart
The tunnel is configured with `restart: unless-stopped` to automatically restart on:
- Container crashes
- System reboots (when Docker is set to start on boot)

### Monitoring on RPI
```bash
# Check resource usage
docker stats cloudflared-tunnel-prod

# Monitor continuously
watch -n 5 'docker stats --no-stream cloudflared-tunnel-prod'
```

## Comparison: Local Ports vs Cloudflare Tunnel

| Feature | Local Ports (14000/14001) | Cloudflare Tunnel |
|---------|---------------------------|-------------------|
| **Access** | Local network only | Internet accessible |
| **Security** | Firewall required | Built-in protection |
| **HTTPS** | Manual SSL setup | Automatic |
| **IP Exposure** | Server IP visible | IP hidden |
| **Setup** | Port forwarding needed | No port forwarding |
| **Cost** | Free | Free (basic tier) |

## Migration Guide

### From Local Ports to Tunnel
1. Current state: Application on ports 14000/14001
2. Add Cloudflare Tunnel: `./manage.sh restart`
3. Test tunnel access: Visit your Cloudflare URL
4. Optional: Close ports 14000/14001 in firewall

### From Tunnel to Local Ports
1. Stop tunnel: `docker stop cloudflared-tunnel-prod`
2. Access via: `http://localhost:14000`

### Run Both Simultaneously
The current configuration supports both:
- Local access: `http://localhost:14000`
- Remote access: `https://your-tunnel.yourdomain.com`

## Cost and Limits

### Free Tier Includes:
- Unlimited bandwidth
- Unlimited connections
- DDoS protection
- Basic access controls
- 50 active users for Access

### Paid Tier Adds:
- Advanced access policies
- More user seats
- Enhanced security features
- Priority support

## Support and Resources

### Documentation
- Cloudflare Tunnel Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Zero Trust Dashboard: https://dash.cloudflare.com

### Troubleshooting
1. Check tunnel status in Cloudflare dashboard
2. Review container logs: `docker logs cloudflared-tunnel-prod`
3. Test local connectivity: `curl http://reflex-app-prod:13000`
4. Check Cloudflare status: https://www.cloudflarestatus.com

## Summary

✅ Cloudflare Tunnel configured in docker-compose.prod.yml
✅ Automatic HTTPS and DDoS protection
✅ No port forwarding required
✅ Health checks enabled
✅ Auto-restart on failure
✅ Works alongside local port access

Your application is now securely accessible from anywhere! 🌐🔒
