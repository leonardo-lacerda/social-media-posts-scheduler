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
class FacebookPoster:
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
        self.feed_url = self.base_url + "/feed"
        self.photos_url = self.base_url + "/photos"

    def get_post_url(self, post_id: int):
        return f"https://www.facebook.com/{self.page_id}/posts/{post_id}"

    def post_text(self, text: str):
        payload = {
            "message": text,
            "published": True,
            "access_token": self.access_token,
        }
        response = requests.post(self.feed_url, json=payload)
        response.raise_for_status()
        return self.get_post_url(response.json()["id"])

    def post_text_with_link(self, text: str, link: str):
        payload = {
            "message": text,
            "link": link,
            "published": True,
            "access_token": self.access_token,
        }
        response = requests.post(self.feed_url, json=payload)
        response.raise_for_status()
        return self.get_post_url(response.json()["id"])

    def post_text_with_image(self, text: str, image_url: str):
        payload = {
            "message": text,
            "url": image_url,
            "access_token": self.access_token,
        }
        response = requests.post(self.photos_url, json=payload)
        response.raise_for_status()

        return self.get_post_url(response.json()["post_id"])

    def make_post(self, text: str, media_url: str = None):
        if media_url is None:
            pattern = r"(https?://[^\s]+)$"
            match = re.search(pattern, text)
            if match:
                link = match.group(1)
                return self.post_text_with_link(text, link)
            return self.post_text(text)

        if media_url.endswith((".jpg", ".jpeg", ".png")):
            return self.post_text_with_image(text, media_url)

        raise ErrorThisTypeOfPostIsNotSupported


def post_on_facebook(
    integration,
    post_id: int,
    post_text: str,
    media_url: str = None,
):

    post_url = None

    try:
        poster = FacebookPoster(integration)
        post_url = poster.make_post(post_text, media_url)
        log.success(f"Facebook post url: {post_url}")
    except Exception as err:
        log.exception(err)

    PostModel.objects.filter(id=post_id).update(
        link_facebook=post_url, post_on_facebook=False
    )
