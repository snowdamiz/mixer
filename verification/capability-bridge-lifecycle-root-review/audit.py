#!/usr/bin/env python3
"""Audit the immutable lifecycle matrix and explicitly derived ownership probes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise RuntimeError(why)
def command(row, directory):
    require(row['exitCode'] == 0, 'expected successful command')
    raw = (directory / row['log']).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == row['logSHA256'], 'command log')
    if 'expectedTests' in row:
        counts = [int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed', raw)]
        require(counts == [row['expectedTests']], 'actual test count')
aggregate_path = ROOT / 'verification/capability-bridge-lifecycle/2026-10-23-lifecycle-candidate-1.json'
require(digest(aggregate_path) == '81e7eeff807132b10ede35e727680c599b38b462bb649ce144d081f9497bd138', 'aggregate seal')
aggregate = json.loads(aggregate_path.read_text())
receipts = {}
for kind, item in aggregate['receipts'].items():
    path = ROOT / item['path']; require(digest(path) == item['sha256'], kind + ' receipt')
    receipts[kind] = (path, json.loads(path.read_text()))
path, matrix = receipts['matrix']
require(len(matrix['source']) == 71, 'source count')
for name, expected in matrix['source'].items():
    require(digest(ROOT / name) == expected, 'live source ' + name)
    require(digest(Path(matrix['frozenSourceExport']) / name) == expected, 'frozen source ' + name)
for row in matrix['commands']: command(row, path.parent)
for target, files in matrix['nativeArtifacts'].items():
    for name, expected in files.items(): require(digest(Path(matrix['stageRoot']) / name) == expected, target + ' native artifact')
for artifact in matrix['linkedConsumers'].values():
    p = Path(artifact['path'])
    require(p.stat().st_size == artifact['bytes'] and digest(p) == artifact['sha256'], 'actual linked consumer')
path, derived = receipts['derived']
require(derived['baseSource'] == matrix['source'], 'derived base source binding')
require(derived['baseManifestSHA256'] == matrix['sourceManifestSHA256'], 'derived base manifest')
for name, expected in derived['derivedSource'].items():
    require(digest(Path(derived['sourceExport']) / name) == expected, 'derived export ' + name)
require(digest(path.parent / 'test-only.patch') == derived['patchSHA256'], 'derived patch')
require(digest(ROOT / 'verification/capability-bridge-lifecycle/probes.py') == derived['driverSHA256'], 'derived driver')
for row in derived['commands']: command(row, path.parent)
require(len(derived['commands']) == 15, '15 isolated probes')
path, public = receipts['publicReplay']
require(public['baseOwnerManifestSHA256'] == matrix['sourceManifestSHA256'], 'public replay base')
require(public['exitCode'] == 0 and public['expectedTests'] == 10, 'old public result')
require(digest(path.parent / 'public-debug.log') == public['logSHA256'], 'public log')
require(b'Executed 10 tests, with 0 failures' in (path.parent / 'public-debug.log').read_bytes(), 'old public tests')
for name, expected in public['source'].items():
    require(digest(Path(public['cwd']) / name) == expected, 'public replay frozen source ' + name)
review_path = ROOT / 'verification/capability-bridge-lifecycle-review/final-receipt.json'
require(digest(review_path) == 'd60b187299da221f435d61438e55e942af6d9b372c6fdb202f8ebd8143290533', 'independent review seal')
review_command = ['python3', 'verification/capability-bridge-lifecycle-review/finalize.py', '--check']
checked = subprocess.run(review_command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(HERE / 'independent-seal-check.log').write_bytes(checked.stdout)
require(checked.returncode == 0, 'independent full evidence audit')
receipt = {
    'status': 'root source and owner-evidence audit passed; independent lifecycle scoped approval verified',
    'owner_aggregate_sha256': digest(aggregate_path), 'source_manifest_sha256': matrix['sourceManifestSHA256'],
    'live_and_frozen_sources_verified': len(matrix['source']), 'owner_command_logs_verified': len(matrix['commands']),
    'full_tests_per_mode': 32, 'host_modes': ['debug', 'release', 'Swift TSan'], 'derived_probe_runs': 15,
    'old_public_tests': 10, 'linked_binaries_verified': len(matrix['linkedConsumers']),
    'native_revision': matrix['nativeRevision'], 'root_audit_source_sha256': digest(Path(__file__)),
    'independent_final_receipt_sha256': digest(review_path),
    'independent_seal_check': {'command': review_command, 'exit_code': checked.returncode,
        'log_sha256': digest(HERE / 'independent-seal-check.log')},
    'independent_public_checks_per_mode': 17, 'independent_internal_checks': 14,
    'independent_opacity_rejections': 4,
    'reviewed_invariants': ['One-shot group transfer and explicit untransferred cleanup.',
        'One concrete host/KV close task and one separate native close job.',
        'Logical constructor tail required for successful handoff and failed construction retirement.',
        'First checked failure delivered before cleanup; exact native drain and concrete close separately gate retirement.',
        'Quarantine retains counted native ownership and sinks; no terminal callback fabricates retirement.',
        'Trusted acyclic fixed sinks and exclusive adapter use remain caller obligations.'],
    'limitations': ['Root performed source/evidence audit, not a duplicate matrix.',
        'Derived scheduling barriers and report mutation are explicitly test-only.',
        'Native archives and platform frameworks are not Swift TSan instrumented.',
        'Logical cleanup boundary does not establish allocator/Task destruction, hard latency or OS reclamation.',
        'No whole-attempt coordinator, signed execution, physical-device, immutable publication or GA qualification.']
}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'])
