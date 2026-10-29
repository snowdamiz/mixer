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
    for name in ('audit_actual.py', 'deny_runtime.py', 'prepare_sources.py'):
        source = raw(HERE / name)
        ast.parse(source, filename=str(HERE / name))
        parsed[name] = {'bytes': len(source), 'sha256': sha(source), 'ast_parse': 'passed', 'executed_as_subject': False}
    module = ast.parse(raw(HERE / 'audit_actual.py'))
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in module.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {'PINS', 'BOUNDS'}}
    template = json.loads(raw(HERE / 'root-binding.template.json'))
    if not (template['root_selected'] is False and template['status'] == 'unselected-no-result'
            and all(template[k] is None for k in ('revision', 'git_tree', 'run_id', 'run_attempt', 'job_id'))
            and all(value is None for value in template['artifact'].values())
            and all(value is None for ref in template['evidence'].values() for value in ref.values())
            and template['pins'] == constants['PINS'] and all(v is False for v in template['authority'].values())):
        raise RuntimeError('Preparation template acquired result/authority')
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
    write('source-bindings.json', {'schema': 1, 'scope': 'Bounded reviewed immutable source/data closure for future data-only audit; not entire working tree',
        'member_count': len(rows), 'total_bytes': sum(value['bytes'] for value in rows), 'tree_sha256': tree(rows), 'members': rows})
    if rows != sorted([row(ROOT, path) for path in paths], key=lambda value: value['path']):
        raise RuntimeError('Source closure changed during preparation')
    write('preparation.json', {'schema': 1, 'status': 'inert-source-data-preparation-only',
        'actual_result_exists_in_this_packet': False, 'root_result_binding_selected': False,
        'audit_invocations': 0, 'guard_invocations': 0, 'subject_imports': 0, 'synthetic_control_reruns': 0,
        'compiler_product_oracle_native_ui_invocations': 0, 'network_git_gh_acquisition_process_probe_or_signal_operations': 0,
        'python': {'executable': sys.executable, 'version': sys.version},
        'read_tools_observed': {'rg': '15.2.0 (rev e89fff89ac)', 'shasum': '6.02'},
        'validation': {'kind': 'standard-library source/data builder; ast.parse only; no auditor/guard/subject import or execution',
                       'sources': parsed, 'source_closure_rehashed_before_after': True, 'source_members': len(rows)},
        'instructions_observed_as_data': [row(ROOT, ROOT / name) for name in ('AGENTS.md', 'PLAN.md')],
        'required_future_checks': ['independent source review of prepared auditor/facade/guard',
            'separate root selection of one exact first delivered result and data-audit invocation',
            'actual source/job/selection/compiler/archive/run binding and all40command data review',
            'root external custody/lease closure', 'separate root immutable acceptance if complete'],
        'bounds': constants['BOUNDS'], 'pins': constants['PINS'], 'runtime_or_release_allowance': False,
        'preparation_command': 'python3 -I -B -S verification/rust-1991-actual-audit-preparation/prepare_sources.py',
        'command_argv': sys.argv,
        'prior_source_data_builder': 'One initial standard-library heredoc builder generated template/schema and initial manifests; no subject/guard/auditor import or execution'})
    names = ['.gitignore', 'README.md', 'audit_actual.py', 'deny_runtime.py', 'prepare_sources.py',
             'preparation.json', 'root-binding.schema.json', 'root-binding.template.json', 'source-bindings.json']
    own_rows = [row(HERE, HERE / name) for name in sorted(names)]
    write('preparation-seal.json', {'schema': 1,
        'scope': 'Inert future audit source/template/schema and source-data preparation only; no actual result or execution selection; local outputs excluded',
        'member_count': len(own_rows), 'total_bytes': sum(value['bytes'] for value in own_rows), 'tree_sha256': tree(own_rows), 'members': own_rows})
    print(json.dumps({'ast_only_sources': parsed, 'bound_source_members': len(rows), 'source_tree_sha256': tree(rows),
        'preparation_members': len(own_rows), 'preparation_seal_sha256': sha(raw(HERE / 'preparation-seal.json')),
        'auditor_invocations': 0, 'guard_invocations': 0, 'subject_imports': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
