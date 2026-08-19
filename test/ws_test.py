import asyncio
import json
import websockets


async def connect():
    user_id = input("User ID: ").strip()

    if not user_id:
        print("User ID is required.")
        return

    url = f"ws://localhost:8000/ws?user_id={user_id}"

    print(f"\nConnecting as {user_id}...")

    try:
        async with websockets.connect(url) as ws:
            print("Connected!")
            print("Type messages. Ctrl+C to exit.\n")

            while True:
                message = await asyncio.to_thread(input, "> ")

                if not message.strip():
                    continue

                await ws.send(json.dumps({
                    "event": "message",
                    "content": message,
                }))

                response = await ws.recv()

                print("←", response)

    except websockets.exceptions.InvalidStatus as e:
        print(f"\nConnection rejected: {e}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"\nConnection closed: {e}")

    except KeyboardInterrupt:
        print("\nDisconnected.")


asyncio.run(connect())
