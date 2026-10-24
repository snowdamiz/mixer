"""Create an immutable, separately scoped metadata companion review manifest."""
from pathlib import Path
import json, hashlib, sys, datetime
HERE = Path(__file__).resolve().parent
V7 = HERE.parent / 'swift-calls-dispatch/v7-fixture-expectations'
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def bind(path): return {'sha256': digest(path), 'bytes': path.stat().st_size}
assert not (HERE / 'review-seal.json').exists(), 'never overwrite a seal'
for p in HERE.glob('*.py'): compile(p.read_bytes(), str(p), 'exec')
controls = json.loads((HERE / 'controls.json').read_bytes())
assert len(controls['controls']) == 25 and controls['allRejected'] and controls['dummyTargetRemoved']
cleanup = json.loads((HERE / 'cleanup.json').read_bytes())
assert cleanup['allOwnedMetadataGroupsEmpty'] and cleanup['syntheticTargetRemoved']
bindings = {str(p.relative_to(HERE)): bind(p) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
base = [V7 / 'review-seal.json', V7 / 'qualified_runtime.py', V7 / 'candidate/tests/span_execution_oracle.rs']
assert digest(base[0]) == '79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
assert digest(base[1]) == '86595d8e18360fec5101a90feef7744c2f2a32d0482f88a6003ff1b7dfd4d2fb'
assert digest(base[2]) == '3725f2a95a439a6b2998a7c85bd06a5fd22bebe2112ec6644ecfe974b117f8a2'
seal = {'schema': 1, 'scope': 'Separate Node-only metadata/prelaunch companion for immutable V7',
        'baseBindings': {str(p): bind(p) for p in base}, 'bindings': bindings,
        'baseProducerSealSHA256': digest(base[0]), 'baseDriverSHA256': digest(base[1]),
        'candidateSourceClosure': '78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237',
        'companionSHA256': digest(HERE / 'companion.py'), 'controls': 25,
        'compilerCompilationExecuted': False, 'wasmExecuted': False, 'runtimeSelected': False,
        'createdUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': [sys.executable, '-B', str(Path(__file__))], 'pythonVersion': sys.version,
        'pythonExecutableSHA256': digest(sys.executable)}
p = HERE / 'review-seal.json'; p.write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
(HERE / 'review-seal.sha256').write_text(digest(p) + '  review-seal.json\n')
print(digest(p), len(bindings), 'bound files; no runtime selected')
