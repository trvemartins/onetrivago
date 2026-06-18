# C-Test Audit Dashboard

Live dashboard: **https://trvemartins.github.io/onetrivago/**

A Trivago internal tool for tracking iOS and Android deliverable coverage for web tests. Displays KR audit results with live editing, GitHub sync, and team collaboration.

## Quick Start

### Option 1: View Only (No Setup Required)
Open https://trvemartins.github.io/onetrivago/ — read test data, view charts. No authentication needed.

**Note:** GitHub Pages shows read-only mode. Status updates are disabled without a backend.

### Option 2: Local Editing (5 minutes)

For local development with live status updates:

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set GitHub token (needed for status updates)
export GITHUB_TOKEN=ghp_xxxxxxx   # Your GitHub PAT with contents:write on this repo

# 3. Start server
python3 app.py
# → Running on http://127.0.0.1:5000
```

Open **http://localhost:5000** in your browser.

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed instructions.

### Option 3: Deploy for Permanent Team Access

Recommended for ongoing use — gives team always-on access without running a local server.

**Easy options:**
- **Render** (~$7/mo, ~10 min setup) — [see DEPLOYMENT.md](DEPLOYMENT.md#option-c-cloud-deployed-backend)
- **Fly.io** (~$5-10/mo, ~15 min setup) — [see DEPLOYMENT.md](DEPLOYMENT.md#option-c-cloud-deployed-backend)

## Features

- **Live editing** — Update test status, syncs to GitHub automatically
- **Rich metrics** — KPI cards, coverage charts, PM breakdowns, status heatmap
- **Zero auth** — No GitHub PAT needed for team (backend handles authentication)
- **Graceful degradation** — Works read-only on GitHub Pages, full editing with backend

## Architecture

- **Frontend** (index.html) — Vue/vanilla JS SPA with Tailwind CSS
- **Backend** (app.py) — Unified Flask server (static files + API endpoints)
- **Data** (Confluence page) — Single source of truth at https://trivago.atlassian.net/wiki/x/FwR7HAE

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions.

## File Structure

```
onetrivago/
├── app.py                    ← Unified server (static files + API)
├── index.html                ← Dashboard SPA
├── ctest-tracker.html        ← Backup tracker
├── data/
│   └── tests.json            ← Test audit data (on GitHub)
├── README.md                 ← This file
├── DEVELOPMENT.md            ← Local dev setup
├── DEPLOYMENT.md             ← Cloud deployment guide
├── ARCHITECTURE.md           ← Design & tech decisions
├── PLAN.md                   ← Implementation plan
└── requirements.txt          ← Python dependencies
```

## Common Tasks

### I just want to view the dashboard
→ https://trvemartins.github.io/onetrivago/ (no setup needed)

### I want to edit test statuses locally
→ Follow "Option 2: Local Editing" above

### I want the team to access it permanently
→ See [DEPLOYMENT.md](DEPLOYMENT.md) for cloud deployment

### I want to modify the frontend
→ See [DEVELOPMENT.md](DEVELOPMENT.md#making-changes)

### I need to understand how it works
→ See [ARCHITECTURE.md](ARCHITECTURE.md)

## Troubleshooting

**"Backend not available — read-only mode"**
- Backend server is not running
- Option 1: Start it locally (`python3 app.py`)
- Option 2: Deploy it to cloud (see DEPLOYMENT.md)

**"Sync failed — changes saved locally"**
- Backend is running but GitHub API call failed
- Check GITHUB_TOKEN is set and valid: `echo $GITHUB_TOKEN`
- Check token has `contents:write` permission on this repo

**"Port 5000 already in use"**
- Another app is using port 5000
- Start on different port: `PORT=8765 python3 app.py`

**"ModuleNotFoundError: No module named 'flask'"**
- Install dependencies: `pip3 install -r requirements.txt`

## GitHub Pages Deployment

The live URL (https://trvemartins.github.io/onetrivago/) is automatically deployed from the `main` branch via GitHub Pages.

- Repo settings → Pages → Deploy from `main` / `(root)`
- No build step required (static HTML)
- Updates appear within ~5 minutes of push

## Contributing

Changes to `index.html`, `data/tests.json`, or `app.py` on `main` are live immediately (frontend) or within ~5 minutes (GitHub Pages cache).

For backend changes:
1. Test locally: `python3 app.py`
2. Push to main
3. If deployed to cloud, redeploy (Render auto-deploys on push)

## Support

- **Local dev issues** → See DEVELOPMENT.md
- **Deployment issues** → See DEPLOYMENT.md
- **Architecture questions** → See ARCHITECTURE.md
