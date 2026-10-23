#!/usr/bin/env python3
"""Replay original release-v2 review tests in a private immutable Git export."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = '16f6175441565adf5d1a2dc13bf2a591e65518e6'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default=PIN)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.isascii() or not args.name.replace('-', '').replace('_', '').isalnum() or len(args.name) > 80:
        parser.error('bounded ASCII evidence name required')
    output = HERE / 'evidence' / args.name
    output.mkdir(parents=True, exist_ok=False)
    work = Path(tempfile.mkdtemp(prefix='mixer-release-v2-review-'))
    record = {'schema': 1, 'status': 'running', 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'Independent original adversarial host tests of explicit release-v2 HTTP composition, storage variant dispatch, durability, RBAC/tenant binding and replay. No device/OTA/GA claim.',
              'reviewer': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'}, 'commands': [],
              'limitations': ['Tests use a private frozen local source export and in-process HTTP handlers; actual loopback HTTP/public Swift/real PostgreSQL are separately matched implementing-lane evidence.',
                              'Non-executable original public TEST payloads and deterministic public Ed25519 test keys only.',
                              'No native guest imports, activation, signing service, hosted identity/operations, production publication, outbox dispatch, immutable external FieldLog adoption, physical iOS/Android or GA qualification.',
                              'Phones remain disconnected; no physical-device command was attempted.']}
    env = {key: value for key, value in os.environ.items() if key in {'HOME', 'USER', 'LOGNAME', 'PATH', 'TMPDIR', 'LANG', 'TERM'} or key.startswith('LC_')}
    env.update(GOTOOLCHAIN='go1.26.4', PYTHONDONTWRITEBYTECODE='1')

    def run(name, argv, cwd=ROOT, timeout=180):
        argv = [str(item) for item in argv]
        if not Path(argv[0]).is_absolute():
            argv[0] = shutil.which(argv[0]) or argv[0]
        command = {'name': name, 'argv': argv, 'cwd': str(cwd), 'executable_sha256': sha(Path(argv[0]).resolve())}
        record['commands'].append(command)
        started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
            command['exit_code'] = result.returncode
            for label, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
                path = output / (name + '.' + label)
                path.write_bytes(data)
                command[label] = {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(path)}
            print(name + ': ' + str(result.returncode), flush=True)
            if result.returncode != 0:
                raise RuntimeError('command failed: ' + name)
            return result.stdout.decode()
        finally:
            command['elapsed_host_development_seconds'] = round(time.monotonic() - started, 6)

    try:
        revision = run('revision', ['git', 'rev-parse', args.revision + '^{commit}']).strip()
        record['source_revision'] = revision
        archive = work / 'services.tar'
        run('export-source', ['git', 'archive', '--format=tar', '--output=' + str(archive), revision, 'services'])
        record['archive_sha256'] = sha(archive)
        with tarfile.open(archive) as stream:
            stream.extractall(work / 'source', filter='data')
        source = work / 'source' / 'services'
        original = {str(path.relative_to(source)): sha(path) for path in sorted(source.rglob('*')) if path.is_file()}
        record['immutable_export_manifest'] = original
        record['immutable_export_digest'] = hashlib.sha256(json.dumps(original, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        # Run only independently authored probes; never depend on implementing
        # lane test helpers, fixture constructors, assertion logic or test data.
        removed = []
        for path in source.rglob('*_test.go'):
            removed.append(str(path.relative_to(source)))
            path.unlink()
        record['excluded_original_test_files'] = sorted(removed)
        tests = HERE / 'independent_test.go'
        target = source / 'release' / 'independent_review_test.go'
        shutil.copyfile(tests, target)
        record['original_review_test_sha256'] = sha(tests)
        record['runner_sha256'] = sha(Path(__file__))
        record['go_version'] = run('go-version', ['go', 'version'], source).strip()
        record['go_environment'] = run('go-environment', ['go', 'env', 'GOROOT', 'GOOS', 'GOARCH'], source).strip()
        record['python_version'] = run('python-version', [os.sys.executable, '--version']).strip()
        record['host_os'] = run('host-os', ['/usr/bin/sw_vers']).strip()
        run('independent-vet', ['go', 'vet', './release'], source)
        run('independent-race', ['go', 'test', '-race', '-count=1', '-json', './release', '-run', '^TestReview'], source)
        rows = [json.loads(line) for line in (output / 'independent-race.stdout').read_text().splitlines()]
        passed = [row['Test'] for row in rows if row.get('Action') == 'pass' and row.get('Test')]
        failed = [row.get('Test', '<package>') for row in rows if row.get('Action') == 'fail']
        skipped = [row.get('Test', '<package>') for row in rows if row.get('Action') == 'skip']
        record['test_counts'] = {'top_level': len([name for name in passed if '/' not in name]), 'executions_including_subtests': len(passed), 'failed': failed, 'skipped': skipped, 'passed_names': passed}
        if len([name for name in passed if '/' not in name]) != 9 or failed or skipped:
            raise RuntimeError('independent test count/failure/skip contract differs')
        unchanged = all((source / name).is_file() and sha(source / name) == digest for name, digest in original.items() if name not in removed)
        if not unchanged or sha(target) != record['original_review_test_sha256'] or sha(tests) != record['original_review_test_sha256']:
            raise RuntimeError('frozen source or original probes changed during execution')
        record['immutable_product_source_unchanged'] = True
        record['status'] = 'passed-independent-original-adversarial-host-probes'
    except BaseException as error:
        record['status'] = 'failed'
        record['failure'] = str(error)
        raise
    finally:
        shutil.rmtree(work)
        record['private_export_removed'] = not work.exists()
        record['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'status': record['status'], 'source_revision': revision, 'tests': record['test_counts'], 'receipt': str(output / 'receipt.json')}, indent=2))


if __name__ == '__main__':
    main()
