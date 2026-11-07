"""Record Python/fake-child controls only; never select compiler/native execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNED = ('scripts/ci/check-android-generated-java.py',
         'scripts/ci/tests/test_android_generated_java_runner.py')


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    before = {p: identity(ROOT / p) for p in OWNED}
    receipt = {'observed_utc': datetime.now(timezone.utc).isoformat(),
        'harness_argv': sys.argv, 'python': sys.version, 'python_executable': sys.executable,
        'interpreter_identity': identity(Path(sys.executable).resolve()),
        'scope': 'Python controls with owned fake Python children and dummy data; no compiler/native execution',
        'source_inputs': before, 'commands': []}
    temporary = tempfile.TemporaryDirectory(prefix='python-controls-owned-', dir=HERE)
    receipt['temporary_root'] = temporary.name
    env = os.environ.copy()
    env.update({'TMPDIR': temporary.name, 'PYTHONDONTWRITEBYTECODE': '1'})
    try:
        for mode, flags in (('normal', []), ('optimized', ['-O'])):
            argv = [sys.executable, '-B', *flags, OWNED[1], '-v']
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=45)
            log = HERE / ('tests-' + mode + '.log')
            log.write_bytes(result.stdout)
            receipt['commands'].append({'argv': argv, 'cwd': str(ROOT),
                'exit_code': result.returncode, 'log': log.name, **identity(log)})
            save(HERE / 'test-commands.json', receipt)
        after = {p: identity(ROOT / p) for p in OWNED}
        receipt['source_inputs_stable'] = after == before
        baseline = json.loads((HERE / 'baseline.json').read_text())
        sealed = {name: {str(p.relative_to(HERE.parent / name)): identity(p)
                         for p in sorted((HERE.parent / name).rglob('*')) if p.is_file()}
                  for name in baseline['sealed']}
        receipt['sealed_evidence_unchanged'] = sealed == baseline['sealed']
        receipt['passed'] = (all(c['exit_code'] == 0 for c in receipt['commands'])
                             and receipt['source_inputs_stable'] and receipt['sealed_evidence_unchanged'])
    finally:
        receipt['test_temporary_entries_remaining_before_harness_cleanup'] = sorted(
            str(p.relative_to(temporary.name)) for p in Path(temporary.name).iterdir())
        temporary.cleanup()
        receipt['temporary_root_removed'] = not Path(temporary.name).exists()
        save(HERE / 'test-commands.json', receipt)
    print(json.dumps({'passed': receipt['passed'], 'commands': len(receipt['commands']),
                      'sealed_evidence_unchanged': receipt['sealed_evidence_unchanged']}))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
