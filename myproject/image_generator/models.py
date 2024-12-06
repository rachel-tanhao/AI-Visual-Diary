"""
Create models to store user data, generated images, and any relevant metadata.
- UserDiary: To store user diary entries.
- GeneratedImage: To store information about generated images.
"""

from django.db import models
from django.contrib.auth.models import User

class UserDiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Make user optional
    diary_image = models.ImageField(upload_to='diary_images/')
    extracted_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diary entry {self.id} - {self.created_at}"


class GeneratedImage(models.Model):
    user_diary = models.ForeignKey(UserDiary, on_delete=models.CASCADE)
    image_url = models.URLField()
    description = models.TextField()

    def __str__(self):
        return f"Image for {self.user_diary}"


class UserProfile(models.Model):
    username = models.CharField(max_length=30, unique=True)
    # Add other fields as needed, e.g., email, avatar, etc.

    def __str__(self):
        return self.username