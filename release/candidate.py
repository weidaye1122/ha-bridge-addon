#!/usr/bin/env python3
"""Prepare an immutable Add-on candidate; formal channels belong to the full release."""
import json
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import release_state

ROOT = Path(__file__).resolve().parents[1]


def command(*args, capture=False, env=None):
    return subprocess.check_output(args, cwd=ROOT, text=True, env=env).strip() if capture else subprocess.run(args, cwd=ROOT, env=env, check=True)


def git(*args):
    return command('git', *args, capture=True)


def inspect(ref, optional=False):
    result = subprocess.run(['docker', 'buildx', 'imagetools', 'inspect', ref], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        if optional and re.search(r'not found|manifest unknown|MANIFEST_UNKNOWN', result.stderr, re.I):
            return None
        raise ValueError('Cannot inspect image ' + ref + ': ' + result.stderr.strip())
    match = re.search(r'^Digest:\s*(sha256:[0-9a-f]{64})\s*$', result.stdout, re.M)
    if not match:
        raise ValueError('No immutable image digest: ' + ref)
    return {'ref': ref, 'digest': match[1], 'platforms': re.findall(r'Platform:\s*(linux/\w+)', result.stdout)}


def require_platforms(image):
    if not {'linux/amd64', 'linux/arm64'} <= set(image['platforms']):
        raise ValueError('Candidate must contain both required architectures')


def receipt_path(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+-[1-9]\d*', version):
        raise ValueError('Invalid Add-on version')
    return release_state.directory() / ('addon-candidate-' + version + '.json')


def source_matches(state):
    if git('status', '--porcelain'):
        raise ValueError('Add-on source has uncommitted changes')
    head = git('rev-parse', 'HEAD')
    if head != state['source']:
        if not state.get('releaseHead') or head != state['releaseHead']:
            if (git('rev-parse', 'HEAD^') != state['source']
                    or set(git('diff', '--name-only', 'HEAD^', 'HEAD').splitlines()) - {'ha_bridge/config.yaml', 'ha_bridge/CHANGELOG.md'}
                    or command(sys.executable, 'release/version.py', 'current', capture=True) != state['version']):
                raise ValueError('Add-on source differs from the prepared candidate')
            state['releaseHead'] = head
    return head


def prepare(version):
    path = receipt_path(version)
    if git('status', '--porcelain'):
        raise ValueError('Prepare requires clean Add-on source')
    base = os.environ['BASE_IMAGE_REF']
    ref = os.environ['ADDON_CANDIDATE_REF']
    previous = os.environ['PREVIOUS_ADDON_REF']
    old_app = os.environ['PREVIOUS_APP_VERSION']
    official = os.environ['ADDON_IMAGE_REPOSITORY'] + ':' + version
    if not re.fullmatch(r'.+@sha256:[0-9a-f]{64}', base) or not re.fullmatch(r'.+@sha256:[0-9a-f]{64}', previous):
        raise ValueError('Candidate base and upgrade source must be digest-pinned')
    if not re.fullmatch(r'.+:candidate-' + re.escape(version) + r'-[0-9a-f]{16}', ref):
        raise ValueError('Preparation requires a unique candidate reference')
    identity = dict(source=git('rev-parse', 'HEAD'), version=version, base=base, ref=ref, previous=previous, previousApplication=old_app, official=official)
    if path.exists():
        state = json.loads(path.read_text())
        if any(state.get(k) != v for k, v in identity.items()):
            raise ValueError('Candidate identity changed; do not replace its receipt')
        source_matches(state)
        if state.get('digest'):
            if inspect(ref)['digest'] != state['digest']:
                raise ValueError('Candidate image changed')
            if state['phase'] in {'verified', 'complete'}:
                return state
        elif inspect(ref, optional=True):
            raise ValueError('Interrupted candidate upload has no recorded digest; inspect it before recovery')
    else:
        for other in path.parent.glob('addon-*.json'):
            if json.loads(other.read_text()).get('phase') not in {'complete', 'abandoned'}:
                raise ValueError('An earlier Add-on release requires recovery: ' + str(other))
        if inspect(official, optional=True) or inspect(ref, optional=True):
            raise ValueError('Candidate or formal image already exists without this receipt')
        state = dict(format=2, phase='building', digest=None, **identity)
        release_state.save(path, state)
    if not state.get('digest'):
        with tempfile.TemporaryDirectory(prefix='hb-addon-build-') as directory:
            metadata = Path(directory) / 'metadata.json'
            command('docker', 'buildx', 'build', '--builder', os.environ.get('BUILDER_NAME', 'ha-bridge-release-builder'), '--file', 'release/Dockerfile', '--platform', 'linux/amd64,linux/arm64', '--build-arg', 'BASE_IMAGE=' + base, '--build-arg', 'ADDON_VERSION=' + version, '--label', 'io.habridge.release-source=' + state['source'], '--metadata-file', str(metadata), '--provenance=mode=min', '--output', 'type=image,oci-artifact=false', '--tag', ref, '--push', 'release')
            built_digest = json.loads(metadata.read_text()).get('containerimage.digest')
            if not built_digest or not re.fullmatch(r'sha256:[0-9a-f]{64}', built_digest):
                raise ValueError('Add-on build metadata has no immutable digest')
        source_matches(state)
        image = inspect(ref)
        require_platforms(image)
        if image['digest'] != built_digest:
            raise ValueError('Uploaded Add-on candidate differs from the built artifact')
        state.update(digest=image['digest'], phase='built')
        release_state.save(path, state)
    with tempfile.TemporaryDirectory(prefix='hb-addon-candidate-auth-') as directory:
        original = Path(os.environ.get('DOCKER_CONFIG', str(Path.home() / '.docker')))
        (Path(directory) / 'config.json').write_text(json.dumps({
            'auths': {'https://index.docker.io/v1/': {}, 'registry-1.docker.io': {}},
            'cliPluginsExtraDirs': [str(original / 'cli-plugins')],
        }))
        env = dict(os.environ, DOCKER_CONFIG=directory)
        command('docker', 'buildx', 'imagetools', 'inspect', ref + '@' + state['digest'], env=env)
    for platform in ['linux/amd64', 'linux/arm64']:
        command('sh', 'release/verify_addon_upgrade.sh', previous, ref + '@' + state['digest'], version.rsplit('-', 1)[0], old_app, env=dict(os.environ, VERIFY_PLATFORM=platform))
    source_matches(state)
    state.update(phase='verified', verifiedPlatforms=['linux/amd64', 'linux/arm64'])
    release_state.save(path, state)
    return state


def finalize(version):
    path = receipt_path(version)
    state = json.loads(path.read_text())
    source_matches(state)
    full = Path(os.environ['FULL_RELEASE_RECEIPT']).resolve()
    owner = json.loads(full.read_text())
    if owner.get('images', {}).get('addon', {}).get('digest') != state['digest'] or owner['addonSource'] != state['source'] or owner['addonVersion'] != version:
        raise ValueError('Full release does not identify this verified Add-on candidate')
    # The owner checks current acceptance evidence, source, digests and the full
    # promotion phase. This is not an environment-variable bypass flag.
    main_root = Path(owner['mainRoot'])
    command(sys.executable, str(main_root / 'release/full_release_pipeline.py'), 'authorize-addon', owner['version'])
    if state['phase'] not in {'verified', 'complete'}:
        raise ValueError('Add-on candidate is not verified')
    if inspect(state['official'])['digest'] != state['digest'] or inspect(state['official'].rsplit(':', 1)[0] + ':latest')['digest'] != state['digest']:
        raise ValueError('Formal Add-on channels do not match the verified candidate')
    app, revision = version.rsplit('-', 1)
    if git('rev-parse', 'HEAD') == state['source']:
        command(sys.executable, 'release/version.py', 'set', app, revision)
        command(sys.executable, 'release/version.py', 'check', app, revision)
        changed = set(git('diff', '--name-only').splitlines())
        if changed - {'ha_bridge/config.yaml', 'ha_bridge/CHANGELOG.md'}:
            raise ValueError('Unexpected Add-on source changes during finalization')
        command('git', 'add', '--', 'ha_bridge/config.yaml', 'ha_bridge/CHANGELOG.md')
        command('git', 'commit', '-m', 'release: HA Bridge Add-on ' + version)
        state['releaseHead'] = git('rev-parse', 'HEAD')
    release_state.save(path, state)
    tag = 'v' + version
    result = subprocess.run(['git', 'rev-parse', '--verify', tag + '^{}'], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        command('git', 'tag', '-a', tag, '-m', 'HA Bridge Add-on ' + version)
    elif result.stdout.strip() != state['releaseHead']:
        raise ValueError('Add-on tag belongs to a different source')
    command('git', 'push', '--atomic', 'origin', 'HEAD:refs/heads/main', 'refs/tags/' + tag)
    for ref in ['refs/heads/main', 'refs/tags/' + tag + '^{}']:
        if git('ls-remote', 'origin', ref).split()[0] != state['releaseHead']:
            raise ValueError('Add-on remote Git identity differs after publication')
    state['phase'] = 'complete'
    release_state.save(path, state)
    return state


def abandon(version):
    path = receipt_path(version)
    if not path.exists():
        return {'phase': 'not-created'}
    state = json.loads(path.read_text())
    owner = json.loads(Path(os.environ['FULL_RELEASE_RECEIPT']).read_text())
    if owner.get('phase') != 'abandoning' or owner.get('addonVersion') != version or owner.get('addonSource') != state['source'] or state['phase'] == 'complete':
        raise ValueError('Only the owning, never-promoted full candidate can abandon this attempt')
    if inspect(state['official'], optional=True):
        raise ValueError('Formal Add-on version exists; recovery is required')
    state.update(phase='abandoned', abandonmentReason=owner['abandonmentReason'])
    release_state.save(path, state)
    archive = path.with_name(path.stem + '-attempt-' + state['ref'].rsplit('-', 1)[1] + '.json')
    release_state.save(archive, state)
    path.unlink()
    return state


if __name__ == '__main__':
    try:
        action, version = sys.argv[1:]
        if action == 'inspect':
            result = json.loads(receipt_path(version).read_text())
            source_matches(result)
        elif action in {'prepare', 'finalize', 'abandon'}:
            directory = receipt_path(version).parent
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / '.addon-candidate.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                result = {'prepare': prepare, 'finalize': finalize, 'abandon': abandon}[action](version)
        else:
            raise ValueError('Unknown Add-on candidate action')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('Add-on candidate stopped: ' + str(error), file=sys.stderr)
        sys.exit(2)
