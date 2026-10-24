"""Replay the version-only raw loader trace into explicit image provenance."""
from pathlib import Path
import sys, json, gzip, re, hashlib
HERE = Path(__file__).resolve().parent
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def save(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
p = HERE / 'node-provenance.json'
d = json.loads(p.read_bytes())
before = digest(p)
maps = '\n'.join(Path(x).read_text() for x in d['systemCacheFiles'] if x.endswith('.map'))
images, diagnostics, physical = [], [], {}
for line in gzip.decompress((HERE / d['loaderTraceRaw']).read_bytes()).decode().splitlines():
    m = re.fullmatch(r'dyld\[\d+\]: <([A-F0-9-]+)> (.+)', line)
    if not m:
        diagnostics.append(line)
        continue
    uuid, name = m.groups()
    path = Path(name)
    assert name == d['actualPath'] or name.startswith(('/System/Library/', '/usr/lib/'))
    images.append({'uuid': uuid, 'path': name, 'isPhysicalFile': path.is_file(), 'pathAppearsInHashedCacheMap': name in maps})
    if path.is_file() and name != d['actualPath']:
        physical[name] = {'sha256': digest(path), 'bytes': path.stat().st_size}
assert len(images) == 546
update = {'loadedVersionImages': images, 'otherLoaderDiagnostics': diagnostics,
          'physicalLoadedSystemFiles': physical,
          'logicalSystemCacheDirectory': '/System/Cryptexes/OS/System/Library/dyld',
          'metadataClosureQualification': 'Actual version-only image UUID/path trace, physical system files if present, and entire dyld cache set/bytes are bound. Cache aliases absent from map spelling retain actual UUID/path evidence; no claim of per-image extraction or Wasm execution.'}
# The first inline capture is retained byte-exactly by requiring replay equality.
for key, value in update.items(): assert d.get(key, value) == value, key
d.update(update)
save(p, d)
assert digest(p) == before
save(HERE / 'augmentation-receipt.json', {'argv': [sys.executable, '-B', str(Path(__file__))],
     'sourceSHA256': digest(__file__), 'pythonExecutableSHA256': digest(sys.executable),
     'pythonVersion': sys.version, 'provenanceUnchanged': True, 'provenanceSHA256': digest(p),
     'rawTraceSHA256': digest(HERE / d['loaderTraceRaw']), 'images': len(images),
     'physicalSystemFiles': len(physical), 'compilerCompilationExecuted': False,
     'wasmExecuted': False, 'newChildProcesses': 0})
print('Exact loader-image replay passed; provenance bytes unchanged')
