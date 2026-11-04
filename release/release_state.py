#!/usr/bin/env python3
"""Small local receipt for continuing this Add-on publication without rebuilding it."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def directory():
    owner = (ROOT / git('rev-parse', '--git-common-dir')).resolve().parent
    for workspace in owner.parents:
        registry = workspace / 'workspace/projects.json'
        if registry.is_file():
            for project in json.loads(registry.read_text())['projects']:
                if (workspace / project['path']).resolve() == owner:
                    return workspace / project['local_materials_path'] / '记录/发布事务'
    return owner / 'output/release-transactions'


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.addon-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(state, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    action, version, *values = sys.argv[1:]
    if not version or any(c not in '0123456789.-' for c in version):
        raise ValueError('Invalid Add-on receipt version')
    path = directory() / ('addon-' + version + '.json')
    if action == 'exists':
        return 0 if path.is_file() else 1
    if action in ('pending', 'begin'):
        for other in path.parent.glob('addon-*.json'):
            if json.loads(other.read_text()).get('phase') != 'complete':
                raise ValueError('An earlier Add-on publication requires recovery: ' + str(other))
        if path.exists():
            raise ValueError('Publication receipt exists; use the explicit resume action')
        if action == 'pending':
            return 0
        previous, base, image = values
        save(path, dict(format=1, version=version, source=git('rev-parse', 'HEAD'),
                        previous=previous, base=base, image=image, digest=None, phase='prepared'))
        return 0
    state = json.loads(path.read_text())
    if state.get('format') != 1 or state.get('version') != version:
        raise ValueError('Invalid Add-on publication receipt')
    if action == 'verify':
        base, image = values
        head = git('rev-parse', 'HEAD')
        tag = subprocess.run(['git', '-C', str(ROOT), 'rev-list', '-n', '1', 'v' + version],
                             capture_output=True, text=True).stdout.strip()
        if tag and tag != head:
            raise ValueError('Add-on tag differs from the interrupted release source')
        if head != state['source']:
            if (git('rev-parse', 'HEAD^') != state['source']
                    or set(git('diff', '--name-only', 'HEAD^', 'HEAD').splitlines())
                       - {'ha_bridge/config.yaml', 'ha_bridge/CHANGELOG.md'}
                    or subprocess.check_output([sys.executable, str(ROOT / 'release/version.py'),
                                                'current'], text=True).strip() != version):
                raise ValueError('Add-on source changed since the interrupted publication')
        if state['base'] != base or state['image'] != image:
            raise ValueError('Add-on publication base/destination changed')
    elif action == 'get':
        print(state[values[0]] if state[values[0]] is not None else '')
    elif action == 'image-ready':
        if state['digest'] and state['digest'] != values[0]:
            raise ValueError('Add-on exact image changed since publication')
        state.update(digest=values[0], phase='image-ready')
        save(path, state)
    elif action == 'complete':
        state['phase'] = 'complete'
        save(path, state)
    else:
        raise ValueError('Unknown Add-on receipt action')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('Add-on publication stopped: ' + str(error), file=sys.stderr)
        sys.exit(2)
