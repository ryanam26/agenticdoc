import json
import os
import logging
import requests
from typing import Dict, List, Any, TypedDict, Literal, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define types
class DataField(TypedDict):
    id: str
    name: str
    description: str

DocumentType = Literal["paystub", "w2", "tax_return", "lease_agreement", 
                      "mortgage_statement", "bank_statement", 
                      "card_processing_statement", "custom"]

class ExtractDataParams(TypedDict):
    markdown: str
    document_type: DocumentType
    fields: List[DataField]

ExtractionResult = Dict[str, str]

def create_extractor_prompt(document_type: DocumentType, fields: List[DataField]) -> str:
    """
    Helper function to create a structured prompt for document data extraction.
    
    Args:
        document_type: Type of document to extract data from
        fields: List of fields to extract
        
    Returns:
        Formatted prompt string
    """
    document_type_map = {
        "paystub": "Paystub/Pay Slip",
        "w2": "W-2 Tax Form",
        "tax_return": "Tax Return",
        "lease_agreement": "Lease Agreement",
        "mortgage_statement": "Mortgage Statement",
        "bank_statement": "Bank Statement",
        "card_processing_statement": "Card Processing Statement",
        "custom": "Document",
    }
    
    document_label = document_type_map[document_type]
    
    field_descriptions = "\n".join([
        f"- {field['id']}: {field['name']} - {field['description']}"
        for field in fields
    ])
    
    # Create a list of fields for the JSON response
    fields_for_json = ", ".join([f'"{field["id"]}"' for field in fields])
    
    return f"""You are a precise document data extraction assistant. 
Extract the following specific information from this {document_label}:

{field_descriptions}

Important instructions:
1. Only extract the specific data fields requested
2. Return the data in valid JSON format with these exact keys: {{{fields_for_json}}}
3. If you cannot find a particular piece of information, use an empty string for that field
4. Do not include any explanations or notes in your response, only the JSON object
5. Be precise and extract the exact data as it appears in the document"""

def extract_data_from_document(params: ExtractDataParams) -> ExtractionResult:
    """
    Extract data from a document using OpenAI's API.
    
    Args:
        params: Dictionary containing markdown, documentType, and fields
        
    Returns:
        Dictionary with extracted field values
    """
    markdown = params["markdown"]
    document_type = params["document_type"]
    fields = params["fields"]
    
    # Create a formatted prompt for the OpenAI API
    prompt = create_extractor_prompt(document_type, fields)
    logger.info("Created prompt for OpenAI: %s", prompt)
    logger.info("Markdown to be processed: %s", markdown)
    
    try:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Make the API request
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_api_key}",
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nHere is the text to extract from the document:\n\n{markdown}",
                    }
                ],
                "temperature": 0.2,
            },
        )
        
        if not response.ok:
            error_data = response.json()
            logger.error("OpenAI API error response: %s", error_data)
            raise Exception(f"OpenAI API Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
        
        extraction_data = response.json()
        logger.info("Raw OpenAI API response: %s", extraction_data)
        
        # Process the extraction results
        result: ExtractionResult = {}
        
        if (
            extraction_data.get("choices")
            and extraction_data["choices"][0]
            and extraction_data["choices"][0].get("message")
        ):
            try:
                # Parse the JSON from the response content
                content = extraction_data["choices"][0]["message"]["content"]
                logger.info("OpenAI response content: %s", content)
                
                # Clean up the content by removing markdown code block syntax
                clean_content = content.replace("```json", "").replace("```", "").strip()
                logger.info("Cleaned content for parsing: %s", clean_content)
                
                extracted_data = json.loads(clean_content)
                logger.info("Parsed JSON data from OpenAI: %s", extracted_data)
                
                # Map the extracted fields to our result format
                for field in fields:
                    result[field["id"]] = extracted_data.get(field["id"], "")
                
                logger.info("Final mapped extraction results: %s", result)
            except Exception as e:
                logger.error("Error parsing JSON from OpenAI response: %s", e)
                raise Exception("Failed to parse extracted data")
        else:
            raise Exception("No valid response data received from OpenAI API")
        
        return result
    except Exception as error:
        logger.error("Error in OpenAI extraction process: %s", error)
        raise error