"""Seal the separate transport; never change or reseal original evidence."""
from pathlib import Path
import datetime, hashlib, json, sys
HERE = Path(__file__).resolve().parent
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        while b := f.read(1024 * 1024): h.update(b)
    return h.hexdigest()
assert not (HERE / 'review-seal.json').exists(), 'never replace a transport seal'
controls = json.loads((HERE / 'controls.json').read_bytes())
assert controls['allRejected'] and controls['artificialFixtureRootRemoved'] and controls['allFailureScratchRemoved']
assert controls['sourceSHA256'] == digest(HERE / 'controls.py') and controls['restoreSourceSHA256'] == digest(HERE / 'restore.py')
assert not list(HERE.glob('owned-controls-*'))
for p in HERE.glob('*.py'): compile(p.read_bytes(), str(p), 'exec')
manifest = json.loads((HERE / 'transport-manifest.json').read_bytes())
for label, source in [('controls', 'controls.py'), ('delivery-inventory', 'inspect_closure.py'), ('actual-discard-stream', 'restore.py'), ('actual-existing-no-op', 'restore.py')]:
    command = json.loads((HERE / (label + '-command.json')).read_bytes())
    assert command['exitCode'] == 0 and command['sourceSHA256'] == digest(HERE / source)
    assert command['stdoutSHA256'] == digest(HERE / (label + '-stdout.txt')) and command['stderrSHA256'] == digest(HERE / (label + '-stderr.txt'))
discard = json.loads((HERE / 'actual-discard-stream-stdout.txt').read_bytes())
assert discard == {'repoWritten': False, 'discardStreamChecks': [{'bytes': x['bytes'], 'sha256': x['sha256'], 'gzipSHA256': x['gzip']['sha256']} for x in manifest['entries']]}
existing = json.loads((HERE / 'actual-existing-no-op-stdout.txt').read_bytes())
assert existing == {'existingEvidenceOverwritten': False, 'normalization': 'none', 'restored': [{'path': x['path'], 'result': 'existing-byte-identical-no-op'} for x in manifest['entries']]}
root = HERE.parents[1]
for name, row in manifest['authority'].items():
    assert (root / name).stat().st_size == row['bytes'] and digest(root / name) == row['sha256']
for row in manifest['entries']:
    assert (root / row['path']).stat().st_size == row['bytes'] and digest(root / row['path']) == row['sha256']
inventory = json.loads((HERE / 'delivery-inventory.json').read_bytes())
assert inventory['rootPreparationSourceSHA256'] == digest(HERE / 'root-delivery-prepare.snapshot.py')
for p in HERE.rglob('*'): assert not p.is_symlink()
bindings = {str(p.relative_to(HERE)): {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(HERE.rglob('*')) if p.is_file()}
assert all(x['bytes'] < 95_000_000 for x in bindings.values())
seal = {'schema': 1, 'scope': 'Exact two-file immutable evidence transport only',
        'bindings': bindings, 'originalAuthority': manifest['authority'],
        'manifestSHA256': digest(HERE / 'transport-manifest.json'),
        'excludedRawPaths': manifest['excludedRawPaths'], 'normalization': 'none',
        'pureNegativeControls': controls['negativeControls'], 'actualRestoreAgainstExistingCheckout': 'two exact no-ops',
        'oldSealsOrEvidenceModified': False, 'compilerOrProductRuntimeExecuted': False, 'gitExecuted': False,
        'createdUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': [sys.executable, '-B', str(Path(__file__))], 'pythonVersion': sys.version,
        'pythonExecutableSHA256': digest(Path(sys.executable))}
p = HERE / 'review-seal.json'; p.write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
(HERE / 'review-seal.sha256').write_text(digest(p) + '  review-seal.json\n')
print(digest(p), len(bindings), 'transport bindings')
