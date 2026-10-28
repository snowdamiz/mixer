#!/usr/bin/env python3
"""Exactly one root-authorized formatting VM, then exact PID/group cleanup."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PREPARED = LANE / 'prepared-2'
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
SOURCE_NAMES = ['hosted/lib/mixer_hosted/identity/admission.ex',
                'hosted/lib/mixer_hosted/identity/key_owner.ex',
                'hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs']


def ensure(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('formatting command deadline exceeded')


def sha(path, deadline):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            ensure(deadline)
            data = stream.read(262144)
            if not data:
                return value.hexdigest()
            value.update(data)


def pin(path, deadline, relative=None):
    return {'path': str(relative if relative is not None else path),
            'bytes': path.stat().st_size, 'sha256': sha(path, deadline)}


def check(path, expected, deadline):
    if pin(path, deadline, expected['path']) != expected:
        raise ValueError('frozen input differs: ' + str(path))


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def group_absent(pid):
    try:
        os.killpg(pid, 0)
        return False
    except ProcessLookupError:
        return True


def main():
    started = time.monotonic()
    work = started + 40
    cleanup = started + 46
    finalize = started + 52
    terminal = started + 55
    received = []
    for number in SIGNALS:
        signal.signal(number, lambda signum, _frame: received.append(signum))
    output = LANE / 'formatting-pass-1'
    output.mkdir(exist_ok=False)
    (output / 'outputs').mkdir()
    child = None
    scratch = None
    selector = None
    errors = []
    cleanup_errors = []
    original_pins = []
    stable = False
    returncode = None
    captured = 0
    plan_hash = None
    output_pins = []
    cleanup_observation = {'direct_child_reaped': False, 'owned_group_absent': False}
    try:
        plan_path = PREPARED / 'execution-plan.json'
        if sha(plan_path, work) != '1ae8bd1e9e38c2a18abae465b054fdcf562b842972475bc9bc1d3e80c07a52b3':
            raise ValueError('selected prepared-2 plan differs')
        plan = json.loads(plan_path.read_text())
        save(output / 'tool-pins.json', plan['tools'])
        for expected in plan['tools']:
            path = Path(expected['path'])
            check(path, expected, work)
            original_pins.append((path, expected))
        source_pins = [next(item for item in plan['canonical_inputs'] if item['path'] == name)
                       for name in SOURCE_NAMES]
        for expected in source_pins:
            for path in [ROOT / expected['path'], PREPARED / 'inputs' / expected['path']]:
                check(path, expected, work)
                original_pins.append((path, expected))
        formatter = LANE / 'formatting-only.exs'
        script_pin = pin(formatter, work)
        original_pins.append((formatter, script_pin))
        runner_pin = pin(Path(__file__).resolve(), work)
        original_pins.append((Path(__file__).resolve(), runner_pin))
        scratch = Path(tempfile.mkdtemp(prefix='mixer-key-owner-format-only-', dir='/private/tmp'))
        for directory in ['home', 'tmp', 'inputs']:
            (scratch / directory).mkdir()
        staged_sources = []
        for expected in source_pins:
            destination = scratch / 'inputs' / Path(expected['path']).name
            shutil.copyfile(ROOT / expected['path'], destination)
            check(destination, expected, work)
            staged_sources.append(str(destination))
        staged_formatter = scratch / 'formatting-only.exs'
        shutil.copyfile(formatter, staged_formatter)
        check(staged_formatter, script_pin, work)
        environment = dict(plan['environment'])
        environment.update(HOME=str(scratch / 'home'), TMPDIR=str(scratch / 'tmp'))
        command = [plan['elixir'], '--no-color', '--boot', plan['boot'], '--erl',
                   '+S 2:2 +A 2 -home ' + str(scratch / 'home'), str(staged_formatter),
                   str(output / 'outputs')] + staged_sources
        execution_plan = {
            'schema': 1, 'status': 'root-authorized-one-formatting-only-vm',
            'at': datetime.now(timezone.utc).isoformat(),
            'argv': command, 'cwd': str(scratch), 'environment': environment,
            'inherited_environment': [], 'source_pins': source_pins,
            'source_revision': plan['source_revision'],
            'selected_input_tree_sha256': plan['source_tree_sha256'],
            'prepared_2_plan_sha256': sha(plan_path, work),
            'tool_pins_file': 'tool-pins.json', 'tool_pins_sha256': sha(output / 'tool-pins.json', work),
            'formatter_script': script_pin, 'runner': runner_pin,
            'limits': {'work_seconds': 40, 'cleanup_cutoff': 46, 'finalization_cutoff': 52,
                       'total_seconds': 55, 'combined_output_bytes': 65536},
            'scope': 'Code.format_string! only for three source byte strings. No Mix project, product app, product compilation/test, network or native/UI/capture.',
            'authorization': 'Root task message exclusively releases one bounded formatting-only VM after candidate-2 formatting failure.'}
        save(output / 'execution-plan.json', execution_plan)
        plan_hash = sha(output / 'execution-plan.json', work)
        ensure(work)
        if received:
            raise RuntimeError('signal observed before launch')
        child = subprocess.Popen(command, cwd=scratch, env=environment,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ)
        with (output / 'stdout.txt').open('xb') as stream:
            eof = False
            while not eof:
                ensure(work)
                if received:
                    raise RuntimeError('signal observed during formatting')
                for key, _ in selector.select(min(0.05, work - time.monotonic())):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        eof = True
                        break
                    captured += len(data)
                    if captured > 65536:
                        raise ValueError('formatting output cap exceeded')
                    stream.write(data)
            returncode = child.wait(timeout=work - time.monotonic())
        if returncode != 0:
            errors.append('formatting VM exited ' + str(returncode))
    except BaseException as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
    finally:
        if selector is not None:
            selector.close()
        if child is not None:
            try:
                if not group_absent(child.pid):
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    until = min(cleanup, time.monotonic() + 0.4)
                    while time.monotonic() < until and not group_absent(child.pid):
                        child.poll()
                        time.sleep(0.01)
                    if not group_absent(child.pid):
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                ensure(cleanup)
                child.wait(timeout=max(0.001, cleanup - time.monotonic()))
                cleanup_observation['direct_child_reaped'] = child.returncode is not None
                while time.monotonic() < cleanup and not group_absent(child.pid):
                    time.sleep(0.01)
                cleanup_observation['owned_group_absent'] = group_absent(child.pid)
                if not all(cleanup_observation.values()):
                    raise RuntimeError('exact formatting child cleanup not confirmed')
            except BaseException as exc:
                cleanup_errors.append(repr(exc))
            finally:
                if child.stdout is not None:
                    child.stdout.close()
        if scratch is not None:
            if child is not None and all(cleanup_observation.values()) and not cleanup_errors:
                try:
                    ensure(cleanup)
                    shutil.rmtree(scratch)
                except BaseException as exc:
                    cleanup_errors.append('scratch: ' + repr(exc))
            else:
                cleanup_errors.append('scratch preserved because exact child cleanup was not confirmed')
        try:
            for path, expected in original_pins:
                check(path, expected, finalize)
            stable = True
            expected_lines = ['FORMAT_RUNTIME elixir=1.20.4 otp=29 node=nonode@nohost schedulers=2 product_application_started=false']
            expected_lines += ['FORMATTED ' + Path(path).name for path in SOURCE_NAMES]
            if (output / 'stdout.txt').read_text().splitlines() != expected_lines:
                raise ValueError('formatter runtime/version/output observations differ')
            actual_outputs = sorted(path.name for path in (output / 'outputs').iterdir())
            if actual_outputs != sorted(Path(path).name for path in SOURCE_NAMES):
                raise ValueError('exact three formatter outputs required')
            output_pins = [pin(output / 'outputs' / Path(path).name, finalize, path) for path in SOURCE_NAMES]
        except BaseException as exc:
            errors.append('finalization: ' + repr(exc))
        observation = {'returncode': returncode, 'output_bytes': captured,
                       'child_pid': child.pid if child else None, **cleanup_observation,
                       'scratch_removed': scratch is None or not scratch.exists(),
                       'all_input_tool_pins_stable': stable, 'formatted_outputs': output_pins,
                       'errors': errors, 'cleanup_errors': cleanup_errors,
                       'elapsed_seconds': round(time.monotonic() - started, 6)}
        ensure(finalize)
        save(output / 'observations.json', observation)
        signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        cutoff_signals = list(received) + [int(s) for s in signal.sigpending() if s in SIGNALS]
        cutoff_elapsed = time.monotonic() - started
        for number in SIGNALS:
            signal.signal(number, signal.SIG_IGN)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS)
        if cutoff_signals:
            errors.append('signals observed through cutoff: ' + repr(cutoff_signals))
        if cutoff_elapsed >= 52:
            errors.append('formatting finalization exceeded 52-second cutoff')
        receipt = {
            'schema': 1, 'status': 'passed' if not errors and not cleanup_errors else 'failed',
            'at': datetime.now(timezone.utc).isoformat(), 'execution_plan_sha256': plan_hash,
            'observations': observation, 'observed_signals_at_cutoff': cutoff_signals,
            'finite_signal_cutoff_elapsed_seconds': round(cutoff_elapsed, 6),
            'observed_versions': {'elixir': '1.20.4', 'otp_release': '29', 'schedulers': 2, 'node': 'nonode@nohost'},
            'formatter_vm_invocations': 1 if child else 0, 'product_compiler_test_invocations': 0,
            'scope': 'Single root-authorized formatting-only VM; no source application yet, no product runtime/test/compiler execution.'}
        ensure(terminal)
        save(output / 'receipt.json', receipt)
        print(json.dumps({'status': receipt['status'], 'child_pid': observation['child_pid'],
                          'direct_child_reaped': observation['direct_child_reaped'],
                          'owned_group_absent': observation['owned_group_absent'],
                          'scratch_removed': observation['scratch_removed'],
                          'elapsed_seconds': round(time.monotonic() - started, 6)}))
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
