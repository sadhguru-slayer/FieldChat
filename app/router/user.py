from fastapi import APIRouter,HTTPException, Depends
from app.dependencies import DBSession
from sqlalchemy import select
from app.schema.auth.user import UserResponse, UserRegister
from app.models.auth.user import User, UserRole
from app.services.user import user_service
from app.router.auth import create_username
from app.core.security.password import password_manager
from uuid import UUID
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

from typing import Optional
from app.core.security.auth import oauth2_scheme

@router.get('/get_users_free',response_model=list[UserResponse])
async def get_users_free(db:DBSession):
    stmp = select(User)
    result = await db.execute(stmp)
    users = result.scalars().all()
    return users

@router.get('/get_users', response_model=list[UserResponse])
async def get_users(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    token_user = await user_service.get_current_user(db, token)
    stmt = select(User).where(
        User.id != token_user.id,
        User.role.notin_([UserRole.ADMIN, UserRole.MODERATOR])
    )
    
    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.username.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern))
        )
    
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users

@router.post("/create-admin")
async def create_admin(user_data: UserRegister, db: DBSession):
    existing_user = await user_service.get_user_with_email_or_username(
        db, user_data.email
    )

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=await create_username(db, user_data.email),
        email=user_data.email,
        hashed_password=password_manager.hash_password(user_data.password),
        role=UserRole.ADMIN,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
