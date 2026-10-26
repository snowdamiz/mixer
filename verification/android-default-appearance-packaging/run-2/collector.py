#!/usr/bin/env python3
"""Owned, bounded host/cross-build collector. No native runtime or discovery."""
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKET = pathlib.Path(__file__).resolve().parent
OUT = PACKET / (sys.argv[1] if len(sys.argv) == 2 else 'run-1')
OUT.mkdir(exist_ok=False)
SCRATCH = pathlib.Path(tempfile.mkdtemp(prefix='mixer-appearance-', dir='/tmp')).resolve()
ENV = os.environ.copy()
ENV['MIXER_JDK'] = str(pathlib.Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home').resolve())
ENV['JAVA_HOME'] = ENV['MIXER_JDK']
ENV['ANDROID_HOME'] = '/opt/homebrew/share/android-commandlinetools'
ENV['PATH'] = str(pathlib.Path(ENV['JAVA_HOME']) / 'bin') + os.pathsep + ENV.get('PATH', '')
COMMANDS = []
GROUPS = set()
RECEIPT = {'schema': 1, 'status': 'running', 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'scope': 'Development default data packaging, host tests and complete unsigned cross-build only.',
           'collector_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
           'native_runtime_or_capture_started': False, 'GA_qualified': False, 'scratch': str(SCRATCH),
           'commands': COMMANDS}
shutil.copy2(pathlib.Path(__file__), OUT / 'collector.py')


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save():
    (OUT / 'receipt.json').write_text(json.dumps(RECEIPT, indent=2) + '\n')


def group_alive(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def run(name, args, timeout=900, cwd=ROOT, success=(0,)):
    args = list(map(str, args))
    stdout, stderr = OUT / (name + '.stdout'), OUT / (name + '.stderr')
    entry = {'name': name, 'argv': args, 'cwd': str(cwd), 'timeout_seconds': timeout,
             'environment_overrides': {k: ENV[k] for k in ['MIXER_JDK', 'JAVA_HOME', 'ANDROID_HOME']}}
    start = time.monotonic()
    print('START', name, flush=True)
    with stdout.open('wb') as output, stderr.open('wb') as error:
        process = subprocess.Popen(args, cwd=cwd, env=ENV, stdout=output, stderr=error, start_new_session=True)
        group = process.pid
        GROUPS.add(group)
        entry['owned_process_group'] = group
        reason = None
        while process.poll() is None:
            if time.monotonic() - start > timeout:
                reason = 'timeout'
                break
            if stdout.stat().st_size + stderr.stat().st_size > 32 * 1024 * 1024:
                reason = 'output-limit'
                break
            time.sleep(0.2)
        if reason:
            os.killpg(group, signal.SIGTERM)
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(group, signal.SIGKILL)
        process.wait()
        # Only this command's dedicated group is inspected or signalled.
        if group_alive(group):
            os.killpg(group, signal.SIGTERM)
            deadline = time.monotonic() + 3
            while group_alive(group) and time.monotonic() < deadline: time.sleep(0.1)
            if group_alive(group): os.killpg(group, signal.SIGKILL)
        if not group_alive(group): GROUPS.discard(group)
    entry.update({'exit': process.returncode, 'stop_reason': reason, 'child_returned': True,
                  'group_gone': group not in GROUPS, 'elapsed_seconds': time.monotonic() - start,
                  'stdout': {'path': stdout.name, **identity(stdout)},
                  'stderr': {'path': stderr.name, **identity(stderr)}})
    COMMANDS.append(entry)
    save()
    print('END', name, 'exit', process.returncode, 'group_gone', entry['group_gone'], flush=True)
    if reason or process.returncode not in success or group in GROUPS:
        raise RuntimeError('Command failed: ' + name)
    return stdout.read_text()


def source_manifest(label):
    paths = run(label + '-paths', ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'cli', 'sdk', 'updates', 'native/android'], timeout=30).splitlines()
    files = {p: identity(ROOT / p) for p in sorted(set(paths)) if (ROOT / p).is_file() and not (ROOT / p).is_symlink()}
    result = {'files': files, 'sha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
    (OUT / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result


try:
    RECEIPT['revision'] = run('revision', ['git', 'rev-parse', 'HEAD'], timeout=30).strip()
    before = source_manifest('product-before')
    for name, args in [('python-version', [sys.executable, '--version']), ('swift-version', ['/usr/bin/swift', '--version']),
                       ('java-version', [pathlib.Path(ENV['JAVA_HOME']) / 'bin/java', '--version']),
                       ('javac-version', [pathlib.Path(ENV['JAVA_HOME']) / 'bin/javac', '--version']),
                       ('aapt2-version', [pathlib.Path(ENV['ANDROID_HOME']) / 'build-tools/37.0.0/aapt2', 'version']),
                       ('d8-version', [pathlib.Path(ENV['ANDROID_HOME']) / 'build-tools/37.0.0/d8', '--version'])]:
        run(name, args, timeout=30)
    run('python-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'cli/build-tests', '-v'], timeout=90)
    selected = 'androidSnapshotOwns|androidCoordinatorAndAuthored|androidDefaultAppearance|directAndroidDriver|unsupportedAndroidRequest|installedDistribution'
    for mode in ['debug', 'release']:
        run('swift-tests-' + mode, ['/usr/bin/swift', 'test', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / ('cli-' + mode), '-c', mode, '--filter', selected])
    run('build-cli', ['/usr/bin/swift', 'build', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / 'cli-debug', '--product', 'mixer'])
    bindir = pathlib.Path(run('cli-bin-path', ['/usr/bin/swift', 'build', '--package-path', ROOT / 'cli', '--scratch-path', SCRATCH / 'cli-debug', '--show-bin-path']).strip())
    cli = bindir / 'mixer'
    RECEIPT['compiled_cli'] = identity(cli)
    app = SCRATCH / 'AppearanceConsumer'
    run('create-consumer', [cli, 'create', 'AppearanceConsumer', '--directory', app, '--application', 'dev.mixer.appearanceconsumer', '--platform', 'android', '--sdk-path', ROOT / 'sdk', '--android-adapter-path', ROOT / 'native/android'], timeout=1200)
    RECEIPT['generated_project'] = {str(p.relative_to(app)): identity(p) for p in sorted(app.rglob('*')) if p.is_file()}
    adapter = app / 'Generated/MixerAndroid'
    descriptor = adapter / 'app/assets/MixerAppearanceV2/descriptor.json'
    RECEIPT['created_descriptor'] = identity(descriptor)
    shutil.copy2(descriptor, OUT / 'created-descriptor.json')
    run('actual-generated-driver-build', [sys.executable, '-B', adapter / 'android-build.py', 'build', app], timeout=1200)
    output = app / '.mixer/android-build'
    apk = output / 'AppearanceConsumer-unsigned.apk'
    shutil.copy2(output / 'build-receipt.json', OUT / 'generated-build-receipt.json')
    shutil.copy2(apk, OUT / apk.name)
    RECEIPT['apk'] = identity(apk)
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assets = [n for n in names if n == 'assets' or n.startswith('assets/')]
        assert assets == ['assets/MixerAppearanceV2/descriptor.json']
        final = archive.read(assets[0])
        assert final == descriptor.read_bytes()
        (OUT / 'final-descriptor.json').write_bytes(final)
        (OUT / 'apk-inventory.json').write_text(json.dumps({n: {'bytes': archive.getinfo(n).file_size, 'sha256': hashlib.sha256(archive.read(n)).hexdigest()} for n in names}, indent=2) + '\n')
    RECEIPT['final_descriptor'] = identity(OUT / 'final-descriptor.json')
    RECEIPT['classes'] = {str(p.relative_to(output / 'classes')): identity(p) for p in sorted((output / 'classes').rglob('*.class'))}
    prior = ROOT / 'verification/android-authored-toggle-generated-export/commands/run-1'
    old = json.loads((prior / 'receipt.json').read_text())
    java_sources = {p.name: identity(p) for p in sorted((adapter / 'app/src').rglob('*.java'))}
    assert java_sources == old['exported_java']
    historical_classes = {}
    with tarfile.open(prior / 'generated-and-compiled.tar.gz') as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.startswith('classes/') and member.name.endswith('.class'):
                data = archive.extractfile(member).read()
                historical_classes[member.name.removeprefix('classes/')] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    assert historical_classes and historical_classes == RECEIPT['classes']
    RECEIPT['accepted_java_binding'] = {'sources_equal': True, 'classes_equal': True, 'source_count': len(java_sources), 'class_count': len(historical_classes), 'prior_receipt': str((prior / 'receipt.json').relative_to(ROOT)), 'prior_receipt_identity': identity(prior / 'receipt.json')}
    probe = SCRATCH / 'AppearanceProbe.java'
    probe.write_text('''package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
public final class AppearanceProbe {
  public static void main(String[] args) throws Exception {
    byte[] bytes = Files.readAllBytes(Path.of(args[0]));
    AppearanceDescriptorV2 value = AppearanceDescriptorV2.decode(bytes);
    if (value.mode != AppearanceDescriptorV2.Mode.shared || !value.resources.isEmpty()
        || !(value.android.typography().font() instanceof AppearanceDescriptorV2.SystemSans)) throw new AssertionError("shape");
    System.out.println("production Java codec accepted shared empty-catalog systemSans; bytes=" + bytes.length + "; id=" + value.id);
  }
}
''')
    shutil.copy2(probe, OUT / probe.name)
    run('javac-final-codec-probe', [pathlib.Path(ENV['JAVA_HOME']) / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-classpath', output / 'classes', '-d', SCRATCH / 'probe-classes', probe])
    run('java-final-codec-probe', [pathlib.Path(ENV['JAVA_HOME']) / 'bin/java', '-cp', str(output / 'classes') + os.pathsep + str(SCRATCH / 'probe-classes'), 'dev.mixer.android.AppearanceProbe', OUT / 'final-descriptor.json'])
    host = SCRATCH / 'swift-codec'
    (host / 'Sources/Probe').mkdir(parents=True)
    for name in ['MixerCore', 'MixerUI']:
        shutil.copytree(app / 'Generated/MixerSDK/Sources' / name, host / 'Sources' / name)
    (host / 'Package.swift').write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "AppearanceProbe", targets: [.target(name: "MixerCore"), .target(name: "MixerUI", dependencies: ["MixerCore"]), .executableTarget(name: "Probe", dependencies: ["MixerUI"])])
''')
    (host / 'Sources/Probe/main.swift').write_text('''import Foundation
import MixerUI
let bytes = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let value = try UIAppearanceDescriptorCodecV2.decode(bytes)
let selectedDefault = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
let canonical = try UIAppearanceDescriptorCodecV2.canonicalData(value)
guard value == selectedDefault, canonical == bytes, value.resources.isEmpty,
      case let .shared(theme) = value.mode, theme.typography.font == .systemSans else { fatalError("shape/default/bytes") }
print("production Swift codec accepted selected SDK observed default equality; bytes=\\(bytes.count); id=\\(value.id)")
''')
    shutil.copy2(host / 'Package.swift', OUT / 'SwiftProbe-Package.swift')
    shutil.copy2(host / 'Sources/Probe/main.swift', OUT / 'SwiftProbe-main.swift')
    run('swift-final-codec-probe', ['/usr/bin/swift', 'run', '--package-path', host, '--scratch-path', SCRATCH / 'swift-codec-build', '-c', 'release', 'Probe', OUT / 'final-descriptor.json'])
    with tarfile.open(OUT / 'generated-source-and-classes.tar.gz', 'w:gz') as archive:
        for path in sorted(app.rglob('*')):
            relative = path.relative_to(app)
            if path.is_file() and not any(part in {'.build', '.mixer', '.swiftpm'} for part in relative.parts): archive.add(path, arcname='AppearanceConsumer/' + str(relative), recursive=False)
        for path in sorted((output / 'classes').rglob('*.class')):
            archive.add(path, arcname='classes/' + str(path.relative_to(output / 'classes')), recursive=False)
        for path in sorted((output / 'dex').glob('*.dex')):
            archive.add(path, arcname='dex/' + path.name, recursive=False)
    RECEIPT['retained_sources_and_classes'] = identity(OUT / 'generated-source-and-classes.tar.gz')
    after = source_manifest('product-after')
    RECEIPT['product_before_sha256'] = before['sha256']
    RECEIPT['product_after_sha256'] = after['sha256']
    RECEIPT['inputs_unchanged_during_collection'] = before == after
    assert before == after
    RECEIPT['status'] = 'passed-producer-evidence-awaiting-independent-review'
except BaseException as error:
    RECEIPT['status'] = 'failed'
    RECEIPT['error'] = repr(error)
    raise
finally:
    remaining = [group for group in GROUPS if group_alive(group)]
    RECEIPT['cleanup'] = {'owned_process_groups_remaining': remaining, 'scratch_removed': False}
    if not remaining:
        shutil.rmtree(SCRATCH)
        RECEIPT['cleanup']['scratch_removed'] = not SCRATCH.exists()
    RECEIPT['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
