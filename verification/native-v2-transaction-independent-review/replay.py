#!/usr/bin/env python3
"""UNEXECUTED prospective native replay draft; this is not acceptance evidence.

Native work was paused before a final Apple qualification existed. Required
assertions and paint checks must be reconciled with the eventual frozen source
before this draft can issue a useful receipt. Current accepted review evidence
uses seal-jni-cli-source-review.py and replay-android-headless.py instead.
This script never runs/discovers native targets.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import traceback
import zipfile

from PIL import Image, __version__ as pillow_version

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
APPLE = ROOT / 'verification/apple-native-appearance-v2'
ANDROID = ROOT / 'verification/android-native-appearance-v2'
KINDS = {'text', 'button', 'textField', 'toggle', 'vStack', 'hStack', 'zStack', 'list', 'section', 'navigation'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_path(base, name):
    path = (base / name).resolve()
    assert path.is_relative_to(base.resolve()), ('path escapes receipt', name)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apple', required=True)
    parser.add_argument('--android', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    for value in [args.apple, args.android, args.output]:
        assert re.fullmatch(r'candidate-[0-9]+', value), ('bounded candidate name required', value)
    out = BASE / args.output
    out.mkdir()
    reads = {}
    checks = []
    supporting_drift = []
    summary = {}

    def read(path):
        data = path.read_bytes()
        reads[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = digest(data)
        return data

    def obj(path):
        return json.loads(read(path))

    def check(condition, name):
        assert condition, name
        checks.append(name)

    def sources(directory, manifest):
        for name, expected in manifest.items():
            check(digest(read(checked_path(directory / 'inputs', name))) == expected, 'captured-source:' + name)
            actual = digest(read(checked_path(ROOT, name)))
            if actual != expected and name == 'AGENTS.md':
                supporting_drift.append(dict(path=name, capturedSHA256=expected, currentSHA256=actual))
            else:
                check(actual == expected, 'live-source:' + name)

    def read_image(path):
        import io
        image = Image.open(io.BytesIO(read(path))).convert('RGB')
        check(image.width > 0 and image.height > 0, 'decoded-image:' + path.name)
        return image

    def native_artifact_members(archive):
        read(archive)
        result = {}
        with tarfile.open(archive, 'r:*') as package:
            for member in package.getmembers():
                if member.isfile():
                    result[member.name] = package.extractfile(member).read()
        return result

    try:
        # Git inspection is read-only. All executable native/compile logs below are retained evidence.
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
        audit_manifest = obj(BASE / 'audit-inputs/manifest.json')
        for name, metadata in audit_manifest['inputs'].items():
            data = read(checked_path(BASE / 'audit-inputs', name))
            check(len(data) == metadata['bytes'] and digest(data) == metadata['sha256'], 'historical-review-input:' + name)
        apple = APPLE / args.apple
        android = ANDROID / args.android
        a_lock = obj(apple / 'source-lock.json')
        sources(apple, a_lock['sha256'])
        a_observed = obj(apple / 'observations.json')
        a_result = obj(apple / 'result.json')
        check(a_observed['checks'] and all(item['pass'] for item in a_observed['checks']), 'apple-native-assertions-pass')
        check(a_result['failed'] == [] and a_result['checkCount'] == len(a_observed['checks']), 'apple-result-count')
        required_apple_checks = {
            'stale-environment-native-hit-blocker', 'stale-environment-native-proposals-denied',
            'stale-environment-native-buffer-and-actions-gated', 'environment-same-native-identities',
            'same-revision-retains-unacknowledged-native-values',
            'new-guest-document-authoritative-even-unchanged-binding',
            'unsupported-recapture-retires-and-gates-existing-owner',
            'row-hit-rejection-has-no-native-attachment', 'hidden-native-control-action-gated',
            'disabled-native-buffer-proposals-denied',
            'native-switch-zero-area-mask-and-public-press-observer',
            'native-switch-explicit-accessibility-value-updates',
            'native-switch-cleared-override-uses-native-checked-value',
            'native-unequal-hstack-bounded-proposals',
            'fixed-control-hstack-proposal-overflow-rejected',
            'hstack-overflow-rejection-no-attachment',
            *['native-accessibility-overrides-on-traversal-leaf-' + str(index) for index in range(5)],
        }
        check(required_apple_checks <= {item['name'] for item in a_observed['checks']}, 'apple-correction-native-assertion-coverage')
        check(a_observed['physicalDeviceTested'] is False and a_observed['realKeyboardIMEQualified'] is False and a_observed['voiceOverQualified'] is False, 'apple-qualification-boundaries-explicit')
        a_commands = obj(apple / 'commands.json')
        for command in a_commands + obj(apple / 'build-commands.json'):
            if 'argv' in command:
                check(command['exitCode'] == 0, 'apple-command:' + ' '.join(map(str, command['argv'][:3])))
        a_built = obj(apple / 'built-app.json')
        archives = [p for p in sorted(apple.glob('*.tar*')) if any('.app/' in m.name for m in tarfile.open(p, 'r:*').getmembers())]
        check(len(archives) == 1, 'one-retained-final-apple-app-archive')
        a_archive_manifest = obj(apple / 'built-app-manifest.json')
        check(archives[0].name == a_archive_manifest['archive'] and digest(read(archives[0])) == a_archive_manifest['sha256'], 'apple-retained-app-archive-seal')
        a_members = native_artifact_members(archives[0])
        a_relative = {key.split('.app/', 1)[1]: value for key, value in a_members.items() if '.app/' in key}
        check(set(a_relative) == set(a_archive_manifest['files']), 'apple-retained-app-complete-file-set')
        for name, metadata in a_archive_manifest['files'].items():
            data = a_relative[name]
            check(digest(data) == metadata['sha256'] and len(data) == metadata['bytes'], 'apple-retained-app-member:' + name)
        expected_native = {'MixerAppearanceV2Harness': a_built['binarySHA256'], **a_built['libraries']}
        for name, expected in expected_native.items():
            matches = [value for key, value in a_members.items() if Path(key).name == name]
            check(len(matches) == 1 and digest(matches[0]) == expected, 'apple-native-artifact:' + name)
        a_descriptor = read(apple / 'descriptor.json')
        descriptors = [value for key, value in a_members.items() if key.endswith('.app/MixerAppearanceV2/descriptor.json')]
        check(len(descriptors) == 1 and descriptors[0] == a_descriptor and digest(a_descriptor) == a_built['descriptorSHA256'], 'apple-retained-app-exact-descriptor')
        a_frames = obj(apple / 'fixture-frames-roles-states.json')
        check({node['kind'] for node in a_frames['nodes']} == KINDS, 'apple-real-all-ten-kinds')
        a_lifecycle = obj(apple / 'simulator-lifecycle.json')
        installed_app = obj(apple / 'installed-app-receipt.json')
        check(installed_app['simulator'] == a_lifecycle['ownedSimulator'] and installed_app['matchesRetainedBuiltApp'] is True, 'apple-distinct-installed-app-simulator-identity')
        installed_expected = {'MixerAppearanceV2Harness': a_built['binarySHA256'], **{'Frameworks/' + name: value for name, value in a_built['libraries'].items()}}
        check(installed_app['hashes'] == installed_expected, 'apple-installed-executable-and-three-libraries-equal-retained-app')
        check('/Devices/' + a_lifecycle['ownedSimulator'] + '/' in installed_app['appPath'] and installed_app['appPath'].endswith('/MixerAppearanceV2.app'), 'apple-installed-app-path-matches-owned-simulator')
        for command in installed_app['commands']:
            check(command['exitCode'] == 0, 'apple-installed-inspection-command:' + ' '.join(command['argv'][:3]))
        container_commands = [item for item in installed_app['commands'] if item['argv'][:3] == ['xcrun', 'simctl', 'get_app_container']]
        check(len(container_commands) == 1 and container_commands[0]['argv'][3] == a_lifecycle['ownedSimulator'] and container_commands[0]['argv'][-1] == 'app' and container_commands[0]['stdout'].strip() == installed_app['appPath'], 'apple-installed-container-inspection-binds-exact-app')
        build_inspections = [item for item in installed_app['commands'] if item['argv'][:3] == ['xcrun', 'vtool', '-show-build']]
        check(len(build_inspections) == 1 and build_inspections[0]['argv'][-1] == installed_app['appPath'] + '/MixerAppearanceV2Harness' and 'platform IOSSIMULATOR' in build_inspections[0]['stdout'] and 'minos 17.0' in build_inspections[0]['stdout'], 'apple-installed-native-binary-platform-and-minimum')
        signature_inspections = [item for item in installed_app['commands'] if item['argv'][:3] == ['xcrun', 'codesign', '--verify']]
        check(len(signature_inspections) == 1 and signature_inspections[0]['argv'][-1] == installed_app['appPath'] and '--deep' in signature_inspections[0]['argv'] and '--strict' in signature_inspections[0]['argv'], 'apple-installed-local-adhoc-signature-inspection-recorded')
        if a_lifecycle.get('cleanedUp') is True:
            final_inventory = a_lifecycle['after']
        else:
            cleanup = obj(APPLE / 'owned-simulator-cleanup.json')
            check(cleanup['allOwnedSimulatorsRetired'] is True, 'apple-owned-simulator-retired-after-retained-gui-session')
            for operation in ['shutdown', 'delete']:
                matching = [item for item in cleanup['commands'] if item['argv'][-2:] == [operation, a_lifecycle['ownedSimulator']]]
                check(len(matching) == 1 and matching[0]['exitCode'] == 0, 'apple-final-owned-simulator-' + operation)
            final_inventory = cleanup['finalSimulatorInventory']
        after_ids = {device['udid'] for devices in final_inventory['devices'].values() for device in devices}
        check(a_lifecycle['ownedSimulator'] not in after_ids, 'apple-owned-simulator-absent-from-retained-final-inventory')

        # Replay retained compositor samples independently of producer verify.py.
        stages = {item['stage']: item['after'] for item in a_observed['observations']}
        a_nodes = {item['id']: item for item in a_frames['nodes']}
        scale = a_frames['density1024'] / 1024

        def apple_pixel(stage, x, y):
            return list(read_image(apple / (stage + '.png')).getpixel((round(x * scale), round(y * scale))))

        def apple_toggle(stage, enabled):
            node = a_nodes['toggle']
            frame, visual = node['windowFrame64'], node['visual64']
            return apple_pixel(stage, (frame[0] + visual[0]) / 64 + (10 if enabled else 53), (frame[1] + visual[1]) / 64 + 14)

        samples = dict(toggleEnabledOn=apple_toggle('initial', True), toggleNativeInputOff=apple_toggle('toggle-input', False), toggleDisabledOff=apple_toggle('disabled', False))
        check(samples['toggleEnabledOn'] == [52, 199, 89] and samples['toggleNativeInputOff'] == [197, 197, 199] and samples['toggleDisabledOff'] == [229, 229, 231], 'apple-authored-native-toggle-pixels')
        blink = []
        for stage in ['blink-a', 'blink-b', 'blink-c', 'blink-d']:
            rect = stages[stage]['nodes']['field']['cursorRectInWindow']
            blink.append(apple_pixel(stage, rect[0] + rect[2] / 2, rect[1] + rect[3] / 2))
        check([0, 136, 255] in blink and [255, 255, 255] in blink, 'apple-compositor-cursor-blink-visible-and-hidden')
        summary['apple'] = dict(candidate=args.apple, checkCount=len(a_observed['checks']), runtime=a_observed['runtime'], sourceRevision=a_lock['revision'], sourceTree=a_lock['tree'], inputCount=len(a_lock['sha256']), nativeArtifactSHA256=expected_native, installedSimulator=installed_app['simulator'], installedNativeArtifactHashes=installed_app['hashes'], pixelSamples=samples, cursorBlinkSamples=blink)

        d_receipt = obj(android / 'receipt.json')
        sources(android, d_receipt['sourceManifest'])
        check(d_receipt['status'] == 'passed-compile-and-native-emulator' and d_receipt['sourceUnchanged'] is True and d_receipt['error'] is None, 'android-native-candidate-passed-source-stable')
        closure = digest(json.dumps(d_receipt['sourceManifest'], sort_keys=True, separators=(',', ':')).encode())
        check(closure == d_receipt['sourceClosureSHA256'], 'android-source-closure-digest')
        for name, expected in obj(android / 'artifact-seal.json').items():
            check(digest(read(checked_path(android, name))) == expected, 'android-evidence-seal:' + name)
        for command in d_receipt['commands']:
            check(command['exitCode'] == 0, 'android-command:' + command['name'])
            check(digest(read(checked_path(ROOT, command['output']))) == command['sha256'], 'android-command-output:' + command['name'])
        for name, expected in d_receipt['artifacts'].items():
            check(digest(read(checked_path(ANDROID, name))) == expected, 'android-retained-native-artifact:' + name)
        for name, expected in d_receipt['toolSHA256'].items():
            check(digest(read(Path(name))) == expected, 'android-tool:' + name)
        native_log = read(android / 'native-instrumentation.log').decode()
        check('INSTRUMENTATION_RESULT: status=passed' in native_log and 'INSTRUMENTATION_CODE: 0' in native_log, 'android-native-instrumentation-passed')
        count = re.search(r'INSTRUMENTATION_RESULT: checks=(\d+)', native_log)
        check(count is not None and int(count[1]) == d_receipt['native']['checks'], 'android-native-assertion-count')
        inset_log = read(android / 'button-insets-native.log').decode()
        inset_count = re.search(r'INSTRUMENTATION_RESULT: checks=(\d+)', inset_log)
        check('INSTRUMENTATION_RESULT: status=passed' in inset_log and 'INSTRUMENTATION_CODE: 0' in inset_log and inset_count is not None, 'android-packaged-positive-inset-native-assertions')
        negative_commands = [item for item in d_receipt['commands'] if item['name'].endswith('-native-capture')]
        check(len(negative_commands) == 5, 'android-five-packaged-negative-capture-cases')
        for command in negative_commands:
            value = read(checked_path(ROOT, command['output'])).decode()
            check('INSTRUMENTATION_RESULT: status=passed' in value and 'INSTRUMENTATION_CODE: 0' in value, 'android-packaged-negative:' + command['name'])
        target = d_receipt['target']
        check(target['ro.kernel.qemu'] == '1' and target['ro.build.version.sdk'] == '37', 'android-retained-api37-emulator-identity')
        apk_path = ANDROID / 'build' / args.android / 'test.apk'
        apk_bytes = read(apk_path)
        check(digest(apk_bytes) == target['installedAPK_SHA256'], 'android-retained-apk-equals-installed-hash')
        with zipfile.ZipFile(apk_path) as apk:
            check(apk.read('assets/MixerAppearanceV2/descriptor.json') == a_descriptor, 'native-apps-exact-same-canonical-authored-descriptor')
            paired = apk.read('assets/NativeAppearanceV2/paired-packet.bin')
            check(paired == read(apple / 'fixture-native-packet.bin') == read(ANDROID / args.android / 'paired-packet.bin') == read(APPLE / 'shared-fixture/native-packet-v1.bin'), 'native-apps-exact-same-swift-authored-packet')
            for name in apk.namelist():
                if re.fullmatch(r'classes\d*\.dex', name):
                    check(apk.read(name) == read(ANDROID / 'build' / args.android / 'dex' / name), 'android-packaged-native-dex:' + name)
        paired_map = obj(android / 'paired-map.json')
        check({node['kind'] for node in paired_map['nodes']} == KINDS, 'android-shared-packet-real-all-ten-kinds')
        check({(node['id'], str(node['generation'])) for node in paired_map['nodes']} == {(node['id'], str(node['generation'])) for node in a_frames['nodes']}, 'native-shared-fixture-exact-identities')
        check(paired_map['descriptorSHA256'] == a_built['descriptorSHA256'], 'native-shared-map-descriptor-digest')
        preferences = obj(android / 'preference-corpus.json')
        check({value['profile'] for value in preferences['profiles']} == {'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl', 'a1', 'a2', 'a3', 'a4', 'a5'}, 'android-twelve-native-configuration-contexts')
        d_pixels = {name: list(read_image(android / name).size) for name in ['paired-compositor.png', 'all-ten-compositor.png', 'disabled-software.png']}
        hardware_analysis = {}
        for scene in ['all-ten', 'paired', 'inset']:
            capture = obj(android / (scene + '-capture.json'))
            scene_map = obj(android / (scene + '-map.json'))
            environment = scene_map['environment']
            density = environment['density1024']
            px = lambda value: int(value * density / 65536 + .5)
            safe_top, safe_bottom = px(environment['safeTop64']), px(environment['safeBottom64'])
            images = {kind: read_image(android / (scene + '-' + kind + '.png')) for kind in ['software', 'hardware', 'compositor']}
            expected_size = (px(environment['viewportWidth64']), px(environment['viewportHeight64']))
            check(all(value.size == expected_size for value in images.values()), 'android-capture-same-native-viewport:' + scene)
            root_node = scene_map['nodes'][0]
            # This exact Activity has zero image/root origin; infer and record it
            # from actual native root frame minus its independently captured safe edge.
            root_origin = [root_node['pixels']['left'] - px(root_node['logical64']['x']), root_node['pixels']['top'] - px(root_node['logical64']['y'])]
            check(root_origin == [0, 0], 'android-native-map-zero-root-image-origin:' + scene)
            pixels = {kind: value.load() for kind, value in images.items()}

            def ink(value):
                return max(value) < 128 or max(value) - min(value) > 64

            ratios = {}
            for kind in ['hardware', 'compositor']:
                union = common = 0
                for y in range(safe_top, expected_size[1] - safe_bottom, 2):
                    for x in range(0, expected_size[0], 2):
                        a, b = ink(pixels['software'][x, y]), ink(pixels[kind][x, y])
                        union += a or b
                        common += a and b
                ratios[kind] = common / union if union else 0
                check(ratios[kind] >= .75, 'android-independent-content-ink-correspondence:' + scene + ':' + kind)
            matching = [item for item in capture['attempts'] if item.get('current') is True and item.get('windowInkIntersectionOverUnion', 0) >= .75 and item.get('compositorInkIntersectionOverUnion', 0) >= .75]
            check(bool(matching) and abs(matching[-1]['windowInkIntersectionOverUnion'] - ratios['hardware']) < .005 and abs(matching[-1]['compositorInkIntersectionOverUnion'] - ratios['compositor']) < .005, 'android-native-capture-ratios-reproduced-offline:' + scene)
            hardware_analysis[scene] = dict(viewport=list(expected_size), safeTopPx=safe_top, safeBottomPx=safe_bottom, inferredRootImageOrigin=root_origin, independentInkIntersectionOverUnion=ratios, scope='Structural same-Activity software/PixelCopy/compositor content correspondence; zero image origin inferred from retained actual native root frame and safe edge; no cross-platform pixel parity claim')
        cleanup = obj(ANDROID / 'emulator-cleanup.json')
        check(cleanup['status'] == 'stopped' and cleanup['serial'] == target['serial'], 'android-owned-emulator-cleanup-identity')
        cleanup_commands = {item['name']: item for item in cleanup['commands']}
        check(cleanup_commands['stop-owned-emulator']['exitCode'] == 0 and cleanup_commands['owned-process-after']['exitCode'] != 0 and cleanup_commands['owned-console-port-after']['exitCode'] != 0, 'android-owned-emulator-stopped-and-port-absent')
        summary['android'] = dict(candidate=args.android, checkCount=d_receipt['native']['checks'], positiveInsetCheckCount=int(inset_count[1]), packagedNegativeCaseCount=len(negative_commands), target=target, sourceRevision=d_receipt['sourceRevision'], sourceTree=d_receipt['sourceTree'], sourceClosureSHA256=closure, retainedArtifactCount=len(d_receipt['artifacts']), compositorImageSizes=d_pixels, hardwareContentReplay=hardware_analysis)
        summary.update(status='passed', currentSourceRevision=revision, currentSourceTree=tree)
    except Exception as failure:
        summary.update(status='failed', error=str(failure), traceback=traceback.format_exc())
    finally:
        read(Path(__file__))
        summary.update(observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), command=[sys.executable, *sys.argv], python=sys.version, pythonExecutable=sys.executable, platform=platform.platform(), pillow=pillow_version, checks=checks, checkCount=len(checks), supportingLivePolicyDrift=supporting_drift, scope='Independent read-only offline replay of source-bound producer assertions/native artifacts/compositor evidence; no new native execution, target discovery, physical phone, ordinary engine/JNI/bootstrap, signed release, full runtime, FieldLog or GA qualification.')
        (out / 'input-sha256.json').write_text(json.dumps(reads, indent=2, sort_keys=True) + '\n')
        (out / 'receipt.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        print(json.dumps({key: summary.get(key) for key in ['status', 'error', 'checkCount', 'apple', 'android']}, indent=2))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
