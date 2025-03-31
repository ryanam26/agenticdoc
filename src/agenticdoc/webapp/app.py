import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agentic_doc.parse import parse_documents
import logging
import tempfile
import shutil

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

@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    """
    Process a document (PDF or image) and return markdown content.
    
    Args:
        file: The uploaded file (PDF, PNG, JPEG, JPG)
        
    Returns:
        dict: Contains the markdown output
        
    Raises:
        HTTPException: If file type is invalid or processing fails
    """
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_file_path = Path(temp_dir) / file.filename
            
            try:
                # Read file content
                content = await file.read()
                
                # Save to temporary file
                with open(temp_file_path, "wb") as buffer:
                    buffer.write(content)
                
                # Process the document
                logger.info(f"Processing document: {temp_file_path}")
                results = parse_documents([str(temp_file_path)])
                
                if not results or len(results) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail="Document processing failed: No results returned"
                    )
                
                # Get the markdown from the first (and only) document
                parsed_doc = results[0]
                
                return {
                    "markdown": parsed_doc.markdown
                }
                
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing document: {str(e)}"
                )
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 