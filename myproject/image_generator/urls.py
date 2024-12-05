from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),  # Home view
    path('upload/', views.upload_diary, name='upload_diary'),
    path('generate/<int:diary_id>/', views.generate_images, name='generate_images'),
    path('display/<str:generation_id>/', views.display_generated_images, name='display_images'),
    path('test-leonardo-api-key/', views.test_leonardo_api_key, name='test_leonardo_api_key'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)