# ⚠️ DEPRECATED

This file is outdated. The server setup has been consolidated.

## What Changed?

**Old approach (separate servers):**
- `serve.py` — Static file server (port 3456)
- `server.pl` — Static file server (port 3457)
- `backend.py` — Flask API (port 3459)

**New approach (unified server):**
- `app.py` — Single Flask server (port 5000) serving both static files and API

## Where to Find Updated Instructions

| Task | See |
|------|-----|
| Local development | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Cloud deployment | [DEPLOYMENT.md](DEPLOYMENT.md) |
| How it all works | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Quick start | [README.md](README.md) |

## Quick Migration

**Old (multiple terminals):**
```bash
# Terminal 1
python3 serve.py 3458

# Terminal 2
python3 backend.py 3459
```

**New (one terminal):**
```bash
export GITHUB_TOKEN=ghp_xxxxx
python3 app.py
# → http://localhost:5000
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for full setup.
