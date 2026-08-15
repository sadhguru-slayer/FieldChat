from app.models.chat.participants import ConversationParticipant, ParticipantRole
from sqlalchemy import select

from datetime import timezone,datetime
import json

from sqlalchemy import select

from app.ws.manager import manager
# from app.ws.events import WSMessageEvent

from app.models.messages import Message,MessageDeleteState


from app.redis_client import r

from app.dependencies.db import db_session

class MessageService:
    def __init__(self, db):
        self.db = db
    async def MessageCreate(self, user, data):
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            return
        
        pass