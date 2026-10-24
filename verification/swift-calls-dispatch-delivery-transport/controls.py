"""Pure byte-transport controls in owned artificial fixtures; no product execution."""
from pathlib import Path
import copy, gzip, hashlib, json, os, stat, sys, tempfile
import restore as r
HERE = Path(__file__).resolve().parent
rows = []
def reject(name, fn):
    try: fn()
    except (ValueError, OSError, EOFError): rows.append({'name': name, 'rejected': True})
    else: raise AssertionError('accepted invalid transport: ' + name)
def hashbytes(x): return hashlib.sha256(x).hexdigest()
def entry(data, packed):
    return {'path': 'evidence/raw.json', 'bytes': len(data), 'sha256': hashbytes(data),
            'mode': '100644', 'payload': 'payloads/raw.json.gz',
            'gzip': {'bytes': len(packed), 'sha256': hashbytes(packed)}}
with tempfile.TemporaryDirectory(prefix='owned-controls-', dir=HERE) as temp:
    base = Path(temp); repo = base / 'repo'; payloads = base / 'transport'
    (repo / 'evidence').mkdir(parents=True); (payloads / 'payloads').mkdir(parents=True)
    data = b'{"scope":"artificial byte-transport control"}\n'; packed = gzip.compress(data, mtime=0)
    target = repo / 'evidence/raw.json'; payload = payloads / 'payloads/raw.json.gz'; payload.write_bytes(packed)
    row = entry(data, packed); fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = r.restore_entry(fd, payloads, row)
        assert result['result'] == 'created-verified-exact-raw-file' and target.read_bytes() == data
        assert stat.S_IMODE(target.stat().st_mode) == 0o644
        before = target.stat(); assert r.restore_entry(fd, payloads, row)['result'] == 'existing-byte-identical-no-op'
        after = target.stat(); assert (before.st_ino, before.st_mtime_ns) == (after.st_ino, after.st_mtime_ns)
        target.write_bytes(b'conflicting existing bytes')
        reject('existing-conflicting-file', lambda: r.restore_entry(fd, payloads, row)); assert target.read_bytes() == b'conflicting existing bytes'
        target.unlink(); target.mkdir(); reject('existing-directory', lambda: r.restore_entry(fd, payloads, row)); target.rmdir()
        outside = base / 'outside'; outside.write_bytes(b'preserve outside')
        target.symlink_to(outside); reject('existing-file-link', lambda: r.restore_entry(fd, payloads, row)); assert outside.read_bytes() == b'preserve outside'; target.unlink()
        saved = repo / 'evidence'; saved.rename(repo / 'real-evidence'); saved.symlink_to(repo / 'real-evidence', target_is_directory=True)
        reject('symlink-target-ancestor', lambda: r.restore_entry(fd, payloads, row)); saved.unlink(); (repo / 'real-evidence').rename(saved)
        for name, raw in [('corrupt-compressed-bytes', packed[:8] + bytes([packed[8] ^ 1]) + packed[9:]), ('truncated-compressed-bytes', packed[:-5]), ('extra-compressed-bytes', packed + b'extra')]:
            payload.write_bytes(raw); reject(name, lambda: r.restore_entry(fd, payloads, row)); assert not target.exists()
        for name, raw in [('bounded-truncated-gzip-stream', packed[:-5]), ('bounded-extra-raw-length', gzip.compress(data + b'extra', mtime=0)), ('bounded-wrong-raw-hash', gzip.compress(b'x' * len(data), mtime=0))]:
            payload.write_bytes(raw); altered = copy.deepcopy(row); altered['gzip'] = {'bytes': len(raw), 'sha256': hashbytes(raw)}
            reject(name, lambda altered=altered: r.restore_entry(fd, payloads, altered)); assert not target.exists()
        payload.write_bytes(packed)
        real_link = payloads / 'payloads/raw-real.gz'; payload.rename(real_link); payload.symlink_to(real_link)
        reject('payload-file-link', lambda: r.restore_entry(fd, payloads, row)); payload.unlink(); real_link.rename(payload)
        packdir = payloads / 'payloads'; packdir.rename(payloads / 'real-payloads'); packdir.symlink_to(payloads / 'real-payloads', target_is_directory=True)
        reject('payload-ancestor-link', lambda: r.restore_entry(fd, payloads, row)); packdir.unlink(); (payloads / 'real-payloads').rename(packdir)
        payload.write_bytes(b'not gzip')
        reject('invalid-gzip-header', lambda: r.payload_check(payloads, entry(data, b'not gzip')))
        payload.write_bytes(packed)
        # Force the exact temporary-name collision; the conflicting file must survive.
        original = r.secrets.token_hex; r.secrets.token_hex = lambda _: 'collision'
        scratch = repo / 'evidence/.mixer-evidence-restore-collision'; scratch.write_bytes(b'preserve collision')
        try: reject('temporary-exclusive-collision', lambda: r.restore_entry(fd, payloads, row)); assert scratch.read_bytes() == b'preserve collision'
        finally: r.secrets.token_hex = original; scratch.unlink()
        original_link = r.os.link
        def race_link(src, dest, **kw):
            race = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=kw['dst_dir_fd'])
            with os.fdopen(race, 'wb') as f: f.write(b'preserve concurrent target')
            return original_link(src, dest, **kw)
        r.os.link = race_link
        try:
            reject('concurrent-exclusive-target-creation', lambda: r.restore_entry(fd, payloads, row))
            assert target.read_bytes() == b'preserve concurrent target'
        finally: r.os.link = original_link; target.unlink()
        assert not list((repo / 'evidence').glob('.mixer-evidence-restore-*'))
    finally: os.close(fd)
    root_link = base / 'linked-root'; root_link.symlink_to(repo, target_is_directory=True)
    reject('symlink-checkout-root', lambda: r.no_symlink_ancestors(root_link))
    reject('noncanonical-checkout-root', lambda: r.no_symlink_ancestors(repo / '..' / 'repo'))
    manifest = json.loads((HERE / 'transport-manifest.json').read_bytes()); r.validate_manifest(manifest)
    for name, path in [('parent-traversal', '../outside'), ('absolute-target', '/tmp/outside'), ('normalized-traversal', 'verification/../outside'), ('empty-target', '')]:
        value = copy.deepcopy(manifest); value['entries'][0]['path'] = path
        reject(name, lambda value=value: r.validate_manifest(value))
    for name, mutate in [
        ('extra-entry', lambda d: d['entries'].append(copy.deepcopy(d['entries'][0]))),
        ('changed-selected-raw-hash', lambda d: d['entries'][0].update(sha256='0' * 64)),
        ('changed-selected-raw-length', lambda d: d['entries'][0].update(bytes=d['entries'][0]['bytes'] + 1)),
        ('changed-selected-mode', lambda d: d['entries'][0].update(mode='100755')),
        ('payload-traversal', lambda d: d['entries'][0].update(payload='../payload.gz')),
    ]:
        value = copy.deepcopy(manifest); mutate(value); reject(name, lambda value=value: r.validate_manifest(value))
    saved_here = r.HERE; fake = base / 'fake-companion'; fake.mkdir(); (fake / 'transport-manifest.json').write_bytes(b'wrong manifest')
    r.HERE = fake
    try: reject('fixed-manifest-hash-drift', lambda: r.main(['--check-payloads']))
    finally: r.HERE = saved_here
    # Original authority files are copied into an artificial checkout, never edited.
    actual_repo = HERE.parents[1]
    for name in manifest['authority']:
        p = repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((actual_repo / name).read_bytes())
    fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        r.authority_check(fd, manifest)
        authority = repo / next(iter(manifest['authority'])); authority.write_bytes(b'wrong authority')
        reject('wrong-original-authority', lambda: r.authority_check(fd, manifest))
    finally: os.close(fd)
assert not Path(temp).exists()
result = {'controls': rows, 'negativeControls': len(rows), 'allRejected': all(x['rejected'] for x in rows),
          'positiveArtificialRestoreAndExactNoOp': True, 'atomicExclusiveCreation': True,
          'allFailureScratchRemoved': True, 'artificialFixtureRootRemoved': True,
          'existingEvidenceModified': False, 'compilerOrProductRuntimeExecuted': False,
          'argv': [sys.executable, '-B', str(Path(__file__))], 'sourceSHA256': hashbytes(Path(__file__).read_bytes()),
          'restoreSourceSHA256': hashbytes((HERE / 'restore.py').read_bytes()), 'pythonVersion': sys.version}
(HERE / 'controls.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(len(rows), 'pure transport failure controls rejected; exact artificial restore/no-op passed; owned fixture removed')
