import requests
from requests_oauthlib import OAuth2Session
from django.conf import settings
from core.settings import log
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from .common import ErrorAccessTokenOrUserIdNotFound


def _refresh_access_token(refresh_token: str):
    token_url = "https://api.x.com/oauth2/token"
    client = OAuth2Session(
        client_id=settings.X_CLIENT_ID, token={"refresh_token": refresh_token}
    )
    extra = {
        "client_id": settings.X_CLIENT_ID,
        "client_secret": settings.X_CLIENT_SECRET,
    }
    token = client.refresh_token(token_url, **extra)
    return token.get("access_token")


def _upload_media(media_path: str, access_token: str):
    if media_path.lower().endswith(".png"):
        media_type = "image/png"
    elif media_path.lower().endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif media_path.lower().endswith(".mp4"):
        media_type = "video/mp4"
    else:
        raise ValueError("Unsupported media type")

    with open(media_path, "rb") as media_file:
        files = {"media": (media_path, media_file, media_type)}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(
            url="https://upload.x.com/2/media/upload", headers=headers, files=files
        )

    media_id = response.json().get("media_id_string")
    return media_id


def post_on_x(integration, post_id: int, post_text: str, media_path: str = None):
    try:

        access_token = integration.access_token
        refresh_token = integration.refresh_token

        if not access_token:
            raise ErrorAccessTokenOrUserIdNotFound

        tweet_url = "https://api.x.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {"text": post_text}

        if media_path:
            media_id = _upload_media(media_path, access_token)
            payload["media"] = {"media_ids": [media_id]}

        response = requests.post(url=tweet_url, headers=headers, json=payload)

        if response.status_code == 401:  # Unauthorized, token might have expired
            access_token = _refresh_access_token(refresh_token)
            headers["Authorization"] = f"Bearer {access_token}"
            response = requests.post(url=tweet_url, headers=headers, json=payload)

            IntegrationsModel.objects.filter(platform=Platform.X_TWITTER.value).update(
                access_token=access_token
            )

        tweet = response.json()

        if "id" in tweet.get("data", ""):
            posted_url = f"https://x.com/user/status/{tweet['data']['id']}"
            PostModel.objects.filter(id=post_id).update(link_x=posted_url)
            log.info(f"Post url: {posted_url}")
            return integration

        log.error(tweet)

        if "duplicate" in tweet.get("detail", ""):
            PostModel.objects.filter(id=post_id).update(post_on_x=False)
            return integration

        IntegrationsModel.objects.filter(platform=Platform.X_TWITTER.value).delete()

        return None

    except Exception as err:
        log.error(err)
        PostModel.objects.filter(id=post_id).update(post_on_x=False)
        IntegrationsModel.objects.filter(platform=Platform.X_TWITTER.value).delete()
        return None
