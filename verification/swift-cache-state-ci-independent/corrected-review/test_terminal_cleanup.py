#!/usr/bin/env python3
"""Independent shortened expiry controls on the exact first corrected bytes."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
from unittest import mock

HERE = Path(__file__).absolute().parent

def main():
    path = HERE / 'candidate-copy/check_cache_state.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'd30871f94721fff10a3b508670cc9520fc021812b1d39c4655a17420308635a7'
    spec = importlib.util.spec_from_file_location('independent_terminal_cleanup', path)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    output = HERE / 'evidence/terminal-cleanup'
    output.mkdir(exist_ok=False)
    results = []
    for stage in ('postflight', 'retention'):
        state = {'verify_calls': 0, 'cleanup_entered': False, 'after_delayed_work': False}
        original_verify, original_cleanup = candidate.verify_pack, candidate.cleanup
        def verify(base):
            state['verify_calls'] += 1
            if stage == 'postflight' and state['verify_calls'] == 3:
                time.sleep(1)
                state['after_delayed_work'] = True
            return original_verify(base)
        def clean(*args):
            state['cleanup_entered'] = True
            if stage == 'retention':
                time.sleep(1)
                state['after_delayed_work'] = True
            return original_cleanup(*args)
        out = candidate.fresh_output(candidate.RUNS / ('independent-deadline-' + stage))
        with mock.patch.object(candidate, 'CLEANUP_SECONDS', .05), \
             mock.patch.object(candidate, 'verify_pack', verify), \
             mock.patch.object(candidate, 'cleanup', clean):
            code = candidate.execute(out, str(HERE / 'intentionally-missing-compiler'))
        receipt = json.loads((out / 'receipt.json').read_bytes())
        assert code == 1 and receipt['status'] == 'failed' and receipt['commands'] == []
        assert receipt['cleanup']['deadline_expired'] and not receipt['cleanup']['removed']
        assert (out / 'scratch/ownership.json').is_file()
        assert not state['after_delayed_work']
        assert state['cleanup_entered'] == (stage == 'retention')
        assert .04 <= receipt['cleanup_elapsed_seconds'] < .2
        if stage == 'postflight':
            assert state['verify_calls'] == 3 and receipt['postflight'] == {}
        assert any(e['type'] == 'CleanupDeadlineExpired' for e in receipt['errors'])
        preserved = candidate.inventory(out / 'scratch')
        ownership = json.loads((out / 'scratch/ownership.json').read_bytes())
        shutil.rmtree(out / 'scratch')
        results.append({'stage': stage, 'state': state, 'exit': code,
            'runner_receipt': str(out / 'receipt.json'),
            'runner_receipt_sha256': hashlib.sha256((out / 'receipt.json').read_bytes()).hexdigest(),
            'cleanup_elapsed_seconds': receipt['cleanup_elapsed_seconds'],
            'recoverable_scratch_preserved_at_deadline': True,
            'preserved_inventory': preserved, 'preserved_ownership': ownership,
            'synthetic_control_scratch_removed_after_observation': True,
            'child_commands_started': 0, 'passed': True})
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'test_only_cleanup_allowance_seconds': .05, 'results': results,
        'normal_qualification_or_native_run_started': False,
        'terminal_cleanup_repair_independently_passed': True}
    (output / 'receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print('PASS independent terminal cleanup: postflight+retention expiration stops work, retains scratch, starts no child')

if __name__ == '__main__':
    main()
