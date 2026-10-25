"""Finite independent design review with source/output receipts; never executes VM."""
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
PRODUCER = ROOT / 'verification/swift-ordered-retention-diagnostic-design'
MANIFEST = ROOT / 'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json'
INPUTS = (
    'AGENTS.md', 'PLAN.md', 'mixer-product-plan.md',
    'docs/swift-current-attribution-runtime-review.md',
    'docs/swift-attribution-schema-correction.md',
    'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json',
)


def digest(path):
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while block := stream.read(65536):
            h.update(block); size += len(block)
    return dict(bytes=size, sha256=h.hexdigest())


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')


def closure():
    declared = json.loads(MANIFEST.read_text())
    if len(declared) != 132 or digest(MANIFEST)['sha256'] != '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd':
        raise ValueError('unexpected selected VM closure')
    hashes = {}
    for name, expected in declared.items():
        target = ROOT / 'vm' / name
        if '..' in Path(name).parts or target.is_symlink() or not target.is_file():
            raise ValueError('unsafe selected source')
        hashes[name] = digest(target)['sha256']
        if hashes[name] != expected:
            raise ValueError('selected VM source drift: '+name)
    raw = (json.dumps(hashes, indent=2, sort_keys=True)+'\n').encode()
    return dict(files=132, sha256=hashlib.sha256(raw).hexdigest())


def main():
    # The frozen producer copy and seal are staged by reviewer only after freeze.
    seal = json.loads((PRODUCER/'seal.json').read_text())
    if digest(PRODUCER/'seal.json')['sha256'] != '3d28dad80748a4b35ac0e49f9567a95bd5175997d57197c36ad6d85513d555c3':
        raise ValueError('producer frozen seal digest')
    if len(seal['members']) != 34:
        raise ValueError('producer frozen member count')
    declared = set(seal['members'])
    actual = {str(p.relative_to(ROOT)) for p in PRODUCER.rglob('*') if p.is_file() and p.name not in {'seal.json','seal.sha256'}}
    actual.add('docs/swift-ordered-retention-diagnostic-design.md')
    if actual != declared:
        raise ValueError('producer packet inventory')
    for name, expected in seal['members'].items():
        path = ROOT/name
        if path.is_symlink() or '..' in Path(name).parts or digest(path) != expected:
            raise ValueError('producer seal member drift: '+name)
    producer_inputs = HERE / 'inputs/producer'
    required = ('codec_model.py', 'test_codec_model.py', 'finalization_model.py', 'test_finalization_model.py', 'run_checks.py', 'design.md', 'seal.json')
    frozen = {name: digest(producer_inputs/name) for name in required}
    for name in ('codec_model.py', 'test_codec_model.py', 'finalization_model.py', 'test_finalization_model.py', 'run_checks.py', 'seal.json'):
        if frozen[name] != digest(PRODUCER/name):
            raise ValueError('frozen producer drift: '+name)
    if frozen['design.md'] != digest(ROOT/'docs/swift-ordered-retention-diagnostic-design.md'):
        raise ValueError('frozen design drift')
    attempts = HERE / 'attempts'
    attempts.mkdir(exist_ok=True)
    for number in range(1, 33):
        attempt = attempts / str(number)
        try:
            attempt.mkdir(); break
        except FileExistsError:
            continue
    else:
        raise ValueError('finite attempts exhausted')
    before = closure()
    argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_independent.py', '-v']
    producer_argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(producer_inputs), '-p', 'test_*_model.py', '-v']
    command = dict(argv=argv, producerArgv=producer_argv, cwd=str(ROOT),
                   environment=dict(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0'),
                   inheritedEnvironment='other variables inherited, not emitted',
                   python=dict(path=sys.executable, resolved=str(Path(sys.executable).resolve()), version=sys.version,
                               **digest(Path(sys.executable).resolve())),
                   platform=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
                   sourceRevisionContext=(HERE/'revision-context.txt').read_text().strip(),
                   selectedInputs={name:digest(ROOT/name) for name in INPUTS},
                   producerSealMembers=len(seal['members']), producerInputs=frozen, reviewerInputs={name:digest(HERE/name) for name in ('audit.py','test_independent.py')},
                   liveBefore=before,
                   scope='finite Python synthetic review only; no Rust/guest/full target/native/UI/capture/process discovery')
    write_json(attempt/'command.json', command)
    started = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0')
    producer_result = subprocess.run(producer_argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    (attempt/'producer-stdout').write_bytes(producer_result.stdout)
    (attempt/'producer-stderr').write_bytes(producer_result.stderr)
    write_json(attempt/'producer-raw-result.json', dict(returncode=producer_result.returncode, stdout=digest(attempt/'producer-stdout'), stderr=digest(attempt/'producer-stderr')))
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    # Tests emit only fixed unittest names/status; no target or arbitrary guest output.
    (attempt/'stdout').write_bytes(result.stdout)
    (attempt/'stderr').write_bytes(result.stderr)
    # Persist the raw child outcome before independent classification.
    write_json(attempt/'raw-result.json', dict(returncode=result.returncode, stdout=digest(attempt/'stdout'),
                                               stderr=digest(attempt/'stderr'), elapsedSeconds=time.monotonic()-started))
    after = closure()
    drift = before != after
    for name in ('codec_model.py', 'test_codec_model.py', 'finalization_model.py', 'test_finalization_model.py', 'run_checks.py', 'seal.json'):
        drift |= frozen[name] != digest(PRODUCER/name)
    drift |= frozen['design.md'] != digest(ROOT/'docs/swift-ordered-retention-diagnostic-design.md')
    output_bound = all(len(x) <= 65536 for x in (result.stdout, result.stderr, producer_result.stdout, producer_result.stderr))
    receipt = dict(exitCode=result.returncode, producerExitCode=producer_result.returncode, rawResult=digest(attempt/'raw-result.json'),
                   producerRawResult=digest(attempt/'producer-raw-result.json'),
                   elapsedSeconds=time.monotonic()-started, liveAfter=after,
                   inputsStable=not drift, finiteOutputWithin64KiBEach=output_bound,
                   acceptedFiniteReview=result.returncode==0 and producer_result.returncode==0 and not drift and output_bound,
                   originalTargetOrRustExecuted=False, noScratchCreated=True,
                   cleanup='Synchronous finite Python child exited; -B suppressed bytecode. No source/build/native/temporary/selection products; retained files are review evidence. No process discovery or cleanup signal.')
    write_json(attempt/'result.json', receipt)
    print(json.dumps(dict(attempt=number, finiteReviewPassed=receipt['acceptedFiniteReview'],
                          command=digest(attempt/'command.json'), result=digest(attempt/'result.json')), sort_keys=True))
    return 0 if receipt['acceptedFiniteReview'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
