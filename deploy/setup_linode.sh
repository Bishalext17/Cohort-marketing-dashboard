#!/bin/bash
# ==============================================================================
# Linode (Akamai Cloud) Automated Server Provisioning & Deployment Script
# Cohort Marketing Performance Dashboard
# OS: Ubuntu 22.04 / 24.04 LTS
# ==============================================================================

set -e

echo "=== 1. Updating System Packages ==="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git ufw fail2ban nginx \
    python3-pip python3-venv python3-dev build-essential \
    libmysqlclient-dev pkg-config

echo "=== 2. Configuring Firewall (UFW) ==="
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "=== 3. Setting Up Application Directory ==="
APP_DIR="/opt/cohort-marketing-dashboard"
if [ ! -d "$APP_DIR" ]; then
    echo "Creating directory: $APP_DIR"
    sudo mkdir -p $APP_DIR
    sudo chown -R $USER:$USER $APP_DIR
fi

echo "=== 4. Setting up Python Virtual Environment ==="
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "=== 5. Setting up Systemd Service ==="
sudo tee /etc/systemd/system/cohort-dashboard.service > /dev/null <<EOF
[Unit]
Description=Cohort Marketing Performance Dashboard
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cohort-dashboard
sudo systemctl restart cohort-dashboard

echo "=== 6. Configuring Nginx Reverse Proxy ==="
sudo cp deploy/nginx.conf /etc/nginx/sites-available/cohort-dashboard
sudo ln -sf /etc/nginx/sites-available/cohort-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=============================================================================="
echo " Deployment Complete!"
echo " Server is live on: http://$(curl -s ifconfig.me)"
echo " Check service status with: sudo systemctl status cohort-dashboard"
echo " View live logs with: sudo journalctl -u cohort-dashboard -f"
echo "=============================================================================="
