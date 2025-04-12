import os
import uuid
import mimetypes
from typing import Optional
from fastapi import HTTPException
from .db import get_supabase_client

def upload_file_to_storage(
    user_id: str,
    file_content: bytes,
    file_name: str,
    bucket_name: str = "documents",
) -> str:
    """
    Upload a file to Supabase storage and return its public URL.
    
    Args:
        user_id: The ID of the user uploading the file
        file_content: The binary content of the file to upload
        file_name: The original name of the file
        bucket_name: The name of the storage bucket (default: "documents")
        
    Returns:
        The public URL of the uploaded file
        
    Raises:
        HTTPException: If the upload fails
    """
    try:
        # Get the Supabase client
        supabase = get_supabase_client()
        
        # Extract file extension
        _, file_extension = os.path.splitext(file_name)
        if not file_extension:
            file_extension = ".bin"  # Default extension if none is found
            
        # Generate a unique filename using UUID
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Construct the file path with user_id and unique filename
        file_path = f"{user_id}/{unique_filename}"
        
        # Determine the correct MIME type based on file extension
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"  # Default MIME type if none is detected
        
        print(f"Uploading file to {file_path} with MIME type: {mime_type}")
        
        # Upload the file to Supabase storage with the correct content type
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": mime_type}
        )
        
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        
        print(f"File uploaded to {public_url}")
        
        return public_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
