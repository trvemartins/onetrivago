# Architecture

Design and technical decisions for the C-Test Audit Dashboard.

## Problem Statement

Team members need to view and edit test audit data without:
- Needing GitHub accounts
- Managing GitHub Personal Access Tokens (security risk)
- Manual JSON edits

**Solution:** Backend proxy — team talks to a local server that uses a shared PAT to access GitHub.

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
    │  │  Static File Server  │  │    GitHub API Proxy          │ │
    │  │  ├─ index.html       │  │  ├─ POST /api/update-status │ │
    │  │  ├─ ctest-tracker.html    │  │    GET /health           │ │
    │  │  └─ data/tests.json  │  │                              │ │
    │  └──────────────────────┘  └──────────────────────────────┘ │
    │              ▲                           │                     │
    │              │                           │                     │
    │         Serves HTML                  Uses GITHUB_TOKEN        │
    │         CSS, JS                       (server-only)           │
    │                                                                │
    └────────────────┬────────────────────────┬────────────────────┘
                     │                        │
         Reads from  │                        │  API calls with PAT
         filesystem  │                        │
                     │                        ▼
                     │        ┌───────────────────────────┐
                     │        │  GitHub API               │
                     │        │  ├─ Fetch data/tests.json │
                     │        │  └─ Commit updates        │
                     │        └───────────────────────────┘
                     │
                     └─ Can also serve from /data/tests.json
```

## Data Flow

### Reading Test Data

1. **User opens dashboard** → Browser loads `http://localhost:5000`
2. **Frontend fetches** `/` → Flask serves `index.html`
3. **JavaScript loads** `data/tests.json` → Fetches from `/data/tests.json`
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
5. **Backend receives request** → Fetches current `data/tests.json` from GitHub API
6. **Backend updates** → Finds test CT-101, updates status field
7. **Backend commits** → Uploads updated JSON back to GitHub with commit message
8. **GitHub updates** → `data/tests.json` is now changed in the repo
9. **Frontend shows** → "Synced to GitHub ✓" badge
10. **GitHub Pages** → Reflects change within ~5 minutes (cache)

### Graceful Degradation (No Backend)

If backend is unavailable (GitHub Pages without server):
1. Frontend `detectBackend()` → Tries to ping `/health` on multiple URLs
2. **Timeout after 2s** → No backend found
3. Frontend sets `window.API_CONFIG.available = false`
4. **Status dropdowns disabled** → Show tooltip "Edit data/tests.json directly on GitHub"
5. **Dashboard remains readable** → Can still view all data, just can't edit

---

## Why This Architecture?

### Problem: Exposing GitHub PAT

❌ **Bad approach:** Share a GitHub PAT with team members
- Security risk (token in browsers, chat, code)
- Hard to rotate
- Can't audit who changed what
- Accidentally committed to repos

✅ **Good approach:** PAT stays on server only
- Team never sees the token
- Token in environment variable (secure)
- Audit trail: commits show timestamp
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
| **GitHub as data store** | Single source of truth, built-in version control | Eventual consistency (~5s delay) |
| **Local storage fallback** | Works offline, no data loss | Needs eventual sync to server |
| **2-second backend timeout** | Quick user feedback if backend unavailable | May miss slow networks |
| **POST for updates** (not GET) | Safer, no accidental data changes in logs | Slightly more complex |
| **Graceful degradation** (read-only if no backend) | Better UX than broken app | Users expect editing and get surprise |

---

## File Organization

### `app.py` (115 lines)

Unified Flask server:
- **Lines 1-20:** Initialization, Flask setup, CORS
- **Lines 22-34:** Static file serving (`/`, `/<path:path>`)
- **Lines 36-62:** GitHub API proxy functions
- **Lines 64-96:** API endpoints (`/api/update-status`, `/health`)
- **Lines 98-101:** Server startup

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

### `data/tests.json`

Test audit data:
```json
[
  {
    "testId": "CT-101",
    "platform": "Web",
    "month": "April",
    "name": "Test name",
    "pm": "PM name",
    "status": "Has iOS + Android deliverables"
  }
]
```

---

## Deployment Scenarios

### Scenario 1: Local Development
```
Developer machine:
├─ python3 app.py  → Backend listening on localhost:5000
├─ Browser: http://localhost:5000
└─ GITHUB_TOKEN set in shell
```

### Scenario 2: GitHub Pages (Read-Only)
```
trvemartins/onetrivago main branch
├─ index.html (served by GitHub Pages)
├─ data/tests.json (readable)
└─ app.py (ignored by Pages, no server running)
```

### Scenario 3: Cloud Deployment (Recommended)
```
Render/Fly.io:
├─ Docker container with gunicorn + Flask
├─ GITHUB_TOKEN in environment
├─ URL: https://onetrivago-xxxxx.onrender.com
└─ Team accesses: https://onetrivago-xxxxx.onrender.com
```

---

## Security Considerations

### Token Exposure

✅ **Secure:**
- `GITHUB_TOKEN` in environment variables (Render, Fly.io, .env)
- Token never in code, never sent to browser
- Only server-side uses token for GitHub API

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
- No audit log of who changed what

**If needed in future:** Add optional auth middleware (JWT tokens, IP whitelist, etc.)

---

## Performance Considerations

### Frontend (Browser)

- **Lazy loading:** Tests loaded once on page load
- **Local storage:** Status changes cached locally before sync
- **Debouncing:** Sync waits 800ms after status change (groups rapid clicks)
- **No polling:** Page doesn't constantly check for updates

### Backend (Server)

- **GitHub API calls:** Each update = 2 GitHub API calls (fetch + commit)
- **Rate limit:** GitHub allows ~60 unauthenticated, unlimited authenticated per hour
- **No caching:** Always fetches fresh data from GitHub (simple but slower)

**If needed in future:** Cache tests.json locally, validate before commit

---

## Testing Checklist

- [ ] Local server starts: `python3 app.py`
- [ ] Health endpoint works: `curl http://localhost:5000/health`
- [ ] Frontend loads: `http://localhost:5000/` shows dashboard
- [ ] Backend detected: Status badge shows "✓ Backend connected"
- [ ] Status update works: Click dropdown → "Synced to GitHub ✓"
- [ ] GitHub commit created: Check repo commits
- [ ] GitHub Pages works: https://trvemartins.github.io/onetrivago/ shows read-only
- [ ] Graceful fallback: Kill backend, reload page, status dropdowns disabled

---

## Future Improvements

1. **Caching** — Cache `data/tests.json` locally to reduce GitHub API calls
2. **Validation** — Validate test data before committing (schema validation)
3. **Authentication** — Add optional password/token protection to editing
4. **Audit log** — Track who changed what and when
5. **Conflict resolution** — Handle simultaneous edits from multiple users
6. **Webhooks** — Auto-refresh frontend when data changes on GitHub
7. **Search/filter** — More advanced data filtering (currently basic)
8. **Export** — Download dashboard data as CSV/PDF
9. **Version history** — View and restore previous versions of tests

---

## Related Documents

- [README.md](README.md) — Quick start and overview
- [DEVELOPMENT.md](DEVELOPMENT.md) — Local development setup
- [DEPLOYMENT.md](DEPLOYMENT.md) — Cloud deployment guide
- [PLAN.md](PLAN.md) — Implementation plan and decisions
