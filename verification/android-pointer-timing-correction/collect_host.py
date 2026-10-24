#!/usr/bin/env python3
"""Retain bounded host attempts; never calls Git, Android, or device discovery."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
import traceback
import support

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt', required=True); args = parser.parse_args()
    if not re.fullmatch(r'host-[1-9][0-9]*', args.attempt): parser.error('fresh host-N required')
    out = support.HERE / args.attempt
    if out.exists() or out.is_symlink(): raise ValueError('fresh host attempt required')
    out.mkdir()
    receipt = {'schema': 1, 'startedUTC': now(), 'scope': 'host-only oracle/wrapper/package replay', 'commands': [],
               'nativeCommandsExecuted': 0, 'physicalTargetsQueried': False, 'GitCommandsExecuted': 0,
               'rebuilds': 0, 'sourceRevisionContext': json.loads(support.SELECTION.read_text())['sourceRevision'],
               'sourceRevisionAuthority': 'immutable root selection context; this collector does not invoke Git',
               'sourceFiles': {p.name: support.bind(p) for p in sorted(support.HERE.glob('*.py'))}}
    used = out / 'source-used'; used.mkdir()
    for path in support.HERE.glob('*.py'): shutil.copyfile(path, used / path.name)
    scratch = Path(tempfile.mkdtemp(prefix='mixer-pointer-timing-correction-', dir='/private/tmp'))
    identity = scratch.stat(); receipt['scratch'] = {'path': str(scratch), 'device': identity.st_dev, 'inode': identity.st_ino}
    helper = support.load('timing_command_groups', support.ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py')
    java_home = '/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'
    env = dict(os.environ, JAVA_HOME=java_home, PATH=java_home + '/bin:' + os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1')
    def command(name, argv, allowed=(0,), timeout=180):
        started = now(); argv = [str(a) for a in argv]
        result = helper.execute(argv, cwd=support.ROOT, env=env, timeout=timeout)
        log = out / (name + '.log'); log.write_bytes(result.stdout)
        receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(support.ROOT), 'startedUTC': started,
                                    'finishedUTC': now(), 'exitCode': result.returncode, 'output': str(log.relative_to(support.ROOT)),
                                    'environmentOverrides': {'JAVA_HOME': java_home, 'PATHPrefix': java_home + '/bin', 'PYTHONDONTWRITEBYTECODE': '1'},
                                    'ownedCommandGroupCleanup': result.groupCleanup, **support.bind(log)})
        support.save(out / 'receipt.json', receipt)
        print(name + ': exit ' + str(result.returncode), flush=True)
        if result.returncode not in allowed: raise RuntimeError(name + ' failed')
        return result.stdout
    try:
        receipt['upstreamBefore'] = support.upstream()
        support.save(out / 'upstream-before.json', receipt['upstreamBefore'])
        tools = json.loads((support.HERE / 'runner-contract.json').read_text())['toolBindings']
        receipt['tools'] = {name: support.bind(name) for name in tools}
        if any(v['sha256'] != tools[k] for k, v in receipt['tools'].items()): raise ValueError('tool binding drift')
        command('python-version', [sys.executable, '--version'])
        command('java-version', [java_home + '/bin/java', '--version'])
        command('producer-packet-before', [sys.executable, '-B', support.PRIOR / 'check_packet.py'])
        command('review-packet-before', [sys.executable, '-B', support.REVIEW / 'check_review.py'])
        command('host-controls', [sys.executable, '-B', support.HERE / 'test_host.py', '--work', scratch / 'tests', '--results', out / 'test-results.json'])
        results = json.loads((out / 'test-results.json').read_text())
        if results['status'] != 'passed' or results['priorTests'] != 42 or len(results['exactFiveControls']) != 5: raise ValueError('host controls incomplete')
        packet = json.loads((support.PRIOR / 'packet.json').read_text())
        apk = Path(packet['retainedSignedAPK']['path'])
        archive_path = support.PRIOR / 'candidate-5/built-artifacts.tar.gz'
        if support.sha(apk) != support.APK or support.sha(archive_path) != support.ARCHIVE: raise ValueError('unchanged APK/archive drift')
        guard = support.load('timing_packaging_guard', support.ROOT / 'verification/android-coordinator-apk-packaging/apk_packaging.py')
        common, _, _ = support.prior_modules(); candidate = common.candidate(support.PRIOR / 'candidate-5', guard)
        if candidate['sourceClosureSHA256'] != support.CLOSURE: raise ValueError('source closure drift')
        artifacts = json.loads((support.PRIOR / 'candidate-5/built-artifacts.json').read_text())
        with tarfile.open(archive_path, 'r:gz') as archive:
            members = archive.getmembers()
            if len(members) != 179 or len({m.name for m in members}) != 179 or set(m.name for m in members) != set(artifacts): raise ValueError('179 archive members required')
            for member in members:
                if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts: raise ValueError('unsafe archive member')
                data = archive.extractfile(member).read()
                if artifacts[member.name] != {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}: raise ValueError('archive member drift')
        support.save(out / 'artifact-replay.json', {'apk': support.bind(apk), 'archive': support.bind(archive_path),
                     'sourceClosureSHA256': candidate['sourceClosureSHA256'], 'sourceInputs': 105, 'liveNativeSDKInputs': 88,
                     'archiveMembersVerified': 179, 'packaging': guard.validate(apk), 'rebuilds': 0, 'archiveCopied': False,
                     'nativeRuntime': 'NOT RUN'})
        sdk = Path('/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0')
        command('zipalign-version', [sdk / 'zipalign', '-h'], allowed=(0, 2))
        command('apksigner-version', [sdk / 'apksigner', 'version'])
        command('official-zipalign', [sdk / 'zipalign', '-c', '-P', '16', '-v', '4', apk])
        signature = command('official-apksigner', [sdk / 'apksigner', 'verify', '--verbose', '--print-certs', apk])
        if re.findall(rb'certificate SHA-256 digest: ([0-9a-f]{64})', signature) != [candidate['debugCertificateSHA256'].encode()]: raise ValueError('official certificate mismatch')
        wrapper = support.load('timing_loaded_adaptation', support.HERE / 'run.py'); runner, source, _ = wrapper.load_runner()
        support.save(out / 'loaded-adaptation.json', {'timingCorrection': runner._ADAPTATION['timingCorrection'],
                     'concreteSourceSHA256': hashlib.sha256(source.encode()).hexdigest(),
                     'oracleFilename': runner._pointer_validate_native.__code__.co_filename,
                     'runtimeDirectoryFunctionFilename': runner._pointer_runtime_directory.__code__.co_filename,
                     'nativeEntryPointCalled': False})
        receipt['upstreamAfter'] = support.upstream()
        if receipt['upstreamAfter'] != receipt['upstreamBefore']: raise ValueError('prior packets changed during correction')
        support.save(out / 'upstream-after.json', receipt['upstreamAfter'])
        command('producer-packet-after', [sys.executable, '-B', support.PRIOR / 'check_packet.py'])
        command('review-packet-after', [sys.executable, '-B', support.REVIEW / 'check_review.py'])
        receipt['status'] = 'passed-host-only-correction-controls-and-unchanged-artifact-replay'
    except BaseException as failure:
        receipt['status'] = 'failed-host-attempt-retained'; receipt['failure'] = repr(failure)
        (out / 'failure.log').write_text(traceback.format_exc())
        raise
    finally:
        try:
            holders = command('scratch-open-holders', ['/usr/sbin/lsof', '-nP', '+D', scratch], allowed=(1,))
            current = scratch.stat()
            if holders or scratch.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino): raise ValueError('scratch identity/open-holder cleanup refusal')
            if any(p.is_symlink() for p in scratch.rglob('*')): raise ValueError('scratch symlink cleanup refusal')
            shutil.rmtree(scratch)
            receipt['scratch']['cleanup'] = 'removed after unchanged device/inode, no symlinks, empty open holders'
            receipt['scratch']['existsAfter'] = scratch.exists()
        except BaseException as failure:
            receipt['status'] = 'failed-scratch-cleanup'; receipt['cleanupFailure'] = repr(failure)
        receipt['finishedUTC'] = now(); support.save(out / 'receipt.json', receipt)
        support.save(out / 'artifact-seal.json', {str(p.relative_to(out)): support.bind(p) for p in sorted(out.rglob('*')) if p.is_file() and p != out / 'artifact-seal.json'})

if __name__ == '__main__': main()
