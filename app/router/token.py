from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from app.dependencies import DBSession
from app.models.auth.refresh import RefreshToken
from app.models.auth.user import User
from sqlalchemy import select
from uuid import UUID
from app.services.user import user_service
from app.services.auth import auth_service
from app.core.security.auth import token_manager, oauth2_scheme

router = APIRouter(
    prefix="/api/tokens",
    tags=["Token Management"]
)

def serialize_token(t: RefreshToken) -> dict:
    return {
        "id": str(t.id),
        "user_id": str(t.user_id),
        "device_name": t.device_name,
        "device_id": getattr(t, "device_id", None),
        "ip_address": t.ip_address,
        "expires_at": t.expires_at.isoformat() if t.expires_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "revoked": t.revoked,
    }

@router.get("/me")
async def get_my_refresh_tokens(
    req: Request,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    device_id = req.headers.get("x-device-id")
    current_user = await user_service.get_current_user(db, token, device_id=device_id)
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked.is_(False)
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    return [serialize_token(t) for t in tokens]

@router.post("/me/revoke-all")
async def revoke_all_my_tokens(
    db: DBSession,
    token: str = Depends(oauth2_scheme)
):
    current_user = await user_service.get_current_user(db, token)
    await auth_service.revoke_all_user_sessions(db, current_user.id)
    return {"message": "All sessions revoked successfully"}

@router.delete("/me/{token_id}")
async def delete_my_refresh_token(
    token_id: str,
    db: DBSession,
    token: str = Depends(oauth2_scheme)
):
    current_user = await user_service.get_current_user(db, token)
    await auth_service.revoke_token_by_id(db, token_id, user_id=current_user.id)
    return {"message": "Session token deleted successfully"}

from sqlalchemy import delete

@router.delete("/hard-delete/{token_id}")
async def hard_delete_my_refresh_token(
    user_id:str,
    db: DBSession,
):
    current_user = await user_service.get_user_with_id(db, user_id)
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == current_user.id
        )
    )
    await db.commit()
    return {"message": "Session tokens deleted successfully"}

# ── Existing Endpoints ────────────────────────────────────────────────────────
@router.get("/")
async def get_all_refresh_tokens(db: DBSession):
    result = await db.execute(select(RefreshToken))
    tokens = result.scalars().all()
    return [serialize_token(t) for t in tokens]

@router.post('/refresh_token')
async def refresh_token(db: DBSession, token: str):
    payload = token_manager.verify_refresh_token(token)
    payload = token_manager.verify_token_type(payload, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Token not valid")
    
    refresh_record = await auth_service.get_refresh_token_by_hash(db, token)
    if not refresh_record or refresh_record.revoked or (refresh_record.expires_at and refresh_record.expires_at < datetime.utcnow()):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked or expired")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    access_token = token_manager.create_access_token(user_id)
    return {"access_token": access_token}

@router.get("/user_refresh_tokens/{user_id}")
async def get_user_refresh_tokens(db: DBSession, user_id: str):
    user = await user_service.get_user_with_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    stmt = select(RefreshToken).where(RefreshToken.user_id == UUID(user_id))
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    return [serialize_token(t) for t in tokens]

@router.post("/revoke_refresh_token/{token}")
async def revoke_refresh_token(db: DBSession, token: str):
    refresh = await auth_service.revoke_refresh_token(db, token)
    return {"message": "Token revoked successfully"}

@router.delete("/delete_refresh_token/{token_id}")
async def delete_refresh_token(db: DBSession, token_id: str):
    await auth_service.revoke_token_by_id(db, token_id)
    return {"message": "Token deleted successfully"}

@router.post("/revoke_user_refresh_tokens/{user_id}")
async def revoke_user_refresh_tokens(db: DBSession, user_id: str):
    user = await user_service.get_user_with_id(db, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    await auth_service.revoke_all_user_sessions(db, user_id)
    return {"message": "All sessions revoked successfully"}



