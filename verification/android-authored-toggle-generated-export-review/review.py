#!/usr/bin/env python3
"""Independent frozen-source export/Java/D8 replay; no native runtime or network fetch."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/android-authored-toggle-generated-export'
EXPECTED_SEAL = '18b101a646638f16840cbec7af294da4feafda20197373c2646905554a966486'
EXPECTED_BASELINE = 'bcc49902f47011cd39d15bcb93c9f654ec446fa24482c582ffc2e67f221ea650'
ATTEMPT = HERE / sys.argv[1]
ATTEMPT.mkdir(exist_ok=False)
WORK = ATTEMPT / 'scratch'
WORK.mkdir()
TOKEN = uuid.uuid4().hex
OWNER = WORK / '.owner.json'
OWNER.write_text(json.dumps({'owner': str(HERE), 'token': TOKEN}) + '\n')
IDENTITY = (WORK.stat().st_dev, WORK.stat().st_ino)
COMMANDS = []
GROUPS = []
CHECKS = []


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw)}


def save(name, data):
    (ATTEMPT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def require(ok, label):
    CHECKS.append({'label': label, 'passed': bool(ok)})
    if not ok:
        raise AssertionError(label)


def manifest(folder):
    return {str(p.relative_to(folder)): row(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def run(label, argv, cwd, success=True, timeout=900):
    argv = list(map(str, argv))
    begin = time.monotonic()
    stdout = ATTEMPT / (label + '.stdout')
    stderr = ATTEMPT / (label + '.stderr')
    with stdout.open('wb') as out, stderr.open('wb') as err:
        child = subprocess.Popen(argv, cwd=cwd, env=ENV, stdout=out, stderr=err,
                                 start_new_session=True)
        GROUPS.append(child.pid)
        try:
            code = child.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait()
    command = {'label': label, 'argv': argv, 'cwd': str(cwd), 'exitCode': code,
               'timedOut': timed_out, 'childReturned': True,
               'seconds': time.monotonic() - begin,
               'stdout': {'name': stdout.name, **row(stdout)},
               'stderr': {'name': stderr.name, **row(stderr)}}
    COMMANDS.append(command)
    save(label + '.json', command)
    print(label, code, flush=True)
    require(not timed_out and ((code == 0) if success else code != 0), label + ' expected exit')
    return stdout.read_text(errors='replace') + stderr.read_text(errors='replace')


receipt = {'schema': 1, 'status': 'running',
           'startedUTC': datetime.now(timezone.utc).isoformat(),
           'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT)), sys.argv[1]],
           'pythonVersion': sys.version, 'reviewerSHA256': row(Path(__file__))['sha256'],
           'producerSealSHA256': EXPECTED_SEAL, 'baselineSHA256': EXPECTED_BASELINE,
           'nativeRuntime': False, 'deviceDiscovery': False, 'capture': False,
           'uiAutomation': False, 'publicRouting': False,
           'signedOrHealthAuthority': False, 'gaAcceptance': False,
           'scope': 'Independent sealed-source host CLI/test/export and isolated Java/D8 replay only.'}
try:
    seal_raw = (PRODUCER / 'seal.json').read_bytes()
    require(digest(seal_raw) == EXPECTED_SEAL, 'root seal identity')
    seal = json.loads(seal_raw)
    for name, expected in seal['files'].items():
        require(row(ROOT / name) == expected, 'sealed file ' + name)
    receipt['sealedMembers'] = len(seal['files'])
    baseline_raw = (HERE / 'baseline.json').read_bytes()
    require(digest(baseline_raw) == EXPECTED_BASELINE, 'independent prior baseline identity')
    baseline = json.loads(baseline_raw)
    for name, expected in baseline['inputBindings'].items():
        require(row(ROOT / name)['sha256'] == expected, 'baseline original input ' + name)
    expected_java = baseline['expectedJavaSources']
    producer_run = PRODUCER / 'commands/run-1'
    producer = json.loads((producer_run / 'receipt.json').read_text())
    for path, expected in producer['tools'].items():
        require(row(Path(path).resolve()) == expected, 'recorded tool identity ' + path)
    receipt['tools'] = producer['tools']
    commands = {r['name']: r for r in producer['commands']}
    SWIFT = Path(commands['swift-version']['argv'][0])
    JAVAC = Path(commands['javac-version']['argv'][0])
    JDK = JAVAC.parent.parent
    D8 = Path(commands['d8-version']['argv'][0])
    DEXDUMP = D8.parent / 'dexdump'
    JAR = Path(next(p for p in producer['tools'] if p.endswith('/android.jar')))
    ENV = os.environ.copy()
    ENV.update({'JAVA_HOME': str(JDK), 'MIXER_JDK': str(JDK),
                'ANDROID_HOME': str(JAR.parents[2]),
                'PATH': str(JDK / 'bin') + os.pathsep + ENV.get('PATH', '')})
    receipt['environmentOverrides'] = {k: ENV[k] for k in ['JAVA_HOME', 'MIXER_JDK', 'ANDROID_HOME']}
    source = WORK / 'source'
    inputs = json.loads((producer_run / 'inputs-before.json').read_text())
    require(inputs == json.loads((producer_run / 'inputs-after.json').read_text()), 'producer before/after identity')
    for name, expected in inputs.items():
        original = producer_run / 'source-inputs' / name
        require(row(original) == expected, 'frozen source ' + name)
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    receipt['sourceInputCount'] = len(inputs)
    receipt['sourceTreeSHA256'] = digest(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())
    save('replayed-source-inputs.json', inputs)
    for path, expected in expected_java.items():
        require(row(source / path)['sha256'] == expected, 'independent accepted Java baseline ' + path)
    # Route both remote identifiers to existing local bare repositories. No
    # dependency source/manifest is rewritten and no network fetch is needed.
    for identity, suffix, revision in [
        ('swift-crypto', '7e0614ea', 'c2cbadd7263439d8015189668f96ff5b5be565ce'),
        ('swift-asn1', '7065ad2c', '3b6410f7dee09eb33cdd26260c5fd47fda19b0e2')]:
        mirror = ROOT / 'cli/.build/repositories' / (identity + '-' + suffix)
        actual = run('local-' + identity + '-identity', ['git', '--git-dir', mirror, 'rev-parse', revision + '^{commit}'], source, timeout=30)
        require(actual.strip() == revision, identity + ' existing pinned commit')
        run('local-' + identity + '-mirror', [SWIFT, 'package', '--package-path', source / 'cli',
            'config', 'set-mirror', '--original', 'https://github.com/apple/' + identity + '.git',
            '--mirror', mirror.as_uri()], source, timeout=30)
    for label, argv in [('swift-version', [SWIFT, '--version']), ('javac-version', [JAVAC, '--version']),
                        ('d8-version', [D8, '--version'])]:
        run(label, argv, source, timeout=30)
    filter_value = 'androidSnapshotOwnsOnlyRuntimeRendererCoordinatorAndBridgeAndLocksExactBytes|androidCoordinatorAndAuthoredToggleSnapshotChangesInvalidateAdapterLock'
    for mode in ['debug', 'release']:
        output = run('host-tests-' + mode, [SWIFT, 'test', '--package-path', source / 'cli',
            '--scratch-path', WORK / ('swift-' + mode), '--skip-update', '-c', mode, '--filter', filter_value], source)
        require('Test run with 2 tests in 0 suites passed' in output, mode + ' two actual test functions')
        require(output.count('Test case passing 2 arguments') == 6 and 'with 6 test cases passed' in output,
                mode + ' six observed parameterized cases')
    run('build-cli', [SWIFT, 'build', '--package-path', source / 'cli', '--scratch-path', WORK / 'swift-debug',
                     '--skip-update', '--product', 'mixer'], source)
    binary = run('cli-location', [SWIFT, 'build', '--package-path', source / 'cli', '--scratch-path',
                 WORK / 'swift-debug', '--show-bin-path'], source).strip()
    cli = Path(binary) / 'mixer'
    receipt['compiledCLI'] = row(cli)
    app = WORK / 'IndependentConsumer'
    run('create-independent-consumer', [cli, 'create', 'IndependentExport', '--directory', app,
        '--application', 'dev.mixer.independentexport', '--platform', 'android',
        '--sdk-path', source / 'sdk', '--android-adapter-path', source / 'native/android'], source)
    adapter = app / 'Generated/MixerAndroid'
    exported = sorted((adapter / 'app/src').rglob('*.java'))
    expected_names = {Path(path).name for path in expected_java}
    require(len(exported) == 14 and {p.name for p in exported} == expected_names, 'exact independent fourteen-source export')
    for p in exported:
        path = 'native/android/app/src/dev/mixer/android/' + p.name
        require(row(p)['sha256'] == expected_java[path], 'fresh exported accepted source ' + p.name)
    save('exported-java.json', {p.name: row(p) for p in exported})
    lock = json.loads((app / 'mixer.lock').read_text())
    require(lock['android']['toolchain']['min_api'] == 28, 'unchanged compile API28')
    require(lock['android']['adapterDigest'] == producer['generated_lock']['android']['adapterDigest'], 'same generated adapter digest')
    require(not list(app.rglob('descriptor.json')), 'no descriptor/public opt-in introduced')
    empty, positive, negative, dex = [WORK / name for name in ['empty', 'positive', 'negative', 'dex']]
    for folder in [empty, positive, negative, dex]: folder.mkdir()
    common = [JAVAC, '--release', '17', '-Werror', '-Xlint:all', '-implicit:none',
              '-sourcepath', empty, '-classpath', JAR]
    output = run('independent-omit-authored', common + ['-d', negative] +
                 [p for p in exported if p.name != 'AuthoredToggleInputV2.java'], empty, success=False)
    require('AuthoredToggleInputV2' in output and ('cannot find symbol' in output or 'does not exist' in output),
            'omitted source rejected for missing authored type')
    require(not list(negative.rglob('*.class')), 'negative control produced no classes')
    run('independent-java', common + ['-d', positive] + exported, empty)
    classes = manifest(positive)
    require(len(classes) == 160, 'independent 160-class closure')
    for path, expected in baseline['expectedRetainedAuthoredClassArtifacts'].items():
        require(classes[path.removeprefix('production-classes/')] == expected, 'accepted authored class ' + path)
    run('independent-d8', [D8, '--min-api', '28', '--lib', JAR, '--output', dex] + sorted(positive.rglob('*.class')), empty)
    dump = run('independent-dexdump', [DEXDUMP, dex / 'classes.dex'], empty)
    for path in baseline['expectedRetainedAuthoredClassArtifacts']:
        descriptor = 'L' + path.removeprefix('production-classes/').removesuffix('.class') + ';'
        require(descriptor in dump, 'independent DEX descriptor ' + descriptor)
    producer_dex = json.loads((producer_run / 'dex.json').read_text())
    require(manifest(dex) == producer_dex, 'independent exact complete DEX identity')
    mutations = []
    for filename in ['NativeCoordinatorV2.java', 'AuthoredToggleInputV2.java']:
        target = adapter / 'app/src/dev/mixer/android' / filename
        original = target.read_bytes()
        for change in ['edit', 'remove', 'rename']:
            renamed = target.with_suffix('.java.renamed')
            if change == 'edit': target.write_bytes(b'// independent source mutation\n' + original)
            elif change == 'remove': target.unlink()
            else: target.rename(renamed)
            tag = filename.removesuffix('.java') + '-' + change
            try:
                output = run('independent-cli-lock-' + tag, [cli, 'build', '--directory', app, '--platform', 'android'], source, success=False)
                require('lock.android-drift' in output, tag + ' CLI exact lock reason')
                require(not (app / '.mixer').exists(), tag + ' CLI no output creation')
                output = run('independent-driver-lock-' + tag, [sys.executable, adapter / 'android-build.py', 'build', app], source, success=False)
                require('Bundled SDK or Android adapter source differs from mixer.lock.' in output, tag + ' direct driver exact reason')
                require(not (app / '.mixer').exists(), tag + ' direct driver no output creation')
                mutations.append({'filename': filename, 'change': change, 'cliAndDriverRejected': True})
            finally:
                if renamed.exists(): renamed.rename(target)
                target.write_bytes(original)
    save('classes.json', classes)
    save('dex.json', manifest(dex))
    save('mutations.json', mutations)
    save('generated-project.json', manifest(app))
    with tarfile.open(ATTEMPT / 'independent-generated-and-compiled.tar.gz', 'w:gz') as archive:
        for name, folder in [('IndependentConsumer', app), ('classes', positive), ('dex', dex)]:
            archive.add(folder, arcname=name)
    receipt['retainedArchive'] = row(ATTEMPT / 'independent-generated-and-compiled.tar.gz')
    receipt['counts'] = {'javaSources': 14, 'classes': 160, 'acceptedAuthoredClasses': 4,
                         'hostTestFunctionsPerMode': 2, 'hostParameterizedCasesPerMode': 6,
                         'freshConsumerRejections': 12, 'missingSourceControl': 1}
    for name, expected in inputs.items():
        require(row(source / name) == expected, 'replayed frozen source unchanged ' + name)
    for name, expected in seal['files'].items():
        require(row(ROOT / name) == expected, 'root handoff unchanged ' + name)
    receipt['status'] = 'independent-review-passed-scoped-export-only'
except BaseException as failure:
    receipt['status'] = 'failed'
    receipt['failure'] = repr(failure)
    raise
finally:
    alive = []
    for pgid in GROUPS:
        try:
            os.killpg(pgid, 0)
            alive.append(pgid)
        except ProcessLookupError:
            pass
    cleanup = {'ownedCommandGroupsRemaining': alive, 'scratchRemoved': False}
    if not alive and not WORK.is_symlink() and (WORK.stat().st_dev, WORK.stat().st_ino) == IDENTITY and json.loads(OWNER.read_text())['token'] == TOKEN:
        if receipt['status'] == 'failed':
            with tarfile.open(ATTEMPT / 'failed-scratch.tar.gz', 'w:gz') as archive:
                for name in ['IndependentConsumer', 'positive', 'negative', 'dex', '.owner.json']:
                    if (WORK / name).exists(): archive.add(WORK / name, arcname=name)
        shutil.rmtree(WORK)
        cleanup['scratchRemoved'] = not WORK.exists()
    receipt['cleanup'] = cleanup
    receipt['commands'] = COMMANDS
    receipt['checks'] = CHECKS
    receipt['finishedUTC'] = datetime.now(timezone.utc).isoformat()
    save('receipt.json', receipt)
    print(json.dumps({'status': receipt['status'], 'checks': len(CHECKS), 'cleanup': cleanup}, sort_keys=True), flush=True)
