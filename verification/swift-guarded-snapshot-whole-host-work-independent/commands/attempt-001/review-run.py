#!/usr/bin/env python3
"""Record bounded, read-only pure-Python replay and review commands."""
import datetime, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parents[1]
C = R / 'verification/swift-guarded-snapshot-whole-host-work-composition'
choices = {
    'producer-derive': [str(C / 'derive.py'), '--check'],
    'producer-tests': [str(C / 'test_work.py')],
    'independent-audit': [str(D / 'audit.py')],
}
if len(sys.argv) != 2 or sys.argv[1] not in choices:
    raise SystemExit('choose producer-derive, producer-tests, or independent-audit')
base = D / 'commands'
base.mkdir(exist_ok=True)
index = 1
while (base / f'attempt-{index:03}').exists():
    index += 1
out = base / f'attempt-{index:03}'
out.mkdir()
sources = []
for directory, prefix in [(D, 'review-'), (C, 'producer-')]:
    for path in sorted(directory.glob('*.py')):
        raw = path.read_bytes()
        (out / (prefix + path.name)).write_bytes(raw)
        sources.append({'path': str(path.relative_to(R)), 'bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})
command = [sys.executable, '-B', *choices[sys.argv[1]]]
started = time.monotonic()
at = datetime.datetime.now(datetime.timezone.utc).isoformat()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
result = subprocess.run(command, cwd=R, env=env, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=55)
for name in ['stdout', 'stderr']:
    (out / name).write_bytes(getattr(result, name))
record = {'at': at, 'command': command, 'cwd': str(R), 'python': sys.version,
          'platform': platform.platform(), 'exit_code': result.returncode,
          'elapsed_seconds': time.monotonic() - started, 'sources': sources,
          'script_tree_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest(),
          'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
          'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
          'source_revision': 'Exact source146/host11 manifests; no Git operation.',
          'child_waited': True, 'compiler_or_product_or_native_run': False,
          'scope': 'Pure offline Python replay/review only; no UI, capture, native, global process inventory, or root metadata changes.'}
(out / 'receipt.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
