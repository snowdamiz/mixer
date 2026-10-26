#!/usr/bin/env python3
"""Root delivery preparation: copy only an explicitly supplied sealed member list."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
from evidence_transport import canonical, digest, verify

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def build(seal_path, expected_seal_hash, name):
    if not name.isascii() or not name.replace('-', '').isalnum():
        raise ValueError('Invalid archive label')
    seal = ROOT / canonical(seal_path)
    if digest(seal) != expected_seal_hash:
        raise ValueError('Selected seal differs')
    value = json.loads(seal.read_bytes())
    rows = value['members']
    if isinstance(rows, dict):
        rows = [{'path': name, **row} for name, row in rows.items()]
    rows = [dict(row) for row in rows]
    rows.append({'path': seal_path, 'bytes': seal.stat().st_size, 'sha256': digest(seal)})
    sidecar = seal.with_suffix('.sha256')
    if sidecar.is_file():
        rows.append({'path': str(sidecar.relative_to(ROOT)), 'bytes': sidecar.stat().st_size,
                     'sha256': digest(sidecar)})
    rows.sort(key=lambda row: row['path'])
    if len({row['path'] for row in rows}) != len(rows):
        raise ValueError('Duplicate member')
    archive = OUT / (name + '.tar.gz')
    manifest = OUT / (name + '-manifest.json')
    if archive.exists() or manifest.exists():
        raise ValueError('Transport output already exists')
    with archive.open('xb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as tar:
                for row in rows:
                    source = ROOT / canonical(row['path'])
                    if (not source.is_file() or any(p.is_symlink() for p in [source, *source.parents])
                            or source.stat().st_size != row['bytes'] or digest(source) != row['sha256']):
                        raise ValueError('Selected source differs: ' + row['path'])
                    info = tarfile.TarInfo(row['path'])
                    info.size, info.mode, info.mtime = row['bytes'], 0o644, 0
                    with source.open('rb') as stream:
                        tar.addfile(info, stream)
                    if digest(source) != row['sha256']:
                        raise ValueError('Source changed while archiving')
    record = {'schema': 1, 'archive': archive.name, 'archive_bytes': archive.stat().st_size,
              'archive_sha256': digest(archive), 'member_count': len(rows),
              'uncompressed_bytes': sum(row['bytes'] for row in rows), 'members': rows,
              'sealed_input': {'path': seal_path, 'sha256': expected_seal_hash},
              'path_semantics': 'Each members.path is an archive member / original repository-relative evidence path; presence in this manifest does not assert an ordinary checked-out file.',
              'runtime_dependency': False, 'members_executed': False}
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    result = verify(archive, manifest)
    result.update({'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'command': sys.argv, 'python_version': sys.version,
                   'archive_bytes': record['archive_bytes'], 'manifest_sha256': digest(manifest)})
    (OUT / (name + '-verification.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    build(args.seal, args.sha256, args.name)
