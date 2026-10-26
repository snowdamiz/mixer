#!/usr/bin/env python3
"""Independent fresh CLI/consumer execution from the root-frozen source archive."""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import traceback
import zipfile

from review_runtime import Runner, digest

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCE = BASE / 'frozen-source'
PRODUCER = ROOT / 'verification/android-default-appearance-packaging'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(root):
    skip = {'.build', '.git', '.swiftpm', '.mixer', 'node_modules', '__pycache__'}
    result = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in skip)
        for name in sorted(names):
            path = pathlib.Path(base) / name
            assert path.is_file() and not path.is_symlink(), str(path)
            result[path.relative_to(root).as_posix()] = {'bytes': path.stat().st_size, 'sha256': digest(path)}
    return result


def main():
    name = sys.argv[sys.argv.index('--run-name') + 1] if '--run-name' in sys.argv else 'independent-run-1'
    assert name.startswith('independent-run-') and '/' not in name
    out = BASE / name
    out.mkdir(exist_ok=False)
    runner = Runner(out)
    scratch = pathlib.Path(tempfile.mkdtemp(prefix='mixer-review-', dir='/tmp')).resolve()
    receipt = {'schema_version': 1, 'status': 'running', 'scratch': str(scratch),
               'source_archive_sha256': '2f6268251008747bcb60dbacba44d8d8a7dfb30f7b3b55d8c1caa4e16d9e70c5',
               'source_sha256': '2d3058772475493328a86abd8f4417aae87cf517337184e615da8344b5ca5aed',
               'scope': 'Independent host vectors, actual fresh CLI and complete unsigned cross-build; no native runtime/signing/release authority',
               'vectors': {}, 'tool_identities': {}, 'native_runtime_or_capture_started': False}
    def save():
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    def passed(identifier, detail):
        receipt['vectors'][identifier] = {'status': 'passed', 'detail': detail}; save()
    try:
        source_manifest = json.loads((BASE / 'handoff-inspection.json').read_text())['source_files']
        for name, row in source_manifest.items():
            assert digest(SOURCE / name) == row['sha256'], name
        work = scratch / 'source'; shutil.copytree(SOURCE, work)
        source_before = manifest(work)
        assert source_before == source_manifest
        receipt['source_files'] = len(source_before)
        if '--reuse-host-evidence' not in sys.argv:
            python_output = runner.run('python-selected-suites', [sys.executable, '-B', '-m', 'unittest', 'discover',
                '-s', work / 'cli/build-tests', '-p', 'test_android*.py', '-v'], work, timeout=90)
            assert 'OK' in python_output[1] and 'Ran 20 tests' in python_output[1]
        else:
            previous = json.loads((BASE / 'independent-run-1/receipt.json').read_text())
            assert previous['source_sha256'] == receipt['source_sha256']
            assert previous['vectors']['S01']['status'] == 'passed'
            receipt['reused_exact_source_host_evidence'] = {'receipt': 'independent-run-1/receipt.json',
                'sha256': digest(BASE / 'independent-run-1/receipt.json'),
                'scope': 'Exact-source 20 Python methods and 42 adversarial host vectors completed before collector version-probe error.'}
        passed('S01', 'Exact frozen 20-test Python suite passed; staging changed only minimum valid-asset fixture and matching digest.')
        vector_out = BASE / 'adversarial-2'
        if '--reuse-host-evidence' not in sys.argv:
            runner.run('independent-host-vectors', [sys.executable, '-B', BASE / 'independent_vectors.py', '--output', vector_out], ROOT, timeout=90)
        vector_result = json.loads((vector_out / 'summary.json').read_text())
        assert vector_result['status'] == 'passed' and vector_result['cases'] == 42
        receipt['vectors'].update(vector_result['results']); save()
        spec = importlib.util.spec_from_file_location('review_tool_identity_driver', work / 'cli/Sources/MixerBuild/Resources/android-build.py')
        build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
        runner.environment = os.environ.copy()
        runner.environment['JAVA_HOME'] = str(build.JDK)
        runner.environment['PATH'] = str(build.JDK / 'bin') + os.pathsep + runner.environment.get('PATH', '')
        receipt['environment_overrides'] = {'JAVA_HOME': str(build.JDK), 'PATH_prefix': str(build.JDK / 'bin')}
        tools = {'host_swift': pathlib.Path(shutil.which('swift')).absolute(), 'android_swift': build.SWIFT.absolute(),
                 'python': pathlib.Path(sys.executable).resolve(), 'javac': build.JDK / 'bin/javac',
                 'java': build.JDK / 'bin/java', 'aapt2': build.BT / 'aapt2', 'd8': build.BT / 'd8',
                 'zipalign': build.BT / 'zipalign', 'android_jar': build.JAR}
        for name, path in tools.items():
            receipt['tool_identities'][name] = {'path': str(path), 'resolved_path': str(path.resolve()), 'sha256': digest(path)}
        for name, args in [('host_swift', ['--version']), ('android_swift', ['--version']),
                           ('python', ['--version']), ('javac', ['--version']), ('java', ['--version']),
                           ('aapt2', ['version']), ('d8', ['--version'])]:
            stdout, stderr, _ = runner.run('tool-' + name, [tools[name], *args], work, timeout=15)
            receipt['tool_identities'][name]['version_stdout'] = stdout
            receipt['tool_identities'][name]['version_stderr'] = stderr
        save()
        cli_scratch = scratch / 'cli-build'
        cli_args = [tools['host_swift'], 'build', '--package-path', work / 'cli', '--scratch-path', cli_scratch,
                    '-j', '2', '--product', 'mixer']
        runner.run('fresh-cli-build', cli_args, work, timeout=600)
        stdout, _, _ = runner.run('fresh-cli-bin-path', [*cli_args, '--show-bin-path'], work, timeout=20)
        cli = pathlib.Path(stdout.strip()) / 'mixer'; assert cli.is_file()
        receipt['compiled_cli'] = {'bytes': cli.stat().st_size, 'sha256': digest(cli)}; save()
        app = scratch / 'IndependentAppearanceConsumer'
        def create(label, name, target, sdk, platform='android', expected=0):
            args = [cli, 'create', name, '--directory', target, '--application', 'dev.mixer.independentreview',
                    '--sdk-path', sdk, '--platform', platform]
            if platform == 'android': args += ['--android-adapter-path', work / 'native/android']
            return runner.run(label, args, work, timeout=180, expected=expected)
        create('fresh-cli-create-android', 'IndependentAppearanceConsumer', app, work / 'sdk')
        descriptor = app / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'
        expected = descriptor.read_bytes()
        assert len(expected) == 9587 and sha(expected) == '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'
        created_manifest = manifest(app)
        (out / 'generated-source-manifest.json').write_text(json.dumps(created_manifest, indent=2, sort_keys=True) + '\n')
        adapter = app / 'Generated/MixerAndroid'
        java_files = sorted((adapter / 'app/src').rglob('*.java'))
        assert len(java_files) == 14
        for path in java_files:
            assert path.read_bytes() == (work / 'native/android' / path.relative_to(adapter)).read_bytes()
        generated_lock = json.loads((app / 'mixer.lock').read_text())
        assert build.source_tree(adapter) == generated_lock['android']['adapterDigest']
        assert build.source_tree(app / 'Generated/MixerSDK') == generated_lock['sdkDigest']
        passed('G01', {'descriptor_bytes': len(expected), 'descriptor_sha256': sha(expected),
                       'exact_exported_java_sources': len(java_files), 'locks_match_before_build': True})
        existing = scratch / 'Existing'; existing.mkdir(); (existing / 'sentinel').write_bytes(b'preserve existing destination')
        existing_before = manifest(existing)
        create('fresh-cli-refuse-existing', 'Existing', existing, work / 'sdk', expected=1)
        assert manifest(existing) == existing_before
        assert not list(scratch.glob('.mixer-create-*'))
        passed('G03', 'Existing destination unchanged and no owned creation staging remained.')
        ios = scratch / 'IndependentIOS'
        create('fresh-cli-create-ios', 'IndependentIOS', ios, work / 'sdk', platform='ios')
        assert not (ios / 'Generated/MixerAndroid').exists()
        assert not (ios / 'Platforms/Android/app/assets').exists()
        passed('G05', 'Actual iOS-only create emitted no Android adapter/default asset and returned successfully.')
        alternate = scratch / 'SDKWithoutDefaultAPI'; shutil.copytree(work / 'sdk', alternate)
        alternate_default = alternate / 'Sources/MixerUI/AppearanceDefaultV2.swift'
        original_default = alternate_default.read_text()
        needle = 'static func mixerDefaultV2()'
        assert original_default.count(needle) == 1
        alternate_default.write_text(original_default.replace(needle, 'static func reviewDeliberatelyAbsentDefaultV2()', 1))
        alternate_app = scratch / 'NoCopiedDefaultAPI'
        create('fresh-cli-create-absent-copied-api', 'NoCopiedDefaultAPI', alternate_app, alternate)
        alternate_bytes = (alternate_app / 'Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json').read_bytes()
        assert alternate_bytes == expected
        assert build.source_tree(alternate_app / 'Generated/MixerSDK') != generated_lock['sdkDigest']
        assert not list(scratch.glob('.mixer-create-*'))
        passed('G02', 'Create-only absent copied-SDK API succeeded with exact CLI-owned asset; no copied-SDK compatibility claim or cross-build uses this fixture.')
        passed('G04', 'Exact six-path diff reviewed; one typed CLI producer and exact snapshot bytes; native/V1/SDK/updates/ProjectGenerator/ProcessRunner unchanged. G02 independently proves no copied-SDK compile gate.')
        generated_driver = adapter / 'android-build.py'
        assert digest(generated_driver) == digest(work / 'cli/Sources/MixerBuild/Resources/android-build.py')
        runner.run('fresh-generated-complete-unsigned-build', [sys.executable, '-B', generated_driver, 'build', app], app, timeout=900)
        output = app / '.mixer/android-build'
        build_receipt = json.loads((output / 'build-receipt.json').read_text())
        apk = pathlib.Path(build_receipt['apk'])
        with zipfile.ZipFile(apk) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names))
            assets = [name for name in names if name == 'assets' or name.startswith('assets/')]
            assert assets == ['assets/MixerAppearanceV2/descriptor.json']
            extracted = archive.read(assets[0]); assert extracted == expected
            assert not any(name.startswith('META-INF/') or 'ChecklistEngine' in name for name in names)
            apk_inventory = {name: {'bytes': archive.getinfo(name).file_size, 'sha256': sha(archive.read(name))} for name in sorted(names)}
        assert build_receipt['qualification'] == 'local-unsigned-cross-build-only'
        assert build_receipt['appearance_descriptor']['sha256'] == sha(expected)
        assert build_receipt['source_tree_sha256'] == build_receipt['source_tree_after_sha256']
        assert manifest(app) == created_manifest
        shutil.copy2(apk, out / apk.name)
        shutil.copy2(output / 'build-receipt.json', out / 'generated-build-receipt.json')
        (out / 'apk-inventory.json').write_text(json.dumps(apk_inventory, indent=2, sort_keys=True) + '\n')
        (out / 'extracted-descriptor.json').write_bytes(extracted)
        receipt['apk'] = {'bytes': apk.stat().st_size, 'sha256': digest(apk), 'members': len(names), 'complete_asset_inventory': assets}
        classes = {path.relative_to(output / 'classes').as_posix(): digest(path) for path in sorted((output / 'classes').rglob('*.class'))}
        producer_classes = {}
        with tarfile.open(PRODUCER / 'run-2/generated-source-and-classes.tar.gz', 'r:gz') as archive:
            for member in archive:
                if member.isfile() and member.name.startswith('classes/'):
                    producer_classes[member.name[len('classes/'):]] = sha(archive.extractfile(member).read())
        assert classes == producer_classes and len(classes) == 160
        receipt['classes_match_frozen_producer_exactly'] = len(classes)
        (out / 'class-manifest.json').write_text(json.dumps(classes, indent=2, sort_keys=True) + '\n')
        with tarfile.open(out / 'generated-source-and-classes.tar.gz', 'w:gz') as archive:
            for name in created_manifest: archive.add(app / name, arcname='project/' + name, recursive=False)
            for name in classes: archive.add(output / 'classes' / name, arcname='classes/' + name, recursive=False)
        passed('B01', {'actual_generated_unsigned_apk': receipt['apk'], 'production_classes': len(classes),
                       'source_before_after_equal': True, 'fresh_source_and_classes_retained': True})
        probe = scratch / 'CodecProbe'; (probe / 'Sources/Probe').mkdir(parents=True)
        for target in ['MixerCore', 'MixerUI']:
            shutil.copytree(app / 'Generated/MixerSDK/Sources' / target, probe / 'Sources' / target)
        (probe / 'Package.swift').write_text('// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: "IndependentCodecProbe", targets: [.target(name: "MixerCore"), .target(name: "MixerUI", dependencies: ["MixerCore"]), .executableTarget(name: "Probe", dependencies: ["MixerUI"])], swiftLanguageModes: [.v6])\n')
        (probe / 'Sources/Probe/main.swift').write_text('''import Foundation
import MixerUI
let actual = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let value = try UIAppearanceDescriptorCodecV2.decode(actual)
let expected = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(expected)
guard value == expected, actual == bytes, value.resources.isEmpty,
      case let .shared(theme) = value.mode, theme.typography.font == .systemSans else { fatalError("canonical API identity mismatch") }
do { _ = try UIAppearanceDescriptorCodecV2.decode(actual + Data([32])); fatalError("noncanonical accepted") }
catch let error as UIAppearanceErrorV2 { guard error == .noncanonical else { fatalError("wrong rejection") } }
try bytes.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
print("realSwiftCodec=shared/default/emptyCatalog/systemSans canonicalBytes=\\(bytes.count) noncanonicalRejected=true")
''')
        derived = out / 'api-derived-default.json'
        runner.run('fresh-real-swift-codec', [tools['host_swift'], 'run', '--package-path', probe, '--scratch-path', scratch / 'codec-build', '-j', '2', 'Probe', out / 'extracted-descriptor.json', derived], probe, timeout=300)
        assert derived.read_bytes() == extracted
        java_probe = scratch / 'IndependentDescriptorProbe.java'
        java_probe.write_text('''package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
final class IndependentDescriptorProbe {
 public static void main(String[] args) throws Exception {
  byte[] bytes=Files.readAllBytes(Path.of(args[0]));
  AppearanceDescriptorV2 d=AppearanceDescriptorV2.decode(bytes);
  if(d.mode!=AppearanceDescriptorV2.Mode.shared || d.iOS!=d.android || !d.resources.isEmpty() || !(d.iOS.typography().font() instanceof AppearanceDescriptorV2.SystemSans)) throw new AssertionError("default contract");
  byte[] bad=java.util.Arrays.copyOf(bytes,bytes.length+1);bad[bytes.length]=32;
  try { AppearanceDescriptorV2.decode(bad);throw new AssertionError("noncanonical accepted"); }
  catch(AppearanceDescriptorV2.Failure e){if(e.code!=AppearanceDescriptorV2.Error.noncanonical)throw e;}
  System.out.println("realJavaCodec=shared/identicalTheme/emptyCatalog/systemSans noncanonicalRejected=true");
 }
}
''')
        java_output = scratch / 'java-probe'; java_output.mkdir()
        empty_source = scratch / 'empty-source'; empty_source.mkdir()
        runner.run('fresh-java-probe-compile', [tools['javac'], '--release', '17', '-Xlint:all', '-Werror', '-implicit:none',
                   '-sourcepath', empty_source, '-classpath', output / 'classes', '-d', java_output, java_probe], scratch, timeout=30)
        runner.run('fresh-real-java-codec', [tools['java'], '-classpath', str(java_output) + os.pathsep + str(output / 'classes'),
                   'dev.mixer.android.IndependentDescriptorProbe', out / 'extracted-descriptor.json'], scratch, timeout=15)
        passed('B02', {'real_swift_and_java_codecs_executed': True, 'fresh_api_output_equals_actual_apk': True,
                       'noncanonical_negative_rejected_by_both': True, 'installed_capture_executed': False})
        final_output_before = {'apk': digest(apk), 'receipt': digest(output / 'build-receipt.json')}
        cli_case_logs = {}
        def cli_reject(identifier, path, operation='edit'):
            data = path.read_bytes()
            renamed = path.with_name(path.name + '.review-renamed')
            try:
                if operation == 'remove': path.unlink()
                elif operation == 'rename': path.rename(renamed)
                else: path.write_bytes(data + b'\nreview mutation\n')
                _, _, row = runner.run('cli-lock-' + identifier + '-' + operation, [cli, 'build', '--platform', 'android', '--directory', app], app, timeout=30, expected=1)
                assert digest(apk) == final_output_before['apk'] and digest(output / 'build-receipt.json') == final_output_before['receipt']
                cli_case_logs.setdefault(identifier, []).append(row['label'])
            finally:
                if renamed.exists(): renamed.rename(path)
                else: path.write_bytes(data)
        cli_reject('L01', descriptor)
        cli_reject('L02', adapter / 'app/src/dev/mixer/android/AuthoredToggleInputV2.java')
        for operation in ['remove', 'rename']:
            cli_reject('L03', adapter / 'app/src/dev/mixer/android/AuthoredToggleInputV2.java', operation)
        cli_reject('L04', app / 'Generated/MixerSDK/Sources/MixerUI/AppearanceDefaultV2.swift')
        for identifier, labels in cli_case_logs.items():
            receipt['vectors'][identifier]['detail']['cli_lock_layer'] = {'actual_fresh_cli_rejected': labels, 'original_unsigned_outputs_unchanged': True}
        for identifier, filenames in [('R01', ['extra.txt']), ('R02', ['.hidden', 'extra.pem'])]:
            labels = []
            for index, name in enumerate(filenames):
                path = app / 'Resources' / name; path.write_bytes(b'unsupported review app resource')
                try:
                    stdout, stderr, row = runner.run('cli-resource-' + identifier + '-' + str(index), [cli, 'build', '--platform', 'android', '--directory', app], app, timeout=30, expected=1)
                    assert 'resource' in (stdout + stderr).lower()
                    assert digest(apk) == final_output_before['apk'] and digest(output / 'build-receipt.json') == final_output_before['receipt']
                    labels.append(row['label'])
                finally: path.unlink()
            receipt['vectors'][identifier]['detail']['cli_layer'] = {'actual_fresh_cli_rejected': labels, 'original_unsigned_outputs_unchanged': True}
        assert manifest(app) == created_manifest
        assert manifest(work) == source_before
        assert set(receipt['vectors']) == {row['id'] for row in json.loads((BASE / 'vectors.json').read_text())['vectors']}
        assert all(row['status'] == 'passed' for row in receipt['vectors'].values())
        receipt['status'] = 'independent-selected-development-contract-checks-passed'
        receipt['source_inputs_unchanged'] = True
        receipt['pending'] = ['Copied-SDK default/API/ABI compatibility', 'Public V2 native capture/lifecycle',
                              'API28-35 runtime coverage and physical matrix', 'Resources/fonts/custom themes',
                              'External immutable FieldLog packages', 'Signed authority/release/store/GA']
    except Exception:
        receipt['status'] = 'failed-independent-review-execution'
        receipt['failure'] = traceback.format_exc()
        print(receipt['failure'], flush=True)
    finally:
        receipt['commands'] = runner.commands
        receipt['collector_sha256'] = digest(pathlib.Path(__file__).resolve())
        shutil.copy2(pathlib.Path(__file__).resolve(), out / 'collector.py')
        shutil.rmtree(scratch)
        receipt['cleanup'] = {'owned_scratch_removed': not scratch.exists(),
                              'all_collector_owned_command_groups_absent': all(row['owned_group_absent_on_completion'] for row in runner.commands),
                              'native_capture_or_other_project_processes_started_or_stopped': False}
        save()
        print(json.dumps({'status': receipt['status'], 'vectors_recorded': len(receipt['vectors']),
                          'cleanup': receipt['cleanup']}, sort_keys=True), flush=True)
    return receipt['status'] != 'independent-selected-development-contract-checks-passed'


if __name__ == '__main__':
    raise SystemExit(main())
