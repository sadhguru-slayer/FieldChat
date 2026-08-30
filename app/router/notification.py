from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import DBSession
from app.core.security.auth import oauth2_scheme
from app.services.user import user_service
from app.services.notification_service import notification_service
from app.schema.notification import (
    NotificationResponse,
    NotificationUnreadCountResponse,
    SendNotificationRequest,
)

notification_router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


@notification_router.get("", response_model=list[NotificationResponse])
async def get_notifications(
    db: DBSession,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    token: str = Depends(oauth2_scheme),
):
    user = await user_service.get_current_user(db, token)
    notifications = await notification_service.get_user_notifications(
        db,
        user_id=user.id,
        unread_only=unread_only,
        limit=limit,
        skip=skip,
    )
    return notifications


@notification_router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    user = await user_service.get_current_user(db, token)
    count = await notification_service.get_unread_count(db, user_id=user.id)
    return NotificationUnreadCountResponse(unread_count=count)


@notification_router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: UUID,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    user = await user_service.get_current_user(db, token)
    success = await notification_service.mark_as_read(
        db,
        user_id=user.id,
        notification_id=notification_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}


@notification_router.post("/read-all", response_model=dict)
async def mark_all_notifications_read(
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    user = await user_service.get_current_user(db, token)
    await notification_service.mark_as_read(
        db,
        user_id=user.id,
        read_all=True,
    )
    return {"message": "All notifications marked as read"}


@notification_router.post("/send", response_model=dict)
async def send_notification(
    payload: SendNotificationRequest,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    sender = await user_service.get_current_user(db, token)
    
    if payload.user_id:
        result = await notification_service.send_notification(
            db=db,
            user_id=payload.user_id,
            title=payload.title,
            body=payload.body,
            type=payload.type,
            data=payload.data,
        )
        if not result:
            return {"message": "Notification suppressed due to user settings"}
        return {"message": "Notification sent successfully", "id": str(result.id)}
    else:
        await notification_service.broadcast_notification(
            title=payload.title,
            body=payload.body,
            type=payload.type,
            data=payload.data,
        )
        return {"message": "Global notification broadcasted successfully"}

@notification_router.post("/subscribe", response_model=dict)
async def subscribe_push(
    payload: __import__("app.schema.notification", fromlist=["PushSubscriptionRequest"]).PushSubscriptionRequest,
    db: DBSession,
    token: str = Depends(oauth2_scheme),
):
    user = await user_service.get_current_user(db, token)
    # print(f"[DEBUG] [Router] Received push subscription request from user: {user.username} (ID: {user.id})")
    # print(f"[DEBUG] [Router] Endpoint: {payload.endpoint[:60]}...")
    success = await notification_service.save_push_subscription(
        db,
        user_id=user.id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
    )
    # print(f"[DEBUG] [Router] Save subscription success status: {success}")
    return {"message": "Push subscription saved successfully", "success": success}
