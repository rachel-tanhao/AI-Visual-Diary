from django import forms
from .models import UserProfile

class AvatarGenerationForm(forms.Form):
    username = forms.CharField(
        label='Username',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter a unique username'
        })
    )
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

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long")
        if not username.isalnum():
            raise forms.ValidationError("Username can only contain letters and numbers")
        if UserProfile.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username