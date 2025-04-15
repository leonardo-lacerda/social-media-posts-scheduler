from facebook_business.api import FacebookAdsApi, FacebookRequest
from facebook_business.adobjects.abstractobject import AbstractObject
from facebook_business.typechecker import TypeChecker
from core.settings import log
from core import settings


def post_on_instagram(
    integration,
    post_id: int,
    post_text: str,
    media_url: str = None,
):
    access_token = integration.access_token
    instagram_account_id = integration.user_id

    FacebookAdsApi.init(
        settings.FACEBOOK_CLIENT_ID, settings.FACEBOOK_CLIENT_SECRET, access_token
    )

    # Step 1: Create media container
    create_media_request = FacebookRequest(
        node_id=instagram_account_id,
        method="POST",
        endpoint="/media",
        api=FacebookAdsApi.get_default_api(),
        param_checker=TypeChecker({}, {}),
        target_class=AbstractObject,
        api_type="EDGE",
        response_parser=None,
    )
    create_media_request.add_params(
        {
            "image_url": media_url,
            "caption": post_text,
            "access_token": access_token,
        }
    )
    media_response = create_media_request.execute()
    media_response_data = media_response.json()
    creation_id = media_response_data.get("id")

    # Step 2: Publish the post
    publish_request = FacebookRequest(
        node_id=instagram_account_id,
        method="POST",
        endpoint="/media_publish",
        api=FacebookAdsApi.get_default_api(),
        param_checker=TypeChecker({}, {}),
        target_class=AbstractObject,
        api_type="EDGE",
        response_parser=None,
    )
    publish_request.add_params(
        {
            "creation_id": creation_id,
            "access_token": access_token,
        }
    )
    publish_response = publish_request.execute()
    publish_response_data = publish_response.json()
    media_id = publish_response_data.get("id")

    permalink_request = FacebookRequest(
        node_id=media_id,
        method="GET",
        endpoint="/",
        api=FacebookAdsApi.get_default_api(),
        param_checker=TypeChecker({}, {}),
        target_class=AbstractObject,
        api_type="NODE",
        response_parser=None,
    )
    permalink_request.add_params(
        {
            "fields": "permalink",
            "access_token": access_token,
        }
    )
    permalink_response = permalink_request.execute()
    permalink_response_data = permalink_response.json()
    post_url = permalink_response_data.get("permalink")
    log.info(f"Instagram post URL: {post_url}")

    return post_url
