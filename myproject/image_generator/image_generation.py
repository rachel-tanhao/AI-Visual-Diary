import requests
import json
import time
import os

leonardo_api_key = os.getenv("LEONARDO_API_KEY")
authorization = "Bearer %s" % leonardo_api_key

def formatJsonResponse(response):
    """Convert JSON response to a formatted string."""
    response_dict = json.loads(response.text)
    formatted_response = json.dumps(response_dict, indent=4)
    return formatted_response

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
    """Fetch generated images using the generation ID."""
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}/images"
    headers = {
        "accept": "application/json",
        "authorization": authorization
    }
    response = requests.get(url, headers=headers, timeout=30)
    response_dict = json.loads(response.text)
    return response_dict.get("images", [])

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

def display_images(generation_id):
    """Display generated images based on generation ID."""
    images = get_generated_image_ids(generation_id)
    for image in images:
        print(f"Image URL: {image['url']}")  # Replace with your display logic

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

def create_user_dataset(dataset_name, seed_image_id, describe_user):
    """Create a new dataset for the user based on a seed image."""
    url = "https://cloud.leonardo.ai/api/rest/v1/datasets"
    payload = {
        "name": dataset_name,
        "description": describe_user,
        "seedImageId": seed_image_id
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": authorization
    }
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json().get("datasetId")
    return None

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
    return None