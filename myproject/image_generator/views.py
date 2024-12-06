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
    display_all_images_in_dataset,
    train_custom_model,
    get_model_status,
    generate_with_custom_model
)
import requests
import os
import logging
import json
from django.http import JsonResponse
import threading
import time
from django.contrib import messages
from .forms import AvatarGenerationForm

logger = logging.getLogger(__name__)

###################################################

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

############# upload and parse diary ######################

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

########## allow user to create and select avatar ##############

def generate_avatars(request):
    """Generate multiple avatar images based on user description."""
    if request.method == 'POST':
        form = AvatarGenerationForm(request.POST)
        if form.is_valid():
            describe_user = form.cleaned_data['describe_user']
            num_images = form.cleaned_data['num_images']
            
            # Store the description in session
            request.session['describe_user'] = describe_user
            
            # Preset prompt template
            prompt_template = "Highly detailed 3D Disney Pixar-style animation of a %s. Disney, Pixar art style, CGI, clean background, high details, 3d animation."
            prompt = prompt_template % describe_user
            
            # logger.info(f"Generating avatars with description: {describe_user}")
            logger.info(f"Full prompt: {prompt}")
            
            try:
                generation_id = generate(prompt, num_images)
                if generation_id:
                    return redirect('image_generator:display_generated_images', generation_id=generation_id)
                else:
                    messages.error(request, "Failed to generate avatars. Please try again.")
            except Exception as e:
                logger.error(f"Error generating avatars: {str(e)}")
                messages.error(request, "An error occurred while generating avatars.")
    else:
        form = AvatarGenerationForm()
    
    return render(request, 'image_generator/generate_avatars.html', {'form': form})


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


########## use selected avatar to train a model ##############

def create_user_dataset_view(request, selected_image_id):
    if request.method == 'POST':
        # Retrieve the user description from the session
        describe_user = request.session.get('describe_user', "8-year-old Asian girl with black hair, pigtail hairstyle, very pretty, cute")
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


def generate_images(request, diary_id):
    """Generate images based on the diary text"""
    if request.method == 'POST':
        # Your image generation logic here
        # This should use your Leonardo AI functions
        pass
    return HttpResponseRedirect(reverse('image_generator:dataset_complete', args=[dataset_id]))




def train_model_view(request, dataset_id):
    """View to handle model training."""
    try:
        # Get describe_user from session or use default
        describe_user = request.session.get('describe_user', 'anonymous')
        
        logger.info(f"Starting model training for dataset: {dataset_id}")
        training_info = train_custom_model(dataset_id, describe_user)
        
        if training_info:
            logger.info(f"Model training started. Info: {training_info}")
            return JsonResponse({
                'status': 'success',
                'model_id': training_info['model_id']
            })
        else:
            logger.error("Failed to start model training")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to start model training'
            })
            
    except Exception as e:
        logger.error(f"Error in train_model_view: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })



def view_trained_model(request, model_id):
    """View to display trained model details."""
    try:
        logger.info(f"Fetching details for model: {model_id}")
        url = f"https://cloud.leonardo.ai/api/rest/v1/models/{model_id}"
        
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {os.getenv('LEONARDO_API_KEY')}"
        }
        
        response = requests.get(url, headers=headers)
        logger.info(f"Model API response: {response.text}")
        
        if response.status_code == 200:
            model_data = response.json().get('custom_models_by_pk', {})
            
            context = {
                'model': {
                    'id': model_id,
                    'name': model_data.get('name'),
                    'status': model_data.get('status'),
                    'created_at': model_data.get('createdAt'),
                    'preview_image_url': model_data.get('previewImageUrl'),
                    'description': model_data.get('description'),
                    'instance_prompt': model_data.get('instancePrompt')
                }
            }
            
            return render(request, 'image_generator/trained_model.html', context)
        else:
            messages.error(request, "Failed to retrieve model details")
            logger.error(f"Failed to retrieve model. Status: {response.status_code}")
            return redirect('image_generator:home')
            
    except Exception as e:
        logger.error(f"Error retrieving model details: {str(e)}")
        messages.error(request, f"Error: {str(e)}")
        return redirect('image_generator:home')





def check_model_status_view(request, model_id):
    """View to check model training status."""
    try:
        logger.info(f"Checking status for model ID: {model_id}")
        status = get_model_status(model_id)
        logger.info(f"Retrieved status: {status}")
        
        return JsonResponse({
            'status': 'success',
            'training_status': status,
            'model_id': model_id
        })
            
    except Exception as e:
        logger.error(f"Error checking model status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


########## utils ##############


def create_dataset_background(session_key, dataset_name, seed_image_id, describe_user):
    """Background task to create dataset and update progress"""
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore(session_key=session_key)
    
    logger.info(f"Starting dataset creation with description: {describe_user}")
    
    try:
        dataset_id = create_dataset(dataset_name)
        logger.info(f"Dataset created with ID: {dataset_id}")
        
        if not dataset_id:
            logger.error("Failed to create dataset")
            session['dataset_progress'].update({
                'status': 'failed',
                'logs': ['Failed to create dataset']
            })
            session.save()
            return
            
        # Initialize or update the progress dictionary
        progress_data = session.get('dataset_progress', {})
        progress_data.update({
            'dataset_id': dataset_id,
            'status': 'in_progress',
            'current_activity': '',
            'completed_activities': 0,
            'total_activities': 9,
            'logs': [f"Dataset created with ID: {dataset_id}"]
        })
        session['dataset_progress'] = progress_data
        session.save()
        
        activities = [
            "playing basketball", "riding a bicycle", "reading a book",
            "playing the piano", "cooking in the kitchen", "flying a kite",
            "playing tennis", "swimming in a pool", "watering flowers"
        ]
        
        for idx, activity in enumerate(activities):
            try:
                prompt = f"Highly detailed 3D Disney Pixar-style animation of a {describe_user}, {activity}. Disney, Pixar art style, CGI, high details, 3d animation."
                logger.info(f"Activity {idx + 1}/{len(activities)}: {activity}")
                logger.info(f"Full prompt: {prompt}")
                
                progress_data = session.get('dataset_progress', {})
                progress_data.update({
                    'current_activity': activity,
                    'completed_activities': idx,
                    'logs': progress_data.get('logs', []) + [
                        f"Starting generation for: {activity}",
                        f"Using prompt: {prompt}"
                    ]
                })
                session['dataset_progress'] = progress_data
                session.save()
                
                # Generate image for activity
                generation_id = generate_with_image_id(seed_image_id, prompt, 1)
                
                if generation_id:
                    logger.info(f"Generation started for {activity} with ID: {generation_id}")
                    session['dataset_progress']['logs'].append(f"Generation started for {activity} (ID: {generation_id})")
                    session.save()
                    
                    # Wait for generation
                    while True:
                        status = check_generation_status(generation_id)
                        if status == 'COMPLETE':
                            break
                        time.sleep(2)
                    
                    # Upload to dataset
                    image_ids = get_generated_image_ids(generation_id)
                    for image_id in image_ids:
                        upload_success = upload_image_to_dataset(dataset_id, image_id)
                    
                    session['dataset_progress'].update({
                        'completed_activities': idx + 1,
                        'logs': session['dataset_progress']['logs'] + [f"Completed: {activity}"]
                    })
                    session.save()
                else:
                    logger.info(f"Failed to generate image for {activity}")
                    session['dataset_progress']['logs'].append(f"Failed to generate image for {activity}")
                    session.save()
                
            except Exception as e:
                logger.error(f"Error processing activity {activity}: {str(e)}")
                progress_data = session.get('dataset_progress', {})
                progress_data.update({
                    'status': 'error',
                    'logs': progress_data.get('logs', []) + [f"Error: {str(e)}"]
                })
                session['dataset_progress'] = progress_data
                session.save()
                
        session['dataset_progress']['status'] = 'complete'
        session['dataset_progress']['logs'].append("Dataset creation completed")
        session.save()
        logger.info("Dataset creation completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error in background task: {str(e)}")
        progress_data = session.get('dataset_progress', {})
        progress_data.update({
            'status': 'failed',
            'logs': progress_data.get('logs', []) + [f"Critical error: {str(e)}"]
        })
        session['dataset_progress'] = progress_data
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
    logger.info(f"Retrieved {len(images)} images for dataset {dataset_id}")
    logger.info(f"Image data: {images}")  # Add this for debugging
    
    return render(request, 'image_generator/dataset_complete.html', {
        'dataset_id': dataset_id,
        'images': images
    })


def generate_with_model(request, model_id):
    """Generate images using a trained model."""
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        if prompt:
            try:
                generation_id = generate_with_custom_model(model_id, prompt)
                if generation_id:
                    messages.success(request, "Image generation started successfully!")
                    return redirect('image_generator:display_generated_images', generation_id=generation_id)
                else:
                    messages.error(request, "Failed to generate image")
            except Exception as e:
                logger.error(f"Error generating image: {str(e)}")
                messages.error(request, f"Error generating image: {str(e)}")
        else:
            messages.error(request, "Prompt is required")
    
    return redirect('image_generator:view_trained_model', model_id=model_id)






