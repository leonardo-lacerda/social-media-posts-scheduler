import os
import time
from typing import Literal
import requests
import mimetypes
from datetime import timedelta
from django.utils import timezone
from core import settings
from core.logger import log, send_notification
from dataclasses import dataclass
from asgiref.sync import sync_to_async
from socialsched.models import PostModel
from requests_oauthlib import OAuth2Session
from integrations.models import IntegrationsModel
from .common import (
    ErrorAccessTokenNotProvided,
    ErrorThisTypeOfPostIsNotSupported,
)


def refresh_access_token_for_x(integration: IntegrationsModel):
    refresh_token = integration.refresh_token_value
    if not refresh_token:
        log.error(f"Missing refresh token for account {integration.account_id}")
        raise ValueError("No refresh token available")

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


@dataclass
class XPoster:
    integration: IntegrationsModel
    api_version: str = "2"
    chunk_size: int = 1024 * 1024  # 1MB

    def __post_init__(self):
        self.access_token = self.integration.access_token_value
        if not self.access_token:
            raise ErrorAccessTokenNotProvided

        self.base_url = f"https://api.x.com/{self.api_version}/tweets"
        self.upload_url = f"https://api.x.com/{self.api_version}/media/upload"
        self.client = OAuth2Session(
            client_id=settings.X_CLIENT_ID,
            token={"access_token": self.access_token, "token_type": "bearer"},
        )

    def _make_authenticated_request(
        self, method: Literal["post", "get"], url: str, **kwargs
    ):
        response = getattr(self.client, method)(url, **kwargs)
        response.raise_for_status()
        return response

    def _upload_media(self, media_path: str):
        total_bytes = os.path.getsize(media_path)
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type:
            raise ValueError(f"Cannot determine MIME type for {media_path}")

        if mime_type.startswith("image/"):
            media_category = "tweet_image"
        elif mime_type.startswith("video/"):
            media_category = "tweet_video"
        elif mime_type == "image/gif":
            media_category = "tweet_gif"
        else:
            raise ErrorThisTypeOfPostIsNotSupported

        init_response = self._make_authenticated_request(
            "post",
            self.upload_url,
            files={
                "command": (None, "INIT"),
                "media_type": (None, mime_type),
                "total_bytes": (None, str(total_bytes)),
                "media_category": (None, media_category),
            },
        )
        media_id = init_response.json()["data"]["id"]

        with open(media_path, "rb") as f:
            for segment_index, chunk in enumerate(
                iter(lambda: f.read(self.chunk_size), b"")
            ):
                self._make_authenticated_request(
                    "post",
                    self.upload_url,
                    files={
                        "command": (None, "APPEND"),
                        "media_id": (None, media_id),
                        "segment_index": (None, str(segment_index)),
                        "media": ("media", chunk),
                    },
                )

        finalize_response = self._make_authenticated_request(
            "post",
            self.upload_url,
            files={
                "command": (None, "FINALIZE"),
                "media_id": (None, media_id),
            },
        )

        processing_info = (
            finalize_response.json().get("data", {}).get("processing_info")
        )
        if processing_info:
            self._wait_for_processing(media_id)

        return media_id

    def _wait_for_processing(self, media_id):
        while True:
            response = self._make_authenticated_request(
                "get", f"{self.upload_url}?command=STATUS&media_id={media_id}"
            )
            info = response.json().get("data", {}).get("processing_info")

            if not info or info.get("state") == "succeeded":
                return
            if info.get("state") == "failed":
                raise Exception(f"Media processing failed: {info.get('error')}")

            time.sleep(info.get("check_after_secs", 5))

    def get_post_url(self, id: int):
        return f"https://x.com/user/status/{id}"

    def post_text(self, text: str):
        response = self._make_authenticated_request(
            "post",
            self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text},
        )
        return self.get_post_url(response.json()["data"]["id"])

    def post_text_with_media(self, text: str, media_path: str):
        media_id = self._upload_media(media_path)
        response = self._make_authenticated_request(
            "post",
            self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text, "media": {"media_ids": [media_id]}},
        )
        return self.get_post_url(response.json()["data"]["id"])

    def make_post(self, text: str, media_path: str = None):
        if not media_path:
            return self.post_text(text)
        if media_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov")):
            return self.post_text_with_media(text, media_path)
        raise ErrorThisTypeOfPostIsNotSupported


@sync_to_async
def update_x_link(post_id: int, post_url: str):
    post = PostModel.objects.get(id=post_id)
    post.link_x = post_url
    post.post_on_x = False
    post.save(skip_validation=True)


async def post_on_x(
    integration: IntegrationsModel,
    post_id: int,
    post_text: str,
    media_path: str = None,
):
    post_url = None
    try:
        poster = XPoster(integration)
        post_url = poster.make_post(post_text, media_path)
        log.success(f"X post url: {integration.account_id} {post_url}")
    except Exception as err:
        log.error(f"X post error: {integration.account_id} {err}")
        log.exception(err)
        send_notification(
            "ImPosting", f"AccountId: {integration.account_id} got error {str(err)}"
        )
        await sync_to_async(integration.delete)()

    await update_x_link(post_id, post_url)
