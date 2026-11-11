#!/usr/bin/env python3
"""Check the staged verification tree against its retention budget."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


POLICY = 'scripts/verification-artifact-policy.json'
LIMITS = ('max_total_bytes', 'max_files', 'max_file_bytes')
EXCEPTIONS = ('large_files', 'generated_files')
BUILD_DIRS = {'node_modules', '.build', 'target', '.gradle', '__pycache__', '.swiftpm'}
OUTPUT_SUFFIXES = ('.apk', '.aab', '.class', '.o', '.obj', '.a', '.so', '.dylib',
                   '.dll', '.exe', '.pyc', '.wasm', '.zip', '.tar', '.tgz', '.gz',
                   '.ll', '.mir', '.s')
REGULAR_MODES = {'100644', '100755'}
OID = re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})')


def git(repo, *args, data=None, allow_lazy_fetch=True):
    env = os.environ.copy()
    if not allow_lazy_fetch:
        env['GIT_NO_LAZY_FETCH'] = '1'
    return subprocess.run(['git', *args], cwd=repo, input=data, stdout=subprocess.PIPE,
                          env=env, check=True).stdout


def load_policy(repo):
    policy = json.loads(git(repo, 'cat-file', 'blob', f':{POLICY}'))
    version = policy.get('schema_version') if isinstance(policy, dict) else None
    if type(version) is not int or version != 1:
        raise ValueError(f'{POLICY}: expected schema_version 1')
    for key in LIMITS:
        value = policy.get(key)
        if type(value) is not int or value <= 0:
            raise ValueError(f'{POLICY}: {key} must be a positive integer')
    for key in EXCEPTIONS:
        rows = policy.get(key)
        if not isinstance(rows, dict):
            raise ValueError(f'{POLICY}: {key} must map paths to exact blob exceptions')
        for name, row in rows.items():
            if (not name.startswith('verification/') or not isinstance(row, dict)
                    or not isinstance(row.get('oid'), str) or not OID.fullmatch(row['oid'])
                    or type(row.get('size')) is not int or row['size'] < 0
                    or not isinstance(row.get('reason'), str) or not row['reason'].strip()):
                raise ValueError(f'{POLICY}: invalid {key} exception for {name!r}')
    return policy


def staged_verification(repo):
    raw = git(repo, 'ls-files', '--stage', '-z', '--', 'verification')
    for row in raw.split(b'\0'):
        if row:
            metadata, path = row.split(b'\t', 1)
            mode, oid, stage = metadata.decode('ascii').split()
            yield os.fsdecode(path), mode, oid, stage


def read_blob_sizes(repo, oids):
    if not oids:
        return {}, []
    data = ''.join(oid + '\n' for oid in oids).encode('ascii')
    output = git(repo, 'cat-file', '--batch-check=%(objecttype) %(objectsize)',
                 data=data, allow_lazy_fetch=False).decode('ascii').splitlines()
    sizes = {}
    missing = []
    for oid, row in zip(oids, output, strict=True):
        kind, size = row.split()
        if kind == 'blob':
            sizes[oid] = int(size)
        elif row == f'{oid} missing':
            missing.append(oid)
        else:
            raise ValueError(f'expected a blob for staged Git object {oid}, got {row!r}')
    return sizes, missing


def blob_sizes(repo, oids, fetch_remote):
    sizes, missing = read_blob_sizes(repo, sorted(oids))
    if missing and fetch_remote:
        # A sparse partial clone lacks these blobs. Fetch the exact selected IDs
        # in one request without materializing verification or changing refs.
        git(repo, 'fetch', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules',
            '--no-auto-maintenance', '--filter=blob:none', '--stdin', '--', fetch_remote,
            data=''.join(oid + '\n' for oid in missing).encode('ascii'))
        fetched, missing = read_blob_sizes(repo, missing)
        sizes.update(fetched)
    if missing:
        raise ValueError(f'{len(missing)} staged verification blobs are unavailable locally '
                         '(use --fetch-missing-from for a partial clone)')
    return sizes


def check(repo, fetch_remote):
    policy = load_policy(repo)
    entries = list(staged_verification(repo))
    if len(entries) > policy['max_files']:
        raise ValueError(f'verification contains {len(entries)} tracked files, '
                         f'exceeding max_files ({policy["max_files"]})')

    generated = {}
    for name, mode, oid, stage in entries:
        if stage != '0':
            raise ValueError(f'{name!r}: resolve index stage {stage} before checking verification')
        if mode not in REGULAR_MODES or not name.startswith('verification/'):
            raise ValueError(f'{name!r}: unsupported verification entry with mode {mode}')
        directories = PurePosixPath(name.lower()).parts[:-1]
        if BUILD_DIRS.intersection(directories) or name.lower().endswith(OUTPUT_SUFFIXES):
            exception = policy['generated_files'].get(name)
            if not exception or exception['oid'] != oid:
                raise ValueError(f'{name!r}: generated output belongs in verification/local/ '
                                 'unless the staged blob is an approved canonical fixture')
            generated[name] = exception

    sizes = blob_sizes(repo, {oid for _, _, oid, _ in entries}, fetch_remote)
    total = 0
    for name, _, oid, _ in entries:
        size = sizes[oid]
        total += size
        if name in generated and generated[name]['size'] != size:
            raise ValueError(f'{name!r}: generated output size differs from its canonical exception')
        if size > policy['max_file_bytes']:
            exception = policy['large_files'].get(name)
            if not exception or (exception['oid'], exception['size']) != (oid, size):
                raise ValueError(f'{name!r}: {size} staged bytes exceed max_file_bytes '
                                 f'({policy["max_file_bytes"]}) without an exact canonical exception')
    if total > policy['max_total_bytes']:
        raise ValueError(f'verification contains {total} tracked bytes, '
                         f'exceeding max_total_bytes ({policy["max_total_bytes"]})')
    print(f'Verification retention passed for {len(entries)} tracked files and {total} bytes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--fetch-missing-from', metavar='REMOTE',
                        help='fetch required staged blobs from this remote in a partial clone')
    args = parser.parse_args()
    try:
        check(args.repo, args.fetch_missing_from)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Verification retention failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
