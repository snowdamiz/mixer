#!/usr/bin/env python3
"""One-shot independent oracle. Does not read the new producer lane or spawn tools."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-root-bound-work-storage-delta'
SOURCE = ROOT / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm'
FUTURE = ROOT / 'verification/swift-root-bound-work-storage-layout-probe'
TREE = '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def record(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': digest(data)}


def write(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def location(text, token, start=0):
    offset = text.index(token, start)
    before = text[:offset]
    line = before.count('\n') + 1
    column = len(before.rsplit('\n', 1)[-1]) + 1
    return {'byte_start': len(before.encode()), 'byte_end': len((before + token).encode()),
            'line_start': line, 'line_end': line + token.count('\n'),
            'column_start': column, 'column_end': column + len(token), 'text': token}


def main():
    assert not (HERE / 'preaccess-oracle.json').exists(), 'Do not rewrite frozen oracle'
    accepted = ROOT / 'verification/swift-semantic-adapter-root-review/root-bound-work-storage-delta-acceptance.json'
    acceptance = json.loads(accepted.read_bytes())
    assert acceptance['candidate_source146_tree'] == TREE
    assert acceptance['conditional_layout_frontier'] == {
        'named_shapes': 28, 'actual_anonymous_closure': True,
        'diagnostic_strategy_qualified': False, 'compiler_released': False, 'compiler_executed': False}
    custody = []
    for lane, expected in [
        ('swift-root-bound-work-storage-delta', '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29'),
        ('swift-root-bound-work-storage-delta-independent', 'addd2beb80ae25174c210563bffc9122cbe655f69420170ad16305eaeef544ec')]:
        base = ROOT / 'verification' / lane
        seal = json.loads((base / 'seal.json').read_bytes())
        assert record(base / 'seal.json')['sha256'] == expected
        rows = []
        for member in seal['members']:
            row = record(base / member['path'])
            assert {k: row[k] for k in ('bytes', 'sha256')} == {k: member[k] for k in ('bytes', 'sha256')}
            rows.append(member)
        assert len(rows) == seal['member_count']
        assert sum(r['bytes'] for r in rows) == seal['member_bytes']
        assert digest(canonical(rows)) == seal['tree_sha256']
        assert sorted(p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()) == sorted([r['path'] for r in rows] + ['seal.json'])
        custody.append({'seal': record(base / 'seal.json'), 'verified_members': len(rows), 'tree_sha256': seal['tree_sha256']})
    manifest_path = SOURCE.parent.parent / 'source-manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest['tree_sha256'] == TREE and len(manifest['members']) == manifest['member_count'] == 146
    contents = {}
    original_rows = []
    for row in manifest['members']:
        data = (SOURCE / row['path']).read_bytes()
        assert {'path': row['path'], 'bytes': len(data), 'sha256': digest(data)} == row
        original_rows.append(row)
        contents[row['path']] = data
    assert digest(canonical(original_rows)) == TREE
    assert sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()) == sorted(r['path'] for r in original_rows)
    proposal_path = OLD / 'layout-probe-proposal.json'
    proposal = json.loads(proposal_path.read_bytes())
    assert proposal['source_tree'] == TREE and proposal['named_expected_E0308'] == 56
    fragments = {}
    for row in proposal['fragments']:
        path = ROOT / row['path']
        assert record(path) == row
        fragments[path.name] = path.read_text()
    owner_rel = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    cache_rel = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
    owner = contents[owner_rel].decode()
    cache = contents[cache_rel].decode()
    owner_marker = '    // OWNER_PROBE_INSERTION'
    cache_marker = '    // Private outer caller candidate; all prior bodies remain exact.'
    original = '        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))'
    assert owner.count(owner_marker) == cache.count(cache_marker) == cache.count(original) == 1
    staged = {
        owner_rel: owner.replace(owner_marker, fragments['proposed-owner-layout-queries.inc.rs'] + '\n' + owner_marker),
        cache_rel: cache.replace(cache_marker, fragments['proposed-cache-layout-queries.inc.rs'] + '\n' + cache_marker).replace(original, fragments['proposed-actual-closure-layout-fragment.rs'].rstrip())}
    changed_rows = []
    for row in original_rows:
        data = staged[row['path']].encode() if row['path'] in staged else contents[row['path']]
        changed_rows.append({'path': row['path'], 'bytes': len(data), 'sha256': digest(data)})
    assert [a['path'] for a, b in zip(changed_rows, original_rows) if a != b] == [cache_rel, owner_rel]
    named = []
    for rel, fragment in [(owner_rel, 'proposed-owner-layout-queries.inc.rs'), (cache_rel, 'proposed-cache-layout-queries.inc.rs')]:
        text = staged[rel]
        declaration = location(text, 'macro_rules! pair')
        for row in proposal['named_queries']:
            if row['fragment'] != fragment:
                continue
            invocation = 'pair!(' + row['type'] + ')'
            assert text.count(invocation) == 1
            for op in ('size', 'align'):
                rhs = '[0u8; std::mem::' + op + '_of::<$type>()]'
                named.append({'id': len(named), 'type': row['type'], 'operation': op,
                              'file': str(FUTURE / 'source/vm' / rel),
                              'query_rhs': location(text, rhs),
                              'macro_definition': declaration,
                              'invocation': location(text, invocation)})
    assert len(named) == 56 and len({r['type'] for r in named}) == 28
    cache = staged[cache_rel]
    closure = location(cache, '|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)')
    closure['identity_end_line'] = closure['line_start']
    closure['identity_end_column'] = closure['column_start'] + 2
    closure_queries = [
        {'operation': 'size', 'expression': location(cache, 'std::mem::transmute(uninitialized_shape_v1(&action))')},
        {'operation': 'alignment', 'expression': location(cache, 'std::mem::transmute(ClosureAlignmentProbeV1 {\n                leading: 0u8, actual: uninitialized_shape_v1(&action),\n            })')}]
    bindings = {'schema': 1, 'status': 'preaccess-in-memory-source-reconstruction-only',
                'original_source146_tree': TREE, 'diagnostic_source146_tree': digest(canonical(changed_rows)),
                'source_manifest': changed_rows, 'named_queries': named,
                'closure_file': str(FUTURE / 'source/vm' / cache_rel),
                'actual_closure': closure, 'closure_queries': closure_queries,
                'staged_two_sources': {str(FUTURE / 'source/vm' / rel): text for rel, text in staged.items()}}
    write('diagnostic-bindings.json', bindings)
    oracle = {
        'schema': 1, 'frozen_at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_BEFORE_NEW_PRODUCER_PACKET_ACCESS', 'python': sys.version,
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
        'freeze_script': record(Path(__file__)), 'root_acceptance': record(accepted),
        'accepted_packet_custody': custody, 'accepted_proposal': record(proposal_path),
        'original_source_manifest': record(manifest_path), 'original_source146_tree': TREE,
        'diagnostic_bindings': record(HERE / 'diagnostic-bindings.json'),
        'diagnostic_source146_tree': bindings['diagnostic_source146_tree'],
        'source_edits': ['insert exact owner fragment once before owner marker',
                         'insert exact cache fragment once before outer caller marker',
                         'replace exactly the one actual admitted dispatch expression with exact closure fragment'],
        'cardinality': {'named_primary_E0308': 56, 'actual_closure_primary_E0512': 2,
                        'unique_named_shapes': 28, 'other_primary_errors': 0},
        'diagnostic_identity': [
            'Each E0308 must have exactly one primary span, bound to the exact size/align macro RHS and exact same-file pair invocation expansion. Source bytes, lines, columns, excerpts and labels must agree. One observation per type/operation.',
            'Each E0512 must have exactly one primary span at the exact size or leading-u8 repr(C) transmute source expression. Source and target notes must be unique and concrete.',
            'Size source is MaybeUninit of the exact actual closure at frozen path/line/closure-token columns; wrapper source is ClosureAlignmentProbeV1<MaybeUninit<the exact same closure>>. Target is exactly zero-sized [u8; 0]. No alternate closure, capture proxy, capture-field sum or arbitrary type-name suffix match.',
            'All JSON records and unexpected diagnostics are retained. Missing, duplicate, ambiguous, dependently sized, malformed, wrong-code or unexplained extra diagnostics refuse the observation. Unexpected secondary labels alone never substitute for actual primary identity.'
        ],
        'arithmetic': {'S': 'concrete actual closure bit size', 'P': 'concrete repr(C) wrapper bit size',
                       'required': ['S>0', 'P>0', 'S%8==0', 'P%8==0', 'A=(P-S)/8>0', 'A is power of two', '(S/8)%A==0'],
                       'allowed_result': 'closure byte size=S/8, alignment=A only if exact diagnostic identity and all constraints pass'},
        'execution_contract': {'argv': proposal['argv'], 'cwd': proposal['cwd'],
                               'environment': proposal['environment'], 'compiler': proposal['future_compiler'],
                               'bounds': proposal['bounds'], 'expected_exit': 1,
                               'root_release_required': True, 'automatic_retry': False,
                               'cleanup': 'Capture/hash outputs; stop/wait/reap only owned compiler child; hash/remove any owned metadata/temp outputs after custody; never global process inventory.'},
        'strategy_qualified': False, 'new_producer_lane_accessed': False,
        'compiler_or_runtime_executed': False, 'diagnostic_source_files_written': False,
        'not_accepted': ['numerical work/storage prices', 'full layouts', 'dynamic backing capacities',
                         'simultaneous peak/lifetime composition', 'funding sufficiency',
                         'durable forgotten-result/root funding', 'useful joint retirement/full ownership',
                         'native/UI/capture/phone/runtime behavior', 'FieldLog external release', 'OTA/GA'],
        'limits': 'Finite diagnostic/parser controls only; source syntax is never OTA release authority.'}
    write('preaccess-oracle.json', oracle)
    print(json.dumps({'status': oracle['status'], 'oracle': record(HERE / 'preaccess-oracle.json'),
                      'verified_original_source_members': 146, 'accepted_packet_members_verified': 66,
                      'diagnostic_source146_tree': bindings['diagnostic_source146_tree'],
                      'new_producer_lane_accessed': False, 'compiler_or_runtime_executed': False}))


if __name__ == '__main__':
    main()
