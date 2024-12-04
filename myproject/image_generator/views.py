from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UserDiary, GeneratedImage
from .cloudvision import detect_document, format_paragraph
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
        
        # Save the image and create UserDiary instance
        user_diary = UserDiary.objects.create(diary_image=diary_image)
        
        # Get the path to the saved image
        image_path = user_diary.diary_image.path
        
        try:
            # Use your existing cloud vision functions
            words = detect_document(image_path)
            extracted_text = format_paragraph(words)
            
            # Save the extracted text
            user_diary.extracted_text = extracted_text
            user_diary.save()
        except Exception as e:
            extracted_text = f"Error extracting text: {str(e)}"
        
        return render(request, 'image_generator/show_extracted_text.html', {
            'extracted_text': extracted_text,
            'diary_id': user_diary.id
        })
    
    return render(request, 'image_generator/upload_diary.html')

def generate_images(request, diary_id):
    if request.method == 'POST':
        user_diary = UserDiary.objects.get(id=diary_id)
        # Your image generation code will go here
        # For now, just redirect back to home
        return redirect('home')
    return redirect('home')

def display_generated_images(request, generation_id):
    """Fetch and display generated images based on generation_id."""
    images = display_images(generation_id)
    context = {
        'generation_id': generation_id,
        'images': images,
    }
    return render(request, 'image_generator/display_images.html', context)