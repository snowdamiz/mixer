#!/usr/bin/env python3
"""Source/delta/hash review and independent algebra only; no target execution."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
P = R / 'verification/swift-root-bound-dispatch-physical-evidence-v2'
OLD = R / 'verification/swift-root-bound-dispatch-physical-evidence-v1'
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
    row = {'bytes': len(raw), 'sha256': sha(raw)}
    assert name not in inputs or inputs[name] == row
    inputs[name], paths[name] = row, path
    return raw


def load(path, expected=None):
    raw = read(path, expected)
    assert len(raw) <= 1048576
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def pin(row, base=R):
    assert len(read(base / row['path'], row['sha256'])) == row['bytes']


sealed = load(P / 'seal.json', '866d0058d5f54116f3459bc0fcf4a3afe6437e30f796c69d3759d2de8893bedc')
assert len(sealed['members']) == sealed['member_count'] == 12
assert len({row['path'] for row in sealed['members']}) == 12
assert sha(canonical(sealed['members'])) == sealed['tree_sha256'] == 'a8f5cd09364bc9146508a4cdab1ac76f5f9496110a6c6ed44854ee069bc04137'
for row in sealed['members']:
    assert not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
    pin(row, P)
assert not any(path.is_symlink() for path in P.rglob('*'))
assert sorted(path.relative_to(P).as_posix() for path in P.rglob('*') if path.is_file()) == sorted([row['path'] for row in sealed['members']] + ['seal.json'])
manifest = load(P / 'input-manifest.json')
for row in manifest['inputs'] + manifest['source_files']:
    pin(row)
old_seal = load(OLD / 'seal.json', '674fcb6b158055b207c8f2afd1e66e56f06910ec80229f706cab3e29c679e474')
for row in old_seal['members']:
    pin(row, OLD)
review_dir = R / 'verification/swift-root-bound-dispatch-physical-evidence-independent'
review_seal = load(review_dir / 'seal.json', '6dcf38a8030b3639d87b08a5aacec51a9aee5a45cb25a36d9cbd7d4e280106d4')
for row in review_seal['members']:
    pin(row, review_dir)
model = read(P / 'source/region_certificate.py', 'dbddc2d1385eecd545a2d0c9cd9d543d0d44bb5b82609040c9a6fd69a882433b').decode()
tests = read(P / 'source/tests_region_certificate.py', 'd7a240c39c10306ef8c5bd5e941ab0f283f47a6d1f95279709361c8d04d5e954').decode()
old_model = read(OLD / 'source/region_certificate.py').decode()
old_tests = read(OLD / 'source/tests_region_certificate.py').decode()
delta = ''.join(difflib.unified_diff(old_model.splitlines(True), model.splitlines(True),
    fromfile='immutable-v1/source/region_certificate.py', tofile='v2/source/region_certificate.py'))
delta += ''.join(difflib.unified_diff(old_tests.splitlines(True), tests.splitlines(True),
    fromfile='immutable-v1/source/tests_region_certificate.py', tofile='v2/source/tests_region_certificate.py'))
assert delta.encode() == read(P / 'source-delta.patch')
# All trust/custody/diagnostic/source helpers and final approval/output behavior
# are byte-identical. Only the alignment geometry/helper and controls changed.
assert model[:model.index('def merge_congruence(')] == old_model[:old_model.index('def geometry(')]
assert model[model.index('def _verify('):] == old_model[old_model.index('def _verify('):]
assert 'normalized%align' not in model
merge = model[model.index('def merge_congruence('):model.index('def geometry(')]
assert '(residue-old_residue)%min(modulus,old_modulus)==0' in merge
assert 'return (modulus,residue) if modulus>old_modulus else current' in merge
assert 'physical_alignment' in model and "obj(physical,'modulus residue reviewed evidence')" in model
assert "modulus&(modulus-1)==0" in model
assert "integer(physical['residue'],0,modulus-1)" in model
assert "known={};required={};starts={}" in model
assert "residue=(fact['residue']-origin[name]%modulus)%modulus" in model
assert "required[group]=merge_congruence(required.get(group),modulus,residue)" in model
assert "if group in known:merge_congruence(known[group],modulus,residue)" in model
assert "if proof is None or proof[0]<modulus:unknown('local','unsupported physical alignment '+identity)" in model
assert "else:need(proof[1]%modulus==residue,'contradictory physical alignment')" in model
assert "arena=value['arena'];start=starts[value['id']]" in model
assert "local_closed=not any(item['scope']=='local' for item in missing)" in model
assert "return phase_bytes if local_closed else None,missing" in model
names = re.findall(r'^    def (test_p\d+_\w+)\(', tests, re.M)
old_names = re.findall(r'^    def (test_p\d+_\w+)\(', old_tests, re.M)
families = load(P / 'test-family-map.json')['families']
assert len(names) == len(set(names)) == 16 and names == old_names == [row['test_method'] for row in families]
assert all(row['executed'] is False for row in families)
for source in ('for delta in (-1,1):', 'for delta in (0,8):', "arena(case,'A_C')['physical_alignment']=None;self.closed(case)",
    "arena(case,'A_R')['physical_alignment']=None;self.incomplete(case)",
    "region(case,'R')['alignment']=16;self.incomplete(case)",
    ".update(modulus=16,residue=8);self.closed(case)",
    "arena(case,'A_R').update(entry_min=-13625,rebase=13625);self.closed(case)"):
    assert source in tests, source

# Independent algebraic obligations,not tests of producer functions. If base C
# equals base R+d, two8-aligned starts require d-16==0(mod8). A known R base
# congruence supplies C only through an independently reviewed relation.
algebra = []
for delta_value in (-1, 0, 1, 8):
    separation = delta_value - 13640 + 13624
    compatible = separation % 8 == 0
    assert compatible == (delta_value in (0, 8))
    algebra.append({'base_delta': delta_value, 'C_start_minus_R_start': separation,
                    'two8aligned_starts_compatible': compatible})
assert (-(-13624)) % 16 == 8
assert (8 + -13624) % 16 == 0 and (0 + -13624) % 16 != 0
plan = load(P / 'host-test-plan.json', '83fdb4bae803e4f0374307f1302e2ecf4a67c5b37edfbcbc5f97faef1e44786e')
old_plan = load(OLD / 'host-test-plan.json', '57f50c47eee9033e2bcaa88f5040087ffc0947dc68c73ae21a6f79be1ae01b9e')
changed = {'argv', 'argv_sha256_canonical_JSON', 'environment', 'owned_outputs', 'root_release_required', 'source_files'}
assert all(plan[key] == value for key, value in old_plan.items() if key not in changed)
assert plan['argv'] == [plan['python_tool']['path'], '-B', str(P / 'source/tests_region_certificate.py')]
assert sha(canonical(plan['argv'])) == plan['argv_sha256_canonical_JSON']
assert plan['source_files'] == manifest['source_files']
pin(plan['python_tool'])
assert plan['environment'] == {**old_plan['environment'], 'TMPDIR': str(P / 'command/tmp')}
assert plan['owned_outputs'] == {**old_plan['owned_outputs'], 'directory': str(P / 'command'), 'temporary_directory': str(P / 'command/tmp')}
assert plan['root_release_required'] == {**old_plan['root_release_required'],
    'path': 'verification/swift-semantic-adapter-root-review/dispatch-physical-verifier-v2-host-release.json'}
assert plan['bounds']['wall_seconds'] == 55 and plan['bounds']['python_test_invocations'] == 1 and plan['bounds']['automatic_retries'] == 0
assert plan['owned_outputs']['root_precreates_fresh_directory_and_tmp_only'] is True
try:
    (P / 'command').lstat()
except FileNotFoundError:
    pass
else:
    raise AssertionError('command output must be fresh')
after = {}
for name, path in paths.items():
    raw = path.read_bytes()
    after[name] = {'bytes': len(raw), 'sha256': sha(raw)}
assert after == inputs
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_V2_REGION_VERIFIER_SOURCE_REVIEW_R01_CORRECTED_SINGLE_SYNTHETIC_RUN_RECOMMENDED',
    'producer_seal_sha256': sha((P / 'seal.json').read_bytes()), 'producer_members_verified': 12,
    'producer_tree_sha256': sealed['tree_sha256'], 'host_plan_sha256': sha((P / 'host-test-plan.json').read_bytes()),
    'source_files': manifest['source_files'], 'source146_binding': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'R01_status': 'CORRECTED_BY_SOURCE_REVIEW_NOT_EXECUTED', 'findings': [],
    'synthetic_host_test_release_recommended': True, 'declared_synthetic_methods': 16,
    'recommendation': 'Root may release exactly one pinned synthetic Python-B invocation,with fresh root-owned command/tmp,44s work/55s cumulative bounds,no retries and no actual saved-input/capture parse. Require all16names/exit/output/custody/inventory/cleanup/posthash/cutoff evidence.',
    'correction_reasoning': ['Reviewed base congruences translate by signed origin and merge consistently at component base.',
        'Region alignment requirements are separate constraints;they cannot strengthen the known supporting evidence.',
        'Contradictory +/-1 relative starts refuse even when both base facts are missing;compatible requirements alone do not permit numeric output.',
        'Known support can propagate through a reviewed neighbor relation;null/unreviewed/modulo1/weak facts leave local output suppressed.',
        'Geometry widths use physical signed starts;changing numerical rebase alone no longer changes alignment validity.'],
    'no_regression_source_checks': ['Exact complete source delta reproduced.', 'All pre-geometry trust/custody/source/diagnostic helpers byte-identical.',
        'Final verifier/approval/output behavior byte-identical.', 'All16method names retained;only alignment fixture facts andP09/P10subcases added.',
        'One synthetic-only host plan retains prior bounds and all pending scope flags.'],
    'checked_input_members': len(inputs), 'before_after_input_tree_sha256': sha(canonical(inputs)), 'before_after_custody_equal': True,
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R), 'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()), 'sha256': sha(Path(sys.executable).resolve().read_bytes())},
    'review_script_sha256': sha(Path(__file__).read_bytes()),
    'target_import_syntax_parse_compile_tests_actual_saved_input_capture_or_runtime_execution': 0,
    'native_UI_capture_devices_network_process_inventory_actions': 0,
    'canonical_product_metadata_commit_push_actions': 0,
    'physical_capacity_prices_backings_root_funding_product_GA_accepted': False,
    'limits': ['No syntax or passing test result claimed;prepared subcases are source-reviewed only.',
        'Physical facts still require whole-function semantics review and external root approval;no symbolic label or synthetic fixture proves actual native geometry.',
        'Transitive/destruction/backing/funding obligations stay missing;all output local_geometry_only and whole capacityfalse.',
        'Original/v1 packets and R01 review remain unchanged.'],
    'cleanup': 'No selected module/child or command artifact created;no cleanup owed.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
for name, value in [('review-result.json', report), ('alignment-algebra.json', {'status': 'INDEPENDENT_ARITHMETIC_ONLY_NO_PRODUCER_EXECUTION', 'cases': algebra}), ('checked-inputs.json', inputs)]:
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'producer_members_verified', 'declared_synthetic_methods', 'checked_input_members', 'synthetic_host_test_release_recommended', 'elapsed_seconds')}))
