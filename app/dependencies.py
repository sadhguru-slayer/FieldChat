from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from typing import Annotated
from app.database import get_db

DBSession = Annotated[AsyncSession,Depends(get_db)]