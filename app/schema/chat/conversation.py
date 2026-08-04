from pydantic import BaseModel
from typing import List
from uuid import UUID

class CreateConversation(BaseModel):
    conversation_name:str | None
    participants : List[str | None]

