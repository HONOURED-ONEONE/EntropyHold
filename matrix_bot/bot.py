import os
import asyncio
import httpx
from dotenv import load_dotenv
from nio import AsyncClient, MatrixRoom, RoomMessageText

load_dotenv()

HOMESERVER_URL = os.environ.get("MATRIX_HOMESERVER_URL")
ACCESS_TOKEN = os.environ.get("MATRIX_ACCESS_TOKEN")
ROOM_ID = os.environ.get("MATRIX_ROOM_ID")
HONEYPOT_BASE_URL = os.environ.get("HONEYPOT_BASE_URL")
HONEYPOT_API_KEY = os.environ.get("HONEYPOT_API_KEY")

async def main():
    if not all([HOMESERVER_URL, ACCESS_TOKEN, ROOM_ID, HONEYPOT_BASE_URL]):
        print("Missing required environment variables. Ensure MATRIX_HOMESERVER_URL, MATRIX_ACCESS_TOKEN, MATRIX_ROOM_ID, HONEYPOT_BASE_URL are set.")
        return

    client = AsyncClient(HOMESERVER_URL)
    client.access_token = ACCESS_TOKEN

    # Fetch user_id to ignore our own messages
    async with httpx.AsyncClient() as http_client:
        try:
            r = await http_client.get(
                f"{HOMESERVER_URL}/_matrix/client/v3/account/whoami",
                headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                timeout=10.0
            )
            if r.status_code == 200:
                client.user_id = r.json().get("user_id")
                print(f"Authenticated as {client.user_id}")
            else:
                print(f"Failed to fetch whoami. Status: {r.status_code}")
        except Exception as e:
            print(f"Warning: Failed to fetch whoami: {e}")

    api_endpoint = f"{HONEYPOT_BASE_URL.rstrip('/')}/api/honeypot"

    async def message_callback(room: MatrixRoom, event: RoomMessageText) -> None:
        if room.room_id != ROOM_ID:
            return
        if client.user_id and event.sender == client.user_id:
            return

        body = event.body
        payload = {
            "sessionId": f"matrix:{ROOM_ID}:{event.sender}",
            "message": {"sender": "scammer", "text": body, "timestamp": 0},
            "conversationHistory": [],
            "metadata": {
                "channel": "Matrix",
                "roomId": ROOM_ID,
                "provider": "Matrix"
            }
        }
        
        headers = {}
        if HONEYPOT_API_KEY:
            headers["x-api-key"] = HONEYPOT_API_KEY

        async with httpx.AsyncClient() as http_client:
            try:
                # Forward to Honeypot API
                res = await http_client.post(api_endpoint, json=payload, headers=headers, timeout=15.0)
                if res.status_code == 200:
                    data = res.json()
                    reply = data.get("reply")
                    if reply:
                        # Send reply back to the Matrix room
                        await client.room_send(
                            room_id=ROOM_ID,
                            message_type="m.room.message",
                            content={
                                "msgtype": "m.text",
                                "body": reply
                            }
                        )
                else:
                    print(f"API returned status {res.status_code}: {res.text}")
            except Exception as e:
                print(f"Failed to process message: {e}")

    client.add_event_callback(message_callback, RoomMessageText)

    print(f"Joining {ROOM_ID}...")
    try:
        await client.join(ROOM_ID)
        print(f"Joined {ROOM_ID} successfully.")
    except Exception as e:
        print(f"Join attempt failed or already joined: {e}")
    
    print("Starting sync loop...")
    await client.sync_forever(timeout=30000, full_state=True)

if __name__ == "__main__":
    asyncio.run(main())
