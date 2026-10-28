#!/usr/bin/env python3
"""Seal this reviewer-owned packet after a final read-only source recheck."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
signal.alarm(30)


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec', 'os.kill', 'os.killpg'}:
        raise RuntimeError('finalization forbids external actions')


sys.addaudithook(audit)


def row(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


result = read(OUT / 'verification-result.json')
committed = read(OUT / 'committed-source.json')
assert result['passed'] and committed['passed']
for path, expected in result['sources']['canonical_bindings'].items():
    assert row((ROOT / path).read_bytes()) == expected
for path, expected in result['sources']['protected_and_inventory_sha256'].items():
    assert row((ROOT / path).read_bytes())['sha256'] == expected
outer_base = ROOT / 'verification/identity-network-image-amendment-v2'
outer = read(outer_base / 'packet-manifest.json')
assert outer['tree_digest_sha256'] == digest(outer['files']) == '878b66c7e21a5ca2da2b8fdc97275f302abc99da450c9acf9429bfdaaa78149a'
for path, expected in outer['files'].items():
    assert row((outer_base / path).read_bytes()) == expected
assert not any(path.is_dir() or path.is_symlink() for path in OUT.iterdir()), 'unexpected leftover temporary object'
decision = {
    'schema': 1,
    'at': datetime.now(timezone.utc).isoformat(),
    'reviewer': {'role': 'fresh independent difficult review', 'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh'},
    'verdict': 'source-accepted-for-root-selected-fresh-bounded-remote-identity-attempt',
    'blocking_findings': [],
    'canonical_tree_digest_sha256': result['sources']['canonical_tree_digest_sha256'],
    'canonical_bindings': result['sources']['canonical_bindings'],
    'metadata': {
        'files': 16,
        'amendment_sha256': 'b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c',
        'packet_tree_digest_sha256': '0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d',
        'packet_manifest_sha256': 'dcac91f5cae0a2495f79448a76098975edc18db0ce96a1e769106244a0cf8061',
    },
    'completed_v2_outer_packet': {'files': len(outer['files']), 'tree_digest_sha256': outer['tree_digest_sha256'], 'manifest': row((outer_base / 'packet-manifest.json').read_bytes()), 'all_files_rehashed': True},
    'source_revision': {k: committed[k] for k in ('HEAD', 'git_tree', 'source_files', 'source_tree_digest_sha256')},
    'canonical_controls': result['canonical_controls'],
    'independent_controls': result['independent_controls'],
    'forbidden_process_socket_pid_audit_events': result['forbidden_process_socket_pid_audit_events'],
    'command_receipts': [
        {'argv': ['python3', '-B', str(OUT.relative_to(ROOT) / 'review.py')], 'exit_code': 0, 'alarm_seconds': 50, 'stdout': 'review.stdout', 'stderr': 'review.stderr'},
        {'argv': ['python3', '-B', str(OUT.relative_to(ROOT) / 'verify_committed.py')], 'exit_code': 0, 'alarm_seconds': 30, 'readonly_git_commands': 3, 'each_git_timeout_seconds': 10, 'stdout': 'committed-source.stdout', 'stderr': 'committed-source.stderr'},
        {'argv': ['python3', '-B', str(OUT.relative_to(ROOT) / 'finalize.py')], 'alarm_seconds': 30, 'scope': 'source rehash and local review seal only'},
    ],
    'tools': {'python': result['python'], 'git': committed['git_version']},
    'unlock': {'owner': 'root', 'workflow': '.github/workflows/identity-network.yml', 'command': 'python3 -B hosted/scripts/test-identity-network.py --sha "$GITHUB_SHA" --output "$GITHUB_WORKSPACE/identity-network-evidence"', 'attempts': 1, 'scope': 'unchanged two Linux production-DNS/TLS methods followed by independent artifact acceptance'},
    'runtime_acceptance': False,
    'product_methods_run': 0,
    'pending': ['fresh actual mount and isolation observations', 'complete verified copy and direct Rebar execution', 'full bootstrap and locked dependency preparation', 'offline compilation and the unchanged two methods', 'fresh exact owned cleanup and independent artifact acceptance', 'all native/process/custody/provider/customer/GA holds'],
    'held_local_groups': [20745, 20770, 20780, 20817, 20842, 20851, 20866],
    'other_holds': ['prior local FieldLog compiler PID unknown and cleanup unverified', 'Android stopped-v5 held', 'native/UI/capture paused'],
    'cleanup': {'owned_test_temporary_directories_removed': True, 'leftover_subdirectories': 0, 'new_runtime_instances': 0, 'other_project_processes_untouched': True},
    'writes': str(OUT.relative_to(ROOT)) + '/ only',
    'canonical_or_metadata_edits': False,
    'commit_push_dispatch': False,
}
(OUT / 'decision.json').write_text(json.dumps(decision, sort_keys=True, indent=2) + '\n')
files = {path.name: row(path.read_bytes()) for path in sorted(OUT.iterdir()) if path.name != 'packet-manifest.json'}
packet = {'schema': 1, 'files': files, 'tree_digest_sha256': digest(files)}
(OUT / 'packet-manifest.json').write_text(json.dumps(packet, sort_keys=True, indent=2) + '\n')
print(json.dumps({'verdict': decision['verdict'], 'files': len(files), 'tree_digest_sha256': packet['tree_digest_sha256'], 'decision': row((OUT / 'decision.json').read_bytes()), 'packet_manifest': row((OUT / 'packet-manifest.json').read_bytes())}, sort_keys=True, indent=2))
