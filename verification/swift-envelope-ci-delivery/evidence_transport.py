#!/usr/bin/env python3
"""Verify or recover a sealed evidence archive. Never execute archive members."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(name):
    path = PurePosixPath(name)
    if (not name or not path.parts or name != str(path) or path.is_absolute()
            or any(part in ('.', '..', '.git') for part in path.parts)
            or '\\' in name or '\x00' in name):
        raise ValueError('Noncanonical member: ' + repr(name))
    return path


def verify(archive, manifest, output=None):
    record = json.loads(manifest.read_bytes())
    expected = record['members']
    if (not isinstance(expected, list) or not 0 < len(expected) <= 4096
            or any(type(row.get('bytes')) is not int or row['bytes'] < 0 for row in expected)
            or sum(row['bytes'] for row in expected) > 512 * 1024 * 1024):
        raise ValueError('Evidence inventory exceeds the selected transport bounds')
    names = [str(canonical(row['path'])) for row in expected]
    if len(names) != len(set(names)) or len(names) != record['member_count']:
        raise ValueError('Duplicate or inconsistent member inventory')
    if sum(row['bytes'] for row in expected) != record['uncompressed_bytes']:
        raise ValueError('Inconsistent byte inventory')
    if archive.stat().st_size != record['archive_bytes'] or digest(archive) != record['archive_sha256']:
        raise ValueError('Archive identity differs')
    if output is not None:
        output = output.absolute()
        if output.exists() or '..' in output.parts or '.git' in output.parts:
            raise ValueError('Recovery requires a new destination outside Git metadata')
        if any(path.is_symlink() for path in [output, *output.parents]):
            raise ValueError('Recovery cannot traverse a symlink')
        if not output.parent.is_dir():
            raise ValueError('Recovery parent must already exist')
        output.mkdir()
    verified = 0
    with tarfile.open(archive, 'r:gz') as tar:
        for member, row in zip(tar, expected, strict=True):
            if (member.name != row['path'] or not member.isfile()
                    or member.size != row['bytes'] or member.linkname):
                raise ValueError('Archive member differs: ' + member.name)
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError('Missing ordinary file stream')
            with stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != row['sha256']:
                raise ValueError('Member digest differs: ' + member.name)
            if output is not None:
                target = output / canonical(member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, target.open('xb') as destination:
                    shutil.copyfileobj(source, destination, 65536)
                if target.stat().st_size != row['bytes'] or digest(target) != row['sha256']:
                    raise ValueError('Recovered file differs: ' + member.name)
            verified += 1
    return {'archive_sha256': record['archive_sha256'], 'members_verified': verified,
            'bytes_verified': record['uncompressed_bytes'], 'extracted_to': str(output) if output else None,
            'members_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.manifest, args.out), indent=2))
