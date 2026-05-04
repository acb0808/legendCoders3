# LoL Auction Mini-game Design Document

**Date:** 2026-02-19
**Topic:** League of Legends Esports Auction System
**Tech Stack:** Next.js (App Router), TailwindCSS, Framer Motion, Node.js FS API

## 1. Overview
A standalone web application for managing LoL Esports player auctions. The system supports random player selection via roulette, manual bidding entry, real-time status updates, and a comprehensive admin dashboard.

## 2. Design System: "Hextech & Shadow"
- **Background:** Dark Navy (`#010A13`), Black (`#000000`)
- **Primary Color:** Hextech Gold (`#C89B3C`)
- **Secondary Color:** Magic Blue (`#005A82`)
- **Typography:** Sans-serif with metallic weights (Inter/Spiegel)
- **Effects:** Glassmorphism, Hextech borders, Glow animations for highlights.

## 3. Data Model (`data/db.json`)
```json
{
  "captains": [
    { "id": "c1", "name": "조장A", "points": 1000, "team": [] }
  ],
  "players": [
    { 
      "id": "p1", "name": "플레이어1", "tier": "Challenger", "position": "TOP", "status": "unassigned" 
    }
  ],
  "auctionHistory": [
    { "round": 1, "playerId": "p1", "winnerId": "c1", "bidPrice": 300 }
  ],
  "config": {
    "currentRound": 1,
    "phase": "waiting",
    "activePlayerId": null
  }
}
```

## 4. Key Features
### 4.1. Auction Workflow
1. **Roulette:** Smooth acceleration/deceleration animation to select an unassigned player.
2. **Profile Display:** Large centered player card with tier/position icons.
3. **Bidding:** Modal for entering the winning captain and bid price.
4. **Result:** Updates the captain's team and subtracts points. Marks player as `assigned`.
5. **Skip:** If no one bids, mark player as `skipped` (not assigned to any team).

### 4.2. Status Board
- Real-time list of captains and their recruited players.
- **Drag & Drop:** Use `dnd-kit` or `react-beautiful-dnd` to allow manual team re-assignment.
- Unassigned player pool display at the bottom.

### 4.3. Admin Dashboard
- **Round Recovery:** Reset `currentRound` and revert history.
- **Point Adjustment:** Manually edit captain points.
- **Data Reset:** Wipe all auction results to start fresh.

## 5. Implementation Strategy
- **Backend:** Next.js API Routes (`/api/db`) will handle GET/POST requests to modify the `db.json` file.
- **Frontend State:** `SWR` for data fetching and automatic revalidation.
- **Animations:** `framer-motion` for the roulette and transitions between auction phases.

## 6. Verification Plan
- **Data Integrity:** Ensure points are correctly subtracted and never go below zero (unless forced by admin).
- **Persistence:** Refresh page and verify auction state is maintained via `db.json`.
- **UI/UX:** Check responsiveness and LoL-themed aesthetic consistency.
