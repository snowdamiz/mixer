#!/usr/bin/env python3
"""Real-clock cleanup deadline control without candidate helper instrumentation."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import tempfile
import time
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_actual_runner', HERE / 'source/check_cache_state.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def main():
    states = []
    for stage in ['postflight', 'retention']:
        state = {'stage': stage, 'pack_calls': 0, 'cleanup_entered': False, 'after_delay': False}
        verify = r.verify_pack
        cleanup = r.cleanup
        def checked_pack(base):
            state['pack_calls'] += 1
            if stage == 'postflight' and state['pack_calls'] == 3:
                time.sleep(.4)
                state['after_delay'] = True
            return verify(base)
        def checked_cleanup(*args):
            state['cleanup_entered'] = True
            if stage == 'retention':
                time.sleep(.4)
                state['after_delay'] = True
            return cleanup(*args)
        # Retention gets cheap predecessor identity checks here, so actual-clock
        # interruption is isolated from the unrelated expensive Python binary hash.
        # Postflight keeps original preflight verification, then delays its first
        # postflight verification without any logical-clock/timer changes.
        if stage == 'retention':
            def ready_pack(base):
                state['pack_calls'] += 1
                if state['pack_calls'] <= 2:
                    return verify(base)
                return {'tree_sha256': 'independent-fast-postflight'}
            pack_fn = ready_pack
        else:
            pack_fn = checked_pack
        with tempfile.TemporaryDirectory(prefix='independent-natural-', dir=HERE / 'tmp') as temp:
            runs = Path(temp) / 'runs'
            runs.mkdir()
            # Intercept only Python executable hashing during cleanup in the
            # retention control to keep predecessor work below the 50ms budget.
            orig_sha = r.sha
            def fast_cleanup_sha(path):
                if stage == 'retention' and state['pack_calls'] >= 3 and Path(path) == Path(os.sys.executable).resolve():
                    return python_hash
                return orig_sha(path)
            python_hash = orig_sha(Path(os.sys.executable).resolve())
            previous = {s: signal.getsignal(s) for s in [signal.SIGALRM, signal.SIGINT, signal.SIGTERM]}
            with mock.patch.object(r, 'RUNS', runs), mock.patch.object(r, 'CLEANUP_SECONDS', .05), mock.patch.object(r, 'verify_pack', pack_fn), mock.patch.object(r, 'cleanup', checked_cleanup), mock.patch.object(r, 'sha', fast_cleanup_sha):
                output = r.fresh_output(runs / stage)
                started = time.monotonic()
                code = r.execute(output, 'mixer-no-such-official-compiler-control')
                elapsed = time.monotonic() - started
            receipt = json.loads((output / 'receipt.json').read_text())
            assert code == 1 and receipt['cleanup']['deadline_expired']
            assert not receipt['cleanup']['removed'] and (output / 'scratch/ownership.json').is_file()
            assert receipt['commands'] == [] and not state['after_delay']
            assert state['cleanup_entered'] == (stage == 'retention')
            assert .035 <= receipt['cleanup_elapsed_seconds'] < .2
            assert signal.getitimer(signal.ITIMER_REAL) == (0., 0.)
            assert all(signal.getsignal(s) == h for s, h in previous.items())
            state.update(receipt=receipt, actual_wall_seconds=elapsed,
                         cleanup_alarm_cleared=True, original_handlers_restored=True,
                         scratch_preserved_at_assertion=True)
            states.append(state)
    (HERE / 'natural-clock.json').write_text(json.dumps({'states': states, 'scope': 'Actual real-clock deadline; no logical-clock or signal proxy. Retention predecessor pack checks and Python executable hashing are cheapened only in this separate supplemental probe.'}, sort_keys=True, indent=2)+'\n')


if __name__ == '__main__':
    main()
