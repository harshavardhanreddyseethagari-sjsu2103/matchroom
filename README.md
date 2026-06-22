# Match Room — Real-Time Watch Party Chat

A live, multi-room chat app built around WebSockets — join a room for a
specific match, chat in real time with everyone else watching, see who's
online, react to messages, and pick up right where you left off on refresh.

**Live demo:** _add your Render URL here once deployed_

## What this project covers

| Feature | What's happening under the hood |
|---|---|
| Real-time messaging | A WebSocket connection stays open per user — the server pushes messages instantly, no polling, no refresh |
| Rooms | Connections are grouped by room name; broadcasts only reach clients in the same room |
| Live participant list | The server is the single source of truth for who's in a room — broadcast on every join/leave, never guessed client-side |
| Typing indicators | Debounced client-side events (`typing` / `stop_typing`) broadcast to the room, auto-clearing after a pause |
| Message history | An in-memory per-room message log replayed to any client that joins or refreshes |
| Reactions | Emoji reactions attached to a specific message by ID, toggled on/off, stored server-side, broadcast live to everyone |
| Session persistence | `sessionStorage` (per-tab) remembers your room/username across a refresh, without merging identities across multiple open tabs |

## Architecture notes / honest limitations

- **Message history is in-memory**, not a database. It survives a page
  refresh (the server still has it) but NOT a server restart (e.g. a
  Render redeploy wipes it). A production version would back this with
  Postgres or Redis.
- **No authentication** — usernames are self-declared, not verified.
  Anyone can claim any name. This is intentional scope for this project;
  a real product would need actual auth.
- **sessionStorage, not localStorage**, for session persistence —
  deliberately chosen so multiple tabs (e.g. testing as two different
  users at once) don't collide and overwrite each other's identity.

## Running locally

```bash
uvicorn server:app --reload
# visit http://127.0.0.1:8000/
```

## Running with Docker

```bash
docker build -t matchroom .
docker run -p 8000:8000 matchroom
```