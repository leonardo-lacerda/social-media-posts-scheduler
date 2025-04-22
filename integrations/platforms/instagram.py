import re
import requests
from core.settings import log
from dataclasses import dataclass
from integrations.models import IntegrationsModel
from socialsched.models import PostModel
from .common import (
    ErrorAccessTokenNotProvided,
    ErrorPageIdNotProvided,
    ErrorThisTypeOfPostIsNotSupported,
)


@dataclass
class InstagramPoster:
    integration: IntegrationsModel
    api_version: str = "v22.0"

    def __post_init__(self):
        self.access_token = self.integration.access_token_value
        self.page_id = self.integration.user_id

        if not self.access_token:
            raise ErrorAccessTokenNotProvided

        if not self.page_id:
            raise ErrorPageIdNotProvided

        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}"
        self.media_url = self.base_url + "/media"
        self.media_publish_url = self.base_url + "/media_publish"

    def get_post_url(self, post_id: int):
        url = f"https://graph.facebook.com/{post_id}"
        params = {
            "fields": "permalink",
            "access_token": self.access_token,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()["permalink"]

    def post_text_with_image(self, text: str, image_url: str):
        params = {
            "image_url": image_url,
            "is_carousel_item": False,
            "alt_text": text,
            "caption": text,
            "access_token": self.access_token,
        }
        container = requests.post(self.media_url, params=params)
        container.raise_for_status()

        publish = requests.post(
            self.media_publish_url,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"creation_id": container.json()["id"]},
        )
        publish.raise_for_status()

        return self.get_post_url(publish.json()["id"])

    def make_post(self, text: str, media_url: str = None):
        if media_url is None:
            log.info("No media url for instagram post. Skip posting.")
            return
        if media_url.endswith((".jpg", ".jpeg", ".png")):
            return self.post_text_with_image(text, media_url)

        raise ErrorThisTypeOfPostIsNotSupported


def post_on_instagram(
    integration,
    post_id: int,
    post_text: str,
    media_url: str = None,
):

    post_url = None

    try:
        poster = InstagramPoster(integration)
        post_url = poster.make_post(post_text, media_url)
        log.success(f"Instagram post url: {post_url}")
    except Exception as err:
        log.exception(err)

    PostModel.objects.filter(id=post_id).update(
        link_instagram=post_url, post_on_instagram=False
    )
