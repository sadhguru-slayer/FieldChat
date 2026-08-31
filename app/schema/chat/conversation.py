from pydantic import BaseModel
from typing import List
from uuid import UUID

class CreateConversation(BaseModel):
    conversation_name:str | None
    participants : List[str | None]

class ConversationPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    avatar_url: str | None = None