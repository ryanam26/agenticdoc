from typing import Dict, Any
from dotenv import load_dotenv

from agenticdoc.webapp.documents import  save_document_info,create_agentic_doc_job
load_dotenv()

import os

from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
import logging
import tempfile
from agenticdoc.webapp.tasks import TaskStatus,task_manager
from agenticdoc.webapp.background import process_document_in_background
from agenticdoc.webapp.auth import get_current_user
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document Processing API",
    description="API for processing documents and returning markdown",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

def is_valid_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process a document with additional metadata.
    
    Args:
        file: The uploaded file to process
        metadata: JSON string containing additional metadata
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
    """
    try:
        # Parse the metadata JSON string
        metadata_dict = json.loads(metadata)

        task_id = task_manager.create_task()
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)

        content = await file.read()
            
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)

        agentic_job_doc = create_agentic_doc_job(
            user_id=current_user.id,
            fields=metadata_dict.get("fields", {}),
            result={},
            error="",
            document_type=metadata_dict.get("document_type", "unknown")
        )

        agentic_job_doc_id = agentic_job_doc[0]["job_id"]
        # Save document info with metadata
        document_info = save_document_info(
            user_id=current_user.id,
            file_name=file.filename,
            file_size=file.size,  
            file_type=file.content_type,
            status="processing",
            document_type=metadata_dict.get("document_type", "unknown"),
            processing_result="",
            error_message="",
            job_id=agentic_job_doc_id,
            metadata=metadata_dict.get("fields", {})
        )

        background_tasks.add_task(process_document_in_background, task_id, temp_file_path, agentic_job_doc_id,metadata_dict)
        
        return {"message": "Document processing started", "document_info": document_info, "task_id": task_id, "status": "processing"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the status of a processing task.
    Requires authentication.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    response = {
        "task_id": task.id,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat()
    }
    
    if task.status == TaskStatus.COMPLETED:
        response["result"] = task.result
    elif task.status == TaskStatus.FAILED:
        response["error"] = task.error
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 

@app.get("/user-test")
async def user_test(
        current_user: Dict[str, Any] = Depends(get_current_user)
):
    """User test endpoint"""
    return {"status": "healthy",
            "user": current_user} 