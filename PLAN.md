# Server Consolidation & Deployment Plan

## Problem Statement

The project has three redundant server files creating confusion and blocking real team deployment:

- **serve.py** — Simple Python HTTP server (7 lines)
- **server.pl** — Perl HTTP server (32 lines, identical functionality)
- **backend.py** — Flask API for GitHub sync proxy (96 lines)

The recent Flask backend addition enabled team members to edit without needing PATs, but it only works locally. Team members visiting https://trvemartins.github.io/onetrivago/ (GitHub Pages) cannot edit statuses because the backend is hardcoded to `localhost:3459`.

### Root Causes

1. **Redundancy** — Two identical static servers create confusion about which to use
2. **Deployment gap** — Frontend on GitHub Pages, backend localhost-only → GitHub sync non-functional for real team use
3. **Development friction** — Local dev requires 2–3 separate processes and remembering 3 ports
4. **Hardcoded values** — Frontend fetch URL is hardcoded to `localhost:3459`, breaks with any deployment
5. **Documentation incomplete** — BACKEND_SETUP.md implies team use but provides no real deployment path

---

## Solution: Unified Server Architecture

**Consolidate to a single unified Python server** (`app.py`) that:

- Combines static file serving + Flask API in one process
- Runs on a single configurable port
- Detects backend availability at runtime
- Supports local dev + cloud deployment seamlessly
- Enables graceful degradation (read-only mode if backend unavailable)

### Why This Approach

- **Eliminates confusion** — One server file, one port, one process to manage
- **Enables deployment** — Single Flask app is trivial to deploy to Render/Fly.io/Vercel
- **Better UX** — Frontend gracefully degrades if backend unavailable, rather than breaking
- **Modern pattern** — Development server and API together is standard practice
- **Future-proof** — Can be containerized with a single Dockerfile

---

## Implementation Plan (5 Phases, ~6 hours total)

### Phase 1: Create Unified Development Server (1–2 hours)

**Goal:** Merge `serve.py` and `backend.py` into a single `app.py` that serves static files + provides Flask API endpoints.

**Implementation:**

```python
# app.py
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os, json, base64, requests

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_OWNER = 'trvemartins'
GITHUB_REPO = 'onetrivago'
GITHUB_FILE = 'data/tests.json'

# ─── Static File Serving ───

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.isfile(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')  # SPA fallback

# ─── GitHub API Proxy (from backend.py) ───

def get_file_sha():
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    resp = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
    return resp.json().get('sha') if resp.status_code == 200 else None

def get_tests_data():
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    resp = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
    if resp.status_code == 200:
        content = base64.b64decode(resp.json()['content']).decode('utf-8')
        return json.loads(content)
    return None

def commit_tests_data(tests_data, sha):
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    content = base64.b64encode(json.dumps(tests_data, indent=2).encode('utf-8')).decode('utf-8')
    payload = {
        'message': 'Update C-test audit status',
        'content': content,
        'sha': sha,
    }
    resp = requests.put(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': 'application/vnd.github+json'}
    )
    return resp.status_code == 200, resp.json() if resp.status_code != 200 else None

@app.route('/api/update-status', methods=['POST'])
def update_status():
    if not GITHUB_TOKEN:
        return jsonify({'error': 'GitHub token not configured'}), 500

    data = request.get_json()
    test_id = data.get('testId')
    new_status = data.get('newStatus')

    if not test_id or not new_status:
        return jsonify({'error': 'testId and newStatus required'}), 400

    tests = get_tests_data()
    sha = get_file_sha()

    if not tests or not sha:
        return jsonify({'error': 'Failed to fetch test data from GitHub'}), 500

    test = next((t for t in tests if t['testId'] == test_id), None)
    if not test:
        return jsonify({'error': f'Test {test_id} not found'}), 404

    test['status'] = new_status
    success, error = commit_tests_data(tests, sha)
    
    if not success:
        return jsonify({'error': f'Failed to commit: {error}'}), 500

    return jsonify({'success': True, 'testId': test_id, 'newStatus': new_status}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'github_configured': bool(GITHUB_TOKEN)}), 200

# ─── Server ───

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=port, debug=debug)
```

**Key design choices:**
- Single port (configurable via `PORT` env var, defaults to 5000)
- Flask handles both static file serving AND API routes
- SPA fallback: `/<path:path>` serves `index.html` for client-side routing
- All backend.py logic preserved
- Optional `DEBUG` flag for development

**Deletion:**
- Remove `serve.py` (functionality merged into app.py)
- Remove `server.pl` (Python is primary server)

---

### Phase 2: Update Frontend for Backend Availability Detection (30 minutes)

**Goal:** Make `index.html` work in three scenarios without code changes:
1. GitHub Pages (no backend) — read-only mode
2. Local development — full editing via localhost backend
3. Deployed backend — full editing via deployed API URL

**Implementation in `index.html`:**

Add this script in the `<head>` before other JS:

```javascript
// Backend availability detection
window.API_CONFIG = {
  url: null,
  available: false,
};

// Try local backend first (development)
async function detectBackend() {
  const possibleUrls = [
    'http://localhost:5000',      // Default local dev
    'http://127.0.0.1:5000',
    window.location.origin,        // Same origin (deployed scenario)
  ];

  for (const url of possibleUrls) {
    try {
      const resp = await fetch(`${url}/health`, {
        method: 'GET',
        mode: 'cors',
        timeout: 2000,
      });
      if (resp.ok) {
        window.API_CONFIG.url = url;
        window.API_CONFIG.available = true;
        console.log(`Backend detected at ${url}`);
        return;
      }
    } catch (e) {
      // Try next URL
    }
  }
  
  console.log('No backend available — running in read-only mode');
  window.API_CONFIG.available = false;
}

// Run detection before any API calls
await detectBackend();
```

**Update existing API calls** (in whatever JS handles status updates):

Replace hardcoded `http://localhost:3459/api/update-status` with:

```javascript
async function updateTestStatus(testId, newStatus) {
  if (!window.API_CONFIG.available) {
    alert('Backend not available. Edit status in data/tests.json directly.');
    return false;
  }

  const resp = await fetch(`${window.API_CONFIG.url}/api/update-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ testId, newStatus }),
  });

  if (!resp.ok) {
    const error = await resp.json();
    alert(`Error: ${error.error}`);
    return false;
  }

  return true;
}
```

**UI Indicator** — Add visual badge showing backend status:

```html
<div id="backend-status" style="position: fixed; bottom: 10px; right: 10px; padding: 8px 12px; border-radius: 4px; font-size: 12px;">
  <span id="status-text">Connecting...</span>
</div>

<script>
window.addEventListener('load', () => {
  const statusEl = document.getElementById('status-text');
  if (window.API_CONFIG.available) {
    statusEl.textContent = '✓ Backend connected';
    statusEl.parentElement.style.backgroundColor = '#d4edda';
  } else {
    statusEl.textContent = '⚠ Read-only mode (no backend)';
    statusEl.parentElement.style.backgroundColor = '#fff3cd';
  }
});
</script>
```

**Disable editing UI** if no backend:

```javascript
document.addEventListener('DOMContentLoaded', () => {
  if (!window.API_CONFIG.available) {
    // Disable all status update buttons
    document.querySelectorAll('[data-update-status]').forEach(btn => {
      btn.disabled = true;
      btn.title = 'Backend not available. Edit data/tests.json manually.';
    });
  }
});
```

---

### Phase 3: Deployment Strategy Documentation (1 hour)

Create `DEPLOYMENT.md` documenting three deployment paths:

#### Option A: GitHub Pages Only (Free, Read-Only)

**Use case:** Team is comfortable editing `data/tests.json` manually via GitHub web UI.

```bash
# Just commit changes to data/tests.json
git add data/tests.json
git commit -m "Update test status"
git push
```

URL: https://trvemartins.github.io/onetrivago/  
Cost: Free  
Editing: Manual via GitHub web UI or git  
Frequency: Ad-hoc edits

---

#### Option B: Local Backend + GitHub Pages (Free, Edit Locally)

**Use case:** Small team, occasional edits, no cloud infrastructure.

```bash
# 1. Set GitHub PAT
export GITHUB_TOKEN=ghp_xxxxx

# 2. Install dependencies (one-time)
pip3 install -r requirements.txt

# 3. Start local backend
python3 app.py
# Server running on http://localhost:5000

# 4. Team members on LAN access via your IP
# If your machine is 192.168.1.100:
# http://192.168.1.100:5000
```

URL: `http://<your-ip>:5000` (on LAN)  
Cost: Free (depends on your machine)  
Editing: Live status updates  
Frequency: While you're running the server  
Availability: Only when your machine is on and server is running

---

#### Option C: Cloud-Deployed Backend (Recommended for Real Team Use)

**Use case:** Team needs always-on access, professional setup.

**Choice 1: Render (Simple, Recommended)**

```bash
# 1. Push code to GitHub
git push

# 2. On Render web UI (render.com):
#    - New → Web Service
#    - Connect onetrivago repo
#    - Build Command: pip install -r requirements.txt
#    - Start Command: gunicorn app:app
#    - Environment: GITHUB_TOKEN=ghp_xxxxx
#    - Auto-deploy on push: yes

# 3. Render assigns URL: https://onetrivago-xxxxx.onrender.com

# 4. Update frontend (optional):
#    - Uncomment DEPLOYMENT_URL in app.py or index.html
#    - Or just rely on runtime detection (will find backend at same origin)
```

Cost: Free tier ($0–7/mo for production)  
URL: Assigned by Render  
Setup time: ~10 min  
Availability: Always-on (unless free tier sleeps)  

Add to `requirements.txt`:
```
gunicorn==21.2.0
```

**Choice 2: Fly.io (Simple, Reasonable Cost)**

```bash
# 1. Install flyctl: https://fly.io/docs/getting-started/installing-flyctl/

# 2. Deploy
cd /path/to/onetrivago
flyctl launch
# Follow prompts:
# - App name: onetrivago-dash
# - Region: (choose nearest)
# - Build: Dockerfile (create if not exists)

# 3. Set secrets
flyctl secrets set GITHUB_TOKEN=ghp_xxxxx

# 4. Deploy
flyctl deploy

# URL: https://onetrivago-dash.fly.dev
```

Cost: ~$5–10/mo  
URL: Assigned by Fly.io  
Setup time: ~15 min  
Availability: Always-on

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080"]
```

Update `requirements.txt`:
```
gunicorn==21.2.0
```

**Choice 3: Vercel Serverless (Advanced, If You Use Vercel for Frontend)**

Requires refactoring backend.py to Vercel's serverless format. Skip unless Trivago already uses Vercel.

---

### Phase 4: Update Documentation (1.5 hours)

**Create `README.md` (NEW):**

```markdown
# C-Test Audit Dashboard

Live dashboard: https://trvemartins.github.io/onetrivago/

## Quick Start

### Option 1: View Only (No Setup Required)
Open https://trvemartins.github.io/onetrivago/ — read data, cannot edit.

### Option 2: Local Editing (5 min setup)
```bash
export GITHUB_TOKEN=ghp_xxxxx  # GitHub PAT with contents:write
pip3 install -r requirements.txt
python3 app.py
# Open http://localhost:5000
```

### Option 3: Deploy Permanently (10 min setup)
See [DEPLOYMENT.md](DEPLOYMENT.md) for Render / Fly.io / Vercel options.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for local dev workflow.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions and data flow.
```

**Create `DEVELOPMENT.md` (NEW):**

```markdown
# Local Development

## Prerequisites

- Python 3.10+
- GitHub PAT with `contents:write` on trvemartins/onetrivago

## Setup

```bash
# 1. Clone repo (if not already)
git clone https://github.com/trvemartins/onetrivago.git
cd onetrivago

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Set GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxx

# 4. Start server
python3 app.py
# Output: "Running on http://127.0.0.1:5000"

# 5. Open browser
open http://localhost:5000
```

## Making Changes

### Frontend (HTML/CSS/JS)
- Edit files directly (index.html, ctest-tracker.html, etc.)
- Server auto-serves updated files on reload
- No rebuild step needed

### Backend (API logic)
- Edit app.py
- Restart server (Ctrl+C, then `python3 app.py`)
- Changes take effect immediately

### Data Schema
- Test data lives in `data/tests.json` on GitHub
- Backend proxies reads/writes to GitHub API
- See [Architecture](ARCHITECTURE.md) for data flow

## Testing API Locally

```bash
# Health check
curl http://localhost:5000/health

# Update a test status
curl -X POST http://localhost:5000/api/update-status \
  -H 'Content-Type: application/json' \
  -d '{"testId":"CT-101","newStatus":"Updated status"}'
```

## Troubleshooting

- **ModuleNotFoundError**: Run `pip3 install -r requirements.txt`
- **GITHUB_TOKEN not set**: `export GITHUB_TOKEN=ghp_xxxxx`
- **Port 5000 already in use**: `PORT=5001 python3 app.py`
```

**Create `ARCHITECTURE.md` (NEW):**

```markdown
# Architecture

## Overview

The dashboard fetches test audit data from GitHub and allows team members to update status without needing a GitHub PAT.

### Components

- **Frontend** (index.html, ctest-tracker.html) — Vue/vanilla JS SPA
- **Backend** (app.py) — Flask API + static file server
- **Data** (data/tests.json on GitHub) — Source of truth

### Data Flow

**View Mode (Read):**
```
Frontend → Backend /health (detect availability)
        → Backend GET /api/status? (future, if needed)
        → Render dashboard
```

**Edit Mode (Write):**
```
User clicks "Update Status"
        ↓
Frontend calls backend POST /api/update-status
        ↓
Backend fetches current data/tests.json from GitHub API
        ↓
Backend updates the target test's status field
        ↓
Backend commits updated tests.json back to GitHub API
        ↓
Frontend refreshes and shows confirmation
```

### Why This Architecture?

**Problem we solved:**  
Team members can't edit the dashboard without GitHub PATs. Sharing a PAT is a security risk.

**Solution:**  
- Server runs with PAT in environment (safe, not exposed to frontend)
- Frontend talks only to local backend (no GitHub API keys exposed)
- Backend proxies requests to GitHub using server-side PAT
- Result: Team can edit without needing PATs

### File Organization

```
onetrivago/
├── app.py              ← Unified server (static + API)
├── index.html          ← Dashboard SPA
├── ctest-tracker.html  ← Backup tracker
├── data/
│   └── tests.json      ← Test data (on GitHub)
├── DEVELOPMENT.md      ← How to run locally
├── DEPLOYMENT.md       ← How to deploy to cloud
├── ARCHITECTURE.md     ← This file
└── requirements.txt    ← Python dependencies
```

### Why Remove serve.py and server.pl?

**Before:** Three separate server files
- serve.py: Python HTTP server
- server.pl: Perl HTTP server
- backend.py: Flask API

**Problem:** Redundancy and confusion — which to use?

**After:** Single app.py
- Combines static serving + API in one Flask app
- Single port, single process to manage
- Easy to deploy (one Dockerfile)
- Standard web app pattern (development server and API together)

### Security Notes

- GitHub PAT is environment-only, never in code or frontend
- Frontend cannot access GitHub API directly (browser CORS)
- All GitHub API calls go through backend (single point of control)
- Team members need no credentials

### Limitations

- Only one user can edit at a time (GitHub has eventual consistency)
- Changes take ~5 sec to appear in GitHub Pages (caching)
- Backend must have valid GITHUB_TOKEN to write (edit mode requires server-side setup)
```

**Update `BACKEND_SETUP.md`:**

Mark as deprecated and point to new docs:

```markdown
# ⚠️ DEPRECATED — See DEVELOPMENT.md and DEPLOYMENT.md instead

This file is outdated. For local development, see [DEVELOPMENT.md](DEVELOPMENT.md).

For deployment options (Render, Fly.io, etc.), see [DEPLOYMENT.md](DEPLOYMENT.md).
```

**Update `.gitignore`:**

Add:
```
.env
.env.local
*.pyc
__pycache__/
.DS_Store
```

---

### Phase 5: Testing Checklist (1 hour)

**Before marking implementation complete:**

- [ ] `python3 app.py` runs without errors
- [ ] http://localhost:5000 loads index.html
- [ ] http://localhost:5000/ctest-tracker.html loads
- [ ] Static files load (CSS, JS, images)
- [ ] `curl http://localhost:5000/health` returns 200 with `{"status":"ok",...}`
- [ ] Open DevTools console — no JS errors on page load
- [ ] Backend detection message appears ("✓ Backend connected" or "⚠ Read-only mode")
- [ ] Click "Update Status" — POST to `/api/update-status` succeeds
- [ ] Status change commits to GitHub (check repo for new commit)
- [ ] GitHub Pages URL https://trvemartins.github.io/onetrivago/ still works
- [ ] GitHub Pages shows "⚠ Read-only mode" badge (no local backend)
- [ ] GitHub Pages status update button is disabled
- [ ] Delete `serve.py`, `server.pl`, `backend.py` — nothing breaks
- [ ] Unit/integration tests pass (if any)
- [ ] Deploy to Render and test with actual team member

---

## Acceptance Criteria

- [ ] Single app.py runs local dev with both static files and API
- [ ] Frontend detects backend availability and disables editing if unavailable
- [ ] GitHub Pages read-only mode works
- [ ] Deployed backend (Render/Fly.io) tested with team member
- [ ] All three usage scenarios documented (Pages-only, local, deployed)
- [ ] serve.py and server.pl deleted
- [ ] DEPLOYMENT.md complete with setup for each option
- [ ] DEVELOPMENT.md covers local dev workflow
- [ ] ARCHITECTURE.md explains design decisions
- [ ] BACKEND_SETUP.md marked deprecated, pointers added
- [ ] All tests passing
- [ ] Zero breaking changes to frontend experience

---

## Timeline

- **Day 1 (Morning):** Phase 1 — create app.py, test locally, delete serve.py/server.pl
- **Day 1 (Afternoon):** Phase 2 — update index.html for backend detection and graceful degradation
- **Day 2 (Morning):** Phase 3 — write DEPLOYMENT.md with all three options
- **Day 2 (Afternoon):** Phase 4 — update README/DEVELOPMENT/ARCHITECTURE, clean up docs
- **Day 3 (Morning):** Phase 5 — testing across all scenarios
- **Day 3 (Afternoon):** Deploy to Render, final team validation

---

## Open Questions

1. **Which deployment option to recommend?** Suggest Render (simplest) or Fly.io (cheaper)?
2. **Should we deploy now or wait?** Can provide template as soon as Phase 1 is complete.
3. **Existing tests?** Any automated tests to update for app.py?
4. **GitHub Actions?** Should we add CI/CD to auto-deploy on push?
5. **Domain?** Should we use a custom domain or keep Render/Fly.io subdomain?

---

*Generated as implementation plan for server consolidation. Subject to revision based on team feedback.*
