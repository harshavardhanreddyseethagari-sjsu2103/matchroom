# server.py
#
# Adds: live participant LIST (not just count), and typing indicators.
# Both follow the exact same pattern as everything before: server holds
# the truth, server broadcasts it, clients just render whatever they're told.

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import json
import uuid

app = FastAPI()


@app.get("/")
def serve_page():
    return FileResponse("static/index.html")


rooms: dict[str, list[WebSocket]] = {}
client_info: dict[WebSocket, dict] = {}

# ── Message history ─────────────────────────────────────────────
# A plain dict mapping room name -> list of past messages (as dicts).
# This is INTENTIONALLY simple: it lives in server memory, so it
# survives a page REFRESH (the browser reconnects, asks for history,
# gets it) but NOT a server restart (this list is wiped if the Python
# process restarts — e.g. a Render redeploy). A real production system
# would back this with a real database (Postgres, Redis) instead.
# For this project, this is an honest, clearly-scoped simplification.
message_history: dict[str, list[dict]] = {}

MAX_HISTORY_PER_ROOM = 50   # cap memory growth — don't store unlimited messages forever


async def broadcast_to_room(room_name: str, message: dict):
    if room_name not in rooms:
        return
    payload = json.dumps(message)
    for client in rooms[room_name][:]:
        try:
            await client.send_text(payload)
        except Exception:
            if client in rooms[room_name]:
                rooms[room_name].remove(client)


def get_usernames_in_room(room_name: str) -> list[str]:
    """
    Looks up the username for every WebSocket currently in a room.
    This is why we keep client_info (websocket -> {room, username}) —
    rooms only stores the connection objects themselves, not names,
    so we cross-reference here whenever we need the actual name list.
    """
    if room_name not in rooms:
        return []
    return [client_info[ws]["username"] for ws in rooms[room_name] if ws in client_info]


@app.websocket("/ws/{room_name}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, username: str):
    await websocket.accept()

    rooms.setdefault(room_name, []).append(websocket)
    client_info[websocket] = {"room": room_name, "username": username}

    print(f"{username} joined room '{room_name}'. Room size: {len(rooms[room_name])}")

    # Send this NEW client (only them, not the whole room) the existing
    # message history for this room, BEFORE telling everyone they joined.
    # This is websocket.send_text() directly — not broadcast_to_room() —
    # because this message is meant for exactly one person.
    history = message_history.get(room_name, [])
    await websocket.send_text(json.dumps({
        "type": "history",
        "messages": history
    }))

    await broadcast_to_room(room_name, {
        "type": "system",
        "text": f"{username} joined the room.",
        "participant_count": len(rooms[room_name]),
        "participants": get_usernames_in_room(room_name),
    })

    try:
        while True:
            # Messages are now JSON from the CLIENT too, not just the
            # server. We need this because we now have TWO kinds of
            # things a client can send: a chat message, or "I'm typing."
            # A plain string can't distinguish those — JSON with a
            # "type" field can.
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data["type"] == "chat":
                print(f"[{room_name}] {username}: {data['text']}")

                chat_message = {
                    "type": "chat",
                    "message_id": str(uuid.uuid4()),   # unique ID — reactions attach to this
                    "username": username,
                    "text": data["text"],
                    "reactions": {}   # e.g. {"🔥": ["harsha", "alex"], "😬": ["sam"]}
                }

                # Save to history BEFORE broadcasting, so the order
                # stored matches the order seen live.
                message_history.setdefault(room_name, []).append(chat_message)
                # Trim to the most recent MAX_HISTORY_PER_ROOM messages
                # only — this is a simple memory cap, not anything fancy.
                message_history[room_name] = message_history[room_name][-MAX_HISTORY_PER_ROOM:]

                await broadcast_to_room(room_name, chat_message)

            elif data["type"] == "reaction":
                # Expected shape: {"type": "reaction", "message_id": "...", "emoji": "🔥"}
                message_id = data["message_id"]
                emoji = data["emoji"]

                # Find the actual message object in history and mutate
                # ITS reactions dict directly — this is the server's
                # permanent record, shared by everyone, not a per-client
                # visual-only effect.
                target_message = None
                for msg in message_history.get(room_name, []):
                    if msg.get("message_id") == message_id:
                        target_message = msg
                        break

                if target_message is not None:
                    target_message["reactions"].setdefault(emoji, [])

                    # Toggle behavior: reacting again with the same emoji
                    # removes your own reaction instead of adding a duplicate.
                    if username in target_message["reactions"][emoji]:
                        target_message["reactions"][emoji].remove(username)
                        if len(target_message["reactions"][emoji]) == 0:
                            del target_message["reactions"][emoji]
                    else:
                        target_message["reactions"][emoji].append(username)

                    await broadcast_to_room(room_name, {
                        "type": "reaction_update",
                        "message_id": message_id,
                        "reactions": target_message["reactions"]
                    })

            elif data["type"] == "typing":
                # Broadcast a typing notice to the room. We deliberately
                # do NOT echo this back to the sender on the frontend
                # (handled client-side) — you don't need to see "you are
                # typing" about yourself.
                await broadcast_to_room(room_name, {
                    "type": "typing",
                    "username": username
                })

            elif data["type"] == "stop_typing":
                await broadcast_to_room(room_name, {
                    "type": "stop_typing",
                    "username": username
                })

    except WebSocketDisconnect:
        rooms[room_name].remove(websocket)
        del client_info[websocket]

        print(f"{username} left room '{room_name}'. Room size: {len(rooms[room_name])}")

        await broadcast_to_room(room_name, {
            "type": "system",
            "text": f"{username} left the room.",
            "participant_count": len(rooms[room_name]),
            "participants": get_usernames_in_room(room_name),
        })

        if len(rooms[room_name]) == 0:
            del rooms[room_name]