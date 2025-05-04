import os
import time
from typing import Literal
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

        self._setup_oauth_session()

    def _setup_oauth_session(self):
        token = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": "bearer",
        }

        # Create a new session with explicit token refresh parameters
        self.client = OAuth2Session(
            client_id=settings.X_CLIENT_ID,
            token=token,
            auto_refresh_url="https://api.x.com/oauth2/token",
            auto_refresh_kwargs={
                "client_id": settings.X_CLIENT_ID,
                "client_secret": settings.X_CLIENT_SECRET,
                "grant_type": "refresh_token",
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

    def _make_authenticated_request(
        self, method: Literal["post", "get"], url: str, **kwargs
    ):
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = getattr(self.client, method)(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401 and attempt < max_retries - 1:
                    # Force token refresh
                    log.warning(
                        f"Auth failed, refreshing token manually for account {self.integration.account_id}"
                    )
                    self._force_token_refresh()
                    continue
                raise

    def _force_token_refresh(self):
        try:
            token_url = "https://api.x.com/2/oauth2/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": settings.X_CLIENT_ID,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            log.info(f"Token refresh payload: {data}")
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()

            new_token = response.json()
            self._token_saver(new_token)

            # Re-create the OAuth session with new tokens
            self._setup_oauth_session()

            log.info(
                f"Manually refreshed token for account {self.integration.account_id}"
            )
        except Exception as err:
            log.exception(err)
            raise

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

        # Use our wrapper method for authenticated requests
        init_response = self._make_authenticated_request(
            "post", self.upload_url, files=files
        )
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

                self._make_authenticated_request(
                    "post", self.upload_url, files=append_files
                )
                segment_index += 1

        # Step 4: FINALIZE
        finalize_files = {
            "command": (None, "FINALIZE"),
            "media_id": (None, media_id),
        }

        finalize_response = self._make_authenticated_request(
            "post", self.upload_url, files=finalize_files
        )

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
            status_response = self._make_authenticated_request("get", status_url)

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
        response = self._make_authenticated_request(
            "post",
            url=self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text},
        )
        return self.get_post_url(response.json()["data"]["id"])

    def post_text_with_media(self, text: str, media_path: str):
        media_id = self._upload_media(media_path)

        response = self._make_authenticated_request(
            "post",
            url=self.base_url,
            headers={"Content-Type": "application/json"},
            json={"text": text, "media": {"media_ids": [media_id]}},
        )

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
