from django.forms import ModelForm, CheckboxInput, TimeInput, DateInput, TextInput
from .models import PostModel


class PostForm(ModelForm):
    class Meta:
        model = PostModel
        fields = [
            "post_on_x",
            "post_on_instagram",
            "post_on_facebook",
            "post_on_linkedin",
            "title",
            "description",
            "scheduled_on_date",
            "scheduled_on_time",
            "media_file",
            "video_file",
        ]

        widgets = {
            "title": TextInput(attrs={"autocomplete": "off"}),
            "scheduled_on_date": DateInput(format=("%m/%d/%Y"), attrs={"type": "date"}),
            "scheduled_on_time": TimeInput(format='%H:%M', attrs={'type': 'time'}),
            "post_on_x": CheckboxInput(),
            "post_on_instagram": CheckboxInput(),
            "post_on_facebook": CheckboxInput(),
            "post_on_linkedin": CheckboxInput(),
        }


