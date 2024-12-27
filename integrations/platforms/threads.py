import time
import requests
from django.conf import settings
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from core.settings import log
from .common import ErrorAccessTokenOrUserIdNotFound


def post_on_threads(integration, post_id: int, post_text: str, media_obj: any = None):
    try:
        user_id = integration.user_id
        access_token = integration.access_token

        if access_token is None or user_id is None:
            raise ErrorAccessTokenOrUserIdNotFound

        media_type = "TEXT"

        params = {
            "text": post_text,
            "media_type": media_type,
            "access_token": access_token,
        }

        if media_obj is not None:
            media_url = settings.APP_URL + media_obj.url
            
            if media_obj.path.lower().endswith(("png", "jpg", "jpeg")):
                params["media_type"] = "IMAGE"
                params["image_url"] = media_url

            if media_obj.path.lower().endswith(".mp4"):
                params["media_type"] = "VIDEO"
                params["video_url"] = media_url

        response_creation = requests.post(
            url=f"https://graph.threads.net/v1.0/{user_id}/threads",
            params=params,
            headers={"Content-Type": "application/json"},
        )

        creation_id = response_creation.json().get("id")

        if not creation_id:
            log.error(response_creation.content)
            PostModel.objects.filter(id=post_id).update(post_on_threads=False)
            IntegrationsModel.objects.filter(platform=Platform.THREADS.value).delete()
            return None
        
        # https://developers.facebook.com/docs/threads/posts
        time.sleep(10) # recommended 30 seconds

        ready_to_publish_func = lambda: requests.get(
            url=f"https://graph.threads.net/v1.0/{creation_id}",
            params={"fields": "status,error_message", "access_token": access_token},
        )

        response_ready_to_publish = ready_to_publish_func()

        log.info(response_ready_to_publish.content)

        ready_to_publish = False
        if response_ready_to_publish.json()["status"] == "FINISHED":
            ready_to_publish = True
        
        if not ready_to_publish:
            for _ in range(5):
                time.sleep(60)
                response_ready_to_publish = ready_to_publish_func()

                ready_to_publish = False
                if response_ready_to_publish.json()["status"] == "FINISHED":
                    ready_to_publish = True      
                    break      
            
        if not ready_to_publish:
            log.error(response_ready_to_publish.content)
            PostModel.objects.filter(id=post_id).update(post_on_threads=False)
            IntegrationsModel.objects.filter(platform=Platform.THREADS.value).delete()
            return None
        
        response_publish = requests.post(
            url=f"https://graph.threads.net/v1.0/{user_id}/threads_publish?creation_id={creation_id}&access_token={access_token}",
            headers={"Content-Type": "application/json"},
        )

        publish_id = response_publish.json().get("id")

        if not publish_id:
            log.error(response_publish.content)
            PostModel.objects.filter(id=post_id).update(post_on_threads=False)
            IntegrationsModel.objects.filter(platform=Platform.THREADS.value).delete()
            return None

        response_url = requests.get(
            url=f"https://graph.threads.net/v1.0/{publish_id}",
            params={"fields": "id,permalink", "access_token": access_token},
        )

        posted_url = response_url.json().get("permalink")

        if not posted_url:
            log.error(response_url.content)
            PostModel.objects.filter(id=post_id).update(post_on_threads=False)
            IntegrationsModel.objects.filter(platform=Platform.THREADS.value).delete()
            return None

        PostModel.objects.filter(id=post_id).update(link_threads=posted_url)
        log.info(f"Post url: {posted_url}")

        return integration

    except Exception as err:
        log.error(err)
        PostModel.objects.filter(id=post_id).update(post_on_threads=False)
        IntegrationsModel.objects.filter(platform=Platform.THREADS.value).delete()
        return None
