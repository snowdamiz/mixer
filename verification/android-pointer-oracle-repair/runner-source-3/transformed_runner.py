#!/usr/bin/env python3
"""Execute one explicitly dispatched private join run on one owned disposable emulator."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import time
execute, stop_group = _accepted_helper.execute, _accepted_helper.stop_group

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILDS = ROOT / 'verification/android-pointer-oracle-repair'
ORIGINAL_RUNNER_SHA256 = '8f4caee8c90fb2ab7348403576e56783e7e9ffd0d13a80850398ca4e34ea78d3'
PROCESS_HELPER_SHA256 = '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
SOURCE_CLOSURE_SHA256 = '9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce'
ARCHIVE_SHA256 = '847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b'
BUILD_BINDINGS = {
    "apk-entries.json": "9fccc1510bad915a97d12d75526fb787b59dda9e3ad51861e1fdd3e383bccd02",
    "apk-entry-delta.json": "f10190961ebd478272880aabec11ecfd1713cb7be8d8e1c4efc4a1de08c4cfdd",
    "artifact-delta.json": "e6425b58427b21045eca0911f265256ea1d7b5c8e0380258fe506995b29fefdd",
    "artifact-seal.json": "a5df3f20d4bd21aa3e68b957ff2fe6297e03cb22152c93ff146bf7f4c58b742d",
    "built-artifacts.json": "8cbdbcca148cba1909fdcdb3eac071c13342346ad2b016113190acf5b3da07b1",
    "built-artifacts.tar.gz": "847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b",
    "post-sign-official-zipalign.log": "43a4399623595f8a4d73214c2b0743e15c6f6cab70bcb2300014ad950d2eb89e",
    "post-sign-packaging.json": "d605699b40f1f9b85581558e80eb65dc30049b461d776e5a0e27da739a7ee7ad",
    "pre-sign-official-zipalign.log": "5c987ce0d154ec99e6666bfa10ea947aeb5c20fb50e0e5ac49122cfce8f7051d",
    "pre-sign-packaging.json": "315b20c7a686353cdbdb3def741eb439197a3b5b71ea5f0c1eeb6b13c06ea1b8",
    "private-debug-signature-cert.log": "80d252035c922ff2c05c87d29b881b9a1574242bb6d3bb24d7de13247b367270",
    "receipt.json": "8079e182a323683cd6d14c558c38a08cb2297faaf679f8ba8ae2d2c86620c1cd",
    "source-lock.json": "5029843a33baf5fa4dfd13525ac3452fe40cdfc3acf301e284f0b7a2e6b9a53a"
}
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


def bind_candidate(built):
    if sha(_helper_path) != PROCESS_HELPER_SHA256:
        raise ValueError('accepted owned process helper drift')
    for name, expected in BUILD_BINDINGS.items():
        if sha(built / name) != expected:
            raise ValueError('pointer frozen build binding drift ' + name)
    return _pointer_bind(built)


class ExtractionCleanupRefused(RuntimeError):
    def __init__(self, message, cleanup):
        super().__init__(message)
        self.cleanup = dict(cleanup, status='failed', failure=message, pathPreserved=True)


def remove_owned_extraction(work, out, expected, ownership):
    """Remove only the exact directory created by this attempt, after a holder check."""
    cleanup = {'path': str(work), 'status': 'not-created'}

    def refuse(message):
        raise ExtractionCleanupRefused(message, cleanup)

    def inspect():
        if (work.parent != out or work.name != '.build' or out.resolve() != out
                or work.is_symlink() or not work.is_dir() or work.resolve() != work):
            refuse('refuse cleanup of an unexpected extraction path')
        current = work.stat()
        if ownership != (current.st_dev, current.st_ino):
            refuse('refuse cleanup of a substituted extraction directory')
        allowed_dirs = {str(parent) for name in expected for parent in Path(name).parents if str(parent) != '.'}
        files = []
        for path in work.rglob('*'):
            mode = path.lstat().st_mode
            relative = str(path.relative_to(work))
            if stat.S_ISLNK(mode):
                refuse('refuse cleanup of extraction with a substituted symlink')
            if stat.S_ISREG(mode):
                if relative not in expected:
                    refuse('refuse cleanup of unexpected files in owned extraction')
                files.append(path)
            elif not stat.S_ISDIR(mode) or relative not in allowed_dirs:
                refuse('refuse cleanup of an unexpected directory or special file in owned extraction')
        return files

    if not work.exists() and not work.is_symlink():
        return cleanup
    files = inspect()
    cleanup.update({'files': len(files), 'bytes': sum(path.stat().st_size for path in files),
                    'ownedDevice': ownership[0], 'ownedInode': ownership[1]})
    argv = ['/usr/sbin/lsof', '-nP', '+D', str(work)]
    checked = execute(argv, cwd=ROOT, timeout=30)
    log = out / 'extraction-open-holders.log'
    index = 1
    while log.exists() or log.is_symlink():
        index += 1
        log = out / ('extraction-open-holders-' + str(index) + '.log')
    with log.open('xb') as stream:
        stream.write(checked.stdout)
    cleanup['openHoldersCheck'] = {'argv': argv, 'cwd': str(ROOT), 'exitCode': checked.returncode,
                                 'output': log.name, 'outputSHA256': sha(log),
                                 'toolSHA256': sha(Path(argv[0])),
                                 'ownedCommandGroupCleanup': checked.groupCleanup}
    if checked.returncode != 1 or checked.stdout:
        refuse('open holder or unavailable open-holder check: extraction preserved')
    inspect()  # Recheck identity and membership immediately before deleting our directory.
    shutil.rmtree(work)
    if work.exists() or work.is_symlink():
        refuse('owned extraction remains after removal')
    cleanup.update({'status': 'removed', 'method': 'Python shutil.rmtree after no-open-holder result',
                    'pathAbsentAfterCleanup': True})
    return cleanup


def owned_identity(command, pid):
    """Require exact PID and individual argv pairs; substrings cannot authorize a stop."""
    return _wifi_identity(command, pid)


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
    parser.add_argument('--build', required=True, help='frozen private actual-pointer candidate-5 only')
    parser.add_argument('--attempt', required=True, help='fresh runtime-N evidence directory')
    parser.add_argument('--execute-native', action='store_true',
                        help='required only after explicit root runtime dispatch; headless native runtime starts')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('runtime is NOT RUN; --execute-native requires explicit root dispatch')
    if args.build != 'candidate-5' or not re.fullmatch(r'runtime-[0-9]+', args.attempt):
        parser.error('bound pointer candidate-5 and fresh runtime-N required')
    out = _pointer_runtime_directory(args.attempt)
    out.parent.mkdir(exist_ok=True)
    out.mkdir()
    work = out / '.build'
    ownership = None
    artifacts = {}
    commands = []
    process = None
    cleanup_errors = []
    emulator_log = None
    emulator_reader = None
    output_budget = _output.Budget()
    receipt = {'schema': 1, 'status': 'running', 'commands': commands,
               'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'runnerSHA256': sha(Path(__file__)), 'build': args.build,
               'originalFrozenRunnerSHA256': ORIGINAL_RUNNER_SHA256,
               'ownedProcessHelperSHA256': sha(_helper_path), 'adaptation': _ADAPTATION,
               'runnerSourceDirectory': str(HERE.relative_to(ROOT)),
               'buildSourceDirectory': str((BUILDS / args.build).relative_to(ROOT)),
               'nativeDispatch': 'explicit root dispatch; headless subset has no desktop-unlock dependency',
               'cleanup': 'not-started', 'physicalTargetsQueried': False,
               'scope': 'bounded actual API37 private pointer delivery/state subset only; internal callbacks unobserved; native IME/accessibility/public/signed/physical/FieldLog/store/operational/GA pending'}

    def run(name, argv, timeout=30, allow_failure=False):
        argv = list(map(str, argv))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = execute(argv, cwd=ROOT, timeout=timeout)
        output, code = result.stdout, result.returncode
        log = out / (name + '.log')
        output_budget.write(log, output, cleanup=name in _output.CLEANUP_NAMES)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': code, 'output': log.name, 'sha256': sha(log),
                         'ownedCommandGroupCleanup': result.groupCleanup})
        print(name + ': exit ' + str(code), flush=True)
        if output_budget.overflow and name not in _output.CLEANUP_NAMES:
            raise RuntimeError('32MiB runner log budget exceeded; cleanup reserved and failure retained')
        if code and not allow_failure:
            raise RuntimeError(name + ' failed: ' + output.decode(errors='replace')[-4000:])
        return code, output

    adb = [SDK / 'platform-tools/adb', '-s', SERIAL]
    try:
        work.mkdir()
        created = work.stat()
        ownership = (created.st_dev, created.st_ino)
        built = BUILDS / args.build
        metadata = bind_candidate(built)
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
                        'buildReceiptSHA256': sha(built / 'receipt.json'),
                        'packagingPreDispatch': metadata['packagingPreDispatch']})
        for name in ['receipt.json', 'source-lock.json', 'built-artifacts.json']:
            (out / ('build-' + name)).write_bytes((built / name).read_bytes())
        session = json.loads((built / 'inputs/verification/android-native-appearance-v2/emulator-session.json').read_text())
        expected_argv = [str(SDK / 'emulator/emulator'), '-avd', AVD, '-port', str(PORT), '-read-only',
                         '-no-snapshot', '-no-window', '-no-audio', '-no-boot-anim', '-gpu', 'swiftshader_indirect']
        if session['argv'] != expected_argv or session['serial'] != SERIAL:
            raise ValueError('bounded owned-instance contract changed')
        expected_argv += ['-feature', '-WiFiPacketStream']
        for path, expected in session['metadataSHA256'].items():
            if sha(Path(path)) != expected:
                raise ValueError('unsupported AVD/toolchain metadata drift ' + path)
        receipt['metadataSHA256'] = session['metadataSHA256']
        _, revision = run('runner-source-revision', ['git', 'rev-parse', 'HEAD'])
        _, tree = run('runner-source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        receipt['adaptation']['runnerSourceRevision'] = revision.decode().strip()
        receipt['adaptation']['runnerSourceTree'] = tree.decode().strip()
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
        process = subprocess.Popen(expected_argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        emulator_reader = _output.Reader(process, emulator_log, output_budget)
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
        _, identity = run('owned-process-before-use', ['ps', '-p', str(process.pid), '-o', 'pid=,pgid=,command='])
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
        preinstall = bind_candidate(built)
        if preinstall['sourceClosureSHA256'] != metadata['sourceClosureSHA256'] or preinstall['apkSHA256'] != metadata['apkSHA256'] or sha(apk) != metadata['apkSHA256']:
            raise ValueError('preinstall frozen source/APK identity differs')
        save(out / 'source-identity-preinstall.json', {'sourceRevision': metadata['sourceRevision'], 'sourceTree': metadata['sourceTree'],
            'sourceClosureSHA256': metadata['sourceClosureSHA256'], 'sourceInputsRechecked': 105, 'liveNativeAndSDKInputsRechecked': 88,
            'apkSHA256': sha(apk), 'scope': 'frozen source plus unchanged live native/SDK content; disjoint repository commits do not alter the content authority'})
        _, signature = run('apk-apksigner-preinstall', [SDK / 'build-tools/37.0.0/apksigner', 'verify', '--verbose', '--print-certs', apk])
        certificates = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', signature.decode())
        if certificates != [metadata['debugCertificateSHA256']]:
            raise ValueError('preinstall private APK signature certificate differs')
        save(out / 'apk-packaging-preinstall.json', _packaging_check_path(apk))
        run('apk-zipalign-preinstall', [SDK / 'build-tools/37.0.0/zipalign', '-c', '-P', '16', '-v', '4', apk])
        run('install-private-apk', adb + ['install', '-r', '--no-incremental', apk], timeout=60)
        _, installed = run('installed-private-package-path', adb + ['shell', 'pm', 'path', PACKAGE])
        path = installed.decode().strip()
        if not re.fullmatch(r'package:/data/app/[A-Za-z0-9_./=+~-]+/base\.apk', path):
            raise ValueError('unexpected installed package path')
        _, installed_sha = run('installed-apk-hash', adb + ['shell', 'sha256sum', path[8:]])
        if installed_sha.decode().split()[0] != metadata['apkSHA256']:
            raise ValueError('installed APK differs from frozen build')
        code, instrument = run('actual-native-pointer', adb + ['shell', 'am', 'instrument', '-w',
            '-e', 'descriptorSHA256', metadata['descriptorSHA256'],
            '-e', 'apkSHA256', metadata['apkSHA256'],
            '-e', 'sourceClosureSHA256', metadata['sourceClosureSHA256'],
            '-e', 'sourceRevision', metadata['sourceRevision'],
            '-e', 'sourceTree', metadata['sourceTree'],
            '-e', 'fixtureSHA256', metadata['fixtureSHA256'],
            PACKAGE + '/dev.mixer.android.CoordinatorJoinInstrumentation'], timeout=180, allow_failure=True)
        exported, content = run('native-results-export', adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/native-results.json'], allow_failure=True)
        if exported == 0:
            native = json.loads(content)
            save(out / 'native-results.json', native)
            receipt['native'] = {'status': native['status'], 'checks': native['checks'], 'operations': native['operations']}
            exports = native.get('exports', {})
            if not isinstance(exports, dict) or not 1 <= len(exports) <= 128:
                raise ValueError('bounded private pointer export index required')
            export_bytes = 0
            for filename, value in exports.items():
                if not re.fullmatch(r'pointer-[a-z0-9-]+\.(json|bin|jsonl)', filename):
                    raise ValueError('unsafe pointer export name')
                if set(value) != {'bytes', 'sha256'} or type(value['bytes']) is not int or not 0 <= value['bytes'] <= 8388608 or not re.fullmatch(r'[0-9a-f]{64}', value['sha256']):
                    raise ValueError('invalid pointer export binding')
                export_bytes += value['bytes']
                if export_bytes > 33554432:
                    raise ValueError('32MiB private metadata export budget exceeded')
                _, payload = run('export-' + filename, adb + ['exec-out', 'run-as', PACKAGE, 'cat', 'files/' + filename])
                if len(payload) != value['bytes'] or hashlib.sha256(payload).hexdigest() != value['sha256']:
                    raise ValueError('private pointer export differs from native binding')
                if filename.endswith('.bin') and len(payload) > 262144:
                    raise ValueError('packet exceeds 256KiB bound')
                (out / filename).write_bytes(payload)
            _pointer_validate_native(native, out, metadata)
        else:
            raise RuntimeError('no actual native result; native execution did not qualify')
        if code or b'INSTRUMENTATION_RESULT: status=passed' not in instrument or b'INSTRUMENTATION_CODE: -1' not in instrument:
            raise RuntimeError('actual bounded native assertions failed; output retained')
        if native['status'] != 'passed' or native['operations'] != 20 or not 1 <= native['checks'] <= 512:
            raise RuntimeError('native fixture/result budget mismatch')
        receipt['status'] = 'actual-API37-private-pointer-bounded-subset-passed'
    except BaseException as failure:
        receipt['status'] = 'failed-native-attempt-retained'
        receipt['failure'] = repr(failure)
        raise
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    _, identity = run('owned-process-before-stop', ['ps', '-p', str(process.pid), '-o', 'pid=,pgid=,command='])
                    if not owned_identity(identity.decode().strip(), process.pid):
                        raise RuntimeError('refuse cleanup: exact owned PID/port/AVD identity no longer matches')
                    run('stop-only-owned-emulator', adb + ['emu', 'kill'], allow_failure=True)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        # Recheck immediately before targeting only our child PID.
                        _, identity = run('owned-process-before-terminate', ['ps', '-p', str(process.pid), '-o', 'pid=,pgid=,command='])
                        if not owned_identity(identity.decode().strip(), process.pid):
                            raise RuntimeError('refuse PID termination after identity drift')
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            _, identity = run('owned-process-before-kill', ['ps', '-p', str(process.pid), '-o', 'pid=,pgid=,command='])
                            if not owned_identity(identity.decode().strip(), process.pid):
                                raise RuntimeError('refuse PID kill after identity drift')
                            process.kill()
                            process.wait(timeout=10)
                receipt['ownedEmulatorGroupCleanup'] = stop_group(process.pid)
                for port in (PORT, PORT + 1):
                    code, output = run('port-after-' + str(port), ['lsof', '-nP', '-iTCP:' + str(port), '-sTCP:LISTEN'], allow_failure=True)
                    if code != 1 or output:
                        cleanup_errors.append('owned port still occupied: ' + str(port))
                receipt['cleanup'] = 'stopped' if not cleanup_errors and process.poll() is not None else 'failed'
            except BaseException as failure:
                cleanup_errors.append(repr(failure))
                receipt['cleanup'] = 'failed'
            finally:
                if emulator_reader is not None:
                    try:
                        emulator_reader.finish()
                    except BaseException as failure:
                        cleanup_errors.append(repr(failure))
                        receipt['cleanup'] = 'failed'
                if emulator_log is not None:
                    emulator_log.close()
        extraction_failure = None
        try:
            receipt['extractionCleanup'] = remove_owned_extraction(work, out, artifacts, ownership)
        except BaseException as failure:
            extraction_failure = failure
            receipt['extractionCleanup'] = getattr(failure, 'cleanup', {
                'status': 'failed', 'failure': repr(failure), 'path': str(work),
                'pathPreserved': work.exists() or work.is_symlink()})
            receipt['status'] = 'failed-owned-extraction-cleanup'
        if cleanup_errors:
            receipt['cleanupErrors'] = cleanup_errors
            receipt['status'] = 'failed-owned-cleanup'
        receipt['outputBudget'] = output_budget.report()
        if output_budget.overflow:
            receipt['status'] = 'failed-runner-output-budget'
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / 'receipt.json', receipt)
        save(out / 'artifact-seal.json', {str(path.relative_to(out)): {'bytes': path.stat().st_size, 'sha256': sha(path)}
             for path in sorted(out.rglob('*')) if path.is_file() and '.build' not in path.relative_to(out).parts
             and path != out / 'artifact-seal.json'})
        if cleanup_errors:
            raise RuntimeError('owned instance cleanup failed; inspect retained receipt')
        if extraction_failure is not None:
            raise RuntimeError('owned extraction cleanup failed; inspect retained receipt') from extraction_failure


if __name__ == '__main__':
    main()
