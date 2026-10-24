#!/usr/bin/env python3
"""Execute one explicitly dispatched private join run on one owned disposable emulator."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
PACKAGE = 'dev.mixer.android.coordinatorjoin'
PORT = 5586
SERIAL = 'emulator-' + str(PORT)
AVD = 'megpt-parity-api37'
FINGERPRINT = 'google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def owned_identity(command, pid):
    """Require exact PID and individual argv pairs; substrings cannot authorize a stop."""
    tokens = shlex.split(command)
    if not tokens or tokens[0] != str(pid):
        return False
    if not any(Path(token).name in ('emulator', 'qemu-system-aarch64') for token in tokens[1:2]):
        return False
    return all(tokens.count(flag) == 1 and tokens.index(flag) + 1 < len(tokens)
               and tokens[tokens.index(flag) + 1] == value
               for flag, value in [('-port', str(PORT)), ('-avd', AVD)])


def validate_members(members, expected):
    names = [member.name for member in members]
    if len(names) != len(set(names)) or set(names) != set(expected):
        raise ValueError('archive membership mismatch')
    for member in members:
        if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
            raise ValueError('unsafe archive member ' + member.name)


def validate_target(target):
    required = {'ro.kernel.qemu': '1', 'ro.product.model': 'sdk_gphone64_arm64',
                'ro.build.version.sdk': '37', 'ro.product.cpu.abi': 'arm64-v8a',
                'ro.build.fingerprint': FINGERPRINT, 'ro.boot.qemu.avd_name': AVD,
                'sys.boot_completed': '1'}
    if target != required:
        raise ValueError('unsupported actual emulator environment; exact API37 arm64 target required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, help='retained built candidate-N')
    parser.add_argument('--attempt', required=True, help='fresh runtime-N evidence directory')
    parser.add_argument('--execute-native', action='store_true',
                        help='required only after explicit root runtime dispatch; this starts native runtime')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('runtime is NOT RUN; --execute-native requires explicit root dispatch after unlock')
    if not re.fullmatch(r'candidate-[0-9]+', args.build) or not re.fullmatch(r'runtime-[0-9]+', args.attempt):
        parser.error('bounded candidate-N and fresh runtime-N required')
    out = HERE / args.attempt
    out.mkdir()
    work = out / '.build'
    work.mkdir()
    commands = []
    process = None
    cleanup_errors = []
    emulator_log = None
    receipt = {'schema': 1, 'status': 'running', 'commands': commands,
               'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'runnerSHA256': sha(Path(__file__)), 'build': args.build,
               'cleanup': 'not-started', 'physicalTargetsQueried': False,
               'scope': 'bounded actual API37 private ordinary JNI/Swift/coordinator/native subset only; no full native fault/IME/lifecycle, public/signed/physical/FieldLog/store/GA acceptance'}

    def run(name, argv, timeout=30, allow_failure=False):
        argv = list(map(str, argv))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=timeout)
            output, code = result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired as failure:
            output, code = (failure.stdout or b'') + (failure.stderr or b'') + b'\nCOMMAND TIMEOUT\n', -1
        log = out / (name + '.log')
        log.write_bytes(output)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': code, 'output': log.name, 'sha256': sha(log)})
        print(name + ': exit ' + str(code), flush=True)
        if code and not allow_failure:
            raise RuntimeError(name + ' failed: ' + output.decode(errors='replace')[-4000:])
        return code, output

    adb = [SDK / 'platform-tools/adb', '-s', SERIAL]
    try:
        built = HERE / args.build
        metadata = json.loads((built / 'receipt.json').read_text())
        if metadata['status'] != 'actual-private-apk-built-runtime-NOT-RUN' or not metadata['sourceUnchanged']:
            raise ValueError('successful unchanged-source build required')
        archive_path = built / 'built-artifacts.tar.gz'
        if sha(archive_path) != metadata['builtArchiveSHA256']:
            raise ValueError('built archive seal changed')
        artifacts = json.loads((built / 'built-artifacts.json').read_text())
        with tarfile.open(archive_path, 'r:gz') as archive:
            members = archive.getmembers()
            validate_members(members, artifacts)
            archive.extractall(work, members=members, filter='data')
        for relative, expected in artifacts.items():
            if sha(work / relative) != expected['sha256']:
                raise ValueError('built artifact hash changed ' + relative)
        apk = work / 'coordinator-join.apk'
        if sha(apk) != metadata['apkSHA256']:
            raise ValueError('APK identity mismatch')
        receipt.update({'apkSHA256': sha(apk), 'descriptorSHA256': metadata['descriptorSHA256'],
                        'sourceRevision': metadata['sourceRevision'], 'sourceClosureSHA256': metadata['sourceClosureSHA256'],
                        'debugCertificateSHA256': metadata['debugCertificateSHA256'],
                        'buildReceiptSHA256': sha(built / 'receipt.json')})
        for name in ['receipt.json', 'source-lock.json', 'built-artifacts.json']:
            (out / ('build-' + name)).write_bytes((built / name).read_bytes())
        session = json.loads((built / 'inputs/verification/android-native-appearance-v2/emulator-session.json').read_text())
        expected_argv = [str(SDK / 'emulator/emulator'), '-avd', AVD, '-port', str(PORT), '-read-only',
                         '-no-snapshot', '-no-window', '-no-audio', '-no-boot-anim', '-gpu', 'swiftshader_indirect']
        if session['argv'] != expected_argv or session['serial'] != SERIAL:
            raise ValueError('bounded owned-instance contract changed')
        for path, expected in session['metadataSHA256'].items():
            if sha(Path(path)) != expected:
                raise ValueError('unsupported AVD/toolchain metadata drift ' + path)
        receipt['metadataSHA256'] = session['metadataSHA256']
        run('python-version', [sys.executable, '--version'])
        run('adb-version', [SDK / 'platform-tools/adb', 'version'])
        run('emulator-version', [SDK / 'emulator/emulator', '-version'])
        # No global adb target discovery and no command directed to an unrelated serial.
        for port in (PORT, PORT + 1):
            code, output = run('port-before-' + str(port), ['lsof', '-nP', '-iTCP:' + str(port), '-sTCP:LISTEN'], allow_failure=True)
            if code != 1 or output:
                raise ValueError('owned port occupied: refuse to reuse/stop any existing instance')
        _, processes = run('processes-before', ['ps', '-axo', 'pid,ppid,command'])
        if any('-port ' + str(PORT) in line and ('qemu-system' in line or '/emulator' in line)
               for line in processes.decode().splitlines()):
            raise ValueError('existing process uses reserved port; refuse takeover')
        emulator_log = (out / 'emulator.log').open('wb')
        process = subprocess.Popen(expected_argv, cwd=ROOT, stdout=emulator_log, stderr=subprocess.STDOUT)
        receipt['ownedInstance'] = {'pid': process.pid, 'serial': SERIAL, 'argv': expected_argv,
                                    'mode': 'existing AVD read-only/no-snapshot; no persisted data mutation'}
        receipt['cleanup'] = 'pending'
        save(out / 'owned-instance.json', receipt['ownedInstance'])
        deadline = time.monotonic() + 180
        poll = 0
        while True:
            if process.poll() is not None:
                raise RuntimeError('owned emulator exited before boot')
            poll += 1
            code, output = run('boot-' + str(poll), adb + ['shell', 'getprop', 'sys.boot_completed'],
                               timeout=10, allow_failure=True)
            if code == 0 and output.strip() == b'1':
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('bounded boot deadline exceeded')
            time.sleep(3)
        _, identity = run('owned-process-before-use', ['ps', '-p', str(process.pid), '-o', 'pid=,command='])
        if not owned_identity(identity.decode().strip(), process.pid):
            raise ValueError('owned process identity changed')
        target = {}
        for prop in ['ro.kernel.qemu', 'ro.product.model', 'ro.build.version.sdk', 'ro.product.cpu.abi',
                     'ro.build.fingerprint', 'ro.boot.qemu.avd_name', 'sys.boot_completed']:
            _, output = run('target-' + prop.replace('.', '-'), adb + ['shell', 'getprop', prop])
            target[prop] = output.decode().strip()
        receipt['target'] = target
        validate_target(target)
        # Approved disposable instance-only viewport; physical/global settings are never addressed.
        run('owned-viewport-size', adb + ['shell', 'wm', 'size', '1206x2622'])
        run('owned-viewport-density', adb + ['shell', 'wm', 'density', '480'])
        _, font = run('owned-font-scale', adb + ['shell', 'settings', 'get', 'system', 'font_scale'])
        if font.strip() not in (b'1', b'1.0', b'null'):
            raise ValueError('unsupported font scale; do not rewrite preferences')
        run('install-private-apk', adb + ['install', '-r', '--no-incremental', apk], timeout=60)
        _, installed = run('installed-private-package-path', adb + ['shell', 'pm', 'path', PACKAGE])
        path = installed.decode().strip()
        if not re.fullmatch(r'package:/data/app/[A-Za-z0-9_./=+~-]+/base\.apk', path):
            raise ValueError('unexpected installed package path')
        _, installed_sha = run('installed-apk-hash', adb + ['shell', 'sha256sum', path[8:]])
        if installed_sha.decode().split()[0] != metadata['apkSHA256']:
            raise ValueError('installed APK differs from frozen build')
        code, instrument = run('actual-native-join', adb + ['shell', 'am', 'instrument', '-w', '-e',
            'descriptorSHA256', metadata['descriptorSHA256'], PACKAGE + '/dev.mixer.android.CoordinatorJoinInstrumentation'],
            timeout=240, allow_failure=True)
        exported, content = run('native-results-export', adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/native-results.json'], allow_failure=True)
        if exported == 0:
            native = json.loads(content)
            save(out / 'native-results.json', native)
            receipt['native'] = {'status': native['status'], 'checks': native['checks'], 'operations': native['operations']}
            for name, packet in native['packets'].items():
                filename = packet['file']
                if not re.fullmatch(r'(jni|joined)-[a-z]+\.bin', filename):
                    raise ValueError('unexpected packet export')
                _, packet_bytes = run('packet-' + name, adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/' + filename])
                (out / filename).write_bytes(packet_bytes)
                if hashlib.sha256(packet_bytes).hexdigest() != packet['sha256']:
                    raise ValueError('actual native packet export differs')
        else:
            raise RuntimeError('no actual native result; native execution did not qualify')
        if code or b'INSTRUMENTATION_RESULT: status=passed' not in instrument or b'INSTRUMENTATION_CODE: -1' not in instrument:
            raise RuntimeError('actual bounded native assertions failed; output retained')
        if native['status'] != 'passed' or native['operations'] != 8 or not 1 <= native['checks'] <= 256:
            raise RuntimeError('native fixture/result budget mismatch')
        receipt['status'] = 'actual-API37-private-ordinary-join-bounded-subset-passed'
    except BaseException as failure:
        receipt['status'] = 'failed-native-attempt-retained'
        receipt['failure'] = repr(failure)
        raise
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    _, identity = run('owned-process-before-stop', ['ps', '-p', str(process.pid), '-o', 'pid=,command='])
                    if not owned_identity(identity.decode().strip(), process.pid):
                        raise RuntimeError('refuse cleanup: exact owned PID/port/AVD identity no longer matches')
                    run('stop-only-owned-emulator', adb + ['emu', 'kill'], allow_failure=True)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        # Recheck immediately before targeting only our child PID.
                        _, identity = run('owned-process-before-terminate', ['ps', '-p', str(process.pid), '-o', 'pid=,command='])
                        if not owned_identity(identity.decode().strip(), process.pid):
                            raise RuntimeError('refuse PID termination after identity drift')
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            _, identity = run('owned-process-before-kill', ['ps', '-p', str(process.pid), '-o', 'pid=,command='])
                            if not owned_identity(identity.decode().strip(), process.pid):
                                raise RuntimeError('refuse PID kill after identity drift')
                            process.kill()
                            process.wait(timeout=10)
                for port in (PORT, PORT + 1):
                    code, output = run('port-after-' + str(port), ['lsof', '-nP', '-iTCP:' + str(port), '-sTCP:LISTEN'], allow_failure=True)
                    if code != 1 or output:
                        cleanup_errors.append('owned port still occupied: ' + str(port))
                receipt['cleanup'] = 'stopped' if not cleanup_errors and process.poll() is not None else 'failed'
            except BaseException as failure:
                cleanup_errors.append(repr(failure))
                receipt['cleanup'] = 'failed'
            finally:
                if emulator_log is not None:
                    emulator_log.close()
        if cleanup_errors:
            receipt['cleanupErrors'] = cleanup_errors
            receipt['status'] = 'failed-owned-cleanup'
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'receipt.json', receipt)
        save(out / 'artifact-seal.json', {str(path.relative_to(out)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
             for path in sorted(out.rglob('*')) if path.is_file() and '.build' not in path.relative_to(out).parts
             and path.name != 'artifact-seal.json'})
        if cleanup_errors:
            raise RuntimeError('owned instance cleanup failed; inspect retained receipt')


if __name__ == '__main__':
    main()
