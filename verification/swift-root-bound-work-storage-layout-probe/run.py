#!/usr/bin/env python3
"""One root-released compiler-only query, bounded capture, unconditional owned cleanup."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import time

from check import check, hash_file, pinned, require, sha
from diagnostics import parse, source_map

D = Path(__file__).resolve().parent
R = D.parents[1]


def write_once(path, obj):
    with path.open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')


def absent(operation, pid):
    try: operation(pid, 0); return False
    except ProcessLookupError: return True


def stop_owned(process, deadline, failures, actions, *, clock=time.monotonic, pause=time.sleep,
               killpg=os.killpg, kill=os.kill, waitpid=os.waitpid):
    """Never enumerate processes. Exact owned PID/group only; ambiguity forbids deletion."""
    result = {'child_started': process is not None, 'child_reaped': False, 'exact_pid_absent': None,
              'exact_group_absent': None, 'exit_code': None}
    if process is None:
        actions.append('no-child-started'); return result
    def fault(reason, error=None):
        failures.append({'classification': reason, 'detail': None if error is None else type(error).__name__ + ': ' + str(error)})
    def signal_group():
        try:
            killpg(process.pid, signal.SIGKILL)
            if 'SIGKILL-exact-owned-group' not in actions: actions.append('SIGKILL-exact-owned-group')
        except ProcessLookupError: pass
        except BaseException as error: fault('owned-signal-failure', error)
    signal_group()
    while clock() < deadline:
        if not result['child_reaped']:
            try:
                result['exit_code'] = process.wait(timeout=min(.05, max(0, deadline-clock())))
                result['child_reaped'] = True
            except subprocess.TimeoutExpired: pass
            except BaseException as error:
                fault('owned-wait-failure', error)
                try:
                    pid, status = waitpid(process.pid, os.WNOHANG)
                    if pid == process.pid:
                        result['exit_code'] = os.waitstatus_to_exitcode(status)
                        process.returncode = result['exit_code']; result['child_reaped'] = True
                except ChildProcessError:
                    if process.returncode is not None:
                        result['exit_code'] = process.returncode; result['child_reaped'] = True
                    else: fault('owned-exit-status-unavailable')
                except BaseException as fallback: fault('owned-exact-waitpid-failure', fallback)
        try:
            result['exact_pid_absent'] = absent(kill, process.pid)
            result['exact_group_absent'] = absent(killpg, process.pid)
        except BaseException as error:
            fault('owned-absence-check-failure', error)
            result['exact_pid_absent'] = result['exact_group_absent'] = None
            break
        if result['child_reaped'] and result['exact_pid_absent'] and result['exact_group_absent']: break
        signal_group()
        pause(min(.01, max(0, deadline-clock())))
    if not result['child_reaped']: fault('owned-child-not-reaped')
    if result['exact_pid_absent'] is not True: fault('owned-pid-absence-unconfirmed')
    if result['exact_group_absent'] is not True: fault('owned-group-absence-unconfirmed')
    return result


def cleanup_build(build, ownership, deadline, plan):
    """Retain ambiguous artifacts. Delete exact owned entries after PID/group closure only."""
    report = {'build_existed': build.exists(), 'removed': False, 'inventory': [], 'preserved_reason': None}
    if not build.exists(): return report
    safe = ownership['child_started'] and ownership['child_reaped'] and ownership['exact_pid_absent'] is True and ownership['exact_group_absent'] is True
    if not safe:
        report['preserved_reason'] = 'owned PID/group closure not fully established'; return report
    require(build.is_dir() and not build.is_symlink(), 'ambiguous build directory')
    entries = []; directories = []; total = 0; pending = [build]
    while pending:
        require(time.monotonic() < deadline, 'artifact inventory deadline')
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            for entry in iterator:
                require(time.monotonic() < deadline, 'artifact inventory deadline')
                require(not entry.is_symlink(), 'ambiguous generated artifact symlink')
                require(len(entries) + len(directories) < plan['bounds']['maximum_build_members'], 'generated member cap')
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False): directories.append(path); pending.append(path)
                else:
                    require(entry.is_file(follow_symlinks=False), 'nonregular generated artifact')
                    total += entry.stat(follow_symlinks=False).st_size
                    require(total <= plan['bounds']['maximum_build_artifact_bytes'], 'generated artifact byte cap')
                    item = {'path': str(path.relative_to(build)), **hash_file(path, deadline)}
                    entries.append((path, item))
    report['inventory'] = [item for _, item in entries]
    # No process can write these files after exact owned PID/group closure.
    for path, item in entries:
        require(time.monotonic() < deadline, 'artifact removal deadline')
        require(hash_file(path, deadline) == {key: item[key] for key in ['bytes', 'sha256']}, 'artifact changed before deletion')
        path.unlink()
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True): path.rmdir()
    build.rmdir(); report['removed'] = True
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--root-release-sha256', required=True)
    args = parser.parse_args()
    start = time.monotonic(); work_deadline = start + 44; cleanup_deadline = start + 49; post_deadline = start + 53.5
    out = D / 'command'; out.mkdir(exist_ok=False)
    process = None; selector = None; files = {}; streams = {}; plan = None
    observed = {'stdout': 0, 'stderr': 0}; captured = dict(observed); failures = []; actions = []
    phase = 'preflight'; ownership = {}; outputs = {}; posthashes = False; build_report = {}; parsed = None
    sources = None; code = None; exception = None
    def fail(reason, error=None):
        failures.append({'classification': reason, 'detail': None if error is None else str(error)})
    class Stopped(BaseException): pass
    def stop_signal(number, frame): raise Stopped('signal ' + str(number) + ' in ' + phase)
    saved = {sig: signal.getsignal(sig) for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGALRM]}
    for sig in saved: signal.signal(sig, stop_signal)
    signal.setitimer(signal.ITIMER_REAL, max(.001, work_deadline-time.monotonic()))
    def capture(timeout):
        if selector is None: return False
        events = selector.select(timeout)
        for key, mask in events:
            stream = key.fileobj; name = key.data
            try: raw = os.read(stream.fileno(), 65536)
            except BlockingIOError: continue
            if not raw:
                selector.unregister(stream); stream.close(); continue
            observed[name] += len(raw)
            cap = plan['bounds']['maximum_' + name + '_bytes']
            keep = raw[:max(0, cap-captured[name])]
            if keep: files[name].write(keep); captured[name] += len(keep)
            if observed[name] > cap: fail('output-limit', name)
        return bool(events)
    try:
        try:
            plan = check(args.plan_sha256, work_deadline)
            release_path = R / plan['root_release_required']['path']
            require(hash_file(release_path, work_deadline)['sha256'] == args.root_release_sha256, 'root release hash mismatch')
            release = json.loads(release_path.read_text())
            require(release.get('plan_sha256') == args.plan_sha256 and release.get('compiler_lane_released') is True and release.get('compiler_invocations') == 1, 'root has not released exact plan/compiler slot')
            require(not (D / 'build').exists(), 'pre-existing build directory must be reviewed')
            sources = source_map(plan, D)
            write_once(out / 'plan.json', {'plan_sha256': args.plan_sha256, 'root_release_sha256': args.root_release_sha256,
                'argv': plan['argv'], 'environment': plan['environment'], 'cwd': plan['cwd'], 'toolchain_version': plan['toolchain_version'],
                'bounds': plan['bounds'], 'parent_pid': os.getpid(), 'parent_pgid': os.getpgrp(),
                'compiler_exit_1_is_intentional_diagnostics_only': True})
            (D / 'build').mkdir()
            for name in observed: files[name] = (out / name).open('xb')
            selector = selectors.DefaultSelector()
            phase = 'spawn'
            require(time.monotonic() < work_deadline, 'work deadline before spawn')
            # Assignment tracks Popen immediately, before any evidence/pipe operation.
            process = subprocess.Popen(plan['argv'], cwd=plan['cwd'], env=plan['environment'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            write_once(out / 'owned-process.json', {'pid': process.pid, 'pgid': process.pid, 'new_session': True, 'global_inventory': False})
            for name in observed:
                stream = getattr(process, name); streams[name] = stream
                os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ, name)
            phase = 'capture'
            while time.monotonic() < work_deadline:
                capture(min(.05, max(0, work_deadline-time.monotonic())))
                if failures: break
                code = process.poll()
                if code is not None: break
            if code is None: fail('compiler-work-deadline-or-incomplete')
        except BaseException as error:
            exception = {'phase': phase, 'type': type(error).__name__, 'message': str(error)}
            fail('work-exception', exception)
        finally:
            phase = 'owned-process-cleanup'
            signal.setitimer(signal.ITIMER_REAL, 0)
            for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]: signal.signal(sig, signal.SIG_IGN)
            try: ownership = stop_owned(process, cleanup_deadline, failures, actions)
            except BaseException as error:
                fail('cleanup-exception', type(error).__name__ + ': ' + str(error))
                ownership = {'child_started': process is not None, 'child_reaped': False, 'exact_pid_absent': None, 'exact_group_absent': None, 'exit_code': None}
            if ownership.get('exit_code') is not None: code = ownership['exit_code']
            try:
                while time.monotonic() < cleanup_deadline and capture(0): pass
                if selector is not None and selector.get_map(): fail('capture-pipes-not-closed')
            except BaseException as error: fail('capture-final-drain-exception', error)
            for stream in [getattr(process, name, None) for name in observed] if process is not None else []:
                if stream is not None:
                    try: stream.close()
                    except BaseException as error: fail('pipe-close-exception', error)
            if selector is not None:
                try: selector.close()
                except BaseException as error: fail('selector-close-exception', error)
            for handle in files.values():
                try: handle.close()
                except BaseException as error: fail('output-close-exception', error)
        phase = 'posthash-and-artifact-cleanup'
        signal.setitimer(signal.ITIMER_REAL, max(.001, post_deadline-time.monotonic()))
        if plan is not None:
            try:
                check(args.plan_sha256, post_deadline); posthashes = True
            except BaseException as error: fail('posthash-exception', error)
            try:
                build_report = cleanup_build(D / 'build', ownership, post_deadline, plan)
                if build_report.get('build_existed') and not build_report.get('removed'): fail('build-preserved-ambiguous', build_report.get('preserved_reason'))
            except BaseException as error:
                build_report = {'removed': False, 'preserved_reason': type(error).__name__ + ': ' + str(error)}
                fail('build-cleanup-exception-preserved', error)
        if code != 1: fail('compiler-exit-is-not-intentional-1', code)
        try:
            outputs = {name: {'path': name, **hash_file(out / name, post_deadline)} for name in observed if (out/name).is_file()}
            require(outputs.get('stdout', {}).get('bytes') == 0, 'compiler stdout is not empty')
            require(not any(item['path'].endswith('.rmeta') for item in build_report.get('inventory', [])), 'failed query produced metadata')
            if not failures:
                phase = 'parse-diagnostics'
                parsed = parse((out / 'stderr').read_bytes(), plan, sources)
        except BaseException as error: fail('diagnostic-or-output-rejection', type(error).__name__ + ': ' + str(error))
    except BaseException as error:
        fail('outer-finalization-exception', type(error).__name__ + ': ' + str(error))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in saved.items(): signal.signal(sig, handler)
        elapsed = time.monotonic()-start
        if elapsed >= 55: fail('total-55-second-ceiling-exceeded', elapsed)
        receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'plan_sha256': args.plan_sha256,
            'root_release_sha256': args.root_release_sha256, 'compiler_invocations': int(process is not None),
            'compiler_exit_code': code, 'intentional_exit_1_diagnostic_evidence_only': code == 1,
            'successful_product_compile_or_runtime': False, 'accepted_diagnostic_observation': not failures and parsed is not None,
            'elapsed_seconds_including_cleanup_posthashes': elapsed, 'failures': failures, 'exception': exception,
            'ownership': ownership, 'cleanup_actions': actions, 'build_cleanup': build_report, 'frozen_source_scratch_preserved': True,
            'observed_output_bytes': observed, 'captured_output_bytes': captured, 'outputs': outputs,
            'posthashes_verified': posthashes, 'global_process_inventory': False,
            'native_UI_capture_network_phone_host_VM_execution': False,
            'work_storage_prices_backing_peak_funding_full_ownership_GA_accepted': False}
        write_once(out / 'receipt.json', receipt)
        if parsed is not None and not failures: write_once(out / 'diagnostic-observation.json', parsed)
    print(json.dumps({'accepted_diagnostic_observation': receipt['accepted_diagnostic_observation'], 'compiler_exit_code': code,
                      'elapsed_seconds': receipt['elapsed_seconds_including_cleanup_posthashes'], 'failures': failures}))
    return 0 if receipt['accepted_diagnostic_observation'] else 1


if __name__ == '__main__': raise SystemExit(main())
