"""
Create models to store user data, generated images, and any relevant metadata.
- UserDiary: To store user diary entries.
- GeneratedImage: To store information about generated images.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    description = models.TextField(max_length=255, blank=True, null=True)  # 允许为空
    created_at = models.DateTimeField(default=timezone.now)  # 使用默认值而不是 auto_now_add
    
    def __str__(self):
        return self.username


class UserCustomModel(models.Model):
    username = models.CharField(max_length=30, unique=True)
    model_id = models.CharField(max_length=100)
    model_status = models.CharField(max_length=20, default='PENDING')  # PENDING, TRAINING, COMPLETE, FAILED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username}'s model: {self.model_id}"