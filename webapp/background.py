import json
from typing import Any, Dict
from agentic_doc.parse import parse_documents
from webapp.documents import get_document_data_by_document_id, update_agentic_doc_job,  update_document_by_job_id, update_agentic_doc_job_fields, update_document_data   
from webapp.llm import extract_data_from_document
from webapp.mistral import get_mistral_ocr_response
from webapp.tasks import task_manager, TaskStatus
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_document_in_background(document_id: str, fields: Dict[str, Any]):
    """Process the document in the background and update the task status."""
    try:
        update_document_data(
            document_id=document_id,
            data={
                "status": "processing",
                "has_checked": False
            }
        )
        print(f"Document {document_id} updated to processing")
        document_data = get_document_data_by_document_id(document_id)
        print(f"Document {document_id} data: {document_data}")

        extracted_data = extract_data_from_document({
            "markdown": document_data["markdown"],
            "document_type": document_data["document_type"],
            "fields": fields,
            "document_id": document_id,
            "file_ids": document_data["file_ids"],
            "vector_store_ids": document_data["vector_store_ids"]
        })

        print(f"Extracted data: {extracted_data}")

        update_agentic_doc_job_fields(
            job_id=document_data["job_id"],
            fields=fields
        )

        print(f"Updated agentic doc job fields: {fields}")

        update_document_by_job_id(
            job_id=document_data["job_id"],
            status="completed",
            processing_result=extracted_data,
            metadata= fields
        )

        print(f"Updated document by job id: {document_data['job_id']}")

        # update document value to processing
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return None


def process_document_in_background(task_id: str, file_path: str, agentic_job_doc_id: str,metadata: Dict[str, Any],file_url: str, document_id: str):
    """Process the document in the background and update the task status."""
    try:
        # Update task status to processing
        task_manager.update_task(task_id, TaskStatus.PROCESSING)
        # Process the document
        logger.info(f"Processing document: {file_path}")
        results = parse_documents([str(file_path)])
        markdown = ""

        # write entire results to a file
        for result in results:
            value = result.model_dump_json()
            with open("results.txt", "a") as f:
                f.write(value)

        chunks = results[0].chunks
        error_chunks = []
        for chunk in chunks:
            if chunk.chunk_type=="error":
                error_chunks.append(chunk)

        if not results or len(results) == 0 or len(error_chunks) > 0:
            try:
                print("Attempting to parse document using mistral ocr")
                markdown = get_mistral_ocr_response(file_url)
                print(f"✅ Successfully parsed document using mistral \n\n{markdown}")
            except Exception as e:
                raise Exception("Document processing failed : No results returned")

        else:
            parsed_doc = results[0]
            markdown = parsed_doc.markdown

        update_agentic_doc_job(
            job_id=agentic_job_doc_id,
            result=markdown,
            error=""
        )

        logger.info(f"✅ Successfully parsed document to get markdown \n\n{markdown}")

        extracted_data = extract_data_from_document({
            "markdown": markdown,
            "document_type": metadata["document_type"],
            "fields": metadata["fields"],
            "document_id": document_id
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
            result={"markdown": markdown, "data": extracted_data}
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        task_manager.update_task(
            task_id,
            TaskStatus.FAILED,
            error=str(e)
        )
        update_document_by_job_id(
            job_id=agentic_job_doc_id,
            status="failed",
            error_message=str(e)
        )
    finally:
        try:
            os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary file: {str(e)}")