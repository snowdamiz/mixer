#!/usr/bin/env python3
"""Freeze the separate correction; no compiler, product code or process discovery."""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
DOC = ROOT / 'docs/android-copied-sdk-appearance-contract-correction.md'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


receipt = json.loads((OUT / 'receipt.json').read_text())
source = json.loads((OUT / 'source-manifest.json').read_text())
inputs = json.loads((OUT / 'input-manifest.json').read_text())
for path, value in source['files'].items():
    assert identity((ROOT / path).read_bytes()) == value, path
    assert identity((OUT / 'accepted-source' / path).read_bytes()) == value, path
for path, value in inputs['files'].items():
    assert identity((ROOT / path).read_bytes()) == value, path
    assert identity((OUT / 'inputs' / path).read_bytes()) == value, path
for binding in receipt['seals_before_and_after']:
    packet = ROOT / binding['packet']
    assert identity((packet / 'seal.json').read_bytes()) == binding['seal']
    for path, value in json.loads((packet / 'seal.json').read_text())['files'].items():
        assert identity((ROOT / path).read_bytes()) == value, path
for path in [DOC, OUT / 'collect.py', OUT / 'data_probe.py', OUT / 'freeze.py']:
    text = path.read_text()
    assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), str(path)
for target in re.findall(r'\]\(([^)]+)\)', DOC.read_text()):
    if not target.startswith(('http://', 'https://', '#')):
        assert (DOC.parent / target.split('#')[0]).exists(), target
argv = ['git', 'diff', '--check', '--', str(DOC.relative_to(ROOT)), str(OUT.relative_to(ROOT))]
p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=20)
(OUT / 'diff-check.stdout').write_bytes(p.stdout)
(OUT / 'diff-check.stderr').write_bytes(p.stderr)
assert p.returncode == 0
handoff = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'frozen-corrected-contract-awaiting-independent-review-and-root-selection',
           'accepted_git': receipt['accepted_git'], 'implementation_selected': False,
           'implementation_accepted': False, 'GA_qualified': False,
           'proposal': {'path': str(DOC.relative_to(ROOT)), **identity(DOC.read_bytes())},
           'receipt': {'path': str((OUT / 'receipt.json').relative_to(ROOT)), **identity((OUT / 'receipt.json').read_bytes())},
           'original_and_review_seals_unchanged': receipt['original_and_review_immutable'],
           'corrected_requirements': {
               'R1': 'Closed ASCII case-insensitive SDK-root Package* namespace; only exact pinned ordinary Package.swift; input and generated SDK before copy/hash.',
               'R2': 'One Swift project preflight inside verifyLock before generic trees and swift --version; applies to any Android lock and direct Android-required/build/run/export contexts; appearance preaccess included.',
               'R3': 'Build-only lazy profile decoder; raw import/inspect usable; exact one marker/literal; actual create/inspect/rendered admission execution remains an implementation test.'},
           'data_only_result': receipt['data_probe']['status'], 'source_files_bound_to_accepted_git': receipt['source_files'],
           'raw_manifest_result_reused_not_reexecuted': True,
           'product_or_compiler_or_native_execution': False, 'process_discovery': False,
           'committed_or_pushed': False,
           'pending': ['Independent correction review and root selection', 'Bounded source/profile/entrypoint/template implementation and tests',
                       'Copied-consumer Swift/Java qualification', 'Stable ABI/native runtime/public V2',
                       'Immutable published CLI/SDK and separate-repository FieldLog', 'Physical/release/store/operational/GA evidence']}
(OUT / 'handoff.json').write_text(json.dumps(handoff, indent=2, sort_keys=True) + '\n')
report = {'status': 'correction-freeze-checks-pass',
          'command': ['python3', '-B', 'verification/android-copied-sdk-appearance-contract-correction/freeze.py'],
          'python': sys.version, 'source_files_rechecked': len(source['files']), 'immutable_inputs_rechecked': len(inputs['files']),
          'original_and_review_seals_unchanged': True, 'new_text_whitespace_and_links': 'pass',
          'git_diff': {'argv': argv, 'exit': p.returncode, 'scope': 'New untracked text separately checked above.'}}
(OUT / 'freeze-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
files = {str(DOC.relative_to(ROOT)): identity(DOC.read_bytes())}
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name != 'seal.json':
        files[str(path.relative_to(ROOT))] = identity(path.read_bytes())
seal = {'schema': 1, 'scope': 'Separate corrected contract and source/data evidence only; original and review preserved; no implementation or release authority.',
        'files': files, 'files_map_sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
(OUT / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': report['status'], 'members': len(files),
                  'bytes': sum(value['bytes'] for value in files.values()),
                  'seal': identity((OUT / 'seal.json').read_bytes()), 'proposal': handoff['proposal']}, indent=2))
