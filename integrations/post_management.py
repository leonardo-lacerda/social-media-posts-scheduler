from core import settings
from core.settings import log
from django.utils import timezone
from socialsched.models import PostModel
from .models import IntegrationsModel, Platform
from .platforms.linkedin import post_on_linkedin
from .platforms.xtwitter import post_on_x
from .platforms.threads import post_on_threads
from .platforms.facebook import post_on_facebook
# from .platforms.instagram import post_on_instagram


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
    threads_integration = IntegrationsModel.objects.filter(
        platform=Platform.THREADS.value
    ).first()
    facebook_integration = IntegrationsModel.objects.filter(
        platform=Platform.FACEBOOK.value
    ).first()
    # instagram_integration = IntegrationsModel.objects.filter(
    #     platform=Platform.INSTAGRAM.value
    # ).first()

    for post in posts:
        text = post.description
        file = post.media_file.path if post.media_file else None
        fileobj = post.media_file if post.media_file else None

        if linkedin_integration and post.post_on_linkedin and settings.LINKEDIN_POSTING_ACTIVE:
            linkedin_integration = post_on_linkedin(linkedin_integration, post.id, text, file)
            
        if x_integration and post.post_on_x and settings.X_POSTING_ACTIVE:
            x_integration = post_on_x(x_integration, post.id, text, file)
        
        if threads_integration and post.post_on_threads and settings.THREADS_POSTING_ACTIVE:
            threads_integration = post_on_threads(threads_integration, post.id, text, fileobj)

        if facebook_integration and post.post_on_facebook and settings.FACEBOOK_POSTING_ACTIVE:
            facebook_integration = post_on_facebook(facebook_integration, post.id, text, file)
        
        # if instagram_integration and post.post_on_instagram and settings.INSTAGRAM_POSTING_ACTIVE:
        #     instagram_integration = post_on_instagram(instagram_integration, post.id, text, fileobj)
            
        PostModel.objects.filter(id=post.id).update(posted=True)
