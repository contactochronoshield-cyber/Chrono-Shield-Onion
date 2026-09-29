import os
import logging
import requests

logger = logging.getLogger("ChronoAlerts")

TELEGRAM_BOT_TOKEN = os.environ.get("CHRONO_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("CHRONO_TELEGRAM_CHAT_ID")

def send_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info(f"[ALERT-LOCAL] {message}")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🛡️ CHRONO SHIELD ALERT\n{message}"}, timeout=5)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Fallo enviando alerta: {e}")
        return False
