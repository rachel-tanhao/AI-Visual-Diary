from django import forms
from .models import UserProfile

class AvatarGenerationForm(forms.Form):
    describe_user = forms.CharField(
        label='Describe yourself',
        max_length=255,
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Example: 8-year-old Asian girl with black hair, pigtail hairstyle, very pretty, cute'
        })
    )
    num_images = forms.IntegerField(
        label='Number of Images',
        min_value=1,
        max_value=10,
        required=True,
        initial=4
    )