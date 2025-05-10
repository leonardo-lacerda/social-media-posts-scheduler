import asyncio
from core import settings
from core.logger import log
from django.utils import timezone
from asgiref.sync import sync_to_async
from socialsched.models import PostModel
from zoneinfo import ZoneInfo
from django.core.files.storage import default_storage
from .models import IntegrationsModel, Platform
from .platforms.linkedin import post_on_linkedin
from .platforms.xtwitter import post_on_x
from .platforms.facebook import post_on_facebook
from .platforms.instagram import post_on_instagram
from .platforms.refresh_tokens import refresh_tokens


@sync_to_async
def get_integration(account_id, platform):
    return IntegrationsModel.objects.filter(
        account_id=account_id, platform=platform
    ).first()


@sync_to_async
def mark_post_posted(post_id):
    return PostModel.objects.filter(id=post_id).update(posted=True)


@sync_to_async
def delete_media_file(post_id: int):
    post = PostModel.objects.get(id=post_id)

    if post.media_file:
        if default_storage.exists(post.media_file.path):
            default_storage.delete(post.media_file.path)
            post.media_file = None

    post.save(skip_validation=True)


def post_scheduled_posts():

    refresh_tokens()

    potential_posts = PostModel.objects.filter(posted=False)
    post_ids_to_publish = []
    now_utc = timezone.now()

    for post in potential_posts:
        target_tz = ZoneInfo(post.post_timezone)
        scheduled_aware = post.scheduled_on.replace(tzinfo=target_tz)
        now_in_target_tz = now_utc.astimezone(target_tz)
        if now_in_target_tz >= scheduled_aware:
            post_ids_to_publish.append(post.pk)

    posts = PostModel.objects.filter(pk__in=post_ids_to_publish)

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
                if cached_integrations.get(fb_key):
                    async_tasks.append(
                        post_on_instagram(
                            cached_integrations[fb_key], post.id, text, media_url
                        )
                    )

            await mark_post_posted(post.id)

        log.debug(f"Gathered async tasks {len(async_tasks)} to run.")
        return await asyncio.gather(*async_tasks)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        log.debug(f"Running async posting for {now_utc}")
        loop.run_until_complete(run_post_tasks())
        loop.run_until_complete(delete_media_file(post.id))
        log.debug(f"Finished async posting for {now_utc}")
    finally:
        loop.close()
