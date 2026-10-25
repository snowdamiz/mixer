"""Read-only packet verification plus finite synthetic tests; no product import."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    seal_path = HERE / 'seal.json'
    seal = json.loads(seal_path.read_text())
    if (HERE / 'seal.sha256').read_text() != sha(seal_path) + '  seal.json\n':
        raise ValueError('seal digest')
    expected = set(seal['members'])
    actual = {str(p.relative_to(ROOT)) for p in HERE.rglob('*')
              if p.is_file() and p.name not in {'seal.json', 'seal.sha256'}}
    actual.add('docs/swift-ordered-retention-diagnostic-design.md')
    if actual != expected:
        raise ValueError('exact packet inventory')
    for name, member in seal['members'].items():
        path = ROOT / name
        if path.is_symlink() or '..' in Path(name).parts or not path.is_file():
            raise ValueError('unsafe member')
        if path.stat().st_size != member['bytes'] or sha(path) != member['sha256']:
            raise ValueError('member drift: ' + name)
    history = HERE / 'history'
    first_bytes = (history / 'first-freeze-seal.json').read_bytes()
    first = json.loads(first_bytes)
    preservation = json.loads((history / 'first-freeze-preservation.json').read_text())
    if hashlib.sha256(first_bytes).hexdigest() != preservation['originalSealSHA256']:
        raise ValueError('first freeze seal preservation')
    archive = history / 'first-freeze.tar.gz'
    if archive.stat().st_size != preservation['archiveBytes'] or sha(archive) != preservation['archiveSHA256']:
        raise ValueError('first freeze archive preservation')
    expected_old = set(first['members']) | {
        'verification/swift-ordered-retention-diagnostic-design/seal.json',
        'verification/swift-ordered-retention-diagnostic-design/seal.sha256'}
    with tarfile.open(archive, 'r:gz') as tf:
        members = tf.getmembers()
        if len(members) != 22 or {m.name for m in members} != expected_old:
            raise ValueError('first freeze exact archive names')
        for member in members:
            if not member.isfile() or '..' in Path(member.name).parts or member.name.startswith('/'):
                raise ValueError('unsafe first freeze member')
            data = tf.extractfile(member).read()
            if member.name in first['members']:
                prior = first['members'][member.name]
                if len(data) != prior['bytes'] or hashlib.sha256(data).hexdigest() != prior['sha256']:
                    raise ValueError('first freeze member drift')
            elif member.name.endswith('/seal.json') and data != first_bytes:
                raise ValueError('first freeze embedded seal')
            elif member.name.endswith('/seal.sha256') and data != (preservation['originalSealSHA256'] + '  seal.json\n').encode():
                raise ValueError('first freeze embedded sidecar')
    manifest_path = ROOT / 'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if len(manifest) != 132 or sha(manifest_path) != seal['baselineNamedClosure']:
        raise ValueError('named baseline manifest')
    for name, digest in manifest.items():
        path = ROOT / 'vm' / name
        if '..' in Path(name).parts or path.is_symlink() or sha(path) != digest:
            raise ValueError('live named VM drift: ' + name)
    argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(HERE),
            '-p', 'test_*_model.py', '-v']
    result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, timeout=30)
    if result.returncode:
        sys.stderr.buffer.write(result.stderr)
        raise ValueError('finite test failure')
    print(json.dumps(dict(status='pass', sealSHA256=sha(seal_path), members=len(expected),
                          baselineFiles=132, finiteCommand=argv,
                          finiteStdoutSHA256=hashlib.sha256(result.stdout).hexdigest(),
                          finiteStderrSHA256=hashlib.sha256(result.stderr).hexdigest(),
                          finiteSummary=result.stderr.decode().splitlines()[-3:],
                          scope=seal['scope']), sort_keys=True))


if __name__ == '__main__':
    main()
