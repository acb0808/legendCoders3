# [Arena v2.0] WebSocket & Advanced Features Implementation Plan

> **For Gemini:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Arena system to support real-time interactions (chat, ready check, draw/skip voting) using WebSockets and enforce a single-room policy.

**Architecture:**
- **Backend:** FastAPI WebSockets for real-time state sync. Enhanced `Arena` model for detailed state tracking. `ConnectionManager` for handling room-based broadcasts.
- **Frontend:** `useWebSocket` hook for managing connection. State-driven UI for Lobby/Ready/Playing phases.
- **Protocol:** JSON-based WebSocket messages (e.g., `{ "type": "CHAT", "payload": { ... } }`).

**Tech Stack:** FastAPI, SQLAlchemy, WebSockets, Next.js, React Hooks, Lucide Icons.

---

### Task 1: Database Schema Expansion

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/migrations/versions/add_arena_fields.py` (if using alembic) or manual script

**Step 1: Add new columns to Arena model**
- Add `host_ready` (Boolean, default=False)
- Add `guest_ready` (Boolean, default=False)
- Add `host_surrender` (Boolean, default=False)
- Add `guest_surrender` (Boolean, default=False)
- Add `draw_agreed` (Boolean, default=False)
- Add `skip_agreed` (Boolean, default=False)

**Step 2: Update Pydantic Schemas**
- Update `ArenaResponse` to include these new fields.

**Step 3: Update `create_tables.py`**
- Since we are using `create_tables.py`, we will use it to apply changes (drop/create strategy for dev environment if needed, or just alter table manually).

### Task 2: WebSocket Connection Manager

**Files:**
- Create: `backend/app/websockets/manager.py`

**Step 1: Implement `ConnectionManager` class**
- Methods: `connect`, `disconnect`, `broadcast_to_room`, `send_personal_message`.
- Store connections in `Dict[str, List[WebSocket]]` where key is `arena_id`.
- Handle duplicate connection from same user (kick old one or prevent new one).

### Task 3: Enforce Single Room Policy & Redirect

**Files:**
- Modify: `backend/app/routers/arena.py`
- Modify: `backend/app/crud/arena.py`

**Step 1: Implement `get_active_arena_by_user`**
- Query `Arena` where `(host_id == user_id OR guest_id == user_id)` AND `status` IN (`WAITING`, `READY`, `PLAYING`).

**Step 2: Update `create_arena` and `join_arena`**
- Before creating/joining, check `get_active_arena_by_user`.
- If exists, return 400 or specific code to trigger redirect in FE.

**Step 3: Add `GET /api/arena/active` endpoint**
- Returns the active arena ID for the current user (if any).

### Task 4: WebSocket Event Handlers (Backend Logic)

**Files:**
- Modify: `backend/app/routers/arena.py` (Add WebSocket endpoint)
- Create: `backend/app/services/arena_ws_service.py` (Business logic)

**Step 1: Define WebSocket Endpoint**
- `@router.websocket("/{arena_id}/ws")`
- Validate token (Query param).

**Step 2: Implement Event Handlers**
- `CHAT`: Broadcast message with sender nickname & title.
- `READY`: Update DB `host_ready`/`guest_ready`. If both true -> Broadcast `COUNTDOWN` -> Start Game (DB update) -> Broadcast `START`.
- `SURRENDER`: Mark loser, finish game, broadcast `GAME_OVER`.
- `VOTE_DRAW`: Handle proposal/acceptance. If accepted -> `GAME_OVER` (Draw).
- `VOTE_SKIP`: Handle proposal/acceptance. If accepted -> Change Problem -> Broadcast `PROBLEM_CHANGED`.
- `DISCONNECT`: Handle user disconnect. If host disconnects in lobby -> destroy room. If guest disconnects in lobby -> remove guest. If playing -> mark disconnected (optional timeout logic).

### Task 5: Frontend WebSocket Hook & Context

**Files:**
- Create: `frontend/hooks/use-arena-socket.ts`

**Step 1: Implement Hook**
- Manage `WebSocket` connection.
- Handle `onopen`, `onmessage`, `onclose`, `onerror`.
- Expose methods: `sendMessage`, `sendChat`, `sendReady`, `sendVote`, `sendSurrender`.
- Auto-reconnect logic.

### Task 6: Frontend UI - Room Phase Split

**Files:**
- Modify: `frontend/app/arena/[id]/page.tsx`
- Create: `frontend/components/arena/chat-box.tsx`
- Create: `frontend/components/arena/ready-view.tsx`
- Create: `frontend/components/arena/game-view.tsx`

**Step 1: Implement Chat Box**
- Simple overlay or side panel.
- Display messages with User Title badge.

**Step 2: Implement Ready View (Lobby)**
- Show Host/Guest cards.
- "Ready" button (toggle).
- "Start" countdown overlay (3-2-1).

**Step 3: Implement Game View**
- Integrate existing `PLAYING` UI.
- Add "Surrender", "Draw", "Skip" buttons (with confirmation/status).

**Step 4: Main Page Integration**
- Switch components based on `arena.status`.
- Handle `GAME_OVER` state.
