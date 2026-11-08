#!/usr/bin/env python3
"""One root-dispatched API28 runtime attempt. No build, signing, or retry path."""
import argparse
import array
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import shutil
import socket
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
SDK = Path('/opt/homebrew/share/android-commandlinetools')
ADB = SDK / 'platform-tools/adb'
EMULATOR = SDK / 'emulator/emulator'
AVDMANAGER = SDK / 'cmdline-tools/latest/bin/avdmanager'
PACKAGE = 'dev.mixer.android.lowerapi.test'
COMPONENT = PACKAGE + '/dev.mixer.android.NativeLowerApiCompatibilityInstrumentation'
APK_SHA = '5d092e8e78ed1a2c8c32c9330f7d6b6d52932a2311aa2ccb30e2709902fbb258'
LIFECYCLE_SHA = '8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
SOURCE_SHA = 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'
ADAPTER_SHA = 'ee9414d3b68f9d66ba275c93339018e5eaebb161a7dc25d7056538c652305d89'
ADB_SHA = '1811e253b21b12cbfda7201ebaf86c10e7ddcb5c606a7a81f7c82b4c429c2d3b'
SCREENSHOTS = ('real-mixer-api28.png', 'legacy-harness-api28.png')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def load(path):
    return json.loads(Path(path).read_text())


def lifecycle():
    require(identity(HERE / 'cleanup_control.py')['sha256'] == LIFECYCLE_SHA,
            'reviewed lifecycle bytes changed')
    spec = importlib.util.spec_from_file_location('api28_exact_lifecycle', HERE / 'cleanup_control.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_bindings(frozen):
    """Read only exact selected inputs; never walk baseline or held scratch."""
    for name, expected in frozen['bindings'].items():
        require(identity(name) == {k: expected[k] for k in ('bytes', 'sha256')},
                'input drift: ' + name)
        if 'realPath' in expected:
            require(str(Path(name).resolve()) == expected['realPath'], 'tool path drift: ' + name)
    for directory, expected in frozen['topology'].items():
        actual = sorted(str(p.relative_to(directory)) for p in Path(directory).rglob('*') if p.is_file())
        require(actual == expected, 'tool/image inventory drift: ' + directory)
    binding = load(BASE / 'native-custody-premise/prepared-source-binding.json')
    spec = importlib.util.spec_from_file_location('api28_source_inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    profile = checker.load_profile(ROOT)
    actual = checker.source_inputs(profile)
    require(len(actual) == 101 and actual == binding['canonicalInputs']
            and checker.source_digest(actual) == SOURCE_SHA, 'current canonical product101 drift')
    require(profile['adapter_files'] == binding['projections']['adapter']['files']
            and profile['adapter_compatibility_sha256'] == ADAPTER_SHA, 'adapter24 drift')
    packet = load(BASE / 'pair9-api28-packaging/runtime-packet.json')
    review = load(BASE / 'pair9-api28-package-review/result.json')
    require(packet['apk']['sha256'] == APK_SHA and packet['apk']['bytes'] == 86284162,
            'APK packet identity')
    require(review['verdict'] == 'ACCEPT' and review['apk'] == {'bytes': 86284162, 'sha256': APK_SHA},
            'package acceptance')
    require(review['DEX']['classes'] == 216 and review['DEX']['productDefinitions'] == 389
            and review['DEX']['harnessDefinitions'] == 12 and not review['DEX']['intersection'],
            'package definitions')
    return packet


def admission(review, frozen, self_sha):
    require(review.get('verdict') == 'ACCEPT' and review.get('scope') == 'ONE_API28_ARM64_RUNTIME_ATTEMPT',
            'independent API28 controller ACCEPT required')
    require(review.get('controllerSHA256') == self_sha
            and review.get('lifecycleSHA256') == LIFECYCLE_SHA
            and review.get('packetSHA256') == identity(HERE / 'controller-packet.json')['sha256'],
            'independent review exact bytes mismatch')
    for mode in ('normal', 'optimized'):
        control = load(HERE / ('host-' + mode + '.json'))
        require(control['status'] == 'passed' and control['mode'] == mode
                and control['controllerSHA256'] == self_sha
                and control['lifecycleSHA256'] == LIFECYCLE_SHA
                and control['packetSHA256'] == identity(HERE / 'controller-packet.json')['sha256']
                and control['controlsSHA256'] == identity(HERE / 'host_controls.py')['sha256']
                and control['realNativeCommands'] == 0, 'host control admission: ' + mode)
        require(review.get('hostReceipts', {}).get(mode) == identity(HERE / ('host-' + mode + '.json')),
                'review must bind both tested host receipts')
    require(frozen['bounds'] == {'bootSeconds': 180, 'instrumentationSeconds': 120, 'totalSeconds': 600},
            'runtime bounds changed')


def runtime_identity(properties, avd):
    require(properties['ro.kernel.qemu'] == '1', 'target is not qemu')
    require(properties['ro.boot.qemu.avd_name'] == avd, 'exact owned AVD mismatch')
    require(properties['ro.build.version.sdk'] == '28', 'runtime API mismatch')
    require(properties['ro.product.cpu.abi'] == 'arm64-v8a', 'runtime ABI mismatch')


def instrumentation_result(output, app_log):
    require('INSTRUMENTATION_CODE: -1' in output and 'INSTRUMENTATION_FAILED' not in output,
            'instrumentation did not finish successfully')
    require(not re.search(r'(?im)^INSTRUMENTATION_(?:RESULT|STATUS):\s*(?:failure|failureStage|failureTrace|cleanupFailure)=', output),
            'instrumentation stage or cleanup failed')
    fields = dict(re.findall(r'^INSTRUMENTATION_RESULT: ([^=\s]+)=(.*)$', output, re.M))
    require(fields.get('gate') == 'PAIR8-LOWER-API-ART-LINKAGE' and fields.get('sdk') == '28'
            and fields.get('abi') == 'arm64-v8a', 'frozen harness result identity')
    count = int(fields.get('checks', '0'))
    assertions = re.findall(r'\bMixerLowerApi\s*:\s*PASS (.*)', app_log)
    require(count > 0 and len(assertions) == count, 'not every assertion retained in app log')
    for text in ('real JNI/Swift session is nonzero', 'real Observer exactly refuses below36',
                 'motion factory exactly refuses below33 without linkage failure',
                 'all exercised paths completed without ART linkage errors'):
        require(text in assertions, 'required assertion missing: ' + text)
    return {'fields': fields, 'assertions': assertions, 'checks': count,
            'historicalEmittedPair': 8, 'actualAPKSourcePair': 9, 'apkSHA256': APK_SHA}


def cleanup(commands, scratch):
    """The exact reviewed module alone owns process custody and scratch removal."""
    try:
        result = commands.cleanup(scratch)
        listener = getattr(commands, 'api28_listener', None)
        if listener is not None and result.get('allTerminalCustody'):
            listener.close()
            result['retainedListenerClosed'] = True
        return result
    except BaseException as error:
        return {'allTerminalCustody': False, 'scratchRemoved': False, 'cleanupError': repr(error)}


def sealed_adb(work):
    require(identity(ADB)['sha256'] == ADB_SHA, 'selected ADB binary drift')
    target = work / 'adb'
    with target.open('xb') as stream:
        stream.write(ADB.read_bytes())
    target.chmod(0o500)
    require(identity(target)['sha256'] == ADB_SHA, 'sealed ADB binary drift')
    return target


def owned_server_alive(commands, server, binary):
    # No poll after UNKNOWN; the unchanged lifecycle alone owns process custody.
    require(not commands.hold and not commands.limit and not getattr(commands, 'api28_server_lost', False), 'owned server admission closed')
    require(time.monotonic() < commands.deadline - commands.cleanup_seconds, 'owned server deadline')
    dead = commands.reaped(server)
    if dead:
        commands.api28_server_lost = True
    require(not commands.hold and not dead, 'owned ADB server lost; no replacement')
    require(identity(binary)['sha256'] == ADB_SHA, 'sealed ADB binary drift')


def start_owned_server(commands, work, listener, binary, serial):
    # Retaining this non-REUSEPORT listener prevents foreign rebinding even after server death.
    commands.api28_listener = listener
    token = os.urandom(32).hex()
    channel_path = work / 'server-fd.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        channel.bind(str(channel_path))
        channel.listen(1)
        channel.settimeout(min(5, max(.001, commands.deadline - time.monotonic() - commands.cleanup_seconds)))
        server = commands.start('owned-adb-server', [sys.executable, '-I', '-B', HERE / 'server_fd_exec.py',
            channel_path, token, binary, ADB_SHA, serial, listener.getsockname()[1]], work, long_lived=True)
        connection, _ = channel.accept()
        with connection:
            connection.settimeout(5)
            request = bytearray()
            while len(request) < 64:
                data = connection.recv(64 - len(request))
                require(data, 'descriptor handoff disconnected')
                request.extend(data)
            require(bytes(request) == token.encode('ascii'), 'foreign descriptor client refused')
            require(not commands.hold and not commands.reaped(server), 'owned server exited before handoff')
            require(not commands.hold, 'descriptor handoff custody unknown')
            count = connection.sendmsg([b'F'], [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                               array.array('i', [listener.fileno()]))])
            require(count == 1, 'descriptor handoff failed')
    channel_path.unlink()
    return server


def retain_screenshots(commands, adb, out, receipt):
    """Only copy bytes already authored by this attempt's harness, within existing budgets."""
    evidence = receipt.setdefault('screenshots', {})
    receipt['screenshotsNeedIndependentVisualReview'] = True
    instrumentation = next((item for item in commands.records if item['label'] == 'exact-api28-instrumentation'), None)
    if not instrumentation or not instrumentation.get('terminal_custody'):
        receipt['screenshotRetrievalSkipped'] = 'instrumentation custody not terminal'
        return
    for name in SCREENSHOTS:
        if commands.hold or commands.limit or getattr(commands, 'api28_server_lost', False) or time.monotonic() >= commands.deadline - commands.cleanup_seconds:
            evidence[name] = {'status': 'pending', 'reason': 'custody/output/deadline admission closed'}
            break
        try:
            adb('retrieve-' + name, ['exec-out', 'run-as', PACKAGE, 'cat', 'files/' + name])
            data = bytes(commands.owned[-1]['buffers']['stdout'])
            require(data.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in data[-16:], 'invalid screenshot: ' + name)
            (out / name).write_bytes(data)
            evidence[name] = {'status': 'retained', **identity(out / name)}
        except Exception as error:
            evidence[name] = {'status': 'unavailable', 'reason': repr(error)}
    receipt['screenshotsNeedIndependentVisualReview'] = True


def execute(commands, work, out, packet, deadline, receipt, flush):
    env = commands.env
    reservations = []
    binary = sealed_adb(work)
    receipt['status'] = 'failed'
    def run(label, args, timeout=45, allowed=(0,)):
        try:
            return commands.run(label, args, work, timeout, allowed)
        finally:
            receipt['commands'] = commands.records
            flush()
    def reserve(port):
        sock = socket.socket()
        try:
            sock.bind(('127.0.0.1', port)); sock.listen(1)
        except BaseException:
            sock.close(); raise
        reservations.append(sock)
        return sock.getsockname()[1]
    def adb(label, args, timeout=45, allowed=(0,)):
        owned_server_alive(commands, server, binary)
        try:
            return run(label, [binary, '-H', '127.0.0.1', '-P', serverport, '-s', serial, *args], timeout, allowed)
        finally:
            owned_server_alive(commands, server, binary)
    try:
        # No port scan/fallback: exactly one requested pair and one ephemeral private server.
        port = 5678
        reserve(port); reserve(port + 1); serverport = reserve(0)
        serial = 'emulator-' + str(port)
        avd = 'mixer_pair9_api28_' + work.name.rsplit('-', 1)[-1]
        avdpath = work / 'avds' / (avd + '.avd')
        for name in ('avds', 'android', 'tmp'):
            (work / name).mkdir()
        for name in ('ANDROID_PREFS_ROOT', 'ANDROID_SDK_HOME', 'ADB_SERVER_SOCKET', 'ANDROID_SERIAL',
                     'ANDROID_ADB_SERVER_ADDRESS', 'ANDROID_ADB_SERVER_PORT', 'ADB_SERVER_PORT'):
            env.pop(name, None)
        env.update(ANDROID_HOME=str(SDK), ANDROID_SDK_ROOT=str(SDK),
                   ANDROID_AVD_HOME=str(work / 'avds'), ANDROID_EMULATOR_HOME=str(work / 'android'),
                   ANDROID_USER_HOME=str(work / 'android'), TMPDIR=str(work / 'tmp'),
                   ADB_SERVER_SOCKET='tcp:127.0.0.1:' + str(serverport),
                   ANDROID_ADB_SERVER_ADDRESS='127.0.0.1',
                   ANDROID_ADB_SERVER_PORT=str(serverport), ADB_SERVER_PORT=str(serverport),
                   ADB_VENDOR_KEYS=str(work / 'android/adbkey'), ADB_LIBUSB='0', ADB_USB='0')
        receipt.update(targetSerial=serial, adbServerPort=serverport, emulatorPort=port,
                       avd={'name': avd, 'path': str(avdpath)}, nativeInstancesStarted=0)
        # Runtime keys belong only to this fresh private server; no APK signing keys.
        run('owned-adb-key', [binary, 'keygen', work / 'android/adbkey'])
        run('owned-avd-create', [AVDMANAGER, '--verbose', 'create', 'avd', '--name', avd,
            '--path', avdpath, '--package', 'system-images;android-28;default;arm64-v8a',
            '--device', 'pixel_6'], 120)
        with (avdpath / 'config.ini').open('a') as stream:
            stream.write('\nhw.cpu.ncore=2\nhw.ramSize=2048\ndisk.dataPartition.size=2G\n')
        save(out / 'owned-avd-config.json', {'config': (avdpath / 'config.ini').read_text()})
        listener = reservations.pop()
        commands.api28_listener = listener
        for sock in reservations:
            sock.close()
        reservations.clear()
        server = start_owned_server(commands, work, listener, binary, serial)
        receipt['serverTransport'] = {'host': '127.0.0.1', 'retainedListener': True,
                                      'sameServerClientSHA256': ADB_SHA, 'binary': str(binary)}
        commands.pause(1)
        owned_server_alive(commands, server, binary)
        emulator = commands.start('owned-emulator', [EMULATOR, '-avd', avd, '-port', port,
            '-no-window', '-no-audio', '-no-boot-anim', '-no-snapshot', '-cores', '2',
            '-memory', '2048', '-gpu', 'swiftshader', '-no-metrics', '-no-sim'], work, long_lived=True)
        receipt['nativeInstancesStarted'] = 1
        flush()
        boot_end = min(time.monotonic() + 180, deadline - 160)
        booted = False
        commands.deadline = boot_end
        try:
            for index in range(80):
                if time.monotonic() >= boot_end - commands.cleanup_seconds or commands.reaped(emulator):
                    break
                if adb('boot-' + str(index), ['shell', 'getprop', 'sys.boot_completed'], 8, (0, 1)) == '1':
                    booted = True; break
                commands.pause(2)
        finally:
            commands.deadline = deadline
        require(booted, 'boot deadline exhausted; no retry')
        devices = adb('private-server-devices', ['devices'])
        require([line for line in devices.splitlines() if '\t' in line] == [serial + '\tdevice'],
                'private server must contain exactly the owned device')
        props = {name: adb('identity-' + name, ['shell', 'getprop', name]) for name in (
            'ro.kernel.qemu', 'ro.boot.qemu.avd_name', 'ro.build.version.sdk',
            'ro.product.cpu.abi', 'ro.build.fingerprint')}
        receipt['observedRuntime'] = props
        runtime_identity(props, avd)
        receipt['installOutput'] = adb('install-accepted-apk', ['install', '--no-streaming',
            '--no-incremental', packet['apk']['path']], 120)
        require('Success' in receipt['installOutput'], 'APK install failure')
        uid_text = adb('installed-uid', ['shell', 'pm', 'list', 'packages', '-U', PACKAGE])
        uid = re.fullmatch(r'package:' + re.escape(PACKAGE) + r' uid:(\d+)', uid_text)
        require(uid, 'exact installed UID missing')
        owned_server_alive(commands, server, binary)
        logcat = commands.start('app-logcat-before-startup', [binary, '-H', '127.0.0.1', '-P', serverport, '-s', serial,
            'logcat', '-v', 'threadtime', '--uid=' + uid[1], '*:V'], work, long_lived=True)
        commands.pause(1)
        require(not commands.reaped(logcat), 'startup logs unavailable')
        receipt['logCaptureStartedBeforeInstrumentation'] = True
        try:
            output = adb('exact-api28-instrumentation', ['shell', 'am', 'instrument', '-w', '-r', COMPONENT], 120)
            commands.pause(1)
            logs = adb('all-assertion-logs', ['logcat', '-d', '-v', 'threadtime', '--uid=' + uid[1], '*:V'])
            receipt['result'] = instrumentation_result(output, logs)
            receipt['status'] = 'passed-development-runtime'
        finally:
            receipt['instrumentationOutput'] = commands.captured('exact-api28-instrumentation')
            receipt['startupAppLog'] = commands.captured('app-logcat-before-startup')
            try:
                retain_screenshots(commands, adb, out, receipt)
            finally:
                if any(receipt.get('screenshots', {}).get(name, {}).get('status') != 'retained' for name in SCREENSHOTS):
                    receipt['status'] = 'failed'
                save(out / 'runtime-diagnostics-before-cleanup.json', receipt)
    finally:
        for sock in reservations:
            sock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-controller-sha256', required=True)
    parser.add_argument('--independent-review', required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('600s total deadline')))
    signal.alarm(600)
    self_sha = identity(__file__)['sha256']
    require(args.reviewed_controller_sha256 == self_sha, 'reviewed controller hash mismatch')
    frozen = load(HERE / 'controller-packet.json')
    admission(load(args.independent_review), frozen, self_sha)
    packet = verify_bindings(frozen)
    # Exclusive durable attempt directory is never removed, including failure before boot.
    out = HERE / 'runtime-attempt'
    out.mkdir(exist_ok=False)
    work = Path(tempfile.mkdtemp(prefix='mixer-pair9-api28-', dir='/tmp'))
    c = lifecycle()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               JAVA_HOME='/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
    commands = c.Commands(out, env, deadline=started + 600)
    receipt = {'status': 'failed', 'sourcePair': 9, 'apkSHA256': APK_SHA, 'scratch': str(work),
               'controllerSHA256': self_sha, 'lifecycleSHA256': LIFECYCLE_SHA, 'commands': [],
               'python': sys.version, 'nativeAcceptance': False, 'gaAcceptance': False,
               'physicalPhones': 'DISCONNECTED', 'stages': packet['instrumentationStageLiterals'],
               'stageEvidence': 'frozen harness PASS logs and failureStage; no invented stage callbacks'}
    def flush():
        save(out / 'receipt.json', receipt)
    try:
        flush()
        git = frozen['gitPath']
        receipt['currentHEAD'] = commands.run('current-head', [git, '-C', ROOT, 'rev-parse', 'HEAD'], work)
        receipt['currentTree'] = commands.run('current-tree', [git, '-C', ROOT, 'rev-parse', 'HEAD^{tree}'], work)
        receipt['gitVersion'] = commands.run('git-version', [git, '--version'], work)
        for label, tool, version in [('adb', ADB, 'version'), ('emulator', EMULATOR, '-version')]:
            receipt[label + 'Version'] = commands.run(label + '-version', [tool, version], work)
        execute(commands, work, out, packet, started + 600, receipt, flush)
    except BaseException as error:
        receipt.update(status='failed', failure=repr(error), traceback=traceback.format_exc())
    finally:
        receipt['cleanup'] = cleanup(commands, work)
        if not receipt['cleanup'].get('allTerminalCustody') or not receipt['cleanup'].get('scratchRemoved'):
            receipt['status'] = 'failed'
        # UNKNOWN prohibits further process actions. Pure selected-file postflight is safe.
        try:
            verify_bindings(frozen)
            receipt['postflightStable'] = True
        except BaseException as error:
            receipt.update(status='failed', postflightStable=False, postflightError=repr(error))
        receipt.update(commands=commands.records, elapsedSeconds=time.monotonic() - started,
                       privateADBKeysRemoved=not (work / 'android/adbkey').exists(),
                       screenshotsNeedIndependentVisualReview=True)
        flush()
        signal.alarm(0)
    return 0 if receipt['status'] == 'passed-development-runtime' else 1


if __name__ == '__main__':
    sys.exit(main())
