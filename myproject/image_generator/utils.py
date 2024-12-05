import json
from django.urls import path
from .views import upload_diary, display_images

def format_json_response(response):
    """Convert JSON response to a formatted string."""
    response_dict = json.loads(response.text)
    formatted_response = json.dumps(response_dict, indent=4)
    return formatted_response
