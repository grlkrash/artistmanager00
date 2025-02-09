# Deployment Guide

This guide explains how to deploy the Artist Manager Bot in a production environment.

## Prerequisites

- Linux server with systemd
- Python 3.9 or higher
- Root access
- Telegram Bot Token
- OpenAI API Key

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/artistmanager00.git
cd artistmanager00
```

2. Create and configure the environment file:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. Run the setup script:
```bash
sudo ./setup_production.sh
```

4. Start the service:
```bash
sudo systemctl start artist_manager
```

## Manual Setup

If you prefer to set up manually or the setup script doesn't work for your environment:

1. Create user and directories:
```bash
sudo groupadd -r artistmanager
sudo useradd -r -g artistmanager -d /opt/artistmanager -s /bin/bash artistmanager
sudo mkdir -p /opt/artistmanager
sudo mkdir -p /var/log/artistmanager
```

2. Copy files and set permissions:
```bash
sudo cp -r . /opt/artistmanager/
sudo chown -R artistmanager:artistmanager /opt/artistmanager
sudo chown -R artistmanager:artistmanager /var/log/artistmanager
```

3. Set up Python environment:
```bash
cd /opt/artistmanager
sudo -u artistmanager python3 -m venv .venv
sudo -u artistmanager .venv/bin/pip install -r requirements.txt
```

4. Install systemd service:
```bash
sudo cp artist_manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable artist_manager
```

## Configuration

Edit `/opt/artistmanager/.env`:

```ini
# Required API Keys
TELEGRAM_BOT_TOKEN=your_telegram_token_here
OPENAI_API_KEY=your_openai_key_here

# Optional Configuration
OPENAI_MODEL=gpt-3.5-turbo
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///artist_manager.db
METRICS_PORT=9090

# Optional External Services
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
AI_MASTERING_KEY=your_ai_mastering_key
```

## Monitoring

1. View logs:
```bash
# Service logs
journalctl -u artist_manager -f

# Application logs
tail -f /var/log/artistmanager/output.log
tail -f /var/log/artistmanager/error.log
```

2. Check metrics:
- Prometheus metrics are available at `http://your-server:9090/metrics`
- Monitor CPU, memory, request counts, and error rates

3. Check service status:
```bash
systemctl status artist_manager
```

## Troubleshooting

1. If the service fails to start:
```bash
journalctl -u artist_manager -n 50
```

2. Check permissions:
```bash
ls -la /opt/artistmanager
ls -la /var/log/artistmanager
```

3. Verify environment:
```bash
sudo -u artistmanager /opt/artistmanager/.venv/bin/python -c "import sys; print(sys.path)"
```

4. Test configuration:
```bash
sudo -u artistmanager /opt/artistmanager/.venv/bin/python /opt/artistmanager/deploy_prod.py --test
```

## Security Notes

1. The service runs with limited privileges
2. File permissions are restricted
3. The service cannot access user home directories
4. System protection is enabled through systemd

## Backup

1. Database:
```bash
cp /opt/artistmanager/artist_manager.db /backup/artist_manager_$(date +%Y%m%d).db
```

2. Configuration:
```bash
cp /opt/artistmanager/.env /backup/env_$(date +%Y%m%d)
```

## Updates

1. Stop the service:
```bash
sudo systemctl stop artist_manager
```

2. Backup current version:
```bash
sudo cp -r /opt/artistmanager /opt/artistmanager_backup_$(date +%Y%m%d)
```

3. Update files:
```bash
sudo cp -r /path/to/new/version/* /opt/artistmanager/
sudo chown -R artistmanager:artistmanager /opt/artistmanager
```

4. Update dependencies:
```bash
sudo -u artistmanager /opt/artistmanager/.venv/bin/pip install -r /opt/artistmanager/requirements.txt
```

5. Restart service:
```bash
sudo systemctl restart artist_manager
``` 