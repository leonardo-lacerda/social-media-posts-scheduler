import requests
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from core.settings import log
from .common import ErrorAccessTokenOrUserIdNotFound


def _upload_media(user_id: str, access_token: str, headers: dict, filepath: str):

    if filepath.lower().endswith((".jpg", ".jpeg", ".png")):
        filetype = "image"
    if filepath.lower().endswith(".mp4"):
        filetype = "video"

    upload_payload = {
        "registerUploadRequest": {
            "recipes": [f"urn:li:digitalmediaRecipe:feedshare-{filetype}"],
            "owner": f"urn:li:person:{user_id}",
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }

    upload_response = requests.post(
        url="https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
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
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream",
            },
            data=image_file,
        )

    return asset


def _get_basic_payload(user_id: str, post_text: str, share_media_category: str):

    payload = {
        "author": f"urn:li:person:{user_id}",
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


def post_on_linkedin(integration, post_id: int, post_text: str, media_path: str = None):
    try:

        user_id = integration.user_id
        access_token = integration.access_token

        if access_token is None or user_id is None:
            raise ErrorAccessTokenOrUserIdNotFound

        post_url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        share_media_category = "IMAGE" if media_path else "NONE"

        payload = _get_basic_payload(user_id, post_text, share_media_category)

        if share_media_category == "IMAGE":  # it works for video as well
            asset = _upload_media(user_id, access_token, headers, media_path)
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "description": {"text": post_text[:20].lower()},
                    "media": asset,
                    "title": {"text": post_text[:20]},
                }
            ]

        response = requests.post(url=post_url, headers=headers, json=payload)
        post_data = response.json()

        if "id" in post_data:
            posted_url = f"https://www.linkedin.com/feed/update/{post_data['id']}"
            PostModel.objects.filter(id=post_id).update(link_linkedin=posted_url)
            log.info(f"Post url: {posted_url}")
            return integration

        log.error(post_data)

        if "duplicate" in post_data.get("message", ""):
            PostModel.objects.filter(id=post_id).update(post_on_linkedin=False)
            return integration

        IntegrationsModel.objects.filter(platform=Platform.LINKEDIN.value).delete()

        return None

    except Exception as err:
        log.error(err)
        PostModel.objects.filter(id=post_id).update(post_on_linkedin=False)
        IntegrationsModel.objects.filter(platform=Platform.LINKEDIN.value).delete()
        return None
