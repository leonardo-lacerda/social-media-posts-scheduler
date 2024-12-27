from django.urls import path
from . import views


urlpatterns = [
    path("", views.timeline, name="timeline"),
    path("settings/", views.settings_form, name="settings"),
    path("delete-all-data/", views.delete_all_data, name="delete_all_data"),
    path("delete-old-data/", views.delete_old_data, name="delete_old_data"),
    path("export-posted-posts/", views.export_posted_posts, name="export_posted_posts"),
    path("download-excel-template/", views.download_excel_template, name="download_excel_template"),
    path("import-zip/", views.import_zip, name="import_zip"),
    path("schedule/<str:isodate>/", views.schedule_form, name="schedule_form"),
    path("schedule-save/<str:isodate>/", views.schedule_save, name="schedule_save"),
    path("schedule-modify/<int:post_id>/", views.schedule_modify, name="schedule_modify"),
    path("schedule-delete/<int:post_id>/", views.schedule_delete, name="schedule_delete"),
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
]
