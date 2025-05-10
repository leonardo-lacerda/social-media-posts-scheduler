import requests
from datetime import timedelta
from core import settings
from django.utils import timezone
from core.logger import log, send_notification
from integrations.models import IntegrationsModel


def refresh_access_token_for_x(integration: IntegrationsModel):
    refresh_token = integration.refresh_token_value
    if not refresh_token:
        log.error(f"Missing refresh token for account {integration.account_id}")

    try:
        token_url = "https://api.x.com/2/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.X_CLIENT_ID,
            "client_secret": settings.X_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        log.info(f"Refreshing access token for account {integration.account_id}")
        response = requests.post(token_url, data=data, headers=headers)
        response.raise_for_status()

        new_token = response.json()

        integration.access_token = new_token["access_token"]

        if new_token.get("refresh_token"):
            integration.refresh_token = new_token["refresh_token"]

        expires_in = new_token.get("expires_in", 7200)
        integration.access_expire = timezone.now() + timedelta(seconds=expires_in - 900)

        integration.save()
        log.success(f"Access token refreshed for account {integration.account_id}")

    except Exception as e:
        log.error(f"Token refresh failed for account {integration.account_id}")
        log.exception(e)
        send_notification(
            "ImPosting",
            f"Token refresh failed for X account {integration.account_id}: {str(e)}",
        )
        integration.delete()


def refresh_access_token_for_linkedin(integration: IntegrationsModel):
    if integration.access_expire < timezone.now():
        log.warning(
            f"Access token expired for account {integration.account_id}. User must reauthenticate."
        )

        integration.access_token = None
        integration.access_expire = None
        integration.save()

        send_notification(
            "ImPosting",
            f"LinkedIn access token expired for account {integration.account_id}.",
        )
        return

    log.info(
        f"LinkedIn access token is still valid for account {integration.account_id}. No action needed."
    )


def refresh_access_token_for_facebook(integration: IntegrationsModel):
    if integration.access_expire < timezone.now():
        log.warning(
            f"Access token expired for account {integration.account_id}. User must reauthenticate."
        )

        integration.access_token = None
        integration.access_expire = None
        integration.save()

        send_notification(
            "ImPosting",
            f"Facebook access token expired for account {integration.account_id}. Please log in again.",
        )
        return

    try:
        token_url = "https://graph.facebook.com/v22.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "client_secret": settings.FACEBOOK_CLIENT_SECRET,
            "fb_exchange_token": integration.access_token_value,  # Use current access token
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        log.info(
            f"Refreshing Facebook access token for account {integration.account_id}"
        )
        response = requests.get(token_url, params=params, headers=headers)
        response.raise_for_status()

        new_token_data = response.json()
        new_access_token = new_token_data.get("access_token")
        expires_in = new_token_data.get("expires_in")

        if not new_access_token:
            raise ValueError("Failed to retrieve new access token.")

        integration.access_token = new_access_token
        integration.access_expire = timezone.now() + timedelta(seconds=expires_in - 900)
        integration.save()

        log.success(f"Facebook token refreshed for account {integration.account_id}")

    except Exception as e:
        log.error(f"Token refresh failed for Facebook account {integration.account_id}")
        log.exception(e)

        send_notification(
            "ImPosting",
            f"Facebook token refresh failed for account {integration.account_id}: {str(e)}",
        )

        integration.delete()
