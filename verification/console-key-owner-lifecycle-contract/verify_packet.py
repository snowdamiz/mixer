#!/usr/bin/env python3
"""Bounded read-only packet/source hash audit; executes no product runtime."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys
import time

started = time.monotonic()
parser = argparse.ArgumentParser()
parser.add_argument('--require-freeze', action='store_true')
args = parser.parse_args()
packet = Path(__file__).resolve().parent
root = packet.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
errors = []
source = json.loads((packet / 'source-bindings.json').read_text())
evidence = json.loads((packet / 'reviewed-evidence.json').read_text())
checked = 0
for group in [source['sources'], evidence['files']]:
    for item in group:
        for p in [root / item['path'], packet / item['snapshot']]:
            if not p.is_file() or sha(p) != item['sha256']:
                errors.append('pin mismatch: ' + str(p))
            checked += 1
        ranges = item.get('line_ranges', [])
        lines = (packet / item['snapshot']).read_text().splitlines()
        if not all(1 <= a <= b <= len(lines) for a, b in ranges):
            errors.append('invalid source range: ' + item['path'])
expected = '3700d4fd7f89a52de22967e510289745f8ed8aad3bbf7ff7e0a0c2fa88a9fa33'
if evidence['accepted_freeze_sha256'] != expected:
    errors.append('accepted freeze identity mismatch')
for item in evidence['identity_source_comparisons']:
    old = root / 'verification/console-dispatcher-default-authority-slice' / item['candidate'] / 'inputs' / item['canonical']
    if sha(old) != item['sha256'] or sha(root / item['canonical']) != item['sha256'] or not item['matches_current']:
        errors.append('historical/current comparison mismatch: ' + str(old))
    checked += 2
prospective = json.loads((packet / 'prospective-tests.json').read_text())
if len(prospective['tests']) != 9 or prospective['execution_authorized_by_this_packet']:
    errors.append('prospective test contract mismatch')
if prospective['first_boundary'] != ['KOL01','KOL02','KOL03','KOL04','KOL05','KOL06','KOL07']:
    errors.append('first implementation boundary mismatch')
freeze_path = packet / 'freeze.json'
frozen_count = 0
if freeze_path.is_file():
    freeze = json.loads(freeze_path.read_text())
    expected_paths = set()
    for item in freeze['files']:
        p = packet / item['path']
        expected_paths.add(item['path'])
        if not p.is_file() or sha(p) != item['sha256'] or p.stat().st_size != item['bytes']:
            errors.append('frozen packet mismatch: ' + item['path'])
        frozen_count += 1
    actual_paths = {str(p.relative_to(packet)) for p in packet.rglob('*') if p.is_file() and p.name != 'freeze.json'}
    if expected_paths != actual_paths:
        errors.append('frozen packet file set mismatch')
    tree = hashlib.sha256(''.join(item['path']+'\0'+item['sha256']+'\n' for item in sorted(freeze['files'],key=lambda v:v['path'])).encode()).hexdigest()
    if tree != freeze['packet_tree_sha256']:
        errors.append('frozen packet tree mismatch')
elif args.require_freeze:
    errors.append('freeze required but absent')
result = {
    'schema': 1,
    'status': 'passed-source-only-hash-audit' if not errors else 'failed-source-only-hash-audit',
    'created_at': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 -B verification/console-key-owner-lifecycle-contract/verify_packet.py' + (' --require-freeze' if args.require_freeze else ''),
    'python': sys.version,
    'source_revision': source['source_revision'],
    'source_git_tree': source['git_tree'],
    'source_tree_sha256': source['source_tree_sha256'],
    'source_files': len(source['sources']),
    'evidence_files': len(evidence['files']),
    'historical_identity_source_comparisons': len(evidence['identity_source_comparisons']),
    'pin_comparisons': checked,
    'prospective_tests': len(prospective['tests']),
    'behavioral_tests_executed': 0,
    'product_changes': 0,
    'frozen_files_checked': frozen_count,
    'scope': 'Read-only local source/evidence/packet byte and source-range audit. Does not validate Elixir syntax, lifecycle behavior, callbacks, application startup, TLS drain, provider/custody, browser/session/HTTP, SQL, native, FieldLog or GA.',
    'new_processes': 'Only this bounded Python audit; no BEAM/compiler/DB/network fixture/native/capture processes.',
    'errors': errors,
    'elapsed_seconds': round(time.monotonic() - started, 6),
}
print(json.dumps(result, indent=2))
sys.exit(1 if errors else 0)
