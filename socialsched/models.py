import os
import uuid
from django.db import models
from django.utils import timezone
from django.utils.timezone import is_aware
from enum import IntEnum


class TextMaxLength(IntEnum):
    X_FREE = 280
    X_BLUE = 4000
    INSTAGRAM = 2200
    FACEBOOK = 63206
    LINKEDIN = 3000


def get_filename(_, filename: str):
    return uuid.uuid4().hex + filename.lower()


class PostModel(models.Model):
    scheduled_on = models.DateTimeField()
    post_timezone = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    account_id = models.IntegerField()
    description = models.TextField(max_length=63206)
    media_file = models.FileField(
        max_length=100_000,
        upload_to=get_filename,
        null=True,
        blank=True,
    )
    post_on_x = models.BooleanField(blank=True, null=True, default=False)
    post_on_instagram = models.BooleanField(blank=True, null=True, default=False)
    post_on_facebook = models.BooleanField(blank=True, null=True, default=False)
    post_on_linkedin = models.BooleanField(blank=True, null=True, default=False)

    link_x = models.CharField(max_length=50000, blank=True, null=True)
    link_instagram = models.CharField(max_length=50000, blank=True, null=True)
    link_facebook = models.CharField(max_length=50000, blank=True, null=True)
    link_linkedin = models.CharField(max_length=50000, blank=True, null=True)

    posted = models.BooleanField(blank=True, null=True, default=False)

    def save(self, *args, **kwargs):

        if not any(
            [
                self.post_on_x,
                self.post_on_instagram,
                self.post_on_facebook,
                self.post_on_linkedin,
            ]
        ):
            raise ValueError("At least one platform must be selected for posting.")

        if not is_aware(self.scheduled_on):
            raise ValueError("The scheduled_on field must be timezone-aware.")

        if self.scheduled_on <= timezone.now():
            raise ValueError("Can't schedule post in the past")

        if self.media_file:
            ext = os.path.splitext(self.media_file.name)[1].lower()
            if ext not in [".jpeg", ".jpg", ".png"]:
                raise ValueError(
                    "Unsupported file type. Only JPEG, PNG images are allowed."
                )

        postlen = len(self.description)

        if postlen > TextMaxLength.X_BLUE and self.post_on_x:
            raise ValueError(f"Maximum length of a X post is {TextMaxLength.X_BLUE}")

        if postlen > TextMaxLength.INSTAGRAM and self.post_on_instagram:
            raise ValueError(
                f"Maximum length of a Instagram post is {TextMaxLength.INSTAGRAM}"
            )

        if postlen > TextMaxLength.FACEBOOK and self.post_on_facebook:
            raise ValueError(
                f"Maximum length of a Facebook post is {TextMaxLength.FACEBOOK}"
            )

        if postlen > TextMaxLength.LINKEDIN and self.post_on_linkedin:
            raise ValueError(
                f"Maximum length of a LinkedIn post is {TextMaxLength.LINKEDIN}"
            )

        super().save(*args, **kwargs)

    class Meta:
        app_label = "socialsched"
        verbose_name_plural = "scheduled"

    def __str__(self):
        return f"Post '{self.description[:150]}' to be/was posted on {self.scheduled_on.isoformat()}"
