from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import UserDiary, GeneratedImage
from .cloudvision import parse_diary
from .image_generation import generate, display_images, formatJsonResponse  # Import formatJsonResponse
from django.shortcuts import render
import requests
import os


def home(request):
    """Render the home page."""
    return render(request, 'image_generator/home.html')


def test_leonardo_api_key(request):
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


def upload_diary(request):
    if request.method == 'POST':
        diary_image = request.FILES['diary_image']
        # Save the image and create UserDiary instance
        user_diary = UserDiary.objects.create(diary_image=diary_image)
        # Get the path to the saved image
        image_path = user_diary.diary_image.path
        
        try:
            # Use existing cloud vision functions to parse the uploaded image
            extracted_text = parse_diary(image_path)
            user_diary.extracted_text = extracted_text # pass text to the instance
            user_diary.save() # Save the extracted text
        except Exception as e:
            extracted_text = f"Error extracting text: {str(e)}"
        
        return render(request, 'image_generator/show_extracted_text.html', {
            'extracted_text': extracted_text,
            'diary_id': user_diary.id,
            'diary_image': user_diary.diary_image  # Pass the image to the template
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
    """View to display generated images"""
    # Get images using the function from image_generation.py
    images = display_images(generation_id)
    
    # Add debugging information
    print(f"Generation ID: {generation_id}")
    print(f"Number of images found: {len(images)}")
    if images:
        print("Image URLs:", [img['url'] for img in images])
    
    context = {
        'generation_id': generation_id,
        'images': images,
    }
    return render(request, 'image_generator/display_images.html', context)


def select_image(request, generation_id):
    if request.method == 'POST':
        # Debug print all POST data
        print("POST data:", request.POST)
        
        selected_image_id = request.POST.get('image_id')
        print("Raw selected_image_id:", selected_image_id)
        
        if selected_image_id:
            request.session['selected_image_id'] = selected_image_id
            print(f"Stored image ID in session: {selected_image_id}")
            
            # Instead of redirecting to home, let's show a success page
            return render(request, 'image_generator/selection_success.html', {
                'selected_image_id': selected_image_id,
                'generation_id': generation_id
            })
        else:
            print("No image_id found in POST data")
    else:
        print("Request method was not POST")
    
    return redirect('display_generated_images', generation_id=generation_id)