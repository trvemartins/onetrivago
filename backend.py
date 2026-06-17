#!/usr/bin/env python3
import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_OWNER = 'trvemartins'
GITHUB_REPO = 'onetrivago'
GITHUB_FILE = 'data/tests.json'

if not GITHUB_TOKEN:
    print('WARNING: GITHUB_TOKEN environment variable not set. Backend will not work.')

def get_file_sha():
    """Fetch the current SHA of data/tests.json"""
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    resp = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
    if resp.status_code == 200:
        return resp.json().get('sha')
    return None

def get_tests_data():
    """Fetch current tests data from GitHub"""
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}'
    resp = requests.get(url, headers={'Authorization': f'Bearer {GITHUB_TOKEN}'})
    if resp.status_code == 200:
        content = base64.b64decode(resp.json()['content']).decode('utf-8')
        return json.loads(content)
    return None

def commit_tests_data(tests_data, sha):
    """Commit updated tests data back to GitHub"""
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
    """Update a test's status and commit to GitHub"""
    if not GITHUB_TOKEN:
        return jsonify({'error': 'GitHub token not configured'}), 500

    data = request.get_json()
    test_id = data.get('testId')
    new_status = data.get('newStatus')

    if not test_id or not new_status:
        return jsonify({'error': 'testId and newStatus required'}), 400

    # Fetch current data and SHA
    tests = get_tests_data()
    sha = get_file_sha()

    if not tests or not sha:
        return jsonify({'error': 'Failed to fetch test data from GitHub'}), 500

    # Update the test
    test = next((t for t in tests if t['testId'] == test_id), None)
    if not test:
        return jsonify({'error': f'Test {test_id} not found'}), 404

    test['status'] = new_status

    # Commit back to GitHub
    success, error = commit_tests_data(tests, sha)
    if not success:
        return jsonify({'error': f'Failed to commit: {error}'}), 500

    return jsonify({'success': True, 'testId': test_id, 'newStatus': new_status}), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'github_configured': bool(GITHUB_TOKEN)}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3459, debug=False)
