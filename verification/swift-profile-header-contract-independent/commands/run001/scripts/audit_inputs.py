#!/usr/bin/env python3
"""Independent offline custody audit. Treat Rust and archives only as bytes."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import tarfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PREP = ROOT / 'verification/swift-profile-header-preparation'
EXPECTED = {
    'verification/swift-profile-header-preparation/seal.json':
        'aee8ffbe028f9fe3084a62a81fe0946dc6a21cc132e16d83915917cf6657515f',
    'verification/swift-semantic-adapter-root-review/profile-header-preparation-custody.json':
        '89a0afcaaec10e0d76acbbe1b326939a61e7c1c931aa6899eb57407ccc424730',
    'verification/swift-semantic-adapter-root-review/profile-adapter-acceptance.json':
        'ee3ef423db5e404b58ab86c1e1123a81113e542c6af8b691e37f5932b3e42381',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rows_digest(rows):
    return sha(''.join(f"{r['path']}\t{r['bytes']}\t{r['sha256']}\n"
                       for r in rows).encode())


def checked_bytes(base, row, key='path'):
    rel = PurePosixPath(row[key])
    assert not rel.is_absolute() and '..' not in rel.parts
    raw = (base / rel).read_bytes()
    assert len(raw) == row['bytes'], (str(base / rel), 'length')
    assert sha(raw) == row['sha256'], (str(base / rel), 'sha256')
    return raw


def audit():
    # These three trusted exact paths precede any processing of untrusted names.
    bindings = []
    for name, expected in EXPECTED.items():
        raw = (ROOT / name).read_bytes()
        assert sha(raw) == expected, name
        bindings.append({'path': name, 'bytes': len(raw), 'sha256': expected})
    seal = json.loads((PREP / 'seal.json').read_bytes())
    members = seal['members']
    assert len(members) == seal['member_count'] == 200
    assert len({r['path'] for r in members}) == len(members)
    for row in members:
        checked_bytes(PREP, row)
    assert sum(r['bytes'] for r in members) == seal['total_bytes'] == 23038631
    # Producer used sorted(Path.rglob()), i.e. component tuple order. The exact
    # seal hash and every member are sound; make this ordering distinction explicit.
    component_order = sorted(members, key=lambda r: PurePosixPath(r['path']).parts)
    assert members == component_order
    assert rows_digest(members) == seal['tree_sha256']
    lexical_tree = rows_digest(sorted(members, key=lambda r: r['path']))

    nested_count = 0
    for name in ['input-manifest.json', 'additional-inputs.json', 'acceptance-input.json']:
        manifest = json.loads((PREP / name).read_bytes())
        assert len({r['snapshot'] for r in manifest['members']}) == len(manifest['members'])
        for row in manifest['members']:
            checked_bytes(PREP, row, 'snapshot')
            nested_count += 1
        if 'tree_sha256' in manifest:
            assert rows_digest(sorted(manifest['members'], key=lambda r: r['path'])) == manifest['tree_sha256']

    closure = json.loads((PREP / 'closure-comparison.json').read_bytes())
    canonical = closure['canonical_members']
    completion = closure['completion_members']
    row_members = closure['row_source_members']
    assert len(canonical) == len(completion) == 132
    assert len(row_members) == 131
    for rows, key in [(canonical, 'canonical_tree_sha256'),
                      (completion, 'completion_tree_sha256'),
                      (row_members, 'row_source_tree_sha256')]:
        assert len({r['path'] for r in rows}) == len(rows)
        assert rows_digest(sorted(rows, key=lambda r: r['path'])) == closure[key]
    for row in canonical:
        checked_bytes(PREP / 'inputs/vm', row)
    old_root = PREP / 'inputs/verification/swift-ordered-retention-diagnostic-completion'
    old = json.loads((old_root / 'candidate-manifest.json').read_bytes())
    raw_archive = (old_root / 'candidate-source.tar.gz').read_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw_archive), mode='r:gz') as archive:
        # Read as data; never extract paths, import or execute archived code.
        files = [m for m in archive.getmembers() if m.isfile()]
        assert len(files) == 132
        assert len({m.name for m in files}) == 132
        assert set(old) == {m.name for m in files} == {r['path'] for r in completion}
        lookup = {r['path']: r for r in completion}
        for member in files:
            raw = archive.extractfile(member).read()
            r = lookup[member.name]
            assert sha(raw) == old[member.name] == r['sha256']
            assert len(raw) == r['bytes']

    # Reconstruct the row source identity using its copied changed/new inputs
    # plus byte-identical frozen canonical members, without visiting its active lane.
    row_root = PREP / 'inputs/verification/swift-cache-state-profile-adapter/source/vm'
    base = {r['path']: r for r in canonical}
    row_seal = json.loads((PREP / 'inputs/verification/swift-cache-state-profile-adapter/seal.json').read_bytes())
    row_sealed = {r['path'][len('source/vm/'):]: r for r in row_seal['members']
                  if r['path'].startswith('source/vm/')}
    assert set(row_sealed) == {r['path'] for r in row_members}
    for r in row_members:
        assert (r['sha256'], r['bytes']) == (row_sealed[r['path']]['sha256'], row_sealed[r['path']]['bytes'])
        if r['path'] in base and r['sha256'] == base[r['path']]['sha256']:
            checked_bytes(PREP / 'inputs/vm', r)
        else:
            checked_bytes(row_root, r)
    comparison = []
    orig = {r['path']: r for r in completion}
    candidate = {r['path']: r for r in row_members}
    for path, r in sorted(base.items()):
        q = candidate.get(path)
        comparison.append({
            'path': path,
            'completion_sha256': orig[path]['sha256'],
            'canonical_sha256': r['sha256'],
            'row_candidate_sha256': None if q is None else q['sha256'],
            'completion_equal_canonical': orig[path]['sha256'] == r['sha256'],
            'row_equal_canonical': None if q is None else q['sha256'] == r['sha256'],
        })
    assert comparison == closure['comparisons']
    assert [r['path'] for r in comparison if not r['completion_equal_canonical']] == closure['completion_changed']
    assert closure['completion_changed'] == [
        'src/experimental/cache/borrowed.rs', 'src/experimental_swift_reactor/cache.rs',
        'src/experimental_swift_reactor/cache_tests.rs', 'src/experimental_swift_reactor/control.rs']
    assert [r['path'] for r in comparison if r['row_equal_canonical'] is False] == closure['row_changed']
    assert [r['path'] for r in comparison if r['row_equal_canonical'] is None] == closure['row_missing']
    assert sorted(set(candidate) - set(base)) == closure['row_added']

    custody = json.loads((ROOT / bindings[1]['path']).read_bytes())
    assert custody['seal_sha256'] == bindings[0]['sha256']
    assert custody['members_verified'] == 200 and custody['bytes_verified'] == 23038631
    return {
        'schema': 1, 'scope': 'Exact offline source/data custody only; no code import/compile/runtime or authority',
        'trusted_bindings': bindings, 'producer_member_count': 200,
        'producer_total_bytes': 23038631, 'nested_snapshots_verified': nested_count,
        'producer_tree_sha256': seal['tree_sha256'],
        'producer_tree_order': 'sorted POSIX path component tuples, identical to listed member order',
        'plain_relative_string_lexical_tree_sha256': lexical_tree,
        'plain_relative_string_lexical_order_equals_producer_order': lexical_tree == seal['tree_sha256'],
        'archive_members_read_as_data_only': 132, 'canonical_snapshot_members': 132,
        'row_source_members_reconstructed': 131,
        'canonical_tree_sha256': closure['canonical_tree_sha256'],
        'completion_tree_sha256': closure['completion_tree_sha256'],
        'row_tree_sha256': closure['row_source_tree_sha256'],
        'completion_deltas': closure['completion_changed'],
        'row_delta': closure['row_changed'], 'row_additions': closure['row_added'],
        'row_omitted_C_headers': closure['row_missing'],
        'canonical_sources_or_active_other_lanes_accessed_by_audit': False,
        'producer_members': members,
    }


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
