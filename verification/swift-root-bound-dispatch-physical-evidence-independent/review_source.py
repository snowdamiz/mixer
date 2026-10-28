#!/usr/bin/env python3
"""Text/hash and independent integer witness only; no target import/parse/run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-dispatch-physical-evidence-v1'
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


def read(path, expected=None):
    assert time.monotonic() - started < 55 and path.is_file() and not path.is_symlink()
    raw = path.read_bytes()
    if expected is not None:
        assert sha(raw) == expected, path
    name = str(path.relative_to(R)) if path.is_relative_to(R) else str(path)
    actual = {'bytes': len(raw), 'sha256': sha(raw)}
    assert name not in inputs or inputs[name] == actual
    inputs[name], paths[name] = actual, path
    return raw


def load(path, expected=None):
    raw = read(path, expected)
    assert len(raw) <= 1048576
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def pin(row, base=R):
    raw = read(base / row['path'], row['sha256'])
    assert len(raw) == row['bytes']


sealed = load(P / 'seal.json', '674fcb6b158055b207c8f2afd1e66e56f06910ec80229f706cab3e29c679e474')
assert len(sealed['members']) == sealed['member_count'] == 11
assert len({row['path'] for row in sealed['members']}) == 11
assert sha(canonical(sealed['members'])) == sealed['tree_sha256'] == '20bfaf9dc45a32edf7b1fc0f11d5af0eb9a5119999f886ba3fb1f0c8d2b1045b'
for row in sealed['members']:
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
    pin(row, P)
assert not any(path.is_symlink() for path in P.rglob('*'))
assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in sealed['members']] + ['seal.json'])
manifest = load(P / 'input-manifest.json')
for row in manifest['inputs'] + manifest['source_files']:
    pin(row)
plan = load(P / 'host-test-plan.json', '57f50c47eee9033e2bcaa88f5040087ffc0947dc68c73ae21a6f79be1ae01b9e')
pin(plan['python_tool'])
assert plan['argv'] == [plan['python_tool']['path'], '-B', str(P / 'source/tests_region_certificate.py')]
assert sha(canonical(plan['argv'])) == plan['argv_sha256_canonical_JSON']
assert plan['source_files'] == manifest['source_files'] and plan['cwd'] == str(R)
assert plan['bounds'] == {'automatic_retries': 0, 'compiler_capture_model_layout_version_formatter_invocations': 0,
    'maximum_generated_bytes': 16777216, 'maximum_generated_members': 64, 'maximum_stderr_bytes': 524288,
    'maximum_stdout_bytes': 262144, 'owned_cleanup_deadline_seconds': 49, 'posthash_deadline_seconds': 53.5,
    'python_test_invocations': 1, 'test_deadline_seconds': 44, 'wall_seconds': 55}
assert plan['owned_outputs']['directory'] == str(P / 'command')
assert plan['owned_outputs']['temporary_directory'] == str(P / 'command/tmp')
assert plan['owned_outputs']['root_precreates_fresh_directory_and_tmp_only'] is True
try:
    (P / 'command').lstat()
except FileNotFoundError:
    pass
else:
    raise AssertionError('host command directory already exists')
model_raw = read(P / 'source/region_certificate.py', 'da3d7f05e92dccd32447d98414b7e8d611d26b89758a7f8bfe423067222d8788')
tests_raw = read(P / 'source/tests_region_certificate.py', '098e7488af9c7a4f50d1564f4bf231dbf917c0e6a03739df46ef6a3ccf06f1fe')
assert len(model_raw) == 37212 and len(tests_raw) == 25085
model, tests = model_raw.decode(), tests_raw.decode()
names = re.findall(r'^    def (test_p\d+_\w+)\(', tests, re.M)
families = load(P / 'test-family-map.json')['families']
assert len(names) == len(set(names)) == 16
assert names == [row['test_method'] for row in families]
assert [row['family'] for row in families] == [f'P{index:02}' for index in range(1, 17)]
assert all(row['executed'] is False for row in families)
assert 'unittest.main(verbosity=2)' in tests
assert not any(token in model for token in ('import subprocess', 'os.system(', 'os.environ', 'os.getenv(', 'eval(', 'exec(', 'importlib'))
assert 'expected_approval_sha256: str|None' in model
assert 'digest(approval_raw)==expected' in model and 'inputs\':pins(blobs)' in model
assert "'semantic_review_sha256':digest(blobs['semantic_review'])" in model
assert "'capture_acceptance_sha256':digest(blobs['capture_acceptance'])" in model
assert "'whole_cfg_and_exits_checked':True,'outgoing_edges_exhaustive':True" in model
assert "'complete_capacity_accepted':False" in model
assert "if not permitted:values=None" in model
assert "status='synthetic_local_geometry' if invocation.synthetic" in model
assert "if kind" not in model  # No alternate unchecked interpreter/decoder branch.
assert "need(integer(value['rebase'])==-low" in model
assert "normalized=checked_add(offset,a['rebase'])" in model
assert 'normalized%align==0' in model
assert "origin[right]=proposed" in model
assert "finish=checked_add(start,value['capacity'],I64_MIN,I64_MAX)" in model
assert model.count('%') == 1  # Only rebased local alignment,none on same-base graph origins.
assert "obj(value,'id base entry_min entry_max rebase reviewed_rebase evidence')" in model

# Independent arithmetic: do not import or call producer fixture/verifier.
# Both region offsets normalize to zero in their own arena. A same-base delta1
# makes their physical start separation incongruent with both8-byte alignments.
r_offset, c_offset, delta = -13624, -13640, 1
assert (r_offset + 13624) % 8 == (c_offset + 13640) % 8 == 0
physical_separation = delta + c_offset - r_offset
assert physical_separation == -15 and physical_separation % 8 != 0
witness = {'schema': 1, 'status': 'SOURCE_DEDUCTION_AND_INDEPENDENT_INTEGER_WITNESS_NOT_EXECUTED_AGAINST_VERIFIER',
    'R': {'arena': 'A_R', 'offset': r_offset, 'entry_min': r_offset, 'rebase': 13624, 'alignment': 8, 'capacity': 13624, 'end': 4},
    'C': {'arena': 'A_C', 'offset': c_offset, 'entry_min': c_offset, 'rebase': 13640, 'alignment': 8, 'capacity': 13640, 'begin': 3},
    'relation': {'left': 'A_R', 'right': 'A_C', 'kind': 'same_base', 'right_minus_left': delta, 'reviewed': True},
    'same_live_phase': 3, 'local_normalized_starts': [0, 0], 'C_start_minus_R_start': physical_separation,
    'separation_mod_alignment': physical_separation % 8,
    'source_case_specification': 'Start with the current synthetic baseline;extend R.end to4 as existingP10does;replace just A_R/A_C disjoint pair with the shown same-base delta1,keeping all other pins/capture/approval joins freshly bound by synthetic helper. Existing normalized local checks and graph/union checks lack the alignment contradiction guard.',
    'required_result_after_fix': 'Contradictory aligned starts refuse,or missing physical alignment evidence suppresses all numeric local unions;never a closed numeric local union.',
    'not_claimed': 'No producer import,syntax parse,test,fixture construction or actual verifier result occurred.'}
finding = {'id': 'R01', 'priority': 1, 'file': 'source/region_certificate.py', 'source_lines': [302, 306, 315, 328, 329, 433, 441, 455],
    'issue': 'Alignment is checked relative to each independently rebased arena origin,not the physical symbolic base. Same-base origin deltas are not checked against region alignment congruences. Two8-aligned extents can pass their local normalized-zero checks while a reviewed delta1 makes their start separation odd,which is mathematically inconsistent.',
    'consequence': 'An internally contradictory certificate can reach the closed numeric local union source path. External approval still gates actual geometry and whole capacity remains false,but arithmetic guards do not validate the alignment claim.',
    'minimum_fix': 'Tie alignment to the physical symbolic base plus signed offset and propagate/check congruences through same-base deltas. A numerical rebase alone is not base-alignment evidence. Refuse contradictory alignments;unsupported/unknown alignment facts suppress local numeric output. Preserve checked range/end arithmetic and independent semantic approval.',
    'controls': ['R/C both8-aligned with delta+1 and delta-1 must refuse.', 'Consistent delta0/delta8 and evidenced aligned negative-SP rebase remain positive.',
                 'A rebased-zero offset must not acquire stronger alignment than the physical base supports.'],
    'source_deduction_only': True}
after = {}
for name, path in paths.items():
    raw = path.read_bytes()
    after[name] = {'bytes': len(raw), 'sha256': sha(raw)}
assert after == inputs
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_REGION_VERIFIER_SOURCE_REVIEW_PHYSICAL_ALIGNMENT_CORRECTION_REQUIRED',
    'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 11,
    'host_plan_sha256': sha((P / 'host-test-plan.json').read_bytes()), 'source_files': manifest['source_files'],
    'source146_binding': manifest['source146_binding'], 'declared_synthetic_methods': 16,
    'findings': [finding], 'synthetic_host_test_release_recommended': False,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
                    'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()), 'checked_input_members': len(inputs),
    'before_after_input_tree_sha256': sha(canonical(inputs)), 'before_after_custody_equal': True,
    'positives': ['External Invocation approval digest binds exact certificate/map/all inputs,independent semantic review seal,and accepted capture/diagnostic custody.',
        'Bounded saved memory/path reader,strict records,source146/four-target binding,source/MIR scopes and full warning-stream equality are explicit.',
        'Carrier/child/outer widths,phase coverage,frame SP continuity/extrema and unknown relation suppression remain separate from transitive/backing obligations.',
        'Synthetic provenance is explicit;actual candidates without approval have no numeric union;all output whole-capacity flags remainfalse.',
        'Single synthetic test plan is confined to fresh root-owned command/tmp and no compiler/capture/product process.'],
    'geometry_witness_executed_against_producer': False,
    'target_module_import_syntax_parse_compile_test_actual_capture_saved_input_or_runtime_execution': 0,
    'native_UI_capture_device_network_process_inventory_actions': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_capacity_prices_backings_root_funding_product_GA_accepted': False,
    'cleanup': 'No target import,child or command/build artifact created;no cleanup owed.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
for name, value in [('review-result.json', report), ('alignment-witness.json', witness), ('checked-inputs.json', inputs)]:
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'declared_synthetic_methods', 'checked_input_members', 'synthetic_host_test_release_recommended', 'elapsed_seconds')}))
