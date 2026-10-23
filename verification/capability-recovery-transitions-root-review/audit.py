#!/usr/bin/env python3
"""Audit the frozen transition candidate and original negative/fixed replays."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OWNER = ROOT / 'verification/capability-recovery-transitions'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def audit(label):
    receipt = OWNER / label / 'receipt.json'
    r = json.loads(receipt.read_text())
    source = Path(r['export'])
    for name, digest in r['source_files'].items():
        require(sha(source / name) == digest, 'source ' + name)
    for name, digest in r['baseline_files'].items():
        raw = subprocess.check_output(['git', 'show', r['dependency_revision'] + ':' + name], cwd=ROOT)
        require(hashlib.sha256(raw).hexdigest() == digest, 'Git baseline ' + name)
    manifest = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(r['source_files'].items()))
    require(hashlib.sha256(manifest.encode()).hexdigest() == r['source_manifest_sha256'], 'manifest')
    require(sha(OWNER / label / 'source-manifest.sha256') == r['source_manifest_sha256'], 'saved manifest')
    for c in r['commands']:
        log = ROOT / c['log']
        require(sha(log) == c['sha256'], 'log ' + c['name'])
        require(c['exit_code'] == c['expected_exit'], 'command ' + c['name'])
        if 'expected_tests' in c:
            require(c['observed_tests'] == [c['expected_tests']], 'tests ' + c['name'])
            require('Executed ' + str(c['expected_tests']) + ' tests, with 0 failures' in log.read_text(), 'test output')
    retained = 0
    for row in r['retained_products'].values():
        for name, digest in row['files'].items():
            require(sha(Path(row['directory']) / name) == digest, 'retained ' + name)
            retained += 1
    artifacts = 0
    for rows in r['artifacts'].values():
        for row in rows:
            p = Path(row['path'])
            require(p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], 'artifact ' + str(p))
            artifacts += 1
    for name, digest in r['native_files'].items():
        require(sha(Path(r['native_copy']) / name) == digest, 'native ' + name)
    if label.endswith('candidate-3'):
        for name, digest in r['owned_files'].items():
            require(sha(ROOT / name) == digest, 'current owned ' + name)
        cache = r['host_cache_origin']
        require(sha(Path(cache['preservation_receipt'])) == cache['preservation_sha256'], 'cache preservation')
        preserved = json.loads(Path(cache['preservation_receipt']).read_text())
        for name, digest in preserved['files'].items():
            require(sha(Path(preserved['directory']) / name) == digest, 'prior TSan preservation')
    return {'receipt_sha256': sha(receipt), 'source_files': len(r['source_files']),
            'baseline_git_files': len(r['baseline_files']), 'commands': len(r['commands']),
            'retained_files': retained, 'artifacts': artifacts, 'source_manifest_sha256': r['source_manifest_sha256']}


def replay(label, expected, count):
    directory = HERE / label
    path = directory / 'receipt.json'
    r = json.loads(path.read_text())
    require(r['probe_sha256'] == sha(HERE / 'negative-cold-interruption/ColdInterruptionProbe.swift'), 'same probe')
    runs = [c for c in r['commands'] if not c['name'].endswith('compile') and c['name'] != 'swift-version']
    require(len(runs) == count, 'run count')
    for c in r['commands']:
        require(sha(directory / c['log']) == c['log_sha256'], 'replay log')
        require(c['exit_code'] == (0 if c['name'].endswith('compile') or c['name'] == 'swift-version' else expected), 'replay result')
    for mode, rows in r.get('products', {}).items():
        base = ROOT / ('capability-activation/.build/transitions-qualified-2026-10-23-candidate-' + str(r.get('candidate', 2)) + '/retained-' + mode)
        for name, digest in rows.items():
            require(sha(base / name) == digest, 'replay dependency')
    for row in r.get('binaries', {}).values():
        require(sha(Path(row['path'])) == row['sha256'], 'replay binary')
    return {'receipt_sha256': sha(path), 'executions': count, 'expected_exit': expected}


result = {
    'status': 'frozen source and evidence audit passed; cold-recovery defect repaired',
    'candidate_1': audit('2026-10-23-candidate-1'),
    'candidate_2': audit('2026-10-23-candidate-2'),
    'candidate_3': audit('2026-10-23-candidate-3'),
    'command': ['python3', str(Path(__file__).relative_to(ROOT))],
    'python': sys.version,
    'audit_sha256': sha(Path(__file__)),
    'negative': replay('negative-cold-interruption', 42, 3),
    'fixed_candidate_2': replay('cold-recovery-replay', 0, 9),
    'fixed_candidate_3': replay('cold-recovery-replay-3', 0, 9),
    'scope': 'Root source review and evidence audit, plus original cold-reopen probe with explicitly reused signed fixture scaffold. Native boot/enable are real. Controlled persisted close/reopen is not a process crash.',
    'reviewed': ['one-shot issuer and exact signal binding', 'intent-before-enable and conservative effects failure',
                 'health observation and terminal-during-commit behavior', 'cold failed/unhealthy stage suppression',
                 'retained fallback budget including failure/cleanup commit', 'requestStop separated from descriptor close', 'allowFallback false persists failure without selecting a replacement'],
    'limitations': ['Owner full-matrix evidence is audited, not independently rerun.',
                    'The dependency baseline is bf5021e; the later control-wake seam and concrete coordinator are separately qualified.',
                    'No physical, real UI milestone, full app, published package or GA qualification.'],
}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
