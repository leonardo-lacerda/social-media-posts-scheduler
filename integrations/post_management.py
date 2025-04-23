import asyncio
from core import settings
from core.settings import log
from django.utils import timezone
from asgiref.sync import sync_to_async
from socialsched.models import PostModel
from .models import IntegrationsModel, Platform
from .platforms.linkedin import post_on_linkedin
from .platforms.xtwitter import post_on_x
from .platforms.facebook import post_on_facebook
from .platforms.instagram import post_on_instagram


@sync_to_async
def get_integration(account_id, platform):
    return IntegrationsModel.objects.filter(
        account_id=account_id, platform=platform
    ).first()


@sync_to_async
def mark_post_posted(post_id):
    return PostModel.objects.filter(id=post_id).update(posted=True)


def post_scheduled_posts():
    now = timezone.now()
    posts = PostModel.objects.filter(posted=False, scheduled_on__lte=now)

    if len(posts) == 0:
        return

    async def run_post_tasks():
        async_tasks = []

        cached_integrations = {}

        for post in posts:
            text = post.description
            media_path = post.media_file.path if post.media_file else None
            media_object = post.media_file if post.media_file else None
            media_url = None
            if media_object:
                media_url = settings.APP_URL + media_object.url

            # LINKEDIN
            if post.post_on_linkedin:
                linkedin_key = f"linkedin_integration_{post.account_id}"
                if linkedin_key not in cached_integrations:
                    linkedin_integration = await get_integration(
                        post.account_id, Platform.LINKEDIN.value
                    )
                    if linkedin_integration:
                        cached_integrations[linkedin_key] = linkedin_integration

                if cached_integrations.get(linkedin_key):
                    async_tasks.append(
                        post_on_linkedin(
                            cached_integrations[linkedin_key], post.id, text, media_path
                        )
                    )

            # X
            if post.post_on_x:
                x_key = f"x_integration_{post.account_id}"
                if x_key not in cached_integrations:
                    x_integration = await get_integration(
                        post.account_id, Platform.X_TWITTER.value
                    )
                    if x_integration:
                        cached_integrations[x_key] = x_integration

                if cached_integrations.get(x_key):
                    async_tasks.append(
                        post_on_x(cached_integrations[x_key], post.id, text, media_path)
                    )

            # FACEBOOK
            if post.post_on_facebook:
                fb_key = f"facebook_integration_{post.account_id}"
                if fb_key not in cached_integrations:
                    facebook_integration = await get_integration(
                        post.account_id, Platform.FACEBOOK.value
                    )
                    if facebook_integration:
                        cached_integrations[fb_key] = facebook_integration

                if cached_integrations.get(fb_key):
                    async_tasks.append(
                        post_on_facebook(
                            cached_integrations[fb_key], post.id, text, media_url
                        )
                    )

            # INSTAGRAM
            if post.post_on_instagram:
                ig_key = f"instagram_integration_{post.account_id}"
                if ig_key not in cached_integrations:
                    instagram_integration = await get_integration(
                        post.account_id, Platform.INSTAGRAM.value
                    )
                    if instagram_integration:
                        cached_integrations[ig_key] = instagram_integration

                if cached_integrations.get(ig_key):
                    async_tasks.append(
                        post_on_instagram(
                            cached_integrations[ig_key], post.id, text, media_url
                        )
                    )

            await mark_post_posted(post.id)

        log.debug(f"Gathered async tasks {len(async_tasks)} to run.")
        return await asyncio.gather(*async_tasks)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        log.debug(f"Running async posting for {now}")
        loop.run_until_complete(run_post_tasks())
        log.debug(f"Finished async posting for {now}")
    finally:
        loop.close()
