from fastapi import APIRouter,HTTPException
from app.dependencies import DBSession
from app.schema.auth.user import UserResponse
from app.services.user import user_service
router = APIRouter(
    prefix="/api/auth/users",
    tags=["User Management"]
)

@router.get('/get_user_with_email',response_model=UserResponse)
async def get_user_with_email(db:DBSession,email:str):
    user = await user_service.get_user_with_email_or_username(db,email)
    if not user:
        raise HTTPException(404,"User not found")
    return user