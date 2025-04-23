from django.forms import ModelForm, CheckboxInput, DateTimeInput
from .models import PostModel


class PostForm(ModelForm):

    def save(self, commit=True, account_id=None):
        post = super().save(commit=False)
        if account_id is None:
            raise Exception("Please provide request.user.id to account_id parameter")
        post.account_id = account_id
        if commit:
            post.save()
        return post

    class Meta:
        model = PostModel
        fields = [
            "post_on_x",
            "post_on_instagram",
            "post_on_facebook",
            "post_on_linkedin",
            "description",
            "scheduled_on",
            "media_file",
            "post_timezone",
        ]

        widgets = {
            "scheduled_on": DateTimeInput(
                format=("%Y-%m-%dT%H:%M"), attrs={"type": "datetime-local"}
            ),
            "post_on_x": CheckboxInput(),
            "post_on_instagram": CheckboxInput(),
            "post_on_facebook": CheckboxInput(),
            "post_on_linkedin": CheckboxInput(),
        }
