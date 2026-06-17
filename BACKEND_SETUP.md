# Backend Setup

The dashboard now uses a Python Flask backend to handle GitHub API calls. This means team members don't need GitHub accounts or PATs — they just open the dashboard and edit.

## How It Works

1. **Frontend** (index.html): Users edit statuses in the dashboard
2. **Backend** (backend.py): Receives updates, uses a server-side PAT to commit to GitHub
3. **GitHub**: data/tests.json is updated and committed

## Setup

### 1. Install dependencies (one-time)
```bash
pip3 install -r requirements.txt
```

### 2. Set your GitHub PAT as an environment variable
```bash
export GITHUB_TOKEN=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
```

This PAT needs `contents: write` permission on the `trvemartins/onetrivago` repo and must be SSO-authorized for Trivago's GitHub org.

### 3. Start both servers

**Terminal 1: Frontend (HTTP server)**
```bash
python3 -m http.server 3458
```

**Terminal 2: Backend (Flask)**
```bash
python3 backend.py
```

Both will be running:
- Dashboard: http://localhost:3458/index.html
- Backend API: http://localhost:3459/api/update-status

### 4. Share the live URL

For your team to use without running locally, ensure GitHub Pages is enabled:
- Repo → Settings → Pages → Deploy from `main` / `(root)`
- URL: https://trvemartins.github.io/onetrivago/

For local/internal use, run the backend + frontend as above.

## For Deployment

If you deploy this somewhere (Heroku, Vercel, fly.io, etc.):

1. **Environment variable**: Set `GITHUB_TOKEN` in the platform's config
2. **Backend port**: Change `port=3459` in `backend.py` if needed
3. **Frontend API URL**: Update the fetch call in `index.html` from `http://localhost:3459` to your backend domain

## Testing

```bash
# Health check
curl http://localhost:3459/health

# Test an update (replace values)
curl -X POST http://localhost:3459/api/update-status \
  -H "Content-Type: application/json" \
  -d '{"testId":"CT-102","newStatus":"Has iOS + Android deliverables"}'
```

## Troubleshooting

- **"GITHUB_TOKEN not configured"**: Set `export GITHUB_TOKEN=...` before running backend.py
- **Connection refused on :3459**: Backend not running — start it in a separate terminal
- **401 on GitHub**: PAT is invalid or not SSO-authorized for the org
- **404 on data/tests.json**: File doesn't exist in repo or path is wrong

See the Flask logs for details.
