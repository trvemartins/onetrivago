#!/usr/bin/env python3
import os
import json
import re
import hashlib
import requests
from flask import Flask, send_from_directory, request, jsonify, session
from flask_cors import CORS
from functools import wraps
from html.parser import HTMLParser

# ── Initialization ──

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

CONFLUENCE_TOKEN = os.environ.get('CONFLUENCE_TOKEN')
JIRA_TOKEN = os.environ.get('JIRA_TOKEN')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL', 'emilio.martins@trivago.com')
JIRA_DOMAIN = 'trivago.atlassian.net'
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'warp#engage')
CONFLUENCE_CLOUD = 'trivago.atlassian.net'
CONFLUENCE_PAGE_ID = 'FwR7HAE'

if not CONFLUENCE_TOKEN:
    print('WARNING: CONFLUENCE_TOKEN environment variable not set. Status updates disabled.')
if not JIRA_TOKEN:
    print('WARNING: JIRA_TOKEN environment variable not set. Jira data fetch disabled.')

# ── Authentication ──

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ── Jira API ──

def jira_api_get(endpoint):
    """Fetch from Jira API"""
    url = f'https://{JIRA_DOMAIN}/rest/api/3/{endpoint}'
    resp = requests.get(
        url,
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        headers={'Accept': 'application/json'}
    )
    return resp.json() if resp.status_code == 200 else None

def get_c_tests_from_jira():
    """Fetch C-tests from Jira"""
    if not JIRA_TOKEN:
        return []

    # Query for C-test issues (adjust JQL as needed for your Jira setup)
    jql = 'project = "CTEST" AND type = "Test" ORDER BY key'
    result = jira_api_get(f'search?jql={jql}&maxResults=500&fields=key,summary,customfield_10000,customfield_10001,customfield_10002,customfield_10003,assignee')

    if not result or 'issues' not in result:
        return []

    tests = []
    for issue in result['issues']:
        fields = issue.get('fields', {})
        assignee = fields.get('assignee', {})
        pm_name = assignee.get('displayName', 'Unknown') if assignee else 'Unknown'

        test = {
            'testId': issue['key'],
            'name': fields.get('summary', ''),
            'pm': pm_name,
            'platform': fields.get('customfield_10000', 'Web'),  # Platform custom field
            'month': fields.get('customfield_10001', '2026-06'),  # Month custom field
            'status': fields.get('customfield_10002', 'Missing deliverables'),  # Status custom field
            'jiraKey': issue['key'],
            'jiraUrl': f'https://{JIRA_DOMAIN}/browse/{issue["key"]}'
        }
        tests.append(test)

    return tests

# ── Static File Serving ──

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.isfile(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

# ── Confluence API Proxy ──

def get_confluence_page():
    """Fetch the Confluence page content"""
    url = f'https://{CONFLUENCE_CLOUD}/wiki/api/v2/pages/{CONFLUENCE_PAGE_ID}'
    resp = requests.get(
        url,
        headers={'Authorization': f'Bearer {CONFLUENCE_TOKEN}', 'Accept': 'application/json'},
        params={'body-format': 'storage'}
    )
    if resp.status_code == 200:
        return resp.json()
    return None

def parse_table_to_tests(html_body):
    """Parse HTML table and extract test data"""
    tests = []
    # Find all table rows (skip header)
    pattern = r'<tr><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td></tr>'
    matches = re.findall(pattern, html_body)

    for match in matches:
        test_id, name, pm, platform, month, status = match
        tests.append({
            'testId': test_id.strip(),
            'name': name.strip(),
            'pm': pm.strip(),
            'platform': platform.strip(),
            'month': month.strip(),
            'status': status.strip()
        })
    return tests

def tests_to_table_html(tests):
    """Convert test data back to HTML table"""
    rows = ''.join([
        f'<tr><td>{t["testId"]}</td><td>{t["name"]}</td><td>{t["pm"]}</td><td>{t["platform"]}</td><td>{t["month"]}</td><td>{t["status"]}</td></tr>'
        for t in tests
    ])
    return f'<table><thead><tr><th>Test ID</th><th>Name</th><th>PM</th><th>Platform</th><th>Month</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>'

def get_tests_data():
    """Fetch tests from Confluence page"""
    page = get_confluence_page()
    if not page or 'body' not in page:
        return None

    body = page['body'].get('storage', {}).get('value', '')
    return parse_table_to_tests(body)

def update_confluence_page(html_body):
    """Update the Confluence page with new content"""
    page = get_confluence_page()
    if not page or 'version' not in page:
        return False, 'Could not fetch page'

    version_number = page['version']['number']

    url = f'https://{CONFLUENCE_CLOUD}/wiki/api/v2/pages/{CONFLUENCE_PAGE_ID}'
    payload = {
        'id': CONFLUENCE_PAGE_ID,
        'version': {'number': version_number + 1},
        'body': {
            'storage': {
                'value': f'<p>This page is the authoritative data store for the C-Test Audit Dashboard (https://trvemartins.github.io/onetrivago/). Do not edit manually — edits will be overwritten by the dashboard backend when status updates are synced.</p>{html_body}',
                'representation': 'storage'
            }
        }
    }

    resp = requests.put(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {CONFLUENCE_TOKEN}', 'Content-Type': 'application/json'}
    )
    return resp.status_code in [200, 201], resp.json() if resp.status_code >= 400 else None

# ── API Endpoints ──

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate with password"""
    data = request.get_json()
    password = data.get('password', '')

    if password == DASHBOARD_PASSWORD:
        session['authenticated'] = True
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Invalid password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear session"""
    session.pop('authenticated', None)
    return jsonify({'success': True}), 200

@app.route('/api/tests', methods=['GET'])
@require_auth
def get_all_tests():
    """Get all tests (from Jira + Confluence status)"""
    # Fetch from Jira
    tests = get_c_tests_from_jira()

    # Augment with Confluence status
    if CONFLUENCE_TOKEN:
        confluence_tests = get_tests_data()
        if confluence_tests:
            # Create status map from Confluence
            status_map = {t['testId']: t['status'] for t in confluence_tests}
            # Update statuses from Confluence
            for test in tests:
                if test['testId'] in status_map:
                    test['status'] = status_map[test['testId']]

    return jsonify(tests), 200

@app.route('/api/pms', methods=['GET'])
@require_auth
def get_pms():
    """Get list of unique PMs for filtering"""
    tests = get_c_tests_from_jira()
    pms = sorted(set(t['pm'] for t in tests if t.get('pm')))
    return jsonify({'pms': pms}), 200

@app.route('/api/update-status', methods=['POST'])
@require_auth
def update_status():
    """Update a test's status and sync to Confluence"""
    if not CONFLUENCE_TOKEN:
        return jsonify({'error': 'Confluence token not configured'}), 500

    data = request.get_json()
    test_id = data.get('testId')
    new_status = data.get('newStatus')

    if not test_id or not new_status:
        return jsonify({'error': 'testId and newStatus required'}), 400

    # Fetch current tests from Confluence
    tests = get_tests_data()
    if not tests:
        return jsonify({'error': 'Failed to fetch test data from Confluence'}), 500

    # Find and update the test
    test = next((t for t in tests if t['testId'] == test_id), None)
    if not test:
        return jsonify({'error': f'Test {test_id} not found'}), 404

    test['status'] = new_status

    # Update Confluence page
    table_html = tests_to_table_html(tests)
    success, error = update_confluence_page(table_html)

    if not success:
        return jsonify({'error': f'Failed to update Confluence: {error}'}), 500

    return jsonify({'success': True, 'testId': test_id, 'newStatus': new_status}), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    configured = {
        'confluence': bool(CONFLUENCE_TOKEN),
        'jira': bool(JIRA_TOKEN)
    }
    return jsonify({'status': 'ok', 'configured': configured}), 200

# ── Server ──

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=port, debug=debug)
