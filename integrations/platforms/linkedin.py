import requests
from core.settings import log
from dataclasses import dataclass
from socialsched.models import PostModel
from .common import (
    ErrorAccessTokenNotProvided,
    ErrorUserIdNotProvided,
)


@dataclass
class LinkedinPoster:
    integration: any
    api_version: str = "v2"

    def __post_init__(self):

        self.user_id = self.integration.user_id
        self.access_token = self.integration.access_token

        if not self.user_id:
            raise ErrorUserIdNotProvided

        if not self.access_token:
            raise ErrorAccessTokenNotProvided

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _get_basic_payload(self, post_text: str, share_media_category: str):

        payload = {
            "author": f"urn:li:person:{self.user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": share_media_category,
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        return payload

    def _upload_media(self, filepath: str):

        upload_payload = {
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{self.user_id}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }

        upload_response = requests.post(
            url=f"https://api.linkedin.com/{self.api_version}/assets?action=registerUpload",
            headers=self.headers,
            json=upload_payload,
        )
        upload_data = upload_response.json()
        upload_url = upload_data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset = upload_data["value"]["asset"]

        with open(filepath, "rb") as image_file:
            requests.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/octet-stream",
                },
                data=image_file,
            )

        return asset

    def make_post(self, text: str, media_path: str = None):
        share_media_category = "IMAGE" if media_path else "NONE"
        payload = self._get_basic_payload(text, share_media_category)

        if share_media_category == "IMAGE":
            asset = self._upload_media(media_path)
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "description": {"text": text[:20].lower()},
                    "media": asset,
                    "title": {"text": text[:20]},
                }
            ]

        response = requests.post(
            url=f"https://api.linkedin.com/{self.api_version}/ugcPosts",
            headers=self.headers,
            json=payload,
        )

        return f"https://www.linkedin.com/feed/update/{response.json()['id']}"


def post_on_linkedin(
    integration,
    post_id: int,
    post_text: str,
    media_path: str = None,
):

    post_url = None

    try:
        poster = LinkedinPoster(integration)
        post_url = poster.make_post(post_text, media_path)
        log.success(f"Linkedin post url: {post_url}")
    except Exception as err:
        log.exception(err)

    PostModel.objects.filter(id=post_id).update(
        link_linkedin=post_url, post_on_linkedin=False
    )
