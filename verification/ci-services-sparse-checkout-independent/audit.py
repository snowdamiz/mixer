"""Independent, offline services checkout review; --check is read-only."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import unittest

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PRODUCER = ROOT / 'verification/ci-services-sparse-checkout'
BASE = '9398732c23648a82097d5a72b02b1c77af818e41'
PRODUCER_SEAL = '244417580cacbd04fcb79685e5a15d376314320d9c70f40be49d2df2194f071f'
PATTERNS = ['/services/', '/contracts/release-v2.json']
INSERT = (b'        with:\n'
          b'          # Protocol tests also read the frozen descriptor outside services/.\n'
          b'          sparse-checkout-cone-mode: false\n'
          b'          sparse-checkout: |\n'
          b'            /services/\n'
          b'            /contracts/release-v2.json\n')
sha = lambda b: hashlib.sha256(b).hexdigest()


def members(folder, excluded):
    rows = []
    for path in sorted(folder.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file() and path.name not in excluded:
            body = path.read_bytes()
            rows.append({'path': str(path.relative_to(folder)), 'bytes': len(body), 'sha256': sha(body)})
    return rows


def producer_custody():
    value = json.loads((PRODUCER / 'seal.json').read_text())
    assert sha((PRODUCER / 'seal.json').read_bytes()) == PRODUCER_SEAL
    assert value['members'] == members(PRODUCER, {'seal.json'})
    assert value['member_count'] == 31 and value['member_bytes'] == 120762
    assert value['tree_sha256'] == sha(json.dumps(value['members'], sort_keys=True, separators=(',', ':')).encode())
    return value


def preserved(original, candidate):
    before, after = original.split(b'  services:\n', 1)
    old_service, old_tail = after.split(b'  swift-cache-state-fixture:\n', 1)
    new_before, new_after = candidate.split(b'  services:\n', 1)
    new_service, new_tail = new_after.split(b'  swift-cache-state-fixture:\n', 1)
    anchor = b'      - uses: actions/checkout@v4\n'
    return (before == new_before and old_tail == new_tail and
            old_service.replace(anchor, anchor + INSERT, 1) == new_service)


def select(paths, patterns):
    # The accepted policy contains only anchored directory and exact-file entries.
    assert patterns == PATTERNS
    return {p for p in paths if p.startswith('services/') or p == 'contracts/release-v2.json'}


def readonly():
    seal = json.loads((OUT / 'seal.json').read_text())
    rows = members(OUT, {'seal.json'})
    assert rows == seal['members']
    assert seal['tree_sha256'] == sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
    assert seal['member_count'] == len(rows) and seal['member_bytes'] == sum(x['bytes'] for x in rows)
    producer_custody()
    review = json.loads((OUT / 'review.json').read_text())
    assert sha((ROOT / '.github/workflows/verify.yml').read_bytes()) == review['workflow_sha256']
    assert (ROOT / '.github/workflows/verify.yml').read_bytes() == (PRODUCER / 'workflow-candidate.yml').read_bytes()
    manifest = json.loads((OUT / 'source-manifest.json').read_text())
    for row in manifest:
        body = (ROOT / row['path']).read_bytes()
        assert len(body) == row['bytes'] and sha(body) == row['sha256'], row['path']
    assert not (OUT / 'owned-scratch').exists()
    print(json.dumps({'result': 'read-only-custody-pass', 'seal_sha256': sha((OUT / 'seal.json').read_bytes()),
                      'members': len(rows), 'bytes': seal['member_bytes'], 'source_files': len(manifest)}))


def execute():
    assert not (OUT / 'review.json').exists() and not (OUT / 'owned-scratch').exists()
    scratch = OUT / 'owned-scratch'
    scratch.mkdir()
    (scratch / 'tmp').mkdir()
    env = dict(os.environ)
    env.update({'GOOS': 'linux', 'GOARCH': 'amd64', 'CGO_ENABLED': '1',
                'GOTOOLCHAIN': 'local', 'GOPROXY': 'off', 'GOSUMDB': 'off', 'GOENV': 'off', 'GOWORK': 'off',
                'GOMODCACHE': '/Users/andreyyurlov/go/pkg/mod', 'GOCACHE': str(scratch / 'go-cache'),
                'TMPDIR': str(scratch / 'tmp')})
    commands = []

    def run(name, argv, cwd=ROOT):
        start = time.monotonic()
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        pid, pgid = child.pid, os.getpgid(child.pid)
        timed = False
        signals = []
        try:
            stdout, stderr = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed = True
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(pgid, sig)
                    signals.append(sig.name)
                except ProcessLookupError:
                    pass
                try:
                    stdout, stderr = child.communicate(timeout=5)
                    break
                except subprocess.TimeoutExpired:
                    continue
            else:
                raise RuntimeError('owned command exceeded 55 seconds')
        try:
            os.killpg(pgid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        for suffix, data in [('stdout', stdout), ('stderr', stderr)]:
            (OUT / (name + '.' + suffix)).write_bytes(data)
        command = {'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': env,
                   'tool': str(Path(argv[0]).resolve()), 'tool_sha256': sha(Path(argv[0]).resolve().read_bytes()),
                   'pid': pid, 'pgid': pgid, 'exit': child.returncode, 'timed_out': timed,
                   'elapsed_seconds': time.monotonic() - start, 'signals_sent': signals,
                   'owned_child_reaped': True, 'owned_group_absent': absent,
                   'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)}
        commands.append(command)
        (OUT / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert child.returncode == 0 and absent and not timed, name
        return stdout

    try:
        pseal = producer_custody()
        workflow = (ROOT / '.github/workflows/verify.yml').read_bytes()
        assert workflow == (PRODUCER / 'workflow-candidate.yml').read_bytes()
        git = '/opt/homebrew/bin/git'
        go = '/Users/andreyyurlov/.local/share/megpt-ios/go1.26.4/bin/go'
        run('git-version', [git, '--version'])
        run('source-revision', [git, 'rev-parse', 'HEAD'])
        original = run('base-workflow', [git, 'show', BASE + ':.github/workflows/verify.yml'])
        assert original == (PRODUCER / 'original-workflow.stdout').read_bytes()
        assert preserved(original, workflow)
        (OUT / 'workflow.diff').write_text(''.join(difflib.unified_diff(original.decode().splitlines(True),
            workflow.decode().splitlines(True), fromfile=BASE + '/verify.yml', tofile='candidate/verify.yml')))
        tree = run('selected-tree', [git, 'ls-tree', '-rzl', BASE, '--', 'services', 'contracts/release-v2.json'])
        rows = []
        for record in tree.split(b'\0'):
            if not record:
                continue
            meta, raw_path = record.split(b'\t', 1)
            mode, kind, oid, size = meta.decode().split()
            path = raw_path.decode()
            body = (ROOT / path).read_bytes()
            assert kind == 'blob' and mode in ('100644', '100755')
            assert not (ROOT / path).is_symlink()
            assert len(body) == int(size)
            assert hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == oid, path
            rows.append({'path': path, 'bytes': len(body), 'sha256': sha(body), 'git_blob': oid})
        assert rows == json.loads((PRODUCER / 'inputs.json').read_text())
        assert len(rows) == 153 and sum(x['bytes'] for x in rows) == 4379716
        (OUT / 'source-manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
        root_tree = run('root-tree', [git, 'ls-tree', '-zl', BASE])
        root_paths = {r.split(b'\t', 1)[1].decode() for r in root_tree.split(b'\0') if r}
        assert root_paths.isdisjoint({'go.mod', 'go.sum', 'go.work', 'go.work.sum', '.gitmodules', '.gitattributes'})
        assert (ROOT / 'services/go.mod').read_text().startswith('module mixer/services\n\ngo 1.26.0\n')
        assert '\nreplace ' not in (ROOT / 'services/go.mod').read_text()
        run('go-version', [go, 'version'], ROOT / 'services')
        packages_raw = run('linux-packages', [go, 'list', '-mod=readonly', '-json', './...'], ROOT / 'services')
        packages = []
        decoder = json.JSONDecoder()
        rest = packages_raw.decode().lstrip()
        while rest:
            item, end = decoder.raw_decode(rest)
            packages.append(item)
            rest = rest[end:].lstrip()
        expected_packages = {'mixer/services/' + x for x in ['cmd/mixer-service', 'internal/durable', 'internal/testutil', 'protocol', 'release', 'updater']}
        assert {p['ImportPath'] for p in packages} == expected_packages
        selected = {x['path'] for x in rows}
        package_files = []
        for package in packages:
            assert package['Module']['Path'] == 'mixer/services'
            assert 'Error' not in package and not package.get('Incomplete', False)
            directory = Path(package['Dir']).relative_to(ROOT)
            for field in ['GoFiles', 'CgoFiles', 'TestGoFiles', 'XTestGoFiles', 'EmbedFiles', 'TestEmbedFiles', 'XTestEmbedFiles', 'IgnoredGoFiles']:
                for name in package.get(field, []):
                    path = str(directory / name)
                    assert path in selected, path
                    package_files.append({'package': package['ImportPath'], 'field': field, 'path': path})
        release = next(p for p in packages if p['ImportPath'] == 'mixer/services/release')
        assert release['EmbedFiles'] == ['migrations/001_release.sql']
        assert set(release['IgnoredGoFiles']) == {'postgres_guards_integration_test.go', 'postgres_integration_test.go', 'postgres_v2_integration_test.go', 'postgres_v3_integration_test.go'}
        (OUT / 'package-files.json').write_text(json.dumps(package_files, indent=2) + '\n')
        positive = (PRODUCER / 'protocol-descriptor-positive.stdout').read_bytes()
        negative = (PRODUCER / 'protocol-descriptor-missing-contract.stdout').read_bytes()
        assert b'--- PASS: TestV2StaticCrossLanguageVectorAndFrozenDescriptor' in positive
        assert b'--- FAIL: TestV2StaticCrossLanguageVectorAndFrozenDescriptor' in negative
        assert b'../../contracts/release-v2.json: no such file or directory' in negative
        producer_receipt = json.loads((PRODUCER / 'receipt.json').read_text())
        for command in producer_receipt['commands']:
            assert command['exit'] == command['expected_exit'] and not command['timed_out']
            assert command['owned_child_reaped'] and command['owned_group_absent']
            for suffix in ('stdout', 'stderr'):
                assert sha((PRODUCER / (command['name'] + '.' + suffix)).read_bytes()) == command[suffix + '_sha256']
        assert not (PRODUCER / 'owned-scratch').exists()

        class SelectionControls(unittest.TestCase):
            def test_candidate_preserves_all_commands(self):
                self.assertTrue(preserved(original, workflow))
            def test_missing_contract_is_rejected(self):
                with self.assertRaises(AssertionError): select(selected, ['/services/'])
            def test_narrow_service_tree_is_rejected(self):
                with self.assertRaises(AssertionError): select(selected, ['/services/protocol/', PATTERNS[1]])
            def test_broad_contract_tree_is_rejected(self):
                with self.assertRaises(AssertionError): select(selected, [PATTERNS[0], '/contracts/'])
            def test_selection_includes_every_service_file(self):
                self.assertEqual(select(selected, PATTERNS), selected)
            def test_unrelated_roots_are_excluded(self):
                self.assertEqual(select(selected | {'vm/Cargo.toml', 'contracts/release-v3.json', 'verification/old/receipt.json'}, PATTERNS), selected)
            def test_race_command_cannot_change(self):
                self.assertFalse(preserved(original, workflow.replace(b'go test -race ./...', b'go test ./...')))
            def test_vet_command_cannot_change(self):
                self.assertFalse(preserved(original, workflow.replace(b'go vet ./...', b'go vet ./protocol')))
            def test_go_version_cannot_change(self):
                self.assertFalse(preserved(original, workflow.replace(b"go-version: '1.26.4'", b"go-version: '1.26.3'")))
            def test_timeout_cannot_change(self):
                self.assertFalse(preserved(original, workflow.replace(b'timeout-minutes: 15', b'timeout-minutes: 30')))
            def test_cone_mode_cannot_change(self):
                changed = workflow.replace(INSERT, INSERT.replace(b'cone-mode: false', b'cone-mode: true'))
                self.assertFalse(preserved(original, changed))
            def test_other_jobs_cannot_change(self):
                self.assertFalse(preserved(original, workflow.replace(b'cargo test --locked', b'cargo test', 1)))

        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelectionControls))
        assert result.wasSuccessful() and result.testsRun == 12
        assert workflow == (ROOT / '.github/workflows/verify.yml').read_bytes()
        producer_custody()
        review = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'base': BASE,
                  'result': 'accept-checkout-selection-with-explicit-limits', 'workflow_sha256': sha(workflow),
                  'producer_seal_sha256': PRODUCER_SEAL, 'producer_members': pseal['member_count'],
                  'producer_member_bytes': pseal['member_bytes'], 'selected_files': len(rows),
                  'selected_service_files': len(rows) - 1, 'selected_bytes': sum(x['bytes'] for x in rows),
                  'linux_packages': sorted(expected_packages), 'package_file_records': len(package_files),
                  'independent_control_methods': result.testsRun, 'producer_host_positive_and_negative_reviewed': True,
                  'producer_numeric_pid_pgid_available': False, 'full_service_suite_run_by_reviewer': False,
                  'remote_changed_job_result': 'pending; historical run40545367451 job122334424079 cancelled during checkout with no tests',
                  'product_runtime_or_native_or_capture_started': False, 'global_process_inventory': False,
                  'git_mutations': False, 'owned_scratch_removed': False}
    finally:
        shutil.rmtree(scratch)
    review['owned_scratch_removed'] = not scratch.exists()
    (OUT / 'review.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps({'result': review['result'], 'controls': result.testsRun, 'packages': len(packages),
                      'selected_files': len(rows), 'owned_scratch_removed': review['owned_scratch_removed']}))


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        readonly()
    else:
        assert sys.argv[1:] == ['--run']
        execute()
