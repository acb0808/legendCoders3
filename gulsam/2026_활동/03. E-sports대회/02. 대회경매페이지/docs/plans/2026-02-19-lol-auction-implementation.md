# LoL Auction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a standalone LoL auction mini-game with Next.js, featuring a roulette, bidding system, and admin dashboard.

**Architecture:** Next.js App Router for frontend and API. Use Node.js `fs` for a local JSON database. Framer Motion for animations.

**Tech Stack:** Next.js 15+, TypeScript, TailwindCSS, Framer Motion, Lucide React, dnd-kit.

---

### Task 1: Project Scaffolding

**Step 1: Scaffold Next.js project**
Run: `npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --yes`

**Step 2: Install additional dependencies**
Run: `npm install framer-motion lucide-react @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities swr`

**Step 3: Commit**
```bash
git add .
git commit -m "chore: scaffold project and install dependencies"
```

### Task 2: Data & API Layer

**Files:**
- Create: `data/db.json`
- Create: `src/lib/db.ts`
- Create: `src/app/api/db/route.ts`

**Step 1: Create initial db.json with sample data**
Create `data/db.json` with 4 captains and 20 sample players.

**Step 2: Create DB utility in lib/db.ts**
Implement `readDb` and `writeDb` using `fs/promises`.

**Step 3: Create API route in app/api/db/route.ts**
Handle GET (read all) and POST (update specific fields).

**Step 4: Commit**
```bash
git add data/db.json src/lib/db.ts src/app/api/db/route.ts
git commit -m "feat: setup file-based database and API route"
```

### Task 3: Core UI Components - Layout & Theme

**Files:**
- Modify: `src/app/globals.css`
- Modify: `src/app/layout.tsx`
- Create: `src/components/layout/Navbar.tsx`

**Step 1: Apply LoL-themed global styles**
Update `globals.css` with dark background (`#010A13`) and Hextech colors.

**Step 2: Create Hextech-styled Navbar**
Include navigation between "Auction", "Board", and "Admin".

**Step 3: Commit**
```bash
git add src/app/globals.css src/app/layout.tsx src/components/layout/Navbar.tsx
git commit -m "style: apply LoL Hextech theme and layout"
```

### Task 4: Auction Phase 1 - Roulette

**Files:**
- Create: `src/components/auction/Roulette.tsx`
- Create: `src/app/page.tsx` (Main Auction Page)

**Step 1: Implement Roulette component**
Use `framer-motion` for a sliding/cycling effect of player names.

**Step 2: Integrate Roulette into Main Page**
Add a "Start Selection" button that triggers the roulette.

**Step 3: Commit**
```bash
git add src/components/auction/Roulette.tsx src/app/page.tsx
git commit -m "feat: implement player selection roulette"
```

### Task 5: Auction Phase 2 - Bidding Modal

**Files:**
- Create: `src/components/auction/BiddingModal.tsx`
- Create: `src/components/auction/PlayerProfile.tsx`

**Step 1: Create PlayerProfile display**
Large card showing Tier icon, Position, and Name.

**Step 2: Implement BiddingModal**
Dropdown to select Captain, input for Points, and "Confirm" button.

**Step 3: Update DB on Bidding Confirmation**
Call POST `/api/db` to assign player and deduct points.

**Step 4: Commit**
```bash
git add src/components/auction/BiddingModal.tsx src/components/auction/PlayerProfile.tsx
git commit -m "feat: add player profile and bidding modal"
```

### Task 6: Status Board with Drag & Drop

**Files:**
- Create: `src/app/board/page.tsx`
- Create: `src/components/board/CaptainTeamCard.tsx`

**Step 1: Build Board layout**
Grid of captains showing their current team members.

**Step 2: Implement Drag & Drop with dnd-kit**
Allow moving player tags between Captain cards.

**Step 3: Commit**
```bash
git add src/app/board/page.tsx src/components/board/CaptainTeamCard.tsx
git commit -m "feat: implement status board with drag & drop"
```

### Task 7: Admin Dashboard

**Files:**
- Create: `src/app/admin/page.tsx`

**Step 1: Round Control**
Buttons to set `currentRound` and list `auctionHistory` for deletion.

**Step 2: Point & Data Management**
Form to edit captain points and a "Reset All" button.

**Step 3: Commit**
```bash
git add src/app/admin/page.tsx
git commit -m "feat: implement admin dashboard"
```

### Task 8: Final Polish & Verification

**Step 1: Add sound effects (optional) and visual polish**
Hextech borders, glow effects on winner.

**Step 2: Final testing**
Test the full cycle: Roulette -> Bid -> Board -> Admin Reset.

**Step 3: Commit**
```bash
git commit -m "refactor: final polish and bug fixes"
```
