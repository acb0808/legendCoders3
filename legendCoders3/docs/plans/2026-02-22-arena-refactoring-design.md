# Arena Dark Pro: Refactoring Design Document

**Date:** 2026-02-22
**Status:** Approved
**Topic:** Fixing redirection bugs, chat issues, and UI/UX overhaul.

## 1. 🎯 Goals
- Eliminate the "infinite redirection" loop by properly handling match cancellations.
- Fix the real-time chat system to ensure messages are displayed instantly with user titles.
- Upgrade the Arena UI to a professional, high-performance "Dark Pro" aesthetic using Bento Grid and Glassmorphism.

## 2. 🛠️ Technical Architecture

### 2.1. Backend: State Management & Data Loading
- **Match Abandonment**: Modify `handle_disconnect` in `arena_ws_service.py` to set the arena status to `CANCELLED` instead of deleting the record. This allows `/api/arena/active` to accurately filter out dead rooms.
- **Eager Loading for Chat**: Ensure `CHAT` message handling fetches the full `User` object with `joinedload(models.User.equipped_title)` to prevent missing title badges in broadcasts.
- **Broadcast Isolation**: Every message type (`CHAT`, `ARENA_STATE`, `GAME_OVER`) must be sanitized using `jsonable_encoder` and sent after closing any active DB session to prevent pool leaks.

### 2.2. Frontend: State & WebSocket Lifecycle
- **Clean Unmount**: Implement a strict cleanup in `useArenaSocket` and `ArenaBattle` page to close the socket with code `1000` and reset local states when navigating away.
- **Unified State**: Use a single `arena` state that reacts to `ARENA_STATE` messages to keep the UI perfectly synced with the backend.

## 3. 🎨 Visual Design: "Arena Dark Pro"

### 3.1. Layout: Bento Grid
- **Global Structure**: 3-column layout on desktop.
    - **Left (Players)**: Stacked profile cards showing host and guest with neon borders for "Ready" status.
    - **Center (Action)**: Dynamic view switching between a countdown lobby and a focused problem viewer.
    - **Right (Social)**: High-density chat box with title badges and system logs.

### 3.2. Aesthetic: Glassmorphism
- **Background**: Deep Slate/Navy gradient (`#020617` to `#0f172a`).
- **Surface**: `bg-slate-900/40` with `backdrop-blur-xl` and `border-white/10`.
- **Typography**: Restore bold weights by removing `antialiased` and ensuring `Geist` font is correctly applied via Tailwind v4 variables.

## 4. ✅ Success Criteria
- [ ] Users can leave an arena and return to the lobby without being redirected back.
- [ ] Chat messages appear instantly for both players with correct titles.
- [ ] The transition from lobby to game is smooth with a visual 3-2-1 countdown.
- [ ] The UI looks modern, premium, and specifically designed for competitive programming.
