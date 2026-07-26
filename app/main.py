from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.router.auth import router as auth_router
from app.router.token import router as token_router
from app.router.user import router as user_router
from app.router.chat import router as chat_router
from app.database import init_db
@asynccontextmanager
async def lifespan(app:FastAPI):
# Start the conntection and get the db
    yield
    await init_db()
    # Shutdown
    pass

app = FastAPI(
    title="Chat-Application",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(token_router)
app.include_router(user_router)
app.include_router(chat_router)
