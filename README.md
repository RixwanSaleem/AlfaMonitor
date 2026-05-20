# Lightweight Linux Monitoring Dashboard

A Python-based real-time monitoring dashboard for multiple Linux servers with alerting via Telegram/Discord and Ansible integration.

## Features

- Central dashboard for CPU, RAM, disk, temperature, and service status
- Real-time updates via WebSocket
- Admin login page
- Add servers with IP, username, and password
- Alerts sent to Telegram and Discord
- Ansible playbook runner for managed servers
- Agent script for Linux hosts

## Supported platforms

- Backend: Rocky Linux, Fedora, CentOS, and other Linux distributions with Python 3 support
- Agent: Linux hosts and Windows hosts via Python

## Automatic Telegram notifications

The app can send a system status update to Telegram every 5 minutes using `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`. There is also a dashboard notification settings panel where you can enable/disable Telegram alerts and set the interval. Adjust the interval with `TELEGRAM_NOTIFY_INTERVAL` in seconds if needed.

## Install

1. Create and activate a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Export configuration values

```bash
export SECRET_KEY="replace-with-secret"
export ADMIN_USER="admin"
export ADMIN_PASSWORD="password"
export TELEGRAM_TOKEN="your-telegram-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/…"
```

3. Run the dashboard

```bash
python backend/main.py
```

For Rocky Linux / Fedora / CentOS install steps, see `instructions.txt` in the project root.

## Agent installation

Copy `agents/agent.py`, `agents/system_info.py`, and `agents/config.py` to the target Linux server and run:

```bash
python agent.py --host YOUR_SERVER_IP
```

## Notes

- For production, configure HTTPS and secure credential storage.
- Replace the example background and static assets with your own branding.
