"""Create two exact gzip transports without changing any existing evidence."""
from pathlib import Path
import gzip, hashlib, json, os, sys, zlib
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V7 = ROOT / 'verification/swift-calls-dispatch/v7-fixture-expectations'
V6 = ROOT / 'verification/swift-calls-dispatch/v6-fixture-expectation'
SEAL = '79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        while b := f.read(1024 * 1024): h.update(b)
    return h.hexdigest()
def binding(p): return {'sha256': digest(p), 'bytes': p.stat().st_size}
def save(name, data):
    (HERE / name).write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
assert digest(V7 / 'review-seal.json') == SEAL
s = json.loads((V7 / 'review-seal.json').read_bytes())
h = json.loads((V7 / 'v6-history-bindings.json').read_bytes())
rows = []
for base, rel, payload, authority in [
    (V6, 'inventory-v5.json', 'payloads/v6-inventory-v5.raw.json.gz', h['files']),
    (V7, 'compiler-partitions-v5.json', 'payloads/v7-compiler-partitions-v5.raw.json.gz', s['bindings']),
]:
    source = base / rel
    assert not source.is_symlink() and binding(source) == authority[rel]
    dest = HERE / payload
    dest.parent.mkdir(exist_ok=True)
    assert not dest.exists(), 'never overwrite a captured transport'
    with source.open('rb') as src, dest.open('xb') as out:
        with gzip.GzipFile(filename='', mode='wb', fileobj=out, compresslevel=9, mtime=0) as z:
            while b := src.read(1024 * 1024): z.write(b)
    total = 0; checksum = hashlib.sha256()
    with gzip.open(dest, 'rb') as f:
        while b := f.read(1024 * 1024): total += len(b); checksum.update(b)
    assert total == authority[rel]['bytes'] and checksum.hexdigest() == authority[rel]['sha256']
    assert dest.stat().st_size < 95_000_000
    rows.append({'path': str(source.relative_to(ROOT)), 'bytes': total,
                 'sha256': checksum.hexdigest(), 'mode': '100644', 'payload': payload,
                 'gzip': binding(dest), 'originalAuthority': str((V7 / ('v6-history-bindings.json' if base == V6 else 'review-seal.json')).relative_to(ROOT))})
old = V6 / 'inventory-v5.json.gz'
old_raw_hash = hashlib.sha256(); old_bytes = 0
with gzip.open(old, 'rb') as f:
    while b := f.read(1024 * 1024): old_raw_hash.update(b); old_bytes += len(b)
assert binding(old) == h['files'][old.name]
manifest = {'schema': 1, 'scope': 'Portable exact-byte delivery only; no source or evidence replacement',
            'authority': {str(p.relative_to(ROOT)): binding(p) for p in [V7 / 'review-seal.json', V7 / 'v6-history-bindings.json']},
            'entries': rows, 'normalization': 'none; original raw bytes restored exactly',
            'excludedRawPaths': [x['path'] for x in rows],
            'originalHistoricalGzipPreserved': {'path': str(old.relative_to(ROOT)), **binding(old),
                'decompressedBytes': old_bytes, 'decompressedSHA256': old_raw_hash.hexdigest(),
                'equalsBoundRawInventory': False}}
assert old_raw_hash.hexdigest() != rows[0]['sha256']
save('transport-manifest.json', manifest)
save('preparation.json', {'argv': [sys.executable, '-B', str(Path(__file__))],
     'source': binding(Path(__file__)), 'pythonExecutable': str(Path(sys.executable).resolve()),
     'pythonSHA256': digest(Path(sys.executable)), 'pythonVersion': sys.version, 'zlibVersion': zlib.ZLIB_VERSION,
     'gzip': {'mtime': 0, 'filename': '', 'compressionLevel': 9, 'streamChunkBytes': 1048576},
     'existingInputsUnchanged': all(binding(ROOT / x['path']) == {'bytes': x['bytes'], 'sha256': x['sha256']} for x in rows),
     'existingHistoricalGzipUnchanged': binding(old) == h['files'][old.name],
     'runtimeOrCompilerExecuted': False, 'gitExecuted': False})
print(json.dumps({'manifestSHA256': digest(HERE / 'transport-manifest.json'), 'entries': rows}, sort_keys=True))
