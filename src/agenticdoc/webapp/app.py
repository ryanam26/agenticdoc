import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from agentic_doc.parse import parse_documents
import logging
import tempfile
import shutil
from agenticdoc.webapp.tasks import task_manager, TaskStatus

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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}

def is_valid_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def process_document_in_background(task_id: str, file_path: str):
    """Process the document in the background and update the task status."""
    try:
        # Update task status to processing
        task_manager.update_task(task_id, TaskStatus.PROCESSING)
        
        # Process the document
        logger.info(f"Processing document: {file_path}")
        results = parse_documents([str(file_path)])
        
        if not results or len(results) == 0:
            raise Exception("Document processing failed: No results returned")
        
        # Get the markdown from the first (and only) document
        parsed_doc = results[0]
        
        # Update task with result
        task_manager.update_task(
            task_id,
            TaskStatus.COMPLETED,
            result={"markdown": parsed_doc.markdown}
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        task_manager.update_task(
            task_id,
            TaskStatus.FAILED,
            error=str(e)
        )
    finally:
        # Clean up temporary file
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary file: {str(e)}")

@app.post("/process")
async def process_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process a document asynchronously and return a task ID for polling.
    """
    try:
        # Validate file
        if not is_valid_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported types: PDF, PNG, JPG, JPEG"
            )
        
        # Create a task
        task_id = task_manager.create_task()
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        try:
            # Read file content
            content = await file.read()
            
            # Save to temporary file
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content)
            
            # Add background task
            background_tasks.add_task(process_document_in_background, task_id, temp_file_path)
            
            return {
                "task_id": task_id,
                "status": "pending",
                "message": "Document processing started"
            }
            
        except Exception as e:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error saving file: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a processing task.
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