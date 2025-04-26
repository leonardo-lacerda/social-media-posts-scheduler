from django.apps import AppConfig


class SocialschedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "socialsched"

    def ready(self):
        import socialsched.signals
