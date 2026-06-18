# Architecture

Design and technical decisions for the C-Test Audit Dashboard.

## Problem Statement

Team members need to view and edit test audit data without:
- Needing Confluence accounts  
- Managing Confluence API tokens (security risk to share)
- Manual table edits

**Solution:** Backend proxy — team accesses via dashboard, backend uses a shared token to update Confluence.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Team Members                               │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 │ Browser (HTTP)
                 │
    ┌────────────▼──────────────────────────────────────────────────┐
    │                  Unified Flask Server (app.py)                │
    │  ┌──────────────────────┐  ┌──────────────────────────────┐ │
    │  │  Static File Server  │  │  Confluence API Proxy        │ │
    │  │  ├─ index.html       │  │  ├─ POST /api/update-status │ │
    │  │  ├─ ctest-tracker.html    │  │    GET /health           │ │
    │  │  └─ data/           │  │                              │ │
    │  └──────────────────────┘  └──────────────────────────────┘ │
    │              ▲                           │                     │
    │              │                           │                     │
    │         Serves HTML                  Uses CONFLUENCE_TOKEN    │
    │         CSS, JS                       (server-only)           │
    │                                                                │
    └────────────────┬────────────────────────┬────────────────────┘
                     │                        │
         Reads from  │                        │  API calls with token
         filesystem  │                        │
                     │                        ▼
                     │        ┌───────────────────────────────────┐
                     │        │  Confluence API                   │
                     │        │  ├─ Fetch page FwR7HAE            │
                     │        │  └─ Update page with new table    │
                     │        └───────────────────────────────────┘
```

## Data Flow

### Reading Test Data

1. **User opens dashboard** → Browser loads `http://localhost:5000`
2. **Frontend fetches** `/` → Flask serves `index.html`
3. **Frontend loads local data** (fallback in browser for demo mode)
4. **Frontend detects backend** → Pings `/health` endpoint
5. **Dashboard renders** → Shows data, enables/disables editing based on backend availability

### Updating Status (with Backend)

1. **User clicks status dropdown** → Selects new value
2. **JavaScript calls** `window.onStatusChange()` → Stores locally + schedules sync
3. **After 800ms** → Calls `syncToBackend(testId, newStatus)`
4. **Frontend POSTs** to `http://localhost:5000/api/update-status`
   ```json
   {
     "testId": "CT-101",
     "newStatus": "Has iOS + Android deliverables"
   }
   ```
5. **Backend receives request** → Fetches Confluence page (FwR7HAE) via API
6. **Backend parses** → Extracts test data from HTML table
7. **Backend updates** → Finds test CT-101, changes status field
8. **Backend converts** → Regenerates HTML table with updated data
9. **Backend posts** → Updates Confluence page with new table content
10. **Confluence updates** → Page now reflects the change
11. **Frontend shows** → "Synced to Confluence ✓" badge

### Graceful Degradation (No Backend)

If backend is unavailable (GitHub Pages without server):
1. Frontend `detectBackend()` → Tries to ping `/health` on multiple URLs
2. **Timeout after 2s** → No backend found
3. Frontend sets `window.API_CONFIG.available = false`
4. **Status dropdowns disabled** → Show tooltip "Edit on Confluence directly"
5. **Dashboard remains readable** → Can still view all data, just can't edit via UI

---

## Why This Architecture?

### Problem: Sharing Confluence Credentials

❌ **Bad approach:** Share a Confluence API token with team members
- Security risk (token in browsers, chat, code)
- Hard to rotate
- Can't audit who changed what
- Accidentally committed to repos

✅ **Good approach:** Token stays on server only
- Team never sees the token
- Token in environment variable (secure)
- Audit trail: Confluence revisions show timestamp
- Single point of control

### Why Unified Server (Not Three Separate Ones)?

❌ **Old way:** `serve.py`, `server.pl`, `backend.py` running separately
- Confusion: which one to use?
- Port management: remember 3 different ports
- Deployment: coordinate multiple processes
- Development friction: start multiple terminals

✅ **New way:** Single `app.py` (Flask) handles everything
- One file, one port, one process
- Easy to containerize (one Dockerfile)
- Standard web app pattern
- Deploy to Render/Fly.io with 10 minutes setup

### Why Local Detection + Fallback?

Frontend tries multiple backend URLs in order:
1. `http://localhost:5000` (development)
2. `http://127.0.0.1:5000` (development, alternative)
3. `window.location.origin` (deployed scenario)

This means:
- **Locally:** Developer runs `python3 app.py`, frontend auto-detects
- **Deployed:** Backend and frontend same origin, frontend auto-detects
- **GitHub Pages:** No backend available, falls back to read-only
- **No code changes needed** for different deployment scenarios

---

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Single Flask app** (not separate servers) | Easier deployment, less confusion | Slightly less flexibility |
| **Confluence as data store** | Single source of truth, built-in versioning | HTML table parsing complexity |
| **HTML table storage** | Visible in Confluence UI, human-readable | Need to parse/regenerate HTML |
| **Local storage fallback** | Works offline, no data loss | Needs eventual sync to server |
| **2-second backend timeout** | Quick user feedback if backend unavailable | May miss slow networks |
| **POST for updates** (not GET) | Safer, no accidental data changes in logs | Slightly more complex |
| **Graceful degradation** | Better UX than broken app | Users expect editing and get surprise |

---

## File Organization

### `app.py` (130+ lines)

Unified Flask server:
- **Lines 1-20:** Initialization, Flask setup, CORS, Confluence config
- **Lines 22-34:** Static file serving (`/`, `/<path:path>`)
- **Lines 36-95:** Confluence API proxy functions
  - `get_confluence_page()` — Fetch page content
  - `parse_table_to_tests()` — Extract test data from HTML
  - `tests_to_table_html()` — Convert data back to HTML
  - `get_tests_data()` — Wrapper that fetches and parses
  - `update_confluence_page()` — Post updated content
- **Lines 97-132:** API endpoints (`/api/update-status`, `/health`)
- **Lines 134-138:** Server startup

### `index.html` (430+ lines)

Dashboard SPA:
- **Lines 1-70:** HTML structure, header, filters, KPI cards
- **Lines 71-430:** Inline JavaScript
  - **Lines 140-160:** Data loading (`loadTests()`)
  - **Lines 165-190:** UI state (`setSyncBadge()`, `showError()`)
  - **Lines 193-213:** Backend sync (`syncToBackend()`)
  - **Lines 220-240:** Status change handler (`onStatusChange()`)
  - **Lines 245-310:** Metrics calculation (`renderMetrics()`)
  - **Lines 354-420:** Table rendering (`renderTable()`)
  - **Lines 424-430:** Page initialization (`init()`)

### Confluence Page (FwR7HAE)

Test audit data stored as HTML table at:
https://trivago.atlassian.net/wiki/x/FwR7HAE

The page contains:
- Introductory paragraph
- HTML table with test data (Test ID | Name | PM | Platform | Month | Status)

Backend parses this table, updates cells, and regenerates the HTML.

---

## Deployment Scenarios

### Scenario 1: Local Development
```
Developer machine:
├─ python3 app.py  → Backend listening on localhost:5000
├─ Browser: http://localhost:5000
└─ CONFLUENCE_TOKEN set in shell
```

### Scenario 2: GitHub Pages (Read-Only)
```
trvemartins/onetrivago main branch
├─ index.html (served by GitHub Pages)
├─ (no backend running)
└─ app.py (ignored by Pages, not served)
```

### Scenario 3: Cloud Deployment (Recommended)
```
Render/Fly.io:
├─ Docker container with gunicorn + Flask
├─ CONFLUENCE_TOKEN in environment
├─ URL: https://onetrivago-xxxxx.onrender.com
└─ Team accesses: https://onetrivago-xxxxx.onrender.com
```

---

## Security Considerations

### Token Exposure

✅ **Secure:**
- `CONFLUENCE_TOKEN` in environment variables (Render, Fly.io, .env)
- Token never in code, never sent to browser
- Only server-side uses token for Confluence API

❌ **Insecure:**
- Token in git commits (NEVER)
- Token in HTML/JS (NEVER)
- Token shared via chat/email

### API Security

✅ **Good:**
- `POST` for mutations (harder to accidentally trigger in URLs)
- CORS enabled (browsers enforce same-origin for XSS protection)
- Input validation (check testId and newStatus exist)

⚠️ **Current limitations:**
- No authentication on `/api/update-status` (anyone on network can edit)
- No rate limiting (someone could hammer the API)
- No audit log of who changed what (Confluence handles this automatically)

**If needed in future:** Add optional auth middleware (JWT tokens, IP whitelist, etc.)

---

## Performance Considerations

### Frontend (Browser)

- **Lazy loading:** Tests loaded once on page load
- **Local storage:** Status changes cached locally before sync
- **Debouncing:** Sync waits 800ms after status change (groups rapid clicks)
- **No polling:** Page doesn't constantly check for updates

### Backend (Server)

- **Confluence API calls:** Each update = 2 API calls (fetch page + update page)
- **Rate limit:** Confluence allows unlimited API calls for authenticated users
- **No caching:** Always fetches fresh page (simple but slower)

**If needed in future:** Cache page content locally, validate before update

---

## Testing Checklist

- [ ] Local server starts: `python3 app.py`
- [ ] Health endpoint works: `curl http://localhost:5000/health`
- [ ] Frontend loads: `http://localhost:5000/` shows dashboard
- [ ] Backend detected: Status badge shows "✓ Backend connected"
- [ ] Status update works: Click dropdown → "Synced to Confluence ✓"
- [ ] Confluence page updated: Check page for new status value
- [ ] GitHub Pages works: https://trvemartins.github.io/onetrivago/ shows read-only
- [ ] Graceful fallback: Kill backend, reload page, status dropdowns disabled

---

## Future Improvements

1. **Caching** — Cache page content locally to reduce Confluence API calls
2. **Validation** — Validate test data before updating (schema validation)
3. **Authentication** — Add optional password/token protection to editing
4. **Audit log** — Track who changed what and when (beyond Confluence revisions)
5. **Conflict resolution** — Handle simultaneous edits from multiple users
6. **Webhooks** — Auto-refresh frontend when Confluence page changes
7. **Search/filter** — More advanced data filtering (currently basic)
8. **Export** — Download dashboard data as CSV/PDF
9. **Version history** — View and restore previous versions of tests

---

## Related Documents

- [README.md](README.md) — Quick start and overview
- [DEVELOPMENT.md](DEVELOPMENT.md) — Local development setup
- [DEPLOYMENT.md](DEPLOYMENT.md) — Cloud deployment guide
- [PLAN.md](PLAN.md) — Implementation plan and decisions
