from django.urls import path
from .views import upload_diary, display_images

urlpatterns = [
    path('upload/', upload_diary, name='upload_diary'),
    path('display/<int:generation_id>/', display_images, name='display_images'),
]