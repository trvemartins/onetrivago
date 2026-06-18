# Local Development

How to run the dashboard locally with a working backend for testing and development.

## Prerequisites

- Python 3.9+
- Git
- A GitHub Personal Access Token (PAT) with `contents:write` on `trvemartins/onetrivago`

## Setup

### 1. Clone or navigate to the repo

```bash
cd /path/to/onetrivago
```

### 2. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

This installs:
- `flask` — web framework
- `flask-cors` — enable browser requests to backend
- `requests` — GitHub API calls

### 3. Set your Confluence API token

```bash
export CONFLUENCE_TOKEN=ATCTT3xxxxxxxxxxxxxxxxxxx
```

**How to create a Confluence API token:**
1. Confluence → Settings (top-right) → Personal settings → API tokens
2. Click "Create API token"
3. Name: `onetrivago-dev`
4. Copy the token and run: `export CONFLUENCE_TOKEN=...`

The backend will sync test status updates to: https://trivago.atlassian.net/wiki/x/FwR7HAE

### 4. Start the server

```bash
python3 app.py
```

Output:
```
WARNING: GITHUB_TOKEN environment variable not set...  [ignore if you set it above]
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### 5. Open in browser

http://localhost:5000

You should see:
- Dashboard loads
- Backend status badge shows "✓ Backend connected" (top right)
- Status dropdowns are enabled (clickable)
- Click a status to update → saves locally + syncs to GitHub

## Making Changes

### Frontend Changes (HTML/CSS/JS)

Edit `index.html`, `ctest-tracker.html`, etc. directly.

```bash
python3 app.py    # Server already running, watches for file changes
# Browser: Reload (Cmd+R) to see changes
```

No build step needed — Flask serves updated files on reload.

### Backend Changes (API Logic)

Edit `app.py`.

```bash
# Stop server: Ctrl+C
python3 app.py    # Restart to apply changes
```

Changes to API endpoints take effect immediately after restart.

### Data Schema

Test data lives in a Confluence page table: https://trivago.atlassian.net/wiki/x/FwR7HAE

Columns: Test ID | Name | PM | Platform | Month | Status

When you update a status in the dashboard:
1. Frontend sends POST to backend
2. Backend fetches the Confluence page (parses HTML table)
3. Backend updates the target test's status in the table
4. Backend updates the Confluence page with new HTML
5. Frontend shows "Synced to Confluence" badge

See [ARCHITECTURE.md](ARCHITECTURE.md) for full data flow.

## Testing the API

### Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "ok",
  "github_configured": true
}
```

### Update Status

```bash
curl -X POST http://localhost:5000/api/update-status \
  -H 'Content-Type: application/json' \
  -d '{
    "testId": "CT-101",
    "newStatus": "Has iOS + Android deliverables"
  }'
```

Success response:
```json
{
  "success": true,
  "testId": "CT-101",
  "newStatus": "Has iOS + Android deliverables"
}
```

Error responses:
```json
{
  "error": "GitHub token not configured"
}
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"

**Fix:** Install dependencies
```bash
pip3 install -r requirements.txt
```

### "GITHUB_TOKEN environment variable not set"

The backend prints this warning but still works (read-only). To enable status updates:

```bash
export GITHUB_TOKEN=ghp_xxxxx
python3 app.py
```

### "Port 5000 already in use"

Another app is using port 5000. Start on a different port:

```bash
PORT=8765 python3 app.py
# Then open http://localhost:8765
```

### "Sync failed — changes saved locally"

Backend ran but GitHub API failed. Check:

1. **Token is valid:** `echo $GITHUB_TOKEN` (should print `ghp_...`)
2. **Token has write access:** GitHub → Settings → Developer settings → Personal access tokens → Verify scope includes `contents:write`
3. **Token is SSO-authorized:** If your org uses SSO, token needs SSO authorization (GitHub shows prompt after login)
4. **File exists:** `data/tests.json` exists in the repo
5. **Backend logs:** Check terminal where `python3 app.py` runs for errors

### "Backend not available — read-only mode"

Frontend is trying to reach the backend but can't. Check:

1. **Server is running:** `python3 app.py` in another terminal
2. **No firewall blocking:** Try `curl http://localhost:5000/health`
3. **Custom port:** If you used `PORT=XXXX`, browser must also use that port

### "Changes not syncing to GitHub"

1. **Backend is running?** Check `python3 app.py` terminal
2. **No backend errors?** Look for red messages in the terminal
3. **GitHub token valid?** Try `curl http://localhost:5000/health` → should show `"github_configured": true`
4. **File in right place?** Check `data/tests.json` exists: `ls -la data/tests.json`

## Development Workflow

### Typical session:

```bash
# 1. Terminal 1 — start server
export GITHUB_TOKEN=ghp_xxxxx
python3 app.py

# 2. Terminal 2 — edit code
# Edit index.html, app.py, etc. in your editor
# Reload browser (Cmd+R) for frontend changes
# Restart server (Ctrl+C + python3 app.py) for backend changes

# 3. Test
# Open http://localhost:5000
# Click status → syncs to GitHub
# Check GitHub commits to see your changes
```

## Next Steps

- **Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Want to understand the architecture?** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Need to fix a bug?** Check [PLAN.md](PLAN.md) for known issues
