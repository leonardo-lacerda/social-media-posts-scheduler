import os
import time
import requests
import mimetypes
from core import settings
from core.logger import log, send_notification
from dataclasses import dataclass
from asgiref.sync import sync_to_async
from socialsched.models import PostModel
from requests_oauthlib import OAuth2Session
from integrations.models import IntegrationsModel, Platform
from .common import (
    ErrorAccessTokenNotProvided,
    ErrorRefreshTokenNotProvided,
    ErrorThisTypeOfPostIsNotSupported,
)


@dataclass
class XPoster:
    integration: IntegrationsModel
    api_version: str = "2"
    chunk_size: int = 1024 * 1024  # 1MB chunks for uploads

    def __post_init__(self):
        self.access_token = self.integration.access_token_value
        self.refresh_token = self.integration.refresh_token_value

        if not self.access_token:
            raise ErrorAccessTokenNotProvided

        if not self.refresh_token:
            raise ErrorRefreshTokenNotProvided

        self.base_url = f"https://api.x.com/{self.api_version}/tweets"
        self.upload_url = f"https://api.x.com/{self.api_version}/media/upload"

        # Configure OAuth2Session with automatic token refresh
        token = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": "bearer",
            "expires_in": 10,  # This will trigger a refresh when the session is used
        }

        self.client = OAuth2Session(
            client_id=settings.X_CLIENT_ID,
            token=token,
            auto_refresh_url="https://api.x.com/oauth2/token",
            auto_refresh_kwargs={
                "client_id": settings.X_CLIENT_ID,
                "client_secret": settings.X_CLIENT_SECRET,
            },
            token_updater=self._token_saver,
        )

    def _token_saver(self, token):
        self.access_token = token["access_token"]
        new_refresh_token = token.get("refresh_token")

        integration = IntegrationsModel.objects.get(
            platform=Platform.X_TWITTER.value, account_id=self.integration.account_id
        )

        integration.access_token = self.access_token
        if new_refresh_token:
            self.refresh_token = new_refresh_token
            integration.refresh_token = new_refresh_token

        integration.save()

        log.info(f"Updated X token for account {self.integration.account_id}")

    def _upload_media(self, media_path: str):
        # Step 1: Get file info
        total_bytes = os.path.getsize(media_path)
        mime_type, _ = mimetypes.guess_type(media_path)

        if not mime_type:
            raise ValueError(f"Cannot determine MIME type for {media_path}")

        # Determine media category based on MIME type
        if mime_type.startswith("image/"):
            media_category = "tweet_image"
        elif mime_type.startswith("video/"):
            media_category = "tweet_video"
        elif mime_type == "image/gif":
            media_category = "tweet_gif"
        else:
            raise ValueError(f"Unsupported media type: {mime_type}")

        # Step 2: INIT
        files = {
            "command": (None, "INIT"),
            "media_type": (None, mime_type),
            "total_bytes": (None, str(total_bytes)),
            "media_category": (None, media_category),
        }

        # Use the OAuth2Session for all requests to handle token refresh automatically
        init_response = self.client.post(self.upload_url, files=files)
        init_response.raise_for_status()
        media_id = init_response.json()["data"]["id"]

        # Step 3: APPEND (in chunks for larger files)
        with open(media_path, "rb") as f:
            segment_index = 0

            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break

                append_files = {
                    "command": (None, "APPEND"),
                    "media_id": (None, media_id),
                    "segment_index": (None, str(segment_index)),
                    "media": ("media", chunk),
                }

                append_response = self.client.post(self.upload_url, files=append_files)
                append_response.raise_for_status()
                segment_index += 1

        # Step 4: FINALIZE
        finalize_files = {
            "command": (None, "FINALIZE"),
            "media_id": (None, media_id),
        }

        finalize_response = self.client.post(self.upload_url, files=finalize_files)
        finalize_response.raise_for_status()

        # Step 5: Check for processing_info and wait if necessary
        finalize_data = finalize_response.json().get("data", {})
        processing_info = finalize_data.get("processing_info")

        # Only wait for processing if processing_info is present in the response
        if processing_info:
            self._wait_for_processing(media_id)

        return media_id

    def _wait_for_processing(self, media_id):
        processing_info = None
        check_after_secs = 1

        while True:
            status_url = f"{self.upload_url}?command=STATUS&media_id={media_id}"
            status_response = self.client.get(status_url)
            status_response.raise_for_status()

            data = status_response.json().get("data", {})
            processing_info = data.get("processing_info", None)

            if not processing_info:
                return

            state = processing_info.get("state")

            if state == "succeeded":
                return
            elif state == "failed":
                error = processing_info.get("error", {})
                raise Exception(f"Media processing failed: {error}")

            check_after_secs = processing_info.get("check_after_secs", 5)
            time.sleep(check_after_secs)

    def get_post_url(self, id: int):
        return f"https://x.com/user/status/{id}"

    def post_text(self, text: str):
        response = self.client.post(
            url=self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text},
        )
        response.raise_for_status()
        return self.get_post_url(response.json()["data"]["id"])

    def post_text_with_media(self, text: str, media_path: str):
        media_id = self._upload_media(media_path)

        response = self.client.post(
            url=self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text, "media": {"media_ids": [media_id]}},
        )
        response.raise_for_status()

        return self.get_post_url(response.json()["data"]["id"])

    def make_post(self, text: str, media_path: str = None):
        if media_path is None:
            return self.post_text(text)

        # Support for images, videos, and GIFs
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
