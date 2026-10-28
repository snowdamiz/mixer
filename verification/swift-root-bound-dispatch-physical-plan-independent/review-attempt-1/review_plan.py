#!/usr/bin/env python3
"""Independent offline source-plan/custody review. No compiler or producer replay."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-dispatch-physical-plan'
started = time.monotonic()
inputs, paths = {}, {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def observe(path):
    assert time.monotonic() - started < 55
    assert path.is_file() and not path.is_symlink(), path
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(262144):
            assert time.monotonic() - started < 55
            digest.update(chunk)
            size += len(chunk)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def pin(row, base=R):
    path = base / row['path']
    actual = observe(path)
    assert actual == {key: row[key] for key in ('bytes', 'sha256')}, path
    name = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
    assert name not in inputs or inputs[name] == actual
    inputs[name], paths[name] = actual, path


def load(path, expected=None):
    raw = path.read_bytes()
    assert len(raw) <= 1048576
    if expected is not None:
        assert sha(raw) == expected
    pin({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


sealed = load(P / 'seal.json', 'dae114f54519f570e009db7eda8308f96008305eb9d4cfd102ae6e69f10998db')
assert len(sealed['members']) == sealed['member_count'] == 11
assert len({row['path'] for row in sealed['members']}) == 11
assert sha(canonical(sealed['members'])) == sealed['tree_sha256'] == 'f7238df7b0bcc9fed635afe0f66f39ec30c09d06c29d9bd3a03890070aaaca07'
for row in sealed['members']:
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
    pin(row, P)
assert not any(path.is_symlink() for path in P.rglob('*'))
assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in sealed['members']] + ['seal.json'])
manifest = load(P / 'input-manifest.json')
for row in manifest['inputs'] + manifest['SDK_settings']:
    pin(row)
capture = load(P / 'capture-plan.json', 'bed9476b169810452ac0932605784125365f57c897d1e3bf74cd9eaa6ebb8184')
source_manifest = load(R / capture['source_manifest']['path'], capture['source_manifest']['sha256'])
VM = Path(capture['source_directory'])
assert source_manifest['member_count'] == len(source_manifest['members']) == 146
assert sha(canonical(source_manifest['members'])) == source_manifest['tree_sha256'] == capture['source_tree_sha256'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
for row in source_manifest['members']:
    pin(row, VM)
tools = load(R / capture['toolchain_manifest']['path'], capture['toolchain_manifest']['sha256'])
assert sha(canonical(tools['members'])) == tools['tree_sha256']
assert len(tools['members']) == 67
for row in tools['members']:
    pin(row, Path(tools['root']))
pin(capture['compiler'])
sdk = load(R / capture['SDK_manifest']['path'], capture['SDK_manifest']['sha256'])
for row in sdk['settings']:
    pin(row)
acceptance = load(R / 'verification/swift-semantic-adapter-root-review/dispatch-region-model-v4-acceptance.json',
                  '75016d390a06112fce1463b6d84edfe9329442d747c69086b7333f2ed4e7dbe3')
assert acceptance['status'] == 'accepted-isolated-synthetic-host-model-only'
assert acceptance['physical_capacity_numeric_prices_root_funding_product_integration_GA_accepted'] is False

frontier = load(P / 'target-frontier.json')
assert [target['id'] for target in frontier['targets']] == ['Caller', 'Closure', 'Dispatch', 'Body']
assert frontier['unknown_Body_frame_bytes'] is None
assert [row['bytes'] for row in frontier['known_type_minima_only']] == [13624, 13640, 13640]
assert all(row['alignment'] == 8 for row in frontier['known_type_minima_only'])
assert frontier['targets'][2]['retained_MIR_is_generic_template_not_native_monomorphization'] is True
span_count = 0


def span(row):
    global span_count
    pin(row['file'])
    raw = (R / row['file']['path']).read_bytes()
    begin, end = row['byte_begin'], row['byte_end']
    assert 0 <= begin < end <= len(raw)
    assert sha(raw[begin:end]) == row['span_sha256']
    if 'line_begin' in row:
        lines = raw.splitlines(keepends=True)
        assert begin == sum(map(len, lines[:row['line_begin'] - 1]))
        assert end == sum(map(len, lines[:row['line_end_inclusive']]))
    span_count += 1
    return raw[begin:end]


for target in frontier['targets']:
    source = span(target['source'])
    mir = span(target['retained_MIR'])
    assert mir.startswith(b'fn ') and mir.rstrip().endswith(b'}')
    if target['id'] != 'Closure':
        assert source.lstrip().startswith((b'fn ', b'pub(super) fn '))
    for row in target.get('complete_return_constructs', []):
        span(row)
span(frontier['destruction_continuation']['source'])
assert span_count == 11
closure = frontier['targets'][1]['source']
initial = (R / closure['file']['path']).read_bytes()
expression = closure['expression'].encode()
assert initial.count(expression) == 1 and initial[closure['byte_begin']:closure['byte_end']] == expression
prefix = initial[:closure['byte_begin']]
assert prefix.count(b'\n') + 1 == 861
assert len(prefix.rsplit(b'\n', 1)[-1].decode()) + 1 == 36
assert frontier['destruction_continuation']['out_of_this_capture_frontier'] is True
assert frontier['destruction_continuation']['no_normal_return_fact_qualifies_destruction_or_unwind_peak'] is True

argv = capture['argv']
expected_argv = [capture['compiler']['path'], '--crate-name', 'mixer_vm', '--edition=2021', '--target', 'aarch64-apple-darwin',
    '-C', 'overflow-checks=yes', '-C', 'panic=unwind']
for feature in ('experimental-swift-reactor', 'experimental-swift-wasi', 'experimental-stream-validation', 'experimental-function-cache'):
    expected_argv += ['--cfg', 'feature="' + feature + '"']
expected_argv += ['--cfg', 'mixer_bootstrap_one_fixture_v1', '-C', 'opt-level=0', '-Zmir-opt-level=0', '-C', 'codegen-units=1',
    '-C', 'debuginfo=2', '--crate-type', 'rlib', str(VM / 'src/lib.rs'), '--error-format=json',
    '--emit=llvm-ir=' + str(P / 'command/dispatch.ll') + ',asm=' + str(P / 'command/dispatch.s')]
assert argv == expected_argv and sha(canonical(argv)) == capture['argv_sha256_canonical_JSON']
assert capture['bounds'] == {'automatic_retries': 0, 'compiler_invocations': 1, 'formatter_or_version_queries': 0,
    'maximum_generated_members': 64, 'maximum_generated_total_bytes': 268435456, 'maximum_stderr_bytes': 2097152,
    'maximum_stdout_bytes': 1048576, 'owned_cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5,
    'wall_seconds': 55, 'work_deadline_seconds': 44}
assert all(capture[field] == 0 for field in ('compiler_executed_during_this_preparation', 'host_binary_invocations', 'layout_query_invocations', 'linker_invocations', 'model_test_invocations', 'source_edits'))
assert capture['raw_capture_accepts_no_region_fact_or_capacity'] is True
assert capture['qualifies_only_this_exact_build_not_previous_Debug_opt2_or_future_product'] is True
assert capture['environment']['CARGO_MANIFEST_DIR'] == str(VM)
assert capture['environment']['TMPDIR'] == str(P / 'command/tmp')
assert capture['environment']['RUSTC_BOOTSTRAP'] == '1'
assert capture['owned_output_directory'] == str(P / 'command')
try:
    (P / 'command').lstat()
except FileNotFoundError:
    pass
else:
    raise AssertionError('capture output already exists')

requirements = load(P / 'evidence-requirements.json')
assert requirements['all_results_local_geometry_only'] is True
assert requirements['complete_capacity_accepted'] is False and requirements['production_authority_constructible'] is False
assert [row['id'] for row in requirements['requirements']] == ['R', 'C', 'F', 'B']
assert len(requirements['retained_partitions']) == 10
controls = load(P / 'prospective-controls.json')
assert [row['id'] for row in controls['families']] == [f'P{index:02}' for index in range(1, 17)]
assert all(row['executed'] is False for row in controls['families'])
next_slice = load(P / 'next-slice.json')
assert next_slice['proposed_source_files'] == [
    'verification/swift-root-bound-dispatch-physical-evidence-v1/source/region_certificate.py',
    'verification/swift-root-bound-dispatch-physical-evidence-v1/source/tests_region_certificate.py']
assert next_slice['canonical_product_source_changes'] == 0 and next_slice['new_storage_wrapper_selected'] is False
assert next_slice['future_offline_limits'] == {'children': 0, 'compiler_or_version_queries': 0, 'network': False, 'wall_seconds': 55}
assert next_slice['semantics_review_cannot_be_replaced_by_matching_snippets'] is True
plan_text = (P / 'PLAN.md').read_text()
assert 'Every normal return must write the complete admitted carrier.' in plan_text
assert 'Matching snippets alone never proves a mapping.' in plan_text
assert 'Freeze the verifier and synthetic controls before parsing actual saved artifacts.' in plan_text
assert 'full expected records' in plan_text and 'exact successful warning-summary form' in plan_text

expectations = {
    'P01': 'Closed schema:reject duplicate/nonfinite/boolean numeric values,unknown fields/IDs and path/member collisions.',
    'P02': 'Read bounded+1 bytes;hash actual memory before parsing;pin IR/assembly/source/receipt bytes;recheck paths afterward.',
    'P03': 'Unique actual four-target symbols and exact861:36 closure;generic MIR only guides identity,never substitutes for native mono;missing/DCE stays incomplete.',
    'P04': 'Complete13624-byte allocated carrier extent covers all returns/prewrap phases;do not require padding or inactive enum bytes to be initialized/written.',
    'P05': 'Complete13640-byte child and any distinct outerResult destination,without assuming equal-size identity.',
    'P06': 'Unknown Body is unknown,not8 or alloca sum;whole native frame needs every relevant SP/exit/call-storage relation.',
    'P07': 'Unresolved sret/PHI/cast/indirect or copy provenance remains unknown even if source/certificate names look plausible.',
    'P08': 'Root-reviewed relations establish same-base/offset or disjointness;source move,equal width or numeric IDs do not.',
    'P09': 'Checked capacity/end/alignment;native negative entry-SP offsets require explicit reviewed rebase and no wraparound;bytes/work distinct.',
    'P10': 'Union only the explicitly closed/proved local region set;contained frame slots once,partial overlap union,separate proven arenas add.',
    'P11': 'Narrow phases:Body and complete R before child;every applicable segment covered;unknown relation blocks that calculation.',
    'P12': 'Whole frame already containing R/C counts once;entry-relative bases/caller-callee relation independently mapped;unresolved frame storage notzero.',
    'P13': 'List every outgoing/cleanup edge;callee,dynamic/probe,destruction/unwind unknowns block complete capacity while resolved local rows remain scoped.',
    'P14': 'Backing IDs retain whole obligations R→C;missing bounds/destruction stayunknown;never pointer/FD/Arc-request size as actual backing.',
    'P15': 'Root approval expected hash comes from trusted released invocation,notcertificate;bind semantic map,independent review,raw artifact and accepted capture/diagnostic custody hashes. Fake labels/self-approved synthetic data never becomes actual reviewed geometry.',
    'P16': 'Exact source-bound three baseline warnings+success summary must freeze before capture;root capture acceptance binds raw stdout/stderr,exit,custody,bounds. Unknown/truncated/oversize/DCE artifacts or changed bytes refuse with no fallback.'}
with (D / 'implementation-review-expectations.json').open('x') as stream:
    json.dump({'schema': 1, 'status': 'FROZEN_SOURCE_REVIEW_EXPECTATIONS_NOT_EXECUTED', 'families': expectations,
               'all_results_local_geometry_only': True, 'complete_capacity_accepted': False}, stream, indent=2, sort_keys=True)
    stream.write('\n')
after = {name: observe(path) for name, path in paths.items()}
assert after == inputs
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_SOURCE_ONLY_PHYSICAL_PLAN_REVIEW_TWO_FILE_OFFLINE_SLICE_RECOMMENDED',
    'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 11,
    'capture_plan_sha256': sha((P / 'capture-plan.json').read_bytes()),
    'source146_tree_sha256': capture['source_tree_sha256'], 'source_members_verified': 146,
    'toolchain_members_verified': 67, 'source_MIR_spans_verified': span_count,
    'exact_closure_line_column': [861, 36], 'prospective_control_families': 16,
    'checked_input_members': len(inputs), 'before_after_input_tree_sha256': sha(canonical(inputs)), 'before_after_custody_equal': True,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                    'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()),
    'findings': [], 'next_executable_source_slice_recommended': next_slice['proposed_source_files'],
    'capture_or_actual_saved_verifier_release_recommended_now': False,
    'recommendation': 'Implement/freeze/source-review only the two proposed stdlib offline verifier/test files and16finite synthetic controls. Separately freeze/review root capture controller and full expected diagnostics;later actual capture,semantic mapping/root approval and exact saved-input parse each remain separately gated.',
    'useful_possible_facts': ['Exact current-build return-destination identity and13,624-byte carrier coverage','13,640-byte child/outerResult destination relation and containment','Independently reviewed local native reservations and phase-wise local unions'],
    'unproved': ['Whether all private native targets actually emit in this unexecuted capture configuration','Complete Body/caller/closure/dispatcher/transitive peak unless all required facts separately mapped','Deeper callees,stack helpers,destruction/unwind peaks','Actual backing upper bounds/final destruction','Numeric work/storage prices,root durability/funding,product integration,GA'],
    'implementation_clarifications': ['Complete return-carrier coverage is storage capacity/lifetime,not a requirement to write padding or inactive variant bytes.',
        'The artifact-bound root approval must cover accepted capture diagnostic/custody evidence as well as the semantic mapping/review seal;do not trust certificate-supplied approval identity.',
        'Partial resolved rows may be local facts only;unknown arena/frame/call relations prevent the corresponding complete union/capacity calculation.',
        'No source-based promise that four private targets survive codegen;missing/ambiguous/DCE stays incomplete with no automatic compiler changes.'],
    'compiler_query_model_verifier_runtime_producer_replay_version_native_UI_capture_device_network_process_commands': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_capacity_prices_backing_bounds_root_funding_product_GA_accepted': False,
    'cleanup': 'No process or capture artifact created;no cleanup owed.', 'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
for name, value in [('review-result.json', report), ('checked-inputs.json', inputs)]:
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'source_members_verified',
    'source_MIR_spans_verified', 'checked_input_members', 'capture_or_actual_saved_verifier_release_recommended_now', 'elapsed_seconds')}))
