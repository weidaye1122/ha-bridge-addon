"""Exercise publication recovery and cleanup with local Git and owned Docker substitutes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        (self.repo / 'release').mkdir(parents=True)
        (self.repo / 'ha_bridge').mkdir()
        for name in ('publish_addon_release.sh', 'release_state.py', 'version.py'):
            shutil.copy2(ROOT / 'release' / name, self.repo / 'release' / name)
        (self.repo / 'ha_bridge/config.yaml').write_text('version: "0.1.0-1"\n')
        (self.repo / 'ha_bridge/CHANGELOG.md').write_text('# 更新日志\n\n## 0.1.0-1\n\n- previous\n')
        (self.repo / '.gitignore').write_text('output/\n')
        upgrade = self.repo / 'release/verify_addon_upgrade.sh'
        upgrade.write_text('''#!/bin/sh
printf 'upgrade %s %s\\n' "$1" "$2" >> "$FIXTURE_EVENTS"
[ ! -f "$FIXTURE_STATE/fail-upgrade" ] || exit 42
''')
        upgrade.chmod(0o755)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Anonymous fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.remote = self.base / 'origin.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(self.remote)], check=True)
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-qu', 'origin', 'main')
        binary = self.base / 'bin'
        binary.mkdir()
        docker = binary / 'docker'
        docker.write_text('#!' + sys.executable + '\n' + '''import json,os,sys
from pathlib import Path
args=sys.argv[1:];root=Path(os.environ['FIXTURE_STATE'])
with open(os.environ['FIXTURE_EVENTS'],'a') as out:out.write(json.dumps(args)+'\\n')
if args[:3]==['buildx','imagetools','inspect']:
    ref=args[3]
    if ref=='fixture/base:0.1.1':digest='a'*64
    elif ref.endswith(':latest'):digest='b'*64
    elif ref=='fixture/addon:0.1.1-1' and (root/'image').exists():digest='c'*64 if os.getenv('FIXTURE_DRIFT') else 'b'*64
    else:print('manifest unknown',file=sys.stderr);sys.exit(1)
    print('Digest: sha256:'+digest+'\\nPlatform: linux/amd64\\nPlatform: linux/arm64')
elif args[:2]==['buildx','build']:(root/'image').touch()
elif args[:2]==['manifest','inspect']:print('{}')
elif args[:3]!=['buildx','imagetools','create']:sys.exit(99)
''')
        docker.chmod(0o755)
        self.state = self.base / 'state'
        self.state.mkdir()
        self.events = self.base / 'events'
        self.env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                        BASE_VERSION='0.1.1', BASE_IMAGE_REPOSITORY='fixture/base',
                        ADDON_IMAGE_REPOSITORY='fixture/addon', ADDON_REVISION='1',
                        FIXTURE_STATE=str(self.state), FIXTURE_EVENTS=str(self.events))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args],
                                        text=True, stderr=subprocess.DEVNULL).strip()

    def run_release(self, action, **env):
        return subprocess.run(['sh', 'release/publish_addon_release.sh', action], cwd=self.repo,
            env=dict(self.env, **env), text=True, capture_output=True, timeout=15)

    def test_upgrade_failure_resumes_without_rebuilding(self):
        self.recover_after_failure('upgrade')

    def test_git_failure_resumes_and_preserves_previous_upgrade_source(self):
        self.recover_after_failure('git')

    def test_version_commit_without_tag_can_finish_the_same_publication(self):
        self.recover_after_failure('tag')

    def recover_after_failure(self, failure):
        marker = self.state / 'fail-upgrade'
        hook = self.remote / 'hooks/pre-receive'
        if failure == 'upgrade':
            marker.touch()
        else:
            hook.write_text('#!/bin/sh\nexit 1\n')
            hook.chmod(0o755)
        first = self.run_release('publish')
        self.assertNotEqual(first.returncode, 0)
        marker.unlink(missing_ok=True)
        hook.unlink(missing_ok=True)
        if failure == 'tag':
            self.git('tag', '-d', 'v0.1.1-1')
        resumed = self.run_release('resume')
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        calls = self.events.read_text().splitlines()
        self.assertEqual(sum(line.startswith('["buildx", "build"') for line in calls), 1)
        upgrades = [line for line in calls if line.startswith('upgrade ')]
        self.assertTrue(all('fixture/addon:0.1.0-1 ' in line for line in upgrades))
        self.assertIn('0.1.1-1', (self.repo / 'ha_bridge/config.yaml').read_text())
        receipt = self.repo / 'output/release-transactions/addon-0.1.1-1.json'
        self.assertEqual(json.loads(receipt.read_text())['phase'], 'complete')
        self.assertEqual(self.run_release('resume').returncode, 0)


    def test_resume_rejects_image_or_source_drift_before_writes(self):
        marker = self.state / 'fail-upgrade'
        marker.touch()
        self.assertNotEqual(self.run_release('publish').returncode, 0)
        marker.unlink()
        pending = self.run_release('preflight', BASE_VERSION='0.1.2')
        self.assertNotEqual(pending.returncode, 0)
        self.assertIn('requires recovery', pending.stderr)
        before = self.events.read_text()
        result = self.run_release('resume', FIXTURE_DRIFT='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no matching receipt', result.stderr)
        new_calls = self.events.read_text()[len(before):]
        self.assertNotIn('["buildx", "build"', new_calls)
        self.assertNotIn('upgrade ', new_calls)
        (self.repo / 'unrelated.txt').write_text('different source')
        self.git('add', 'unrelated.txt')
        self.git('commit', '-qm', 'source drift')
        result = self.run_release('resume')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('source changed', result.stderr)

    def tearDown(self):
        self.temp.cleanup()


class CleanupTests(unittest.TestCase):
    def test_failed_removal_reports_failure_and_retains_data_but_absent_container_is_ok(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'bin'
            binary.mkdir()
            docker = binary / 'docker'
            docker.write_text('''#!/bin/sh
case "$1 $2" in
  'rm --force') printf '%s\\n' "$FIXTURE_REMOVE_ERROR" >&2; exit 42;;
  'exec '*) case "$*" in *awk*) echo 100;; *) echo '{"status":"ready","version":"0.1.1"}';; esac;;
  run*) echo anonymous-fixture;;
esac
''')
            docker.chmod(0o755)
            for error in ('fixture daemon unavailable', 'Error response from daemon: No such container: fixture'):
                result = subprocess.run(['sh', str(ROOT / 'release/verify_addon_upgrade.sh'),
                    'fixture:0.1.1-1', 'fixture:0.1.1-2', '0.1.1'], text=True, capture_output=True,
                    env=dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                             TMPDIR=str(root), FIXTURE_REMOVE_ERROR=error), timeout=10)
                if 'unavailable' in error:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('temporary data retained', result.stderr)
                    self.assertNotIn('upgrade verified', result.stdout)
                    retained = list(root.glob('ha-bridge-addon-upgrade.*'))
                    self.assertEqual(len(retained), 1)
                    self.assertTrue((retained[0] / 'data').is_dir())
                    shutil.rmtree(retained[0])
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(list(root.glob('ha-bridge-addon-upgrade.*')))


if __name__ == '__main__':
    unittest.main()
