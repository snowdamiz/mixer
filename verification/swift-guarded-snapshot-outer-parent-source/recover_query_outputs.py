#!/usr/bin/env python3
"""Recover already-emitted compiler evidence after receipt error; never compile."""
import json
import re
import shutil
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from prepare import HERE, sha, write

OUT = HERE/'commands/compiler-only-query'
WORK = HERE/'owned-work/compiler-only-query'

def main():
    assert not (OUT/'receipt.json').exists(), 'no replacement recovery'
    context = json.loads((OUT/'context.json').read_bytes())
    original = OUT/'runner-original.py'
    assert original.is_file() and WORK.is_dir()
    stdout, stderr = (OUT/'stdout').read_bytes(), (OUT/'stderr').read_bytes()
    receipt = dict(context, compiler_invocations=1, compiler_retries=0,
        actual_runtime=False, compiler_exit_code=None, elapsed_seconds=None,
        unretained_facts=['compiler exit code', 'compiler elapsed seconds', 'owned process group id/absence'],
        child_wait='original Popen.communicate returned before receipt error; child reaped by that call',
        receipt_failure="TypeError: dict() got multiple values for keyword argument 'product_or_test_runtime'",
        original_runner_sha256=sha(original.read_bytes()),
        recovery_sha256=sha(Path(__file__).read_bytes()),
        stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
        compiler_outputs_emitted=False, metadata_status_pass_claim=False,
        compile_success=False, artifacts=[])
    try:
        for name in ['query.rmeta', 'query.mir']:
            path = WORK/name
            receipt['artifacts'].append(dict(path=name, bytes=path.stat().st_size,
                sha256=sha(path.read_bytes()), retained=False))
        receipt['compiler_outputs_emitted'] = True
        mir = (WORK/'query.mir').read_text()
        names_to_retain = ['selected_outer_request_v1', 'borrow_original_diagnostics_once_v1',
            'observe_borrowed_originals_v1', 'run_selected_one_fixture_outer_v1',
            'consume_outer_request_v1', 'outer_parent_layout_query_v1',
            'outer_parent_account_layout_query_v1']
        selected = [body for body in re.split(r'(?=^fn |^const |^static )', mir, flags=re.M)
            if any(body.startswith('fn '+name+'(') for name in names_to_retain)]
        assert len(selected) == len(names_to_retain), 'all exact private outer/query MIR bodies required'
        (OUT/'outer-and-query.mir').write_text(''.join(selected))
        layouts = []
        for file_name, fn_name in [('query-layout.inc.rs', 'outer_parent_layout_query_v1'),
                                   ('query-account-layout.inc.rs', 'outer_parent_account_layout_query_v1')]:
            decl = (HERE/file_name).read_text()
            names = re.findall(r'\s+_(\w+): \[u8;', decl)
            header = next(body.split('\n',1)[0] for body in selected if body.startswith('fn '+fn_name+'('))
            values = [int(n) for n in re.findall(r'_\d+: \[u8; (\d+)\]', header)]
            assert len(names) == len(values), (names, values)
            layouts += [dict(query=name, observed=value) for name, value in zip(names, values)]
        write('commands/compiler-only-query/layouts.json', dict(schema=1, rows=layouts,
            observed_by='concrete array lengths in retained exact rustc MIR query signatures',
            target='aarch64-apple-darwin', compiler_only=True,
            compiler_exit_status_not_retained=True,
            actual_native_or_dynamic_backing_bound=False))
        receipt['retained_outer_and_query_MIR_bodies'] = len(selected)
        receipt['retained_layout_observations'] = len(layouts)
        receipt['postprocess_success'] = True
    except Exception as error:
        receipt['postprocess_error'] = str(error)
        receipt['postprocess_success'] = False
    finally:
        shutil.rmtree(WORK)
        if WORK.parent.exists() and not any(WORK.parent.iterdir()): WORK.parent.rmdir()
        receipt['owned_scratch_removed'] = not WORK.exists()
        write('commands/compiler-only-query/receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))
    if not receipt['postprocess_success']: sys.exit(1)

if __name__ == '__main__': main()
