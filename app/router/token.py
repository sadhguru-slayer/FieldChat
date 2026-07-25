from fastapi import APIRouter
from app.dependencies import DBSession
from app.models.auth.refresh import RefreshToken
from sqlalchemy import select
router = APIRouter(
    prefix="/api/tokens",
    tags=["Token Management"]
)

@router.get("/")
async def get_all_refresh_rokens(db:DBSession):
    result = await db.execute(select(RefreshToken))
    tokens = result.scalars().all()
    return tokens