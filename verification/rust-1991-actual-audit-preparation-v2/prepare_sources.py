#!/usr/bin/env python3
"""Build only this preparation's source/data manifests; never import subjects."""
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def raw(path):
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise RuntimeError('Source symlink refused')
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise RuntimeError('Bounded regular source required')
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(base, path):
    data = raw(path)
    return {'path': path.relative_to(base).as_posix(), 'bytes': len(data), 'sha256': sha(data)}


def tree(rows):
    return sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


def write(name, value):
    target = HERE / name
    if target.is_symlink() or '/' in name:
        raise RuntimeError('Owned regular output required')
    target.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def main():
    parsed = {}
    for name in ('audit_actual.py', 'deny_runtime.py', 'controls.py', 'prepare_sources.py'):
        source = raw(HERE / name)
        ast.parse(source, filename=str(HERE / name))
        parsed[name] = {'bytes': len(source), 'sha256': sha(source), 'ast_parse': 'passed', 'execution_by_this_builder': False}
    module = ast.parse(raw(HERE / 'audit_actual.py'))
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in module.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {'PINS', 'BOUNDS', 'JSON_LIMITS'}}
    template = json.loads(raw(HERE / 'root-binding.template.json'))
    if not (template['root_selected'] is False and template['status'] == 'unselected-no-result'
            and all(template[k] is None for k in ('revision', 'git_tree', 'run_id', 'run_attempt', 'job_id'))
            and all(value is None for value in template['artifact'].values())
            and all(value is None for ref in template['evidence'].values() for value in ref.values())
            and template['pins'] == constants['PINS'] and all(v is False for v in template['authority'].values())):
        raise RuntimeError('Preparation template acquired result/authority')
    if set(template['evidence']) != {'delivery', 'run', 'job', 'artifact', 'acquisition'}:
        raise RuntimeError('Acquisition reference absent')
    json.loads(raw(HERE / 'root-binding.schema.json'))
    adoption = ROOT / 'verification/envelope-rust-1991-default-ci-adoption'
    review = ROOT / 'verification/envelope-rust-1991-default-ci-adoption-review'
    if sha(raw(adoption / 'seal.json')) != constants['PINS']['adoption_seal_sha256']:
        raise RuntimeError('Frozen adoption differs')
    if sha(raw(review / 'seal.json')) != constants['PINS']['implementation_review_seal_sha256']:
        raise RuntimeError('Frozen independent review differs')
    if sha(raw(ROOT / '.github/workflows/verify.yml')) != constants['PINS']['workflow_sha256']:
        raise RuntimeError('Installed workflow differs')
    paths = {ROOT / '.github/workflows/verify.yml', adoption / 'seal.json', review / 'seal.json',
             ROOT / 'verification/rust-1991-qualification-design/DESIGN.md',
             ROOT / 'verification/engine-ci-2c751cbb-swift-failure/inspect_artifact.py',
             ROOT / 'verification/envelope-ordinary-actual-review/raw/audit_body.py',
             ROOT / 'verification/envelope-ordinary-actual-review/review.json'}
    for packet in (adoption, review):
        sealed = json.loads(raw(packet / 'seal.json'))
        for expected in sealed['members']:
            source = packet / expected['path']
            if row(packet, source) != expected:
                raise RuntimeError('Frozen packet member differs')
            paths.add(source)
    dependencies = json.loads(raw(adoption / 'dependencies.json'))
    for expected in dependencies['members']:
        source = ROOT / expected['path']
        if row(ROOT, source) != expected:
            raise RuntimeError('Frozen dependency differs')
        paths.add(source)
    rows = sorted([row(ROOT, path) for path in paths], key=lambda value: value['path'])
    old = ROOT / 'verification/rust-1991-actual-audit-preparation'
    if raw(HERE / 'source-bindings.json') != raw(old / 'source-bindings.json') or sha(raw(HERE / 'source-bindings.json')) != 'b68e6aa09a6ca0b898777ae1ec52bbf53f2c33f9207c3f90832a89147a2c9299':
        raise RuntimeError('Original145member source closure changed')
    if json.loads(raw(HERE / 'source-bindings.json'))['members'] != rows:
        raise RuntimeError('Current immutable source closure differs')
    if rows != sorted([row(ROOT, path) for path in paths], key=lambda value: value['path']):
        raise RuntimeError('Source closure changed during preparation')
    preserved = []
    source_review = ROOT / 'verification/rust-1991-actual-audit-source-review'
    for packet, seal_name, expected_sha in (
            (old, 'preparation-seal.json', '5302dd2551e58ce993004e4888b233df9a026bbb8f12e071d444e6dbc2bd9620'),
            (source_review, 'seal.json', 'f0aed535b14406574471b18fd8426e914ec8375657331bc97175061183aea487')):
        if sha(raw(packet / seal_name)) != expected_sha:
            raise RuntimeError('Preserved baseline/review seal differs')
        sealed = json.loads(raw(packet / seal_name))
        preserved.append(row(ROOT, packet / seal_name))
        for expected in sealed['members']:
            path = packet / expected['path']
            if row(packet, path) != expected:
                raise RuntimeError('Preserved baseline/review member differs')
            preserved.append(row(ROOT, path))
    preserved.sort(key=lambda value: value['path'])
    write('preservation-bindings.json', {'schema': 1, 'scope': 'Original v1 nine members/seal and independent source review preserved byte-identical',
        'member_count': len(preserved), 'total_bytes': sum(value['bytes'] for value in preserved),
        'tree_sha256': tree(preserved), 'members': preserved})
    controls_bytes = raw(HERE / 'local/control-result.json')
    controls = json.loads(controls_bytes)
    actual_sources = {name: sha(raw(HERE / name)) for name in ('audit_actual.py', 'deny_runtime.py', 'controls.py')}
    if not (controls['tests'] == 27 and controls['passed'] is True and controls['outer_denied'] == []
            and controls['source_before'] == controls['source_after'] == actual_sources
            and all(controls['scratch_cleanup'].values())):
        raise RuntimeError('Controls incomplete, failed, changed or unclean')
    (HERE / 'controls.json').write_bytes(controls_bytes)
    write('preparation.json', {'schema': 1, 'status': 'inert-source-data-preparation-only',
        'actual_result_exists_in_this_packet': False, 'root_result_binding_selected': False,
        'actual_audit_main_invocations': 0, 'checked_in_envelope_subject_imports': 0,
        'auditor_and_guard_control_imports': 2, 'guard_installations_for_alias_metadata_control': 1,
        'original_33_control_suite_reruns': 0,
        'compiler_product_oracle_native_ui_invocations': 0, 'network_git_gh_acquisition_process_probe_or_signal_operations': 0,
        'python': {'executable': sys.executable, 'version': sys.version},
        'read_tools_observed': {'rg': '15.2.0 (rev e89fff89ac)', 'shasum': '6.02'},
        'validation': {'kind': 'This builder uses AST/source data only; separate27inert controls imported new auditor/guard under an outer active-API deny guard',
                       'sources': parsed, 'source_closure_rehashed_before_after': True, 'source_members': len(rows)},
        'controls': {'command': 'python3 -I -B -S verification/rust-1991-actual-audit-preparation-v2/controls.py',
            'attempts': 1, 'tests': controls['tests'], 'passed': controls['passed'], 'exit': 0,
            'evidence_sha256': sha(controls_bytes), 'outer_denied': controls['outer_denied'],
            'stdout': row(HERE, HERE / 'local/controls-attempt-1.stdout'),
            'stderr': row(HERE, HERE / 'local/controls-attempt-1.stderr'), 'cleanup': controls['scratch_cleanup']},
        'instructions_observed_as_data': [row(ROOT, ROOT / name) for name in ('AGENTS.md', 'PLAN.md')],
        'required_future_checks': ['independent source review of prepared auditor/facade/guard',
            'separate root selection of one exact first delivered result and data-audit invocation',
            'actual source/job/selection/compiler/archive/run binding and all40command data review',
            'root external custody/lease closure', 'separate root immutable acceptance if complete'],
        'bounds': constants['BOUNDS'], 'json_limits': constants['JSON_LIMITS'], 'pins': constants['PINS'], 'runtime_or_release_allowance': False,
        'original_source_bindings_sha256': sha(raw(HERE / 'source-bindings.json')),
        'preserved_members': len(preserved),
        'review_findings_addressed': ['F1 bounded parser/check/report and early archive closure', 'F2 original/effective/local ZIP names and Unicode extras',
                                    'F3 underlying posix/_signal/_socket/_ctypes aliases and open wrappers', 'F4 required normalized acquisition reference'],
        'preparation_command': 'python3 -I -B -S verification/rust-1991-actual-audit-preparation-v2/prepare_sources.py',
        'command_argv': sys.argv,
        'prior_source_data_builder': 'V2 copied verified v1 as data, wrote repair sources/template/schema and AST-parsed sources; the only behavioral run is the recorded27control invocation'})
    names = ['.gitignore', 'README.md', 'audit_actual.py', 'deny_runtime.py', 'prepare_sources.py', 'controls.py', 'controls.json',
             'acquisition.template.json', 'preparation.json', 'preservation-bindings.json', 'root-binding.schema.json', 'root-binding.template.json', 'source-bindings.json']
    own_rows = [row(HERE, HERE / name) for name in sorted(names)]
    write('preparation-seal.json', {'schema': 1,
        'scope': 'V2 source/parser/ZIP-name/fake-API preparation and27inert controls only; no actual result or execution selection; v1 preserved; local outputs excluded',
        'member_count': len(own_rows), 'total_bytes': sum(value['bytes'] for value in own_rows), 'tree_sha256': tree(own_rows), 'members': own_rows})
    print(json.dumps({'ast_syntax_sources': parsed, 'bound_source_members': len(rows), 'source_tree_sha256': tree(rows),
        'preparation_members': len(own_rows), 'preparation_seal_sha256': sha(raw(HERE / 'preparation-seal.json')),
        'actual_audit_main_invocations': 0, 'checked_in_envelope_subject_imports': 0,
        'inert_controls': controls['tests'], 'preserved_members': len(preserved)}, sort_keys=True))


if __name__ == '__main__':
    main()
