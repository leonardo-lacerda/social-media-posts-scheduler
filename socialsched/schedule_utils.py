import os
import zipfile
import pandas as pd
from functools import lru_cache
from datetime import date, timedelta, datetime
from django.conf import settings
from django.core.files.base import ContentFile
from .models import PostModel


def get_df_from_zip(zip_file, export_path):

    zip_path = os.path.join(settings.MEDIA_ROOT, "exports", "external.zip")
    os.makedirs(export_path, exist_ok=True)

    with open(zip_path, "wb+") as destination:
        for chunk in zip_file.chunks():
            destination.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(export_path)

    excel_file_path = os.path.join(export_path, "schedule_posts.xlsx")
    df = pd.read_excel(excel_file_path, dtype={"Date YYYY-MM-DD at HH:MM": "str"})

    try:
        df["Post at YYYY-MM-DD at HH:MM"] = pd.to_datetime(df["Post at YYYY-MM-DD at HH:MM"], format="%Y-%m-%d at %H:%M")
    except Exception:
        df["Post at YYYY-MM-DD at HH:MM"] = pd.to_datetime(df["Post at YYYY-MM-DD at HH:MM"], format="mixed").dt.round(freq='s')

    return df



def save_row_on_post(row: dict, scheduled_on: datetime, export_path: str):

    has_yes = lambda val: val.strip().lower() in ["yes", "y"]

    post = PostModel(
        title=row["Title"],
        description=row["Description"],
        scheduled_on_date=scheduled_on.date(),
        scheduled_on_time=scheduled_on.time(),
        scheduled_on=scheduled_on, 
        post_on_x=has_yes(row["X"]),
        post_on_instagram=has_yes(row["Instagram"]),
        post_on_facebook=has_yes(row["Facebook"]),
        post_on_tiktok=has_yes(row["Tiktok"]),
        post_on_linkedin=has_yes(row["Linkedin"]),
        post_on_youtube=has_yes(row["Youtube"]),
    )

    file_name = row["File Name"]
    file_path = os.path.join(export_path, "files", file_name)
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            post.media_file.save(file_name, ContentFile(f.read()))

    post.save()


@lru_cache(maxsize=None)
def get_year_dates(year: int) -> list[date]:
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


def get_initial_month_placeholder(today, d):

    past_month_bg = "slate-800"
    current_month_bg = "jade-650"
    next_month_bg = "blue-850"
    light_text = "blue-50"
    dark_text = "blue-250"

    current_month = today.date().month == d.month and today.year == d.year

    if current_month:
        bg = current_month_bg
        text_color = light_text
    elif d < today.date():
        bg = past_month_bg
        text_color = dark_text
    else:
        bg = next_month_bg
        text_color = light_text

    return {
        "article_background": bg,
        "text_color": text_color,
        "current_month": current_month,
        "days": [],
    }


def get_day_data(posts, d):
    posts_count = 0
    post_on_x = 0
    post_on_instagram = 0
    post_on_facebook = 0
    post_on_tiktok = 0
    post_on_linkedin = 0
    post_on_youtube = 0
    for post in posts:

        if post["scheduled_on"].date() != d:
            continue

        post_on_x += 1 if post["post_on_x"] else 0
        post_on_instagram += 1 if post["post_on_instagram"] else 0
        post_on_facebook += 1 if post["post_on_facebook"] else 0
        post_on_tiktok += 1 if post["post_on_tiktok"] else 0
        post_on_linkedin += 1 if post["post_on_linkedin"] else 0
        post_on_youtube += 1 if post["post_on_youtube"] else 0
        posts_count += (
            1
            if any(
                [
                    post["post_on_x"],
                    post["post_on_instagram"],
                    post["post_on_facebook"],
                    post["post_on_tiktok"],
                    post["post_on_linkedin"],
                    post["post_on_youtube"],
                ]
            )
            else 0
        )

    return {
        "isodate": d.isoformat(),
        "day": f"{d.day:02}",
        "posts_count": posts_count,
        "instagram_count": post_on_instagram,
        "facebook_count": post_on_facebook,
        "linkedin_count": post_on_linkedin,
        "twitter_count": post_on_x,
        "tiktok_count": post_on_tiktok,
        "youtube_count": post_on_youtube,
    }
