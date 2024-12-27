import requests
from core.settings import log
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from .common import ErrorAccessTokenOrUserIdNotFound


def post_on_facebook(integration, post_id: int, post_text: str, media_path: any = None):
    try:

        access_token = integration.access_token
        page_id = integration.user_id

        if access_token is None or page_id is None:
            raise ErrorAccessTokenOrUserIdNotFound
        
        if media_path:
            with open(media_path, 'rb') as media_file:
                media_response = requests.post(
                    f"https://graph.facebook.com/v21.0/{page_id}/photos",
                    params={"access_token": access_token},
                    files={"source": media_file},
                    data={"published": False}
                )

            if media_response.status_code != 200:
                log.error(f"Media upload failed: {media_response.json()}")
                raise Exception("Failed to upload media to Facebook")

            media_id = media_response.json().get("id")

            post_response = requests.post(
                f"https://graph.facebook.com/v21.0/{page_id}/feed",
                params={"access_token": access_token},
                data={
                    "message": post_text,
                    "attached_media[0]": f'{{"media_fbid":"{media_id}"}}',
                    "published": "true"  # Publish immediately
                }
            )
        else:
            post_response = requests.post(
                f"https://graph.facebook.com/v21.0/{page_id}/feed",
                params={"access_token": access_token},
                data={
                    "message": post_text,
                    "published": "true"
                }
            )
        
        if post_response.status_code != 200:
            log.error(post_response.content)
            PostModel.objects.filter(id=post_id).update(post_on_facebook=False)
            IntegrationsModel.objects.filter(platform=Platform.FACEBOOK.value).delete()
            return None

        posted_url = f"https://www.facebook.com/{post_response.json()["id"]}"

        PostModel.objects.filter(id=post_id).update(link_facebook=posted_url)
        log.info(f"Post url: {posted_url}")

    except Exception as err:
        log.error(err)
        PostModel.objects.filter(id=post_id).update(post_on_facebook=False)
        IntegrationsModel.objects.filter(platform=Platform.FACEBOOK.value).delete()
        return None
