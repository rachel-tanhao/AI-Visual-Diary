from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'image_generator'

urlpatterns = [
    path('', views.home, name='home'),
    path('initial/', views.initial_user_flow, name='initial'),
    path('generate-avatars/', views.avatar_generation_flow, name='generate_avatars'),
    path('display/<str:generation_id>/', views.display_generated_images, name='display_generated_images'),
    
    # 数据集相关的路由
    path('create-dataset/<str:selected_image_id>/', views.create_user_dataset_view, name='create_dataset'),
    path('dataset-progress/', views.dataset_progress, name='dataset_progress'),
    path('dataset-complete/<str:dataset_id>/', views.dataset_complete, name='dataset_complete'),
    
    # 模型相关的路由
    path('train-model/<str:dataset_id>/', views.train_model_view, name='train_model'),
    path('check-model-status/<str:model_id>/', views.check_model_status_view, name='check_model_status'),
    path('trained-model/<str:model_id>/', views.trained_model_view, name='trained_model'),
    
    # 日记处理相关的路由
    path('upload-diary/', views.diary_processing_flow, name='upload_diary'),
    path('view-generated-scenes/', views.view_generated_scenes, name='view_generated_scenes'),
    path('extract-text/', views.extract_text_view, name='extract_text'),
    path('generate-scenes/', views.generate_scenes_view, name='generate_scenes'),
    path('generate-with-model/<str:model_id>/', views.generate_with_model, name='generate_with_model'),
    
    # 工具路由
    path('test-leonardo-api-key/', views.test_leonardo_api_key, name='test_leonardo_api_key'),
    path('logout/', views.logout_view, name='logout'),
]

# urlpatterns = [
#     path('', views.home, name='home'),

#     path('generate-avatars/', views.avatar_generation_flow, name='generate_avatars'),
#     path('create-dataset/', views.create_dataset_flow, name='create_dataset'),
#     path('upload-diary/', views.diary_processing_flow, name='upload_diary'),

#     path('test-leonardo-api-key/', views.test_leonardo_api_key, name='test_leonardo_api_key'),

#     # path('upload-diary/', views.upload_diary, name='upload_diary'),
#     path('process-diary/', views.process_diary_view, name='process_diary'),

#     # path('generate-avatars/', views.generate_avatars, name='generate_avatars'),
#     path('generate-images/<str:diary_id>/', views.generate_images, name='generate_images'),
#     path('display/<str:generation_id>/', views.display_generated_images, name='display_generated_images'),
#     path('select-image/<str:generation_id>/', views.select_image, name='select_image'),

#     # path('create-dataset/<str:selected_image_id>/', views.create_user_dataset_view, name='create_dataset'),
#     path('dataset-progress/', views.dataset_progress, name='dataset_progress'),
#     path('dataset-complete/<str:dataset_id>/', views.dataset_complete, name='dataset_complete'),
#     path('train-model/<str:dataset_id>/', views.train_model_view, name='train_model'), 
    
#     path('trained-model/<str:model_id>/', views.view_trained_model, name='view_trained_model'),
#     path('check-model-status/<str:model_id>/', views.check_model_status_view, name='check_model_status'),
#     path('generate-with-model/<str:model_id>/', views.generate_with_model, name='generate_with_model'), 

# ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)