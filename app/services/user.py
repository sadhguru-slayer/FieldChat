from app.models.auth.user import User
from fastapi import HTTPException
from sqlalchemy import select
from app.core.security.auth import token_manager
from uuid import UUID
class UserService:
    @classmethod
    async def get_user_with_id(cls, db,user_id:str):
        result= await db.execute(select(User).where(
            User.id == UUID(user_id)
        ))
        return result.scalar_one_or_none()
    
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

    @classmethod
    async def get_user_with_id_ws(cls, db,user_id:str):
        result= await db.execute(select(User).where(
            User.id == UUID(user_id)
        ))
        return result.scalar_one_or_none()

    async def get_current_user_ws(
        db,
        token: str
    ):

        payload = verify_access_token(token)

        if not payload:
            return None

        user_id = payload.get("sub")

        stmt = select(User).where(User.id == user_id)

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

user_service = UserService()