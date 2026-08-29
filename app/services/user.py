from app.models.auth.user import User
from app.models.profile.profile import UserProfile
from fastapi import HTTPException
from sqlalchemy import select
rom sqlalchemy.orm import selectinload
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
    async def get_current_user(cls, db, token: str, device_id: str | None = None):
        payload = token_manager.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token payload")
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(401, "User not found")

        if device_id:
            from app.models.auth.refresh import RefreshToken
            res = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == UUID(user_id),
                    RefreshToken.device_id == device_id
                )
            )
            refresh_session = res.scalars().first()
            if refresh_session and refresh_session.revoked:
                raise HTTPException(401, "Session has been revoked")

        return user


    @classmethod
    async def get_user_with_id_ws(cls, db,user_id:str):
        result= await db.execute(select(User).where(
            User.id == UUID(user_id)
        ))
        return result.scalar_one_or_none()

    @classmethod
    async def get_current_user_ws(cls, db, token: str):
        try:
            payload = token_manager.decode_token(token)
            if not payload or payload.get("type") != "access":
                return None
            user_id = payload.get("sub")
            if not user_id:
                return None
            stmt = (
                select(User)
                .options(selectinload(User.profile))
                .where(User.id == UUID(user_id))
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"[WS AUTH ERROR] {e}", flush=True)
            return None

user_service = UserService()