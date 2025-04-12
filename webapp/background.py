from typing import Any, Dict
from agentic_doc.parse import parse_documents
from webapp.documents import update_agentic_doc_job, update_document_by_job_id
from webapp.llm import extract_data_from_document
from webapp.tasks import task_manager, TaskStatus
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_document_in_background(task_id: str, file_path: str, agentic_job_doc_id: str,metadata: Dict[str, Any]):
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

        update_agentic_doc_job(
            job_id=agentic_job_doc_id,
            result=parsed_doc.markdown,
            error=""
        )

        logger.info(f"✅ Successfully parsed document to get markdown \n\n{parsed_doc.markdown}")

        extracted_data = extract_data_from_document({
            "markdown": parsed_doc.markdown,
            "document_type": metadata["document_type"],
            "fields": metadata["fields"]
        })

        update_document_by_job_id(
            job_id=agentic_job_doc_id,
            status="completed",
            processing_result=extracted_data,
        )

        # Update task with result
        task_manager.update_task(
            task_id,
            TaskStatus.COMPLETED,
            result={"markdown": parsed_doc.markdown, "data": extracted_data}
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