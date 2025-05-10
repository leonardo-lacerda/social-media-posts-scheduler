import requests
from django.contrib import messages
from django.shortcuts import redirect
from loguru import logger as log
from functools import wraps
from social_django.models import UserSocialAuth
from .settings import logpath
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


# def log_exception(view_func):
#     @wraps(view_func)
#     def wrapper(request, *args, **kwargs):
#         try:
#             return view_func(request, *args, **kwargs)
#         except Exception as err:
#             account_id = "N/A"
#             if hasattr(request, "user"):
#                 try:
#                     user_social_auth = UserSocialAuth.objects.filter(
#                         user=request.user
#                     ).first()
#                     account_id = user_social_auth.uid
#                 except Exception as serr:
#                     log.error(f"User not logged in. {serr}")

#             log.error(f"Account ID: {account_id} got error: {err}")
#             log.exception(err)
#             send_notification(
#                 email="ImPosting",
#                 message=f"AccountId: {account_id} got error {err}",
#             )
#             messages.add_message(
#                 request,
#                 messages.ERROR,
#                 "",
#                 extra_tags="🟥 Error!",
#             )
#             log.debug(f"THE REQUEST PATH: {request.path}")
#             return redirect("/integrations/")

#     return wrapper
