#!/usr/bin/env python3
"""Bind v4 and frozen v3/v2; no requirement to keep invalid v3 installed."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V3 = ROOT / 'verification/cache-fixture-compiler-admission-v3'
V3_SEAL = '966040b813f5bf0d771b140ebffee0081812caca04578a72a2c3d52f0c7c5cdc'
WORKFLOW = '.github/workflows/cache-fixture-workflow-context-v4.yml'
REJECTED = '.github/workflows/cache-fixture-compiler-admission-v3.yml'
REJECTED_SHA256 = 'eba3999e14305e3b4edcca6046536087f129a82598af195aa1db1239a453e25c'


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


def members(base, seal):
    rows = seal['members']
    need(rows == sorted(rows, key=lambda row: row['path'])
         and len({row['path'] for row in rows}) == len(rows) == seal['member_count'], 'Member order/count')
    need(digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
         == seal['tree_sha256'], 'Tree digest differs')
    need(sum(row['bytes'] for row in rows) == seal['total_bytes'], 'Total bytes differ')
    for row in rows:
        path = Path(row['path'])
        need(not path.is_absolute() and '..' not in path.parts and str(path) == row['path'], 'Invalid member')
        data = raw(base / path)
        need(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Member changed: ' + row['path'])
    observed = set()
    for item in base.rglob('*'):
        relative = item.relative_to(base)
        if relative.parts[0] in {'logs', 'control-scratch', '__pycache__'}:
            continue
        need(not item.is_symlink(), 'Extra symlink')
        if item.is_file():
            observed.add(relative.as_posix())
    need(observed == {row['path'] for row in rows} | {'seal.json'}, 'Shipping closure differs')


def verify(installed=False):
    own = json.loads(raw(HERE / 'seal.json'))
    members(HERE, own)
    v3raw = raw(V3 / 'seal.json')
    need(digest(v3raw) == V3_SEAL, 'Frozen v3 seal changed')
    # Bind imported source and every v3 member before executing its file verifier.
    frozen_seal = json.loads(v3raw)
    for row in frozen_seal['members']:
        data = raw(V3 / row['path'])
        need(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Frozen v3 member changed')
    spec = importlib.util.spec_from_file_location('frozen_v3_verifier', V3 / 'verify_candidate.py')
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    inputs = frozen.verify(False)
    need(digest(raw(V3 / 'workflow' / Path(REJECTED).name)) == REJECTED_SHA256,
         'Rejected original workflow changed')
    from workflow_context import parse, validate_contract
    context = validate_contract(parse(raw(HERE / 'workflow' / Path(WORKFLOW).name).decode()),
                                parse(raw(V3 / 'workflow' / Path(REJECTED).name).decode()))
    if installed:
        need(not (ROOT / REJECTED).exists() and not (ROOT / REJECTED).is_symlink(),
             'Rejected canonical v3 workflow must be retired')
        need(raw(ROOT / WORKFLOW) == raw(HERE / 'workflow' / Path(WORKFLOW).name),
             'Installed v4 workflow differs')
        v2 = frozen.V2
        need(raw(ROOT / '.github/workflows/cache-fixture-shared-input-controls-v2.yml')
             == raw(v2 / 'workflow/cache-fixture-shared-input-controls-v2.yml'),
             'Installed v2 workflow differs')
    return {'v4_tree_sha256': own['tree_sha256'], 'frozen_v3_seal_sha256': V3_SEAL,
            'frozen_v3': inputs, 'installed_v2_v4_bound_and_invalid_v3_absent': installed,
            'context_check': context}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-installed', action='store_true')
    print(json.dumps(verify(parser.parse_args().workflow_installed), sort_keys=True))
