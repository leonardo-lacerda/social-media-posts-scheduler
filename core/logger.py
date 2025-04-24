from loguru import logger as log
from functools import wraps
from .settings import logpath


log.add(
    logpath,
    enqueue=True,
    level="INFO",
    rotation="100 MB",
)


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
            raise

    return wrapper
