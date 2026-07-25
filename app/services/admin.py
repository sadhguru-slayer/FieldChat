from app.models.auth.user import UserRole
from fastapi import HTTPException,Depends

from app.services.user import user_service
from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme

class AdminService:
    @classmethod
    async def get_current_admin_user(db:DBSession ,token:str = Depends(oauth2_scheme)):
        user = await user_service.get_current_user(db,token)
        if user.role != UserRole.ADMIN:
            raise HTTPException(403,"Admin access required")
        return user

admin_service = AdminService()