#!/usr/bin/env python3
"""Independent textual/source and custody review; never executes Rust or producer code."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[2]
P = R / 'verification/swift-root-bound-dispatch-region-model-v2'
OLD = R / 'verification/swift-root-bound-dispatch-region-model'
OLD_REVIEW = D.parent


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
    input_paths = {}

    def observe(path):
        assert time.monotonic() - started < 55
        assert path.is_file() and not path.is_symlink(), path
        digest, length = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while chunk := stream.read(262144):
                assert time.monotonic() - started < 55
                digest.update(chunk)
                length += len(chunk)
        return {'bytes': length, 'sha256': digest.hexdigest()}

    def pin(row, base=R):
        path = base / row['path']
        actual = observe(path)
        assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
        key = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
        assert key not in inputs or inputs[key] == actual
        inputs[key] = actual
        input_paths[key] = path

    def packet(path, digest, count, tree=None, exact_roster=True):
        raw = (path / 'seal.json').read_bytes()
        assert sha(raw) == digest
        pin({'path': str(path / 'seal.json'), 'bytes': len(raw), 'sha256': digest})
        sealed = load(path / 'seal.json')
        assert len(sealed['members']) == sealed['member_count'] == count
        assert sha(canonical(sealed['members'])) == sealed['tree_sha256']
        if tree is not None:
            assert sealed['tree_sha256'] == tree
        assert len({row['path'] for row in sealed['members']}) == count
        for row in sealed['members']:
            assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
            pin(row, path)
        if exact_roster:
            assert not any(member.is_symlink() for member in path.rglob('*'))
            assert sorted(member.relative_to(path).as_posix() for member in path.rglob('*') if member.is_file()) == sorted([row['path'] for row in sealed['members']] + ['seal.json'])
        return sealed

    sealed = packet(P, '53ab4e6ef041346dadadbbba69b7e5f5a7c35df004d9f1da753845be15779861', 11,
                    '348f163d40ddc9931b8c78abaedb3b5a535327cd54560b9951899e0de72db952')
    packet(OLD, 'e0d38e4ddc3e2ab130d516750208981112d62135ab58b9598c751ac16e847c5d', 10,
           'd2ca8f1721f2a4b8df37e9afdebe63ef408322aaad1854717eaa8a7336fa95aa')
    packet(OLD_REVIEW, '7511b6f50d3b701eecaddfaa710b8342626bb36fc748d4b185b0072a14bd744d', 6,
           '4c882d61e31d407134b4bc937482fb39594c429847f6b8ee482ce5db38b69684', exact_roster=False)
    manifest = load(P / 'input-manifest.json')
    for row in manifest['inputs'] + manifest['source_files'] + manifest['SDK_settings']:
        pin(row)
    for field in ('compiler', 'linker_driver', 'link_editor'):
        pin(manifest[field])
    tool_manifest = load(R / manifest['toolchain_manifest']['path'])
    assert sha(canonical(tool_manifest['members'])) == tool_manifest['tree_sha256']
    for row in tool_manifest['members']:
        pin(row, Path(tool_manifest['root']))
    packet(R / 'verification/swift-root-bound-dispatch-lifetime-contract',
           '1ce05f8759b634e7a8c651a88ea4290b69ba8fde5bb100ed86802a0a5599a882', 12)
    packet(R / 'verification/swift-root-bound-dispatch-lifetime-contract-independent',
           'ea02c82bb26690ac3d1b3dd5692b0b649b4f737b6bfde59c882e177fdde0f3d6', 10)

    model = (P / 'source/model.rs').read_text()
    tests = (P / 'source/tests.rs').read_text()
    old_model = (OLD / 'source/model.rs').read_text()
    old_tests = (OLD / 'source/tests.rs').read_text()
    # Exact complete model delta, not merely presence of added test assertions.
    replacements = [
        ('    Body, Leaf, Child, View, PrimaryView, DestroyWrapper, DestroyPayload, Token, Forgotten, UnwindRetained }',
         '    Body, Leaf, AdmittedReturn, Child, View, PrimaryView, DestroyWrapper, DestroyPayload, Token, Forgotten, UnwindRetained }'),
        ('self.own(BackingKey::Error, ValueId::Body); self.phase = P::BodyReturned(Payload::SetupRefused(stage));',
         'self.own(BackingKey::Error, ValueId::Body); self.return_admitted(Payload::SetupRefused(stage));'),
        ('self.phase = P::BodyReturned(Payload::InvariantRefused(mask));',
         'self.return_admitted(Payload::InvariantRefused(mask));'),
        ('(P::RawRefusal(payload) | P::LeafReturned(payload), E::BoundReturn) if self.arguments_prepared => self.phase = P::BodyReturned(payload),\n'
         '            (P::BodyReturned(payload), E::ChildWrap) => { self.transfer(ValueId::Body, ValueId::Child); self.phase = P::Returned(payload); }',
         '(P::RawRefusal(payload) | P::LeafReturned(payload), E::BoundReturn) if self.arguments_prepared => self.return_admitted(payload),\n'
         '            (P::BodyReturned(payload), E::ChildWrap) => {\n'
         '                self.transfer(ValueId::AdmittedReturn, ValueId::Child); self.destroyed(ValueId::Body); self.phase = P::Returned(payload);\n'
         '            }'),
        ('    fn move_payload_out(&mut self) {',
         '    fn return_admitted(&mut self, payload: Payload) {\n'
         '        // Complete AdmittedFixtureOutcome exists before PrepaidOwned wrapping.\n'
         '        // The callee activation/frame remains a separate unknown-size obligation.\n'
         '        // Moving ownership establishes neither a return-slot alias nor disjointness.\n'
         '        self.transfer(ValueId::Body, ValueId::AdmittedReturn);\n'
         '        self.values.insert(ValueId::Body);\n'
         '        self.phase = Phase::BodyReturned(payload);\n'
         '    }\n'
         '    fn move_payload_out(&mut self) {'),
        ('ValueId::DestroyPayload => Self::AdmittedOutcome, ValueId::View => Self::SharedView, ValueId::PrimaryView => Self::PrimaryView,',
         'ValueId::AdmittedReturn | ValueId::DestroyPayload => Self::AdmittedOutcome, ValueId::View => Self::SharedView, ValueId::PrimaryView => Self::PrimaryView,'),
    ]
    expected_model = old_model
    for before, after in replacements:
        assert expected_model.count(before) == 1, before
        expected_model = expected_model.replace(before, after)
    assert model == expected_model
    assert tests.startswith(old_tests)
    delta = ''.join(difflib.unified_diff(old_model.splitlines(True), model.splitlines(True),
                                        fromfile='immutable-v1/source/model.rs', tofile='v2/source/model.rs'))
    delta += ''.join(difflib.unified_diff(old_tests.splitlines(True), tests.splitlines(True),
                                        fromfile='immutable-v1/source/tests.rs', tofile='v2/source/tests.rs'))
    assert delta.encode() == (P / 'source-delta.patch').read_bytes()

    names = re.findall(r'#\[test\]\s*fn\s+([A-Za-z_0-9]+)\(', tests)
    old_names = re.findall(r'#\[test\]\s*fn\s+([A-Za-z_0-9]+)\(', old_tests)
    family_map = load(P / 'test-family-map.json')
    assert len(names) == len(set(names)) == 24
    assert len(old_names) == 20 and names[:20] == old_names
    assert names == [row['rust_test'] for row in family_map['families']]
    assert [row['review_case'] for row in family_map['families'][20:]] == ['C01', 'C02', 'C03', 'C04']
    assert all(row['executed'] is False for row in family_map['families'])
    assert not re.search(r'#\[(ignore|should_panic)', tests)
    assert len(list((P / 'source').glob('*.rs'))) == 2
    assert model.count('use std::') == 1 and 'use std::collections::{BTreeMap, BTreeSet};' in model
    for forbidden in ('unsafe {', 'extern crate ', 'include!(', 'std::fs::', 'std::process::', 'std::env::', 'mixer_vm::'):
        assert forbidden not in model and forbidden not in tests
    assert '#[path = "tests.rs"]' in model
    # The existing complete assessment algorithm is unchanged and enforces the
    # new owner's known shape before segment coverage and checked arena unions.
    assert model.count('self.phase = Phase::BodyReturned(payload);') == 1
    assert 'self.phase = P::BodyReturned' not in model
    assert model.count('self.return_admitted(') == 3
    assert 'Self::AdmittedOutcome => Some(Bytes(13624))' in model
    assert 'region.parent.is_none() && region.shape != CurrentShape::for_owner(region.owner)' in model
    assert 'if bytes < minimum.0 || region.alignment.0 < 8' in model
    assert 'region.owner == *owner && region.parent.is_none() && region.live.covers(segment, horizon)' in model
    assert 'Assessment { outcome, marker: ModelOnly }' in model
    assert 'pub fn is_model_only(&self) -> bool { true }' in model
    assert 'seen_quote != (0u8..10).collect::<BTreeSet<_>>()' in model
    assert 'retained_child_storage_sum: Bytes(child_storage)' in model
    assert 'let mut candidate = self.clone();' in model and 'candidate.step(event)?;' in model
    assert 'candidate.record(); *self = candidate;' in model
    added = tests[len(old_tests):]
    for source in (
        'let mut paths = (0..5).map(setup_prewrap).collect::<Vec<_>>();',
        'paths.extend(loaded_prewrap_paths()); paths',
        'assert!(snapshot.values.contains(&ValueId::Body));',
        'assert!(snapshot.values.contains(&ValueId::AdmittedReturn));',
        'for owners in snapshot.backings.values() { assert!(!owners.contains(&ValueId::Body)); }',
        'region.live = Interval { begin: first as u16, end: End::At((last + 1) as u16) };',
        'assert_eq!(carrier.live.end, End::At(child.live.begin));',
        'assert_eq!(child.live.end_at(trace.history.len()), usize::from(child.live.begin) + 1);',
        'd.inline.retain(|r| r.owner != ValueId::AdmittedReturn);',
        'd.inline[index].capacity.bound = Bytes(8);',
        'd.inline[index].shape = CurrentShape::UnobservedFrame(ValueId::AdmittedReturn);',
        'd.inline[index].capacity.origin = EvidenceOrigin::Missing;',
        'd.inline[carrier_index].arena = child.arena;',
        'd.inline[carrier_index].live.end = End::At(child.live.begin + 1);',
        'd.inline[carrier_index].funding = Funding::P0;',
    ):
        assert source in added, source

    plan = load(P / 'host-test-plan.json')
    assert sha((P / 'host-test-plan.json').read_bytes()) == '5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8'
    assert plan['execution_so_far'] == {'compiler': 0, 'formatter': 0, 'tests': 0, 'version_queries': 0}
    assert plan['bounds'] == {'automatic_retries': 0, 'compile_deadline_seconds': 30, 'compiler_invocations': 1,
        'formatter_or_version_invocations': 0, 'host_test_deadline_seconds': 45, 'host_test_invocations': 1,
        'maximum_generated_bytes': 33554432, 'maximum_generated_members': 64,
        'maximum_stderr_bytes_per_command': 524288, 'maximum_stdout_bytes_per_command': 262144,
        'owned_cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5, 'test_threads': 1, 'wall_seconds': 55}
    binary = str(P / 'command/model-tests')
    compile_argv = [manifest['compiler']['path'], '--edition=2021', '--target', 'aarch64-apple-darwin', '--test',
                    str(P / 'source/model.rs'), '-C', 'opt-level=0', '-C', 'overflow-checks=yes', '-C', 'panic=unwind',
                    '-C', 'linker=' + manifest['linker_driver']['path'], '-o', binary]
    assert plan['cwd'] == str(R)
    assert plan['commands'] == [
        {'argv': compile_argv, 'execute_only_after_root_release': True, 'expected_exit': 0, 'kind': 'compile'},
        {'argv': [binary, '--test-threads=1', '--nocapture'], 'execute_only_if_compile_exit_zero': True, 'expected_exit': 0, 'kind': 'host-tests'}]
    assert plan['source_files'] == manifest['source_files']
    for field in ('compiler', 'linker_driver', 'link_editor'):
        assert plan[field] == manifest[field]
    assert plan['environment'] == {'LANG': 'C', 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin',
        'SDKROOT': '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk',
        'TMPDIR': str(P / 'command/tmp'), 'TZ': 'UTC'}
    assert plan['owned_outputs']['directory'] == str(P / 'command')
    assert plan['owned_outputs']['temporary_directory'] == str(P / 'command/tmp')
    assert plan['owned_outputs']['binary'] == binary
    assert plan['owned_outputs']['must_be_absent_prelaunch'] is True
    assert plan['owned_outputs']['new_process_sessions_and_exact_owned_cleanup_required'] is True
    assert plan['owned_outputs']['global_process_inventory_forbidden'] is True
    assert not (P / 'command').exists()
    assert plan['root_release_required']['path'] == 'verification/swift-semantic-adapter-root-review/dispatch-region-model-v2-host-release.json'
    assert plan['root_release_required']['required_fields'] == {'automatic_retries': 0, 'compiler_invocations': 1,
        'host_test_invocations': 1, 'isolated_model_host_lane_released': True, 'plan_sha256': 'exact digest of this plan'}
    assert not (R / plan['root_release_required']['path']).exists()
    assert plan['all_assessments_model_only'] is True
    assert plan['physical_capacity_price_grant_root_funding_full_ownership_native_FieldLog_OTA_GA_accepted'] is False

    # Re-read the actual pinned inputs after all source/plan inspection. No
    # compiler/version/model execution, dynamic Rust import, or producer replay.
    after = {key: observe(path) for key, path in input_paths.items()}
    assert after == inputs
    executable = Path(sys.executable).resolve(strict=True)
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_INDEPENDENT_V2_MODEL_SOURCE_REVIEW_R01_CORRECTED_ROOT_HOST_RELEASE_RECOMMENDED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))],
        'cwd': str(R), 'python': sys.version,
        'python_tool': {'reported_path': sys.executable, 'resolved_path': str(executable), **observe(executable)},
        'review_script_sha256': sha(Path(__file__).read_bytes()),
        'producer_seal_sha256': sha((P / 'seal.json').read_bytes()),
        'producer_tree_sha256': sealed['tree_sha256'], 'producer_members_verified': 11,
        'host_plan_sha256': sha((P / 'host-test-plan.json').read_bytes()),
        'source146_binding': manifest['source146_contract_binding'],
        'source_files': manifest['source_files'], 'checked_input_members': len(inputs),
        'before_after_input_tree_sha256': sha(canonical(inputs)), 'before_after_custody_equal': True,
        'declared_test_methods': 24, 'original_methods_preserved_byte_for_byte': 20,
        'new_R01_methods': 4, 'declared_return_trace_representatives': 11,
        'all_three_BodyReturned_transition_forms_share_typed_helper': True,
        'R01_status': 'CORRECTED_BY_SOURCE_REVIEW_RUNTIME_UNVERIFIED',
        'findings': [], 'root_host_compile_test_release_recommended': True,
        'reviewer_attempt_1': 'Preserved script/stdout/stderr:source and plan checks completed;receipt writer then refused Homebrew reported Python symlink.Resolved executable path recording corrected;no producer/model execution occurred.',
        'recommendation': 'Release exactly the two pinned argv arrays serially under the single55-second plan;execute test binary only after compile0;24 tests none ignored;retain failures without retry;root owns generated output and exact child/group cleanup.',
        'unexecuted_cases': ['C01 five setup-refusal prefixes;typed carrier absent refuses with child starting only at ChildWrap.',
            'C02 two raw-refusal and three leaf-result representatives;typed carrier absent refuses.',
            'C03 all eleven representatives;undersized reviewed-looking bound,wrong shape,expired interval and missing evidence refuse.',
            'C04 all eleven representatives;complete separate coverage or declared same-arena return/child overlap remains model_only;missing identity,frame disjointness,frame lifetime or compatible funding refuses.'],
        'limits': ['Source reasoning and textual custody checks do not establish Rust compilation or any test result.',
            'Counterfactual fallback is one declared representative,not evidence of actual normal File reachability.',
            'Unknown Body frame needs its own evidence;8-byte test input is arbitrary,not measured.',
            'All physical identities,bounds,unions and reviewed-looking labels remain model hypotheses.',
            'No actual physical capacity,work prices,production grant,root funding,full ownership,FieldLog,OTA or GA accepted.'],
        'compiler_test_producer_model_runtime_parser_version_native_UI_capture_phone_network_global_process_inventory_commands': 0,
        'canonical_product_or_metadata_edits': 0, 'commit_push': 0,
        'cleanup': 'No compiler/test child or generated build artifact created;no cleanup owed.',
        'elapsed_seconds': time.monotonic() - started}
    with (D / 'review-result.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    with (D / 'checked-inputs.json').open('x') as stream:
        json.dump(inputs, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'checked_input_members',
        'declared_test_methods', 'R01_status', 'root_host_compile_test_release_recommended', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
