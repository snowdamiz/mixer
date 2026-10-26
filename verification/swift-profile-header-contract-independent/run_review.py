#!/usr/bin/env python3
"""Run only authored offline Python review; retain every attempt without overwrite."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    runs = OUT / 'commands'
    runs.mkdir(exist_ok=True)
    index = 1
    while (runs / f'run{index:03}').exists():
        index += 1
    run = runs / f'run{index:03}'
    run.mkdir()
    scripts_dir = run / 'scripts'
    scripts_dir.mkdir()
    script_names = ['audit_inputs.py', 'controls.py', 'run_review.py']
    for name in script_names:
        (scripts_dir / name).write_bytes((OUT / name).read_bytes())
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                              capture_output=True, timeout=15, check=True)
    revision_tree = subprocess.run(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT,
                                   capture_output=True, timeout=15, check=True)
    results = []
    for name, argv in [('custody', [sys.executable, '-B', str(OUT / 'audit_inputs.py')]),
                       ('controls', [sys.executable, '-B', str(OUT / 'controls.py'), '-v'])]:
        started = time.monotonic()
        at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        (run / f'{name}.stdout').write_bytes(completed.stdout)
        (run / f'{name}.stderr').write_bytes(completed.stderr)
        results.append({'name': name, 'argv': argv, 'cwd': str(ROOT),
                        'at': at, 'elapsed_seconds': time.monotonic() - started,
                        'timeout_seconds': 60, 'exit_code': completed.returncode,
                        'stdout': {'bytes': len(completed.stdout), 'sha256': sha(completed.stdout)},
                        'stderr': {'bytes': len(completed.stderr), 'sha256': sha(completed.stderr)}})
    scripts = []
    for name in script_names:
        raw = (OUT / name).read_bytes()
        scripts.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    receipt = {'schema': 1,
               'scope': 'Independent offline contract arithmetic/byte encoding/source witnesses and custody; no product import/compile/execution',
               'python_executable': sys.executable,
               'python_executable_resolved': str(Path(sys.executable).resolve()),
               'python_executable_sha256': sha(Path(sys.executable).resolve().read_bytes()),
               'python': sys.version,
               'sys_platform': sys.platform,
               'requested_review_agent': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh',
                                          'fresh_context': True, 'runtime_self_attestation': False},
               'source_revision_context': revision.stdout.decode().strip(),
               'source_revision_tree_context': revision_tree.stdout.decode().strip(),
               'revision_scope': 'Context only; producer seal/member hashes are authoritative',
               'read_only_context_commands': [
                   {'argv': ['git', 'rev-parse', 'HEAD'], 'exit_code': revision.returncode,
                    'stdout': revision.stdout.decode(), 'stderr': revision.stderr.decode()},
                   {'argv': ['git', 'rev-parse', 'HEAD^{tree}'], 'exit_code': revision_tree.returncode,
                    'stdout': revision_tree.stdout.decode(), 'stderr': revision_tree.stderr.decode()}],
               'environment_added': {'PYTHONDONTWRITEBYTECODE': '1'},
               'authored_script_bindings': scripts, 'commands': results,
               'producer_scripts_imported_or_executed': False,
               'Rust_compilation_or_VM_execution': False,
               'native_UI_capture_or_process_inventory': False,
               'limits_deadlines_crypto_dependencies_or_Git_changed': False,
               'all_authority_claims': False}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'run': str(run.relative_to(ROOT)),
                      'exit_codes': {r['name']: r['exit_code'] for r in results},
                      'scope': receipt['scope']}, sort_keys=True))
    for r in results:
        if r['exit_code']:
            print((run / f"{r['name']}.stderr").read_text())
    raise SystemExit(0 if all(r['exit_code'] == 0 for r in results) else 1)


if __name__ == '__main__':
    main()
