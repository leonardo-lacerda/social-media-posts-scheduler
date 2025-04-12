from django.db import models
from django.utils.translation import gettext_lazy as _



class Platform(models.TextChoices):
    X_TWITTER = "X", _("X")
    LINKEDIN = "LinkedIn", _("LinkedIn")
    FACEBOOK = "Facebook", _("Facebook")
    INSTAGRAM = "Instagram", _("Instagram")
    TIKTOK = "TikTok", _("TikTok")
    YOUTUBE = "YouTube", _("YouTube")


# TODO - save tokens encrypted
class IntegrationsModel(models.Model):
    user_id = models.CharField(max_length=5000, null=True, blank=True)
    access_token = models.CharField(max_length=5000, null=True, blank=True)
    access_expire = models.DateTimeField(null=True, blank=True)
    refresh_token = models.CharField(max_length=5000, null=True, blank=True)
    platform = models.CharField(max_length=1000, choices=Platform)

    class Meta:
        app_label = "integrations"
        verbose_name_plural = "integrations"



