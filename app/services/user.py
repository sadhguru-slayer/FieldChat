from app.models.auth.user import User
from fastapi import HTTPException
from sqlalchemy import select
from app.core.security.auth import token_manager
from uuid import UUID
class UserService:
    @classmethod
    async def get_user_with_email_or_username(cls, db,email_username:str):
        result= await db.execute(select(User).where(
            (User.email == email_username) | (User.username == email_username)
        ))
        return result.scalar_one_or_none()

    @classmethod
    async def get_current_user(cls, db,token:str):
        payload = token_manager.decode_token(token)
        user_id  = payload.get("sub")
        if not user_id :
            raise HTTPException(401,"Invalid token payload")
        result = await db.execute(select(User).where(User.id==UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(401,"User not found")
        return user

user_service = UserService()