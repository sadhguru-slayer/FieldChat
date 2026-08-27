from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.router.auth import router as auth_router
from app.router.token import router as token_router
from app.router.user import router as user_router
from app.router.chat import router as chat_router
from app.router.chat import general_chat_router as general_chat_router
from app.router.messages import general_message_router
from app.router.messages import router as message_router
from app.router.profile import profile_router
from app.router.settings import settings_router
from app.ws.sockets import router as MessageRouter
from app.admin import *
from fastadmin import fastapi_app as admin_app
from app.redis_client import r
from app.database import init_db, SessionLocal
from app.services.cache_management.conversation import conversation_cache
from app.redis.subscribers import start_redis_listener
import asyncio

from app.database import init_db
@asynccontextmanager
async def lifespan(app:FastAPI):
# Start the conntection and get the db
    await init_db()

    lock = r.lock(
        "lock:sync_conversation_cache",
        timeout = 300,
        blocking = False
        )
    acquired = await lock.acquire()
    if acquired:
        try:
            async with SessionLocal() as db:
                await conversation_cache.sync_all(db)
        finally:
            await lock.release()
    asyncio.create_task(start_redis_listener())
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Chat-Application",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://fieldchatapp.vercel.app",
        "https://fieldchat.sadguruchenu.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/admin", admin_app)

app.include_router(auth_router)
app.include_router(token_router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(settings_router)
app.include_router(MessageRouter)
app.include_router(message_router)
app.include_router(chat_router)
# app.include_router(general_chat_router)
# app.include_router(general_message_router)

