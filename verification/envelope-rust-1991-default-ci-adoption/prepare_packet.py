#!/usr/bin/env python3
"""Data-only reproducible packet construction; never installs the proposed workflow."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import offline_guard
offline_guard.install(HERE)
import difflib
import hashlib
import json

ROOT = HERE.parents[1]
OLD = ROOT / 'verification/envelope-partition-default-ci-adoption'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def row(base, path):
    data = path.read_bytes()
    return {'path': path.relative_to(base).as_posix(), 'bytes': len(data), 'sha256': digest(data)}


def manifest(rows, **extra):
    rows = sorted(rows, key=lambda item: item['path'])
    assert len(rows) == len({item['path'] for item in rows})
    return {'schema': 1, 'members': rows, 'member_count': len(rows),
            'total_bytes': sum(item['bytes'] for item in rows),
            'tree_sha256': digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()), **extra}


def prepare():
    old = json.loads((OLD / 'dependencies.json').read_bytes())
    old_seal = json.loads((OLD / 'seal.json').read_bytes())
    assert old['member_count'] == 93 and old_seal['member_count'] == 17
    rows = old['members'] + [row(ROOT, OLD / item['path']) for item in old_seal['members']]
    rows.append(row(ROOT, OLD / 'seal.json'))
    assert len(rows) == 111
    save('dependencies.json', manifest(rows,
        closure_scope='93 unchanged historical inputs plus all17 sealed historical adoption members and its seal;111 distinct preservation bindings',
        compiler_policy={'source': 'scripts/ci/check-analyzer-envelope.py',
            'exact_function_reused': 'rustc_identity', 'original_resolver_delegations': 1,
            'historical_selector_delegation': True,
            'prospective_selection': 'verification/envelope-rust-1991-default-ci-adoption/compiler-selection.json',
            'prospective_selection_sha256': '07db30ea3a63e0a30b8b5762e18255a0e0bc720945ac813b6b7e017aec9edd5c',
            'installer_retry_fallback': False}, fixture_source=old['fixture_source']))
    before = (HERE / 'workflow/original-verify.yml').read_text()
    sparse = '            /verification/envelope-partition-default-ci-adoption/\n'
    sparse_after = sparse + '            /verification/envelope-rust-1991-default-ci-adoption/\n'
    start = before.index('      - name: Bind reviewed envelope partition source and ordinary compiler policy\n')
    end = before.index('  swift-capability-native:\n', start)
    # Preserve any later Swift steps; only the fixed envelope group is selected.
    old_span = before[start:end]
    final_line = '            ${{ github.workspace }}/.github/workflows/verify.yml\n'
    cut = old_span.index(final_line) + len(final_line)
    old_span = old_span[:cut]
    new_span = old_span.replace('MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/envelope-partition-default-ci-adoption"',
                               'MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/envelope-rust-1991-default-ci-adoption"')
    new_span = new_span.replace('Bind reviewed envelope partition source and ordinary compiler policy',
                               'Bind reviewed envelope and prospective compiler selection')
    new_span = new_span.replace('Guarded envelope partition and ordinary adoption controls',
                               'Guarded envelope and prospective compiler adoption controls')
    new_span = new_span.replace('Accepted standalone analyzer fixture envelope',
                               'Standalone analyzer envelope with prospectively selected compiler')
    new_span = new_span.replace('Verify envelope partition adoption source postflight',
                               'Verify prospective envelope adoption source postflight')
    new_span = new_span.replace('            ${{ github.workspace }}/verification/envelope-partition-default-ci-adoption/\n',
        '            ${{ github.workspace }}/verification/envelope-partition-default-ci-adoption/\n'
        '            ${{ github.workspace }}/verification/envelope-rust-1991-default-ci-adoption/\n')
    changes = [{'label': 'one new adoption sparse path', 'before': sparse, 'after': sparse_after},
               {'label': 'existing envelope group only', 'before': old_span, 'after': new_span}]
    after = before
    for item in changes:
        assert after.count(item['before']) == 1
        after = after.replace(item['before'], item['after'])
    def job(text):
        return text.split('  swift:\n', 1)[1].split('  swift-capability-native:\n', 1)[0]
    (HERE / 'workflow/swift-job.yml').write_text('  swift:\n' + job(after))
    (HERE / 'workflow/original-swift-job.yml').write_text('  swift:\n' + job(before))
    (HERE / 'workflow/envelope-steps.yml').write_text(new_span)
    save('workflow/changes.json', {'schema': 1, 'changes': changes})
    (HERE / 'workflow.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='a/.github/workflows/verify.yml', tofile='b/.github/workflows/verify.yml')))


def seal():
    rows = []
    for path in HERE.rglob('*'):
        relative = path.relative_to(HERE)
        if relative.parts[0] in {'logs', 'control-scratch', '__pycache__'} or relative.as_posix() == 'seal.json':
            continue
        assert not path.is_symlink()
        if path.is_file(): rows.append(row(HERE, path))
    save('seal.json', manifest(rows,
        scope='Prospective exact Rust1.99.1 ordinary envelope derivative; source and synthetic controls only; actual qualification pending; logs/control scratch excluded'))


if __name__ == '__main__':
    assert sys.argv[1:] in [[], ['--seal-only']]
    if not sys.argv[1:]: prepare()
    seal()
