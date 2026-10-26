"""Run the unchanged manifest/gate guard on only the selected closed inputs."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
assert __debug__ and not (HERE / 'validation.json').exists()
selection = json.loads((HERE / 'selection.json').read_text())
names = {'Package.swift', 'Package.resolved', 'Cargo.toml', 'Cargo.lock',
         'package.json', 'package-lock.json', 'go.mod', 'go.sum',
         'build.gradle', 'build.gradle.kts', 'settings.gradle.kts'}
paths = {p for p in selection['paths'] if Path(p).name in names}
paths.update({'scripts/check-policy.py', 'gates/ga.json', 'work-graph.json',
              'dogfood/receipts/milestones.json'})
inputs = []
scratch = Path(tempfile.mkdtemp(prefix='selected-guardrail-', dir=HERE))
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
    for name in sorted(paths):
        source = ROOT / name
        assert not source.is_symlink()
        data = source.read_bytes()
        target = scratch / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs.append({'path': name, 'bytes': len(data),
                       'sha256': hashlib.sha256(data).hexdigest()})
    argv = [sys.executable, '-B', str(scratch / 'scripts/check-policy.py')]
    result = subprocess.run(argv, cwd=scratch, capture_output=True, timeout=60)
    (HERE / 'validation.stdout').write_bytes(result.stdout)
    (HERE / 'validation.stderr').write_bytes(result.stderr)
    assert result.returncode == 0, result.returncode
    output = json.loads(result.stdout)
    assert output['status'] == 'passed' and not output['failures']
    assert set(output['manifests']) == {p for p in paths if Path(p).name in names}
finally:
    shutil.rmtree(scratch)
receipt = {
    'schema': 1, 'started': started,
    'completed': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'argv': argv, 'python': sys.version, 'exit_code': result.returncode,
    'inputs': inputs, 'selected_manifests': len(output['manifests']),
    'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
    'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
    'scope': 'Unchanged check-policy.py against selected frozen manifests and current gate/package/milestone metadata only; no active candidate source read or product execution',
    'owned_scratch_removed': not scratch.exists(), 'child_reaped': True,
    'native_or_GA_accepted': False,
}
(HERE / 'validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'selected_manifests': len(output['manifests']),
                  'inputs': len(inputs), 'owned_scratch_removed': not scratch.exists()}))
