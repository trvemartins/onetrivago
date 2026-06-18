#!/usr/bin/env python3
import os
import json
import re
import requests
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from html.parser import HTMLParser

# ── Initialization ──

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

CONFLUENCE_TOKEN = os.environ.get('CONFLUENCE_TOKEN')
CONFLUENCE_CLOUD = 'trivago.atlassian.net'
CONFLUENCE_PAGE_ID = 'FwR7HAE'

if not CONFLUENCE_TOKEN:
    print('WARNING: CONFLUENCE_TOKEN environment variable not set. Backend edit functionality disabled.')

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

@app.route('/api/update-status', methods=['POST'])
def update_status():
    """Update a test's status and sync to Confluence"""
    if not CONFLUENCE_TOKEN:
        return jsonify({'error': 'Confluence token not configured'}), 500

    data = request.get_json()
    test_id = data.get('testId')
    new_status = data.get('newStatus')

    if not test_id or not new_status:
        return jsonify({'error': 'testId and newStatus required'}), 400

    # Fetch current tests
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
    configured = bool(CONFLUENCE_TOKEN)
    return jsonify({'status': 'ok', 'confluence_configured': configured}), 200

# ── Server ──

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=port, debug=debug)
