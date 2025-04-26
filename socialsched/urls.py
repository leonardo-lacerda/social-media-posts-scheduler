from django.urls import path
from . import views


urlpatterns = [
    path("", views.calendar, name="calendar"),
    path("schedule/<str:isodate>/", views.schedule_form, name="schedule_form"),
    path("schedule-save/<str:isodate>/", views.schedule_save, name="schedule_save"),
    path(
        "schedule-modify/<int:post_id>/", views.schedule_modify, name="schedule_modify"
    ),
    path(
        "schedule-delete/<int:post_id>/", views.schedule_delete, name="schedule_delete"
    ),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
]
