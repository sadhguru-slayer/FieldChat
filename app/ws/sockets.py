from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect
from app.database import SessionLocal
from app.services.user import user_service
from app.ws.manager import manager
from app.services.cache_management.conversation import conversation_cache
router = APIRouter()

@router.websocket("/ws")
async def web_socket_endpoint(
    ws: WebSocket,
    # token : str = Query(...),
    user_id:str
    ):

    async with SessionLocal() as db:
        # user = await user_service.get_current_user_ws(db, token)
        user = await user_service.get_user_with_id_ws(db, user_id)

    if not user:
        await ws.close(code = 1000)
        return

    await manager.connect(str(user.id), user.username, ws)

    conversation_ids = await conversation_cache.get_user_conversations(str(user.id))

    for conv_id in conversation_ids:
        await manager.join_conversation(
            conv_id,str(user.id),ws
        )
    try:
        while True:
            data = await ws.receive_json()
            
            
            await ws.send_json({
                "event": "received",
                "data": data,
            })
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(
            user.id,
            ws
        )
    
