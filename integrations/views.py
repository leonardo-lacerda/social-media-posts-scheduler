import uuid
import requests
from requests_oauthlib import OAuth2Session
from core import settings
from core.logger import log
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from social_django.models import UserSocialAuth
from .models import IntegrationsModel, Platform


@login_required
def integrations_form(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    linkedin_integration = IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.LINKEDIN.value
    ).first()
    linkedin_ok = bool(linkedin_integration)

    x_integration = IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.X_TWITTER.value
    ).first()
    x_ok = bool(x_integration)

    facebook_integration = IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.FACEBOOK.value
    ).first()
    facebook_ok = bool(facebook_integration)

    instagram_integration = IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.INSTAGRAM.value
    ).first()
    instagram_ok = bool(instagram_integration)

    x_expire = None
    if x_integration:
        if x_integration.access_expire:
            x_expire = x_integration.access_expire.date()

    linkedin_expire = None
    if linkedin_integration:
        if linkedin_integration.access_expire:
            linkedin_expire = linkedin_integration.access_expire.date()

    facebook_expire = None
    if facebook_integration:
        if facebook_integration.access_expire:
            facebook_expire = facebook_integration.access_expire.date()

    return render(
        request,
        "integrations.html",
        context={
            "x_ok": x_ok,
            "linkedin_ok": linkedin_ok,
            "instagram_ok": facebook_ok,
            "meta_ok": facebook_ok and instagram_ok,
            "x_expire": x_expire,
            "linkedin_expire": linkedin_expire,
            "meta_expire": facebook_expire
        },
    )


@login_required
def linkedin_login(request):
    linkedin_auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        "?response_type=code"
        f"&client_id={settings.LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
        "&scope=w_member_social openid profile email"
    )
    return redirect(linkedin_auth_url)


@login_required
def linkedin_callback(request):
    # Refresh tokens are only for approved Marketing Developer Platform (MDP) partners
    # https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    code = request.GET.get("code")
    if not code:
        messages.error(request, "LinkedIn authorization failed: No code returned.")
        return redirect("/integrations/")

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }
    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=token_data, headers=token_headers)
    response.raise_for_status()
    token_json = response.json()

    access_token = token_json["access_token"]
    access_token_expires_in = token_json["expires_in"]
    access_token_expire = timezone.now() + timedelta(
        seconds=access_token_expires_in - 900
    )

    # Get LinkedIn user info (sub is the unique user ID)
    user_info_url = "https://api.linkedin.com/v2/userinfo"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(user_info_url, headers=headers)
    response.raise_for_status()
    user_info = response.json()
    user_id = user_info.get("sub")

    # Save Linkedin
    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.LINKEDIN.value
    ).delete()

    IntegrationsModel.objects.create(
        account_id=social_uid,
        user_id=user_id,
        access_token=access_token,
        access_expire=access_token_expire,
        platform=Platform.LINKEDIN.value,
    )

    messages.success(
        request,
        "Successfully logged into LinkedIn! Now the app can make posts on your behalf.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")


@login_required
def linkedin_uninstall(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.LINKEDIN.value
    ).delete()

    messages.add_message(
        request,
        messages.SUCCESS,
        "Deleted the access token.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")


@login_required
def x_login(request):
    x_auth_url = (
        "https://x.com/i/oauth2/authorize"
        "?response_type=code"
        f"&client_id={settings.X_CLIENT_ID}"
        f"&redirect_uri={settings.X_REDIRECT_URI}"
        "&scope=tweet.read tweet.write users.read media.write offline.access"
        f"&state={uuid.uuid4().hex}"
        "&code_challenge=challenge"
        "&code_challenge_method=plain"
    )
    return redirect(x_auth_url)


@login_required
def x_callback(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    code = request.GET.get("code")
    if not code:
        raise Exception("Could not get the code from previous call.")

    oauth = OAuth2Session(
        client_id=settings.X_CLIENT_ID, redirect_uri=settings.X_REDIRECT_URI
    )

    token = oauth.fetch_token(
        "https://api.x.com/2/oauth2/token",
        code=code,
        client_secret=settings.X_CLIENT_SECRET,
        code_verifier="challenge",
        include_client_id=True,
        auth=(
            settings.X_CLIENT_ID,
            settings.X_CLIENT_SECRET,
        ),
    )

    user_info = oauth.get("https://api.x.com/2/users/me").json()
    user_id = user_info["data"]["id"]

    access_expire = timezone.now() + timedelta(seconds=token["expires_in"] - 900)

    # Save X
    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.X_TWITTER.value
    ).delete()

    IntegrationsModel.objects.create(
        account_id=social_uid,
        user_id=user_id,
        access_token=token["access_token"],
        refresh_token=token["refresh_token"],
        access_expire=access_expire,
        platform=Platform.X_TWITTER.value,
    )

    messages.add_message(
        request,
        messages.SUCCESS,
        "Successfully logged into X! Now the app can make posts on your behalf.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")


@login_required
def x_uninstall(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.X_TWITTER.value
    ).delete()

    messages.add_message(
        request,
        messages.SUCCESS,
        "Deleted the access token.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")


@login_required
def facebook_login(request):
    fb_login_url = (
        "https://www.facebook.com/v22.0/dialog/oauth"
        "?response_type=code"
        f"&client_id={settings.FACEBOOK_CLIENT_ID}"
        f"&redirect_uri={settings.FACEBOOK_REDIRECT_URI}"
        "&scope=email,public_profile,pages_show_list,pages_manage_posts,instagram_basic,instagram_content_publish,business_management"
    )
    return redirect(fb_login_url)


@login_required
def facebook_callback(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    code = request.GET.get("code")
    if not code:
        raise Exception("Could not get the code from the previous call")

    # Exchange code for access token
    response = requests.post(
        url="https://graph.facebook.com/v22.0/oauth/access_token",
        data={
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "client_secret": settings.FACEBOOK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()

    short_token = response.json().get("access_token")

    # Exchange short-lived token for long-lived token
    response = requests.get(
        url="https://graph.facebook.com/v22.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "client_secret": settings.FACEBOOK_CLIENT_SECRET,
            "fb_exchange_token": short_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]

    # Retrieve user ID using the Graph API directly
    user_info_url = "https://graph.facebook.com/v22.0/me"
    user_info_params = {"access_token": access_token, "fields": "id"}
    user_info_response = requests.get(user_info_url, params=user_info_params)
    user_info_response.raise_for_status()
    user_data = user_info_response.json()
    user_id = user_data.get("id")

    # Retrieve pages associated with the user
    response_pages = requests.get(
        url=f"https://graph.facebook.com/v22.0/{user_id}/accounts",
        params={"access_token": access_token},
    )
    response_pages.raise_for_status()

    response_data = response_pages.json()
    pages_data = response_data["data"]
    page = pages_data[0]
    page_id = page["id"]
    page_access_token = page["access_token"]
    page_access_token_expire = timezone.now() + timedelta(days=60)

    # Retrieve Instagram accounts linked to the page
    response_instagram = requests.get(
        url=f"https://graph.facebook.com/v22.0/{page_id}/instagram_accounts",
        params={"access_token": page_access_token},
    )
    response_instagram.raise_for_status()

    instagram_user_id = response_instagram.json()["data"][0]["id"]

    # Save Facebook
    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.FACEBOOK.value
    ).delete()

    IntegrationsModel.objects.create(
        account_id=social_uid,
        user_id=page_id,
        access_token=page_access_token,
        access_expire=page_access_token_expire,
        platform=Platform.FACEBOOK.value,
    )

    # Save Instagram
    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.INSTAGRAM.value
    ).delete()

    IntegrationsModel.objects.create(
        account_id=social_uid,
        user_id=instagram_user_id,
        access_token=page_access_token,
        access_expire=page_access_token_expire,
        platform=Platform.INSTAGRAM.value,
    )

    messages.add_message(
        request,
        messages.SUCCESS,
        "Successfully logged into Facebook and Instagram! Now the app can make posts on your behalf.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")


@login_required
def facebook_uninstall(request):
    user_social_auth = UserSocialAuth.objects.filter(user=request.user).first()
    social_uid = user_social_auth.pk

    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.FACEBOOK.value
    ).delete()

    IntegrationsModel.objects.filter(
        account_id=social_uid, platform=Platform.INSTAGRAM.value
    ).delete()

    messages.add_message(
        request,
        messages.SUCCESS,
        "Deleted the access tokens.",
        extra_tags="✅ Success!",
    )

    return redirect("/integrations/")
