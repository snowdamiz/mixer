#!/usr/bin/env python3
"""Retain before/after guardrail decisions without touching website source."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = HERE / '.build/source'
source.mkdir(parents=True, exist_ok=False)
paths = ['scripts/check-policy.py', 'scripts/ci/verify-apple-toolchain.py',
         'scripts/ci/tests/test_apple_toolchain.py', 'scripts/ci/tests/test_dependency_policy.py',
         'gates/ga.json', 'work-graph.json', 'dogfood/receipts/milestones.json',
         'website/package.json', 'website/package-lock.json']
files = {}
for name in paths:
    dest = source / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((ROOT / name).read_bytes())
    files[name] = sha(dest)
receipt = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
           'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           'source_files': files, 'commands': [], 'collector_sha256': sha(Path(__file__)),
           'scope': 'Manifest guardrail only. wasm32 architecture names remain allowed; prohibited engines including wasm3 suffixes/URLs remain rejected. No release authorization, provenance/legal audit or website change.'}
original = subprocess.check_output(['git', 'show', '401e16c:scripts/check-policy.py'], cwd=ROOT)
patched = (source / 'scripts/check-policy.py').read_bytes()
(HERE / 'original-check-policy.py.txt').write_bytes(original)
receipt['original_sha256'] = hashlib.sha256(original).hexdigest()
for label, content, expected_tests, expected_guard in [('original', original, 1, 1), ('repaired', patched, 0, 0)]:
    (source / 'scripts/check-policy.py').write_bytes(content)
    for kind, argv, expected in [('tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v'], expected_tests),
                                 ('guard', [sys.executable, 'scripts/check-policy.py'], expected_guard)]:
        result = subprocess.run(argv, cwd=source, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        log = HERE / f'{label}-{kind}.log'
        log.write_bytes(result.stdout)
        receipt['commands'].append({'name': f'{label}-{kind}', 'argv': argv, 'cwd': str(source),
                                    'exit': result.returncode, 'expected_exit': expected,
                                    'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
        assert result.returncode == expected
        if kind == 'guard':
            data = json.loads(result.stdout)
            assert len(data['failures']) == (11 if label == 'original' else 0)
for name, digest in files.items():
    assert sha(source / name) == digest == sha(ROOT / name), name
receipt['result'] = 'Original reproduces 11 false positives and fails architecture regression; repaired seven-test suite and guard pass.'
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['result'])
