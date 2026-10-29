#!/usr/bin/env python3
"""Materialize a closed shared-input overlay into this sibling's owned CI scratch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/swift-cache-state-ci/pack'
OVERLAY = HERE / 'pack-overlay'
OVERLAY_MANIFEST = HERE / 'overlay-manifest.json'
MATERIALIZED = HERE / 'materialized'
OVERLAY_SHA256 = 'c7c4ecd65f4a92f1edd2b36fcbb54bc8e233662b9a673d6555fd36b284d201a6'
BASE_MANIFEST_SHA256 = 'd1caf2069e17ac1beff6707d6e084ea49d18382bc959d73d5184ec49cb7886b9'
BASE_TREE_SHA256 = 'ab2d0a6ef1c0df25f9624fc4b7d72cb0007df749fd1ed88bf43f243336eeedb2'
ORIGINAL_SOURCE_SHA256 = '7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411'
ACCEPTED_SOURCE_SHA256 = 'f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141'
REPLACEMENTS = {'manifest.json', 'inventories/bindings.json',
                'inventories/source-roster.json', 'source/regression/independent_tests.rs'}


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def load(path):
    return json.loads(regular(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False, 'Nonfinite JSON'))


def save(path, value):
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    os.replace(partial, path)


def member(name):
    need(isinstance(name, str), 'Member must be text')
    path = PurePosixPath(name)
    need(name and name == str(path) and name != '.' and not path.is_absolute()
         and not any(part in {'..', '.git'} for part in path.parts)
         and '\\' not in name and '\x00' not in name, 'Noncanonical member path')
    return Path(name)


def no_symlinks(path):
    need(path.is_absolute(), 'Absolute path required')
    for parent in [*reversed(path.parents), path]:
        need(not parent.is_symlink(), 'Symlink forbidden: ' + str(parent))


def regular(path):
    no_symlinks(path)
    need(stat.S_ISREG(path.stat().st_mode), 'Regular file required')
    return path


def identity(path):
    no_symlinks(path)
    observed = path.stat()
    need(stat.S_ISDIR(observed.st_mode) and observed.st_uid == os.geteuid(),
         'Owned directory required')
    return [observed.st_dev, observed.st_ino, observed.st_uid]


def inventory(base, excluded=()):
    identity(base)
    rows = []
    for directory, dirs, files in os.walk(base, followlinks=False):
        if Path(directory) == base:
            dirs[:] = [name for name in dirs if name not in excluded]
            files = [name for name in files if name not in excluded]
        for name in sorted(dirs + files):
            path = Path(directory) / name
            relative = path.relative_to(base).as_posix()
            member(relative)
            mode = path.lstat().st_mode
            need(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'Nonregular/symlink member')
            if stat.S_ISREG(mode):
                rows.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    return sorted(rows, key=lambda row: row['path'])


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_tree(base, manifest_hash, expected_tree=None):
    need(sha(regular(base / 'manifest.json')) == manifest_hash, 'Pinned pack manifest differs')
    manifest = load(base / 'manifest.json')
    rows = manifest['members']
    for row in rows:
        member(row['path'])
        need(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int
             and row['bytes'] >= 0, 'Malformed pack row')
    need(rows == sorted(rows, key=lambda row: row['path'])
         and len(rows) == len({row['path'] for row in rows}) == manifest['member_count'] == 86,
         'Pack member count/order/duplicates')
    need(sum(row['bytes'] for row in rows) == manifest['total_bytes']
         and tree(rows) == manifest['tree_sha256'], 'Pack digest/count')
    if expected_tree is not None:
        need(manifest['tree_sha256'] == expected_tree, 'Pinned pack tree differs')
    need([row for row in inventory(base) if row['path'] != 'manifest.json'] == rows,
         'Missing/extra/mutated pack member')
    allowed_dirs = {str(parent) for row in rows for parent in member(row['path']).parents if str(parent) != '.'}
    for directory, dirs, _ in os.walk(base, followlinks=False):
        for name in dirs:
            need((Path(directory) / name).relative_to(base).as_posix() in allowed_dirs,
                 'Extra pack directory')
    return manifest


def verify_inputs():
    need(sha(regular(OVERLAY_MANIFEST)) == OVERLAY_SHA256, 'Pinned overlay manifest differs')
    overlay = load(OVERLAY_MANIFEST)
    need(overlay['schema'] == 1 and overlay['base'] == {
        'path': 'verification/swift-cache-state-ci/pack', 'manifest_sha256': BASE_MANIFEST_SHA256,
        'tree_sha256': BASE_TREE_SHA256, 'member_count': 86}, 'Frozen base binding differs')
    base = verify_tree(BASE, BASE_MANIFEST_SHA256, BASE_TREE_SHA256)
    need(overlay['source_preimage_sha256'] == ORIGINAL_SOURCE_SHA256
         and sha(regular(BASE / 'source/regression/independent_tests.rs')) == ORIGINAL_SOURCE_SHA256,
         'Wrong original source preimage')
    replacements = overlay['replacements']
    need(len(replacements) == len({row['path'] for row in replacements}) == 4
         and {row['path'] for row in replacements} == REPLACEMENTS, 'Replacement closure/duplicates')
    expected_overlay = []
    by_path = {}
    for row in replacements:
        path = member(row['path'])
        need(row['overlay'] == 'pack-overlay/' + path.as_posix(), 'Overlay path binding differs')
        member(row['overlay'])
        source = regular(OVERLAY / path)
        need(sha(source) == row['sha256'] and source.stat().st_size == row['bytes'],
             'Missing/mutated overlay replacement')
        need(sha(regular(BASE / path)) == row['base_sha256'], 'Replacement base preimage differs')
        by_path[row['path']] = row
        expected_overlay.append({key: row[key] for key in ['path', 'bytes', 'sha256']})
    need(inventory(OVERLAY) == sorted(expected_overlay, key=lambda row: row['path']), 'Extra overlay member')
    allowed_overlay_dirs = {str(parent) for row in expected_overlay
                            for parent in member(row['path']).parents if str(parent) != '.'}
    for directory, dirs, _ in os.walk(OVERLAY, followlinks=False):
        for name in dirs:
            need((Path(directory) / name).relative_to(OVERLAY).as_posix() in allowed_overlay_dirs,
                 'Extra overlay directory')
    need(overlay['accepted_source_sha256'] == ACCEPTED_SOURCE_SHA256
         and by_path['source/regression/independent_tests.rs']['sha256'] == ACCEPTED_SOURCE_SHA256,
         'Reviewed source differs')
    candidate = load(OVERLAY / 'manifest.json')
    need(sha(OVERLAY / 'manifest.json') == overlay['candidate_manifest_sha256'], 'Candidate manifest differs')
    expected = []
    for row in base['members']:
        replacement = by_path.get(row['path'], row)
        expected.append({key: replacement[key] for key in ['path', 'bytes', 'sha256']})
    need(candidate['members'] == expected and candidate['member_count'] == 86
         and candidate['total_bytes'] == sum(row['bytes'] for row in expected)
         and candidate['tree_sha256'] == tree(expected) == overlay['candidate_tree_sha256']
         and candidate['compiler_targets'] == base['compiler_targets']
         and candidate['release_or_GA_authority'] is False, 'Effective candidate union differs')
    review = overlay['review']
    seal_path = ROOT / member(review['seal_path'])
    need(sha(regular(seal_path)) == review['seal_sha256'], 'Review seal differs')
    seal = load(seal_path)
    need(seal['tree_sha256'] == review['tree_sha256'] == tree(review['members'])
         and seal['members'] == review['members'], 'Review closure differs')
    for row in review['members']:
        path = regular(ROOT / member(row['path']))
        need(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Review member differs')
    return {'overlay_manifest_sha256': OVERLAY_SHA256, 'base_manifest_sha256': BASE_MANIFEST_SHA256,
            'base_tree_sha256': BASE_TREE_SHA256, 'candidate_manifest_sha256': overlay['candidate_manifest_sha256'],
            'candidate_tree_sha256': candidate['tree_sha256'], 'candidate_member_count': 86,
            'borrowed_unchanged_member_count': 83, 'review_tree_sha256': review['tree_sha256']}


def verify_materialized():
    inputs = verify_inputs()
    marker = load(MATERIALIZED / 'ownership.json')
    need(marker['purpose'] == 'mixer-shared-input-materialization'
         and marker['identity'] == identity(MATERIALIZED)
         and isinstance(marker['token'], str) and len(marker['token']) == 32
         and marker['inputs'] == inputs, 'Materialization ownership/binding differs')
    verify_tree(MATERIALIZED / 'pack', inputs['candidate_manifest_sha256'], inputs['candidate_tree_sha256'])
    return inputs


def materialize():
    inputs = verify_inputs()
    need(MATERIALIZED.is_absolute() and MATERIALIZED.parent == HERE
         and MATERIALIZED.name == 'materialized' and not MATERIALIZED.exists(),
         'Materialization must be fresh fixed owned sibling scratch')
    identity(HERE)
    no_symlinks(MATERIALIZED)
    MATERIALIZED.mkdir()
    marker = {'purpose': 'mixer-shared-input-materialization', 'token': uuid.uuid4().hex,
              'identity': identity(MATERIALIZED), 'inputs': inputs}
    save(MATERIALIZED / 'ownership.json', marker)
    receipt = {'schema': 1, 'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
               'inputs': inputs, 'copies': [], 'compiler_or_product_executed': False,
               'hardlinks_used': False, 'cleanup': 'retained owned materialization for diagnostic artifact'}
    try:
        pack = MATERIALIZED / 'pack'
        pack.mkdir()
        manifest = load(OVERLAY / 'manifest.json')
        for name in [row['path'] for row in manifest['members']] + ['manifest.json']:
            relative = member(name)
            source = regular((OVERLAY if name in REPLACEMENTS else BASE) / relative)
            target = pack / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as reader, target.open('xb') as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)
            before, after = source.stat(), target.stat()
            need((before.st_dev, before.st_ino) != (after.st_dev, after.st_ino), 'Materialization aliases source')
            receipt['copies'].append({'path': name, 'sha256': sha(target), 'bytes': after.st_size,
                                      'source': 'overlay' if name in REPLACEMENTS else 'frozen-base'})
        verify_materialized()
        need(load(MATERIALIZED / 'ownership.json') == marker, 'Materialization marker changed')
        receipt['status'] = 'passed-exact-materialization'
    except BaseException as error:
        receipt.update(status='failed-preserved-owned-materialization', error={'type': type(error).__name__, 'message': str(error)})
        raise
    finally:
        receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save(MATERIALIZED / 'materialization.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    result = verify_materialized() if args.verify_only else materialize()
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
