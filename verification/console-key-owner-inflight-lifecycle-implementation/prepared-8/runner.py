#!/usr/bin/env python3
"""Execute only an exact root-released lifecycle plan; no inherited environment."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import importlib.util
import sys
import custody
import vm_cleanup
import time

SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path, cap=1048576):
    if path.stat().st_size > cap:
        raise ValueError('JSON input exceeds byte cap: ' + str(path))
    def reject(value):
        raise ValueError('non-finite JSON number: ' + value)
    return json.loads(path.read_text(), object_pairs_hook=strict_pairs, parse_constant=reject)


def ensure(deadline, label):
    if time.monotonic() >= deadline:
        raise TimeoutError(label + ' deadline exceeded')


def digest(path, deadline):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            ensure(deadline, 'hash')
            chunk = stream.read(262144)
            if not chunk:
                break
            value.update(chunk)
    return value.hexdigest()


def check_pin(path, pin, deadline):
    ensure(deadline, 'pin')
    if not path.is_file() or path.stat().st_size != pin['bytes'] or digest(path, deadline) != pin['sha256']:
        raise ValueError('input pin mismatch: ' + str(path))


def write_json(path, value):
    encoded = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    if len(encoded) > 1048576:
        raise ValueError('receipt byte cap exceeded')
    with path.open('xb') as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def validation_module(prepared):
    spec = importlib.util.spec_from_file_location('inflight_artifact_validation', prepared / 'artifact-validation.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('invoke this runner with Python -B')
    started = time.monotonic()
    # Reserve time after work for exact-child cleanup, pin rechecks, strict parsing,
    # durable observations and a finite signal cutoff before the terminal receipt.
    work_deadline = started + 40
    cleanup_deadline = started + 46
    finalize_deadline = started + 52
    receipt_deadline = started + 55
    received = []
    for signum in SIGNALS:
        signal.signal(signum, lambda number, _frame: received.append(number))
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True, type=Path)
    args = parser.parse_args()
    prepared = Path(__file__).resolve().parent
    lane = prepared.parent
    if prepared.name != 'prepared-8' or lane.name != 'console-key-owner-inflight-lifecycle-implementation':
        raise ValueError('runner must execute from its exact frozen lane')
    plan_path = prepared / 'execution-plan.json'
    plan = read_json(plan_path)
    plan_sha256 = digest(plan_path, work_deadline)
    release = read_json(args.release.resolve(), 16384)
    if (release.get('status') != 'root-released-exact-plan' or
            release.get('execution_plan_sha256') != plan_sha256 or
            release.get('single_execution') is not True):
        raise ValueError('exact single-execution root release missing or mismatched')
    if plan.get('real_runtime_dependency_closure_compatible') is not True:
        raise ValueError('real runtime blocked: frozen local dependency closure differs from selected canonical lock')
    output = lane / 'executions' / 'candidate-8'
    output.mkdir(parents=True, exist_ok=False)
    scratch = None
    children = []
    errors = []
    cleanup_errors = []
    originals = []
    original_changes = []
    phase_results = []
    artifact_observations = {}
    captured = 0
    custodian = None
    custody_output = None
    pins_rechecked = False

    def remaining():
        if custodian is not None:
            custodian.service()
            if custodian.errors:
                raise RuntimeError('custody protocol failed: ' + repr(custodian.errors))
        ensure(work_deadline, 'work')
        if received:
            raise RuntimeError('interrupted by observed signal ' + str(received[-1]))
        return work_deadline - time.monotonic()

    def reap(owner):
        observation = owner.cleanup(cleanup_deadline, lambda: custodian.service() if custodian is not None else None)
        if observation['uncertain'] or not observation['direct_child_reaped'] or not observation['group_absent']:
            # Full syscall/errno/traceback diagnostics are retained in the exact
            # owned-process observation, not reduced to a guessed cause.
            cleanup_errors.append('exact child ' + str(owner.pid) + ': ' + json.dumps(observation['diagnostics'], sort_keys=True))
        return observation

    try:
        root = Path(plan['workspace_root'])
        frozen = read_json(prepared / 'freeze.json')
        expected_files = {row['path'] for row in frozen['files']}
        if frozen['sole_excluded_relative_path'] != 'freeze.json' or len(expected_files) != len(frozen['files']):
            raise ValueError('invalid finite prepared membership')
        actual_files = set()
        for path in prepared.rglob('*'):
            if path.is_symlink():
                raise ValueError('prepared symlink forbidden')
            if path.is_file() and path.relative_to(prepared).as_posix() != 'freeze.json':
                actual_files.add(path.relative_to(prepared).as_posix())
        if actual_files != expected_files:
            raise ValueError('prepared membership changed')
        for row in frozen['files']:
            if Path(row['path']).is_absolute() or '..' in Path(row['path']).parts:
                raise ValueError('prepared path escapes')
            check_pin(prepared / row['path'], row, work_deadline)
        for pin in plan['tools']:
            path = Path(pin['path'])
            check_pin(path, pin, work_deadline)
            originals.append((path, pin))
        for pin in plan['canonical_inputs']:
            path = root / pin['path']
            check_pin(path, pin, work_deadline)
            originals.append((path, pin))
        for pin in plan['prepared_files']:
            check_pin(prepared / pin['path'], pin, work_deadline)
        scratch = Path(tempfile.mkdtemp(prefix='mixer-key-owner-inflight-', dir='/private/tmp'))
        for subdir in ['home', 'tmp', 'inputs', 'dependencies']:
            (scratch / subdir).mkdir()
        for pin in plan['prepared_files']:
            remaining()
            destination = scratch / pin['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prepared / pin['path'], destination)
            check_pin(destination, pin, work_deadline)
        (scratch / 'bin' / 'openssl').chmod(0o700)
        metadata = [
            {'name': dep['name'], 'version': dep['version'],
             'ebin': str(scratch / 'dependencies' / dep['name'] / 'ebin')}
            for dep in plan['dependencies']
        ]
        (scratch / 'dependency-metadata.json').write_text(json.dumps(metadata))
        for phase in plan['phases']:
            remaining()
            phase_output = output / phase['id']
            phase_output.mkdir()
            compile_output = scratch / (phase['id'] + '-ebin')
            compile_output.mkdir()
            sources = [
                str(scratch / phase['source_replacements'].get(path, 'inputs/' + path))
                for path in plan['source_roster']
            ]
            source_manifest = scratch / (phase['id'] + '-sources.json')
            source_manifest.write_text(json.dumps(sources))
            environment = dict(plan['environment'])
            environment.update(HOME=str(scratch / 'home'), TMPDIR=str(scratch / 'tmp'), MIX_ENV=phase['build'])
            environment['PATH'] = str(scratch / 'bin') + ':' + plan['environment']['PATH']
            environment['MIXER_OPENSSL_AUDIT'] = str(phase_output / 'openssl-audit.jsonl')
            environment['MIXER_OPENSSL_STARTED'] = str(phase_output / 'openssl-started.jsonl')
            if phase['id'] == 'test':
                custody_output = phase_output
                config = {'mode': 'real', 'run_nonce': custody.secrets.token_hex(16),
                          'directory': str(phase_output / 'custody'), 'execution_plan_sha256': plan_sha256,
                          'work_deadline_ns': int(work_deadline * 1e9), 'cleanup_deadline_ns': int(cleanup_deadline * 1e9),
                          'native_seconds': 5, 'owned_tmp': str(scratch / 'tmp')}
                for role, path in [('wrapper', scratch / 'bin/openssl'), ('interpreter', Path(plan['python'])), ('native', Path(plan['openssl']))]:
                    config[role + '_path'] = str(path)
                    config[role + '_sha256'] = digest(path, work_deadline)
                custodian = custody.Custodian(phase_output / 'custody', config, phase_output / 'custody-journal.jsonl', lambda: bool(received))
                config_path = scratch / 'custody-config.json'
                custody.publish(config_path, config, 16384)
                environment['MIXER_CUSTODY_CONFIG'] = str(config_path)
            environment['MIXER_KEY_OWNER_LIFECYCLE_ROOT_PEM'] = str(scratch / 'root.pem')
            environment['MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE'] = str(phase_output)
            command = [plan['elixir'], '--no-color', '--boot', plan['boot'], '--erl',
                       '+S 2:2 +A 2 -home ' + str(scratch / 'home')]
            for dep in metadata:
                command += ['-pa', dep['ebin']]
            command += [str(scratch / phase['bootstrap']), str(source_manifest), str(compile_output),
                        str(scratch / 'dependency-metadata.json')]
            write_json(phase_output / 'command.json', {'argv': command, 'cwd': str(scratch), 'environment': environment})
            remaining()
            # Nonraising handlers cannot interrupt ownership retention after launch.
            child = subprocess.Popen(command, cwd=scratch, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            children.append({'child': child, 'owner': vm_cleanup.RetainedChild(child), 'cleanup': None})
            selector = selectors.DefaultSelector()
            phase_bytes = 0
            try:
                if children[-1]['owner'].uncertain:
                    raise RuntimeError('VM leader identity retention failed; active cleanup authority closed')
                selector.register(child.stdout, selectors.EVENT_READ)
                with (phase_output / 'stdout.txt').open('xb') as log:
                    eof = False
                    while not eof:
                        for key, _ in selector.select(min(0.005, remaining())):
                            chunk = os.read(key.fileobj.fileno(), 8192)
                            if not chunk:
                                eof = True
                                break
                            phase_bytes += len(chunk)
                            captured += len(chunk)
                            if (phase_bytes > plan['limits']['phase_output_bytes'] or
                                    captured > plan['limits']['combined_output_bytes']):
                                raise RuntimeError('output byte cap exceeded')
                            log.write(chunk)
                    returncode = child.wait(timeout=remaining())
                phase_results.append({'id': phase['id'], 'returncode': returncode, 'output_bytes': phase_bytes})
            finally:
                selector.close()
                if custodian is not None:
                    custodian.close()
                children[-1]['cleanup'] = reap(children[-1]['owner'])
            if cleanup_errors or returncode != 0:
                raise RuntimeError('phase failed: ' + phase['id'])
    except BaseException as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
    finally:
        for record in children:
            if record['cleanup'] is None:
                record['cleanup'] = reap(record['owner'])
        owned_absent = all(r['cleanup']['direct_child_reaped'] and r['cleanup']['group_absent'] for r in children)
        custody_safe = True
        if custodian is not None:
            try:
                custodian.close()
                custodian.drain(cleanup_deadline)
                if custodian.grants != 7 or len(custodian.records) != 7 or any(not row['completion_sha256'] or not row['child_reaped'] or not row['released'] for row in custodian.records.values()):
                    custodian.fail('incomplete protocol; bootstrap/prepublication/spawn uncertainty')
                custodian.finalize()
                custody_safe = custodian.journal_reconciled and not custodian.uncertain and not custodian.errors and all(row['group_absent'] and not row['identity_lost'] for row in custodian.records.values())
                custody.publish(custody_output / 'custody-result.json', custodian.snapshot())
                if not custody_safe:
                    cleanup_errors.append('custody failed or incomplete; scratch preserved')
            except BaseException as exc:
                custody_safe = False
                cleanup_errors.append('custody finalization: ' + repr(exc))
        # A child-cleanup exception never grants permission to remove its scratch.
        if scratch is not None and owned_absent and custody_safe and not cleanup_errors:
            try:
                ensure(cleanup_deadline, 'scratch cleanup')
                shutil.rmtree(scratch)
            except BaseException as exc:
                cleanup_errors.append('scratch: ' + repr(exc))
        elif scratch is not None:
            cleanup_errors.append('scratch preserved because exact child cleanup was not confirmed')
        try:
            expected_phase_dirs = {phase['id'] for phase in plan['phases']}
            actual_phase_dirs = set()
            for path in output.iterdir():
                if path.is_symlink() or not path.is_dir():
                    errors.append('unexpected terminal root output member before observations: ' + str(path))
                actual_phase_dirs.add(path.name)
            if actual_phase_dirs != expected_phase_dirs:
                errors.append('exact terminal root phase membership differs')
            for path, pin in originals:
                try:
                    check_pin(path, pin, finalize_deadline)
                except ValueError:
                    original_changes.append(str(path))
            pins_rechecked = True
            for pin in plan['prepared_files']:
                check_pin(prepared / pin['path'], pin, finalize_deadline)
            artifact_bytes = 0
            for phase in plan['phases']:
                phase_output = output / phase['id']
                names = phase['required_artifacts']
                allowed = set(names) | {'stdout.txt', 'command.json'}
                if phase['id'] == 'test':
                    allowed.add('openssl-audit.jsonl')
                    allowed.add('openssl-started.jsonl')
                    allowed.update(['custody', 'custody-journal.jsonl'])
                actual = set()
                for path in phase_output.iterdir():
                    if path.name == 'custody' and phase['id'] == 'test' and path.is_dir() and not path.is_symlink():
                        actual.add(path.name)
                        members = list(path.iterdir())
                        if len(members) > 104:
                            raise ValueError('custody spool member cap')
                        permitted = {f'{ordinal:02d}.{suffix}.json' for ordinal in range(16) for suffix in ['offer', 'request', 'ack', 'child', 'completion', 'exit']}
                        for member in members:
                            if member.is_symlink() or not member.is_file() or member.name not in permitted:
                                raise ValueError('unexpected custody spool member')
                            artifact_bytes += member.stat().st_size
                            if member.stat().st_size > plan['limits']['artifact_bytes'] or artifact_bytes > plan['limits']['combined_artifact_bytes']:
                                raise ValueError('custody spool byte cap')
                        continue
                    if path.is_symlink() or not path.is_file():
                        raise ValueError('non-ordinary phase output member: ' + str(path))
                    actual.add(path.name)
                    if path.name not in allowed:
                        errors.append('unexpected phase output member: ' + str(path))
                    if path.name != 'stdout.txt':
                        artifact_bytes += path.stat().st_size
                        if path.stat().st_size > plan['limits']['artifact_bytes'] or artifact_bytes > plan['limits']['combined_artifact_bytes']:
                            raise ValueError('artifact byte cap exceeded')
                if actual != allowed:
                    errors.append('exact phase output membership differs: ' + phase['id'] +
                                  ': missing=' + repr(sorted(allowed - actual)) +
                                  ', extra=' + repr(sorted(actual - allowed)))
                for name in names:
                    try:
                        ensure(finalize_deadline, 'artifact parsing')
                        path = phase_output / name
                        value = read_json(path, plan['limits']['artifact_bytes'])
                        artifact_observations[phase['id'] + '/' + name] = value
                    except BaseException as exc:
                        errors.append('artifact parsing ' + phase['id'] + '/' + name + ': ' + repr(exc))
            schema_packet = read_json(prepared / plan['artifact_schemas'], 262144)
            validator = validation_module(prepared)
            validator.validate_artifacts(artifact_observations, schema_packet)
            test_index = next(i for i, phase in enumerate(plan['phases']) if phase['id'] == 'test')
            validator.validate_openssl(artifact_observations['test/openssl-invocations.json'], plan, artifact_observations['test/custody-result.json'])
            if custodian is None or artifact_observations['test/custody-result.json'] != custodian.snapshot():
                raise ValueError('terminal custody artifact differs from accepted memory')
            if custodian.reconcile() != artifact_observations['test/custody-result.json']['journal_sha256']:
                raise ValueError('terminal journal hash changed after cleanup')
            if artifact_observations['test/openssl-version.json']['output'] != artifact_observations['test/openssl-invocations.json']['invocations'][0]['output'].strip():
                raise ValueError('OpenSSL version observation differs from exact invocation output')
            validator.validate_clean_gates(artifact_observations)
        except BaseException as exc:
            errors.append('finalization: ' + repr(exc))
        observation = {
            'schema': 1, 'execution_plan_sha256': plan_sha256,
            'phases': phase_results,
            'owned_processes': [r['cleanup'] for r in children],
            'scratch_path': str(scratch) if scratch else None,
            'scratch_removed': scratch is None or not scratch.exists(),
            'all_original_pins_rechecked': pins_rechecked,
            'original_changes': original_changes, 'artifacts': artifact_observations,
            'errors': errors, 'cleanup_errors': cleanup_errors,
            'observed_signals_before_observation_write': list(received),
            'elapsed_seconds': round(time.monotonic() - started, 6)
        }
        try:
            ensure(finalize_deadline, 'observation persistence')
            write_json(output / 'observations.json', observation)
        except BaseException as exc:
            errors.append('observation persistence: ' + repr(exc))
        # Finite observation boundary after cleanup, hashes, strict parsing, durable
        # observations. Block delivery briefly, sample pending signals, then ignore
        # later signals only for the bounded final receipt write and immediate exit.
        signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        cutoff_signals = list(received) + [int(s) for s in signal.sigpending() if s in SIGNALS]
        cutoff_elapsed = time.monotonic() - started
        for signum in SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS)
        if cutoff_signals:
            errors.append('signals observed by finite cutoff: ' + repr(cutoff_signals))
        if cutoff_elapsed >= 52:
            errors.append('52-second observation cutoff exceeded')
        status = 'passed' if not errors and not cleanup_errors and not original_changes else 'failed'
        receipt = {
            'schema': 1, 'status': status, 'created_at': datetime.now(timezone.utc).isoformat(),
            'execution_plan_sha256': plan_sha256,
            'source_revision': plan['source_revision'], 'source_tree_sha256': plan['source_tree_sha256'],
            'observations_file': 'observations.json', 'output_bytes': captured,
            'observed_signals_at_cutoff': cutoff_signals,
            'finite_signal_cutoff_elapsed_seconds': round(cutoff_elapsed, 6),
            'signal_scope': 'Signals received or pending through the finite cutoff after durable observations; later signals are outside this receipt.',
            'errors': errors, 'cleanup_errors': cleanup_errors, 'scope': plan['scope'], 'pending': plan['pending']
        }
        ensure(receipt_deadline, 'terminal receipt')
        write_json(output / 'receipt.json', receipt)
        print(json.dumps({'status': status, 'receipt': str(output / 'receipt.json'),
                          'elapsed_seconds': round(time.monotonic() - started, 6)}))
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
