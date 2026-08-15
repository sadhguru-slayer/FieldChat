from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.router.auth import router as auth_router
from app.router.token import router as token_router
from app.router.user import router as user_router
from app.router.chat import router as chat_router
from app.router.chat import general_chat_router as general_chat_router
from app.router.messages import general_message_router
from app.router.messages import router as message_router
from app.admin import *
from fastadmin import fastapi_app as admin_app

from app.database import init_db
@asynccontextmanager
async def lifespan(app:FastAPI):
# Start the conntection and get the db
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Chat-Application",
    lifespan=lifespan
)

app.mount("/admin", admin_app)

app.include_router(auth_router)
app.include_router(token_router)
app.include_router(general_chat_router)
app.include_router(general_message_router)
app.include_router(message_router)
app.include_router(user_router)
app.include_router(chat_router)

