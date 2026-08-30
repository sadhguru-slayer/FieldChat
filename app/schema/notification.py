from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    body: str
    data: Optional[dict[str, Any]] = None
    is_read: bool
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class SendNotificationRequest(BaseModel):
    user_id: Optional[UUID] = None  # None implies broadcast
    type: NotificationType = NotificationType.SYSTEM
    title: str = Field(..., max_length=255)
    body: str
    data: Optional[dict[str, Any]] = None


class NotificationWSEvent(BaseModel):
    event: str = "notification"
    notification: NotificationResponse


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
