from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Enum
from datetime import datetime,timezone
from .base import Base
from .conversations import Conversation
import enum