from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'image_generator'

urlpatterns = [
    path('', views.home, name='home'),
    path('test-leonardo-api-key/', views.test_leonardo_api_key, name='test_leonardo_api_key'),

    path('upload-diary/', views.upload_diary, name='upload_diary'),

    path('generate-avatars/', views.generate_avatars, name='generate_avatars'),
    path('generate-images/<str:diary_id>/', views.generate_images, name='generate_images'),
    path('display/<str:generation_id>/', views.display_generated_images, name='display_generated_images'),
    path('select-image/<str:generation_id>/', views.select_image, name='select_image'),

    path('create-dataset/<str:selected_image_id>/', views.create_user_dataset_view, name='create_dataset'),
    path('dataset-progress/', views.dataset_progress, name='dataset_progress'),
    path('dataset-complete/<str:dataset_id>/', views.dataset_complete, name='dataset_complete'),
    path('train-model/<str:dataset_id>/', views.train_model_view, name='train_model'), 
    
    path('trained-model/<str:model_id>/', views.view_trained_model, name='view_trained_model'),
    path('check-model-status/<str:model_id>/', views.check_model_status_view, name='check_model_status'),
    path('generate-with-model/<str:model_id>/', views.generate_with_model, name='generate_with_model'), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)