# here, we first need to save this information on database (supabase)
# user_id, file_name, file_path, file_size, file_type, status (pending, processing, completed, failed), document_type, processing_result, error_message, job_id, metadata (we store user's fields to be extracted here)


from typing import Any, Dict, List
from webapp.db import get_supabase_client

def create_agentic_doc_job(
    user_id: str,
    fields: Dict[str, Any],
    result: Dict[str, Any],
    error: str,
    document_type: str
) -> Dict[str, Any]:
    supabase = get_supabase_client()
    response = supabase.table("agentic_doc_jobs").insert({
        "user_id": user_id,
        "fields": fields,
        "result": result,
        "error": error,
        "document_type": document_type,
        "status": "pending"
    }).execute()

    return response.data

def update_agentic_doc_job(
    job_id: str,
    result: Dict[str, Any],
    error: str,
) -> Dict[str, Any]:
    supabase = get_supabase_client()

    update_data = {
        "result": result,
        "error": error
    }

    response = supabase.table("agentic_doc_jobs").update(update_data).eq("job_id", job_id).execute()

    return response.data


def update_agentic_doc_job_fields(
    job_id: str,
    fields: Dict[str, Any]= None
) -> Dict[str, Any]:
    supabase = get_supabase_client()

    update_data = {
        "fields": fields
    }

    response = supabase.table("agentic_doc_jobs").update(update_data).eq("job_id", job_id).execute()

    return response.data

def save_document_info(
    user_id: str,
    file_name: str,
    file_size: int,
    file_type: str,
    status: str,
    document_type: str,
    processing_result: str,
    error_message: str,
    job_id: str,
    metadata: Dict[str, Any],
    file_path: str
) -> Dict[str, Any]:
    """
    Save document information to the Supabase database.
    
    Args:
        user_id: The ID of the user who uploaded the document
        file_name: Name of the uploaded file
        file_path: Path where the file is stored
        file_size: Size of the file in bytes
        file_type: MIME type of the file
        status: Processing status (pending, processing, completed, failed)
        document_type: Type of the document
        processing_result: Results from document processing
        error_message: Error message if processing failed
        job_id: ID of the processing job
        metadata: Additional metadata about the document
        
    Returns:
        Dict containing the response from Supabase
    """
    supabase = get_supabase_client()
    
    document_data = {
        "user_id": user_id,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "file_type": file_type,
        "status": status,
        "document_type": document_type,
        "processing_result": processing_result,
        "error_message": error_message,
        "job_id": job_id,
        "metadata": metadata
    }
    
    response = supabase.table("documents").insert(document_data).execute()
    return response.data

def update_document_by_job_id(
    job_id: str,
    status: str,
    processing_result: str = "",
    error_message: str = "",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Update document information in the Supabase database based on job_id.
    
    Args:
        job_id: ID of the processing job
        status: New processing status (pending, processing, completed, failed)
        processing_result: Results from document processing (optional)
        error_message: Error message if processing failed (optional)
        metadata: Additional metadata to update (optional)
        
    Returns:
        Dict containing the updated document data from Supabase
    """
    supabase = get_supabase_client()
    
    update_data = {
        "status": status,
        "processing_result": processing_result,
        "error_message": error_message
    }
    
    if metadata is not None:
        update_data["metadata"] = metadata
    
    response = (
        supabase.table("documents")
        .update(update_data)
        .eq("job_id", job_id)
        .execute()
    )
    
    return response.data

def update_document_data(
    document_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update document information in the Supabase database based on document_id.
    
    Args:
        document_id: ID of the document
        data: Data to update
        
    Returns:
        Dict containing the updated document data from Supabase
    """
    supabase = get_supabase_client()
    
    response = (
        supabase.table("documents")
        .update(data)
        .eq("id", document_id)
        .execute()
    )
    
    return response.data

def get_document_data_by_document_id(document_id: str) -> Dict[str, Any]:
    supabase = get_supabase_client()
    document_response = supabase.table("documents").select("job_id, document_type, file_ids, vector_store_ids").eq("id", document_id).execute()
    agentic_job_response = supabase.table("agentic_doc_jobs").select("result").eq("job_id", document_response.data[0]["job_id"]).execute()

    return {
        "document_type": document_response.data[0]["document_type"],
        "markdown": agentic_job_response.data[0]["result"],
        "job_id": document_response.data[0]["job_id"],
        "file_ids": document_response.data[0]["file_ids"],
        "vector_store_ids": document_response.data[0]["vector_store_ids"]
    }

def save_file_and_vector_store_ids(
    document_id: str,
    file_ids: List[str],
    vector_store_ids: List[str]
) -> Dict[str, Any]:
    supabase = get_supabase_client()
    response = supabase.table("documents").update({
        "file_ids": file_ids,
        "vector_store_ids": vector_store_ids
    }).eq("id", document_id).execute()
    return response.data






