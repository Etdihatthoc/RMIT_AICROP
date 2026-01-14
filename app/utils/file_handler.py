"""
File upload handling utilities
"""

import aiofiles
from fastapi import UploadFile, HTTPException
from pathlib import Path
import uuid
import logging

logger = logging.getLogger(__name__)


async def save_uploaded_file(
    file: UploadFile,
    upload_dir: str,
    allowed_extensions: set = None
) -> str:
    """
    Save uploaded file and return path

    Args:
        file: FastAPI UploadFile object
        upload_dir: Directory to save file
        allowed_extensions: Set of allowed file extensions (e.g., {'.jpg', '.png'})

    Returns:
        File path as string

    Raises:
        HTTPException: If file extension not allowed
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if allowed_extensions and file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed: {allowed_extensions}"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = Path(upload_dir) / unique_filename

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file asynchronously
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"File saved: {file_path}")
        return str(file_path)

    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")


def validate_file_size(file: UploadFile, max_size_mb: int):
    """
    Validate file size (note: this reads the file into memory)

    Args:
        file: UploadFile object
        max_size_mb: Maximum file size in MB

    Raises:
        HTTPException: If file too large
    """
    # Note: For production, implement streaming validation
    # This is a simple check for MVP
    pass  # Will implement in route if needed
