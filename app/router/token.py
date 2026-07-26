from fastapi import APIRouter,HTTPException
from app.dependencies import DBSession
from app.models.auth.refresh import RefreshToken
from app.models.auth.user import User
from sqlalchemy import select
from uuid import UUID
from app.services.user import user_service
from app.services.auth import auth_service
from app.core.security.auth import token_manager
router = APIRouter(
    prefix="/api/tokens",
    tags=["Token Management"]
)

@router.get("/")
async def get_all_refresh_rokens(db:DBSession):
    result = await db.execute(select(RefreshToken))
    tokens = result.scalars().all()
    return tokens

@router.post('/refresh_token')
async def refresh_token(db:DBSession,token:str):
    payload = token_manager.verify_refresh_token(token)
    payload = token_manager.verify_token_type(payload,"refresh")
    if not payload:
        raise HTTPException(status_code=401,detail="Token not valid")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    access_token = token_manager.create_access_token(user_id)
    return {"access_token":access_token}


@router.get("/user_refresh_tokens/{user_id}")
async def get_user_refresh_tokens(db:DBSession,user_id:str):
    user = user_service.get_user_with_id(db,user_id)
    if not user:
        raise HTTPException(404,"User not found")
    stmp = select(RefreshToken).where(RefreshToken.user_id == UUID(user_id))
    result = await db.execute(stmp)
    tokens = result.scalars().all()
    return tokens

@router.post("/revoke_refresh_token/{token}")
async def revoke_refresh_token(db:DBSession,token:str):
    refresh = await auth_service.revoke_refresh_token(db,token)
    return {"message":"Token revoked successfuly"}

@router.delete("/delete_refresh_token/{token_id}")
async def delete_refresh_token(db:DBSession,token_id:str):
    token = await auth_service.get_refresh_token(db,token_id)
    if token is None:
        raise HTTPException(404,"Token not found")
    await db.delete(token)
    await db.commit()
    return {"message":"Token deleted successfuly"}

@router.post("/revoke_user_refresh_tokens/{user_id}")
async def revoke_user_refresh_tokens(db:DBSession,user_id:str):
    user = await user_service.get_user_with_id(db,user_id)
    if user is None:
        raise HTTPException(404,"User not found")
    stmp = select(RefreshToken).where(RefreshToken.user_id == UUID(user_id))
    result = await db.execute(stmp)   
    tokens = result.scalars().all()
    if not tokens:
        return {"message":"No sessions available"}
    for token in tokens:
        token.revoked = True
    await db.commit()
    return {"message":"All sessions revoked successfuly"}
