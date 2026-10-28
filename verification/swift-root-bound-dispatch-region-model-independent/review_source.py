#!/usr/bin/env python3
"""Source/hash review only. Does not compile, interpret or execute the model."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-dispatch-region-model'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def main():
    started = time.monotonic()
    inputs = {}
    def pin(row, base=R):
        assert time.monotonic() - started < 55
        path = base / row['path']
        assert path.is_file() and not path.is_symlink()
        digest, length = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while chunk := stream.read(262144):
                assert time.monotonic() - started < 55
                digest.update(chunk); length += len(chunk)
        actual = {'bytes': length, 'sha256': digest.hexdigest()}
        assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
        inputs[str(path.relative_to(R)) if path.is_relative_to(R) else str(path)] = actual
    assert sha((P / 'seal.json').read_bytes()) == 'e0d38e4ddc3e2ab130d516750208981112d62135ab58b9598c751ac16e847c5d'
    sealed = load(P / 'seal.json')
    assert len(sealed['members']) == sealed['member_count'] == 10
    assert sha(canonical(sealed['members'])) == sealed['tree_sha256'] == 'd2ca8f1721f2a4b8df37e9afdebe63ef408322aaad1854717eaa8a7336fa95aa'
    for row in sealed['members']:
        pin(row, P)
    assert not any(path.is_symlink() for path in P.rglob('*'))
    assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in sealed['members']] + ['seal.json'])
    manifest = load(P / 'input-manifest.json')
    for row in manifest['inputs'] + manifest['source_files'] + manifest['SDK_settings']:
        pin(row)
    for field in ['compiler', 'linker_driver', 'link_editor']:
        pin(manifest[field])
    tool_manifest = load(R / manifest['toolchain_manifest']['path'])
    for row in tool_manifest['members']:
        pin(row, Path(tool_manifest['root']))
    assert sha(canonical(tool_manifest['members'])) == tool_manifest['tree_sha256']
    source_contract = load(R / 'verification/swift-root-bound-dispatch-lifetime-contract/seal.json')
    for row in source_contract['members']:
        pin(row, R / 'verification/swift-root-bound-dispatch-lifetime-contract')
    independent_contract = load(R / 'verification/swift-root-bound-dispatch-lifetime-contract-independent/seal.json')
    for row in independent_contract['members']:
        pin(row, R / 'verification/swift-root-bound-dispatch-lifetime-contract-independent')
    selection = load(R / 'verification/swift-semantic-adapter-root-review/dispatch-region-model-selection.json')['selection']
    assert selection['current_production_selectors_remain_pending'] is True and selection['compiler_or_runtime_released'] is False
    assert selection['implementation_files'] == [row['path'] for row in manifest['source_files']]
    plan = load(P / 'host-test-plan.json')
    assert sha((P / 'host-test-plan.json').read_bytes()) == 'ab5584b2783ef8186908a5ba05fefbf55fcd429a37431d55d93043400c6de522'
    assert plan['execution_so_far'] == {'compiler': 0, 'formatter': 0, 'tests': 0, 'version_queries': 0}
    assert plan['bounds'] == {'automatic_retries': 0, 'compile_deadline_seconds': 30, 'compiler_invocations': 1,
        'formatter_or_version_invocations': 0, 'host_test_deadline_seconds': 45, 'host_test_invocations': 1,
        'maximum_generated_bytes': 33554432, 'maximum_generated_members': 64,
        'maximum_stderr_bytes_per_command': 524288, 'maximum_stdout_bytes_per_command': 262144,
        'owned_cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5, 'test_threads': 1, 'wall_seconds': 55}
    assert len(plan['commands']) == 2 and plan['commands'][0]['kind'] == 'compile' and plan['commands'][1]['kind'] == 'host-tests'
    compile_argv, test_argv = [row['argv'] for row in plan['commands']]
    assert compile_argv[0] == plan['compiler']['path'] and '--test' in compile_argv
    assert compile_argv[compile_argv.index('--target') + 1] == 'aarch64-apple-darwin'
    assert compile_argv[compile_argv.index('-o') + 1] == plan['owned_outputs']['binary']
    assert test_argv == [plan['owned_outputs']['binary'], '--test-threads=1', '--nocapture']
    assert plan['commands'][1]['execute_only_if_compile_exit_zero'] is True
    assert plan['owned_outputs']['directory'] == str(P / 'command')
    assert plan['environment']['TMPDIR'] == str(P / 'command/tmp')
    assert plan['owned_outputs']['global_process_inventory_forbidden'] is True and not (P / 'command').exists()
    model = (P / 'source/model.rs').read_text()
    tests = (P / 'source/tests.rs').read_text()
    names = re.findall(r'#\[test\]\s*fn\s+([A-Za-z_0-9]+)\(', tests)
    family_map = load(P / 'test-family-map.json')
    assert len(names) == len(set(names)) == 20
    assert names == [row['rust_test'] for row in family_map['families']]
    assert all(row['executed'] is False for row in family_map['families'])
    assert model.count('use std::') == 1 and 'use std::collections::{BTreeMap, BTreeSet};' in model
    assert '#[path = "tests.rs"]' in model
    for forbidden in ['unsafe {', 'extern crate ', 'include!(', 'std::fs::', 'std::process::', 'std::env::', 'mixer_vm::']:
        assert forbidden not in model and forbidden not in tests
    assert 'let mut candidate = self.clone();' in model and 'candidate.step(event)?;' in model and 'candidate.record(); *self = candidate;' in model
    assert 'ScopePairReady' in model and 'E::SplitScopePair' in model and 'Self::ScopePair => Some(Bytes(56))' in model
    assert 'PayloadDropping' in model and 'WrapperDropping' in model and 'UnwindSite::CaptureMoves => false' in model
    assert 'struct ModelOnly;' in model and 'Assessment { outcome, marker: ModelOnly }' in model
    assert 'pub fn is_model_only(&self) -> bool { true }' in model
    assert 'child_storage_retained = false' in model and 'self.destroyed(ValueId::Token)' in model
    assert 'if matches!(trace.phase, Phase::Terminal(Terminal::Forgotten | Terminal::Unwound))' in model
    assert 'seen_quote != (0u8..10).collect::<BTreeSet<_>>()' in model
    assert 'retained_child_storage_sum: Bytes(child_storage)' in model
    # Source-order proof of the missing typed return carrier. These checks are
    # not an execution of producer functions or a declaration of test results.
    snapshot = model[model.index('struct Snapshot'):model.index('pub struct TraceState')]
    assert 'phase:' not in snapshot and 'Payload' not in snapshot
    assert 'P::BodyReturned(Payload::SetupRefused(stage))' in model
    assert 'E::BoundReturn) if self.arguments_prepared => self.phase = P::BodyReturned(payload)' in model
    assert '(P::BodyReturned(payload), E::ChildWrap) => { self.transfer(ValueId::Body, ValueId::Child)' in model
    owner_shapes = model[model.index('fn for_owner(owner: ValueId)'):model.index('#[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum End')]
    assert 'ValueId::Body =>' not in owner_shapes and 'other => Self::UnobservedFrame(other)' in owner_shapes
    assert 'Self::UnobservedFrame(_) => None' in model
    assert 'shape.observed_size().unwrap_or(Bytes(8)).0' in tests
    finding = {'id': 'R01', 'priority': 1, 'file': 'source/model.rs',
        'source_lines': [47, 74, 152, 191, 192, 263, 266],
        'issue': 'The complete pre-wrap admitted return value has no typed representation coverage requirement. Both setup-refusal and BoundReturn use BodyReturned while the only semantic owner stays Body, which maps to UnobservedFrame with no observed minimum. History drops phase/payload, so assess cannot recover a phase-specific requirement. An8-byte Body extent is accepted by geometry validation even when Child is declared live only after ChildWrap.',
        'consequence': 'A fitting model can omit the13624-byte complete admitted return carrier during a known source-value phase. This undermines model capacity completeness, while all outcomes correctly remain model_only and create no actual grant.',
        'minimum_fix': 'Add a distinct typed admitted return owner at every BodyReturned transition, mapping to CurrentShape::AdmittedOutcome, or equivalent explicit phase-aware reviewed return-slot/containment coverage. Preserve the separate unknown callee/frame obligation and do not infer physical aliasing with the later child.',
        'test_requirement': 'Narrow child extents to actual post-ChildWrap live segments. Missing/undersized/expired pre-wrap return coverage must refuse for both setup-refusal and loaded/refused BoundReturn. Explicit full13624-byte evidence or an evidenced containing return slot can permit a synthetic model-only fit.'}
    cases = {'schema': 1, 'status': 'SOURCE_REVIEW_CASE_SPECIFICATIONS_NOT_EXECUTED', 'cases': [
        {'id': 'C01', 'path': 'SetupRefused(0) -> BodyReturned -> ChildWrap -> explicit destruction',
         'declarations': 'Child extent begins only at ChildWrap; Body frame extent8; no admitted return extent or containing-slot mapping.',
         'required_result_after_fix': 'IncompleteEvidence or InvalidTrace before any ModelFitsCapacity.'},
        {'id': 'C02', 'path': 'Loaded branch -> LeafFinish/BoundReturn -> BodyReturned -> ChildWrap',
         'declarations': 'Same narrow child lifetime; no complete13624-byte admitted return coverage.',
         'required_result_after_fix': 'IncompleteEvidence or InvalidTrace.'},
        {'id': 'C03', 'path': 'Each BodyReturned path', 'declarations': 'Typed admitted return carrier with capacity8 or live interval ending before return segment.',
         'required_result_after_fix': 'InvalidTrace/IncompleteEvidence; arbitrary evidence labels cannot defeat known shape width.'},
        {'id': 'C04', 'path': 'Each BodyReturned path', 'declarations': 'Complete13624-byte typed return extent or explicitly evidenced containing slot, plus all existing backing/frame/quote evidence.',
         'required_result_after_fix': 'Synthetic fit may be returned only with model_only=true; no inferred alias, product quote or grant.'}]}
    with (D / 'return-carrier-case-specifications.json').open('x') as stream:
        json.dump(cases, stream, indent=2, sort_keys=True); stream.write('\n')
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_MODEL_SOURCE_REVIEW_TYPED_PREWRAP_RETURN_COVERAGE_CORRECTION_REQUIRED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'python': sys.version,
        'script_sha256': sha(Path(__file__).read_bytes()), 'elapsed_seconds': time.monotonic() - started,
        'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 10,
        'host_plan_sha256': sha((P / 'host-test-plan.json').read_bytes()), 'input_members_verified': len(inputs),
        'checked_input_tree_sha256': sha(canonical(inputs)), 'source146_binding': manifest['source146_contract_binding'],
        'declared_test_methods_read': 20, 'tests_compiled_or_executed': 0,
        'positives': ['ScopePairReady and SplitScopePair add an explicit56-byte caller/P0 value without inferring physical overlap.',
            'Candidate-copy transitions preserve invalid-refusal atomicity; payload/wrapper and unwind cleanup phases are distinct.',
            'Acquisition/P0/C0-C5 terms, Work/Bytes units, checked arithmetic, once-per-backing owner sets and missing evidence gates are explicit.',
            'Every Assessment carries a private ModelOnly marker; reviewed-looking evidence never yields product authority.',
            'Exact host plan contains one compile and one serial host-test command under55seconds, no retry, no product/native work.'],
        'findings': [finding], 'root_host_compile_test_release_recommended': False,
        'invariant_fallback_note': 'The fallback is explicitly synthetic/conservative and is not evidence of normal File reachability. Keep its source-observation assumptions visible; do not promote the after-two-open test into an actual source execution claim.',
        'model_product_compiler_runtime_parser_version_native_ui_capture_child_process_queries': 0,
        'all_prices_physical_capacity_grants_funding_ownership_GA_pending': True,
        'cleanup': 'No compiler/test process or generated build artifact created; no cleanup owed.'}
    with (D / 'review-result.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'declared_test_methods_read',
        'tests_compiled_or_executed', 'root_host_compile_test_release_recommended')}))


if __name__ == '__main__':
    main()
