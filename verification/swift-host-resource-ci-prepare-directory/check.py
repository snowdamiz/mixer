"""Check the actual workflow mkdir against fresh and retained evidence parents."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
workflow = ROOT / '.github/workflows/verify.yml'
text = workflow.read_text()
section = text.split('      - name: Prepare owned closed fixture evidence\n', 1)[1].split('      - name:', 1)[0]
line = next(line.strip() for line in section.splitlines() if line.strip().startswith('mkdir '))
assert line == 'mkdir -p "$MIXER_CACHE_FIXTURE_DIR/logs" "$MIXER_CACHE_FIXTURE_DIR/runs"'
rows = []
with tempfile.TemporaryDirectory(prefix='mixer-cache-prepare-control-') as temporary:
    root = Path(temporary)
    for name in ('fresh', 'retained', 'file-collision'):
        target = root / name
        target.mkdir()
        if name == 'retained':
            (target / 'runs/historical').mkdir(parents=True)
            (target / 'runs/historical/receipt.json').write_bytes(b'preserve-original-evidence\n')
            (target / 'logs').mkdir()
        if name == 'file-collision':
            (target / 'runs').write_bytes(b'not-a-directory\n')
        command = ['bash', '-c', 'set -euo pipefail\n' + line]
        result = subprocess.run(command, env={**os.environ, 'MIXER_CACHE_FIXTURE_DIR': str(target)}, capture_output=True, timeout=10)
        assert (result.returncode == 0) == (name != 'file-collision')
        if name != 'file-collision':
            assert (target / 'logs').is_dir() and (target / 'runs').is_dir()
        if name == 'retained':
            assert (target / 'runs/historical/receipt.json').read_bytes() == b'preserve-original-evidence\n'
        if name == 'file-collision':
            assert (target / 'runs').read_bytes() == b'not-a-directory\n'
        rows.append({'case': name, 'argv': command, 'exit': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode(), 'passed': True})
    owned_path = str(root)
assert not Path(owned_path).exists()
receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'passed', 'python': sys.version, 'workflow_sha256': hashlib.sha256(workflow.read_bytes()).hexdigest(), 'cases': rows, 'owned_temporary_directory_removed': True, 'per_run_fresh_output_check_unchanged': True, 'native_runtime_or_GA': False}
with (HERE / 'check.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'passed', 'cases': len(rows), 'owned_temporary_directory_removed': True}))
