"""Real ITIMER_REAL coverage with a fixed logic clock and explicit wall observations."""
import json
from pathlib import Path
import signal
import time
import types
from unittest import mock


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(observation):
    receipt, state = observation['receipt'], observation['state']
    need(observation['exception'] is None and observation['status'] == 1,
         'Runner must return deadline failure')
    need(receipt['status'] == 'failed' and receipt['cleanup'].get('deadline_expired') is True,
         'Terminal cleanup deadline required')
    need(receipt['cleanup']['removed'] is False and observation['scratch_preserved'],
         'Owned scratch must remain unchanged')
    need(receipt['commands'] == [] and observation['spawn_calls'] == 0, 'No child allowed')
    need(state['after_delay'] is False, 'Work continued after deadline')
    need(state['stage_timer_started'] is True, 'Real stage timer must be armed')
    need(state['cleanup_entered'] == (observation['stage'] == 'retention'),
         'Unexpected cleanup stage')
    handlers = [event for event in observation['events'] if event['event'] == 'handler-raise']
    need(len(handlers) == 1 and handlers[0]['type'] == 'CleanupDeadlineExpired',
         'Actual installed cleanup handler must raise')
    arms = [event for event in observation['events'] if event['event'] == 'stage-arm']
    need(len(arms) == 1 and 0 < arms[0]['seconds'] <= .05,
         'Original 50ms test timer registration required')
    need(observation['timer_disarmed'] and observation['handlers_restored'],
         'Signal state must be restored')
    need(receipt['cleanup_elapsed_seconds'] == 0.0, 'Fixed-clock scope differs')
    if observation['stage'] == 'postflight':
        need(state['pack_calls'] == 3 and receipt['postflight'] == {},
             'Postflight must stop at interrupted pack check')


def run(case, runner, evidence_root, stage):
    need(stage in {'postflight', 'retention'}, 'Unknown deadline stage')
    need(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'Existing process timer refused')
    runs = case.base / 'runs'
    runs.mkdir()
    state = {'pack_calls': 0, 'cleanup_entered': False, 'after_delay': False,
             'stage_timer_started': False}
    events, timers, pending = [], [], []
    original_verify, original_cleanup = runner.verify_pack, runner.cleanup
    original_signal, original_timer = signal.signal, signal.setitimer
    previous = {s: signal.getsignal(s) for s in [signal.SIGALRM, signal.SIGINT, signal.SIGTERM]}
    out, status, failure, before_marker, before_identity = None, None, None, None, None
    wall_start = time.monotonic()

    def register(signum, handler):
        if signum == signal.SIGALRM and getattr(handler, '__name__', '') == 'cleanup_alarm':
            need(Path(handler.__code__.co_filename) == Path(runner.__file__),
                 'Handler must come from frozen runner')
            def observed(number, frame):
                events.append({'event': 'handler-entry', 'wall': time.monotonic()})
                try:
                    return handler(number, frame)
                except BaseException as error:
                    events.append({'event': 'handler-raise', 'wall': time.monotonic(),
                                   'type': type(error).__name__})
                    raise
            return original_signal(signum, observed)
        return original_signal(signum, handler)

    def setitimer(which, seconds, interval=0):
        events.append({'event': 'runner-timer-registration', 'seconds': seconds,
                       'which': which, 'interval': interval, 'wall': time.monotonic()})
        if seconds > 0:
            timers.append(seconds)
            if len(timers) == 2:
                need(which == signal.ITIMER_REAL and interval == 0 and 0 < seconds <= .05,
                     'Cleanup registration differs')
                pending.append(seconds)
                return original_timer(which, 0)
        return original_timer(which, seconds, interval)

    def delay():
        nonlocal before_marker, before_identity
        need(len(timers) == 2 and len(pending) == 1, 'Exactly one cleanup timer required')
        before_marker = (out / 'scratch/ownership.json').read_bytes()
        before_identity = runner.identity(out / 'scratch')
        state['stage_timer_started'] = True
        seconds = pending.pop()
        events.append({'event': 'stage-arm', 'wall': time.monotonic(), 'seconds': seconds})
        original_timer(signal.ITIMER_REAL, seconds)
        time.sleep(.25)
        state['after_delay'] = True

    def verify(base):
        state['pack_calls'] += 1
        if stage == 'postflight' and state['pack_calls'] == 3:
            delay()
        return original_verify(base)

    def cleanup(*args):
        state['cleanup_entered'] = True
        if stage == 'retention':
            delay()
        return original_cleanup(*args)

    timer = types.SimpleNamespace(**{name: getattr(signal, name) for name in
        ['SIGALRM', 'SIGINT', 'SIGTERM', 'ITIMER_REAL', 'getsignal']},
        signal=register, setitimer=setitimer)
    try:
        with mock.patch.object(runner, 'RUNS', runs), \
             mock.patch.object(runner, 'CLEANUP_SECONDS', .05), \
             mock.patch.object(runner, 'time', types.SimpleNamespace(monotonic=lambda: 100.0)), \
             mock.patch.object(runner, 'signal', timer), \
             mock.patch.object(runner, 'verify_pack', verify), \
             mock.patch.object(runner.overlay, 'verify_materialized', return_value={'control': 'isolated'}), \
             mock.patch.object(runner, 'cleanup', cleanup), \
             mock.patch.object(runner.platform, 'platform', return_value='pure control; no platform subprocess'), \
             mock.patch.object(runner.shutil, 'which', return_value=None), \
             mock.patch.object(runner.subprocess, 'Popen', side_effect=RuntimeError('No child allowed')) as spawn:
            out = runner.fresh_output(runs / 'deadline')
            status = runner.execute(out, 'mixer-no-such-official-compiler-control')
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    finally:
        # Capture before any assertion or test teardown, including unexpected exceptions.
        receipt_path = out / 'receipt.json' if out is not None else None
        receipt = json.loads(receipt_path.read_bytes()) if receipt_path and receipt_path.is_file() else {}
        marker = out / 'scratch/ownership.json' if out is not None else None
        preserved = bool(marker and marker.is_file() and before_marker is not None
                         and marker.read_bytes() == before_marker
                         and runner.identity(out / 'scratch') == before_identity)
        observation = {'schema': 1, 'stage': stage, 'status': status, 'exception': failure,
            'state': state, 'events': events, 'receipt': receipt,
            'scratch_preserved': preserved, 'spawn_calls': spawn.call_count,
            'wall_elapsed_seconds': time.monotonic() - wall_start,
            'timer_disarmed': signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
            'handlers_restored': all(signal.getsignal(s) == handler for s, handler in previous.items()),
            'retained_before_assertions_and_teardown': True,
            'scope': 'Actual registered 50ms ITIMER_REAL and frozen handler; fixed logical clock prevents remaining() from impersonating handler delivery. 250ms hook must not continue. Wall observations are diagnostic, not latency qualification.'}
        destination = evidence_root / 'logs'
        destination.mkdir(parents=True, exist_ok=True)
        runner.save(destination / ('deadline-' + stage + '-control.json'), observation)
        # Only this test process's timer and handlers; no process/group probes.
        original_timer(signal.ITIMER_REAL, 0)
        for number, handler in previous.items():
            original_signal(number, handler)
    validate(observation)
    return observation
