import os
import requests
import mimetypes
from core import settings
from core.settings import log
from dataclasses import dataclass
from asgiref.sync import sync_to_async
from socialsched.models import PostModel
from requests_oauthlib import OAuth2Session
from integrations.models import IntegrationsModel, Platform
from .common import ErrorAccessTokenNotProvided, ErrorThisTypeOfPostIsNotSupported


@dataclass
class XPoster:
    integration: IntegrationsModel
    api_version: str = "2"

    def __post_init__(self):
        self.access_token = self.integration.access_token_value
        self.refresh_token = self.integration.refresh_token_value

        if not self.access_token:
            raise ErrorAccessTokenNotProvided

        self.base_url = f"https://api.x.com/{self.api_version}/tweets"
        self.upload_url = f"https://api.x.com/{self.api_version}/media/upload"

    def _refresh_access_token(self):
        token_url = "https://api.x.com/oauth2/token"
        client = OAuth2Session(
            client_id=settings.X_CLIENT_ID, token={"refresh_token": self.refresh_token}
        )
        extra = {
            "client_id": settings.X_CLIENT_ID,
            "client_secret": settings.X_CLIENT_SECRET,
        }
        token = client.refresh_token(token_url, **extra)
        self.access_token = token["access_token"]

        IntegrationsModel.objects.filter(platform=Platform.X_TWITTER.value).update(
            access_token=self.access_token
        )

    def _upload_media(self, media_path: str, refresh_token_was_generated: bool = False):
        # Step 1: Check file size
        total_bytes = os.path.getsize(media_path)
        max_size = 5 * 1024 * 1024  # 5 MB

        if total_bytes > max_size:
            raise ValueError("Image size exceeds 5MB limit for upload.")

        # Step 2: Guess MIME type
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type or not mime_type.startswith("image/"):
            raise ValueError(f"Unsupported or missing image MIME type: {mime_type}")

        # Step 3: INIT
        init_response = requests.post(
            self.upload_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
            },
            files={
                "command": (None, "INIT"),
                "media_type": (None, mime_type),
                "total_bytes": (None, str(total_bytes)),
                "media_category": (None, "tweet_image"),
            },
        )

        if init_response.status_code == 401 and not refresh_token_was_generated:
            self._refresh_access_token()
            return self._upload_media(media_path, True)

        init_response.raise_for_status()

        media_id = init_response.json()["data"]["id"]

        # Step 4: APPEND
        with open(media_path, "rb") as f:
            append_response = requests.post(
                self.upload_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                },
                files={
                    "command": (None, "APPEND"),
                    "media_id": (None, media_id),
                    "segment_index": (None, "0"),
                    "media": ("media", f),
                },
            )
            append_response.raise_for_status()

        # Step 5: FINALIZE
        finalize_response = requests.post(
            self.upload_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
            },
            files={
                "command": (None, "FINALIZE"),
                "media_id": (None, media_id),
            },
        )
        finalize_response.raise_for_status()

        return media_id

    def get_post_url(self, id: int):
        return f"https://x.com/user/status/{id}"

    def post_text(self, text: str, refresh_token_was_generated: bool = False):
        response = requests.post(
            url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={"text": text},
        )

        # Unauthorized, token might be expired
        if response.status_code == 401 and refresh_token_was_generated is False:
            self._refresh_access_token()
            self.post_text(text, True)
        response.raise_for_status()

        return self.get_post_url(response.json()["data"]["id"])

    def post_text_with_image(self, text: str, media_path: str):

        media_id = self._upload_media(media_path)

        response = requests.post(
            url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={"text": text, "media": {"media_ids": [media_id]}},
        )
        response.raise_for_status()

        return self.get_post_url(response.json()["data"]["id"])

    def make_post(self, text: str, media_path: str = None):
        if media_path is None:
            return self.post_text(text)

        if media_path.endswith((".jpg", ".jpeg", ".png")):
            return self.post_text_with_image(text, media_path)

        raise ErrorThisTypeOfPostIsNotSupported


@sync_to_async
def update_x_link(post_id: int, post_url: str):
    return PostModel.objects.filter(id=post_id).update(link_x=post_url, post_on_x=False)


async def post_on_x(
    integration,
    post_id: int,
    post_text: str,
    media_path: str = None,
):

    post_url = None
    try:
        poster = XPoster(integration)
        post_url = poster.make_post(post_text, media_path)
        log.success(f"X post url: {post_url}")
    except Exception as err:
        log.exception(err)

    await update_x_link(post_id, post_url)
