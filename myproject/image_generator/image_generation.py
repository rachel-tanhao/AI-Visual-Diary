import requests
import json
import time
import os
import logging
from django.conf import settings


leonardo_api_key = os.getenv("LEONARDO_API_KEY")
authorization = "Bearer %s" % leonardo_api_key

logger = logging.getLogger(__name__)


############### generate the initial avatar #################

def generate(prompt, num_images):
    """生成初始用户头像
    在 generate_avatars() view 中被调用
    返回 generation_id
    """
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "alchemy": True,
        "height": 768,
        "modelId": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
        "num_images": num_images,
        "presetStyle": "DYNAMIC",
        "prompt": prompt,
        "width": 1024
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response_dict = json.loads(response.text)
    generation_id = response_dict.get("sdGenerationJob", {}).get("generationId")
    return generation_id


def display_images(generation_id):
    """获取生成的图片信息
    在 display_generated_images() view 中被调用
    返回包含图片URL的列表
    """
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    # Poll for image generation completion (with timeout)
    max_attempts = 12  # 1 minute maximum wait
    for _ in range(max_attempts):
        response = requests.get(url, headers=headers)
        response_dict = json.loads(response.text)
        
        status = response_dict.get('generations_by_pk', {}).get('status', '')
        if status == "COMPLETE":
            # Get generated images
            generated_images = response_dict.get('generations_by_pk', {}).get('generated_images', [])
            # Return list of image data with URLs and IDs
            return [
                {
                    'url': image_data['url'],
                    'id': image_data['id']
                }
                for image_data in generated_images
            ]
        elif status == "FAILED":
            return []
            
        time.sleep(5)  # Wait before checking again
    
    return []  # Return empty list if timeout




################ dataset related functions ##################


def create_dataset(name):
    """创建空数据集
    在 create_dataset_background() 中被调用
    返回 dataset_id
    """
    url = "https://cloud.leonardo.ai/api/rest/v1/datasets"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    
    payload = {
        "name": name
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Dataset creation response: {response.json()}")  # Debug log
    
    if response.status_code == 200 and 'insert_datasets_one' in response.json():
        dataset_id = response.json()['insert_datasets_one']['id']
        return dataset_id
    return None


def generate_with_image_id(seed_image_id, prompt, num_images):
    """基于选定的头像生成其他场景图片"""
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }

    url = "https://cloud.leonardo.ai/api/rest/v1/generations"

    payload = {
        "alchemy": True,
        "height": 768,
        "modelId": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
        "num_images": num_images,
        "presetStyle": "DYNAMIC",
        "prompt": prompt,
        "width": 1024,
        "controlnets": [
            {
                "initImageId": seed_image_id,
                "initImageType": "GENERATED",
                "preprocessorId": 67, #Style Reference Id
                "strengthType": "Low",
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # 检查 HTTP 错误
        
        response_data = response.json()
        logger.info(f"Generation response: {response_data}")  # 添加日志
        
        if 'sdGenerationJob' not in response_data:
            logger.error(f"Unexpected API response format: {response_data}")
            return None
            
        generation_id = response_data['sdGenerationJob'].get('generationId')
        if not generation_id:
            logger.error("No generationId in response")
            return None
            
        return generation_id
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in generate_with_image_id: {str(e)}")
        return None


def check_generation_status(generation_id):
    """检查图片生成状态
    在 create_dataset_background() 中被调用
    返回状态（'COMPLETE'/'FAILED'等）
    """
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response_dict = response.json()
        status = response_dict.get('generations_by_pk', {}).get('status', '')
        print(f"Current status for generation {generation_id}: {status}")
        return status
    return None


def get_generated_image_ids(generation_id):
    """获取生成图片的ID列表
    在 create_dataset_background() 中被调用
    返回 image_ids 列表
    """
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    # Fetch the generated images
    response = requests.get(url, headers=headers)
    response_dict = response.json()
    # Get the generated image IDs
    generated_images = response_dict.get('generations_by_pk', {}).get('generated_images', [])
    image_ids = []
    for image_data in generated_images:
        image_id = image_data['id']
        image_ids.append(image_id)
    return image_ids



def upload_image_to_dataset(dataset_id, image_id):
    """将生成的图片上传到数据集
    在 create_dataset_background() 中被调用
    返回上传是否成功
    """
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}/upload/gen"
    
    payload = {
        "generatedImageId": image_id
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Upload response for image {image_id}: {response.text}")
        
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to upload image. Status code: {response.status_code}")
            print(f"Error message: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return False


def display_all_images_in_dataset(dataset_id):
    """获取数据集中所有图片的URL"""
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}"
    
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            dataset = response.json().get('datasets_by_pk', {})
            images = dataset.get('dataset_images', [])
            
            # 提取每个图片的URL
            image_urls = []
            for image in images:
                image_url = image.get('url')
                if image_url:
                    image_urls.append({
                        'url': image_url,
                        'id': image.get('id')
                    })
            
            logger.info(f"Found {len(image_urls)} images in dataset {dataset_id}")
            return image_urls
            
    except Exception as e:
        logger.error(f"Error getting dataset images: {str(e)}")
        return []



################ model related functions ##################


def train_custom_model(dataset_id, describe_user, max_retries=3):
    """训练用户专属模型"""
    # 首先检查数据集状态
    dataset_status = check_dataset_status(dataset_id)
    if not dataset_status:
        logger.error("Failed to check dataset status")
        return None
        
    if dataset_status['status'] != 'ready':
        logger.error(f"Dataset not ready. Status: {dataset_status}")
        return None
        
    if dataset_status['image_count'] < 5:  # 假设需要至少5张图片
        logger.error(f"Not enough images in dataset. Found: {dataset_status['image_count']}")
        return None
    
    logger.info(f"Dataset check passed: {dataset_status}")

    url = "https://cloud.leonardo.ai/api/rest/v1/models"
    
    # 简化模型名称，避免特殊字符
    model_name = f"custom_model_{int(time.time())}"
    
    payload = {
        "name": model_name,
        "description": describe_user,
        "datasetId": dataset_id,
        "modelType": "GENERAL",
        "instance_prompt": "VEF7 character", 
        "nsfw": False,
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    
    logger.info(f"Starting model training with payload: {json.dumps(payload, indent=2)}")
    
    for attempt in range(max_retries):
        try:
            # 添加更长的延迟
            if attempt > 0:
                time.sleep(15 * (attempt + 1))
            
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"Attempt {attempt + 1}: Training response status code: {response.status_code}")
            logger.info(f"Training response body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                training_job = response_data.get('sdTrainingJob', {})
                model_id = training_job.get('customModelId')
                training_id = training_job.get('id')
                
                if model_id:
                    logger.info(f"Successfully extracted model ID: {model_id}")
                    return {
                        'model_id': model_id,
                        'training_id': training_id
                    }
            elif response.status_code == 500:
                error_msg = response.json().get('error', 'Unknown error')
                logger.warning(f"Server error on attempt {attempt + 1}: {error_msg}")
                
                # 如果是配额或限制相关的错误，立即返回
                if 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                    logger.error("API quota or limit reached")
                    return None
                    
                continue
                
        except Exception as e:
            logger.error(f"Exception during model training attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                logger.exception("Final attempt failed. Full traceback:")
                return None
            
    logger.error("All attempts to train model failed")
    return None


def get_model_status(model_id):
    """检查模型训练状态
    用于检查模型是否训练完成
    返回模型状态
    """
    url = f"https://cloud.leonardo.ai/api/rest/v1/models/{model_id}"
    
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            model_info = response.json().get("custom_models_by_pk", {})
            status = model_info.get("status")
            logger.info(f"Model {model_id} status: {status}")
            return status
        return None
    except Exception as e:
        logger.error(f"Error checking model status: {str(e)}")
        return None


def generate_with_custom_model(model_id, prompt, num_images=1):
    """使用训练好的模型生成图片
    在处理日记场景时使用
    返回 generation_id
    """
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    
    payload = {
        "prompt": prompt,
        "modelId": model_id,
        "num_images": num_images,
        "width": 768,
        "height": 768,
        "presetStyle": "DYNAMIC",
        "public": False
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    
    try:
        logger.info(f"Generating image with prompt: {prompt}")  # 添加日志
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            generation_id = response.json().get('sdGenerationJob', {}).get('generationId')
            logger.info(f"Successfully generated image with ID: {generation_id}")
            return generation_id
        logger.error(f"Failed to generate image. Status code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error generating with custom model: {str(e)}")
        return None


################ utils ##################

def get_number_of_images_in_dataset(dataset_id):

    # Define the URL, dynamically inserting the dataset_id
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}"

    # Define the headers, make sure to include authorization if required
    headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": authorization
    }

    # Make the GET request to retrieve the dataset
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        response_data = response.json()
        dataset = response_data.get('datasets_by_pk')

        if dataset and dataset.get('dataset_images'):
            # Count the number of images in the 'dataset_images' array
            number_of_images = len(dataset['dataset_images'])
            print(f"Number of images in the dataset: {number_of_images}")
            return number_of_images
        else:
            print("No images found in the dataset.")
            return 0
    else:
        print(f"Failed to retrieve dataset. Status code: {response.status_code}")
        return 0


def format_json_response(response):
    """Convert JSON response to a formatted string."""
    response_dict = json.loads(response.text)
    formatted_response = json.dumps(response_dict, indent=4)
    return formatted_response


def wait_for_image_generation(generation_id):
    """Wait for image generation to complete"""
    while True:
        status = check_generation_status(generation_id)
        if status == "COMPLETE":
            return True
        elif status == "FAILED":
            print(f"Image generation failed for ID: {generation_id}")
            return False
        time.sleep(5)  # Wait before checking again


def check_dataset_status(dataset_id):
    """检查数据集状态"""
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}"
    
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        logger.info(f"Dataset status response: {json.dumps(response_data)}")
        
        if response.status_code == 200 and 'datasets_by_pk' in response_data:
            dataset = response_data['datasets_by_pk']
            image_count = len(dataset.get('dataset_images', []))
            logger.info(f"Dataset {dataset_id} contains {image_count} images")
            return {
                'status': 'ready',
                'image_count': image_count
            }
    except Exception as e:
        logger.error(f"Error checking dataset status: {str(e)}")
    return None
