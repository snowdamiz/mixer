#!/usr/bin/env python3
"""Checkpoint only completed runtime follow-up evidence and root tracking edits."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
EXPECTED_HEAD = 'c531cfc81cf89cdd591835fedd1dba5a414d31c9'
TRACKERS = ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json']
FINISHED = ['runtime-followup-observation', 'android-api28-image-install',
            'android-lower-api-availability', 'generated-java-ci-integration-review']


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    out = HERE / 'commands'
    out.mkdir()
    spec = importlib.util.spec_from_file_location('generated_java',
        ROOT / 'scripts/ci/check-android-generated-java.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    commands = runner.Commands(out, dict(os.environ), seconds=300, command_seconds=120)
    result = {'schema': 1, 'startedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Local evidence checkpoint only; no compiler, native test, or push',
              'expectedParent': EXPECTED_HEAD}
    try:
        result['gitVersion'] = commands.run('git-version', ['git', '--version']).strip()
        head = commands.run('parent', ['git', 'rev-parse', 'HEAD']).strip()
        if head != EXPECTED_HEAD:
            raise RuntimeError('Parent changed')
        if commands.run('index-before', ['git', 'diff', '--cached', '--name-only']).strip():
            raise RuntimeError('Index already contains another selection')
        dirty = commands.run('tracked-before', ['git', 'diff', '--name-only']).splitlines()
        if set(dirty) != set(TRACKERS):
            raise RuntimeError('Unexpected tracked changes')
        commands.run('whitespace', ['git', 'diff', '--check'])
        members = [ROOT / name for name in TRACKERS]
        for name in FINISHED:
            members.extend(sorted((BASE / name).rglob('*')))
        members.append(Path(__file__).resolve())
        members = [p for p in members if p.is_file()]
        if any(p.is_symlink() or p.stat().st_size > 5_000_000 for p in members):
            raise RuntimeError('Unexpected evidence link or size')
        identities = {str(p.relative_to(ROOT)): digest(p) for p in members}
        selection = HERE / 'selection.json'
        selection.write_text(json.dumps({'schema': 1, 'parent': head,
            'scope': result['scope'], 'members': identities,
            'excludes': ['active repair namespaces', 'raw APKs', 'sealed simulator products',
                         'product source changes', 'all unrelated untracked files'],
            'GAQualified': False}, indent=2) + '\n')
        paths = sorted([*identities, str(selection.relative_to(ROOT))])
        for path, identity in identities.items():
            if digest(ROOT / path) != identity:
                raise RuntimeError('Input changed before staging: ' + path)
        commands.run('stage-selection', ['git', 'add', '--', *paths])
        staged = commands.run('index-selection', ['git', 'diff', '--cached', '--name-only']).splitlines()
        if set(staged) != set(paths):
            raise RuntimeError('Staged selection differs')
        raw = commands.run('index-objects', ['git', 'ls-files', '--stage', '-z', '--', *paths])
        for row in raw.split('\0'):
            if not row:
                continue
            metadata, path = row.split('\t', 1)
            mode, object_id, stage = metadata.split()
            data = (ROOT / path).read_bytes()
            expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if object_id != expected or stage != '0' or mode not in ('100644', '100755'):
                raise RuntimeError('Staged bytes differ: ' + path)
        commands.run('commit', ['git', 'commit', '-m',
            'Record Android callback and lower-API preparation failures'])
        result['revision'] = commands.run('head', ['git', 'rev-parse', 'HEAD']).strip()
        parent = commands.run('committed-parent', ['git', 'rev-parse', 'HEAD^']).strip()
        changed = commands.run('committed-paths', ['git', 'diff-tree', '--no-commit-id',
            '--name-only', '-r', 'HEAD']).splitlines()
        if parent != head or set(changed) != set(paths):
            raise RuntimeError('Committed selection differs')
        if commands.run('index-after', ['git', 'diff', '--cached', '--name-only']).strip():
            raise RuntimeError('Index changed after commit')
        for path, identity in identities.items():
            if digest(ROOT / path) != identity:
                raise RuntimeError('Input changed after commit: ' + path)
        result.update(status='PASS', paths=len(paths), forcePush=False, pushed=False)
    except Exception as error:
        result.update(status='FAIL', error=str(error))
        raise
    finally:
        result['terminalCustody'] = commands.custody_terminal()
        result['commands'] = commands.records
        (HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'commands'}))


if __name__ == '__main__':
    main()
