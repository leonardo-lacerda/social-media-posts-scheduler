import time
import requests
from core.settings import log
from core import settings
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from .common import ErrorAccessTokenOrUserIdNotFound

# TODO - some permision error here
def post_on_instagram(integration, post_id: int, post_text: str, media_obj: str):
    try:
        access_token = integration.access_token
        app_id = integration.user_id

        media_url = settings.APP_URL + media_obj.url

        log.info(f"Media url: {media_url}")

        if access_token is None or app_id is None:
            raise ErrorAccessTokenOrUserIdNotFound

        # Step 1: Create media container
        media_response = requests.post(
            f"https://graph.facebook.com/v21.0/{app_id}/media",
            params={"access_token": access_token},
            data={
                "image_url": media_url,
                "caption": post_text,
            }
        )

        if media_response.status_code != 200:
            log.error(f"Media container creation failed: {media_response.json()}")
            raise Exception("Failed to create media container on Instagram")

        media_id = media_response.json().get("id")

        # Check media status
        status = 'IN_PROGRESS'
        while status == 'IN_PROGRESS':
            status_response = requests.get(
                f"https://graph.facebook.com/v21.0/{media_id}",
                params={"access_token": access_token, "fields": "status_code"}
            )
            if status_response.status_code != 200:
                log.error(f"Failed to check media status: {status_response.json()}")
                raise Exception("Failed to check media status on Instagram")

            status = status_response.json().get("status_code")
            if status == 'IN_PROGRESS':
                time.sleep(3)

        if status != 'FINISHED':
            log.error(f"Media status not finished: {status}")
            raise Exception("Media status not finished on Instagram")

        # Step 2: Publish media
        publish_response = requests.post(
            f"https://graph.facebook.com/v21.0/{app_id}/media_publish",
            params={"access_token": access_token},
            data={
                "creation_id": media_id,
            }
        )

        if publish_response.status_code != 200:
            log.error(f"Media publish failed: {publish_response.json()}")
            raise Exception("Failed to publish media on Instagram")

        posted_url = f"https://www.instagram.com/p/{publish_response.json()['id']}/"

        # Update the post model with the Instagram link
        PostModel.objects.filter(id=post_id).update(link_instagram=posted_url)
        log.info(f"Post url: {posted_url}")

    except Exception as err:
        log.error(err)
        PostModel.objects.filter(id=post_id).update(post_on_instagram=False)
        # IntegrationsModel.objects.filter(platform=Platform.INSTAGRAM.value).delete()
        return None