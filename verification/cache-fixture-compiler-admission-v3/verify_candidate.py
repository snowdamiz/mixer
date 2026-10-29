#!/usr/bin/env python3
"""File-only closure verification; import the reused v2 verifier only after binding it."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V2 = ROOT / 'verification/cache-fixture-shared-input-candidate-v2'
V2_SEAL = 'dd0dc7c030eb19e9763b547c2b9a45601997545e1e94a82f2a38ee76ca1bd591'
WORKFLOW = '.github/workflows/cache-fixture-compiler-admission-v3.yml'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def raw(path):
    for part in [*reversed(path.parents), path]:
        need(not part.is_symlink(), 'Symlink forbidden')
    need(path.is_file(), 'Regular file required')
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_members(base, seal):
    rows = seal['members']
    need(rows == sorted(rows, key=lambda row: row['path'])
         and len({row['path'] for row in rows}) == len(rows) == seal['member_count'],
         'Member order/count/duplicates')
    need(digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
         == seal['tree_sha256'], 'Tree digest differs')
    need(sum(row['bytes'] for row in rows) == seal['total_bytes'], 'Total bytes differ')
    for row in rows:
        member = Path(row['path'])
        need(not member.is_absolute() and '..' not in member.parts
             and str(member) == row['path'] and member.parts, 'Invalid member')
        value = raw(base / member)
        need(len(value) == row['bytes'] and digest(value) == row['sha256'],
             'Bound member differs: ' + row['path'])
    excluded = {'logs', 'runs', 'control-scratch', 'materialized', '__pycache__'}
    observed = set()
    for item in base.rglob('*'):
        relative = item.relative_to(base)
        if relative.parts[0] in excluded:
            continue
        need(not item.is_symlink(), 'Extra symlink')
        if item.is_file():
            observed.add(relative.as_posix())
    need(observed == {row['path'] for row in rows} | {'seal.json'}, 'Shipping closure differs')


def verify(installed=False):
    own = json.loads(raw(HERE / 'seal.json'))
    verify_members(HERE, own)
    v2_raw = raw(V2 / 'seal.json')
    need(digest(v2_raw) == V2_SEAL, 'Frozen v2 seal changed')
    verify_members(V2, {**json.loads(v2_raw), 'total_bytes': 286447})
    sys.path.insert(0, str(V2))
    try:
        spec = importlib.util.spec_from_file_location('frozen_v2_verifier', V2 / 'verify_candidate.py')
        frozen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(frozen)
        inputs = frozen.verify(installed)
    finally:
        sys.path.pop(0)
    if installed:
        need(raw(ROOT / WORKFLOW) == raw(HERE / 'workflow' / Path(WORKFLOW).name),
             'Installed v3 workflow differs from sealed candidate')
    return {'v3_tree_sha256': own['tree_sha256'], 'frozen_v2_seal_sha256': V2_SEAL,
            'installed_workflows_bound': installed, 'frozen_v2': inputs}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-installed', action='store_true')
    print(json.dumps(verify(parser.parse_args().workflow_installed), sort_keys=True))
