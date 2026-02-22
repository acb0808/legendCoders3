# Legend Pro (Premium Plan) Design Specification

**Date:** 2026-02-20
**Status:** Approved
**Topic:** Monetization and Premium User Experience

## 1. Overview
Legend Pro is a premium subscription plan designed to maximize user convenience and provide exclusive aesthetic benefits. The core value proposition is "Zero Effort Tracking" and "Elite Status".

## 2. Key Features
### A. Auto-Sync (Backend Scheduler)
- **Interval:** Every 5 minutes.
- **Scope:** Today's daily problem only.
- **Target:** Pro users whose subscription is active (`is_pro=True` and `pro_expires_at > Now`).
- **Logic:** Automatically crawl Baekjoon for the target problem. If solved, create a `Submission` and trigger a Discord announcement.

### B.Elite Status (UI/UX)
- **Gold Theme:** Golden name color and crown icon for Pro users.
- **Sync Badge:** Display next sync time on the dashboard for Pro users.
- **Pro Dashboard:** Exclusive section showing subscription status.

### C. Admin Management
- Manual Pro status toggle in the Admin Panel.
- Set/Edit expiration dates for Pro users.

## 3. Data Model Changes
- **User Table Extensions:**
    - `is_pro` (Boolean): Default False.
    - `pro_expires_at` (DateTime): Nullable.
    - `last_sync_at` (DateTime): Nullable.

## 4. Performance Considerations
- 5-minute intervals require efficient querying. Only query Pro users who haven't solved today's problem.
- Rate limiting: 2-3 second delay between each user's crawl task to avoid Baekjoon IP blocking.

## 5. Security & Permission
- Admin-only endpoint for upgrading users to Pro.
- Pro-only features (Auto-Sync) strictly enforced at the backend level.
