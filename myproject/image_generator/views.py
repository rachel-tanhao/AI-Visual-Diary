from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from .models import UserDiary, GeneratedImage
from .cloudvision import parse_diary
from .image_generation import (
    generate, 
    display_images, 
    format_json_response,
    create_user_dataset,
    get_number_of_images_in_dataset,
    create_dataset,
    generate_with_image_id,
    check_generation_status,
    get_generated_image_ids,
    upload_image_to_dataset,
    get_number_of_images_in_dataset,
    display_all_images_in_dataset
)
import requests
import os
import logging
import json
from django.http import JsonResponse
import threading
import time

logger = logging.getLogger(__name__)


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
        formatted_response = format_json_response(response)
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
    """Generate images based on the diary text"""
    if request.method == 'POST':
        # Your image generation logic here
        # This should use your Leonardo AI functions
        pass
    return HttpResponseRedirect(reverse('image_generator:dataset_complete', args=[dataset_id]))


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
<<<<<<< Updated upstream
    return render(request, 'image_generator/display_images.html', context)
=======
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


def create_user_dataset_view(request, selected_image_id):
    if request.method == 'POST':
        describe_user = request.session.get('user_description', "8-year-old Asian girl with black hair, pigtail hairstyle, very pretty, cute")
        dataset_name = f"user_dataset_{selected_image_id[:8]}"
        
        # Initialize progress in session
        request.session['dataset_progress'] = {
            'current_activity': '',
            'completed_activities': 0,
            'total_activities': 9,
            'logs': [],
            'status': 'starting',
            'dataset_id': None
        }
        request.session.modified = True
        
        # Start dataset creation in background thread
        thread = threading.Thread(
            target=create_dataset_background,
            args=(request.session.session_key, dataset_name, selected_image_id, describe_user)
        )
        thread.start()
        
        return render(request, 'image_generator/dataset_progress.html', {
            'selected_image_id': selected_image_id
        })
    
    return redirect('image_generator:home')


def create_dataset_background(session_key, dataset_name, seed_image_id, describe_user):
    """Background task to create dataset and update progress"""
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore(session_key=session_key)
    
    try:
        # Create dataset
        dataset_id = create_dataset(dataset_name)
        print(f"Dataset created with ID: {dataset_id}")  # Debug log
        
        if not dataset_id:
            print("Failed to create dataset")  # Debug log
            session['dataset_progress']['status'] = 'failed'
            session['dataset_progress']['logs'].append("Failed to create dataset")
            session.save()
            return
        
        session['dataset_progress']['dataset_id'] = dataset_id
        session['dataset_progress']['status'] = 'in_progress'
        session['dataset_progress']['logs'].append(f"Dataset created with ID: {dataset_id}")
        session.save()
        
        activities = [
            "playing basketball", "riding a bicycle", "reading a book",
            "playing the piano", "cooking in the kitchen", "flying a kite",
            "playing tennis", "swimming in a pool", "watering flowers"
        ]
        
        for idx, activity in enumerate(activities):
            try:
                print(f"Processing activity: {activity}")  # Debug log
                
                session['dataset_progress'].update({
                    'current_activity': activity,
                    'completed_activities': idx,
                    'logs': session['dataset_progress']['logs'] + [f"Starting generation for: {activity}"]
                })
                session.save()
                
                # Generate image for activity
                prompt = f"Highly detailed 3D Disney Pixar-style animation of a {describe_user}, {activity}. Disney, Pixar art style, CGI, high details, 3d animation."
                generation_id = generate_with_image_id(seed_image_id, prompt, 1)
                
                if generation_id:
                    print(f"Generation started for {activity} with ID: {generation_id}")  # Debug log
                    session['dataset_progress']['logs'].append(f"Generation started for {activity} (ID: {generation_id})")
                    session.save()
                    
                    # Wait for generation
                    while True:
                        status = check_generation_status(generation_id)
                        print(f"Status for {activity}: {status}")  # Debug log
                        if status == 'COMPLETE':
                            break
                        time.sleep(2)
                    
                    # Upload to dataset
                    image_ids = get_generated_image_ids(generation_id)
                    for image_id in image_ids:
                        upload_success = upload_image_to_dataset(dataset_id, image_id)
                        print(f"Upload status for {image_id}: {upload_success}")  # Debug log
                    
                    session['dataset_progress'].update({
                        'completed_activities': idx + 1,
                        'logs': session['dataset_progress']['logs'] + [f"Completed: {activity}"]
                    })
                    session.save()
                else:
                    print(f"Failed to generate image for {activity}")  # Debug log
                    session['dataset_progress']['logs'].append(f"Failed to generate image for {activity}")
                    session.save()
                
            except Exception as e:
                print(f"Error processing activity {activity}: {str(e)}")  # Debug log
                session['dataset_progress']['logs'].append(f"Error: {str(e)}")
                session.save()
        
        session['dataset_progress']['status'] = 'complete'
        session['dataset_progress']['logs'].append("Dataset creation completed")
        session.save()
        print("Dataset creation completed successfully")  # Debug log
        
    except Exception as e:
        print(f"Critical error in background task: {str(e)}")  # Debug log
        session['dataset_progress']['status'] = 'failed'
        session['dataset_progress']['logs'].append(f"Critical error: {str(e)}")
        session.save()


def dataset_progress(request, dataset_id=None):
    """API endpoint to check dataset creation progress"""
    progress = request.session.get('dataset_progress', {})
    
    if not progress:
        return JsonResponse({
            'error': 'No dataset creation in progress'
        })
    
    return JsonResponse({
        'current_activity': progress.get('current_activity', ''),
        'completed_activities': progress.get('completed_activities', 0),
        'total_activities': progress.get('total_activities', 9),
        'logs': progress.get('logs', []),
        'status': progress.get('status', 'unknown'),
        'dataset_id': progress.get('dataset_id')
    })


def dataset_complete(request, dataset_id):
    """Show completed dataset images."""
    images = display_all_images_in_dataset(dataset_id)
    return render(request, 'image_generator/dataset_complete.html', {
        'dataset_id': dataset_id,
        'images': images
    })
>>>>>>> Stashed changes
