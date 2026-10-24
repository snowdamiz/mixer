#!/usr/bin/env python3
"""APK-only packaging derivation; never compiles code or discovers native targets."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'verification/android-coordinator-click-fixture/candidate-1'
BASE_WRAPPER = ROOT / 'verification/android-coordinator-click-fixture/run.py'
BASE_WRAPPER_SHA256 = '8e09a2d95734a0287384d65590c27ee65e14611513e8da1a7b153b30ea4f82d4'
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
BT = Path('/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def accepted():
    if sha(BASE_WRAPPER) != BASE_WRAPPER_SHA256:
        raise ValueError('frozen corrected instrumentation wrapper drift')
    adapter = load('apk_packaging_frozen_click_adapter', BASE_WRAPPER)
    runner, source, _ = adapter.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != 'feccd42c3153cafc56872b656483cdbec88a7af48ed95e281c8298aa57780084':
        raise ValueError('frozen corrected concrete runner drift')
    return runner, runner.bind_candidate(BASE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, choices=['candidate-1'])
    args = parser.parse_args()
    runner, original = accepted()  # Fail before creating scratch when references drift.
    guard = load('apk_packaging_build_guard', HERE / 'apk_packaging.py')
    out = HERE / args.attempt; out.mkdir()
    work = out / '.build'; work.mkdir()
    st = work.stat(); ownership = (st.st_dev, st.st_ino)
    commands = []
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'])
    receipt = {'schema': 1, 'status': 'repacking-private-test-APK', 'commands': commands,
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'nativeRuntime': 'NOT RUN', 'nativeAcceptance': False, 'gaAcceptance': False,
        'physicalTargetsQueried': False, 'nativeInstancesStarted': 0,
        'privateKeyRetained': False, 'hostLeavesPackaged': False,
        'compiledMinAPI': 36, 'sourceSDKTargetTripleAPI': 28, 'actuallyQualifiedRuntimeAPI': None,
        'builderSHA256': sha(Path(__file__)), 'packagingValidatorSHA256': sha(HERE / 'apk_packaging.py'),
        'limitations': ['APK-only packaging derivation; no Java/DEX/Swift/JNI code compilation',
            'fresh native install and all app assertions pending explicit root dispatch',
            'physical phones disconnected/deferred; full native/FieldLog/public/store/operational/GA gates pending']}

    def command(name, argv, allowed=(0,)):
        argv = list(map(str, argv)); start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        completed = runner.execute(argv, cwd=ROOT, env=env, timeout=180)
        log = out / (name + '.log'); log.write_bytes(completed.stdout)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'startedUTC': start,
            'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exitCode': completed.returncode,
            'output': log.name, 'sha256': sha(log), 'ownedCommandGroupCleanup': completed.groupCleanup})
        print(name + ': exit ' + str(completed.returncode), flush=True)
        if completed.returncode not in allowed:
            raise RuntimeError(name + ' failed; output retained')
        return completed.stdout.decode(errors='replace').strip()

    try:
        receipt['sourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = command('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        command('source-status', ['git', 'status', '--short'])
        locked = json.loads((BASE / 'source-lock.json').read_text())
        for relative, expected in locked['files'].items():
            source = BASE / 'inputs' / relative
            if sha(source) != expected:
                raise ValueError('frozen corrected source drift: ' + relative)
            target = out / 'inputs' / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        (out / 'source-lock.json').write_bytes((BASE / 'source-lock.json').read_bytes())
        receipt['sourceClosureSHA256'] = original['sourceClosureSHA256']
        receipt['sourceDerivation'] = {'baseCandidate': str(BASE.relative_to(ROOT)),
            'baseSourceRevision': original['sourceRevision'], 'baseSourceClosureSHA256': original['sourceClosureSHA256'],
            'baseAPK_SHA256': original['apkSHA256'], 'baseArchiveSHA256': original['builtArchiveSHA256'],
            'baseInputCount': len(locked['files']), 'changedInputs': [], 'unchangedInputs': len(locked['files']),
            'correctedInstrumentationSourceSHA256': locked['files']['verification/android-coordinator-join/CoordinatorJoinInstrumentation.java']}
        receipt['versions'] = {'python': command('python-version', [sys.executable, '--version']),
            'java': command('java-version', [JDK / 'bin/java', '--version']),
            'apksigner': command('apksigner-version', [BT / 'apksigner', 'version']),
            'zipalignHelp': command('zipalign-help', [BT / 'zipalign', '-h'], allowed=(2,))}
        tool_paths = [JDK / 'bin/java', JDK / 'bin/keytool', BT / 'zipalign', BT / 'apksigner',
                      BT / 'lib/apksigner.jar', BT / 'source.properties']
        receipt['tools'] = {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size, 'realPath': str(p.resolve())} for p in tool_paths}
        artifacts = json.loads((BASE / 'built-artifacts.json').read_text())
        with tarfile.open(BASE / 'built-artifacts.tar.gz', 'r:gz') as archive:
            members = archive.getmembers(); runner.validate_members(members, artifacts)
            archive.extractall(work, members=members, filter='data')
        for relative, value in artifacts.items():
            if sha(work / relative) != value['sha256']:
                raise ValueError('frozen corrected artifact drift: ' + relative)
        old_entries = json.loads((BASE / 'apk-entries.json').read_text())
        with zipfile.ZipFile(work / 'coordinator-join.apk') as archive:
            infos = archive.infolist()
            if set(archive.namelist()) != set(old_entries):
                raise ValueError('frozen corrected APK membership drift')
            payloads = {i.filename: archive.read(i.filename) for i in infos}
        for name, payload in payloads.items():
            if hashlib.sha256(payload).hexdigest() != old_entries[name]['sha256']:
                raise ValueError('frozen corrected APK entry drift: ' + name)
        try:
            guard.validate(work / 'coordinator-join.apk')
        except ValueError as expected:
            if 'resources.arsc must be ZIP_STORED' not in str(expected):
                raise
            save(out / 'base-packaging-rejection.json', {'status': 'expected-original-packaging-rejection',
                'failure': str(expected), 'baseAPK_SHA256': original['apkSHA256']})
        else:
            raise ValueError('base compressed-resources regression was not caught')
        unsigned = work / 'unsigned.apk'
        with zipfile.ZipFile(unsigned, 'w') as archive:
            for info in infos:
                if info.filename.startswith('META-INF/'):
                    continue
                # Preserve each original storage method except the one corrected resource table.
                info.compress_type = zipfile.ZIP_STORED if info.filename == 'resources.arsc' else info.compress_type
                archive.writestr(info, payloads[info.filename])
        aligned = work / 'aligned.apk'
        command('private-apk-align-16k', [BT / 'zipalign', '-f', '-P', '16', '4', unsigned, aligned])
        save(out / 'pre-sign-packaging.json', guard.validate(aligned))
        command('pre-sign-official-zipalign', [BT / 'zipalign', '-c', '-P', '16', '-v', '4', aligned])
        key = work / 'disposable-debug.keystore'
        try:
            env['MIXER_PACKAGING_DEBUG_PASS'] = secrets.token_urlsafe(32)
            command('disposable-debug-key', [JDK / 'bin/keytool', '-genkeypair', '-keystore', key,
                '-storepass:env', 'MIXER_PACKAGING_DEBUG_PASS', '-keypass:env', 'MIXER_PACKAGING_DEBUG_PASS',
                '-alias', 'debug', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '30',
                '-dname', 'CN=Mixer Disposable APK Packaging Test'])
            command('private-debug-apk-sign', [BT / 'apksigner', 'sign', '--ks', key,
                '--ks-pass', 'env:MIXER_PACKAGING_DEBUG_PASS', '--key-pass', 'env:MIXER_PACKAGING_DEBUG_PASS',
                '--out', work / 'coordinator-join.apk', aligned])
        finally:
            key.unlink(missing_ok=True); env.pop('MIXER_PACKAGING_DEBUG_PASS', None)
        apk = work / 'coordinator-join.apk'
        save(out / 'post-sign-packaging.json', guard.validate(apk))
        command('post-sign-official-zipalign', [BT / 'zipalign', '-c', '-P', '16', '-v', '4', apk])
        signing = command('private-debug-signature-cert', [BT / 'apksigner', 'verify', '--verbose', '--print-certs', apk])
        certs = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', signing)
        if len(certs) != 1:
            raise ValueError('exactly one test signer certificate required')
        with zipfile.ZipFile(apk) as archive:
            entries = {i.filename: {'bytes': i.file_size, 'sha256': hashlib.sha256(archive.read(i.filename)).hexdigest()}
                       for i in archive.infolist()}
        if set(entries) != set(old_entries):
            raise ValueError('APK entry membership changed')
        entry_changes = {name: {'before': old_entries[name], 'after': entries[name]}
                         for name in entries if old_entries[name] != entries[name]}
        if any(not name.startswith('META-INF/') for name in entry_changes):
            raise ValueError('uncompressed product APK entry bytes changed')
        updated = {}
        for relative in artifacts:
            p = work / relative
            updated[relative] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
        changes = [name for name in artifacts if artifacts[name] != updated[name]]
        if changes != ['coordinator-join.apk']:
            raise ValueError('APK-only artifact delta required: ' + repr(changes))
        save(out / 'artifact-delta.json', {'changed': {name: {'before': artifacts[name], 'after': updated[name]} for name in changes},
            'unchanged': {name: value for name, value in updated.items() if name not in changes}})
        save(out / 'apk-entry-delta.json', {'changedDebugSignatureEntries': entry_changes,
            'unchangedEntries': {name: value for name, value in entries.items() if name not in entry_changes},
            'storageMethodCorrection': {'resources.arsc': {'before': 8, 'after': 0}}})
        save(out / 'apk-entries.json', entries); save(out / 'built-artifacts.json', updated)
        with tarfile.open(out / 'built-artifacts.tar.gz', 'w:gz') as archive:
            for relative in sorted(updated):
                archive.add(work / relative, arcname=relative, recursive=False)
        receipt.update({'apkSHA256': sha(apk), 'builtArchiveSHA256': sha(out / 'built-artifacts.tar.gz'),
            'debugCertificateSHA256': certs[0], 'descriptorSHA256': original['descriptorSHA256'],
            'coordinatorClassSHA256': original['coordinatorClassSHA256'],
            'compiledProductionSources': original['compiledProductionSources'],
            'productionArtifactsRecompiled': 0, 'productionArtifactsUnchanged': True,
            'correctedInstrumentationUnchanged': True, 'artifactCount': len(updated),
            'changedArtifacts': changes, 'changedAPKEntries': sorted(entry_changes),
            'sourceUnchanged': all(sha(out / 'inputs' / name) == value for name, value in locked['files'].items())})
        if not receipt['sourceUnchanged']:
            raise ValueError('frozen inputs changed during APK-only packaging')
        accepted()
        receipt['status'] = 'actual-private-apk-built-runtime-NOT-RUN'
    except BaseException as failure:
        receipt.update({'status': 'failed-APK-only-packaging-retained', 'failure': repr(failure)})
        raise
    finally:
        (work / 'disposable-debug.keystore').unlink(missing_ok=True)
        expected = {str(p.relative_to(work)): {} for p in work.rglob('*') if p.is_file()}
        try:
            receipt['buildScratchCleanup'] = runner.remove_owned_extraction(work, out, expected, ownership)
        except BaseException as failure:
            receipt.update({'status': 'failed-build-scratch-cleanup', 'buildScratchCleanup': repr(failure)})
            raise
        finally:
            receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save(out / 'receipt.json', receipt)
            save(out / 'artifact-seal.json', {str(p.relative_to(out)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'artifact-seal.json' and '.build' not in p.relative_to(out).parts})


if __name__ == '__main__':
    main()
