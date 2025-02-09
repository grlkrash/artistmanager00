#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

# Create artistmanager user and group
echo "Creating artistmanager user and group..."
groupadd -r artistmanager 2>/dev/null || true
useradd -r -g artistmanager -d /opt/artistmanager -s /bin/bash -c "Artist Manager Bot" artistmanager 2>/dev/null || true

# Create necessary directories
echo "Creating directories..."
mkdir -p /opt/artistmanager
mkdir -p /var/log/artistmanager
chown -R artistmanager:artistmanager /opt/artistmanager
chown -R artistmanager:artistmanager /var/log/artistmanager

# Copy files to production directory
echo "Copying files..."
cp -r . /opt/artistmanager/
chown -R artistmanager:artistmanager /opt/artistmanager

# Set up Python virtual environment
echo "Setting up virtual environment..."
cd /opt/artistmanager
python3 -m venv .venv
chown -R artistmanager:artistmanager .venv
sudo -u artistmanager .venv/bin/pip install -r requirements.txt

# Install systemd service
echo "Installing systemd service..."
cp artist_manager.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable artist_manager.service

echo "Setup complete! Please:"
echo "1. Configure your .env file in /opt/artistmanager/.env"
echo "2. Start the service with: systemctl start artist_manager"
echo "3. Check status with: systemctl status artist_manager"
echo "4. View logs with: journalctl -u artist_manager -f" 