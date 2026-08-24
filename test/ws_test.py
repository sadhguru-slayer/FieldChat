import asyncio
import json
import websockets


class MessageEvent:
    MESSAGE_CREATED = "message.created"
    MESSAGE_EDITED = "message.edited"
    MESSAGE_DELETED_FOR_ME = "message.deleted_for_me"
    MESSAGE_DELETED_FOR_EVERYONE = "message.deleted_for_everyone"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_READ = "message.read"
    MESSAGE_REACTION_ADDED = "message.reaction_added"
    MESSAGE_REACTION_REMOVED = "message.reaction_removed"


EVENTS = {
    "1": MessageEvent.MESSAGE_CREATED,
    "2": MessageEvent.MESSAGE_EDITED,
    "3": MessageEvent.MESSAGE_DELETED_FOR_ME,
    "4": MessageEvent.MESSAGE_DELETED_FOR_EVERYONE,
    "5": MessageEvent.MESSAGE_READ,
    "6": MessageEvent.MESSAGE_REACTION_ADDED,
    "7": MessageEvent.MESSAGE_REACTION_REMOVED,
}

"""
# This is group
CONVERSATION_ID = "01a006b6-1968-7d35-bdb9-3b76b6047713"
"""

# This is DM
CONVERSATION_ID = "01a00a48-4531-7d6d-96c5-2bc0ca6db513"

def show_options():
    print("\n1: Create\n2: Edit\n3: DeleteMe\n4: DeleteEveryone\n5: Read\n6: Add Reaction\n7: Remove Reaction\nexit: Disconnect\n")


async def send_event(ws, user_id, conversation_id, event, content=None, message_id=None, reaction=None):
    data = {"event": event, "user_id": user_id, "conversation_id": conversation_id}
    if content is not None: data["content"] = content
    if message_id is not None: data["message_id"] = message_id
    if reaction is not None: data["reaction"] = reaction
    await ws.send(json.dumps(data))


async def create_message(ws, user_id, conversation_id, content):
    content = content.strip()
    if content:
        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_CREATED, content=content)


async def handle_option(ws, user_id, conversation_id, option):
    if option == "1":
        content = input("Message: ").strip()
        if not content:
            print("Message cannot be empty.")
            return
        await create_message(ws, user_id, conversation_id, content)

    elif option == "2":
        message_id = input("Message ID: ").strip()
        content = input("New content: ").strip()
        if not message_id:
            print("Message ID is required.")
            return
        if not content:
            print("New content cannot be empty.")
            return
        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_EDITED, content=content, message_id=message_id)

    elif option in ("3", "4"):
        message_id = input("Message ID: ").strip()
        if not message_id:
            print("Message ID is required.")
            return
        event = MessageEvent.MESSAGE_DELETED_FOR_ME if option == "3" else MessageEvent.MESSAGE_DELETED_FOR_EVERYONE
        await send_event(ws, user_id, conversation_id, event, message_id=message_id)

    elif option == "5":
        message_id = input("Message ID to read: ").strip()
        if not message_id:
            print("Message ID is required.")
            return
        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_READ, message_id=message_id)

    elif option == "6":
        message_id = input("Message ID: ").strip()
        reaction = input("Reaction: ").strip()
        if not message_id:
            print("Message ID is required.")
            return
        if not reaction:
            print("Reaction is required.")
            return
        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_REACTION_ADDED, message_id=message_id, content=reaction)

    elif option == "7":
        message_id = input("Message ID: ").strip()
        if not message_id:
            print("Message ID is required.")
            return
        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_REACTION_REMOVED, message_id=message_id)


def format_message(data):
    event = data.get("event")
    message_id = data.get("message_id")
    username = data.get("username") or "Unknown"
    message = data.get("message") or ""
    timestamp = data.get("timestamp") or ""

    if event == MessageEvent.MESSAGE_CREATED:
        print(f"\n📨 {username}: {message}")
        if message_id: print(f"ID: {message_id}")
        if timestamp: print(f"Time: {timestamp}")

    elif event == MessageEvent.MESSAGE_EDITED:
        print(f"\n✎ EDITED [{message_id}] {message}")

    elif event == MessageEvent.MESSAGE_REACTION_ADDED:
        print(f"\n❤️ REACTION [{message_id}] {data.get('reaction')} by {data.get('user_id')}")

    elif event == MessageEvent.MESSAGE_REACTION_REMOVED:
        print(f"\n💔 REACTION REMOVED [{message_id}] by {data.get('user_id')}")

    elif event == MessageEvent.MESSAGE_DELETED_FOR_ME:
        print(f"\n🗑 DELETED FOR YOU [{message_id}]")

    elif event == MessageEvent.MESSAGE_DELETED_FOR_EVERYONE:
        print(f"\n🗑 DELETED FOR EVERYONE [{message_id}]")

    elif event == MessageEvent.MESSAGE_DELIVERED:
        print(f"\n✓✓ DELIVERED [{message_id}]")

    elif event == MessageEvent.MESSAGE_READ:
        print(f"\n✓✓ READ [{message_id}]")

    else:
        print(f"\n← {event}")
        print(json.dumps(data, indent=2))


async def receive_messages(ws, user_id):
    try:
        while True:
            response = await ws.recv()
            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                print(response)
                continue

            event = data.get("event")
            sender_id = data.get("sender_id")
            message_id = data.get("message_id")
            conversation_id = data.get("conversation_id")

            if event == MessageEvent.MESSAGE_CREATED:
                if str(sender_id) != str(user_id):
                    format_message(data)
                    if message_id and conversation_id:
                        await send_event(ws, user_id, conversation_id, MessageEvent.MESSAGE_DELIVERED, message_id=message_id)
                continue

            format_message(data)

    except websockets.exceptions.ConnectionClosed:
        return


async def connect():
    user_id = input("User ID: ").strip()
    if not user_id:
        print("User ID is required.")
        return

    conversation_id = CONVERSATION_ID
    url = f"ws://localhost:8000/ws?user_id={user_id}"

    print(f"\nConnecting as {user_id}...")

    try:
        async with websockets.connect(url) as ws:
            print("\nConnected!")
            print("Type a message to send.")
            print("Type OSHOW for advanced options.")
            print("Type exit to disconnect.\n")

            receiver_task = asyncio.create_task(receive_messages(ws, user_id))

            try:
                while True:
                    option = (await asyncio.to_thread(input, "> ")).strip()
                    if not option:
                        continue

                    if option.lower() == "oshow":
                        show_options()
                    elif option.lower() == "exit":
                        print("\nDisconnecting...")
                        break
                    elif option in EVENTS:
                        await handle_option(ws, user_id, conversation_id, option)
                    else:
                        await create_message(ws, user_id, conversation_id, option)

            finally:
                receiver_task.cancel()
                try:
                    await receiver_task
                except asyncio.CancelledError:
                    pass

    except websockets.exceptions.InvalidStatus as e:
        print(f"\nConnection rejected: {e}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\nConnection closed: {e}")
    except KeyboardInterrupt:
        print("\nDisconnected.")


asyncio.run(connect())
