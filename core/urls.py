from django.contrib import admin
from django.urls import path, include
from .settings import MEDIA_URL, MEDIA_ROOT
from django.conf.urls.static import static


urlpatterns = [
    path("", include("socialsched.urls")),
    path("", include("integrations.urls")),
    path("admin/", admin.site.urls),
    path("", include("social_django.urls", namespace="social")),
    path("__reload__/", include("django_browser_reload.urls")),
]

urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
