#!/usr/bin/env python3
"""Derive one test-only APK from candidate2. No device discovery or native launch."""
import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'verification/android-coordinator-join/candidate-2'
WIFI = ROOT / 'verification/android-coordinator-wifi-runner/run.py'
WIFI_SHA256 = 'f1c5d48aee17eaee472ced89c9e09f878f7088eab610429e3f702981467bcaff'
JAVA_SOURCE = 'verification/android-coordinator-join/CoordinatorJoinInstrumentation.java'
CLASS_PREFIX = 'test-classes/dev/mixer/android/CoordinatorJoinInstrumentation'
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
BT = SDK / 'build-tools/37.0.0'
JAR = SDK / 'platforms/android-37.0/android.jar'
OLD = '            check(toggle.performClick(), "actual Switch.performClick");'
NEW = '''            boolean hadOnClickListeners = toggle.hasOnClickListeners();
            boolean performClickReturned = toggle.performClick();
            observations.add(Json.map("nativeSwitchPerformClick", "invoked",
                "hasOnClickListenersBefore", hadOnClickListeners,
                "performClickReturned", performClickReturned));
            check(performClickReturned == hadOnClickListeners,
                "actual Switch.performClick return agrees with pre-click OnClickListener presence");'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accepted():
    if sha(WIFI) != WIFI_SHA256:
        raise ValueError('accepted Wi-Fi wrapper drift')
    adapter = load_module('click_build_accepted_wifi', WIFI)
    runner, source, _ = adapter.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != '6ac0d6a88d4df6058349cc29205ea1b517009d38be011858ee1fc358e577c406':
        raise ValueError('accepted concrete Wi-Fi runner drift')
    metadata = runner.bind_candidate(BASE)
    return adapter, runner, metadata


def corrected(source):
    if source.count(OLD) != 1:
        raise ValueError('exactly one frozen performClick assertion required')
    return source.replace(OLD, NEW, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, choices=['candidate-1'])
    args = parser.parse_args()
    out = HERE / args.attempt
    out.mkdir()
    work = out / '.build'
    work.mkdir()
    identity = work.stat()
    ownership = (identity.st_dev, identity.st_ino)
    commands = []
    env = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK / 'bin') + os.pathsep + os.environ['PATH'])
    receipt = {'schema': 1, 'status': 'building-test-only-derivative', 'commands': commands,
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'nativeRuntime': 'NOT RUN', 'nativeAcceptance': False, 'gaAcceptance': False,
        'physicalTargetsQueried': False, 'nativeInstancesStarted': 0,
        'privateKeyRetained': False, 'hostLeavesPackaged': False,
        'compiledMinAPI': 36, 'sourceSDKTargetTripleAPI': 28, 'actuallyQualifiedRuntimeAPI': None,
        'sourceUnchangedMeaning': 'derived frozen input bytes unchanged during this build; only original instrumentation input was corrected',
        'limitations': ['test-only derivation; no emulator/device discovery or launch',
            'fresh native app assertions pending explicit root dispatch',
            'physical phones disconnected and deferred; full fault/IME/lifecycle, public/signed release, FieldLog, store, operational and GA gates pending']}
    runner = None

    def command(name, argv, timeout=180):
        argv = list(map(str, argv))
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = runner.execute(argv, cwd=ROOT, env=env, timeout=timeout)
        log = out / (name + '.log'); log.write_bytes(result.stdout)
        commands.append({'name': name, 'argv': argv, 'cwd': str(ROOT), 'startedUTC': start,
            'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'exitCode': result.returncode, 'output': log.name, 'sha256': sha(log),
            'ownedCommandGroupCleanup': result.groupCleanup})
        print(name + ': exit ' + str(result.returncode), flush=True)
        if result.returncode:
            raise RuntimeError(name + ' failed; see retained output')
        return result.stdout.decode(errors='replace').strip()

    try:
        adapter, runner, original = accepted()
        receipt['sourceRevision'] = command('source-revision', ['git', 'rev-parse', 'HEAD'])
        receipt['sourceTree'] = command('source-tree', ['git', 'rev-parse', 'HEAD^{tree}'])
        command('source-status', ['git', 'status', '--short'])
        base_files = json.loads((BASE / 'source-lock.json').read_text())['files']
        source_files = {}
        for relative, expected in base_files.items():
            source = BASE / 'inputs' / relative
            if sha(source) != expected:
                raise ValueError('base input drift: ' + relative)
            target = out / 'inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            if relative == JAVA_SOURCE:
                target.write_text(corrected(source.read_text()))
            source_files[relative] = sha(target)
        changed_inputs = [name for name in base_files if source_files[name] != base_files[name]]
        if changed_inputs != [JAVA_SOURCE]:
            raise ValueError('only instrumentation input may differ')
        source = (BASE / 'inputs' / JAVA_SOURCE).read_text()
        derived = (out / 'inputs' / JAVA_SOURCE).read_text()
        (out / 'instrumentation.diff').write_text(''.join(difflib.unified_diff(
            source.splitlines(keepends=True), derived.splitlines(keepends=True),
            fromfile='original-candidate-2/' + JAVA_SOURCE, tofile='derived-candidate-1/' + JAVA_SOURCE)))
        closure = hashlib.sha256(json.dumps(source_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        receipt['sourceClosureSHA256'] = closure
        save(out / 'source-lock.json', {'sourceRevision': receipt['sourceRevision'],
            'sourceClosureSHA256': closure, 'files': source_files})
        receipt['sourceDerivation'] = {'baseCandidate': str(BASE.relative_to(ROOT)),
            'baseSourceRevision': original['sourceRevision'], 'baseSourceClosureSHA256': original['sourceClosureSHA256'],
            'baseAPK_SHA256': original['apkSHA256'], 'baseArchiveSHA256': original['builtArchiveSHA256'],
            'baseBindings': runner.BUILD_BINDINGS, 'baseInputCount': len(base_files),
            'changedInputs': changed_inputs, 'unchangedInputs': len(base_files) - len(changed_inputs),
            'beforeInstrumentationSHA256': base_files[JAVA_SOURCE], 'afterInstrumentationSHA256': source_files[JAVA_SOURCE],
            'instrumentationDiffSHA256': sha(out / 'instrumentation.diff')}
        receipt['versions'] = {name: command(name + '-version', argv) for name, argv in [
            ('python', [sys.executable, '--version']), ('java', [JDK / 'bin/java', '--version']),
            ('javac', [JDK / 'bin/javac', '--version']), ('d8', [BT / 'd8', '--version']),
            ('apksigner', [BT / 'apksigner', 'version'])]}
        tools = [JDK / 'bin/java', JDK / 'bin/javac', JDK / 'bin/keytool', BT / 'zipalign',
                 BT / 'lib/apksigner.jar', BT / 'lib/d8.jar', JAR, BT / 'source.properties']
        receipt['tools'] = {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size,
            'realPath': str(p.resolve())} for p in tools}
        old_artifacts = json.loads((BASE / 'built-artifacts.json').read_text())
        with tarfile.open(BASE / 'built-artifacts.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            runner.validate_members(members, old_artifacts)
            archive.extractall(work, members=members, filter='data')
        for relative, binding in old_artifacts.items():
            if sha(work / relative) != binding['sha256']:
                raise ValueError('base artifact drift: ' + relative)
        old_entries = json.loads((BASE / 'apk-entries.json').read_text())
        with zipfile.ZipFile(work / 'coordinator-join.apk') as archive:
            if set(archive.namelist()) != set(old_entries):
                raise ValueError('base APK membership drift')
            packaged = {name: archive.read(name) for name in archive.namelist()}
        for name, data in packaged.items():
            if hashlib.sha256(data).hexdigest() != old_entries[name]['sha256']:
                raise ValueError('base APK entry drift: ' + name)
        # Remove the complete old instrumentation class family before compiling only its source.
        old_family = [name for name in old_artifacts if name.startswith(CLASS_PREFIX)
                      and (name[len(CLASS_PREFIX):] == '.class' or name[len(CLASS_PREFIX):].startswith('$'))]
        for name in old_family:
            (work / name).unlink()
        empty = work / 'empty-sourcepath'; empty.mkdir()
        production, tests, dex = (work / name for name in ('production-classes', 'test-classes', 'dex'))
        command('corrected-instrumentation-java17-sdk37', [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror',
            '-sourcepath', empty, '-classpath', os.pathsep.join(map(str, [production, tests, JAR])),
            '-d', tests, out / 'inputs' / JAVA_SOURCE])
        for path in dex.glob('*.dex'):
            path.unlink()
        command('joined-dex-min36', [BT / 'd8', '--min-api', '36', '--lib', JAR, '--output', dex,
            *sorted(production.rglob('*.class')), *sorted(tests.rglob('*.class'))])
        unsigned = work / 'unsigned.apk'
        with zipfile.ZipFile(unsigned, 'w') as archive:
            for name, data in packaged.items():
                if name.startswith('META-INF/') or name.endswith('.dex'):
                    continue
                archive.writestr(name, data, compress_type=zipfile.ZIP_STORED
                    if name.endswith('.so') else zipfile.ZIP_DEFLATED)
            for path in sorted(dex.glob('*.dex')):
                archive.write(path, path.name, compress_type=zipfile.ZIP_DEFLATED)
        aligned = work / 'aligned.apk'
        command('private-apk-align-16k', [BT / 'zipalign', '-f', '-P', '16', '4', unsigned, aligned])
        key = work / 'disposable-debug.keystore'
        try:
            env['MIXER_CLICK_DEBUG_PASS'] = secrets.token_urlsafe(32)
            command('disposable-debug-key', [JDK / 'bin/keytool', '-genkeypair', '-keystore', key,
                '-storepass:env', 'MIXER_CLICK_DEBUG_PASS', '-keypass:env', 'MIXER_CLICK_DEBUG_PASS',
                '-alias', 'debug', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '30',
                '-dname', 'CN=Mixer Disposable Corrected Click Fixture'])
            command('private-debug-apk-sign', [BT / 'apksigner', 'sign', '--ks', key,
                '--ks-pass', 'env:MIXER_CLICK_DEBUG_PASS', '--key-pass', 'env:MIXER_CLICK_DEBUG_PASS',
                '--out', work / 'coordinator-join.apk', aligned])
        finally:
            key.unlink(missing_ok=True)
            env.pop('MIXER_CLICK_DEBUG_PASS', None)
        apk = work / 'coordinator-join.apk'
        signing = command('private-debug-signature-cert', [BT / 'apksigner', 'verify', '--verbose', '--print-certs', apk])
        certs = re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', signing)
        if len(certs) != 1:
            raise ValueError('exactly one test signer certificate required')
        command('private-apk-alignment-check', [BT / 'zipalign', '-c', '-P', '16', '-v', '4', apk])
        artifacts = {str(p.relative_to(work)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for folder in [production, tests, dex, work / 'apk/lib/arm64-v8a']
            for p in sorted(folder.rglob('*')) if p.is_file()}
        artifacts['coordinator-join.apk'] = {'bytes': apk.stat().st_size, 'sha256': sha(apk)}
        changes = {name: {'before': old_artifacts.get(name), 'after': artifacts.get(name)}
            for name in sorted(set(old_artifacts) | set(artifacts)) if old_artifacts.get(name) != artifacts.get(name)}
        allowed = lambda name: name == 'coordinator-join.apk' or name.startswith('dex/') or name.startswith(CLASS_PREFIX)
        if any(not allowed(name) for name in changes):
            raise ValueError('production artifact changed')
        if any(name.endswith('.keystore') for name in artifacts):
            raise ValueError('private key retained')
        with zipfile.ZipFile(apk) as archive:
            entries = {info.filename: {'bytes': info.file_size,
                'sha256': hashlib.sha256(archive.read(info.filename)).hexdigest()} for info in archive.infolist()}
        entry_changes = {name: {'before': old_entries.get(name), 'after': entries.get(name)}
            for name in sorted(set(old_entries) | set(entries)) if old_entries.get(name) != entries.get(name)}
        if any(not (name.startswith('META-INF/') or name.endswith('.dex')) for name in entry_changes):
            raise ValueError('product APK entry changed')
        if set(old_entries) != set(entries):
            raise ValueError('APK entry membership changed')
        save(out / 'artifact-delta.json', {'changed': changes,
            'unchanged': {name: value for name, value in artifacts.items() if old_artifacts.get(name) == value},
            'removedInstrumentationFamily': old_family,
            'compiledInstrumentationFamily': [name for name in artifacts if name.startswith(CLASS_PREFIX)]})
        save(out / 'apk-entry-delta.json', {'changedDexOrDebugSignature': entry_changes,
            'unchangedProductEntries': {name: value for name, value in entries.items() if old_entries.get(name) == value}})
        save(out / 'apk-entries.json', entries)
        save(out / 'built-artifacts.json', artifacts)
        with tarfile.open(out / 'built-artifacts.tar.gz', 'w:gz') as archive:
            for name in sorted(artifacts):
                archive.add(work / name, arcname=name, recursive=False)
        receipt.update({'apkSHA256': sha(apk), 'builtArchiveSHA256': sha(out / 'built-artifacts.tar.gz'),
            'debugCertificateSHA256': certs[0], 'descriptorSHA256': original['descriptorSHA256'],
            'coordinatorClassSHA256': original['coordinatorClassSHA256'],
            'compiledProductionSources': original['compiledProductionSources'],
            'productionArtifactsRecompiled': 0, 'productionArtifactsUnchanged': True,
            'artifactCount': len(artifacts), 'changedArtifacts': sorted(changes),
            'changedAPKEntries': sorted(entry_changes),
            'sourceUnchanged': all(sha(out / 'inputs' / name) == value for name, value in source_files.items())})
        if not receipt['sourceUnchanged']:
            raise ValueError('derived frozen inputs changed during build')
        accepted()
        receipt['status'] = 'actual-private-apk-built-runtime-NOT-RUN'
    except BaseException as failure:
        receipt.update({'status': 'failed-test-only-derivation-retained', 'failure': repr(failure)})
        raise
    finally:
        (work / 'disposable-debug.keystore').unlink(missing_ok=True)
        empty = work / 'empty-sourcepath'
        if empty.is_dir() and not empty.is_symlink() and not list(empty.iterdir()):
            empty.rmdir()
        if runner is None:
            # Loading the immutable helper requires no SDK/device operation.
            helper = load_module('click_failed_build_helper', ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py')
            runner = load_module('click_failed_build_cleanup', ROOT / 'verification/android-coordinator-runner-cleanup/run.py')
            runner.execute = helper.execute
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
