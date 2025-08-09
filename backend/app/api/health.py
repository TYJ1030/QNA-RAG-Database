from fastapi import APIRouter
import os
from pathlib import Path

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint to debug deployment issues"""
    try:
        # Check file system
        upload_dir = Path("/tmp/temp_uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Check ChromaDB directory
        chroma_dir = Path("/tmp/chroma_db")
        chroma_dir.mkdir(exist_ok=True)
        
        # Check environment variables
        env_vars = {
            "OPENROUTER_API_KEY": "✓" if os.getenv("OPENROUTER_API_KEY") else "✗",
            "REDIS_URL": "✓" if os.getenv("REDIS_URL") else "✗"
        }
        
        return {
            "status": "healthy",
            "upload_dir": str(upload_dir),
            "upload_dir_exists": upload_dir.exists(),
            "upload_dir_writable": os.access(upload_dir, os.W_OK),
            "chroma_dir": str(chroma_dir),
            "chroma_dir_exists": chroma_dir.exists(),
            "env_vars": env_vars
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }