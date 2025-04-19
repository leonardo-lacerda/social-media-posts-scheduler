from django.forms import ModelForm, CheckboxInput, TimeInput, DateInput
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
            "scheduled_on_date",
            "scheduled_on_time",
            "media_file",
        ]

        widgets = {
            "scheduled_on_date": DateInput(format=("%m/%d/%Y"), attrs={"type": "date"}),
            "scheduled_on_time": TimeInput(format="%H:%M", attrs={"type": "time"}),
            "post_on_x": CheckboxInput(),
            "post_on_instagram": CheckboxInput(),
            "post_on_facebook": CheckboxInput(),
            "post_on_linkedin": CheckboxInput(),
        }
