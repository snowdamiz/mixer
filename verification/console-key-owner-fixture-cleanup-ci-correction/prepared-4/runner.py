#!/usr/bin/env python3
"""Execute only an exact root-released fixture-cleanup plan; no inherited environment."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
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


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True


def write_json(path, value):
    encoded = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    if len(encoded) > 262144:
        raise ValueError('receipt byte cap exceeded')
    with path.open('xb') as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())



def validate_phase_directory(directory, required, deadline):
    ensure(deadline, 'phase membership')
    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise ValueError('phase output must be an ordinary directory, not a symlink')
    expected = set(required) | {'command.json', 'stdout.txt'}
    if len(required) != 8 or len(set(required)) != 8 or len(expected) != 10:
        raise ValueError('exact eight artifact and ten total phase names required')
    entries = []
    for entry in directory.iterdir():
        ensure(deadline, 'phase membership')
        entries.append(entry)
    actual = {entry.name for entry in entries}
    if actual != expected:
        raise ValueError('actual phase directory membership differs; missing=' +
                         repr(sorted(expected - actual)) + '; unexpected=' +
                         repr(sorted(actual - expected)))
    for entry in entries:
        ensure(deadline, 'phase member type')
        if not stat.S_ISREG(entry.lstat().st_mode):
            raise ValueError('phase member must be an ordinary file, not symlink or special type: ' + entry.name)


def validate_terminal_artifacts(artifacts, packet, scratch):
    if type(packet) is not dict or set(packet) != {'schema', 'required_artifacts', 'schemas', 'openssl_commands'}:
        raise ValueError('exact artifact schema packet fields required')
    if type(packet['required_artifacts']) is not int or packet['required_artifacts'] != 8:
        raise ValueError('integer eight required artifacts expected')
    schemas = packet['schemas']
    openssl_paths = ['corrected/openssl-%02d.json' % n for n in range(1, 5)]
    if type(schemas) is not dict or len(schemas) != 4 or set(artifacts) != set(schemas) | set(openssl_paths):
        raise ValueError('exact eight artifact path membership differs')
    for path, schema in schemas.items():
        value = artifacts[path]
        if type(value) is not dict or set(value) != set(schema):
            raise ValueError('exact artifact field membership differs: ' + path)
        for key, rule in schema.items():
            field = value[key]
            kind = rule['type']
            if kind == 'boolean':
                matches = type(rule.get('value')) is bool and field is rule['value']
            elif kind == 'integer':
                matches = type(rule.get('value')) is int and type(field) is int and field == rule['value']
            elif kind == 'string':
                matches = type(field) is str and field == rule['value']
            else:
                raise ValueError('unsupported field schema type: ' + kind)
            if not matches:
                raise ValueError('artifact field type/value differs: ' + path + ':' + key)
    records = [artifacts[path] for path in openssl_paths]
    fields = {'argv', 'exit_code', 'output', 'output_bytes', 'pid', 'child_reaped', 'elapsed_seconds', 'error'}
    for record in records:
        if type(record) is not dict or set(record) != fields:
            raise ValueError('OpenSSL exact field membership differs')
        if (type(record['exit_code']) is not int or record['exit_code'] != 0 or
                type(record['pid']) is not int or record['pid'] <= 0 or
                record['child_reaped'] is not True or record['error'] is not None or
                type(record['output_bytes']) is not int or not 0 <= record['output_bytes'] <= 8192 or
                type(record['output']) is not str or len(record['output'].encode()) != record['output_bytes'] or
                type(record['elapsed_seconds']) not in (int, float) or not 0 <= record['elapsed_seconds'] < 6 or
                type(record['argv']) is not list or not all(type(arg) is str for arg in record['argv'])):
            raise ValueError('OpenSSL field type, bound or successful cleanup differs')
    if len(records[1]['argv']) < 8:
        raise ValueError('OpenSSL CA argument list too short')
    fixture = Path(records[1]['argv'][7]).parent
    stem = 'mixer-key-owner-tls-'
    suffix = fixture.name.removeprefix(stem)
    if (fixture.parent != scratch / 'tmp' or not fixture.name.startswith(stem) or len(suffix) != 22 or
            any(char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for char in suffix)):
        raise ValueError('OpenSSL paths are outside exact owned scratch fixture')
    if type(packet['openssl_commands']) is not list or len(packet['openssl_commands']) != 4:
        raise ValueError('exact four OpenSSL command templates required')
    for record, template in zip(records, packet['openssl_commands'], strict=True):
        expected = [arg.replace('{fixture}', str(fixture)) for arg in template]
        if record['argv'] != expected:
            raise ValueError('exact OpenSSL argv differs')
    if not records[0]['output'].startswith('OpenSSL 3.6.5 '):
        raise ValueError('OpenSSL reported version differs')


def main():
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
    if prepared.name != 'prepared-4' or lane.name != 'console-key-owner-fixture-cleanup-ci-correction':
        raise ValueError('runner must execute from its exact frozen lane')
    plan_path = prepared / 'execution-plan.json'
    plan = read_json(plan_path)
    plan_sha256 = digest(plan_path, work_deadline)
    release = read_json(args.release.resolve(), 16384)
    if (release.get('status') != 'root-released-exact-plan' or
            release.get('execution_plan_sha256') != plan_sha256 or
            release.get('single_execution') is not True):
        raise ValueError('exact single-execution root release missing or mismatched')
    output = lane / 'executions' / 'candidate-4'
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
    pins_rechecked = False

    def remaining():
        ensure(work_deadline, 'work')
        if received:
            raise RuntimeError('interrupted by observed signal ' + str(received[-1]))
        return work_deadline - time.monotonic()

    def reap(child):
        observation = {'pid': child.pid, 'direct_child_reaped': False, 'group_absent': False}
        try:
            if not group_absent(child.pid):
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                until = min(cleanup_deadline, time.monotonic() + 0.4)
                while time.monotonic() < until and not group_absent(child.pid):
                    child.poll()
                    time.sleep(0.01)
                if not group_absent(child.pid):
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            ensure(cleanup_deadline, 'cleanup')
            child.wait(timeout=max(0.001, cleanup_deadline - time.monotonic()))
            observation['direct_child_reaped'] = child.returncode is not None
            while time.monotonic() < cleanup_deadline and not group_absent(child.pid):
                time.sleep(0.01)
            observation['group_absent'] = group_absent(child.pid)
            if not observation['direct_child_reaped'] or not observation['group_absent']:
                raise RuntimeError('owned child or group remains')
        except BaseException as exc:
            cleanup_errors.append('exact child ' + str(child.pid) + ': ' + repr(exc))
        finally:
            if child.stdout is not None:
                child.stdout.close()
        return observation

    try:
        root = Path(plan['workspace_root'])
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
        scratch = Path(tempfile.mkdtemp(prefix='mixer-key-owner-fixture-cleanup-', dir='/private/tmp'))
        for subdir in ['home', 'tmp', 'inputs', 'dependencies']:
            (scratch / subdir).mkdir()
        for pin in plan['prepared_files']:
            remaining()
            destination = scratch / pin['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prepared / pin['path'], destination)
            check_pin(destination, pin, work_deadline)
            if pin['path'] == 'tools/openssl':
                destination.chmod(0o700)
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
            environment = {key: value.replace('{scratch}', str(scratch)) for key, value in plan['environment'].items()}
            environment.update(HOME=str(scratch / 'home'), TMPDIR=str(scratch / 'tmp'))
            environment['MIXER_KEY_OWNER_FIXTURE_EVIDENCE'] = str(phase_output)
            command = [plan['elixir'], '--no-color', '--boot', plan['boot'], '--erl',
                       '+S 2:2 +A 2 -home ' + str(scratch / 'home')]
            for dep in metadata:
                command += ['-pa', dep['ebin']]
            command += [str(scratch / phase['bootstrap']), str(source_manifest),
                        str(scratch / 'inputs' / plan['test_source']), str(compile_output),
                        str(scratch / 'dependency-metadata.json')]
            write_json(phase_output / 'command.json', {'argv': command, 'cwd': str(scratch), 'environment': environment})
            remaining()
            # Nonraising handlers cannot interrupt ownership retention after launch.
            child = subprocess.Popen(command, cwd=scratch, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            children.append({'child': child, 'cleanup': None})
            selector = selectors.DefaultSelector()
            phase_bytes = 0
            try:
                selector.register(child.stdout, selectors.EVENT_READ)
                with (phase_output / 'stdout.txt').open('xb') as log:
                    eof = False
                    while not eof:
                        for key, _ in selector.select(min(0.05, remaining())):
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
                children[-1]['cleanup'] = reap(child)
            if cleanup_errors or returncode != 0:
                raise RuntimeError('phase failed: ' + phase['id'])
    except BaseException as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
    finally:
        for record in children:
            if record['cleanup'] is None:
                record['cleanup'] = reap(record['child'])
        owned_absent = all(r['cleanup']['direct_child_reaped'] and r['cleanup']['group_absent'] for r in children)
        # A child-cleanup exception never grants permission to remove its scratch.
        if scratch is not None and owned_absent and not cleanup_errors:
            try:
                ensure(cleanup_deadline, 'scratch cleanup')
                shutil.rmtree(scratch)
            except BaseException as exc:
                cleanup_errors.append('scratch: ' + repr(exc))
        elif scratch is not None:
            cleanup_errors.append('scratch preserved because exact child cleanup was not confirmed')
        try:
            for path, pin in originals:
                try:
                    check_pin(path, pin, finalize_deadline)
                except ValueError:
                    original_changes.append(str(path))
            pins_rechecked = True
            for pin in plan['prepared_files']:
                check_pin(prepared / pin['path'], pin, finalize_deadline)
            if not owned_absent or cleanup_errors:
                raise RuntimeError('phase membership requires confirmed owned child/group cleanup')
            for phase in plan['phases']:
                phase_output = output / phase['id']
                names = phase['required_artifacts']
                validate_phase_directory(phase_output, names, finalize_deadline)
                for name in names:
                    ensure(finalize_deadline, 'artifact parsing')
                    path = phase_output / name
                    value = read_json(path, 16384)
                    artifact_observations[phase['id'] + '/' + name] = value
            schema_packet = read_json(prepared / plan['artifact_schemas'], 16384)
            validate_terminal_artifacts(artifact_observations, schema_packet, scratch)
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
