"""Run only finite Python design tests and retain exact command receipts."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = (
    'AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
    'docs/swift-count-plan-retention-candidate-review.md',
    'docs/swift-count-plan-retention-candidate.md',
    'docs/swift-cost-retention-candidate-review.md',
    'docs/swift-retention-runtime.md', 'docs/swift-decode-plan-integration.md',
    'docs/swift-retention-next-design-review.md', 'docs/swift-adaptive-retention-design.md',
    'docs/swift-current-attribution-runtime-review.md',
    'docs/swift-current-attribution-runtime.md',
    'docs/swift-attribution-schema-correction.md',
    'docs/swift-current-attribution-preparation-review.md',
    'docs/swift-plan-cache-remaining-work-diagnosis.md',
    'verification/swift-count-plan-retention-candidate/seal.json',
    'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json',
    'verification/swift-cost-retention-candidate-review/seal.json',
    'verification/swift-current-attribution-runtime/result-seal.json',
    'verification/swift-current-attribution-runtime/target-once-telemetry.json',
    'verification/swift-current-attribution-runtime/target-once-result.json',
    'verification/swift-current-attribution-full-preparation/prepared-seal.json',
    'verification/swift-current-attribution-full-preparation/copied-build-manifest.json',
    'verification/swift-current-attribution-full-preparation/binding.json',
    'verification/swift-current-attribution-full-preparation/source-audit.json',
    'verification/swift-current-attribution-full-preparation/output-contract.json',
    'verification/swift-cache-current-attribution-observer/seal.json',
    'verification/swift-cache-current-attribution-observer/observer-contract.json',
    'verification/swift-cache-current-attribution-observer/observer-and-controls.rs',
)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(65_536):
            h.update(block)
    return dict(bytes=path.stat().st_size, sha256=h.hexdigest())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def closure():
    path = ROOT / 'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json'
    declared = json.loads(path.read_text())
    if len(declared) != 132:
        raise ValueError('unexpected named closure')
    current = {}
    for name, expected in declared.items():
        p = ROOT / 'vm' / name
        if p.is_symlink() or not p.is_file() or '..' in Path(name).parts:
            raise ValueError('unsafe source name')
        current[name] = digest(p)['sha256']
        if current[name] != expected:
            raise ValueError('source drift: ' + name)
    raw = (json.dumps(current, indent=2, sort_keys=True) + '\n').encode()
    return dict(files=132, canonicalSHA256=hashlib.sha256(raw).hexdigest(),
                manifest=digest(path), members=current)


def main():
    attempts = HERE / 'attempts'
    attempts.mkdir(exist_ok=True)
    for number in range(1, 101):
        attempt = attempts / str(number)
        try:
            attempt.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise ValueError('finite attempt inventory exhausted')
    before = closure()
    selected = {name: digest(ROOT / name) for name in INPUTS}
    own = {str(p.relative_to(ROOT)): digest(p) for p in sorted(HERE.glob('*.py'))}
    own['docs/swift-ordered-retention-diagnostic-design.md'] = digest(ROOT / 'docs/swift-ordered-retention-diagnostic-design.md')
    argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(HERE),
            '-p', 'test_*_model.py', '-v']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    command = dict(argv=argv, cwd=str(ROOT), environment=dict(PYTHONDONTWRITEBYTECODE='1'),
                   inheritedEnvironment='other variables inherited, not dumped',
                   python=dict(path=sys.executable, resolved=str(Path(sys.executable).resolve()),
                               version=sys.version, **digest(Path(sys.executable).resolve())),
                   platform=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
                   sourceRevisionContext='d1ca165659c72db17c5573d992002635d569c1f1',
                   selectedInputs=selected, ownInputs=own, liveBefore=before,
                   scope='finite synthetic Python only; no product import/execution, Rust, guest, native or discovery')
    write_json(attempt / 'command.json', command)
    start = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=30)
    (attempt / 'stdout').write_bytes(result.stdout)
    (attempt / 'stderr').write_bytes(result.stderr)
    after = closure()
    if after != before:
        raise ValueError('live closure changed')
    receipt = dict(exitCode=result.returncode, seconds=time.monotonic() - start,
                   stdout=digest(attempt / 'stdout'), stderr=digest(attempt / 'stderr'),
                   liveAfter=after, noScratchCreated=True,
                   cleanup='synchronous child completed; no temporary/source/build/native products; no process discovery')
    write_json(attempt / 'result.json', receipt)
    print(json.dumps(dict(attempt=number, exitCode=result.returncode,
                          commandSHA256=digest(attempt / 'command.json')['sha256'],
                          resultSHA256=digest(attempt / 'result.json')['sha256']), sort_keys=True))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
