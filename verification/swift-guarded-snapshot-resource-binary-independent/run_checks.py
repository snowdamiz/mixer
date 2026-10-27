"""Replay this independent review, optionally retaining its own outputs only."""
import contextlib
from datetime import datetime, timezone
import io
import json
import sys
import time

sys.dont_write_bytecode = True
import audit
import test_controls


def main(write=False):
    started = datetime.now(timezone.utc).isoformat()
    begin = time.monotonic()
    candidate_before = audit.sha((audit.C / 'seal.json').read_bytes())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result, _ = audit.main()
        controls = test_controls.main()
    assert candidate_before == audit.sha((audit.C / 'seal.json').read_bytes()) == audit.SEAL_SHA
    assert not (audit.D / '__pycache__').exists()
    summary = dict(status='passed', source_members=result['source_members'],
                   LLVM_functions=result['LLVM']['selected_functions'],
                   native_functions=len(result['native_functions']),
                   native_instruction_records=result['instruction_records'],
                   native_relocation_records=result['relocation_records'],
                   native_combined_checks=result['combined_checks'],
                   original_dataflow_cases=len(result['dataflow_cases']),
                   additional_dataflow_cases=len(result['additional_dataflow_cases']),
                   independent_hostile_controls=controls['independent_mutations'],
                   producer_original_controls=controls['producer_original_controls']['hostile_controls'],
                   preserved_helper_coverage_findings=len(controls['preserved_producer_helper_coverage_findings']),
                   native_or_product_execution=False)
    output = buf.getvalue() + json.dumps(summary, sort_keys=True) + '\n'
    receipt = dict(schema=1, started_at=started, completed_at=datetime.now(timezone.utc).isoformat(),
                   argv=[sys.executable, '-B', str(audit.D / 'run_checks.py')] + (['--write'] if write else []),
                   cwd=str(audit.R), python_version=sys.version, python_executable=sys.executable,
                   source_tree_sha256=audit.TREE, host_tree_sha256=audit.HOST,
                   candidate_seal_sha256=candidate_before, release_sha256=audit.RELEASE_SHA,
                   elapsed_seconds=time.monotonic() - begin, exit_code=0,
                   stdout=dict(bytes=len(output.encode()), sha256=audit.sha(output.encode())),
                   stderr=dict(bytes=0, sha256=audit.sha(b'')),
                   commands_spawned_by_reviewer=0, compiler_or_disassembler_invocations=0,
                   frozen_inputs_or_Git_or_toolchain_changed=False,
                   process_inventory_or_other_process_mutations=False,
                   new_UI_capture_simulator_emulator_or_native_runtime=False,
                   scope='Offline Python review of frozen LLVM/source/archive bytes and in-memory mutations; no runtime or final executable binding.',
                   review_script_sha256=audit.sha((audit.D / 'audit.py').read_bytes()),
                   control_script_sha256=audit.sha((audit.D / 'test_controls.py').read_bytes()),
                   runner_sha256=audit.sha((audit.D / 'run_checks.py').read_bytes()))
    if write:
        for name, data in [('audit.json', result), ('controls.json', controls),
                           ('command-receipt.json', receipt), ('summary.json', summary)]:
            (audit.D / name).write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
        (audit.D / 'command.stdout').write_text(output)
        (audit.D / 'command.stderr').write_bytes(b'')
    else:
        assert result == audit.load(audit.D / 'audit.json')
        assert controls == audit.load(audit.D / 'controls.json')
        assert summary == audit.load(audit.D / 'summary.json')
    print(output, end='')


if __name__ == '__main__':
    main('--write' in sys.argv)
