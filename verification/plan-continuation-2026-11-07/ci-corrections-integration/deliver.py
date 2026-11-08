#!/usr/bin/env python3
"""Deliver only the reviewed corrections and completed supporting evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
EXPECTED_HEAD = 'e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba'
TRACKED = ['AGENTS.md', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json',
           '.github/workflows/verify.yml',
           str((BASE / 'generated-java-ci-integration/bootstrap.py').relative_to(ROOT)),
           str((BASE / 'generated-java-ci-integration/test_bootstrap.py').relative_to(ROOT))]
FINISHED = ['android-api28-integrated', 'android-api28-packaging-review',
            'android-motion-thread-review', 'generated-java-pair9-actual',
            'generated-java-signature-fix', 'generated-java-signature-fix-r2',
            'generated-java-signature-review', 'generated-java-signature-review-r2',
            'cache-deadline-control-fix', 'cache-deadline-control-review',
            'cache-deadline-custody-hold', 'ci-e725-cache-failure',
            'ci-e725-generated-java-failure', 'generated-java-ci-delivery']


def identity(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError('Regular file required: ' + str(path))
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def evidence_files(directory):
    for base, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {'scratch', 'materialized', '__pycache__'}]
        for name in files:
            path = Path(base) / name
            if 'cache-deadline-control-fix/evidence/' in str(path) and name in {'check_cache_state.py', 'materialize_pack.py'}:
                continue
            yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    out = HERE / ('delivery-commands' if args.execute else 'selection-commands')
    out.mkdir()
    spec = importlib.util.spec_from_file_location('delivery_commands', ROOT / 'scripts/ci/check-android-generated-java.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    commands = runner.Commands(out, dict(os.environ), seconds=600, command_seconds=180)
    result = {'schema': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Reviewed CI corrections and accepted API28 harness; product pair8 unchanged',
              'expectedParent': EXPECTED_HEAD, 'nativeQualified': False, 'freshCIPending': True}
    selection_path = HERE / 'delivery-selection.json'
    try:
        runner.require(commands.run('head', ['git', 'rev-parse', 'HEAD']).strip() == EXPECTED_HEAD, 'Parent changed')
        runner.require(not commands.run('index-before', ['git', 'diff', '--cached', '--name-only']).strip(), 'Index already selected')
        dirty = commands.run('tracked-before', ['git', 'diff', '--name-only']).splitlines()
        runner.require(set(dirty) == set(TRACKED), 'Unexpected tracked edits')
        commands.run('whitespace', ['git', 'diff', '--check'])
        if not args.execute:
            paths = {ROOT / p for p in TRACKED}
            for name in FINISHED:
                paths.update(evidence_files(BASE / name))
            paths.update(evidence_files(HERE / 'commands'))
            paths.update(HERE / n for n in ['verify.py', 'deliver.py', 'installation.json',
                'prepared.json', 'verify.yml.proposed', 'preparation-1-failure.json'])
            paths.add(BASE / 'ci-e725-observation.json')
            acceptance = json.loads((BASE / 'android-api28-integrated/acceptance.json').read_text())
            for name, expected in acceptance['files'].items():
                runner.require(identity(ROOT / name) == expected, 'Accepted API28 source drift')
                paths.add(ROOT / name)
            # Include changed/new objects only, not unchanged evidence already in HEAD.
            candidates = sorted(str(p.relative_to(ROOT)) for p in paths)
            changed = set(dirty)
            untracked = commands.run('untracked-selection', ['git', 'ls-files', '--others',
                '--exclude-standard', '--', *candidates]).splitlines()
            selected = sorted(set(candidates) & (changed | set(untracked)))
            members = {name: identity(ROOT / name) for name in selected}
            runner.require(all(v['bytes'] <= 10_000_000 for v in members.values()), 'Unexpected large artifact')
            runner.require(sum(v['bytes'] for v in members.values()) <= 40_000_000, 'Delivery size bound')
            data = dict(result, members=members, paths=len(members), bytes=sum(v['bytes'] for v in members.values()),
                excludes=['active R2 work/reviews', 'held scratch', 'materialized pack copies', 'raw native APKs/products'])
            selection_path.write_text(json.dumps(data, indent=2) + '\n')
            result.update(status='PREPARED', paths=len(members), bytes=data['bytes'])
            return
        data = json.loads(selection_path.read_text())
        members = data['members']
        for path, expected in members.items():
            runner.require(identity(ROOT / path) == expected, 'Selected source drift: ' + path)
        remote = commands.run('remote-before', ['git', 'ls-remote', '--exit-code', 'origin', 'refs/heads/main']).split()
        runner.require(remote == [EXPECTED_HEAD, 'refs/heads/main'], 'Remote changed')
        paths = sorted([*members, str(selection_path.relative_to(ROOT))])
        commands.run('stage', ['git', 'add', '--', *paths])
        staged = commands.run('staged-paths', ['git', 'diff', '--cached', '--name-only']).splitlines()
        runner.require(set(staged) == set(paths), 'Staged path mismatch')
        objects = commands.run('staged-objects', ['git', 'ls-files', '--stage', '-z', '--', *paths])
        for row in objects.split('\0'):
            if not row:
                continue
            metadata, path = row.split('\t', 1)
            mode, object_id, stage = metadata.split()
            content = (ROOT / path).read_bytes()
            expected = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            runner.require(object_id == expected and stage == '0' and mode in {'100644', '100755'}, 'Staged object mismatch')
        commands.run('commit', ['git', 'commit', '-m', 'Fix CI package trust and cache deadline controls'])
        revision = commands.run('committed-head', ['git', 'rev-parse', 'HEAD']).strip()
        runner.require(commands.run('committed-parent', ['git', 'rev-parse', 'HEAD^']).strip() == EXPECTED_HEAD, 'Commit parent mismatch')
        changed = commands.run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()
        runner.require(set(changed) == set(paths), 'Commit path mismatch')
        runner.require(not commands.run('index-after', ['git', 'diff', '--cached', '--name-only']).strip(), 'Index changed')
        for path, expected in members.items():
            runner.require(identity(ROOT / path) == expected, 'Selected input changed after commit')
        commands.run('push', ['git', 'push', 'origin', 'HEAD:refs/heads/main'])
        remote_after = commands.run('remote-after', ['git', 'ls-remote', '--exit-code', 'origin', 'refs/heads/main']).split()
        runner.require(remote_after == [revision, 'refs/heads/main'], 'Remote verification failed; do not retry')
        result.update(status='DELIVERED', revision=revision, paths=len(paths), forcePush=False)
    except BaseException as error:
        result.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        result['terminalCustody'] = commands.custody_terminal()
        result['commands'] = str((out / 'commands.json').relative_to(ROOT))
        name = 'delivery-result.json' if args.execute else 'selection-result.json'
        (HERE / name).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
