from datetime import datetime, timedelta
from uuid6 import uuid7
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

auth_service = AuthService()