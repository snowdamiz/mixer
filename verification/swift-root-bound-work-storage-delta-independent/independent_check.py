#!/usr/bin/env python3
"""Independent finite offline custody/coverage reconstruction; no producer imports.

Reads complete authoritative MIR streams. MIR is compiler evidence, not an
instruction price decoder. No compiler, native runtime, network or subprocess.
"""
from pathlib import Path
from collections import Counter
import copy
import datetime
import gzip
import hashlib
import json
import re
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / 'verification/swift-root-bound-work-storage-delta'
CAND = ROOT / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation'
BASE = ROOT / 'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
ACCEPT = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-acceptance.json'
LOADER = 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
CACHE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
CHILD = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
TYPE_NAMES = {
    'AdmittedLoaderCorrespondenceV1', 'PrepaidCorrelationAttemptV1', 'RootBoundV1',
    'RawSelectedBundleV1', 'CorrelatedSelectedProfileV1', 'RootBoundSelectedProfileV1',
    'OriginalCorrelationRefusalV1', 'RawCorrelationOutcomeV1', 'OwnedCorrelationOutcomeV1',
    'FixtureLeafArgumentsV1', 'RawFixturePrimaryV1', 'RawFixtureResultV1',
    'RootBoundFixtureOutcomeV1', 'RootBoundPrimaryBorrowV1',
    'AdmittedFixtureOutcomeV1', 'AdmittedFixturePayloadV1',
}
FUNCTION_NAMES = [
    'original_root_v1', 'correlation_scope_core_v1', 'correlation_scope_v1',
    'into_result_v1', 'split_pair_v1', 'into_selected_v1', 'primary_v1', 'usage_v1',
    'run_fixture_once_v1', 'correlate_core_v1', 'correlate_admitted_loader_v1',
    'run_one_admitted_fixture_v1', 'run_one_admitted_fixture_v1::{closure#0}',
    'run_prepaid_admitted_fixture_v1', 'destroy_returned_admitted_fixture_v1',
    'observe_admitted_originals_v1', 'consume_admitted_owner_once_v1',
    'dispatch_v1', 'inspect_v1', 'destroy_owned_v1', 'drop(_1: &mut PrepaidOwnedV1',
    'release_destroyed_v1', 'release_after_retirement_v1', 'invoke_loaded_leaf_once_v1',
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(p):
    return json.loads(p.read_text())


def ref(p):
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': sha(b)}


def canonical(rows):
    return sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


def assert_member(directory, row):
    p = directory / row['path']
    assert not p.is_symlink() and p.is_file(), ('not-regular-member', str(p))
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
    got = ref(p)
    assert all(got[k] == row[k] for k in ['bytes', 'sha256']), ('member', str(p))


def verify_seal(directory, expected_sha, complete=False):
    seal = directory / 'seal.json'
    assert ref(seal)['sha256'] == expected_sha, ('seal', str(seal))
    d = load(seal)
    rows = d['members']
    assert len(rows) == len({x['path'] for x in rows}) == d['member_count']
    # Producer sorts pathlib paths (component order), which differs from full
    # string order at build/ versus build-2/. Verify the actual committed order
    # and digest without imposing an unpromised alternative sort convention.
    assert rows == sorted(rows, key=lambda x: Path(x['path']))
    if 'tree_sha256' in d:
        assert canonical(rows) == d['tree_sha256']
    # The already-accepted independent packet is sealed by exact seal hash and
    # member list, without an additional tree_sha256 field.
    if complete:
        for row in rows:
            assert_member(directory, row)
        actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
        assert actual == {'seal.json', *(x['path'] for x in rows)}, ('membership-closure', str(directory))
    return d


def source_tree(directory, seal, tree):
    manifest = load(directory / 'source-manifest.json')
    assert manifest['member_count'] == len(manifest['members']) == 146
    assert canonical(manifest['members']) == manifest['tree_sha256'] == tree
    sealed = {x['path']: x for x in seal['members']}
    assert_member(directory, sealed['source-manifest.json'])
    for row in manifest['members']:
        assert_member(directory / 'source/vm', row)
        sr = sealed['source/vm/' + row['path']]
        assert all(sr[k] == row[k] for k in ['bytes', 'sha256'])
    return {x['path']: x for x in manifest['members']}


def relevant(header):
    return any(re.search(r'(?<![A-Za-z0-9_])' + re.escape(n) + r'(?![A-Za-z0-9_])', header) for n in TYPE_NAMES)


def wanted(header):
    names = [*FUNCTION_NAMES, 'destroy_returned_fixture_v1', 'run_one_loaded_fixture_v1']
    return relevant(header) or any(('fn ' + n + '(' in header or '::' + n + '(' in header) for n in names) or '>::drop(_1: &mut PrepaidOwnedV1' in header


def stream(directory, archive_path, wanted_fn):
    digest = hashlib.sha256()
    records = []
    total = line_no = 0
    active = None
    trailer_target = None
    with gzip.open(directory / archive_path, 'rb') as f:
        for raw in f:
            digest.update(raw)
            start = total
            total += len(raw)
            line_no += 1
            assert total <= 90_000_000
            if raw.startswith(b'fn '):
                assert active is None, 'unterminated-finite-MIR-function'
                trailer_target = None
                header = raw.decode().strip()
                if wanted_fn(header):
                    active = {'header': header, 'line_start': line_no, 'byte_start': start, 'lines': [raw]}
            elif active is not None:
                active['lines'].append(raw)
                if raw == b'}\n':
                    b = b''.join(active.pop('lines'))
                    active.update({'line_end': line_no, 'byte_end_exclusive': total, 'body': b, 'trailer': b'', 'sha256_body_without_blank': sha(b)})
                    records.append(active)
                    trailer_target = active
                    active = None
            elif trailer_target is not None:
                if not raw.strip() or raw.lstrip().startswith(b'//'):
                    trailer_target['trailer'] += raw
                else:
                    trailer_target = None
    assert active is None
    return records, {'uncompressed_bytes': total, 'uncompressed_sha256': digest.hexdigest(), 'functions_retained': len(records)}


def explicit(raw):
    s = raw.decode().strip().split('//', 1)[0].strip()
    return bool(s and s not in ['{', '}'] and not s.startswith('scope '))


def signature_args(header):
    text = header.split('(', 1)[1].rsplit(') -> ', 1)[0]
    # Split only MIR argument place introducers. Embedded tuple/generic commas
    # cannot be confused with an argument `_N:` declaration.
    return re.findall(r'(?:^|, )(_\d+): (.*?)(?=, _\d+: |$)', text)


def audit_rows(entries, parsed):
    for f in entries:
        it = f['MIR']
        matches = [x for x in parsed if x['byte_start'] == it['byte_start']]
        assert len(matches) == 1
        m = matches[0]
        assert m['header'] == it['header'] and m['line_start'] == it['line_start']
        # Complete item spans include the following blank line and, on the
        # first constructor occurrence, the `// MIR FOR CTFE` separator.
        exact = m['body'] + m['trailer']
        assert sha(exact) == it['sha256'] and len(exact) == it['bytes'], ('complete-item-trailer', f['selector'])
        expected = [(m['line_start'] + i, sha(raw)) for i, raw in enumerate(m['body'].splitlines(keepends=True)) if explicit(raw)]
        assert expected == [(r['line'], r['sha256']) for r in f['rows']], ('explicit-MIR-row-omission', f['selector'])
        args = signature_args(m['header'])
        assert args == [(a['place'], a['storage_role']['type_spelling']) for a in f['argument_places']], ('argument-omission', f['selector'])
        declarations = []
        for raw in m['body'].splitlines():
            mm = re.match(rb'\s*let (?:mut )?(_\d+): (.*?);(?:\s*//.*)?$', raw)
            if mm:
                declarations.append((mm[1].decode(), mm[2].decode()))
        got = [(r['place'], r['storage_role']['type_spelling']) for r in f['rows'] if r['kind'] in ['local_place', 'return_place']]
        assert got == declarations, ('local-return-omission', f['selector'])


def semantic_lines(body):
    return [s for raw in body.decode().splitlines() if (s := raw.strip().split('//', 1)[0].strip())]


def coverage(d, parsed, baseline):
    entries = d['functions_and_constructor_occurrences']
    assert {f['selector'] for f in entries if not f['selector'].startswith('constructor:')} == set(FUNCTION_NAMES)
    assert {x['name'] for x in d['types']} == TYPE_NAMES
    assert len(d['types']) == len(TYPE_NAMES)
    audit_rows(entries, parsed)
    represented = {f['MIR']['byte_start'] for f in entries}
    missed = [m for m in parsed if relevant(m['header']) and m['byte_start'] not in represented]
    # OriginalCorrelationRefusal is explicitly unchanged-fields/relocated. The
    # untouched unadmitted PrimaryOutcome constructor mentions that type, but
    # gains no root field and is outside the admitted-family delta. Require its
    # complete non-comment MIR to match the baseline before excluding it.
    for m in missed:
        assert m['header'].startswith('fn PrimaryOutcomeV1::CorrelationRefused('), ('unexpected-unmapped-new-type', m['header'])
        old = [o for o in baseline if o['header'] == m['header']]
        assert old and all(semantic_lines(o['body']) == semantic_lines(m['body']) for o in old)
    missed = [m for m in missed if not m['header'].startswith('fn PrimaryOutcomeV1::CorrelationRefused(')]
    assert not missed, ('meaningful-new-type-MIR-omission', [x['header'] for x in missed])
    assert d['relocation']['no_duplicate_leaf_invocation_inferred'] is True
    assert not any(d['claim_limits'][k] for k in ['layout_or_price_accepted', 'total_funding_accepted', 'full_ownership_or_forgotten_root_funding_accepted', 'OTA_FieldLog_GA_or_native_accepted'])
    assert all(x['price'] == x['layout_or_backing_bound'] == 'UNRESOLVED' for x in d['obligations'])


def main():
    acceptance = load(ACCEPT)
    oracle = load(HERE / 'pre-producer-oracle.json')
    assert ref(ACCEPT) == oracle['acceptance']
    target = verify_seal(TARGET, '1b077039023f424fb72f9e32902f329e3257edb50a4ab99aa42192149271cb29', True)
    assert target['member_count'] == 25 and sum(x['bytes'] for x in target['members']) == 2803947
    assert target['tree_sha256'] == 'a3c169fad11ddff8b3cba126f52528c5a9b319819a121d553eda667d79ec9a07'
    accepted_packets = []
    for packet in acceptance['packets']:
        directory = ROOT / packet['directory']
        sealed = verify_seal(directory, packet['seal']['sha256'], True)
        assert len(sealed['members']) == packet['members_verified']
        assert sum(m['bytes'] for m in sealed['members']) == packet['member_bytes']
        accepted_packets.append({'directory': packet['directory'], 'members': len(sealed['members']), 'bytes': packet['member_bytes']})
    cs = load(CAND / 'seal.json')
    origin = load(CAND / 'source-origin.json')
    bs = verify_seal(BASE, origin['base_seal']['sha256'])
    cm = source_tree(CAND, cs, acceptance['source146_tree'])
    bm = source_tree(BASE, bs, 'c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db')
    assert set(cm) == set(bm)
    assert sorted(x for x in cm if cm[x] != bm[x]) == sorted([LOADER, CACHE])
    d = load(TARGET / 'delta-inventory.json')
    for path, pin in d['inputs'].items():
        assert all(ref(ROOT / path)[k] == pin[k] for k in ['bytes', 'sha256'])
    candidate, cand_receipt = stream(CAND, 'mir/complete-production.mir.gz', wanted)
    baseline_archive = d['MIR_custody']['baseline']['archive']['path']
    baseline, base_receipt = stream(BASE, baseline_archive, wanted)
    for name, receipt in [('candidate', cand_receipt), ('baseline', base_receipt)]:
        pin = d['MIR_custody'][name]['uncompressed']
        assert receipt['uncompressed_bytes'] == pin['bytes'] and receipt['uncompressed_sha256'] == pin['sha256']
    coverage(d, candidate, baseline)
    for f in d['functions_and_constructor_occurrences']:
        if 'baseline_MIR' in f:
            old = f['baseline_MIR']
            matches = [m for m in baseline if m['line_start'] == old['first_line'] and m['header'] == old['header']]
            assert len(matches) == 1, ('baseline-selector-not-retained', f['selector'], old['header'])
            assert len(matches[0]['body']) == old['bytes'] and sha(matches[0]['body']) == old['sha256']
    # Source spans and explicit field declarations are independently read and
    # compared; copied labels alone do not establish these shapes.
    for item in [*d['types'], *d['functions_and_constructor_occurrences']]:
        s = item['source']
        b = b''.join((ROOT / s['path']).read_bytes().splitlines(keepends=True)[s['first_line'] - 1:s['last_line']])
        assert len(b) == s['bytes'] and sha(b) == s['sha256']
    closure = next(m for m in candidate if m['header'].startswith('fn run_one_admitted_fixture_v1::{closure#0}('))
    captures = [x.strip() for x in closure['body'].decode().splitlines() if x.lstrip().startswith('debug ')]
    assert len(captures) == 3
    assert all(('debug ' + n + ' =>') in x and ('(_1.' + str(i) + ':') in x for i, (n, x) in enumerate(zip(['fixture', 'attempt', 'expected'], captures)))
    assert re.search(r'\(_1\.2: &[A-Za-z0-9_:]*AdmittedLoaderCorrespondenceV1', captures[2])
    def find(records, name):
        return next(m['body'].decode() for m in records if m['header'].startswith('fn ' + name + '(') or ('::' + name + '(' in m['header']))
    leaf_calls = ['into_snapshot_scope_v1(', 'construct_v1(', 'outer_v1(', 'finish_v1(']
    new_leaf = find(candidate, 'run_fixture_once_v1')
    new_caller = find(candidate, 'run_prepaid_admitted_fixture_v1')
    old_caller = find(baseline, 'run_prepaid_admitted_fixture_v1')
    old_helper = find(baseline, 'invoke_loaded_leaf_once_v1')
    old_leaf = find(baseline, 'run_one_loaded_fixture_v1')
    # MIR fully-qualified generic calls have `::<...>(` as well as `(`.
    call_count = lambda b, n: len(re.findall(re.escape(n) + r'(?:::<[^\n]*?>)?\(', '\n'.join(semantic_lines(b.encode()))))
    counts = lambda b: {n[:-1]: call_count(b, n[:-1]) for n in leaf_calls}
    assert counts(new_leaf) == {n[:-1]: 1 for n in leaf_calls}
    assert counts(new_caller) == {n[:-1]: 0 for n in leaf_calls}
    assert counts(old_helper) == {n[:-1]: 0 for n in leaf_calls}
    assert counts(old_leaf) == counts(new_leaf)
    # The old helper delegates the four-call sequence through run_one_loaded.
    assert call_count(old_helper, 'run_one_loaded_fixture_v1') == 1
    assert call_count(old_caller, 'invoke_loaded_leaf_once_v1') == 1
    assert call_count(new_caller, 'run_fixture_once_v1') == 1
    for name, rows in [('candidate', candidate), ('baseline', baseline)]:
        out = HERE / (name + '-selected-complete.mir')
        out.write_bytes(b'\n'.join(m['body'] for m in rows))
    negatives = []
    mutations = [
        ('omit-original-root-accessor', lambda x: x['functions_and_constructor_occurrences'].pop(0)),
        ('omit-final-result-type', lambda x: x['types'].__setitem__(slice(None), [t for t in x['types'] if t['name'] != 'RawFixtureResultV1'])),
        ('omit-owned-input-argument', lambda x: next(f for f in x['functions_and_constructor_occurrences'] if f['selector'] == 'run_fixture_once_v1')['argument_places'].pop()),
        ('omit-retirement-unwind-row', lambda x: next(f for f in x['functions_and_constructor_occurrences'] if f['selector'] == 'destroy_owned_v1')['rows'].__setitem__(slice(None), [r for r in next(f for f in x['functions_and_constructor_occurrences'] if f['selector'] == 'destroy_owned_v1')['rows'] if 'unwind' not in r['kind']])),
        ('duplicate-leaf-inference', lambda x: x['relocation'].__setitem__('no_duplicate_leaf_invocation_inferred', False)),
        ('invent-work-price-zero', lambda x: x['obligations'][0].__setitem__('price', 0)),
        ('invent-layout-price', lambda x: x['claim_limits'].__setitem__('layout_or_price_accepted', True)),
        ('invent-whole-funding', lambda x: x['claim_limits'].__setitem__('total_funding_accepted', True)),
    ]
    for label, mutation in mutations:
        altered = copy.deepcopy(d)
        mutation(altered)
        try:
            coverage(altered, candidate, baseline)
        except AssertionError:
            negatives.append({'control': label, 'rejected': True})
        else:
            raise AssertionError(('independent-control-accepted', label))
    report = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': sys.version,
              'status': 'PASS_INDEPENDENT_FINITE_CUSTODY_AND_COVERAGE',
              'accepted_packets_fully_verified': accepted_packets,
              'target_seal': ref(TARGET / 'seal.json'), 'target_members': 25, 'target_member_bytes': 2803947,
              'source_trees_fully_read': {'candidate': acceptance['source146_tree'], 'baseline': 'c3a33b76eef6bf9ad86ef1cb0320e94bcefa5a0609ec1a30872a9d83371bd0db', 'members_each': 146},
              'complete_MIR': {'candidate': cand_receipt, 'baseline': base_receipt},
              'all_new_type_MIR_headers_mapped': True, 'explicit_unadmitted_unchanged_constructor_exclusions': 2,
              'all_selected_argument_local_return_and_explicit_rows_independently_reconstructed': True,
              'counts': d['counts'], 'captures': captures,
              'leaf_call_counts_new_fixed_frame': counts(new_leaf), 'leaf_call_counts_new_caller': counts(new_caller),
              'independent_controls': negatives, 'GA_accepted': False,
              'scope_limit': 'MIR/source/accounting inventory only. Work prices, layouts, dynamic backing, simultaneous peak, funding, durable forgotten root/result funding, useful joint retirement and full ownership remain unresolved.'}
    (HERE / 'independent-check-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
