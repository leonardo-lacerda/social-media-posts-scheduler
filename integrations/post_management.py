from django.utils import timezone
from core import settings
from socialsched.models import PostModel
from .models import IntegrationsModel, Platform
from .platforms.linkedin import post_on_linkedin
from .platforms.xtwitter import post_on_x
from .platforms.facebook import post_on_facebook
from .platforms.instagram import post_on_instagram


def post_scheduled_posts():
    now = timezone.localtime()
    posts = PostModel.objects.filter(posted=False, scheduled_on__lte=now)

    if len(posts) == 0:
        return

    linkedin_integration = IntegrationsModel.objects.filter(
        platform=Platform.LINKEDIN.value
    ).first()
    x_integration = IntegrationsModel.objects.filter(
        platform=Platform.X_TWITTER.value
    ).first()
    facebook_integration = IntegrationsModel.objects.filter(
        platform=Platform.FACEBOOK.value
    ).first()
    instagram_integration = IntegrationsModel.objects.filter(
        platform=Platform.INSTAGRAM.value
    ).first()

    for post in posts:
        text = post.description
        media_path = post.media_file.path if post.media_file else None
        media_object = post.media_file if post.media_file else None
        media_url = None
        if media_object:
            media_url = settings.APP_URL + media_object.url

        if linkedin_integration and post.post_on_linkedin:
            linkedin_integration = post_on_linkedin(
                linkedin_integration, post.id, text, media_path
            )

        if x_integration and post.post_on_x:
            x_integration = post_on_x(x_integration, post.id, text, media_path)

        if facebook_integration and post.post_on_facebook:
            facebook_integration = post_on_facebook(
                facebook_integration, post.id, text, media_url
            )

        if instagram_integration and post.post_on_instagram:
            instagram_integration = post_on_instagram(
                instagram_integration, post.id, text, media_url
            )

        # PostModel.objects.filter(id=post.id).update(posted=True)
