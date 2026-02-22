# [Arena Dark Pro] Stability & Design Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the infinite redirection bug, resolve chat visibility issues, and completely overhaul the Arena UI to a professional "Dark Pro" aesthetic.

**Architecture:** 
- **Backend:** Update `handle_disconnect` to use `CANCELLED` status and fix `CHAT` message serialization.
- **Frontend:** Implement strict component cleanup and migrate the layout to a 3-column Bento Grid with Glassmorphism.
- **WebSocket:** Synchronize state using a single source of truth (`ARENA_STATE`).

**Tech Stack:** FastAPI, SQLAlchemy, Next.js, Tailwind CSS v4, Lucide Icons, shadcn/ui.

---

### Task 1: Backend - Disconnection & Chat Reliability

**Files:**
- Modify: `backend/app/services/arena_ws_service.py`

**Step 1: Fix `handle_disconnect` to set `CANCELLED` instead of `DELETE`**
Modify the logic to preserve records but end the match.

**Step 2: Fix `CHAT` message eager loading**
Ensure `models.User.equipped_title` is loaded when broadcasting chat messages.

**Step 3: Verification**
Run server and simulate a host disconnection. Check DB for `CANCELLED` status.

### Task 2: Frontend - Lifecycle & State Sync

**Files:**
- Modify: `frontend/app/arena/[id]/page.tsx`
- Modify: `frontend/hooks/use-arena-socket.ts`

**Step 1: Implement explicit cleanup**
Ensure the WebSocket is closed with code `1000` on component unmount to prevent stale connections.

**Step 2: Fix chat state update**
Verify that `CHAT` messages are correctly appended to the `messages` state in `ArenaBattle`.

**Step 3: Add `draw_agreed` and `skip_agreed` reset logic**
Reset these flags when a problem is changed or game state updates.

### Task 3: UI - Bento Grid Layout Structure

**Files:**
- Modify: `frontend/app/arena/[id]/page.tsx`
- Create: `frontend/components/arena/player-stats-card.tsx`

**Step 1: Create Player Stats Card**
A sleek, vertical card for host/guest with profile info and title badge.

**Step 2: Implement 3-column Layout**
- Left: Players (Sticky)
- Center: Main Action (Countdown or Problem)
- Right: Chat & Log (Sticky)

**Step 3: Styling with Glassmorphism**
Apply `backdrop-blur-xl` and `bg-slate-900/40` to all major containers.

### Task 4: UI - Component Overhaul (Ready & Game Views)

**Files:**
- Modify: `frontend/components/arena/ready-view.tsx`
- Modify: `frontend/components/arena/game-view.tsx`
- Modify: `frontend/components/arena/chat-box.tsx`

**Step 1: Redesign Ready View**
Large, immersive countdown and status indicators.

**Step 2: Redesign Game View**
Focus on the `ProblemDisplay` with a dedicated "Control Center" for Surrender/Draw/Skip.

**Step 3: Polish Chat Box**
Compact, dark theme with colored user titles and auto-scroll.

**Step 4: Final Integration & Build Test**
Run `npm run build` to ensure no regressions.
