#!/usr/bin/env python3
"""Fresh sealed post-build preflight over the accepted closed V3 composition.

CLI verification only. compose() prepares a private harness but never runs it.
Root must separately select native execution after independent review.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PREP = ROOT/'verification/apple-toggle-keyboard-full-case-preparation-v3'
BUILD = ROOT/'verification/apple-toggle-keyboard-full-case-v3-build'
BUILD_ACCEPTANCE = ROOT/'verification/apple-toggle-keyboard-full-case-root-review/v3-build/acceptance.json'
BUILD_SEAL = 'bb6cc751b0f742367157fa21d4c861718ff9c68416074c8e0b4c37dc79908527'
BUILD_ACCEPTANCE_HASH = '8242b94cee2ad8bd96c48b124ccfe24465f347d7f8bd72e8ab3a594155bb5a74'
BUILD_MANIFEST_HASH = '892c38788433f2574d87d9b30abe19178feb15cb13ac5b0a5a015fd2f8910e0b'
RUNTIME_SELECTION_HASH = '6b99ac953a556e705d488f1c350abcd510dfee639447186538dfb21a32124fad'
RUNNER_TREE = '80ae16baf64547a477e981dc73f31cf8baec1c1d5e0aa8cbde3346ef2dcddde5'
RUNNER_ARCHIVE = '1064c8082add39b2dbaa5e0757c95673f8c54064a3e43adea49f3416fe3b2b1b'
ARCHIVE = BUILD/'supplement/test-runner-products.tar.gz'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff', 'test020EnabledFromOn',
           'test030StaleFromOff', 'test040StaleFromOn', 'test050DisabledFromOff', 'test060DisabledFromOn']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def pinned(path, expected):
    require(path.is_file() and not path.is_symlink() and path.resolve() == path and sha(path) == expected,
            'Pinned adapter input changed: '+str(path))


def build_helper():
    """Load definitions from accepted bytes; never execute its compile entrypoint."""
    pinned(BUILD/'packet-seal.json', BUILD_SEAL)
    seal = read(BUILD/'packet-seal.json')
    name = str((BUILD/'build_runner.py').relative_to(ROOT))
    pinned(ROOT/name, seal['files'][name]['sha256'])
    require('_mixer_v3_postbuild_helper' not in sys.modules, 'Outside helper preload refused')
    spec = importlib.util.spec_from_file_location('_mixer_v3_postbuild_helper', ROOT/name)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def records(helper, entries):
    """The same real byte/mode validator is used by preflight and host controls."""
    for name, expected in entries.items():
        path = pathlib.Path(name) if name.startswith('/') else ROOT/name
        require(helper.file_record(path) == expected, 'Bound bytes/mode changed: '+name)


def verify(unsealed_host_check=False):
    b = build_helper()
    seal_path = BASE/'packet-seal.json'
    if seal_path.exists():
        own = read(seal_path)
        require(own['schema'] == 'mixer.apple-toggle.keyboard-full-case-v3-adapter.1', 'Wrong adapter seal')
        records(b, own['files'])
        seal_hash = sha(seal_path)
    else:
        require(unsealed_host_check is True, 'Sealed adapter required')
        selection = read(BASE/'adapter-runtime-selection.json')
        for name, expected in selection['files'].items():
            pinned(BASE/name, expected)
        seal_hash = None
    pinned(BUILD_ACCEPTANCE, BUILD_ACCEPTANCE_HASH)
    accepted = read(BUILD_ACCEPTANCE)
    require(accepted['sealSHA256'] == BUILD_SEAL and accepted['compilerExitCode'] == 0 and accepted['compilerAttempts'] == 1,
            'Exact one-attempt build acceptance required')
    require(accepted['productTreeSHA256'] == RUNNER_TREE and accepted['productArchiveSHA256'] == RUNNER_ARCHIVE,
            'Root accepted different runner products')
    records(b, read(BUILD/'packet-seal.json')['files'])
    source = b.revalidate()
    require(source == read(BUILD/'source-before.json'), 'Accepted source tree changed')
    pinned(PREP/'runtime-selection.json', RUNTIME_SELECTION_HASH)
    runtime = read(PREP/'runtime-selection.json')
    require(sum(name.endswith('.py') for name in runtime['files']) == 22 and sum(name.endswith('.json') for name in runtime['files']) == 3,
            'Closed V3 source/data selection differs')
    pinned(BUILD/'supplement/build-products-manifest.json', BUILD_MANIFEST_HASH)
    manifest = read(BUILD/'supplement/build-products-manifest.json')
    require(b.digest(manifest['products']) == RUNNER_TREE and b.tree(b.PRODUCTS) == manifest['products'], 'Fresh compiled runner products changed')
    pinned(ARCHIVE, RUNNER_ARCHIVE)
    b.verify_archive(ARCHIVE, manifest['products'])
    require(b.tool_metadata() == read(BUILD/'supplement/tools-verified.json'), 'Accepted compiler/tool/SDK bindings changed')
    # Bind the actual V9 app source closure and both unchanged archive identities.
    v9 = ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation'
    lock = read(v9/'source-lock.json')
    actual = {str(path.relative_to(v9/'source')):sha(path) for path in sorted((v9/'source').rglob('*')) if path.is_file() and not path.is_symlink()}
    require(actual == lock['sha256'] and b.digest(actual) == 'f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46', 'Selected V9 app source closure changed')
    apps = {}
    for key, folder, expected in [('diagnostic', v9, 'b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'),
             ('comparator', ROOT/'verification/apple-toggle-native-failure-analysis/sdk26-comparator', '1c55dab124608b019ab4a1b6e0a9a2355e5f72287602b890a0a3f78aa6b30fa9')]:
        app = read(folder/'built-app-manifest.json')
        pinned(folder/'built-app.tar.gz', expected)
        require(app['archiveSHA256'] == expected, 'Selected app manifest/archive differs')
        apps[key] = expected
    runtime_path = PREP/'runtime'
    require(runtime_path.resolve() == runtime_path and not os.path.lexists(runtime_path), 'Fresh fixed V3 runtime path required')
    return dict(schema='mixer.apple-toggle.keyboard-full-case-v3-postbuild-preflight.1',
        sealSHA256=seal_hash, status='sealed-adapter-preflight' if seal_hash else 'unsealed-host-check-no-native-authority',
        sourceSealSHA256=b.PINS['producer'], reviewSealSHA256=b.PINS['review'], buildSealSHA256=BUILD_SEAL,
        buildAcceptanceSHA256=BUILD_ACCEPTANCE_HASH, runtimeSelectionSHA256=RUNTIME_SELECTION_HASH,
        testRunnerProductTreeSHA256=RUNNER_TREE, productArchiveSHA256=RUNNER_ARCHIVE,
        expectedXCTestMethods=METHODS, appArchives=apps, physicalPhones='disconnected-deferred',
        applicationCasesExecuted=0, nativeInstancesQueried=False, nativeExecution=False,
        nativeAcceptancePending=True, carrierAccepted=False, gaAccepted=False)


class FreshPreflight:
    """Preserve the first failure object; a failed prepared instance never retries."""
    def __init__(self):
        self.first = None

    def __call__(self):
        if self.first is not None:
            raise self.first
        try:
            return verify()
        except BaseException as error:
            self.first = error
            raise


def compose():
    verify()
    # The accepted composition validates every selected transitive import and
    # case-data origin before constructing its private harness.
    path = PREP/'composition.py'
    pinned(path, read(PREP/'runtime-selection.json')['files']['composition.py'])
    spec = importlib.util.spec_from_file_location('_mixer_v3_postbuild_composition', path)
    composition = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(composition)
    h = composition.compose()
    composition.bindings.check(composition.RUNTIME_ROOTS+[composition])
    require(h.SCOPES['interaction']['methods'] == METHODS and set(h.SCOPES) == {'interaction'}, 'Exact seven-method closed scope required')
    require(h.BASE == PREP and h.PRODUCTS == PREP/'build/Build/Products', 'Fixed accepted runtime/product paths required')
    h.PRODUCT_ARCHIVE = ARCHIVE
    h.verify = FreshPreflight()
    return h


if __name__ == '__main__':
    require(sys.argv[1:] == ['verify'], 'Only read-only verify is exposed; root selects native execution separately')
    print(json.dumps(verify(), sort_keys=True))
