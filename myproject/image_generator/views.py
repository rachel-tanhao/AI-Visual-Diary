from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UserDiary, GeneratedImage
from .cloudvision import detect_document
from .image_generation import generate, display_images, formatJsonResponse  # Import formatJsonResponse
import requests
import os

def test_api_key(request):
    """Test the Leonardo AI API key and return the response."""
    leonardo_api_key = os.getenv("LEONARDO_API_KEY")
    authorization = f"Bearer {leonardo_api_key}"
    
    url = "https://cloud.leonardo.ai/api/rest/v1/me"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    try:
        response = requests.get(url, headers=headers)
        formatted_response = formatJsonResponse(response)
        return JsonResponse({'status': 'success', 'response': formatted_response})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def home(request):
    """Render the home page."""
    return render(request, 'image_generator/home.html')

def upload_diary(request):
    if request.method == 'POST':
        diary_image = request.FILES['diary_image']
        user_diary = UserDiary.objects.create(diary_image=diary_image)
        
        # Extract text from the uploaded image
        extracted_text = detect_document(user_diary.diary_image.path)
        user_diary.extracted_text = ' '.join(extracted_text)
        user_diary.save()

        # Generate images based on the extracted text
        generation_id = generate(user_diary.extracted_text, num_images=4)
        
        return redirect('display_images', generation_id=generation_id)

    return render(request, 'image_generator/upload_diary.html')

def display_generated_images(request, generation_id):
    """Fetch and display generated images based on generation_id."""
    images = display_images(generation_id)
    context = {
        'generation_id': generation_id,
        'images': images,
    }
    return render(request, 'image_generator/display_images.html', context)