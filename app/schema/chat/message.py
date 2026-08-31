from pydantic import BaseModel
from typing import Optional
from app.models.chat.messages import MessageEvent

class MessageEventPayload(BaseModel):
    type: str = "chat"
    event: MessageEvent
    message_id: str
    conversation_id: str
    sender_id: str | None = None
    user_id: str | None = None
    username: str | None = None
    display_name:str | None = None
    message: str | None = None
    timestamp: str | None = None
    edited_at: str | None = None
    reply_to: dict | None = None
    reaction: str | None = None
    old_reaction: str | None = None
    media_url: str | None = None
    media_name: str | None = None


from uuid import UUID
from typing import List, Literal

class BulkForwardRequest(BaseModel):
    message_ids: List[UUID]
    target_conversation_ids: List[UUID]

class BulkDeleteRequest(BaseModel):
    message_ids: List[UUID]
    conversation_id: UUID
    delete_type: Literal["for_me", "for_everyone"]

