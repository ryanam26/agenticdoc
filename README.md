# Document Processing Web Application

A web application for processing documents (PDFs and images) using agentic-doc, with a modern web interface.

## Features

- Upload PDFs and images via drag-and-drop or file browser
- Process documents using agentic-doc
- View extracted markdown and structured data
- Modern, responsive UI using TailwindCSS
- Real-time markdown rendering

## Setup

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Run the web application:

   ```bash
   poetry run uvicorn webapp.app:app --host 0.0.0.0 --port 8000
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Supported File Types

- PDF documents
- Images (PNG, JPG, JPEG)

## Development

The application uses:

- FastAPI for the backend
- TailwindCSS for styling
- markdown-it for markdown rendering
- agentic-doc for document processing
