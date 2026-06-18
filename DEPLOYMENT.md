# Deployment Guide

Three paths for getting the dashboard live with a working backend. Pick the one that fits your needs.

## Option A: GitHub Pages Only (Free, Read-Only)

**Cost:** Free  
**Setup time:** Already done  
**URL:** https://trvemartins.github.io/onetrivago/  
**Editing:** Manual via GitHub web UI or git

### How It Works

GitHub Pages serves `index.html` from the main branch. Team members can view the dashboard but cannot edit statuses through the UI.

### To Update Test Data

Edit `data/tests.json` directly on GitHub:

```bash
# Option 1: GitHub web UI
# 1. Go to https://github.com/trvemartins/onetrivago/blob/main/data/tests.json
# 2. Click ✏️ (Edit)
# 3. Make changes
# 4. Commit

# Option 2: Git
git clone https://github.com/trvemartins/onetrivago.git
cd onetrivago
# Edit data/tests.json
git add data/tests.json
git commit -m "Update test status"
git push
```

Changes appear on the live dashboard within ~5 minutes (GitHub Pages cache).

---

## Option B: Local Backend + GitHub Pages (Free, Edit Locally)

**Cost:** Free (depends on your machine)  
**Setup time:** 5 minutes  
**URL:** `http://<your-ip>:5000` (on local network)  
**Editing:** Live status updates via dashboard  
**Availability:** Only when you run the server

### How It Works

You run `python3 app.py` on your machine. Team members on your local network access `http://your-ip:5000` to use the dashboard with live editing.

### Setup

**One-time:**
```bash
pip3 install -r requirements.txt
export CONFLUENCE_TOKEN=ATCTT3xxxxxxx  # Confluence API token
```

**To start the server:**
```bash
python3 app.py
# Running on http://127.0.0.1:5000
```

**For team to access:**
1. Find your machine's IP: `ifconfig | grep "inet " | grep -v 127.0.0.1` (macOS/Linux)
2. Share URL: `http://<your-ip>:5000`
3. Team members on same network can access and edit

### When to Use

- Small team, occasional edits
- No server infrastructure available
- Quick temporary solution
- Testing before deployment

### Limitations

- Only available while your machine is on and server is running
- No redundancy if your machine goes down
- Team depends on your internet connection

---

## Option C: Cloud-Deployed Backend (Recommended for Real Team Use)

Runs permanently in the cloud. Team always has access. Always-on, professional setup.

Pick one:

### C1: Render (Simple, Recommended)

**Cost:** Free tier (limited) or $7+/mo  
**Setup time:** ~10 minutes  
**URL:** `https://onetrivago-xxxxx.onrender.com` (auto-generated)  
**Availability:** Always-on

#### Steps

**1. Create Render account**
- Go to https://render.com
- Sign up with GitHub account

**2. Create Web Service**
- Dashboard → New + → Web Service
- Connect GitHub repo → select `trvemartins/onetrivago`
- Name: `onetrivago-dashboard`
- Environment: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Plan: Free (or $7/mo paid)

**3. Set environment variable**
- Settings → Environment
- Add `CONFLUENCE_TOKEN=ATCTT3xxxxxxx`

**4. Deploy**
- Click Deploy
- Render builds and starts your app
- You get a URL: `https://onetrivago-xxxxx.onrender.com`

**5. Share with team**
- https://onetrivago-xxxxx.onrender.com
- Team can edit statuses immediately
- No further setup needed

#### Update requirements.txt

Add gunicorn for production:
```
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
gunicorn==21.2.0
```

#### Redeploy after code changes

Render auto-deploys when you push to main:
```bash
git add app.py index.html  # or whatever changed
git commit -m "Fix backend bug"
git push
# Render automatically rebuilds and deploys
```

---

### C2: Fly.io (Simple, Reasonable Cost)

**Cost:** ~$5-10/mo  
**Setup time:** ~15 minutes  
**URL:** `https://onetrivago-dash.fly.dev` (you choose)  
**Availability:** Always-on

#### Steps

**1. Install flyctl**
```bash
curl -L https://fly.io/install.sh | sh
```

**2. Authenticate**
```bash
flyctl auth signup  # or flyctl auth login
```

**3. Create app**
```bash
cd /path/to/onetrivago
flyctl launch
```

Follow prompts:
- App name: `onetrivago-dashboard` (or your choice)
- Organization: (default)
- Region: (pick closest to you)
- Would you like to set up Postgres: `N`
- Would you like to set up an upstash redis: `N`

**4. Set GitHub token**
```bash
flyctl secrets set CONFLUENCE_TOKEN=ATCTT3xxxxxxx
```

**5. Deploy**
```bash
flyctl deploy
```

You get a URL: `https://onetrivago-dashboard.fly.dev`

**6. Share with team**
- https://onetrivago-dashboard.fly.dev
- Team can edit statuses immediately

#### Update requirements.txt

Add gunicorn:
```
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
gunicorn==21.2.0
```

#### Create Dockerfile (if not exists)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080"]
```

#### Redeploy after code changes

```bash
git add app.py index.html  # or whatever changed
git commit -m "Fix backend bug"
git push
flyctl deploy
```

---

### C3: Vercel Serverless (Advanced, If You Already Use Vercel)

**Cost:** Free/included in team plan  
**Setup time:** ~20 minutes  
**URL:** `https://onetrivago.vercel.app` (you choose)

Requires refactoring `app.py` to Vercel's serverless format. Only recommend if Trivago already uses Vercel for other projects.

**Skip this unless you know Vercel.**

---

## Comparing Deployment Options

| Factor | Option A (Pages) | Option B (Local) | Option C (Cloud) |
|--------|------------------|------------------|------------------|
| **Cost** | Free | Free | $7-10/mo |
| **Setup time** | 0 min (done) | 5 min | 10-15 min |
| **URL** | `github.io/...` | `http://192.x.x.x:5000` | `fly.dev` / `onrender.com` |
| **Editing** | Manual (GitHub) | Live (local server) | Live (cloud) |
| **Availability** | Always | While you run server | Always |
| **Team access** | Public internet | Local network only | Public internet |
| **Best for** | Read-only, no setup | Small teams, testing | Production, team use |

---

## Migrating Between Options

### From A (GitHub Pages) → B (Local Backend)

1. Start local server: `export CONFLUENCE_TOKEN=...; python3 app.py`
2. Share `http://<your-ip>:5000` with team
3. GitHub Pages URL still works (read-only fallback)

### From B (Local Backend) → C (Cloud Deployed)

1. Push code to main: `git push`
2. Deploy to Render or Fly.io (see steps above)
3. Disable local server (no longer needed)
4. Share cloud URL with team

### From A (Pages) → C (Cloud, skip B)

Same as B → C, just skip the local phase.

---

## Troubleshooting Deployments

### "Build failed on Render/Fly.io"

Check:
1. **requirements.txt valid:** Run locally first: `pip3 install -r requirements.txt`
2. **gunicorn added:** Render/Fly.io need gunicorn for production
3. **Python version:** Render/Fly.io use Python 3.10+
4. **Environment variables:** `CONFLUENCE_TOKEN` set in platform settings

### "Deployed but 404 / app won't start"

1. **Start command correct:** Should be `gunicorn app:app` (not `python3 app.py`)
2. **app.py exists in repo:** Check it's in the main branch
3. **Check logs:** Render/Fly.io dashboards show build/runtime logs

### "Deployed but backend API returns 500"

1. **CONFLUENCE_TOKEN valid:** `curl https://your-url/health` should show `"github_configured": true`
2. **GitHub token has write access:** Check token scopes on GitHub
3. **Token SSO authorized:** If using Trivago's org, token needs SSO auth

### "Team gets 'Read-only mode' on deployed URL"

Backend isn't running. Check:
1. Render/Fly.io dashboard shows "running"
2. No deploy errors in logs
3. `curl https://your-url/health` returns 200

### "Changes not syncing to GitHub from deployed backend"

Same as local troubleshooting in [DEVELOPMENT.md](DEVELOPMENT.md#troubleshooting):
1. Check CONFLUENCE_TOKEN is set
2. Check token has `contents:write`
3. Check `data/tests.json` exists in repo
4. Look at deployment logs for errors

---

## Next Steps

**Ready to deploy?**
1. Pick an option (A, B, or C)
2. Follow the steps for your choice
3. Test with: `curl https://your-url/health`
4. Share URL with team

**Questions?**
- Setup issues → see [DEVELOPMENT.md](DEVELOPMENT.md#troubleshooting)
- Architecture questions → see [ARCHITECTURE.md](ARCHITECTURE.md)
- General help → see [README.md](README.md)
