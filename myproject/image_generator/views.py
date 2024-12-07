from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from .models import UserDiary, GeneratedImage
from .cloudvision import parse_diary
from .image_generation import (
    generate, 
    display_images, 
    format_json_response,
    get_number_of_images_in_dataset,
    create_dataset,
    generate_with_image_id,
    check_generation_status,
    get_generated_image_ids,
    upload_image_to_dataset,
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
from .prompt_generation import process_diary_text
from .models import UserCustomModel


logger = logging.getLogger(__name__)

###################################################

def home(request):
    """Render the home page with model status."""
    username = request.session.get('username')
    
    if not username:
        return redirect('image_generator:initial')
        
    try:
        user_model = UserCustomModel.objects.get(username=username)
        model_status = user_model.model_status
        model_id = user_model.model_id
        request.session['trained_model_id'] = model_id
    except UserCustomModel.DoesNotExist:
        model_status = None
        model_id = None
    
    return render(request, 'image_generator/home.html', {
        'model_status': model_status,
        'model_id': model_id,
        'username': username
    })

def initial_user_flow(request):
    """Handle user login/registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        if not username:
            messages.error(request, "Please enter a username")
            return redirect('image_generator:initial')
            
        try:
            # 检查用户是否存在
            user_model = UserCustomModel.objects.get(username=username)
            # 存在则保存到session并重定向到主页
            request.session['username'] = username
            request.session['trained_model_id'] = user_model.model_id
            messages.success(request, f"Welcome back, {username}!")
            return redirect('image_generator:home')
            
        except UserCustomModel.DoesNotExist:
            # 新用户，保存用户名并重定向到角色创建
            request.session['username'] = username
            messages.info(request, "Let's create your character first!")
            return redirect('image_generator:generate_avatars')
    
    return render(request, 'image_generator/initial.html')

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


###################################################



def avatar_generation_flow(request):
    """Handle avatar generation for new users"""
    if request.method == 'POST':
        describe_user = request.POST.get('describe_user')
        if not describe_user:
            messages.error(request, "Please describe your character")
            return redirect('image_generator:generate_avatars')
            
        request.session['describe_user'] = describe_user
        prompt = f"Highly detailed 3D Disney Pixar-style animation of a {describe_user}. Disney, Pixar art style, CGI, clean background, high details, 3d animation."
        
        generation_id = generate(prompt, 4)
        if generation_id:
            return redirect('image_generator:display_generated_images', generation_id=generation_id)
        else:
            messages.error(request, "Failed to generate avatars")
            return redirect('image_generator:generate_avatars')
    
    return render(request, 'image_generator/avatar_form.html')


def create_dataset_flow(request):
    """Handle dataset creation and model training"""
    if request.method == 'POST':
        selected_image_id = request.POST.get('selected_image_id')
        username = request.session.get('username')
        describe_user = request.session.get('describe_user')
        
        if not all([selected_image_id, username, describe_user]):
            messages.error(request, "Missing required information")
            return redirect('image_generator:generate_avatars')
        
        try:
            # 创建数据集并生成训练图片
            dataset_id = create_dataset(f"dataset_{username}")
            
            # 预定义的场景列表
            activities = [
                "playing basketball",
                "reading a book",
                "walking in a park",
                "cooking in kitchen",
                "painting on canvas"
            ]
            
            for activity in activities:
                generation_id = generate_with_image_id(
                    selected_image_id,
                    f"{describe_user} {activity}",
                    1
                )
                if generation_id:
                    images = display_images(generation_id)
                    for image in images:
                        upload_image_to_dataset(dataset_id, image['id'])
            
            # 开始训练模型
            training_info = train_custom_model(dataset_id, describe_user)
            if training_info:
                UserCustomModel.objects.create(
                    username=username,
                    model_id=training_info['model_id'],
                    model_status='TRAINING'
                )
                messages.success(request, "Model training started! Please check back later.")
                return redirect('image_generator:initial')
                
        except Exception as e:
            logger.error(f"Error in dataset creation: {str(e)}")
            messages.error(request, "Failed to create dataset and train model")
    
    return redirect('image_generator:generate_avatars')


def diary_processing_flow(request):
    """Handle diary upload and processing for users with trained models"""
    # 从 session 获取 model_id
    model_id = request.session.get('model_id')
    
    if not model_id:
        messages.error(request, 'No trained model found. Please train your model first.')
        return redirect('image_generator:home')
    
    if request.method == 'POST' and request.FILES.get('diary_image'):
        try:
            diary_image = request.FILES['diary_image']
            temp_path = 'media/temp_diary_image.jpg'
            
            # 保存上传的图片
            with open(temp_path, 'wb+') as destination:
                for chunk in diary_image.chunks():
                    destination.write(chunk)
            
            try:
                # 提取文字
                extracted_text = parse_diary(temp_path)
                
                # 生成场景描述
                scene_list = process_diary_text(extracted_text)
                request.session['scene_list'] = scene_list
                
                # 使用训练好的模型生成图片
                generated_images = []
                
                for scene in scene_list:
                    generation_id = generate_with_custom_model(model_id, scene)
                    if generation_id:
                        images = display_images(generation_id)
                        generated_images.extend(images)
                
                return render(request, 'image_generator/upload_diary.html', {
                    'diary_text': extracted_text,
                    'scenes': scene_list,
                    'images': generated_images,
                    'model_id': model_id  # 添加 model_id 到上下文
                })
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error processing diary: {str(e)}")
            messages.error(request, str(e))
    
    # GET 请求或出错时的默认渲染
    return render(request, 'image_generator/upload_diary.html', {
        'model_id': model_id  # 确保传入 model_id
    })


############# upload and parse diary ######################

def upload_diary(request):
    """处理日记上传、文字提取、场景生成和图片生成的统一视图"""
    try:
        if request.method == 'POST':
            if 'diary_images' in request.FILES:
                image = request.FILES['diary_images']
                
                # 保存上传的图片到临时文件
                temp_path = f'temp_{image.name}'
                with open(temp_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)
                        
                try:
                    # 1. 提取文字
                    diary_text = parse_diary(temp_path)
                    
                    # 2. 生成场景描述
                    scenes = process_diary_text(diary_text)
                    
                    # 3. 使用训练好的模型为每个场景生成图片
                    model_id = request.session.get('model_id')
                    generated_images = []
                    
                    for scene in scenes:
                        image_result = generate_with_custom_model(
                            model_id=model_id,
                            prompt=scene
                        )
                        if image_result:
                            generated_images.append({
                                'scene': scene,
                                'url': image_result['url']
                            })
                    
                    context = {
                        'diary_text': diary_text,
                        'scenes': scenes,
                        'generated_images': generated_images
                    }
                    
                    return render(request, 'image_generator/upload_diary.html', context)
                    
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
            else:
                messages.error(request, 'Please upload a diary image')
                
    except Exception as e:
        logger.error(f"Error processing diary: {str(e)}")
        messages.error(request, f'An error occurred: {str(e)}')
        
    return render(request, 'image_generator/upload_diary.html')

def process_diary_view(request):
    if request.method == 'POST':
        diary_text = request.POST.get('diary_text')
        try:
            # Process diary text using Gemini
            scene_list = process_diary_text(diary_text)
            logger.info(f"Generated {len(scene_list)} scenes from diary text")
            
            # Store scene list in session
            request.session['scene_list'] = scene_list
            
            # Get the model_id from the session
            model_id = request.session.get('trained_model_id')
            
            if model_id:
                # Generate images for each scene
                generated_images = []
                for scene in scene_list:
                    generation_id = generate_with_custom_model(model_id, scene)
                    if generation_id:
                        images = display_images(generation_id)
                        generated_images.extend(images)
                
                # Store generated images in session
                request.session['generated_images'] = generated_images
                
                # Redirect to view generated scenes
                return redirect('image_generator:view_generated_scenes')
            else:
                logger.error("No trained model found in session")
                messages.error(request, "No trained model found. Please train a model first.")
                return redirect('image_generator:home')
                
        except Exception as e:
            logger.error(f"Error processing diary text: {str(e)}")
            messages.error(request, f"Error processing diary: {str(e)}")
            return redirect('image_generator:upload_diary')
    
    return redirect('image_generator:home')


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


########## use selected avatar to create a dataset ##############

def create_user_dataset_view(request, selected_image_id):
    """初始化数据集创建过程"""
    if request.method == 'POST':
        # 获取用户描述
        describe_user = request.session.get('describe_user', '')
        dataset_name = f"user_dataset_{selected_image_id[:8]}"
        
        # 初始化进度信息
        request.session['dataset_progress'] = {
            'current_activity': '',
            'completed_activities': 0,
            'total_activities': 9,
            'logs': [],
            'status': 'starting',
            'dataset_id': None
        }
        request.session.modified = True
        
        # 在后台线程中开始数据集创建
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
    """后台任务：创建数据集并生成训练图片"""
    from django.contrib.sessions.backends.db import SessionStore
    session = SessionStore(session_key=session_key)
    
    logger.info(f"Starting dataset creation with description: {describe_user}")
    
    try:
        # 创建数据集
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
        
        # 更新进度信息
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
        
        # 预定义活动列表
        activities = [
            "playing basketball", "riding a bicycle", "reading a book",
            "playing the piano", "cooking in the kitchen", "flying a kite",
            "playing tennis", "swimming in a pool", "watering flowers"
        ]
        
        # 为每个活动生成图片
        for idx, activity in enumerate(activities):
            try:
                prompt = f"Highly detailed 3D Disney Pixar-style animation of a {describe_user}, {activity}. Disney, Pixar art style, CGI, high details, 3d animation."
                logger.info(f"Activity {idx + 1}/{len(activities)}: {activity}")
                
                # 更新当前活动状态
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
                
                # 生成图片
                generation_id = generate_with_image_id(seed_image_id, prompt, 1)
                if generation_id:
                    logger.info(f"Generation started for {activity} with ID: {generation_id}")
                    session['dataset_progress']['logs'].append(f"Generation started for {activity} (ID: {generation_id})")
                    session.save()
                    
                    # 等待生成完成
                    while True:
                        status = check_generation_status(generation_id)
                        if status == 'COMPLETE':
                            break
                        time.sleep(2)
                    
                    # 上传到数据集
                    image_ids = get_generated_image_ids(generation_id)
                    for image_id in image_ids:
                        upload_image_to_dataset(dataset_id, image_id)
                    
                    # 更新完成状态
                    session['dataset_progress'].update({
                        'completed_activities': idx + 1,
                        'logs': session['dataset_progress']['logs'] + [f"Completed: {activity}"]
                    })
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
        
        # 数据集创建完成，开始训练模型
        session['dataset_progress'].update({
            'status': 'complete',
            'logs': session['dataset_progress'].get('logs', []) + ["Dataset creation completed"]
        })
        session.save()
        
        # 开始训练模型
        training_info = train_custom_model(dataset_id, describe_user)
        if training_info:
            UserCustomModel.objects.create(
                username=session.get('username', 'anonymous'),
                model_id=training_info['model_id'],
                model_status='TRAINING'
            )
            session['dataset_progress']['logs'].append(f"Model training started with ID: {training_info['model_id']}")
            session.save()
            
    except Exception as e:
        logger.error(f"Critical error in background task: {str(e)}")
        progress_data = session.get('dataset_progress', {})
        progress_data.update({
            'status': 'failed',
            'logs': progress_data.get('logs', []) + [f"Critical error: {str(e)}"]
        })
        session['dataset_progress'] = progress_data
        session.save()
        


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


########## model training ##############


def train_model_view(request, dataset_id):
    """开始模型训练"""
    try:
        username = request.session.get('username')
        describe_user = request.session.get('describe_user')
        
        if not all([username, describe_user]):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required session data'
            })
        
        # 开始训练模型
        training_info = train_custom_model(dataset_id, describe_user)
        if training_info:
            model_id = training_info['model_id']
            
            # 使用 update_or_create 而不是 create
            UserCustomModel.objects.update_or_create(
                username=username,  # 查找条件
                defaults={         # 要更新的字段
                    'model_id': model_id,
                    'model_status': 'TRAINING'
                }
            )
            
            logger.info(f"Model training started for user {username}")
            
            # 立即检查初始状态
            try:
                initial_status = get_model_status(model_id)
                logger.info(f"Initial training status for model {model_id}: {initial_status}")
            except Exception as status_error:
                logger.warning(f"Failed to get initial status: {str(status_error)}")
            
            # 启动后台任务来定期检查状态
            def check_status_periodically():
                max_checks = 60  # 最多检查60次
                check_interval = 30  # 每30秒检查一次
                
                for i in range(max_checks):
                    try:
                        status = get_model_status(model_id)
                        logger.info(f"Training status check {i+1}/{max_checks} for model {model_id}: {status}")
                        
                        # 更新数据库中的状态
                        UserCustomModel.objects.filter(model_id=model_id).update(
                            model_status=status
                        )
                        
                        # 如果训练完成或失败，停止检查
                        if status in ['COMPLETE', 'FAILED']:
                            logger.info(f"Model training {status.lower()} for {model_id}")
                            break
                            
                        time.sleep(check_interval)
                    except Exception as e:
                        logger.error(f"Error checking model status: {str(e)}")
                        time.sleep(check_interval)
                        
            # 在后台线程中运行状态检查
            import threading
            status_thread = threading.Thread(target=check_status_periodically)
            status_thread.daemon = True
            status_thread.start()
            
            return JsonResponse({
                'status': 'success',
                'model_id': model_id
            })
        else:
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
    try:
        # Get scenes from session
        scene_list = request.session.get('scene_list', [])
        
        return render(request, 'image_generator/view_trained_model.html', {
            'model_id': model_id,
            'scenes': scene_list
        })
        
    except Exception as e:
        logger.error(f"Error in view_trained_model: {str(e)}")
        messages.error(request, "Error viewing trained model")
        return redirect('image_generator:home')


def check_model_status_view(request, model_id):
    """View to check model training status."""
    try:
        logger.info(f"Checking status for model ID: {model_id}")
        status = get_model_status(model_id)
        logger.info(f"Retrieved status: {status}")
        
        if status:
            return JsonResponse({
                'status': 'success',
                'training_status': status,
                'model_id': model_id  # Include model_id in response
            })
        else:
            logger.error("No status returned from get_model_status")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to get model status'
            })
            
    except Exception as e:
        logger.error(f"Error checking model status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


########## utils ##############



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
        try:
            data = json.loads(request.body)
            scenes = data.get('scenes', [])
            
            if not scenes:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No scenes provided'
                })
            
            # 生成所有场景的图片
            generation_results = []
            for scene in scenes:
                generation_id = generate_with_custom_model(model_id, scene)
                if generation_id:
                    generation_results.append({
                        'scene': scene,
                        'generation_id': generation_id
                    })
            
            if generation_results:
                return JsonResponse({
                    'status': 'success',
                    'generation_id': generation_results[0]['generation_id']  # 返回第一个生成ID
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to generate images'
                })
                
        except Exception as e:
            logger.error(f"Error generating images: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })


def view_generated_scenes(request):
    """Display generated scenes from diary text"""
    scene_list = request.session.get('scene_list', [])
    generated_images = request.session.get('generated_images', [])
    
    if not scene_list or not generated_images:
        messages.warning(request, "No generated scenes found. Please process your diary first.")
        return redirect('image_generator:upload_diary')
    
    return render(request, 'image_generator/view_generated_scenes.html', {
        'scenes': scene_list,
        'images': generated_images
    })


def trained_model_view(request, model_id):
    """处理模型训练完成后的视图"""
    try:
        # 获取用户信息
        username = request.session.get('username')
        if not username:
            return redirect('image_generator:login')
            
        # 获取model信息
        user_model = UserCustomModel.objects.get(
            username=username,
            model_id=model_id
        )
        
        if user_model.model_status != 'COMPLETE':
            messages.warning(request, '模型尚未训练完成')
            return redirect('image_generator:model_training_progress')
            
        # 更新 session
        request.session['model_id'] = model_id
        
        # 跳转到上传日记页面
        return redirect('image_generator:upload_diary')
        
    except UserCustomModel.DoesNotExist:
        messages.error(request, '找不到对应的模型')
        return redirect('image_generator:home')
    except Exception as e:
        logger.error(f"Error in trained_model_view: {str(e)}")
        messages.error(request, '发生错误')
        return redirect('image_generator:home')

def extract_text_view(request):
    """Extract text from uploaded diary image"""
    try:
        if 'diary_image' not in request.FILES:
            return JsonResponse({'error': 'No image uploaded'}, status=400)
            
        image = request.FILES['diary_image']
        
        # Save the uploaded image temporarily
        temp_path = f'temp_{image.name}'
        with open(temp_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
                
        try:
            # Extract text using Cloud Vision API
            extracted_text = parse_diary(temp_path)
            logger.info(f"Successfully extracted text from image")
            
            return JsonResponse({
                'status': 'success',
                'text': extracted_text
            })
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def generate_scenes_view(request):
    """Generate scenes from diary text"""
    try:
        data = json.loads(request.body)
        diary_text = data.get('diary_text')
        
        if not diary_text:
            return JsonResponse({'error': 'No diary text provided'}, status=400)
            
        # Generate scenes using Gemini API
        scenes = process_diary_text(diary_text)
        logger.info(f"Generated {len(scenes)} scenes from diary text")
        
        # Store scenes in session for later use
        request.session['scene_list'] = scenes
        
        return JsonResponse({
            'status': 'success',
            'scenes': scenes
        })
        
    except Exception as e:
        logger.error(f"Error generating scenes: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def logout_view(request):
    """Handle user logout"""
    if request.method == 'POST':
        # 清除所有 session 数据
        request.session.flush()
        messages.success(request, "You have been logged out successfully!")
    return redirect('image_generator:initial')




