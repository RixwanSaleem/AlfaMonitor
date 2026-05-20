import logging
import os
import requests

from backend.database import SessionLocal
from backend.models import NotificationSetting

logger = logging.getLogger(__name__)

def get_setting(key: str):
    # prefer env, otherwise read from DB
    env = os.environ.get(key.upper())
    if env:
        return env
    db = SessionLocal()
    setting = db.query(NotificationSetting).filter(NotificationSetting.key == key).first()
    val = setting.value if setting else None
    db.close()
    return val or ""

TELEGRAM_TOKEN = get_setting("telegram_token")
TELEGRAM_CHAT_ID = get_setting("telegram_chat_id")
DISCORD_WEBHOOK_URL = get_setting("discord_webhook_url")


def send_telegram(message: str):
    token = get_setting("telegram_token")
    chat_id = get_setting("telegram_chat_id")
    if not token or not chat_id:
        logger.warning("Telegram alert not sent because telegram_token or telegram_chat_id is missing")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload, timeout=10)
    if not response.ok:
        logger.warning("Telegram alert failed", extra={"status_code": response.status_code, "text": response.text})
    return response.ok


def send_discord(message: str):
    url = get_setting("discord_webhook_url")
    if not url:
        return False
    payload = {"content": message}
    response = requests.post(url, json=payload, timeout=10)
    return response.ok


def send_alert(message: str):
    sent = False
    if send_telegram(message):
        sent = True
    if send_discord(message):
        sent = True
    return sent
