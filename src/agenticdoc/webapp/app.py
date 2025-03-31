import os
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from agentic_doc.parse import parse_documents
import logging
import uuid
import shutil
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Document Processor")

# Setup templates and static files
current_dir = Path(__file__).parent.resolve()
templates = Jinja2Templates(directory=str(current_dir / "templates"))
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")

# Setup directories
UPLOAD_DIR = current_dir / "data" / "uploads"  # Original upload directory for processing
PREVIEW_DIR = current_dir / "data" / "previews"  # New directory for preview files
OUTPUT_DIR = current_dir / "data" / "output"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mount preview directory for serving preview files
app.mount("/previews", StaticFiles(directory=str(PREVIEW_DIR)), name="previews")

class Field(BaseModel):
    name: str
    description: str

class ExtractionRequest(BaseModel):
    document_id: str
    document_type: str
    fields: List[Field]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/configure", response_class=HTMLResponse)
async def configure_page(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), document_type: str = Form(...)):
    try:
        # Generate a unique ID for this upload
        file_id = str(uuid.uuid4())
        
        # Create a unique directory for this upload (original flow)
        upload_path = UPLOAD_DIR / file_id
        upload_path.mkdir(exist_ok=True)
        
        # Save uploaded file with original name in the unique directory
        file_path = upload_path / file.filename
        logger.info(f"Saving file to {file_path}")
        
        try:
            # Read file content once
            content = await file.read()
            
            # Save for processing (original flow)
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # Save a copy for preview (parallel flow)
            preview_path = PREVIEW_DIR / f"{file_id}_{file.filename}"
            with open(preview_path, "wb") as buffer:
                buffer.write(content)
            logger.info(f"Saved preview file to {preview_path}")

            # Process the document (original flow)
            logger.info(f"Processing document: {file_path}")
            results = parse_documents([str(file_path)])
            parsed_doc = results[0]
            
            # Return both original data and preview path
            return {
                "success": True,
                "id": file_id,
                "markdown": parsed_doc.markdown,
                "chunks": parsed_doc.chunks,
                "filename": file.filename,
                "document_type": document_type,
                "previewUrl": f"/previews/{file_id}_{file.filename}"  # New field for preview
            }
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            # Clean up preview file if processing failed
            preview_path = PREVIEW_DIR / f"{file_id}_{file.filename}"
            if preview_path.exists():
                preview_path.unlink()
            # Don't delete the original file on processing error so we can debug
            raise HTTPException(status_code=400, detail=f"Error processing document: {str(e)}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "filename": file.filename
            }
        )

@app.post("/extract")
async def extract_data(request: ExtractionRequest):
    try:
        # Get the uploaded file path
        file_path = UPLOAD_DIR / request.document_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Mock extraction response for now
        # In a real implementation, this would call the document processing logic
        extracted_data = {
            "document_type": request.document_type,
            "fields": {
                field.name: f"Extracted {field.name.lower()}" 
                for field in request.fields
            }
        }
        
        return JSONResponse({
            "status": "success",
            "data": extracted_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def cleanup():
    # Clean up uploaded files and previews
    for directory in [UPLOAD_DIR, PREVIEW_DIR, OUTPUT_DIR]:
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True) 