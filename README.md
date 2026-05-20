# AlfaMonitor

## Example Pictures
<p>
<img src="assets/Dashboard.png" width="40%"/>
<img src="assets/Alfa-Dashboard.png" width="40%"/>

AlfaMonitor is a Python-based monitoring dashboard for Linux and Windows servers. It provides live metrics, alerting, and Ansible integration through a Flask backend and lightweight agent.

## Project Overview

AlfaMonitor includes a centralized dashboard to monitor server CPU, RAM, disk, temperature, and service status. Alerts can be delivered via Telegram and Discord, and managed servers can run Ansible playbooks from the dashboard.

## Key Features

- Live dashboard with WebSocket updates
- Server health metrics: CPU, RAM, disk, temperature, network, and services
- Telegram and Discord alerting
- Cross-platform agent support for Linux and Windows
- Windows agent packaging support for one-file executable builds
- Ansible playbook execution from the UI
- Admin login and user management
- Configurable periodic Telegram status notifications

## Core Services

- `backend/main.py` — Flask app, APIs, socket events, and periodic workers
- `backend/alerting.py` — notification delivery via Telegram and Discord
- `backend/ansible_manager.py` — Ansible orchestration and commands
- `backend/database.py` — SQLAlchemy engine and sessions
- `backend/models.py` — database schema definitions
- `backend/websocket.py` — Socket.IO initialization and helpers
- `agents/agent.py` — cross-platform monitoring agent
- `agents/system_info.py` — metrics collection for Linux and Windows
- `static/js/app.js` — frontend dashboard logic
- `templates/dashboard.html` — dashboard layout and controls

## Project Structure

```text
.
├── LICENSE
├── README.md
├── requirements.txt
├── .env.example
├── agents
│   ├── agent.py
│   ├── config.py
│   └── system_info.py
├── ansible
│   ├── inventory.ini
│   └── playbook.yml
├── backend
│   ├── __init__.py
│   ├── alerting.py
│   ├── ansible_manager.py
│   ├── auth.py
│   ├── crypto.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── websocket.py
├── static
│   ├── agent_install_instructions.txt
│   ├── agent_service.template
│   ├── css
│   │   └── style.css
│   └── js
│       └── app.js
└── templates
    ├── dashboard.html
    └── login.html
```

## Prerequisites

### Supported operating systems

- Rocky Linux
- Fedora
- CentOS
- Other Linux distributions with Python 3 support

### Required packages

On Rocky/Fedora:

```bash
sudo dnf install -y epel-release
sudo dnf install -y python3 python3-devel python3-virtualenv python3-pip gcc openssl-devel libffi-devel make git dnf install python3 python3-pip python3-devel gcc nginx augeas-libs -y
```

On CentOS 8:

```bash
sudo yum install -y epel-release firewalld
sudo yum install -y python3 python3-devel python3-virtualenv python3-pip gcc openssl-devel libffi-devel make git
```
## Firewall 

sudo systemctl enable firewalld --now
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload


### Python requirements

- Python 3.8+
- Flask
- Flask-SocketIO
- SQLAlchemy
- passlib[bcrypt]
- requests
- psutil
- ansible-core
- python-dotenv
- cryptography

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Rixwansaleem/AlfaMonitor.git
cd AlfaMonitor
```

2. Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Configure environment variables:

nano /opt/panel/monitoring-dashboard/.env
```bash
SECRET_KEY="replace-with-secret"
ADMIN_USER="admin"
ADMIN_PASSWORD="password"
TELEGRAM_TOKEN="your-telegram-token"
TELEGRAM_CHAT_ID="your-chat-id"
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
TELEGRAM_NOTIFY_INTERVAL="300"
```

5. (Optional) copy example environment file:

```bash
cp .env.example .env
```

## Configuration

### Environment variables

- `SECRET_KEY` — Flask session secret
- `ADMIN_USER` — default admin username
- `ADMIN_PASSWORD` — default admin password
- `TELEGRAM_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Telegram chat or group ID
- `DISCORD_WEBHOOK_URL` — Discord webhook URL for alerts
- `TELEGRAM_NOTIFY_INTERVAL` — periodic Telegram status update interval in seconds

> Tip: For production, keep secrets in a secure environment and do not commit them to source control.

## Running the App

Activate the virtual environment and start the dashboard:

```bash
source venv/bin/activate
python backend/main.py
```

Open the app at:

```bash
http://0.0.0.0:5000
```

## Create a systemd Service

Create `/etc/systemd/system/monitoring-dashboard.service` with the following content:

```ini
[Unit]
Description=Monitoring Dashboard
After=network.target

[Service]
Environment=ADMIN_USER=admin
Environment=ADMIN_PASSWORD=Password
Type=simple
User=root
WorkingDirectory=/opt/panel/monitoring-dashboard
Environment="PATH=/opt/panel/monitoring-dashboard/venv/bin"
EnvironmentFile=/opt/panel/monitoring-dashboard/.env
ExecStart=/opt/panel/monitoring-dashboard/venv/bin/gunicorn \
    --workers 4 \
    --worker-class gthread --threads 4 \
    --bind 127.0.0.1:5000 \
    --access-logfile /var/log/monitoring-dashboard/access.log \
    --error-logfile /var/log/monitoring-dashboard/error.log \
    backend.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
## Nginx

nano /etc/nginx/conf.d/monitoring-dashboard.conf
server {
    listen 80;
    server_name alfasolution.org; # Replace with your domain or server IP

    # Handle static assets directly via Nginx for speed
    location /static/ {
        alias /opt/panel/monitoring-dashboard/static/;
    }

    # Pass all other traffic to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}



Then enable and start it:

```bash
sudo systemctl enable nginx --now
sudo systemctl restart nginx
sudo systemctl restart monitoring-dashboard
```

## Important

- If Password incorrect 
cd /opt/panel/monitoring-dashboard
source venv/bin/activate
python3

import sqlite3
from backend.auth import create_admin_user

conn = sqlite3.connect('monitoring.db')
cursor = conn.cursor()
cursor.execute("DELETE FROM users WHERE username='admin';")
conn.commit()
conn.close()

create_admin_user('admin', 'New_Password')
print("Successfully generated and hashed admin user profile via native auth!")
exit()

## Agent Installation

### Linux agent

Copy `agents/agent.py`, `agents/system_info.py`, and `agents/config.py` to the target host and run:

```bash
python3 agent.py --host YOUR_DASHBOARD_HOST --username agent --port 22
```

### Windows agent

Install Python 3 on Windows, copy the agent files, install dependencies, and run:

```powershell
pip install psutil requests
python agent.py --host YOUR_DASHBOARD_HOST --username agent --port 3389
```

### Build a Windows executable package

If you want a simple double-click deployment package, use the included Windows packaging helper.

1. Open PowerShell as Administrator in the repository root.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\static\windows_agent_build.ps1
```

3. The build creates `dist\AlfaMonitorAgent.exe`.
4. Copy `dist\AlfaMonitorAgent.exe` to the Windows target machine.
5. Run the executable as Administrator, or install it as a Windows service / scheduled task with "Run with highest privileges" for unattended operation.

> Note: The built executable is the easiest way to run the Windows agent with admin privileges for dashboard-driven installer jobs.

### Scheduling agent execution

#### Linux cron example

```cron
*/2 * * * * cd /opt/monitoring-agent && /usr/bin/python3 agent.py --host YOUR_DASHBOARD_HOST --username agent --port 22 >> /var/log/monitoring-agent.log 2>&1
```

#### Windows Task Scheduler

Use Task Scheduler to run the agent every 2 minutes with the Python executable.

## Notification Settings

The dashboard Notifications tab supports:

- enabling/disabling Telegram alerts
- storing Telegram bot token and chat ID
- setting the notification interval
- saving settings to the database
- sending a test notification

## Dependencies

Dependencies are managed in `requirements.txt` and installed with:

```bash
pip install -r requirements.txt
```

## Support & Contribution

To contribute: Rizwan Saleem

1. Fork the repository
2. Create a feature branch
3. Commit changes with clear messages
4. Open a pull request

For support, open an issue with: malik.chand@hotmail.com

- your OS and Python version
- what you tried
- any error logs

## Notes

- Use HTTPS or a reverse proxy for production deployments.
- Secure credentials and secret keys carefully.
- Configure firewalls and network access for the dashboard and remote agents.
