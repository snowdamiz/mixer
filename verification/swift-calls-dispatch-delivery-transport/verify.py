"""Read-only transport binding and discard-stream verification."""
from pathlib import Path
import hashlib, json
import restore as r
HERE = Path(__file__).resolve().parent
seal = json.loads((HERE / 'review-seal.json').read_bytes())
for rel, row in seal['bindings'].items():
    p = HERE / rel
    assert p.is_file() and not p.is_symlink() and p.stat().st_size == row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256'], rel
assert hashlib.sha256((HERE / 'transport-manifest.json').read_bytes()).hexdigest() == seal['manifestSHA256'] == r.MANIFEST_SHA256
r.main(['--check-payloads'])
print('Separate transport bindings and both exact raw payloads verified; no checkout writes or runtime execution')
