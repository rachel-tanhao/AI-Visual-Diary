"""
Create models to store user data, generated images, and any relevant metadata.
- UserDiary: To store user diary entries.
- GeneratedImage: To store information about generated images.
"""

from django.db import models

class UserDiary(models.Model):
    user = models.CharField(max_length=100)
    diary_image = models.ImageField(upload_to='diaries/')
    extracted_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}'s Diary, entry created at {self.created_at}"

class GeneratedImage(models.Model):
    user_diary = models.ForeignKey(UserDiary, on_delete=models.CASCADE)
    image_url = models.URLField()
    description = models.TextField()

    def __str__(self):
        return f"Image for {self.user_diary}"