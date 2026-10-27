#!/usr/bin/env python3
"""Record bounded pure-data checks only; never invokes a compiler or fixture."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
sys.dont_write_bytecode = True
from prepare import HERE, ROOT, sha, write

def main():
    assert not (HERE/'seal.json').exists(), 'sealed packet reproduction is read-only'
    runs = []
    for name, args in [('source-reproduction', ['prepare.py', '--check-only']),
                       ('owner-control-model', ['test_model.py']),
                       ('MIR-data-reproduction', ['inventory_mir.py', '--check-only'])]:
        folder = HERE/'commands'/name
        assert not folder.exists(), 'do not replace receipts'
        folder.mkdir()
        argv = [sys.executable, str(HERE/args[0]), *args[1:]]
        started = time.monotonic()
        p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30, env={'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1'})
        (folder/'stdout').write_bytes(p.stdout)
        (folder/'stderr').write_bytes(p.stderr)
        value = dict(schema=1, argv=argv, cwd=str(ROOT), timeout_seconds=30,
            exit_code=p.returncode, elapsed_seconds=time.monotonic()-started,
            python=platform.python_version(), child_waited=True,
            script_sha256=sha((HERE/args[0]).read_bytes()),
            stdout_sha256=sha(p.stdout), stderr_sha256=sha(p.stderr),
            candidate_source_tree_sha256=json.loads((HERE/'candidate.json').read_bytes())['new_source_tree_sha256'],
            compiler_invocations=0, fixture_or_product_runtime=False,
            native_UI_capture=False)
        write('commands/'+name+'/receipt.json', value)
        runs.append(dict(name=name, exit_code=p.returncode))
        assert p.returncode == 0, (name, p.stderr.decode())
    checks = dict(schema=1, pure_check_runs=runs, python_test_methods=12,
        synthetic_original_kind_and_token_routes=14,
        premature_release_prefixes=8, premature_token_prefixes=5,
        borrowed_owner_mutation_controls=4, repeated_ownership_controls=4,
        excess_snapshot_control=1, unwind_prefixes=3,
        control_scope='synthetic ownership/control plus exact source/MIR data invariants only',
        compiler_terminal_status_pass=False, real_original_io_or_runtime_cases=0,
        source_work_or_storage_grant=False, operational_native_OTA_FieldLog_GA=False)
    write('checks.json', checks)
    print(json.dumps(checks, sort_keys=True))

if __name__ == '__main__': main()
