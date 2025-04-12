import os
import uuid
from django.db import models
from django.utils import timezone
from datetime import datetime
from enum import IntEnum


class TextMaxLength(IntEnum):
    X_FREE = 280
    X_BLUE = 4000
    INSTAGRAM = 2200
    TIKTOK = 2200
    FACEBOOK = 63206
    LINKEDIN = 3000
    YOUTUBE_TITLE = 100
    YOUTUBE_DESCRIPTION = 5000


def get_filename(_, filename: str):
    return uuid.uuid4().hex + filename.lower()


class PostModel(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(max_length=63206)
    scheduled_on_date = models.DateField()
    scheduled_on_time = models.TimeField()
    scheduled_on = models.DateTimeField(blank=True, null=True)
    media_file = models.FileField(
        max_length=100_000,
        upload_to=get_filename,
        null=True,
        blank=True,
    )

    video_file = models.BooleanField(blank=True, null=True, default=False)
    post_on_x = models.BooleanField(blank=True, null=True, default=True)
    post_on_instagram = models.BooleanField(blank=True, null=True, default=True)
    post_on_facebook = models.BooleanField(blank=True, null=True, default=True)
    post_on_linkedin = models.BooleanField(blank=True, null=True, default=True)
    post_on_youtube = models.BooleanField(blank=True, null=True, default=True)
    post_on_tiktok = models.BooleanField(blank=True, null=True, default=True)

    link_x = models.CharField(max_length=50000, blank=True, null=True)
    link_instagram = models.CharField(max_length=50000, blank=True, null=True)
    link_facebook = models.CharField(max_length=50000, blank=True, null=True)
    link_tiktok = models.CharField(max_length=50000, blank=True, null=True)
    link_linkedin = models.CharField(max_length=50000, blank=True, null=True)
    link_youtube = models.CharField(max_length=50000, blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    posted = models.BooleanField(blank=True, null=True, default=False)


    def save(self, *args, **kwargs):

        if not self.scheduled_on:
            naive_scheduled_on = datetime.combine(self.scheduled_on_date, self.scheduled_on_time)
            self.scheduled_on = timezone.make_aware(naive_scheduled_on, timezone.get_current_timezone())

        if self.scheduled_on <= timezone.localtime():
            raise ValueError("Can't schedule post in the past")
        
        if self.media_file:
            ext = os.path.splitext(self.media_file.name)[1].lower()
            if ext not in ['.jpeg', '.jpg', '.png', '.mp4']:
                raise ValueError("Unsupported file type. Only JPEG, PNG images and MP4 videos are allowed.")
            
            if ext == ".mp4":
                self.video_file = True

        if not self.video_file:
            self.post_on_tiktok = False
            self.post_on_youtube = False

        if self.title and self.post_on_youtube:
            if len(self.title) > TextMaxLength.YOUTUBE_TITLE:
                raise ValueError(f"Maximum length of a youtube video title is {TextMaxLength.YOUTUBE_TITLE}")

        postlen = len(self.description)

        if postlen > TextMaxLength.YOUTUBE_DESCRIPTION and self.post_on_youtube:
            raise ValueError(f"Maximum length of a youtube video description is {TextMaxLength.YOUTUBE_DESCRIPTION}")

        if postlen > TextMaxLength.X_BLUE and self.post_on_x:
            raise ValueError(f"Maximum length of a X post is {TextMaxLength.X_BLUE}")

        if postlen > TextMaxLength.INSTAGRAM and self.post_on_instagram:
            raise ValueError(f"Maximum length of a Instagram post is {TextMaxLength.INSTAGRAM}")

        if postlen > TextMaxLength.TIKTOK and self.post_on_tiktok:
            raise ValueError(f"Maximum length of a TikTok video description is {TextMaxLength.TIKTOK}")

        if postlen > TextMaxLength.FACEBOOK and self.post_on_facebook:
            raise ValueError(f"Maximum length of a Facebook post is {TextMaxLength.FACEBOOK}")

        if postlen > TextMaxLength.LINKEDIN and self.post_on_linkedin:
            raise ValueError(f"Maximum length of a LinkedIn post is {TextMaxLength.LINKEDIN}")

        super().save(*args, **kwargs)


    class Meta:
        app_label = "socialsched"
        verbose_name_plural = "scheduled"

    def __str__(self):
        return f"Post '{self.description[:150]}' to be/was posted on {self.scheduled_on.isoformat()}"
