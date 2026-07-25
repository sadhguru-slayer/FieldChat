from datetime import datetime, timedelta
from sqlalchemy import select
from uuid6 import uuid7
from fastapi import HTTPException
from uuid import UUID
from jose import jwt
from app.config import settings
import hashlib
from app.models.auth.refresh import RefreshToken
from app.core.security.auth import token_manager
from user_agents import parse

class AuthService:
    def hash_refresh_token(self,token:str)->str:
        return hashlib.sha256(
            token.encode()
        ).hexdigest()

    def get_device_info(self,user_agent:str | None):
        if not user_agent:
            return "Unknown device"
        ua = parse(user_agent)

        return f"{ua.os.family} - {ua.browser.family}"

    async def store_refresh_token(self,db,user_id:str,ip_address:str,user_agent:str):
        token = token_manager.create_refresh_token(str(user_id))

        device = self.get_device_info(user_agent)
        refresh = RefreshToken(
            user_id = user_id,
            token_hash = self.hash_refresh_token(token),
            ip_address=ip_address,
            device_name=device,
            expires_at = datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
        db.add(refresh)
        await db.commit()
        return token
    async def get_refresh_token(self,db,token_id:str):
        stmp = select(RefreshToken).where(RefreshToken.id == UUID(token_id))
        result = await db.execute(stmp)
        token = result.scalar_one_or_none()
        return token
    async def get_refresh_token(self,db,token:str):
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == self.hash_refresh_token(token)))
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self,db,token:str):
        refresh = await self.get_refresh_token(db,token)
        if not refresh:
            raise HTTPException(status_code=401,detail="Refresh token not found")
        if refresh.revoked:
            raise HTTPException(status_code=401,detail="Refresh token already revoked")
        if refresh.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401,detail="Refresh token expired")
        refresh.revoked=True
        await db.commit()
        return refresh

auth_service = AuthService()