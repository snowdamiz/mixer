#!/usr/bin/env python3
"""Shortened test-only deadline control around the exact candidate functions."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest import mock

HERE = Path(__file__).absolute().parent

def main():
    path = HERE / 'candidate-copy/check_cache_state.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '92bf2c0ca453ad9cae8ad6274d2248870af1cad4f4044039afde28f806d4392d'
    spec = importlib.util.spec_from_file_location('reviewed_candidate_cleanup_gap', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    out = runner.fresh_output(runner.RUNS / 'cleanup-deadline-control')
    original_verify = runner.verify_pack
    original_cleanup = runner.cleanup
    state = {'verify_calls': 0, 'cleanup_after_expired_postflight_entered': False}
    allowance = .05
    def controlled_verify(base):
        state['verify_calls'] += 1
        if state['verify_calls'] == 3:
            # First postflight check; its TimeoutError must stop remaining work.
            time.sleep(1)
        return original_verify(base)
    def observed_cleanup(*args):
        state['cleanup_after_expired_postflight_entered'] = True
        started = time.monotonic()
        time.sleep(.25)
        state['post_expiry_cleanup_delay_observed_seconds'] = time.monotonic() - started
        return original_cleanup(*args)
    with mock.patch.object(runner, 'CLEANUP_SECONDS', allowance), \
         mock.patch.object(runner, 'verify_pack', controlled_verify), \
         mock.patch.object(runner, 'cleanup', observed_cleanup):
        exit_code = runner.execute(out, str(HERE / 'intentionally-missing-compiler'))
    observed = json.loads((out / 'receipt.json').read_bytes())
    assert exit_code == 1 and observed['status'] == 'failed'
    assert observed['commands'] == []
    assert not observed['postflight']['pack']['passed']
    assert observed['postflight']['pack']['error'] == 'Fixed overall deadline exhausted'
    assert state['cleanup_after_expired_postflight_entered']
    assert state['post_expiry_cleanup_delay_observed_seconds'] >= .25
    assert observed['cleanup']['removed'] and not (out / 'scratch').exists()
    elapsed = observed['elapsed_seconds'] - observed['active_elapsed_seconds']
    assert elapsed > .25 > allowance
    result = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runner_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'normal_run_started': False, 'commands_started': 0,
        'test_only_cleanup_allowance_seconds': allowance,
        'test_only_delay_seconds': .25, 'state': state,
        'observed_cleanup_stage_seconds': elapsed,
        'observed_invocation_receipt': str(out / 'receipt.json'),
        'observed_invocation_receipt_sha256': hashlib.sha256((out / 'receipt.json').read_bytes()).hexdigest(),
        'deadline_enforcement_contract_passed': False,
        'finding': 'A one-shot cleanup TimeoutError raised inside a postflight check is swallowed by check(BaseException); cleanup proceeds beyond the expired allowance',
        'repair': 'Treat deadline expiration as terminal for postflight/retention, preserve recoverable scratch and stop remaining work; maintain an absolute cleanup deadline or re-arm only with its remaining time; add focused expiry-during-postflight control',
        'candidate_modified': False, 'scratch_removed': True, 'frozen_packet_unchanged': True,
        'scope': 'Actual Python deadline control with lowered test-only allowance and deliberate slow wrappers; no Rust/Git/native child'}
    (HERE / 'evidence/candidate-cleanup-deadline-gap.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('CONFIRMED cleanup bound failure: postflight consumed .05s alarm; subsequent .25s cleanup work completed after expiry')

if __name__ == '__main__':
    main()
