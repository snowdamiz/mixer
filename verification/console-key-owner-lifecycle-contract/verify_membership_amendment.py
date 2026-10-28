#!/usr/bin/env python3
"""Read-only exact-path membership audit; preserves the original verifier."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys
import time

started = time.monotonic()
parser = argparse.ArgumentParser()
parser.add_argument('--prepare', action='store_true')
args = parser.parse_args()
packet = Path(__file__).resolve().parent
terminal_relative = 'membership-amendment.json'
terminal_path = packet / terminal_relative
original_digest = '85f2376f7f8ba7628890336f08e2dc59935dce922da2f8f908b940e08452f752'
upstream_relative = 'inputs/verification/console-dispatcher-default-authority-slice/freeze.json'
upstream_digest = '3700d4fd7f89a52de22967e510289745f8ed8aad3bbf7ff7e0a0c2fa88a9fa33'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
errors = []
original = json.loads((packet / 'freeze.json').read_text())
if sha(packet / 'freeze.json') != original_digest:
    errors.append('original terminal seal changed')
original_paths = set()
for item in original['files']:
    relative = item['path']
    p = packet / relative
    original_paths.add(relative)
    if not p.is_file() or p.stat().st_size != item['bytes'] or sha(p) != item['sha256']:
        errors.append('original packet file changed: ' + relative)
if not (packet / upstream_relative).is_file() or sha(packet / upstream_relative) != upstream_digest:
    errors.append('copied upstream terminal seal changed')
original_paths.update(['freeze.json', upstream_relative])
if len(original_paths) != 30:
    errors.append('unexpected original packet baseline size')

actual = set()
for p in packet.rglob('*'):
    if p.is_symlink():
        errors.append('symlink not allowed: ' + str(p.relative_to(packet)))
    elif p.is_file():
        relative = str(p.relative_to(packet))
        if relative != terminal_relative:
            actual.add(relative)

sealed = set()
if args.prepare:
    if terminal_path.exists():
        errors.append('preparation cannot rerun after terminal seal exists')
else:
    if not terminal_path.is_file():
        errors.append('amendment terminal seal absent')
    else:
        terminal = json.loads(terminal_path.read_text())
        for item in terminal['files']:
            relative = item['path']
            parts = Path(relative).parts
            if Path(relative).is_absolute() or '..' in parts or relative == terminal_relative:
                errors.append('invalid sealed path: ' + relative)
                continue
            if relative in sealed:
                errors.append('duplicate sealed path: ' + relative)
                continue
            sealed.add(relative)
            p = packet / relative
            if not p.is_file() or p.stat().st_size != item['bytes'] or sha(p) != item['sha256']:
                errors.append('amendment pin mismatch: ' + relative)
        if actual != sealed:
            errors.append('file-set mismatch: ' + json.dumps({'unlisted': sorted(actual-sealed), 'missing': sorted(sealed-actual)}))
        tree_digest = hashlib.sha256(''.join(v['path']+'\0'+v['sha256']+'\n' for v in sorted(terminal['files'],key=lambda v:v['path'])).encode()).hexdigest()
        if tree_digest != terminal['packet_tree_sha256']:
            errors.append('amendment tree digest mismatch')
        if terminal['sole_excluded_packet_relative_path'] != terminal_relative:
            errors.append('terminal exclusion mismatch')
        if not original_paths.issubset(sealed):
            errors.append('original packet not fully sealed by amendment')
        if terminal['original_freeze_sha256'] != original_digest:
            errors.append('original seal binding mismatch')
        if terminal['omitted_upstream_seal']['path'] != upstream_relative or terminal['omitted_upstream_seal']['sha256'] != upstream_digest:
            errors.append('upstream seal binding mismatch')

result = {
    'schema': 1,
    'status': ('passed-baseline-preparation-only' if args.prepare else 'passed-complete-packet-membership') if not errors else 'failed',
    'created_at': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 -B verification/console-key-owner-lifecycle-contract/verify_membership_amendment.py' + (' --prepare' if args.prepare else ''),
    'python': sys.version,
    'scope': 'Read-only packet integrity and exact membership audit; no product runtime, compiler, network fixture, or current canonical behavior verification.',
    'original_freeze_sha256': original_digest,
    'original_listed_files_unchanged': len(original['files']),
    'original_total_files_including_both_seals': len(original_paths),
    'sole_excluded_packet_relative_path': terminal_relative,
    'inventory_uses_basename_exclusion': False,
    'copied_upstream_seal_sha256': sha(packet / upstream_relative),
    'observed_nonterminal_files': len(actual),
    'sealed_nonterminal_files_verified': len(sealed),
    'complete_membership_verified': not args.prepare and not errors,
    'errors': errors,
    'elapsed_seconds': round(time.monotonic() - started, 6),
}
if not args.prepare and terminal_path.is_file():
    result['amendment_sha256'] = sha(terminal_path)
print(json.dumps(result, indent=2))
sys.exit(1 if errors else 0)
