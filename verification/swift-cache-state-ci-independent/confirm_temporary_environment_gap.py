#!/usr/bin/env python3
"""Actual child through exact candidate Commands; no normal qualification run."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).absolute().parent

def main():
    runner = HERE / 'candidate-copy/check_cache_state.py'
    digest = hashlib.sha256(runner.read_bytes()).hexdigest()
    assert digest == '92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d'
    spec = importlib.util.spec_from_file_location('reviewed_candidate_tmp_gap', runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = HERE / 'evidence/candidate-temporary-environment-gap'
    out.mkdir(exist_ok=False)
    receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runner_sha256': digest, 'commands': [], 'normal_qualification_started': False}
    command = module.Commands(out, receipt, time.monotonic() + 30)
    code = 'import json,os;print(json.dumps({k:os.environ.get(k) for k in ["TMPDIR","TMP","TEMP","RUSTUP_AUTO_INSTALL"]},sort_keys=True))'
    text, _, row = command.run('actual-unoverridden-child-environment', [sys.executable, '-B', '-c', code], out)
    observed = json.loads(text)
    assert row['exit'] == 0 and row['child_returned'] and row['owned_group_gone']
    assert observed == {'TMPDIR': None, 'TMP': None, 'TEMP': None, 'RUSTUP_AUTO_INSTALL': '0'}
    receipt.update(observed_environment=observed,
        owned_TMP_contract_passed=False,
        finding='TMPDIR/TMP/TEMP are absent for candidate command calls without env overrides; compiler/sysroot/identity/API/positive/Git call sites use that path',
        required_repair='Set all three temporary variables to an already-created owned scratch temp directory for every child, including tool selection and compilation; retain explicit per-test overrides and add actual unoverridden-child control',
        child_reaped=True, owned_group_gone=True, normal_run_required_after_repair=True,
        candidate_modified=False, native_runtime_or_process_inventory_started=False)
    command.save()
    print('CONFIRMED contract failure: actual owned child TMPDIR/TMP/TEMP=null; no full qualification run started')

if __name__ == '__main__':
    main()
