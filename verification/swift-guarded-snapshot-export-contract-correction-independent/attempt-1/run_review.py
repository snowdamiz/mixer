#!/usr/bin/env python3
"""Bounded independent data review. Never invokes frozen run/freeze wrappers."""
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import unittest

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]
C = REPO / 'verification/swift-guarded-snapshot-export-contract-correction'
P = REPO / 'verification/swift-guarded-snapshot-export-preparation'
I = REPO / 'verification/swift-guarded-snapshot-export-contract-independent'
OUT = OWN / 'controls'
ROOT = REPO / 'verification/swift-semantic-adapter-root-review'
PACKETS = [
    (C, 'e1e5fd13eb421131e8b610ec2cdca7a494cc9f6d3554a48764d37984a9082667', 165),
    (P, '7787c8bbd9164ebdd360186f79c5d696739e89d6b08cd2f7cfbc71e9c156a1fe', 639),
    (I, 'be091218c0c8c47f66c83ac39cded51012c942e7e91d9660b1b25985243401e1', 767),
    (REPO / 'verification/swift-guarded-snapshot-export-accounting-review', 'c638a996d2fa1f54c62f739758c5219f23439541b249e480b0084d1038112068', 29),
    (REPO / 'verification/swift-guarded-snapshot-export-binding-review', '7d3faabd2f930d2daac9865f27dbbb3bc9a661097e6a7834584a93d0527b1cf0', 6),
]
ROOT_INPUTS = {
    'guarded-snapshot-export-correction-independent-release.json': 'a49dd6e8d6d416dab26c0a4f9623b24884660045c68ff6d810ad6a2e0aa75d58',
    'guarded-snapshot-export-correction-selection.json': '9365220136da4af59d1403cf694f3c8108c4f601647c3fe7bf1b4385aff37511',
    'guarded-snapshot-export-positive-fixture-amendment.json': '327db1241e13af8b0c68b0c795c1dcba2c8692c9da5bd7dc100b013025c11457',
    'guarded-snapshot-export-fixture-inventory-amendment.json': '76a2a3c91c46f401d04bfd51f830b50374c24b0d8cbbd4f5d91b48ab15eda518',
}
FIVE = ['bad-memory-minimum-duplicate', 'bad-memory-host-duplicate',
        'bad-table-minimum-duplicate', 'bad-table-max-option-duplicate',
        'bad-runtime-type-count-duplicate']

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def ref(p):
    return {'path': p.relative_to(REPO).as_posix(), 'bytes': p.stat().st_size,
            'sha256': sha(p.read_bytes())}

def compact(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':')).encode()

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def custody():
    packets = []
    for folder, digest, count in PACKETS:
        seal_path = folder / 'seal.json'
        assert sha(seal_path.read_bytes()) == digest, folder
        s = json.loads(seal_path.read_text())
        assert s['member_count'] == count == len(s['members'])
        expected = sorted(r['path'] for r in s['members'])
        assert len(set(expected)) == count
        actual = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*')
                        if p.is_file() and p != seal_path)
        assert expected == actual, folder
        for r in s['members']:
            path = folder / r['path']
            assert not path.is_symlink() and path.resolve().is_relative_to(folder.resolve())
            assert path.stat().st_size == r['bytes'] and sha(path.read_bytes()) == r['sha256'], path
        assert sum(r['bytes'] for r in s['members']) == s['bytes']
        algorithm = s.get('tree_digest_algorithm')
        if algorithm is None:
            tree = sha(compact(s['members']))
        else:
            assert algorithm == 'sha256 of sorted per-member lines: sha256 SPACE decimal-bytes SPACE relative-path LF'
            assert s['members'] == sorted(s['members'], key=lambda r: r['path'])
            tree = sha(''.join(r['sha256'] + ' ' + str(r['bytes']) + ' ' + r['path'] + '\n' for r in s['members']).encode())
        assert tree == s['tree_sha256']
        packets.append({'seal': ref(seal_path), 'members': count, 'bytes': s['bytes'],
                        'tree_sha256': tree, 'all_members_verified': True})
    root_inputs = []
    for name, digest in ROOT_INPUTS.items():
        p = ROOT / name
        assert sha(p.read_bytes()) == digest
        root_inputs.append(ref(p))
    source_root = P / 'inputs/accepted-source/vm'
    manifest_path = P / 'inputs/source-manifest.json'
    m = json.loads(manifest_path.read_text())
    assert m['member_count'] == len(m['members']) == 144
    assert sorted(p.relative_to(source_root).as_posix() for p in source_root.rglob('*') if p.is_file()) == sorted(r['path'] for r in m['members'])
    for r in m['members']:
        p = source_root / r['path']
        assert p.stat().st_size == r['bytes'] and sha(p.read_bytes()) == r['sha256']
    assert sha(compact(m['members'])) == m['tree_sha256'] == '9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
    return {'packets': packets, 'root_inputs': root_inputs,
            'accepted_source': {'manifest': ref(manifest_path), 'members': 144,
                                'tree_sha256': m['tree_sha256'], 'all_members_verified': True}}

def outcome(model, data):
    try:
        model.parse(data)
        return {'accepted': True, 'refusal': None}
    except model.Refused as error:
        return {'accepted': False, 'refusal': str(error)}

def word(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]

def changed(base, pairs):
    b = bytearray(base)
    for offset, value in pairs:
        struct.pack_into('<Q', b, offset, value)
    return bytes(b)

def methods(model):
    sys.modules['format_model'] = model
    suite_module = load('retained_correction_tests', C / 'test_format_model.py')
    names = unittest.defaultTestLoader.getTestCaseNames(suite_module.FormatPreparation)
    assert len(names) == 12
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(suite_module.FormatPreparation))
    (OUT / 'producer-methods.txt').write_text(stream.getvalue())
    value = {'method_names': names, 'methods': result.testsRun,
             'failures': len(result.failures), 'errors': len(result.errors),
             'skipped': len(result.skipped), 'expectation_met': result.wasSuccessful(),
             'source': ref(C / 'test_format_model.py'), 'model': ref(C / 'format_model.py')}
    write(OUT / 'producer-methods.json', value)
    return value

def historical_failures(model, old, independent):
    rows = []
    original_groups = json.loads((I / 'controls-result.json').read_text())['groups']
    historical = {c['name']: c for g in original_groups for c in g['subcases']}
    for name in FIVE:
        before = I / 'controls/fixtures' / (name + '.bin')
        fresh = OUT / 'retained-format/fixtures' / (name + '.bin')
        assert before.read_bytes() == fresh.read_bytes()
        assert historical[name]['candidate_accepted'] and not historical[name]['expectation_met']
        original = outcome(old, before.read_bytes())
        corrected = outcome(model, before.read_bytes())
        rows.append({'name': name, 'original_fixture': ref(before), 'fresh_fixture': ref(fresh),
                     'original_model': original, 'corrected_model': corrected,
                     'original_failure_preserved': True,
                     'expectation_met': original['accepted'] and not corrected['accepted']})
    write(OUT / 'exact-five-regressions.json', {'count': len(rows), 'fixtures': rows})
    return rows

def migration(model, old):
    before = old.assemble_unverified_fixture()
    after = model.assemble_unverified_fixture()
    assert len(before) == len(after) == 4168
    diffs = [(p, word(before, p), word(after, p)) for p in range(0, len(before), 8)
             if before[p:p+8] != after[p:p+8]]
    assert diffs == [(792, 3, 64), (1408, 2, 16777216), (1416, 1, 8388608)]
    d = OUT / 'migration'
    d.mkdir()
    (d / 'unchanged-original-positive.bin').write_bytes(before)
    (d / 'corrected-positive.bin').write_bytes(after)
    assert before == (C / 'controls/migration/original-synthetic-positive.bin').read_bytes()
    assert after == (C / 'controls/migration/migrated-synthetic-positive.bin').read_bytes()
    cases = []
    for p, old_word, new_word in diffs:
        b = changed(after, [(p, old_word)])
        dest = d / ('retained-disagreement-' + str(p) + '.bin')
        dest.write_bytes(b)
        assert b == (C / ('controls/migration/original-disagreement-' + str(p) + '.bin')).read_bytes()
        result = outcome(model, b)
        cases.append({'offset': p, 'original': old_word, 'migrated': new_word,
                      'fixture': ref(dest), **result, 'expectation_met': not result['accepted']})
    test_before = (P / 'test_format_model.py').read_text()
    test_after = (C / 'test_format_model.py').read_text()
    old_assertion = 'self.assertEqual(len(f.DIGESTS),6)'
    assert test_before.count(old_assertion) == 1
    assert test_after == test_before.replace(old_assertion,
        'self.assertEqual(len(f.DIGESTS),5); self.assertEqual(len(f.RETAINED_VALUES),6)')
    assert model.DIGESTS == ['source', 'manifest', 'build', 'session', 'executable']
    assert old.DIGESTS == model.RETAINED_VALUES == model.DIGESTS + ['nonce']
    assert not hasattr(old, 'RETAINED_VALUES')
    value = {'word_changes': cases, 'original_model_original': outcome(old, before),
             'corrected_model_original': outcome(model, before),
             'corrected_model_corrected': outcome(model, after),
             'original_test_unchanged': ref(P / 'test_format_model.py'),
             'corrected_test': ref(C / 'test_format_model.py'),
             'only_test_change': 'One inventory assertion changes 6 digests to 5 digests plus 6 retained values; all 12 methods retained.',
             'digests': model.DIGESTS, 'retained_values': model.RETAINED_VALUES}
    value['expectation_met'] = all(c['expectation_met'] for c in cases) and value['original_model_original']['accepted'] and not value['corrected_model_original']['accepted'] and value['corrected_model_corrected']['accepted']
    write(OUT / 'migration.json', value)
    return value

def source_checks():
    evidence = json.loads((C / 'source-equation-evidence.json').read_text())
    excerpts = []
    for index, r in enumerate(evidence['sources']):
        p = REPO / r['path']
        assert p.resolve().is_relative_to((P / 'inputs/accepted-source/vm').resolve())
        assert sha(p.read_bytes()) == r['sha256']
        assert '\n'.join(p.read_text().splitlines()[r['line_start']-1:r['line_end']]) == r['text']
        excerpts.append({'index': index, 'source': ref(p), 'line_start': r['line_start'],
                         'line_end': r['line_end'], 'role': r['role'], 'exact_excerpt_verified': True})
    assert len(excerpts) == 19
    table = json.loads((C / 'equality-table.json').read_text())
    assert [r['id'] for r in table['equations']] == ['E%02d' % n for n in range(1, 30)]
    for r in table['equations']:
        assert all(0 <= n < 19 for n in r['accepted_source_evidence_indexes'])
    roster = json.loads((C / 'source-roster.json').read_text())
    facts = 0
    for r in roster['sources']:
        p = REPO / r['path']
        assert sha(p.read_bytes()) == r['sha256']
        for f in r['facts']:
            if f['line'] is not None:
                assert f['token'] in p.read_text().splitlines()[f['line']-1]
                facts += 1
    source = P / 'inputs/accepted-source/vm/src'
    cache = (source / 'experimental_swift_reactor/cache.rs').read_text().splitlines()
    wrapper = (source / 'experimental_swift_reactor/cache/initial_profile_v1.rs').read_text().splitlines()
    loader = (source / 'experimental_swift_reactor/retained_profile_loader_v1.rs').read_text().splitlines()
    assert "pub(crate) fn prepare<'a>(" in cache[1472]
    assert 'SwiftFunctionCache::prepare(control,wasi,&adopted,CONSTRUCTION_CURSOR_V1)' in wrapper[136]
    assert 'match preparation.take()' in wrapper[137]
    assert 's.sections[0].bytes != identities[0].encode()' in loader[1044]
    assert 'identity(&files.source, Role::Source)?' in loader[932]
    contract = (C / 'contract.md').read_text()
    assert 'exactly one 64-byte Source File identity' in contract
    assert 'exactly one 64-byte executable identity' not in contract
    result = {'excerpts': excerpts, 'equation_count': 29, 'roster_facts_checked': facts,
              'R2_first_section': 'Source', 'R3_prepare_line': 1473, 'R3_actual_call_line': 137,
              'line138_is_phase_match': True, 'expectation_met': True}
    write(OUT / 'source-checks.json', result)
    inherited = json.loads((C / 'controls/inherited-compiler-attribution.json').read_text())
    assert inherited['prior_case_count'] == 28 and inherited['prior_positive'] == 2 and inherited['prior_expected_negative'] == 26
    for r in inherited['original_receipts'] + inherited['unchanged_exact_inputs_verified_in_original639seal']:
        p = REPO / r['path']
        assert p.resolve().is_relative_to(P.resolve())
        assert ref(p) == r
    for r in inherited['original_receipts']:
        receipt = json.loads((REPO / r['path']).read_text())
        assert receipt['expectation_met']
    result2 = {'prior_case_count': 28, 'prior_positive': 2, 'prior_negative': 26,
               'freshly_compiled': False, 'exact_old_inputs_and_receipts_verified': True,
               'attribution': ref(C / 'controls/inherited-compiler-attribution.json'),
               'scope': 'Historical prototype privacy/signature feasibility only; no exporter behavior or fresh compile.'}
    write(OUT / 'historical-compiler-attribution.json', result2)
    return result

def independent_controls(model, independent):
    base = independent.fixture()
    assert outcome(model, base)['accepted']
    rows = []
    def case(name, expected, pairs=(), data=None):
        value = changed(base, pairs) if data is None else data
        path = OUT / 'new-fixtures' / (name + '.bin')
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(value)
        observed = outcome(model, value)
        rows.append({'name': name, 'expected_acceptance': expected, **observed,
                     'mutations': list(pairs), 'fixture': ref(path),
                     'expectation_met': observed['accepted'] == expected})
    # Every source length duplicate, with one word changed at a time.
    for p in [64, 536, 1360, 1656, 1616, 1632, 1608, 792, 144, 152]:
        case('source-length-disagrees-%d' % p, False, [(p, word(base, p) + 1)])
    for p in list(range(96, 136, 8)) + list(range(544, 584, 8)) + [216, 72, 264, 480]:
        case('header-copy-disagrees-%d' % p, False, [(p, word(base, p) - 1)])
    # Isolate observed logical lengths; types/defined companion joins stay coherent.
    for p in [224, 232, 240, 248, 272, 280, 288, 296]:
        pairs = [(p, word(base, p) + 1)]
        if p == 224: pairs += [(1368, 2)]
        if p == 248: pairs += [(256, 2)]
        case('observed-count-disagrees-%d' % p, False, pairs)
    case('validated-body-count-disagrees', False, [(256, 2)])
    # Exact per-buffer byte/count and native-capacity relations, plus valid spare capacity.
    charge = word(base, 160)
    for sid in range(1, 9):
        row = 1600 + sid * 64
        case('payload-byte-count-%d' % sid, False, [(row + 56, word(base, row + 56) + 8)])
        case('capacity-under-count-%d' % sid, False, [(row + 16, word(base, row + 8) - 1)])
        case('charge-is-not-length-%d' % sid, False, [(row + 16, word(base, row + 16) + 1)])
        elem = word(base, row + 24)
        case('valid-spare-capacity-%d' % sid, True,
             [(row + 16, word(base, row + 16) + 1), (row + 32, word(base, row + 32) + elem), (160, charge + elem)])
    # Clearing complete tuple and observation fields still cannot invent absence.
    memory = [384, 392, 400, 432, 440, 328, 336, 344, 352]
    table = [408, 416, 424, 448, 456, 360, 368, 376]
    for name, fields in [('memory', memory), ('table', table), ('both', memory + table)]:
        case('fully-cleared-' + name, False, [(p, 0) for p in fields])
    for name, p in [('memory', 384), ('table', 408)]:
        case('invalid-presence-' + name, False, [(p, 2)])
    # Some(0), None, exact policy cap, cap+1, and minima > coherent host maximum.
    for name, minimum, omin, host, ohost, flag, oflag, maximum, omax, cap in [
        ('memory', 392, 328, 400, 352, 432, 336, 440, 344, 768),
        ('table', 416, 360, 424, None, 448, 368, 456, 376, 65536)]:
        def pairs(mn, mx, present):
            x = [(minimum, mn), (omin, mn), (host, mx), (flag, present),
                 (oflag, present), (maximum, mx if present else 0), (omax, mx if present else 0)]
            return x + ([(ohost, mx)] if ohost is not None else [])
        case('some-zero-' + name, True, pairs(0, 0, 1))
        case('some-cap-' + name, True, pairs(cap, cap, 1))
        case('some-cap-plus-one-' + name, False, pairs(cap+1, cap+1, 1))
        case('minimum-over-some-zero-' + name, False, pairs(1, 0, 1))
        case('none-host-policy-cap-' + name, True, pairs(cap, cap, 0))
        case('none-host-under-cap-' + name, False, pairs(0, cap-1, 0))
        case('none-nonzero-payload-' + name, False, pairs(0, cap, 0) + [(maximum, 1), (omax, 1)])
        case('declared-pair-flag-mismatch-' + name, False, pairs(0, 0, 1) + [(oflag, 0)])
    for p in [1376, 1384, 1392, 1408, 1416, 1368]:
        case('guard-word-disagrees-%d' % p, False, [(p, word(base, p) + 1)])
    case('slot-minimum-with64-entry-budget', True, [(1160, 64)])
    case('slot-zero-budget', False, [(1160, 0), (1376, 0)])
    case('pin64-boundary', True, [(1168, 64), (1384, 64)])
    case('pin65-refused', False, [(1168, 65), (1384, 65)])
    case('pinzero-refused', False, [(1168, 0), (1384, 0)])
    case('cache-base-at-capacity', True, [(1400, word(base, 1408))])
    case('cache-base-above-capacity', False, [(1400, word(base, 1408)+1)])
    case('runtime-memory-is-separate-configuration', True, [(1208, 767)])
    case('runtime-deadline-is-separate-configuration', True, [(1256, 0)])
    case('validation-runtime-metadata-budgets-distinct', True, [(1136, 0)])
    case('wasi-some-allzero-distinct', True, [(1112, 1)])
    case('wasi-none-with-grant-refused', False, [(1320, 1)])
    case('wasi-some-grant-boundary', True, [(1112, 1), (1320, 1)])
    case('wasi-some-grant-nonboolean-refused', False, [(1112, 1), (1320, 2)])
    write(OUT / 'new-independent-controls.json', {'count': len(rows),
          'passed': sum(r['expectation_met'] for r in rows), 'cases': rows,
          'fixture_origin': ref(I / 'review_controls.py'),
          'scope': 'New independently authored data controls. Synthetic acceptance is never authentic proof, exact ABI or admission.'})
    return rows

def main():
    assert not OUT.exists(), 'Preserve all completed or failed attempts; never overwrite.'
    OUT.mkdir()
    start = datetime.now(timezone.utc).isoformat()
    t = time.monotonic()
    before = custody()
    write(OWN / 'input-custody-before.json', before)
    model = load('reviewed_corrected_model', C / 'format_model.py')
    old = load('reviewed_original_model', P / 'format_model.py')
    independent = load('reviewed_original_data_controls', I / 'review_controls.py')
    tested = methods(model)
    independent.CANDIDATE = C
    independent.OUT = OUT / 'retained-format'
    independent.GROUPS = []
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        independent.formats()  # Reviewed six data groups only; never main/compilers.
    (OUT / 'retained-format.txt').write_text(stream.getvalue())
    groups = independent.GROUPS
    assert [g['id'] for g in groups] == ['F01','F02','F03','F04','F05','F06']
    assert sum(len(g['subcases']) for g in groups) == 26
    write(OUT / 'retained-format.json', {'groups': groups, 'group_count': 6,
           'subcase_count': 26, 'only_formats_invoked': True, 'compiler_functions_invoked': False})
    failures = historical_failures(model, old, independent)
    migrated = migration(model, old)
    source = source_checks()
    fresh = independent_controls(model, independent)
    after = custody()
    write(OWN / 'input-custody-after.json', after)
    assert before == after
    version = subprocess.run([sys.executable, '-B', '--version'], capture_output=True, check=True, timeout=5)
    revision = subprocess.run(['git','rev-parse','HEAD'], cwd=REPO, capture_output=True, check=True, timeout=5)
    (OUT / 'python-version.stdout').write_bytes(version.stdout)
    (OUT / 'python-version.stderr').write_bytes(version.stderr)
    (OUT / 'git-revision.stdout').write_bytes(revision.stdout)
    checks = [tested['expectation_met'], all(g['expectation_met'] for g in groups),
              all(r['expectation_met'] for r in failures), migrated['expectation_met'],
              source['expectation_met'], all(r['expectation_met'] for r in fresh)]
    result = {'schema': 1, 'started': start, 'completed': datetime.now(timezone.utc).isoformat(),
              'elapsed_seconds': time.monotonic()-t, 'runner': ref(Path(__file__)),
              'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'cwd': str(REPO),
              'python': {'version': version.stdout.decode().strip(), 'executable': str(Path(sys.executable).resolve()),
                         'executable_sha256': sha(Path(sys.executable).resolve().read_bytes())},
              'source_revision_context': revision.stdout.decode().strip(),
              'candidate_seal_sha256': PACKETS[0][1], 'accepted_source_tree_sha256': before['accepted_source']['tree_sha256'],
              'producer_methods': 12, 'retained_format_groups': 6, 'retained_format_subcases': 26,
              'exact_original_failure_refusals': 5, 'positive_migration_word_reversions': 3,
              'new_independent_controls': len(fresh), 'new_controls_passed': sum(r['expectation_met'] for r in fresh),
              'all_fresh_expectations_met': all(checks),
              'original_failures_preserved': True, 'input_custody_unchanged': before == after,
              'fresh_compiler_cases': 0, 'historical_prototype_cases': 28,
              'source_equations_reviewed': 29, 'exact_source_excerpts': 19,
              'cleanup': {'owned_children_reaped': True, 'native_UI_capture_process_inventory': False,
                          'scratch_created': False, 'compiler_products_created': False,
                          'bytecode_created': any(OWN.rglob('__pycache__')),
                          'writes_limited_to_owned_directory': True},
              'scope': 'Independent finite R1-R3 contract/model/source review only; no exporter implementation, admission, native/OTA/operational/GA authority.'}
    write(OWN / 'review-result.json', result)
    print(json.dumps({k: result[k] for k in ['all_fresh_expectations_met','producer_methods','retained_format_groups','retained_format_subcases','new_independent_controls','new_controls_passed','cleanup']}, sort_keys=True))
    return 0 if result['all_fresh_expectations_met'] else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        write(OWN / 'failure.json', {'type': type(error).__name__, 'detail': str(error),
              'at': datetime.now(timezone.utc).isoformat(), 'runner': ref(Path(__file__)),
              'scope': 'Review attempt failure retained; no frozen inputs modified.'})
        raise
