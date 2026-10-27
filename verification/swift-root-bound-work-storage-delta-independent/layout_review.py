#!/usr/bin/env python3
"""Source-only proposal review. Never invokes compiler, runtime or subprocess."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-root-bound-work-storage-delta'
CAND = ROOT / 'verification/swift-guarded-snapshot-root-result-lifetime-implementation/source/vm'
LOADER = CAND / 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'
CACHE = CAND / 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(p):
    return json.loads(p.read_text())


def named_queries(fragment):
    return [s.strip()[6:-2] for s in fragment.splitlines() if s.strip().startswith('pair!(')]


def check(p, fragments):
    owner, cache, closure = fragments
    queries = named_queries(owner) + named_queries(cache)
    assert len(queries) == len(set(queries)) == 28
    assert queries == [r['type'] for r in p['named_queries']]
    assert p['named_size_alignment_pairs'] == 28 and p['named_expected_E0308'] == 56
    for f in [owner, cache]:
        assert 'std::mem::size_of::<$type>()' in f and 'std::mem::align_of::<$type>()' in f
    assert 'let action = || run_prepaid_admitted_fixture_v1(fixture, attempt, expected);' in closure
    assert closure.count('std::mem::transmute(') == 2
    assert '#[repr(C)]' in closure and 'struct ClosureAlignmentProbeV1<T> { leading: u8, actual: T }' in closure
    assert 'fn uninitialized_shape_v1<T>(_: &T) -> std::mem::MaybeUninit<T>' in closure
    assert 'actual: uninitialized_shape_v1(&action)' in closure
    assert 'Ok(reservation.dispatch_v1(action))' in closure
    assert p['actual_closure_queries']['expected_E0512'] == 2
    assert p['layout_price_funding_authority'] is False
    assert p['status'] == 'PROPOSAL_ONLY_NOT_RELEASED_NOT_EXECUTED'
    assert p['bounds'] == {'compiler_invocations': 1, 'host_runs': 0, 'version_commands': 0, 'wall_seconds': 55, 'maximum_stdout_bytes': 1048576, 'maximum_stderr_bytes': 2097152, 'source_copy_members': 146}
    assert '--error-format=json' in p['argv']
    assert p['argv'].count('--emit=metadata=' + p['future_scratch_only'] + '/build/layout-proposal.rmeta') == 1
    assert not any(x in p['argv'] for x in ['--test', '--emit=link', '--run'])
    return queries


def inferred_alignment(source_bits, wrapper_bits):
    # Synthetic arithmetic only, not measurements from this product/compiler.
    assert source_bits > 0 and source_bits % 8 == wrapper_bits % 8 == 0
    s = source_bits // 8
    a = (wrapper_bits - source_bits) // 8
    assert a > 0 and (a & (a - 1)) == 0 and s % a == 0
    return s, a


def main():
    p = load(PRODUCER / 'layout-probe-proposal.json')
    fragments = [(PRODUCER / name).read_text() for name in ['proposed-owner-layout-queries.inc.rs', 'proposed-cache-layout-queries.inc.rs', 'proposed-actual-closure-layout-fragment.rs']]
    for r in p['fragments']:
        b = (ROOT / r['path']).read_bytes()
        assert len(b) == r['bytes'] and sha(b) == r['sha256']
    queries = check(p, fragments)
    # These are the finite boundary shapes independently identified from source
    # and full MIR, including nested root, branch Result and child Option places.
    for shape in [
        "RootBoundV1<'static, Result<LoaderCarrierCoreV1<File>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>",
        "Result<RootBoundV1<'static, LoaderCarrierCoreV1<File>>, RootBoundV1<'static, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<File>)>>",
        "(RawFixturePrimaryV1, ReturnedLoaderFilesV1, LoaderUsageV1, &'static BootstrapLedgerV1)",
        "PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>",
        "Result<PrepaidOwnedV1<'static, AdmittedFixtureOutcomeV1<'static>>, RefusalV1>",
        "Option<AdmittedFixtureOutcomeV1<'static>>",
        "Option<&'static AdmittedFixtureOutcomeV1<'static>>",
    ]:
        assert shape in queries
    source = [LOADER.read_text(), CACHE.read_text()]
    markers = ['    // OWNER_PROBE_INSERTION', '    // Private outer caller candidate; all prior bodies remain exact.']
    original = '        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))'
    assert source[0].count(markers[0]) == source[1].count(markers[1]) == source[1].count(original) == 1
    staged = [source[0].replace(markers[0], fragments[0] + '\n' + markers[0]), source[1].replace(markers[1], fragments[1] + '\n' + markers[1]).replace(original, fragments[2].rstrip())]
    controls = []
    def reject(label, pp, ff):
        try:
            check(pp, ff)
        except AssertionError:
            controls.append({'name': label, 'rejected': True})
        else:
            raise AssertionError(('accepted-adverse-proposal', label))
    ff = fragments.copy(); ff[0] = ff[0].replace("        pair!(RootBoundFixtureOutcomeV1<'static>);\n", '')
    reject('omit-bound-final-result-layout', p, ff)
    ff = fragments.copy(); ff[2] = ff[2].replace('run_prepaid_admitted_fixture_v1(fixture, attempt, expected)', 'proxy_captures_v1(fixture, attempt, expected)')
    reject('replace-actual-closure-with-proxy', p, ff)
    ff = fragments.copy(); ff[2] = ff[2].replace('leading: u8, actual: T', 'actual: T')
    reject('lose-leading-byte-alignment-shape', p, ff)
    pp = copy.deepcopy(p); pp['layout_price_funding_authority'] = True
    reject('invent-proposal-layout-authority', pp, fragments)
    pp = copy.deepcopy(p); pp['bounds']['host_runs'] = 1
    reject('invent-runtime-permission', pp, fragments)
    for s, a in [(24, 8), (40, 8), (16, 16), (1, 1), (32, 4)]:
        # repr(C) leading u8 advances to offset a; size(T) is a multiple
        # of align(T), so final wrapper size is exactly a + size(T).
        assert inferred_alignment(s * 8, (s + a) * 8) == (s, a)
    invalid = [(0, 8), (192, 192), (192, 184), (192, 216), (192, 193), (200, 264)]
    for pair in invalid:
        try:
            inferred_alignment(*pair)
        except AssertionError:
            controls.append({'name': 'reject-synthetic-invalid-diagnostic-pair-' + str(pair), 'rejected': True})
        else:
            raise AssertionError(('accepted-invalid-alignment', pair))
    report = {
        'schema': 1, 'status': 'ACCEPTED_SOURCE_ONLY_CONDITIONAL_NEXT_LAYOUT_PROPOSAL',
        'concrete_defects': [], 'named_boundary_shapes': 28,
        'named_expected_primary_E0308': 56, 'actual_closure_expected_primary_E0512': 2,
        'exact_source_insertions_and_replacement_apply_once': True,
        'in_memory_only_staged_source_sha256': {'loader': sha(staged[0].encode()), 'cache': sha(staged[1].encode())},
        'staged_source_files_written': 0, 'compiler_or_runtime_invocations': 0,
        'closure_alignment_reasoning': 'For repr(C) {u8,MaybeUninit<C>} and actual nonzero closure C, S=size(C) is divisible by A=align(C). The second field starts at A, so P=A+S and A=P-S. Both exact concrete diagnostic shapes, byte divisibility, power-of-two A and S%A==0 remain mandatory. Synthetic arithmetic is not a product layout observation.',
        'strategy_qualification': 'UNEXECUTED. Exact concrete diagnostic emission is not established; missing, ambiguous, dependently-sized or unexpected diagnostics require refusal and a separately reviewed correction.',
        'required_future_release': 'Root must release a separate compiler reservation and approve a bounded runner/source delta; this review grants neither execution nor any layout/price/funding acceptance.',
        'sufficiency': 'Sufficient as a conditional next compiler-only frontier for its 28 new named/aggregate shapes plus the actual anonymous dispatch closure. Not globally minimal or a full storage/layout closure: untouched callee/scalar types, test-only pair monomorphizations, monomorphized drop glue, backing capacities and live-range/peak composition stay pending.',
        'controls': controls, 'GA_accepted': False,
    }
    (HERE / 'layout-review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
