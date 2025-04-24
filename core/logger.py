import requests
from loguru import logger as log
from functools import wraps
from .settings import logpath
from .settings import NOTIFICATION_API_KEY, NOTIFICATION_API_URL


log.add(
    logpath,
    enqueue=True,
    level="INFO",
    rotation="100 MB",
)


def sent_notification(email: str, message: str):
    try:
        response = requests.post(NOTIFICATION_API_URL, headers={
            "Accept": "*/*",
            "Content-Type": "application/json"
        }, json={
            "messageType": "general",
            "email": str(email),
            "message": message,
            "apikey": NOTIFICATION_API_KEY
        })
        response.raise_for_status()
    except Exception as err:
        log.exception(err)


def log_exception(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as err:
            account_id = "N/A"
            if hasattr(request, "user"):
                if hasattr(request.user, "id"):
                    account_id = request.user.id
            log.error(f"Account ID: {account_id} got error: {err}")
            log.exception(err)
            if NOTIFICATION_API_KEY:
                sent_notification(email="ImPosting", message=f"Account ID: {account_id} got error: {err}")
            raise

    return wrapper
