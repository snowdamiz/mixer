#!/usr/bin/env python3
"""Exercise the actual generated Java closure, without native runtime execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
RUN = PACKET / 'commands' / sys.argv[1]
RUN.mkdir(parents=True)
TOKEN = uuid.uuid4().hex
SCRATCH = Path(tempfile.mkdtemp(prefix='mixer-generated-java-' + TOKEN + '-'))
MARKER = SCRATCH / '.owner.json'
MARKER.write_text(json.dumps({'owner': str(PACKET), 'token': TOKEN}) + '\n')
IDENTITY = (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino)
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve()
SDK = Path('/opt/homebrew/share/android-commandlinetools')
JAR = SDK / 'platforms/android-37.0/android.jar'
BT = SDK / 'build-tools/37.0.0'
SWIFT = Path(shutil.which('swift')).absolute()
ENV = os.environ.copy()
ENV.update({'JAVA_HOME': str(JDK), 'MIXER_JDK': str(JDK), 'ANDROID_HOME': str(SDK),
            'PATH': str(JDK / 'bin') + os.pathsep + ENV.get('PATH', '')})
JAVA = ['Json.java', 'UiPacket.java', 'NativeRenderer.java', 'NativeBridge.java',
        'MixerActivity.java', 'NativeCoordinatorV2.java', 'AppearanceDescriptorV2.java',
        'AppearanceGeometryV2.java', 'AppearanceResolverV2.java', 'AppearanceNativePathsV2.java',
        'InstalledAppearanceV2.java', 'NativeEnvironmentV2.java', 'AuthoredToggleInputV2.java',
        'NativeAppearanceViewsV2.java']
COMMANDS = []
GROUPS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha(raw)}


def manifest(folder):
    return {str(p.relative_to(folder)): row(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def save(name, value):
    (RUN / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def run(name, args, *, cwd=ROOT, timeout=900, success=True):
    args = list(map(str, args))
    started = time.monotonic()
    out, err = RUN / (name + '.stdout'), RUN / (name + '.stderr')
    timed_out = False
    with out.open('wb') as stdout, err.open('wb') as stderr:
        process = subprocess.Popen(args, cwd=cwd, env=ENV, stdout=stdout, stderr=stderr, start_new_session=True)
        GROUPS.append(process.pid)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    item = {'name': name, 'argv': args, 'cwd': str(cwd), 'exit': code,
            'timeout_seconds': timeout, 'timed_out': timed_out, 'child_returned': True,
            'elapsed_seconds': time.monotonic() - started,
            'environment_overrides': {k: ENV[k] for k in ['JAVA_HOME', 'MIXER_JDK', 'ANDROID_HOME']},
            'stdout': {'path': out.name, **row(out)}, 'stderr': {'path': err.name, **row(err)}}
    COMMANDS.append(item)
    save(name + '.json', item)
    require(not timed_out and ((code == 0) if success else (code != 0)), name + ' unexpected result')
    return out.read_text(errors='replace') + err.read_text(errors='replace')


def inputs():
    tracked = subprocess.check_output(['git', 'ls-files', '-z', 'cli', 'sdk', 'updates'], cwd=ROOT).split(b'\0')
    selected = [p.decode() for p in tracked if p and ('/Sources/' in p.decode() or '/Tests/' in p.decode() or p.decode().endswith('/Package.swift'))]
    selected += ['native/android/app/src/dev/mixer/android/' + name for name in JAVA]
    selected += ['native/android/bridge/jni.c', 'native/android/bridge/mixer_android.h',
                 'native/android/bridge/mixer_android_v2.h', 'native/android/contracts/android-profile-v1.json']
    selected += [str(p.relative_to(ROOT)) for p in (ROOT / 'native/android/engine/Sources/MixerAndroidRuntime').rglob('*.swift')]
    return {name: row(ROOT / name) for name in sorted(set(selected))}


result = {'schema': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
          'scope': 'Actual CLI create, exported Java/D8 compilation and source-lock refusal only',
          'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT)), sys.argv[1]],
          'collector_sha256': sha(Path(__file__).read_bytes()), 'python': platform.python_version(),
          'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'scratch': str(SCRATCH), 'ownership': json.loads(MARKER.read_text()),
          'native_runtime_or_capture_started': False, 'product_or_GA_qualification': False}
try:
    before = inputs()
    save('inputs-before.json', before)
    result['source_tree_sha256'] = sha(json.dumps(before, sort_keys=True, separators=(',', ':')).encode())
    require(before['native/android/app/src/dev/mixer/android/AuthoredToggleInputV2.java']['sha256'] == '4b5f890ee7d3d7f4f4b17ba79bc8a44a8f26fa916e5ecd3c04a3c21fa98978fd', 'accepted authored source differs')
    snapshots = RUN / 'source-inputs'
    for name in before:
        target = snapshots / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    result['tools'] = {str(p): row(p.resolve()) for p in [SWIFT, JDK / 'bin/java', JDK / 'bin/javac', BT / 'd8', BT / 'dexdump', JAR]}
    run('swift-version', [SWIFT, '--version'], timeout=30)
    run('java-version', [JDK / 'bin/java', '--version'], timeout=30)
    run('javac-version', [JDK / 'bin/javac', '--version'], timeout=30)
    run('d8-version', [BT / 'd8', '--version'], timeout=30)
    test_filter = 'androidSnapshotOwnsOnlyRuntimeRendererCoordinatorAndBridgeAndLocksExactBytes|androidCoordinatorAndAuthoredToggleSnapshotChangesInvalidateAdapterLock'
    for config in ['debug', 'release']:
        run('swift-tests-' + config, [SWIFT, 'test', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / ('swift-' + config), '-c', config, '--filter', test_filter])
    run('build-cli', [SWIFT, 'build', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / 'swift-debug', '--product', 'mixer'])
    binary_path = run('cli-bin-path', [SWIFT, 'build', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / 'swift-debug', '--show-bin-path']).strip()
    cli = Path(binary_path) / 'mixer'
    result['compiled_cli'] = {'path': str(cli), **row(cli)}
    app = SCRATCH / 'GeneratedConsumer'
    run('create-consumer', [cli, 'create', 'ExportProbe', '--directory', app, '--application', 'dev.mixer.exportprobe', '--platform', 'android', '--sdk-path', ROOT / 'sdk', '--android-adapter-path', ROOT / 'native/android'])
    adapter = app / 'Generated/MixerAndroid'
    exported = sorted((adapter / 'app/src').rglob('*.java'))
    require(len(exported) == 14 and {p.name for p in exported} == set(JAVA), 'exported Java closure differs')
    for p in exported:
        require(p.read_bytes() == (ROOT / 'native/android/app/src/dev/mixer/android' / p.name).read_bytes(), 'exported source differs: ' + p.name)
    result['exported_java'] = {p.name: row(p) for p in exported}
    result['generated_lock'] = json.loads((app / 'mixer.lock').read_text())
    empty, classes, negative, dex = [SCRATCH / n for n in ['empty-sourcepath', 'classes', 'negative-classes', 'dex']]
    for p in [empty, classes, negative, dex]:
        p.mkdir()
    common = [JDK / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-implicit:none', '-sourcepath', empty, '-classpath', JAR]
    bad = run('javac-omitted-source-control', common + ['-d', negative] + [p for p in exported if p.name != 'AuthoredToggleInputV2.java'], cwd=empty, success=False)
    require('AuthoredToggleInputV2' in bad and ('cannot find symbol' in bad or 'does not exist' in bad), 'negative control failed for unrelated reason')
    run('javac-exported', common + ['-d', classes] + exported, cwd=empty)
    class_manifest = manifest(classes)
    authored = [n for n in class_manifest if '/AuthoredToggleInputV2' in n]
    require(len(authored) == 4 and 'dev/mixer/android/AuthoredToggleInputV2.class' in authored, 'authored classes absent')
    save('classes.json', class_manifest)
    run('d8-exported', [BT / 'd8', '--min-api', '28', '--lib', JAR, '--output', dex] + sorted(classes.rglob('*.class')), cwd=empty)
    dump = run('dexdump-exported', [BT / 'dexdump', dex / 'classes.dex'], cwd=empty)
    for name in authored:
        require('L' + name[:-6] + ';' in dump, 'authored class absent from DEX: ' + name)
    save('dex.json', manifest(dex))
    source = adapter / 'app/src/dev/mixer/android/AuthoredToggleInputV2.java'
    original = source.read_bytes()
    for change in ['edit', 'remove', 'rename']:
        renamed = source.with_suffix('.java.renamed')
        if change == 'edit':
            source.write_bytes(b'changed source\n')
        elif change == 'remove':
            source.unlink()
        else:
            source.rename(renamed)
        cli_error = run('cli-lock-' + change, [cli, 'build', '--platform', 'android', '--directory', app], success=False)
        require('lock.android-drift' in cli_error, 'CLI failed for unrelated reason')
        direct_error = run('driver-lock-' + change, [sys.executable, adapter / 'android-build.py', 'build', app], success=False)
        require('Bundled SDK or Android adapter source differs from mixer.lock.' in direct_error, 'driver failed for unrelated reason')
        require(not (app / '.mixer').exists(), 'drift created build output')
        if renamed.exists():
            renamed.rename(source)
        source.write_bytes(original)
    result['generated_project'] = manifest(app)
    save('generated-project.json', result['generated_project'])
    with tarfile.open(RUN / 'generated-and-compiled.tar.gz', 'w:gz') as archive:
        for name, folder in [('GeneratedConsumer', app), ('classes', classes), ('dex', dex)]:
            archive.add(folder, arcname=name)
    result['retained_archive'] = row(RUN / 'generated-and-compiled.tar.gz')
    result['status'] = 'passed'
    result['counts'] = {'java_sources': 14, 'authored_classes': 4, 'classes': len(class_manifest), 'test_functions_per_configuration': 2, 'parameterized_lock_cases_per_configuration': 6, 'actual_consumer_drift_rejections': 6, 'omitted_source_negative_controls': 1}
except BaseException as error:
    result['status'] = 'failed'
    result['error'] = repr(error)
    raise
finally:
    after = inputs()
    save('inputs-after.json', after)
    result['inputs_unchanged'] = before == after
    result['commands'] = COMMANDS
    alive = []
    for group in GROUPS:
        try:
            os.killpg(group, 0)
            alive.append(group)
        except ProcessLookupError:
            pass
    result['cleanup'] = {'owned_process_groups_remaining': alive, 'removed': False}
    if not alive and not SCRATCH.is_symlink() and (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino) == IDENTITY and json.loads(MARKER.read_text())['token'] == TOKEN:
        if result['status'] == 'failed':
            with tarfile.open(RUN / 'failed-generated-artifacts.tar.gz', 'w:gz') as archive:
                for name in ['GeneratedConsumer', 'classes', 'negative-classes', 'dex', '.owner.json']:
                    if (SCRATCH / name).exists():
                        archive.add(SCRATCH / name, arcname=name)
        shutil.rmtree(SCRATCH)
        result['cleanup']['removed'] = not SCRATCH.exists()
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    save('receipt.json', result)
    print(json.dumps({'status': result['status'], 'counts': result.get('counts'), 'inputs_unchanged': result['inputs_unchanged'], 'cleanup': result['cleanup']}))
