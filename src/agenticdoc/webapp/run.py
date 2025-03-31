import uvicorn
from pathlib import Path

def main():
    # Run the FastAPI application
    uvicorn.run(
        "app:app",  # Changed from src.agenticdoc.webapp.app:app
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        app_dir=str(Path(__file__).parent)  # Set the app directory to the current directory
    )

if __name__ == "__main__":
    main() 