import requests
from .settings import logpath
from loguru import logger as log
from .settings import NOTIFICATION_API_KEY, NOTIFICATION_API_URL


log.add(
    logpath,
    enqueue=True,
    level="INFO",
    rotation="100 MB",
    retention="10 days",
    compression="zip",
)


def send_notification(email: str, message: str):
    if not NOTIFICATION_API_KEY:
        return
    try:
        response = requests.post(
            NOTIFICATION_API_URL,
            headers={"Accept": "*/*", "Content-Type": "application/json"},
            json={
                "messageType": "general",
                "email": str(email),
                "message": message,
                "apikey": NOTIFICATION_API_KEY,
            },
        )
        response.raise_for_status()
    except Exception as err:
        log.exception(err)
