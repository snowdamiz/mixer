#!/usr/bin/env python3
"""Freeze this proposal packet; inspect no processes and execute no product code."""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
DOC = ROOT / 'docs/android-copied-sdk-appearance-contract.md'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


manifest = json.loads((OUT / 'source-manifest.json').read_text())
for path, expected in manifest['files'].items():
    assert identity((ROOT / path).read_bytes()) == expected, 'Named input changed: ' + path
    assert identity((OUT / 'source-inputs' / path).read_bytes()) == expected, path
for path in [DOC, OUT / 'collect.py', OUT / 'probe.py', OUT / 'freeze.py']:
    lines = path.read_text().splitlines()
    assert all(line == line.rstrip() for line in lines), 'Trailing whitespace: ' + str(path)
for target in re.findall(r'\]\(([^)]+)\)', DOC.read_text()):
    if not target.startswith(('https://', 'http://', '#')):
        assert (DOC.parent / target.split('#')[0]).exists(), 'Missing local target: ' + target
diff_command = ['git', 'diff', '--check', '--', 'docs/android-copied-sdk-appearance-contract.md',
                'verification/android-copied-sdk-appearance-contract']
result = subprocess.run(diff_command, cwd=ROOT, capture_output=True, timeout=20)
(OUT / 'diff-check.stdout').write_bytes(result.stdout)
(OUT / 'diff-check.stderr').write_bytes(result.stderr)
assert result.returncode == 0
receipt = json.loads((OUT / 'receipt.json').read_text())
assert receipt['source_unchanged_during_collection']
handoff = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'frozen-source-contract-proposal-awaiting-root-selection',
           'revision': receipt['revision'], 'implementation_selected': False,
           'implementation_accepted': False, 'GA_qualified': False,
           'proposal': {'path': str(DOC.relative_to(ROOT)), **identity(DOC.read_bytes())},
           'source_manifest': {'path': 'source-manifest.json', **identity((OUT / 'source-manifest.json').read_bytes())},
           'recommended_contract': 'Internal compiled exact Core/UI+manifest SDK and exported adapter source-pair profile; CLI-owned canonical default unchanged; no helper/supervisor/public routing.',
           'source_profile_update_authority': 'Deliberate reviewed source change after bounded candidate tests and root selection; never auto-pin local source or trust selected SDK/lock/bundle assertions.',
           'scope': receipt['scope'], 'native_runtime_or_capture_started': False,
           'process_discovery': False, 'product_code_imported_or_executed': False,
           'committed_or_pushed': False, 'pending': receipt['pending']}
(OUT / 'handoff.json').write_text(json.dumps(handoff, indent=2, sort_keys=True) + '\n')
report = {'status': 'proposal-freeze-checks-pass', 'command': ['python3', '-B', str(pathlib.Path(__file__).relative_to(ROOT))],
          'python': sys.version, 'named_inputs_rechecked': len(manifest['files']),
          'new_document_and_script_whitespace': 'pass', 'document_local_links': 'pass',
          'diff_check': {'command': diff_command, 'exit': result.returncode,
                         'limitation': 'Untracked outputs are separately checked above; git diff alone omits them.'},
          'implementation_selected': False, 'native_runtime_or_capture_started': False}
(OUT / 'freeze-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
files = {str(DOC.relative_to(ROOT)): identity(DOC.read_bytes())}
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name != 'seal.json':
        files[str(path.relative_to(ROOT))] = identity(path.read_bytes())
seal = {'schema': 1, 'scope': 'Proposal and named source/data evidence only; not implementation selection/acceptance or GA authority.',
        'files': files, 'files_map_sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
(OUT / 'seal.json').write_text(json.dumps(seal, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': report['status'], 'sealed_files': len(files),
                  'sealed_bytes': sum(value['bytes'] for value in files.values()),
                  'seal': identity((OUT / 'seal.json').read_bytes()),
                  'proposal': handoff['proposal']}, indent=2))
