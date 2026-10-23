#!/usr/bin/env python3
"""Audit frozen I/O qualification and independent review without rebuilding."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW = ROOT / 'verification/capability-durable-io-review'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def require(ok, name):
    if not ok:
        raise RuntimeError(name)

def main():
    inputs = json.loads((HERE / 'inputs.json').read_text())
    host = json.loads((HERE / 'receipt.json').read_text())
    cross = json.loads((HERE / 'cross-receipt.json').read_text())
    final_path = REVIEW / 'final-receipt.json'
    require(digest(final_path) == 'd9da45c178c57df971b8de565aaaab7bedafb4d0aa72da28c97dcc082b497ce9', 'review seal')
    final = json.loads(final_path.read_text())
    require(host['status'] == cross['status'] == 'passed', 'owner status')
    require(len(inputs['files']) == 139 and len(inputs['new_files']) == 5, 'source counts')
    for name, expected in inputs['files'].items():
        require(digest(Path(inputs['source']) / name) == expected, 'frozen source ' + name)
    for name in inputs['new_files']:
        require(digest(ROOT / name) == inputs['files'][name], 'live I/O source ' + name)
    for command in host['commands'] + cross['commands']:
        log = HERE / (command['name'] + '.log')
        require(command['exit_code'] == 0 and digest(log) == command['log_sha256'], 'command ' + command['name'])
        if command['name'] in ('debug', 'release', 'tsan'):
            counts = re.findall(rb'Executed (\d+) tests, with 0 failures', log.read_bytes())
            require(counts == [b'7', b'16', b'23', b'23'], 'test count ' + command['name'])
    artifact_count = 0
    for artifacts in cross['artifacts'].values():
        for name, expected in artifacts.items():
            require(digest(Path(name)) == expected, 'cross artifact ' + name)
            artifact_count += 1
    for name, expected in final['owner_receipts'].items():
        require(digest(ROOT / name) == expected, 'review owner receipt ' + name)
    probe_path = ROOT / final['probe_receipt']['path']
    require(digest(probe_path) == final['probe_receipt']['sha256'], 'independent probe receipt')
    probe = json.loads(probe_path.read_text())
    for command in probe['commands']:
        require(command['exit_code'] == command['expected_exit'], 'review command ' + command['name'])
        require(digest(ROOT / command['log']) == command['sha256'], 'review log ' + command['name'])
    for key in ('reused_debug_library', 'probe_binary'):
        require(digest(Path(probe[key]['path'])) == probe[key]['sha256'], key)
    require(probe['probe_checks'] == 29, 'independent check count')
    manifest = REVIEW / 'evidence-manifest.sha256'
    require(digest(manifest) == final['evidence_manifest_sha256'], 'review manifest')
    rows = manifest.read_text().splitlines()
    require(len(rows) == final['evidence_files'] == 9, 'review evidence count')
    for row in rows:
        expected, name = row.split('  ', 1)
        require(digest(ROOT / name) == expected, 'review evidence ' + name)
    for name, expected in final['old_io_preserved'].items():
        baseline = subprocess.check_output(['git', 'show', '61f34bf:' + name], cwd=ROOT)
        require(hashlib.sha256(baseline).hexdigest() == expected and (ROOT / name).read_bytes() == baseline, 'old I/O preservation ' + name)
    receipt = {
        'status': 'private I/O foundation qualified and independently reviewed; root audit passed',
        'source_manifest_sha256': inputs['manifest_sha256'], 'frozen_sources_verified': 139,
        'live_new_sources_verified': 5, 'host_tests_per_mode': 23, 'host_modes': ['debug', 'release', 'Swift TSan'],
        'cross_artifacts_verified': artifact_count, 'independent_checks': 29,
        'independent_final_receipt_sha256': digest(final_path), 'independent_evidence_files_verified': 9,
        'evidence_sha256': {p.name: digest(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'final-receipt.json'},
        'scope': 'Private fd-relative durable I/O with bounded reads/chunks/state/inventory, exclusive lock, fsync and rename; old update I/O bytes preserved.',
        'limitations': [
            'Qualified against the frozen installed-material dependency graph; current unfinished store and bridge lifecycle changes are not included.',
            'Independent probe uses labelled @testable access to the unchanged library; this is not a public API or authority claim.',
            'iOS and Android module/object compilation only. FIFO behavior observed on Darwin; no device or application execution.',
            'Product actor scheduling, durable signed selection, lifecycle ownership, health/recovery and GA gates remain open.'
        ]
    }
    (HERE / 'final-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'frozen_sources_verified', 'host_tests_per_mode', 'independent_checks')}, indent=2))

if __name__ == '__main__':
    main()
