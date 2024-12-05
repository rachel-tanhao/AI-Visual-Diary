import requests
import json
import time
import os
import logging
from django.conf import settings


leonardo_api_key = os.getenv("LEONARDO_API_KEY")
authorization = "Bearer %s" % leonardo_api_key

logger = logging.getLogger(__name__)


def generate(prompt, num_images):
    """Generate images based on a prompt using the Leonardo AI API."""
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


def get_generated_image_ids(generation_id):
    """ Function to retrieve generated image IDs without displaying them """
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


<<<<<<< Updated upstream
def wait_for_image_generation(generation_id):
    """Poll the API to check the status of image generation."""
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    while True:
        response = requests.get(url, headers=headers, timeout=30)
        response_dict = json.loads(response.text)
        status = response_dict.get("sdGenerationJob", {}).get("status")
        if status == "COMPLETE":
            return response_dict
        elif status == "FAILED":
            raise Exception("Image generation failed.")
        time.sleep(5)  # Wait before polling again


=======
>>>>>>> Stashed changes
def display_images(generation_id):
    """Fetch generated images and return their data"""
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


def generate_with_image_id(image_id, prompt, num_images):
    """ Function: Generate an image based on an image """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }

    # Generate with an image prompt: use Character Reference to control consistency
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
                  "initImageId": image_id,
                  "initImageType": "GENERATED",
                  "preprocessorId": 67, #Style Reference Id
                  "strengthType": "High",
              }
          ]
    }

    response = requests.post(url, json=payload, headers=headers)

    # Print response for debugging
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")

    # Get the generation of images
    generation_id = response.json()['sdGenerationJob']['generationId']
    return generation_id


def create_dataset(name):
    """Create a new dataset and return its ID"""
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


def create_user_dataset(dataset_name, seed_image_id, describe_user):
    """Create a dataset with multiple activity images."""
    logger.info(f"Starting dataset creation with name: {dataset_name}")
    
    dataset_id = create_dataset(dataset_name)
    if not dataset_id:
        logger.error("Failed to create dataset")
        return None
        
    logger.info(f"Dataset created successfully with ID: {dataset_id}")
    
    activities = [
        "playing basketball", "riding a bicycle", "reading a book",
        "playing the piano", "cooking in the kitchen", "flying a kite",
        "playing tennis", "swimming in a pool", "watering flowers"
    ]
    
    generated_images = []
    for activity in activities:
        logger.info(f"Generating image for activity: {activity}")
        prompt = f"Highly detailed 3D Disney Pixar-style animation of a {describe_user}, {activity}. Disney, Pixar art style, CGI, high details, 3d animation."
        
        generation_id = generate_with_image_id(seed_image_id, prompt, 1)
        if generation_id:
            logger.info(f"Generation started with ID: {generation_id}")
            
            # Wait for generation to complete
            generation_response = wait_for_image_generation(generation_id)
            if generation_response:
                image_ids = get_generated_image_ids(generation_id)
                for image_id in image_ids:
                    if upload_image_to_dataset(dataset_id, image_id):
                        logger.info(f"Successfully uploaded image {image_id} for activity: {activity}")
                        generated_images.append({
                            'activity': activity,
                            'image_id': image_id
                        })
                    else:
                        logger.error(f"Failed to upload image {image_id} to dataset")
            else:
                logger.error(f"Generation failed for activity: {activity}")
        else:
            logger.error(f"Failed to start generation for activity: {activity}")
            
        # Get current count of images
        current_count = get_number_of_images_in_dataset(dataset_id)
        logger.info(f"Current number of images in dataset: {current_count}")
    
    return {
        'dataset_id': dataset_id,
        'images': generated_images,
        'total_images': len(generated_images)
    }


def upload_image_to_dataset(dataset_id, generated_image_id):
    """Upload a generated image to a specified dataset."""
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}/images"
    payload = {
        "imageId": generated_image_id
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return response.status_code == 200

<<<<<<< Updated upstream
def create_user_dataset(dataset_name, seed_image_id, describe_user):
    """Create a new dataset for the user based on a seed image."""
    url = "https://cloud.leonardo.ai/api/rest/v1/datasets"
    payload = {
        "name": dataset_name,
        "description": describe_user,
        "seedImageId": seed_image_id
    }
=======

def display_all_images_in_dataset(dataset_id):
    """Get all images from a dataset."""
    url = f"https://cloud.leonardo.ai/api/rest/v1/datasets/{dataset_id}"
>>>>>>> Stashed changes
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    
    response = requests.get(url, headers=headers)
    print(f"Dataset API response status: {response.status_code}")  # Debug log
    
    if response.status_code == 200:
        dataset_info = response.json().get('datasets_by_pk', {})
        dataset_images = dataset_info.get('dataset_images', [])
        
        if not dataset_images:
            print(f"No images found in dataset {dataset_id}.")
            return []
            
        print(f"Found {len(dataset_images)} images in dataset {dataset_id}")
        
        activities = [
            "playing basketball", "riding a bicycle", "reading a book",
            "playing the piano", "cooking in the kitchen", "flying a kite",
            "playing tennis", "swimming in a pool", "watering flowers"
        ]
        
        images = []
        for i, image_data in enumerate(dataset_images):
            activity = activities[i] if i < len(activities) else f"Activity {i+1}"
            images.append({
                'id': image_data['id'],
                'url': image_data['url'],
                'activity': activity
            })
            print(f"Image {i+1}, id={image_data['id']}, URL: {image_data['url']}")
            
        return images
    else:
        print(f"Failed to retrieve dataset {dataset_id}. Status code: {response.status_code}")
        print(response.text)
        return []

def train_user_model(user_model_name, dataset_id):
    """Train a custom model using the specified dataset."""
    url = "https://cloud.leonardo.ai/api/rest/v1/models"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    payload = {
        "modelType": "CHARACTERS",
        "datasetId": dataset_id,
        "name": user_model_name
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json().get("sdTrainingJob", {}).get("customModelId")
<<<<<<< Updated upstream
    return None
=======
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


def check_generation_status(generation_id):
    """Check the status of a generation"""
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


def wait_for_image_generation(generation_id):
    """Wait for image generation to complete"""
    while True:
        status = check_generation_status(generation_id)
        if status == "COMPLETE":
            return True
        elif status == "FAILED":
            print(f"Image generation failed for ID: {generation_id}")
            return False
        time.sleep(2)  # Wait before checking again

 



>>>>>>> Stashed changes
