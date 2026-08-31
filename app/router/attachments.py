import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.services.storage_service import StorageService
from app.config import settings

router = APIRouter(prefix="/api/attachments", tags=["attachments"])

@router.post("/upload")
def upload_file(file: UploadFile = File(...), storage_service: StorageService = Depends()):
    try:
        # Generate a unique filename using UUID
        extension = file.filename.split(".")[-1] if "." in file.filename else ""
        unique_filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
        
        # Upload using the corrected parameter call
        storage_service.upload_file(file.file, unique_filename)
        
        # Return path (e.g. /fieldchat-media/some-uuid.png)
        # Frontend can prepend standard storage host (http://localhost:9000 or OCI URL)
        file_url = f"/{settings.S3_BUCKET_NAME}/{unique_filename}"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "filename": file.filename,
        "url": file_url
    }
