# Setup Guide: Jira Integration & New Features

This guide covers setup for password protection, Jira integration, PM filtering, and Jira links.

## Quick Start

```bash
# 1. Get credentials
export CONFLUENCE_TOKEN=ATCTT3xxx...xxx    # Confluence API token
export JIRA_TOKEN=ATATT3xxx...xxx          # Jira API token
export DASHBOARD_PASSWORD=your-password     # Login password
export SECRET_KEY=your-secret-key          # Flask session key (optional)

# 2. Start server
python3 app.py

# 3. Open in browser
# http://localhost:5000 → prompts for password
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `CONFLUENCE_TOKEN` | Confluence API token for status updates | `ATCTT3xxxxxxxxxxx` |
| `JIRA_TOKEN` | Jira API token for fetching tests | `ATATT3xxxxxxxxxxx` |
| `DASHBOARD_PASSWORD` | Login password | `warp#engage` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `JIRA_EMAIL` | Email for Jira API authentication | `emilio.martins@trivago.com` |
| `SECRET_KEY` | Flask session encryption key | `dev-secret-key-change-in-production` |
| `CONFLUENCE_CLOUD` | Confluence instance domain | `trivago.atlassian.net` |
| `JIRA_DOMAIN` | Jira instance domain | `trivago.atlassian.net` |

## 1. Password Protection Setup

The dashboard now requires a password to access.

**Default password:** `warp#engage`

**To change password:**
```bash
export DASHBOARD_PASSWORD=my-new-password
python3 app.py
```

**For production (Render/Fly.io):**
- Set `DASHBOARD_PASSWORD` environment variable in the platform dashboard
- Set `SECRET_KEY` to a random string (for session encryption)

## 2. Jira Integration Setup

### 2.1 Create Jira API Token

1. Jira → Settings (top-right) → Personal settings → API tokens
2. Click "Create API token"
3. Name: `onetrivago-integration`
4. Copy the token (starts with `ATATT`)

```bash
export JIRA_TOKEN=ATATT3xxxxxxxxxxx
export JIRA_EMAIL=your-email@trivago.com
```

### 2.2 Configure Jira JQL Query

The dashboard fetches C-tests from Jira using a JQL query. You need to customize it for your Jira setup.

**Edit `app.py`, find `get_c_tests_from_jira()` function:**

```python
jql = 'project = "CTEST" AND type = "Test" ORDER BY key'
```

**Adjust based on your Jira:**
- `project` — Your project key (e.g., `CTEST`, `CT`, `KTEST`)
- `type` — Your issue type (e.g., `Test`, `C-Test`, `Task`)
- Add more filters as needed: `AND status = "In Progress"`, `AND assignee = "user@example.com"`

**Examples:**

```python
# Fetch only tests assigned to your team
jql = 'project = "CTEST" AND type = "Test" AND assignee IN (user1, user2) ORDER BY key'

# Fetch only active tests (not closed)
jql = 'project = "CTEST" AND type = "Test" AND status != Done ORDER BY key'

# Fetch tests from a specific sprint
jql = 'project = "CTEST" AND type = "Test" AND sprint = "Q2 2026" ORDER BY key'
```

### 2.3 Map Jira Custom Fields

The dashboard extracts custom fields from Jira. You need to map your field IDs in `app.py`:

```python
def get_c_tests_from_jira():
    ...
    test = {
        'testId': issue['key'],
        'name': fields.get('summary', ''),
        'pm': pm_name,
        'platform': fields.get('customfield_10000', 'Web'),      # ← Platform field ID
        'month': fields.get('customfield_10001', '2026-06'),     # ← Month field ID
        'status': fields.get('customfield_10002', 'Missing'),    # ← Status field ID
        ...
    }
```

**To find your custom field IDs:**

1. Jira → Settings → Issues → Custom fields
2. Find your field, note the ID (e.g., `customfield_10000`)
3. Update the code above with correct IDs

**Alternatively, use REST API:**

```bash
curl -u you@example.com:$JIRA_TOKEN \
  https://trivago.atlassian.net/rest/api/3/fields | jq '.[] | select(.name=="Platform") | .id'
```

**Field mapping in this version:**
- `customfield_10000` → Platform (Web, iOS, Android)
- `customfield_10001` → Month (YYYY-MM format, e.g., 2026-06)
- `customfield_10002` → Status (Missing deliverables, Has iOS + Android deliverables, etc.)
- `assignee` → PM (displayed name from assignee field)

### 2.4 Verify Jira Setup

Test the Jira endpoint:

```bash
curl -u you@example.com:$JIRA_TOKEN \
  'https://trivago.atlassian.net/rest/api/3/search?jql=project=CTEST&maxResults=5'
```

Should return JSON with issues. If you get 401, token is invalid. If you get 0 results, adjust JQL query.

## 3. Confluence Status Storage

The dashboard still stores test status updates in Confluence (not in Jira).

**Confluence page:** https://trivago.atlassian.net/wiki/x/FwR7HAE

When a user updates a status:
1. Frontend sends POST to `/api/update-status`
2. Backend fetches Confluence page
3. Backend updates the HTML table
4. Backend posts updated page back

**To use a different Confluence page:**

Edit `app.py`:
```python
CONFLUENCE_PAGE_ID = 'FwR7HAE'  # Change this to your page ID
```

Page ID is the encoded part from URLs like `/x/FwR7HAE`.

## 4. PM Filtering

PM filter is auto-populated from Jira test data (the `assignee` field).

**No setup needed** — it works automatically if Jira tests have assignees.

**If PMs aren't showing:**
1. Verify assignee field is populated in Jira
2. Check that PM name matches between Jira and frontend
3. Test: `curl http://localhost:5000/api/pms` (requires login)

## 5. Jira Links

Each test ID in the dashboard links to its Jira issue.

**Link format:** `https://trivago.atlassian.net/browse/{ISSUE_KEY}`

**Example:** `CT-101` → `https://trivago.atlassian.net/browse/CT-101`

**To customize domain:**

Edit `app.py`:
```python
'jiraUrl': f'https://YOUR-DOMAIN/browse/{issue["key"]}'
```

## Testing the Setup

### Local Testing

```bash
# 1. Start server
export CONFLUENCE_TOKEN=xxx
export JIRA_TOKEN=xxx
export DASHBOARD_PASSWORD=test123
python3 app.py

# 2. Open http://localhost:5000
# → Login screen appears
# → Enter password: test123
# → Dashboard loads with Jira tests

# 3. Test features
# - Try PM filter dropdown
# - Click a test ID (should open Jira)
# - Update a status (should sync to Confluence)
```

### API Testing

```bash
# 1. Login
curl -c cookies.txt -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"password":"test123"}'

# 2. Get tests
curl -b cookies.txt http://localhost:5000/api/tests | jq '.[0]'

# 3. Get PMs
curl -b cookies.txt http://localhost:5000/api/pms | jq '.pms'

# 4. Update status
curl -b cookies.txt -X POST http://localhost:5000/api/update-status \
  -H "Content-Type: application/json" \
  -d '{"testId":"CT-101","newStatus":"Has iOS + Android deliverables"}'
```

## Troubleshooting

### "Invalid password" on login

- Check `DASHBOARD_PASSWORD` env var is set
- Default password is `warp#engage`

### No tests showing after login

1. Check Jira JQL query in `app.py`
2. Verify `JIRA_TOKEN` is set and valid
3. Test manually:
   ```bash
   curl -u email@example.com:$JIRA_TOKEN \
     'https://trivago.atlassian.net/rest/api/3/search?jql=...'
   ```

### "0 tests found" in Jira

- JQL query returns no issues
- Check project key, issue type, filters
- Example JQL that should always work:
   ```python
   jql = 'project = "CTEST" ORDER BY key'
   ```

### PM filter is empty

- Jira tests have no assignee
- Add assignees in Jira
- Or change PM mapping to use a different field (e.g., custom field)

### Status updates not syncing to Confluence

1. Verify `CONFLUENCE_TOKEN` is set
2. Check Confluence page ID is correct
3. Ensure token has write permission on the page
4. Check backend logs for errors

### Jira links are wrong

- Verify `JIRA_DOMAIN` env var
- Check issue keys are correct in Jira
- Customize link format in `app.py` if needed

## Next Steps

1. ✅ Set up environment variables
2. ✅ Configure Jira JQL and custom field IDs
3. ✅ Test locally
4. 🚀 Deploy to Render/Fly.io (see DEPLOYMENT.md)

## Related Documents

- [README.md](README.md) — Overview
- [DEVELOPMENT.md](DEVELOPMENT.md) — Local dev
- [DEPLOYMENT.md](DEPLOYMENT.md) — Cloud deployment
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design
