#!/usr/bin/env python3
"""Root-dispatched boot-only experiment; one process-local Wi-Fi fallback delta."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'probe-contract.json'
CONTRACT_SHA256 = '954c48ab47b5b3da0c3aaca3b0e65b7c0727771dc8a9b39234e617bdb02bbec4'
PORT = 5586
SERIAL = 'emulator-5586'
AVD = 'megpt-parity-api37'
SDK = Path('/opt/homebrew/share/android-commandlinetools')
EMULATOR = str(SDK / 'emulator/emulator')
HEADLESS = str(SDK / 'emulator/qemu/darwin-aarch64/qemu-system-aarch64-headless')
PROPS = {
    'ro.kernel.qemu': '1',
    'ro.product.model': 'sdk_gphone64_arm64',
    'ro.build.version.sdk': '37',
    'ro.product.cpu.abi': 'arm64-v8a',
    'ro.build.fingerprint': 'google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys',
    'ro.boot.qemu.avd_name': AVD,
    'sys.boot_completed': '1',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def expected_argv():
    return [EMULATOR, '-avd', AVD, '-port', str(PORT), '-read-only', '-no-snapshot',
            '-no-window', '-no-audio', '-no-boot-anim', '-gpu', 'swiftshader_indirect',
            '-feature', '-WiFiPacketStream']


def owned_identity(output, pid, group):
    """Exact installed executable and PID/group/argv pairs; no substring authority."""
    fields = output.strip().split(None, 2)
    if len(fields) != 3 or fields[:2] != [str(pid), str(group)]:
        return False
    try:
        tokens = shlex.split(fields[2])
    except ValueError:
        return False
    if not tokens or tokens[0] not in (EMULATOR, HEADLESS):
        return False
    for flag, value in (('-avd', AVD), ('-port', str(PORT)),
                        ('-gpu', 'swiftshader_indirect'), ('-feature', '-WiFiPacketStream')):
        if tokens.count(flag) != 1:
            return False
        at = tokens.index(flag)
        if at + 1 >= len(tokens) or tokens[at + 1] != value:
            return False
    return all(tokens.count(flag) == 1 for flag in (
        '-read-only', '-no-snapshot', '-no-window', '-no-audio', '-no-boot-anim', '-WiFiPacketStream'))


def reserved_process(output):
    """Refuse takeover of an existing emulator using the reserved console port."""
    for line in output.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) != 3:
            continue
        try:
            tokens = shlex.split(fields[2])
        except ValueError:
            # An unparseable emulator entry cannot authorize a new reservation.
            if '/emulator' in fields[2] or 'qemu-system' in fields[2]:
                return True
            continue
        if not tokens or Path(tokens[0]).name not in (
                'emulator', 'qemu-system-aarch64', 'qemu-system-aarch64-headless'):
            continue
        if any(tokens[index] in ('-port', '-ports') and index + 1 < len(tokens)
               and tokens[index + 1].split(',')[0] == str(PORT)
               for index in range(len(tokens))):
            return True
    return False


def load_contract():
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise ValueError('boot probe contract changed')
    contract = json.loads(CONTRACT.read_text())
    if contract['argv'] != expected_argv() or contract['argv'] != contract['baseArgv'] + ['-feature', '-WiFiPacketStream']:
        raise ValueError('only the approved Wi-Fi feature delta is permitted')
    if contract['bootDeadlineSeconds'] != 180:
        raise ValueError('boot deadline differs from approved contract')
    for binding in contract['bindings']:
        path = Path(binding['path'])
        if not path.is_absolute():
            path = ROOT / path
        if sha(path) != binding['sha256']:
            raise ValueError('bound input drift: ' + str(path))
    for number, pid in ((1, 12041), (2, 13312)):
        crash = json.loads((HERE / f'analysis-1/runtime-{number}-crash-summary.json').read_text())
        if crash['pid'] != pid or crash['faultingThread'] != 4 or crash['netsimBlockedThread'] != 37:
            raise ValueError('original crash evidence binding mismatch')
    return contract


def load_helper():
    path = ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py'
    if sha(path) != '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216':
        raise ValueError('accepted owned process helper changed')
    spec = importlib.util.spec_from_file_location('mixer_boot_probe_owned_process', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe(out, contract, helper, *, popen=subprocess.Popen, clock=time.monotonic, sleep=time.sleep):
    """Dependencies are injectable so host tests can prove cleanup without targets."""
    receipt = {
        'schema': 1, 'startedUTC': utc(), 'status': 'started',
        'scope': 'boot-only WiFiPacketStream diagnostic; no app or product acceptance',
        'runnerSHA256': sha(__file__), 'contractSHA256': sha(CONTRACT),
        'argvDelta': ['-feature', '-WiFiPacketStream'],
        'baseArgv': contract['baseArgv'], 'commands': [],
        'boundInputTreeSHA256': contract['bindingTreeSHA256'],
        'officialSourcesSHA256': sha(HERE / 'official-sources.json'),
        'officialControlURL': 'https://developer.android.com/studio/run/emulator-networking-interconnect',
        'originalCrashes': [{'runtime': 1, 'pid': 12041, 'faultThread': 4, 'netsimBlockedThread': 37},
                            {'runtime': 2, 'pid': 13312, 'faultThread': 4, 'netsimBlockedThread': 37}],
        'physicalTargetsQueried': False, 'apkInstalled': False, 'appAssertionsRun': False,
        'sharedNetsimOrGlobalSettingsMutated': False,
        'knownLimitation': 'console port 5586 / ADB 5587 exceeds installed -help-port recommendation; unchanged for one-variable isolation',
        'cleanup': 'not-started',
    }
    process = None
    log = None
    cleanup_errors = []
    adb = [str(SDK / 'platform-tools/adb'), '-s', SERIAL]

    def run(name, argv, *, timeout=15, allow_failure=False):
        started = utc()
        result = helper.execute([str(a) for a in argv], cwd=ROOT, timeout=timeout)
        path = out / (name + '.log')
        path.write_bytes(result.stdout)
        receipt['commands'].append({
            'name': name, 'argv': [str(a) for a in argv], 'cwd': str(ROOT),
            'startedUTC': started, 'finishedUTC': utc(), 'exitCode': result.returncode,
            'output': path.name, 'outputSHA256': hashlib.sha256(result.stdout).hexdigest(),
            'ownedCommandGroupCleanup': result.groupCleanup,
        })
        if result.returncode and not allow_failure:
            raise RuntimeError('command failed: ' + name)
        return result.returncode, result.stdout

    def identity(stage):
        _, output = run('owned-process-' + stage,
                        ['ps', '-p', str(process.pid), '-o', 'pid=,pgid=,command='])
        if not owned_identity(output.decode().strip(), process.pid, process.pid):
            raise RuntimeError('refuse owned operation after exact PID/group/executable/argv identity drift')

    def ports_empty(stage):
        for port in (PORT, PORT + 1):
            code, output = run('port-' + stage + '-' + str(port),
                               ['lsof', '-nP', '-iTCP:' + str(port), '-sTCP:LISTEN'], allow_failure=True)
            if code != 1 or output:
                raise RuntimeError('reserved port occupied or check unavailable: ' + str(port))

    try:
        for name, argv in (
            ('source-revision', ['git', 'rev-parse', 'HEAD']),
            ('python-version', [sys.executable, '--version']),
            ('adb-version', [SDK / 'platform-tools/adb', 'version']),
            ('emulator-version', [EMULATOR, '-version']),
            ('emulator-help-port', [EMULATOR, '-help-port']),
        ):
            _, output = run(name, argv)
            if name == 'source-revision':
                receipt['sourceRevision'] = output.decode().strip()
        ports_empty('before')
        _, processes = run('processes-before', ['ps', '-axo', 'pid,ppid,command'])
        if reserved_process(processes.decode()):
            raise RuntimeError('existing process uses reserved console port; refuse takeover')
        log = (out / 'emulator.log').open('wb')
        process = popen(contract['argv'], cwd=ROOT, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt['ownedInstance'] = {'pid': process.pid, 'group': process.pid,
                                    'serial': SERIAL, 'argv': contract['argv']}
        save(out / 'owned-instance.json', receipt['ownedInstance'])
        receipt['cleanup'] = 'pending'
        deadline = clock() + contract['bootDeadlineSeconds']
        poll = 0
        while True:
            if process.poll() is not None:
                raise RuntimeError('owned emulator exited before boot')
            remaining = deadline - clock()
            if remaining <= 0:
                raise RuntimeError('bounded boot deadline exceeded')
            poll += 1
            code, output = run('boot-' + str(poll), adb + ['shell', 'getprop', 'sys.boot_completed'],
                               timeout=min(10, remaining), allow_failure=True)
            if code == 0 and output.strip() == b'1':
                break
            remaining = deadline - clock()
            if remaining <= 0:
                raise RuntimeError('bounded boot deadline exceeded')
            sleep(min(3, remaining))
        identity('before-use')
        target = {}
        for prop in PROPS:
            _, output = run('target-' + prop.replace('.', '-'), adb + ['shell', 'getprop', prop])
            target[prop] = output.decode().strip()
        receipt['target'] = target
        if target != PROPS:
            raise RuntimeError('unsupported exact API37 emulator target identity')
        receipt['status'] = 'boot-only-diagnostic-passed'
    except BaseException as failure:
        receipt['status'] = 'failed-boot-only-diagnostic'
        receipt['failure'] = repr(failure)
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    identity('before-stop')
                    run('stop-only-owned-emulator', adb + ['emu', 'kill'], allow_failure=True)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        identity('before-terminate')
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            identity('before-kill')
                            process.kill()
                            process.wait(timeout=10)
                receipt['ownedEmulatorGroupCleanup'] = helper.stop_group(process.pid)
                if receipt['ownedEmulatorGroupCleanup']['after']:
                    raise RuntimeError('owned emulator process group remains active')
                ports_empty('after')
                receipt['cleanup'] = 'stopped' if process.poll() is not None else 'failed'
            except BaseException as failure:
                cleanup_errors.append(repr(failure))
                receipt['cleanup'] = 'failed'
            finally:
                if log is not None:
                    log.close()
        if cleanup_errors:
            receipt['cleanupErrors'] = cleanup_errors
            receipt['status'] = 'failed-owned-cleanup'
        receipt['finishedUTC'] = utc()
        save(out / 'receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, help='fresh boot-probe-N directory')
    parser.add_argument('--execute-native', action='store_true', help='explicit root runtime dispatch only')
    args = parser.parse_args()
    if not args.execute_native:
        parser.error('runtime NOT RUN: explicit root dispatch and --execute-native required')
    if not re.fullmatch(r'boot-probe-[0-9]+', args.attempt):
        parser.error('fresh boot-probe-N evidence directory required')
    contract = load_contract()
    helper = load_helper()
    out = HERE / args.attempt
    out.mkdir()
    result = probe(out, contract, helper)
    print(json.dumps({'status': result['status'], 'cleanup': result['cleanup'], 'receipt': str(out / 'receipt.json')}))
    if result['status'] != 'boot-only-diagnostic-passed' or result['cleanup'] != 'stopped':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
