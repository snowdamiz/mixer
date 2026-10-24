"""Restore only four selected missing raw evidence files; never overwrite."""
from pathlib import Path, PurePosixPath
import argparse, gzip, hashlib, json, os, secrets, stat, sys
HERE = Path(__file__).resolve().parent
MANIFEST_SHA256 = 'b5580b593d27f36d2acc5ad3e9a7dc1660a0b1a163c7ac11cbe57b6edf3a9922'
EXPECTED = {'verification/swift-reactor-lifecycle-accounting/paired-layouts.json': (105906299, 'babe29e41a6217e74375b529cca829a50000b67c962878bcdd7ea1e358c1b875', 'payloads/paired-layouts.json.gz'), 'verification/swift-reactor-lifecycle-accounting/inventory-final.json': (56074963, 'c6ccf90f73249ad7c4341a18441b69d03cd5fdab3d5cef7852a8e76d2a2aefb4', 'payloads/inventory-final.json.gz'), 'verification/swift-reactor-lifecycle-accounting/inventory.json': (56073803, '35afcdee191200bb87ffc1e509f9afb07a279c2fa129e6612aa8c44ce26b87a5', 'payloads/inventory.json.gz'), 'verification/swift-reactor-lifecycle-accounting/discovery-final-preinstall/inventory.json': (56073803, '35afcdee191200bb87ffc1e509f9afb07a279c2fa129e6612aa8c44ce26b87a5', 'payloads/discovery-final-preinstall--inventory.json.gz')}
CHUNK = 1024 * 1024
def require(ok, message):
    if not ok: raise ValueError(message)
def components(name):
    p = PurePosixPath(name)
    require(bool(p.parts) and not p.is_absolute() and p.as_posix() == name and all(x not in ('', '.', '..') for x in p.parts), 'invalid relative path')
    return p.parts
def hash_stream(f, expected_bytes):
    h = hashlib.sha256(); count = 0
    while True:
        b = f.read(min(CHUNK, expected_bytes - count + 1))
        if not b: break
        count += len(b); require(count <= expected_bytes, 'extra bytes'); h.update(b)
    require(count == expected_bytes, 'truncated bytes')
    return h.hexdigest()
def digest_bytes(data): return hashlib.sha256(data).hexdigest()
def no_symlink_ancestors(p):
    require(p.is_absolute() and p == p.resolve(), 'root must use its exact canonical absolute path')
    for q in [p, *p.parents]: require(not q.is_symlink(), 'symlink ancestor')
def open_parent(root_fd, name):
    parts = components(name); fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        return fd, parts[-1]
    except BaseException:
        os.close(fd); raise
def open_regular(root_fd, name):
    fd, leaf = open_parent(root_fd, name)
    try:
        st = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
        require(stat.S_ISREG(st.st_mode), 'expected regular file')
        out = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try: require(os.fstat(out).st_ino == st.st_ino and os.fstat(out).st_dev == st.st_dev, 'file identity changed')
        except BaseException:
            os.close(out); raise
        return out
    finally: os.close(fd)
def validate_manifest(data):
    require(data['schema'] == 1 and len(data['entries']) == 4, 'fixed four-entry manifest required')
    require({r['path'] for r in data['entries']} == set(EXPECTED), 'unselected target')
    require(set(data['excludedRawPaths']) == set(EXPECTED), 'exclusion drift')
    for row in data['entries']:
        components(row['path']); components(row['payload'])
        n, sha, payload = EXPECTED[row['path']]
        require((row['bytes'], row['sha256'], row['payload']) == (n, sha, payload) and row['mode'] == '100644', 'selected target drift')
        require(0 < row['gzip']['bytes'] < 95_000_000 and len(row['gzip']['sha256']) == 64, 'invalid compressed bound')
def payload_check(base, row, sink=None):
    """Validate compressed bytes, then decompress at most the fixed raw bound."""
    no_symlink_ancestors(base)
    fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: source_fd = open_regular(fd, row['payload'])
    finally: os.close(fd)
    with os.fdopen(source_fd, 'rb') as f:
        require(hash_stream(f, row['gzip']['bytes']) == row['gzip']['sha256'], 'gzip hash mismatch')
        f.seek(0); h = hashlib.sha256(); count = 0
        with gzip.GzipFile(fileobj=f, mode='rb') as z:
            while True:
                b = z.read(min(CHUNK, row['bytes'] - count + 1))
                if not b: break
                count += len(b); require(count <= row['bytes'], 'extra decompressed bytes'); h.update(b)
                if sink is not None: sink.write(b)
        require(count == row['bytes'] and h.hexdigest() == row['sha256'], 'raw bytes/hash mismatch')
        return {'bytes': count, 'sha256': h.hexdigest(), 'gzipSHA256': row['gzip']['sha256']}
def restore_entry(root_fd, base, row):
    parent, leaf = open_parent(root_fd, row['path']); tmp = None; created = False
    try:
        try: existing = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError: existing = None
        if existing is not None:
            require(stat.S_ISREG(existing.st_mode), 'existing target is not a regular file')
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
            with os.fdopen(fd, 'rb') as f:
                now = os.fstat(f.fileno())
                require((now.st_dev, now.st_ino) == (existing.st_dev, existing.st_ino), 'existing file changed')
                require(hash_stream(f, row['bytes']) == row['sha256'], 'existing target conflicts')
            return {'path': row['path'], 'result': 'existing-byte-identical-no-op'}
        tmp = '.mixer-evidence-restore-' + secrets.token_hex(16)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        created = True
        with os.fdopen(fd, 'wb') as f:
            payload_check(base, row, f); f.flush(); os.fchmod(f.fileno(), 0o644); os.fsync(f.fileno())
        # link(2) atomically creates a new name and fails EEXIST; no overwrite.
        os.link(tmp, leaf, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        return {'path': row['path'], 'result': 'created-verified-exact-raw-file', 'mode': '100644'}
    finally:
        if created: os.unlink(tmp, dir_fd=parent)
        os.close(parent)
def authority_check(root_fd, data):
    name = 'verification/swift-reactor-lifecycle-accounting/seal.json'
    require(set(data['authority']) == {name}, 'authority set drift')
    row = data['authority'][name]
    require(row['sha256'] == '02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd', 'wrong accounting seal')
    fd = open_regular(root_fd, name)
    with os.fdopen(fd, 'rb') as f:
        raw = f.read(row['bytes'] + 1)
    require(len(raw) == row['bytes'] and digest_bytes(raw) == row['sha256'], 'authority drift')
    sealed = json.loads(raw)['files']
    prefix = 'verification/swift-reactor-lifecycle-accounting/'
    for entry in data['entries']:
        require(entry['path'].startswith(prefix), 'unselected authority path')
        require(sealed[entry['path'][len(prefix):]] == entry['sha256'], 'raw target not selected by original seal')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--check-payloads', action='store_true')
    args = parser.parse_args(argv)
    raw = (HERE / 'transport-manifest.json').read_bytes()
    require(digest_bytes(raw) == MANIFEST_SHA256, 'transport manifest drift')
    data = json.loads(raw); validate_manifest(data)
    if args.check_payloads:
        require(args.repo is None, 'payload-only check takes no checkout')
        print(json.dumps({'discardStreamChecks': [payload_check(HERE, row) for row in data['entries']], 'repoWritten': False}, sort_keys=True)); return
    require(args.repo is not None, '--repo or --check-payloads required')
    root = args.repo; no_symlink_ancestors(root)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        authority_check(fd, data)
        rows = [restore_entry(fd, HERE, row) for row in data['entries']]
    finally: os.close(fd)
    print(json.dumps({'restored': rows, 'normalization': 'none', 'existingEvidenceOverwritten': False}, sort_keys=True))
if __name__ == '__main__': main()
