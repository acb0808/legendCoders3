# Title (Achievement) System Design Specification

**Date:** 2026-02-20
**Status:** Approved
**Topic:** User Engagement and Gamification

## 1. Overview
The Title System allows users to showcase their achievements. Users can unlock titles by meeting specific criteria and equip one to be displayed next to their nickname across the platform. Premium users have access to "Legendary" titles with special visual effects.

## 2. Key Features
### A. Title Management
- **Unlockable Titles:** Titles are automatically granted when users hit milestones (e.g., 10 First Bloods, 30-day streak).
- **Equipment:** Users can choose one equipped title from their collection via the Profile page.
- **Visual Styles:**
    - **Standard:** Solid color badges.
    - **Legendary (Pro Only):** Animated gradients, glow effects, and floating icons.

### B. Title Criteria Examples
- **Early Bird:** Solved between 06:00 - 09:00 (7 times).
- **First Blood:** First person to solve today's problem (10 times).
- **Problem Solver:** Total 50 problems solved.
- **Legend Pro:** Active Pro membership (Exclusive).

## 3. Data Model Changes
### Title Table
- `id`: UUID
- `name`: String (e.g., "First Blood")
- `description`: String (Criteria explanation)
- `color_code`: String (Hex or CSS class)
- `is_pro_only`: Boolean
- `has_glow`: Boolean
- `animation_type`: String (None, "pulse", "shimmer")

### UserTitle (N:M Link)
- `user_id`: UUID (FK)
- `title_id`: UUID (FK)
- `unlocked_at`: DateTime

### User Table Extension
- `equipped_title_id`: UUID (FK, Nullable)

## 4. UI/UX (UI-UX Pro Max)
- **Badge Display:** Show titles in Navbar, Forum Posts, and Ranking list.
- **Collection View:** A "Grimoire" style title collection page in Profile.
- **Equip Feedback:** Visual confirmation when a title is changed.
