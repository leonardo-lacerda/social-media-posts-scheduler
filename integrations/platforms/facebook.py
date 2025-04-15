from core.settings import log
from core import settings
from socialsched.models import PostModel
from integrations.models import IntegrationsModel, Platform
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page
from .common import ErrorAccessTokenOrUserIdNotFound


def post_on_facebook(
    integration,
    post_id: int,
    post_text: str,
    media_url: str = None,
):

    access_token = integration.access_token
    page_id = integration.user_id

    FacebookAdsApi.init(
        settings.FACEBOOK_CLIENT_ID, settings.FACEBOOK_CLIENT_SECRET, access_token
    )

    page = Page(page_id)
    post_params = {"message": post_text, "published": True}

    if media_url.endswith((".jpg", ".jpeg", ".png")):
        media_response = page.create_photo(
            params={
                "url": media_url,
                "published": False,
            }
        )

    # elif media_url.endswith(".mp4"):
    #     media_response = page.create_video(
    #         params={
    #             "file_url": media_url,
    #             "published": False,
    #         }
    #     )
    # else:
    #     raise Exception(
    #         f"File {media_url} not supported! Only .jpg, .jpeg, .png and .mp4 are allowed."
    #     )

    media_id = media_response["id"]
    post_params["attached_media[0]"] = f'{{"media_fbid":"{media_id}"}}'

    response = page.create_feed(params=post_params)
    post_id = response["id"]
    post_url = f"https://www.facebook.com/{page_id}/posts/{post_id}"
    print("Facebook post URL: ", post_url)
    return post_url
