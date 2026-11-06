"""Anonymous fixture probe executed inside the previous and candidate containers."""
import hashlib
import http.cookiejar
import json
from pathlib import Path
import sqlite3
import sys
import urllib.request

ROOT = Path('/data')
MARKER = ROOT / '.release-fixture.json'
USERNAME = 'release-fixture'
PASSWORD = 'Anonymous-release-fixture-only-2026!'


def request(path, payload=None, cookie=None):
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    value = None if payload is None else json.dumps(payload).encode()
    return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/api/v1/' + path, data=value, headers=headers), timeout=10)


def seed():
    with request('setup/admin', {'username': USERNAME, 'password': PASSWORD, 'passwordConfirmation': PASSWORD}) as response:
        user = json.load(response)
        cookie = response.headers['Set-Cookie'].split(';', 1)[0]
    db = sqlite3.connect(ROOT / 'app.db')
    stamp = '2026-01-01 00:00:00.000000'
    project = '00000000-0000-4000-8000-000000000001'
    db.execute('INSERT INTO projects(id,name,slug,description,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)', (project, 'Anonymous upgrade fixture', 'release-fixture', 'Synthetic persistent content', user['id'], stamp, stamp))
    db.execute('INSERT INTO project_drafts(project_id,schema_version,revision,document_json,updated_by,updated_at) VALUES(?,?,?,?,?,?)', (project, 1, 7, json.dumps({'schemaVersion': 1, 'pages': [], 'fixture': 'nonempty-old-version'}), user['id'], stamp))
    db.commit()
    db.close()
    MARKER.write_text(json.dumps({'cookie': cookie, 'user': user}))


def snapshot():
    fixture = json.loads(MARKER.read_text())
    with request('auth/me', cookie=fixture['cookie']) as response:
        assert json.load(response) == fixture['user'], 'existing login session/identity changed'
    with request('auth/login', {'username': USERNAME, 'password': PASSWORD}) as response:
        assert json.load(response) == fixture['user'], 'existing credentials cannot log in'
    db = sqlite3.connect(ROOT / 'app.db')
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    tables = {}
    for table in ['users', 'projects', 'project_drafts']:
        tables[table] = db.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall()
    instance = db.execute('SELECT instance_id FROM license_state WHERE id=1').fetchone()
    assert tables['projects'] and tables['project_drafts'] and instance, 'empty fixture is not an upgrade test'
    db.close()
    identities = {}
    for base in [ROOT, Path('/run/secrets')]:
        for path in base.rglob('*'):
            if path.is_file() and (path.suffix == '.key' or ('admin' in path.name and path.suffix == '.json')):
                identities[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert identities, 'no persisted identity files were checked'
    return {'tables': tables, 'instance': instance, 'identityFiles': identities}


if sys.argv[1] == 'seed':
    seed()
else:
    print(json.dumps(snapshot(), sort_keys=True))
