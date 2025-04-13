from django.urls import path
from . import views


urlpatterns = [
    path("", views.calendar, name="calendar"),
    path("delete-all-data/", views.delete_all_data, name="delete_all_data"),
    path("delete-old-data/", views.delete_old_data, name="delete_old_data"),
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
    path("account/", views.user_account, name="account"),
]
