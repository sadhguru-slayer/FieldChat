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
        storage_service.upload_file(file.file, unique_filename, content_type=file.content_type)
        
        # Return path (e.g. /fieldchat-media/some-uuid.png or absolute OCI/S3 URL if S3_PUBLIC_URL is set)
        if settings.S3_PUBLIC_URL:
            file_url = f"{settings.S3_PUBLIC_URL.rstrip('/')}/{unique_filename}"
        else:
            file_url = f"/{settings.S3_BUCKET_NAME}/{unique_filename}"
        
    except Exception as e:
        import traceback
        print(f"[Upload Router Error] Failed uploading file '{file.filename}': {e}", flush=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")
        
    return {
        "filename": file.filename,
        "url": file_url
    }
