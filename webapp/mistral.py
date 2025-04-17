import requests
import os

def create_mistral_ocr_request(document_url: str):
    body = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": document_url
        },
        "include_image_base64": False
    }
    return body


def format_mistral_ocr_response(response_data):
    """
    Format the Mistral OCR response by combining markdown from all pages with double newlines.
    
    Args:
        response_data (dict): The JSON response from Mistral OCR API
        
    Returns:
        str: Combined markdown with double newlines between pages
    """
    if not response_data.get('pages'):
        return ""
        
    markdown_parts = []
    for page in response_data['pages']:
        if page.get('markdown'):
            markdown_parts.append(page['markdown'])
    
    return "\n\n".join(markdown_parts).strip()

def get_mistral_ocr_response(document_url: str):
    request_url = 'https://api.mistral.ai/v1/ocr'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("VITE_MISTRAL_API_KEY")}'
    }

    body = create_mistral_ocr_request(document_url)

    response = requests.post(request_url, headers=headers, json=body)

    result = response.json()
    return format_mistral_ocr_response(result)
