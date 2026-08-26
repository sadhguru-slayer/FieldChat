from datetime import datetime, timedelta
import hashlib
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from user_agents import parse

from app.config import settings
from app.core.security.auth import token_manager
from app.models.auth.refresh import RefreshToken


class AuthService:
    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def get_device_info(self, user_agent: str | None) -> str:
        if not user_agent:
            return "Unknown device"
        ua = parse(user_agent)
        return f"{ua.os.family} - {ua.browser.family}"

    async def store_refresh_token(
        self,
        db,
        user_id: UUID | str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_id: str | None = None,
    ) -> str:
        user_uuid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        raw_token = token_manager.create_refresh_token(str(user_uuid))
        token_hash = self.hash_refresh_token(raw_token)
        device_name = self.get_device_info(user_agent)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        existing = None
        if device_id:
            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_uuid,
                    RefreshToken.device_id == device_id,
                )
            )
            existing = result.scalars().first()

        if existing:
            existing.token_hash = token_hash
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
            existing.ip_address = ip_address
            existing.device_name = device_name
            existing.revoked = False
        else:
            refresh = RefreshToken(
                user_id=user_uuid,
                token_hash=token_hash,
                ip_address=ip_address,
                device_name=device_name,
                device_id=device_id,
                expires_at=expires_at,
            )
            db.add(refresh)

        await db.commit()
        return raw_token

    async def get_refresh_token_by_id(self, db, token_id: UUID | str):
        uuid_id = UUID(str(token_id)) if isinstance(token_id, str) else token_id
        stmt = select(RefreshToken).where(RefreshToken.id == uuid_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_refresh_token_with_id(self, db, token_id: UUID | str):
        return await self.get_refresh_token_by_id(db, token_id)

    async def get_refresh_token_by_hash(self, db, token: str):
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == self.hash_refresh_token(token)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_refresh_token(self, db, token: str):
        return await self.get_refresh_token_by_hash(db, token)

    async def revoke_refresh_token(self, db, token: str):
        refresh = await self.get_refresh_token_by_hash(db, token)
        if not refresh:
            raise HTTPException(status_code=401, detail="Refresh token not found")
        if refresh.revoked:
            raise HTTPException(status_code=401, detail="Refresh token already revoked")
        if refresh.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Refresh token expired")
        refresh.revoked = True
        await db.commit()
        return refresh

    async def revoke_token_by_id(self, db, token_id: UUID | str, user_id: UUID | str | None = None):
        token = await self.get_refresh_token_by_id(db, token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        if user_id:
            user_uuid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
            if token.user_id != user_uuid:
                raise HTTPException(status_code=404, detail="Token not found")
        token.revoked = True
        await db.commit()
        return token

    async def revoke_all_user_sessions(self, db, user_id: UUID | str):
        user_uuid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_uuid)
        result = await db.execute(stmt)
        tokens = result.scalars().all()
        if not tokens:
            return False
        for t in tokens:
            t.revoked = True
        await db.commit()
        return True


auth_service = AuthService()