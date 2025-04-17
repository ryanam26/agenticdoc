import json
import os
import logging
import tempfile
from typing import Dict, List, Any, TypedDict, Literal, Union, Optional
from openai import OpenAI

from webapp.documents import save_file_and_vector_store_ids

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
    document_id: str
    markdown: str
    document_type: DocumentType
    fields: List[DataField]
    file_ids: Optional[List[str]] = None
    vector_store_ids: Optional[List[str]] = None

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

def create_openai_file_from_markdown(client: OpenAI, markdown: str) -> str:
    """
    Create a file in OpenAI from markdown content.
    
    Args:
        client: OpenAI client
        markdown: Markdown content to create a file from
        
    Returns:
        File ID
    """
    # Create a temporary file with the markdown content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
        temp_file.write(markdown)
        temp_file_path = temp_file.name
    
    try:
        # Create a file in OpenAI
        with open(temp_file_path, 'rb') as file:
            file_response = client.files.create(
                file=file,
                purpose="assistants"
            )
        
        logger.info(f"Created file with ID: {file_response.id}")
        return file_response.id
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

def create_vector_store(client: OpenAI, file_id: str, name: str = "Document Extraction") -> str:
    """
    Create a vector store with the given file.
    
    Args:
        client: OpenAI client
        file_id: ID of the file to use
        name: Name of the vector store
        
    Returns:
        Vector store ID
    """
    vector_store = client.vector_stores.create(
        name=name,
        file_ids=[file_id]
    )
    
    logger.info(f"Created vector store with ID: {vector_store.id}")
    return vector_store.id

def create_file_and_vector_store(markdown: str, document_type: DocumentType) -> Dict[str, str]:
    """
    Create a file from markdown content and a vector store with that file.
    
    Args:
        markdown: Markdown content to create a file from
        document_type: Type of document
        
    Returns:
        Dictionary containing file_id and vector_store_id
    """
    try:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Create a file from the markdown content
        file_id = create_openai_file_from_markdown(client, markdown)
        
        # Create a vector store with the file
        vector_store_id = create_vector_store(client, file_id, f"{document_type} Extraction")
        
        return {
            "file_id": file_id,
            "vector_store_id": vector_store_id
        }
    except Exception as error:
        logger.error("Error creating file and vector store: %s", error)
        raise error

def extract_data_from_document(params: ExtractDataParams) -> ExtractionResult:
    """
    Extract data from a document using OpenAI's API with vector store.
    
    Args:
        params: Dictionary containing markdown, documentType, and fields
        
    Returns:
        Dictionary with extracted field values
    """
    markdown = params["markdown"]
    document_type = params["document_type"]
    fields = params["fields"]
    document_id = params["document_id"]
    
    # Create a formatted prompt for the OpenAI API
    prompt = create_extractor_prompt(document_type, fields)
    logger.info("Created prompt for OpenAI: %s", prompt)
    logger.info("Markdown to be processed: %s", markdown)
    
    try:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Create a file from the markdown content
        file_ids = []
        vector_store_ids = []
        if params.get("file_ids") is None:
            file_id = create_openai_file_from_markdown(client, markdown)
            file_ids.append(file_id)
        else:
            file_ids = params.get("file_ids")
        
        # Create a vector store with the file
        if params.get("vector_store_ids") is None:
            vector_store_id = create_vector_store(client, file_id, f"{document_type} Extraction")
            vector_store_ids.append(vector_store_id)
        else:
            vector_store_ids = params.get("vector_store_ids")

        # save the file id and  vector store id to the database
        save_file_and_vector_store_ids(document_id, file_ids, vector_store_ids)
        
        # Make the API request with vector store
        response = client.responses.create(
            model="gpt-4.1",
            tools=[{
                "type": "file_search",
                "vector_store_ids": vector_store_ids,
                "max_num_results": 100
            }],
            input=prompt
        )
        
        logger.info("Raw OpenAI API response: %s", response)
        
        # Process the extraction results
        result: ExtractionResult = {}
        
        # Check if the response has the expected structure
        if hasattr(response, 'output') and isinstance(response.output, list):
            # Find the message output that contains the content
            for output_item in response.output:
                if hasattr(output_item, 'type') and hasattr(output_item, 'status'):
                    if output_item.type == 'message' and output_item.status == 'completed':
                        # Extract the content from the message
                        if hasattr(output_item, 'content'):
                            content_items = output_item.content
                            for content_item in content_items:
                                if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                    if hasattr(content_item, 'text'):
                                        content = content_item.text
                                        logger.info("OpenAI response content: %s", content)
                                        
                                        clean_content = content.replace("```json", "").replace("```", "").strip()
                                        logger.info("Cleaned content for parsing: %s", clean_content)
                                        
                                        try:
                                            extracted_data = json.loads(clean_content)
                                            logger.info("Parsed JSON data from OpenAI: %s", extracted_data)
                                            
                                            for field in fields:
                                                result[field["id"]] = extracted_data.get(field["id"], "")
                                            
                                            logger.info("Final mapped extraction results: %s", result)
                                            return result
                                        except json.JSONDecodeError as e:
                                            logger.error("Error parsing JSON from OpenAI response: %s", e)
                                            raise Exception("Failed to parse extracted data")
        
        raise Exception("No valid response data received from OpenAI API")
    except Exception as error:
        logger.error("Error in OpenAI extraction process: %s", error)
        raise error 