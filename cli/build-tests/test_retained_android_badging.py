"""Run bounded retained APK identity controls with Android Build Tools 37.0.0."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import zipfile


APPLICATION = 'dev.mixer.managedstarter'
ACTIVITY = 'dev.mixer.android.MixerActivity'
EXPECTED = dict(application=APPLICATION, activity=ACTIVITY, abi='arm64-v8a', min_api=28, target_api=37)
AAPT2_SHA256 = '13a206c0b022ba3b92f21b6f142f3a4b2d0f3bb1ac0bddfa820ee2c6b00c4c99'
DRIVER = Path(__file__).resolve().parents[1] / 'Sources/MixerBuild/Resources/android-build.py'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def refuses(operation, diagnostic):
    try:
        operation()
    except RuntimeError as error:
        require(diagnostic in str(error), str(error))
        return
    raise RuntimeError('Unexpected acceptance: ' + diagnostic)


def exercise(sdk, before_driver):
    aapt2 = sdk / 'build-tools/37.0.0/aapt2'
    require(hashlib.sha256(aapt2.read_bytes()).hexdigest() == AAPT2_SHA256, 'Expected the recorded macOS aapt2 binary')
    jar = sdk / 'platforms/android-37.0/android.jar'
    driver = runpy.run_path(str(DRIVER))
    parse = driver['retained_apk_identity']
    sdk_floor = driver['application_min_api']
    if before_driver is not None:
        original = ast.parse(before_driver.read_text())
        build = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == 'build')
        old_predicate = next(node.test for node in build.body
                             if isinstance(node, ast.If) and 'APK identity, native activity or ABI' in ast.unparse(node))
        old_refuses = compile(ast.Expression(old_predicate), str(before_driver), 'eval')

    with tempfile.TemporaryDirectory(prefix='retained-apk-badging-') as scratch:
        root = Path(scratch)
        manifest = root / 'Platforms/Android/AndroidManifest.xml'
        manifest.parent.mkdir(parents=True)

        def package(case, *, name=APPLICATION, activity=ACTIVITY, floor=28, target=37,
                    abis=('arm64-v8a',), launcher=True):
            target_attribute = f' android:targetSdkVersion="{target}"' if target is not None else ''
            intent = ('<intent-filter><action android:name="android.intent.action.MAIN"/>'
                      '<category android:name="android.intent.category.LAUNCHER"/></intent-filter>' if launcher else '')
            manifest.write_text(f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
                package="{name}" android:versionCode="1">
                <uses-sdk android:minSdkVersion="{floor}"{target_attribute}/>
                <application android:label="{ACTIVITY}">
                  <activity android:name="{activity}" android:exported="true">{intent}</activity>
                </application>
                </manifest>
            ''')
            apk = root / (case + '.apk')
            subprocess.run([aapt2, 'link', '-I', jar, '--manifest', manifest, '--min-sdk-version', str(floor),
                            '--target-sdk-version', '37', '-o', apk], check=True, timeout=15)
            # Badging uses the zip path for ABI discovery. The real Starter control inspects the ELF files.
            with zipfile.ZipFile(apk, 'a') as archive:
                for abi in abis:
                    archive.writestr(f'lib/{abi}/libcontrol.so', b'')
            return subprocess.check_output([aapt2, 'dump', 'badging', apk], text=True, timeout=15)

        cases = {
            'decoy_label': (dict(activity='.OtherActivity'), 'activity differs'),
            'missing_launcher': (dict(launcher=False), 'launchable-activity'),
            'incorrect_package': (dict(name='dev.mixer.other'), 'application differs'),
            'incorrect_abi': (dict(abis=('x86_64',)), 'abi differs'),
            'extra_abi': (dict(abis=('arm64-v8a', 'x86_64')), 'native-code'),
            'incorrect_minimum': (dict(floor=29), 'minAPI differs'),
            'incorrect_target': (dict(target=32), 'targetAPI differs'),
        }
        fields = ('package: ', 'launchable-activity: ', 'native-code: ', 'minSdkVersion:', 'targetSdkVersion:')
        receipts = {}
        for case, (options, diagnostic) in cases.items():
            badging = package(case, **options)
            refuses(lambda: parse(badging, **EXPECTED), diagnostic)
            receipts[case] = [line for line in badging.splitlines() if line.startswith(fields)]
            if before_driver is not None and case in ('decoy_label', 'incorrect_target'):
                require(not eval(old_refuses, {'badging': badging, 'activity': ACTIVITY,
                                              'config': {'application': APPLICATION}}), 'Old predicate unexpectedly refused')
            if case == 'incorrect_target':
                require("targetSdkVersion:'32'" in receipts[case], 'Pinned linker did not reproduce target 32')
                require(sdk_floor(root, {}) == 28, 'Ordinary manifest floor changed')
                refuses(lambda: sdk_floor(root, {}, required_target_api=37), 'android.target-api')

        package('implicit_target', target=None)
        require(sdk_floor(root, {}) == 28, 'Ordinary manifest floor changed')
        refuses(lambda: sdk_floor(root, {}, required_target_api=37), 'android.target-api')
        legacy = parse(package('legacy'), **EXPECTED)
        require(sdk_floor(root, {}, required_target_api=37) == 28, 'Explicit legacy manifest floor changed')
        public_activity = APPLICATION + '.androidhost.PublicActivity'
        public = parse(package('public', floor=36, activity=public_activity),
                       **(EXPECTED | {'activity': public_activity, 'min_api': 36}))
        require(sdk_floor(root, {'androidHost': 'public-v4'}, required_target_api=37) == 36,
                'Explicit public manifest floor changed')
        return {'refusals': receipts, 'accepted': [legacy, public], 'oldPredicateAcceptedDecoys': before_driver is not None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sdk', type=Path)
    parser.add_argument('--before-driver', type=Path)
    print(json.dumps(exercise(**vars(parser.parse_args())), sort_keys=True))
