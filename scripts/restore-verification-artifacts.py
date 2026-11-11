#!/usr/bin/env python3
"""Restore regular verification files from the archived Git tree."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class RestoreError(Exception):
    pass


def git_command(repo, *args):
    return ['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(repo), *args]


def git_environment():
    return {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'}


def git(repo, *args, data=None):
    result = subprocess.run(git_command(repo, *args), env=git_environment(), input=data, capture_output=True)
    if result.returncode:
        raise RestoreError(os.fsdecode(result.stderr).strip() or 'Git command failed')
    return result.stdout


def verification_path(raw):
    parts = raw.split('/')
    if parts[0] != 'verification' or any(part in ('', '.', '..') or part.lower() == '.git' for part in parts):
        raise RestoreError(f'Expected a literal path under verification: {raw!r}')
    return Path(*parts)


def archive_metadata(repo):
    metadata = json.loads((repo / 'verification/archive.json').read_bytes())
    if not isinstance(metadata, dict) or type(metadata.get('schema_version')) is not int or metadata['schema_version'] != 1:
        raise RestoreError('Unsupported verification archive schema')
    commit = metadata.get('archive_commit')
    ref = metadata.get('archive_ref')
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise RestoreError('Invalid archive_commit in verification/archive.json')
    if not isinstance(ref, str) or not re.fullmatch(r'refs/tags/verification-archive/[0-9A-Za-z_-]+', ref):
        raise RestoreError('Invalid archive_ref in verification/archive.json')
    return commit, ref


def archived_files(repo, commit, path, fetch_hint):
    try:
        kind = git(repo, 'cat-file', '-t', commit).strip()
        if kind != b'commit':
            raise RestoreError(f'{commit} is not a commit')
        entries = git(repo, 'ls-tree', '-rz', '--full-tree', commit, '--', path.as_posix())
    except RestoreError as error:
        raise RestoreError(f'Cannot read archive commit {commit}. {fetch_hint}\n{error}') from error
    files = []
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        attributes, name = entry.split(b'\t', 1)
        mode, kind, oid = attributes.split()
        archived_path = verification_path(os.fsdecode(name))
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise RestoreError(f'Archive path is not a regular file: {archived_path}')
        files.append((archived_path, int(mode[-3:], 8), oid))
    if not files:
        raise RestoreError(f'No archived files match {path} at {commit}')
    return files


def destination(repo, raw):
    if '..' in raw.parts:
        raise RestoreError('The output path cannot contain ..')
    output = raw.absolute()
    if os.path.lexists(output):
        raise RestoreError(f'The output directory must be new: {output}')
    if output.parent.resolve(strict=True) != output.parent:
        raise RestoreError(f'The output directory has a symlink ancestor: {output}')
    if output.is_relative_to(repo):
        if not output.is_relative_to(repo / 'verification/local'):
            raise RestoreError('Choose an output outside the repository or inside verification/local')
        if git(repo, 'ls-files', '-z', '--', output.relative_to(repo).as_posix()):
            raise RestoreError(f'The output would overlap tracked files: {output}')
    return output


def read_blob_sizes(repo, oids):
    entries = git(repo, 'cat-file', '--batch-check=%(objecttype) %(objectsize)',
                  data=b'\n'.join(oids) + b'\n').splitlines()
    sizes = {}
    missing = []
    for oid, entry in zip(oids, entries, strict=True):
        kind, size = entry.split()
        if kind == b'blob' and size.isdigit():
            sizes[oid] = int(size)
        elif entry == oid + b' missing':
            missing.append(oid)
        else:
            raise RestoreError(f'Expected archive blob {oid.decode()}, got {entry!r}')
    return sizes, missing


def blob_sizes(repo, files, fetch_remote):
    sizes, missing = read_blob_sizes(repo, sorted({oid for _, _, oid in files}))
    if missing and fetch_remote:
        git(repo, '-c', 'fetch.negotiationAlgorithm=noop', 'fetch',
            '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules',
            '--no-auto-maintenance', '--filter=blob:none', '--stdin', '--', fetch_remote,
            data=b'\n'.join(missing) + b'\n')
        fetched, missing = read_blob_sizes(repo, missing)
        sizes.update(fetched)
    if missing:
        raise RestoreError(f'{len(missing)} requested archive blobs are unavailable locally. '
                           'Use --fetch-missing-from REMOTE to fetch them in a partial clone.')
    return sizes


def write_blob(process, oid, size, output, mode):
    process.stdin.write(oid + b'\n')
    process.stdin.flush()
    size_bytes = str(size).encode('ascii')
    if process.stdout.readline().split() != [oid, b'blob', size_bytes]:
        raise RestoreError(f'Cannot read archive blob {oid.decode()} with expected size {size}')
    digest = hashlib.sha1(b'blob ' + size_bytes + b'\0')
    with output.open('xb') as stream:
        remaining = size
        while remaining:
            data = process.stdout.read(min(remaining, 1024 * 1024))
            if not data:
                raise RestoreError(f'Truncated archive blob for {output}')
            stream.write(data)
            digest.update(data)
            remaining -= len(data)
        if process.stdout.read(1) != b'\n' or digest.hexdigest().encode() != oid:
            raise RestoreError(f'Archive blob failed hash verification for {output}')
        os.fchmod(stream.fileno(), mode)


def restore(repo, path, output, fetch_remote):
    commit, ref = archive_metadata(repo)
    fetch_hint = f'To obtain the archive commit and tree, run: git fetch --filter=blob:none origin {ref}'
    output = destination(repo, output)
    files = archived_files(repo, commit, path, fetch_hint)
    sizes = blob_sizes(repo, files, fetch_remote)
    output.mkdir(mode=0o700)
    try:
        with subprocess.Popen(
            git_command(repo, 'cat-file', '--batch'),
            env=git_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ) as process:
            for path, mode, oid in files:
                target = output / path
                target.parent.mkdir(parents=True, exist_ok=True)
                write_blob(process, oid, sizes[oid], target, mode)
        if process.returncode:
            raise RestoreError('Git could not finish reading the archive')
    except BaseException:
        shutil.rmtree(output)
        raise
    print(f'Restored {len(files)} file(s) to {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='literal verification file or directory in the archive')
    parser.add_argument('--output', required=True, type=Path, help='new directory for repository-relative files')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help='Mixer checkout')
    parser.add_argument('--fetch-missing-from', metavar='REMOTE',
                        help='fetch only the requested missing blobs from this remote')
    args = parser.parse_args()
    try:
        repo = Path(os.fsdecode(git(args.repo, 'rev-parse', '--show-toplevel').rstrip(b'\n'))).resolve(strict=True)
        restore(repo, verification_path(args.path.removesuffix('/')), args.output, args.fetch_missing_from)
    except (OSError, ValueError, RestoreError) as error:
        print(f'Restore failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
