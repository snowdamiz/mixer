#!/usr/bin/env python3
"""Admit the reviewed native-report archive owner and reconstruct its predecessor."""

import argparse
import hashlib
import importlib.util
import json
import stat
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = Path('verification/sdk-feature-ui-source141-v1')
PREVIOUS_SEAL_SHA256 = '06952f22a0a4fc6b2272e7f545abb9e46ec526372abf5e2244c6599e3a6246ed'
TYPE = 'EXACT_NATIVE_REPORT_ARCHIVE_SOURCE141_SUCCESSOR'
CLOSEOUT_SOURCE_SHA256 = '7e04cab7419cf65db0a8ad70a97f6ea94b1cb6db882f6c7ec724e24d170a2b28'
PAIR23_SOURCE_SHA256 = 'f68f02c92c93947becf9e29b7eeef43b88313f13e7f7c915fdf47f902f4f81cd'
STARTER_LOCK_SOURCE_SHA256 = '2da47ad99b33e45367cffce65d20b76d06e33a25eaab2bb4c421fef95d0849cf'
EXPORT_RUNNER = 'scripts/ci/check-android-generated-java.py'
RENDERER = 'app/src/dev/mixer/android/NativeAppearanceViewsV2.java'
CLOSEOUT_SOURCE_CHANGES = frozenset((
    'cli/Sources/MixerBuild/BuildInputSnapshot.swift',
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/NativeProductCapture.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'updates/Sources/MixerUpdates/VerifierV3.swift',
    'updates/Sources/MixerUpdateTool/main.swift',
))
RENDERER_SOURCE_CHANGES = {
    'native/android/' + RENDERER,
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    EXPORT_RUNNER,
}
SOURCE_CHANGES = CLOSEOUT_SOURCE_CHANGES | RENDERER_SOURCE_CHANGES
ADDITIONS = {
    'cli/build-tests/test_public_export.py',
    'native/android/tests/CollapsedEditorFrameHostTests.java',
    'updates/verification/verify-cli.py',
}
JAVA = 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/'
CHANGES = SOURCE_CHANGES | ADDITIONS | {
    'cli/Tests/MixerBuildTests/BuildTests.swift',
    'cli/Tests/MixerBuildTests/NativeOutputAdmissionTests.swift',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/Tests/MixerBuildTests/GeneratedPublicAndroidV4Tests.swift',
    'cli/build-tests/current_android_profile.py',
    'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/view/View.java',
    'native/android/tests/private-owner-barrier-bindings.json',
    'native/android/tests/private-owner-barrier-map.json',
    'native/android/tests/run-public-surface-host.py',
    '.github/workflows/verify.yml',
    'updates/README.md',
    JAVA + 'bootstrap.py',
    JAVA + 'test_bootstrap.py',
    JAVA + 'test_sparse_checkout.py',
}
STARTER_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
}
STARTER_CHANGES = STARTER_SOURCE_CHANGES | {'cli/build-tests/test_public_export.py'}
CAPABILITY_PREDECESSOR_REVISION = 'b4a54df61e8ecb74f9fb9119a41726ac9d7aea0b'
CAPABILITY_PREDECESSOR_SHA256 = 'dde3c72a99e5c2a4821a8ae51b6f77632c0da08a268f556662439c57dfadfbc0'
CAPABILITY = 'capability-activation/Sources/MixerCapabilityActivation/'
CAPABILITY_ADDITIONS = {CAPABILITY + name for name in (
    'CapabilityColdStartPresentation.swift',
    'CapabilityGuestUIAndroidRuntime.swift',
)}
CAPABILITY_CHANGES = CAPABILITY_ADDITIONS | {CAPABILITY + name for name in (
    'CapabilityColdStartControl.swift',
    'CapabilityColdStartRuntime.swift',
    'CapabilityColdStartWorker.swift',
    'CapabilityGuestUIAndroidLifetime.swift',
    'CapabilityGuestUIAndroidResources.swift',
    'CapabilityGuestUIPresentationLifetime.swift',
)} | {'.github/workflows/verify.yml', JAVA + 'test_sparse_checkout.py'}
UPGRADE_PREDECESSOR_SHA256 = "e007c191d056317ec26a66da61c7d302d1de094f0efd9d2a374fa0faed890327"
UPGRADE_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerCLI/main.swift',
}
UPGRADE_CHANGES = UPGRADE_SOURCE_CHANGES | {'cli/build-tests/test_public_export.py'}
PAIR24_PREDECESSOR_REVISION = '02002272c334dd0a3750c502ad5819b26d57fe0d'
PAIR24_PREDECESSOR_SHA256 = 'd538efdbfc542f860b154f11cc1a50e0b1b01e29dfe03a5057671db9bf4eb557'
STARTER_ACTIVITY = 'app/src/dev/mixer/android/MixerActivity.java'
PAIR24_SOURCE_CHANGES = {
    'native/android/' + STARTER_ACTIVITY,
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    EXPORT_RUNNER,
}
ACTIVITY_TESTS = 'native/android/tests/'
PAIR24_ADDITIONS = {
    ACTIVITY_TESTS + 'MixerActivityHostTests.java',
    ACTIVITY_TESTS + 'run-mixer-activity-host.py',
} | {ACTIVITY_TESTS + 'MixerActivityHostLeaves/' + leaf for leaf in (
    'android/app/Activity.java',
    'android/os/Build.java',
    'android/os/Bundle.java',
    'android/util/Log.java',
    'android/view/View.java',
    'android/view/Window.java',
    'android/view/WindowInsets.java',
    'android/view/WindowInsetsController.java',
    'android/widget/FrameLayout.java',
    'android/widget/Toast.java',
    'dev/mixer/android/NativeBridge.java',
    'dev/mixer/android/NativeRenderer.java',
    'dev/mixer/android/UiPacket.java',
)}
PAIR24_CHANGES = PAIR24_SOURCE_CHANGES | PAIR24_ADDITIONS | {
    '.github/workflows/verify.yml',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/Tests/MixerBuildTests/GeneratedPublicAndroidV4Tests.swift',
    JAVA + 'bootstrap.py',
    JAVA + 'test_bootstrap.py',
    JAVA + 'test_sparse_checkout.py',
}
CANCEL_CLI_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/OwnedCommand.swift',
    'cli/Sources/MixerBuild/POSIXCommandControl.swift',
    'cli/Sources/MixerCLI/main.swift',
    'cli/Sources/MixerProcessIO/include/MixerProcessIO.h',
    'cli/Sources/MixerProcessIO/process.c',
}
CANCEL_CLI_CHANGES = CANCEL_CLI_SOURCE_CHANGES | {
    'cli/Tests/MixerBuildTests/AndroidInspectionPolicyReceiptTests.swift',
    'cli/Tests/MixerBuildTests/OwnedCommandControlTests.swift',
}
HYDRATION_SOURCE_CHANGES = {
    'scripts/ci/check-android-binding.py',
    'sdk/Sources/MixerCapabilities/InstalledCapabilityAdapters.swift',
    'sdk/Sources/MixerGuest/GuestUIExchangeCore.swift',
    'sdk/Sources/MixerGuest/GuestUIExchangeV1.swift',
    'sdk/Sources/MixerGuest/GuestUIProtocolV1.swift',
}
HYDRATION_CHANGES = HYDRATION_SOURCE_CHANGES | {CAPABILITY + 'CapabilityColdStartWorker.swift'}
VERIFY_WORKFLOW = '.github/workflows/verify.yml'
HOSTED_V32_WORKFLOW = 'hosted-v32-predecessor-bytes/' + VERIFY_WORKFLOW
WORKSPACE_BUILDS_WORKFLOW = 'workspace-builds-predecessor-bytes/' + VERIFY_WORKFLOW
CONSOLE_BUILD_LOGS_WORKFLOW = 'console-build-logs-predecessor-bytes/' + VERIFY_WORKFLOW
LOCAL_STORE_PREFIX = 'local-store-predecessor-bytes/'
LOCAL_STORE_ADDITIONS = {
    'cli/Sources/MixerBuild/LocalStoreFixture.swift',
    'cli/Sources/MixerBuild/LocalStoreSubmission.swift',
}
LOCAL_STORE_SOURCE_CHANGES = LOCAL_STORE_ADDITIONS | {
    'cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift',
    'cli/Sources/MixerBuild/PlayReleaseStatus.swift',
    'cli/Sources/MixerBuild/StoreReconciliation.swift',
    'cli/Sources/MixerCLI/main.swift',
}
LOCAL_STORE_CHANGES = LOCAL_STORE_SOURCE_CHANGES | {
    VERIFY_WORKFLOW,
    JAVA + 'bootstrap.py',
    JAVA + 'test_bootstrap.py',
    JAVA + 'test_sparse_checkout.py',
}
PUBLIC_UPDATE_MAIN = 'cli/Sources/MixerCLI/main.swift'
PUBLIC_UPDATE_SOURCE = 'cli/Sources/MixerBuild/LocalUpdateRelease.swift'
PUBLIC_UPDATE_PREIMAGE = 'public-update-predecessor-bytes/' + PUBLIC_UPDATE_MAIN
RUNTIME_NOTICE_WITNESS_PREFIX = 'runtime-notice-witness-predecessor-bytes/'
RUNTIME_NOTICE_WITNESS_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'scripts/ci/check-android-binding.py',
}
RUNTIME_NOTICE_WITNESS_CHANGES = RUNTIME_NOTICE_WITNESS_SOURCE_CHANGES | {
    'THIRD_PARTY.yml',
    CAPABILITY + 'CapabilityGuestUIAndroidResources.swift',
    'native/android/signed-guest-ui/binding/include/mixer_ui_binding.h',
    JAVA + 'test_bootstrap.py',
}
RELEASE_INSPECTOR_PREFIX = 'release-inspector-predecessor-bytes/'
RELEASE_INSPECTOR_ADDITIONS = {
    'cli/Sources/MixerBuild/ReleaseInspection.swift',
    'runtime-identity/Package.resolved',
    'runtime-identity/Package.swift',
    'runtime-identity/Sources/MixerIdentityTool/main.swift',
    'runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift',
    'runtime-identity/Sources/MixerRuntimeIdentity/RuntimeIdentity.swift',
}
RELEASE_INSPECTOR_SOURCE_CHANGES = RELEASE_INSPECTOR_ADDITIONS | {
    'cli/Package.swift',
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/MigrationInspector.swift',
    'cli/Sources/MixerBuild/VerificationFile.swift',
    PUBLIC_UPDATE_MAIN,
    EXPORT_RUNNER,
}
RELEASE_INSPECTOR_CHANGES = RELEASE_INSPECTOR_SOURCE_CHANGES | {
    VERIFY_WORKFLOW,
    JAVA + 'test_sparse_checkout.py',
}
ICU_NOTICE_PREFIX = 'icu-notice-predecessor-bytes/'
ICU_NOTICE_PREDECESSOR_SHA256 = '31af762a2f092df7da8fffa5f367e250f2646c9ac18d4a4e75f1b22a01caa579'
ICU_NOTICE_DRIVER = 'cli/Sources/MixerBuild/Resources/android-build.py'
ICU_NOTICE_TEST = 'cli/build-tests/test_android_runtime_notices.py'
ICU_NOTICE_CHANGES = {
    ICU_NOTICE_DRIVER, ICU_NOTICE_TEST, 'THIRD_PARTY.yml', JAVA + 'test_sparse_checkout.py',
}
MEMBERS = {PUBLIC_UPDATE_PREIMAGE, HOSTED_V32_WORKFLOW, WORKSPACE_BUILDS_WORKFLOW, CONSOLE_BUILD_LOGS_WORKFLOW, 'adopt_archive.py', 'binding.json', 'current-source-inputs.json'} | {
    LOCAL_STORE_PREFIX + name for name in LOCAL_STORE_CHANGES - LOCAL_STORE_ADDITIONS
} | {
    RUNTIME_NOTICE_WITNESS_PREFIX + name for name in RUNTIME_NOTICE_WITNESS_CHANGES
} | {
    RELEASE_INSPECTOR_PREFIX + name
    for name in RELEASE_INSPECTOR_CHANGES - RELEASE_INSPECTOR_ADDITIONS
} | {
    ICU_NOTICE_PREFIX + name for name in ICU_NOTICE_CHANGES
} | {
    'predecessor-bytes/' + name for name in CHANGES - ADDITIONS
} | {
    'pair23-predecessor-bytes/' + name for name in STARTER_CHANGES
} | {
    'capability-predecessor-bytes/' + name for name in CAPABILITY_CHANGES - CAPABILITY_ADDITIONS
} | {
    'upgrade-predecessor-bytes/' + name for name in UPGRADE_CHANGES
} | {
    'pair24-predecessor-bytes/' + name for name in PAIR24_CHANGES - PAIR24_ADDITIONS
} | {
    'cancel-cli-predecessor-bytes/' + name for name in CANCEL_CLI_CHANGES
} | {
    'hydration-predecessor-bytes/' + name for name in HYDRATION_CHANGES
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read_predecessor_member(path):
    limit = 256 * 1024
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_size <= limit,
            'Bounded ordinary Source141 member required: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Source141 admission member exceeds read budget')
    return raw


def load_predecessor():
    base = ROOT / PREVIOUS
    for directory in (base.parent, base):
        require(stat.S_ISDIR(directory.lstat().st_mode),
                'Source141 authority directory required: ' + str(directory))
    raw = read_predecessor_member(base / 'seal.json')
    require(hashlib.sha256(raw).hexdigest() == PREVIOUS_SEAL_SHA256,
            'Source141 predecessor seal differs')
    seal = json.loads(raw)
    entry = base / 'adopt_sdk.py'
    raw = read_predecessor_member(entry)
    require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} ==
            seal['members']['adopt_sdk.py'], 'Source141 predecessor entry differs')
    spec = importlib.util.spec_from_file_location('historical_source141_authority', entry)
    previous = importlib.util.module_from_spec(spec)
    # Execute the exact verified bytes, with the original module path.
    exec(compile(raw, str(entry), 'exec'), previous.__dict__)
    previous.closed_members(base, {*seal['members'], 'seal.json'})
    previous.check_rows(base, seal['members'])
    return previous, seal


def read_capability_preimages(previous, transition, effective):
    require(set(transition) == {'baseRevision', 'changes'} and
            transition['baseRevision'] == CAPABILITY_PREDECESSOR_REVISION and
            set(transition['changes']) == CAPABILITY_CHANGES,
            'Capability archive transition roster differs')
    preimages = {}
    predecessor_rows = {}
    for name, change in transition['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] != change['after'] and
                change['mode'] == 0o644 and
                (change['before'] is None) == (name in CAPABILITY_ADDITIONS),
                'Capability transition row differs: ' + name)
        if name not in CAPABILITY_ADDITIONS:
            raw = previous.read(HERE / 'capability-predecessor-bytes' / name)
            predecessor_rows[name] = previous.row(raw)
            require(predecessor_rows[name] == change['before'] and
                    (name not in effective or effective[name] == change['before']),
                    'Capability predecessor bytes differ: ' + name)
            preimages[name] = raw
    require(previous.digest(predecessor_rows) == CAPABILITY_PREDECESSOR_SHA256,
            'Capability predecessor roster digest differs')
    return preimages


def read_pair24_preimages(previous, transition):
    require(set(transition) == {'baseRevision', 'sourceBefore', 'sourceAfter', 'changes', 'profileAfter'} and
            transition['baseRevision'] == PAIR24_PREDECESSOR_REVISION and
            set(transition['changes']) == PAIR24_CHANGES,
            'Pair24 archive transition roster differs')
    preimages = {}
    for name, change in transition['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] != change['after'] and change['mode'] == 0o644 and
                (change['before'] is None) == (name in PAIR24_ADDITIONS),
                'Pair24 transition row differs: ' + name)
        if name not in PAIR24_ADDITIONS:
            raw = previous.read(HERE / 'pair24-predecessor-bytes' / name)
            require(previous.row(raw) == change['before'], 'Pair24 predecessor bytes differ: ' + name)
            preimages[name] = raw
    return preimages


def install_inputs():
    previous, old_seal = load_predecessor()
    seal = previous.load(HERE / 'seal.json')
    require(set(seal) == {'schema', 'members', 'tree_sha256'} and
            type(seal['schema']) is int and seal['schema'] == 1 and
            set(seal['members']) == MEMBERS and
            previous.digest(seal['members']) == seal['tree_sha256'],
            'Archive authority seal differs')
    previous.closed_members(HERE, {*MEMBERS, 'seal.json'})
    previous.check_rows(HERE, seal['members'])
    binding = previous.load(HERE / 'binding.json')
    require(set(binding) == {'schema', 'type', 'source', 'profile', 'predecessor_binding',
                             'changes', 'renderer_transition', 'starter_lock_transition',
                             'export_runner_transition', 'capability_transition', 'upgrade_transition',
                             'pair24_transition', 'cancel_cli_transition', 'hydration_transition',
                             'hosted_v33_workflow', 'local_store_transition', 'workspace_builds_workflow',
                             'public_update_transition', 'runtime_notice_witness_transition',
                             'release_inspector_transition', 'icu_notice_transition', 'console_build_logs_workflow'} and
            type(binding['schema']) is int and binding['schema'] == 1 and binding['type'] == TYPE and
            binding['predecessor_binding'] == (PREVIOUS / 'binding.json').as_posix() and
            set(binding['changes']) == CHANGES, 'Archive binding or change roster differs')

    original = ROOT / PREVIOUS
    current = previous.load(HERE / 'current-source-inputs.json')
    historical_source = previous.load(original / 'current-source-inputs.json')
    historical_binding = previous.load(original / 'binding.json')
    historical = previous.load(original / 'historical-inputs.json')
    caller = previous.load(original / 'caller-inputs.json')
    owning = previous.load(original / 'owning-closure.json')
    effective = {**owning, **caller, **historical_source}
    pair23_source = dict(historical_source)
    starter = binding['starter_lock_transition']
    require(set(starter) == {'sourceBefore', 'sourceAfter', 'changes'} and
            set(starter['changes']) == STARTER_CHANGES, 'Starter lock change roster differs')
    pair23_preimages = {}
    for name, change in starter['changes'].items():
        require(set(change) == {'before', 'after'} and change['before'] != change['after'],
                'Starter lock transition differs: ' + name)
        raw = previous.read(HERE / 'pair23-predecessor-bytes' / name)
        require(previous.row(raw) == change['before'], 'Pair23 owner preimage differs: ' + name)
        pair23_preimages[name] = raw

    export = binding['export_runner_transition']
    require(set(export) == {'sourceBefore', 'sourceAfter', 'before', 'after'} and
            export['before'] == binding['changes'][EXPORT_RUNNER]['after'] and
            export['before'] != export['after'], 'Export runner transition differs')

    # Compare the earlier archive against its exact bytes where this transition
    # replaces an owning input. The original predecessor is restored separately.
    prior_effective = {**effective, **{name: change['after'] for name, change in binding['changes'].items()}}
    capability = binding['capability_transition']
    capability_preimages = read_capability_preimages(previous, capability, prior_effective)

    upgrade = binding['upgrade_transition']
    require(set(upgrade) == {'sourceBefore', 'sourceAfter', 'changes'} and
            set(upgrade['changes']) == UPGRADE_CHANGES, 'Upgrade change roster differs')
    upgrade_preimages = {}
    for name, change in upgrade['changes'].items():
        require(set(change) == {'before', 'after'} and change['before'] != change['after'],
                'Upgrade transition differs: ' + name)
        raw = previous.read(HERE / 'upgrade-predecessor-bytes' / name)
        require(previous.row(raw) == change['before'], 'Upgrade owner preimage differs: ' + name)
        upgrade_preimages[name] = raw

    pair24 = binding['pair24_transition']
    pair24_preimages = read_pair24_preimages(previous, pair24)

    inspector_preimages = {
        name: read_predecessor_member(HERE / RELEASE_INSPECTOR_PREFIX / name)
        for name in RELEASE_INSPECTOR_CHANGES - RELEASE_INSPECTOR_ADDITIONS
    }
    preimages = {}
    for name, change in binding['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                (name not in effective if name in ADDITIONS else name in effective) and
                change['before'] == effective.get(name), 'Predecessor owner binding differs: ' + name)
        path = ROOT / name
        # The runner's historical row is pinned by the Pair23 digest below.
        # Restoration uses the original predecessor bytes from this archive.
        if name != EXPORT_RUNNER:
            raw = pair23_preimages.get(name)
            if raw is None:
                raw = capability_preimages.get(name)
            if raw is None:
                raw = upgrade_preimages.get(name)
            if raw is None:
                raw = pair24_preimages.get(name)
            if raw is None:
                raw = inspector_preimages.get(name)
            if raw is None:
                raw = previous.read(path)
            require(previous.row(raw) == change['after'], 'Pair23 archive owner differs: ' + name)
        require(type(change['mode']) is int and change['mode'] in (0o644, 0o755) and
                stat.S_IMODE(path.stat().st_mode) == change['mode'],
                'Installed archive owner mode differs: ' + name)
        if name not in ADDITIONS:
            raw = previous.read(HERE / 'predecessor-bytes' / name)
            require(previous.row(raw) == change['before'], 'Archive owner preimage differs: ' + name)
            preimages[name] = (raw, change['mode'])
        effective[name] = change['after']
        if name in SOURCE_CHANGES:
            pair23_source[name] = change['after']
    require(previous.digest(pair23_source) == starter['sourceBefore'] == PAIR23_SOURCE_SHA256 and
            all(pair23_source[n] != historical_source[n] for n in SOURCE_CHANGES),
            'Pair23 source inverse differs')
    closeout = {**pair23_source, **{name: historical_source[name] for name in RENDERER_SOURCE_CHANGES}}
    require(previous.digest(closeout) == CLOSEOUT_SOURCE_SHA256, 'CLI closeout source differs')

    expected_source = dict(pair23_source)
    for name, change in starter['changes'].items():
        require(effective[name] == change['before'], 'Pair23 predecessor binding differs: ' + name)
        effective[name] = change['after']
        if name in STARTER_SOURCE_CHANGES:
            expected_source[name] = change['after']
        if name not in CHANGES:
            require(stat.S_IMODE((ROOT / name).stat().st_mode) == 0o644,
                    'Installed starter lock source mode differs: ' + name)
            preimages[name] = (pair23_preimages[name], 0o644)
    require(previous.digest(expected_source) == starter['sourceAfter'] ==
            export['sourceBefore'] == STARTER_LOCK_SOURCE_SHA256, 'Starter lock source inverse differs')
    effective[EXPORT_RUNNER] = expected_source[EXPORT_RUNNER] = export['after']
    require(previous.digest(expected_source) == export['sourceAfter'] ==
            upgrade['sourceBefore'] == UPGRADE_PREDECESSOR_SHA256,
            'Export runner source transition differs')
    for name, change in upgrade['changes'].items():
        require(effective[name] == change['before'], 'Upgrade predecessor owner differs: ' + name)
        require(stat.S_IMODE((ROOT / name).stat().st_mode) == 0o644,
                'Installed upgrade owner mode differs: ' + name)
        if name not in CHANGES:
            preimages[name] = (upgrade_preimages[name], 0o644)
        effective[name] = change['after']
        if name in UPGRADE_SOURCE_CHANGES:
            expected_source[name] = change['after']
    require(previous.digest(expected_source) == upgrade['sourceAfter'] ==
            pair24['sourceBefore'] == PAIR24_PREDECESSOR_SHA256,
            'Pinned Pair23 upgrade source differs')
    installed = {**effective, **{name: change['after'] for name, change in capability['changes'].items()}}
    for name, change in pair24['changes'].items():
        require(installed.get(name) == change['before'], 'Pair24 predecessor owner differs: ' + name)
        installed[name] = change['after']
        if name in PAIR24_SOURCE_CHANGES:
            require(expected_source[name] == change['before'], 'Pair24 source preimage differs: ' + name)
            expected_source[name] = change['after']
        if name in effective and name not in preimages and name not in capability['changes']:
            preimages[name] = (pair24_preimages[name], change['mode'])
        require(stat.S_IMODE((ROOT / name).stat().st_mode) == change['mode'],
                'Installed Pair24 owner mode differs: ' + name)
    cancel = binding['cancel_cli_transition']
    require(set(cancel) == {'sourceBefore', 'sourceAfter', 'changes'} and
            set(cancel['changes']) == CANCEL_CLI_CHANGES and
            cancel['sourceBefore'] == pair24['sourceAfter'] == previous.digest(expected_source),
            'Native cancel predecessor source differs')
    for name, change in cancel['changes'].items():
        raw = previous.read(HERE / 'cancel-cli-predecessor-bytes' / name)
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] and
                change['before'] != change['after'] and
                stat.S_IMODE((ROOT / name).stat().st_mode) == 0o644,
                'Native cancel CLI row differs: ' + name)
        if name not in preimages:
            preimages[name] = (raw, 0o644)
        installed[name] = change['after']
        if name in CANCEL_CLI_SOURCE_CHANGES:
            expected_source[name] = change['after']
    hydration = binding['hydration_transition']
    require(set(hydration) == {'sourceBefore', 'sourceAfter', 'changes'} and
            previous.digest(expected_source) == cancel['sourceAfter'] == hydration['sourceBefore'] and
            set(hydration['changes']) == HYDRATION_CHANGES, 'Hydration predecessor source differs')
    for name, change in hydration['changes'].items():
        raw = previous.read(HERE / 'hydration-predecessor-bytes' / name)
        require(set(change) == {'before', 'after', 'mode'} and
                installed[name] == change['before'] == previous.row(raw) and
                change['before'] != change['after'] and change['mode'] == 0o644,
                'Hydration transition differs: ' + name)
        installed[name] = change['after']
        if name in HYDRATION_SOURCE_CHANGES:
            expected_source[name] = change['after']
        # The existing inverse predates this transition where both own a path.
        preimages.setdefault(name, (raw, change['mode']))
    require(previous.digest(expected_source) == hydration['sourceAfter'] and len(expected_source) == 141,
            'Hydration source transition differs')
    workflow = binding['hosted_v33_workflow']
    before = previous.read(HERE / HOSTED_V32_WORKFLOW)
    require(set(workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == workflow['before'] and
            workflow['before'] != workflow['after'], 'Hosted v32 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = workflow['after']
    local_store = binding['local_store_transition']
    require(set(local_store) == {'sourceBefore', 'sourceAfter', 'changes'} and
            local_store['sourceBefore'] == hydration['sourceAfter'] and
            set(local_store['changes']) == LOCAL_STORE_CHANGES,
            'Local store predecessor source differs')
    for name, change in local_store['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == installed.get(name) and change['before'] != change['after'] and
                type(change['mode']) is int and change['mode'] == 0o644,
                'Local store owner row differs: ' + name)
        if name not in LOCAL_STORE_ADDITIONS:
            raw = read_predecessor_member(HERE / LOCAL_STORE_PREFIX / name)
            require(previous.row(raw) == change['before'], 'Local store predecessor bytes differ: ' + name)
            preimages.setdefault(name, (raw, change['mode']))
        else:
            require(name not in installed, 'Local store addition already owned: ' + name)
        installed[name] = change['after']
        if name in LOCAL_STORE_SOURCE_CHANGES:
            require(expected_source.get(name) == change['before'], 'Local store source inverse differs: ' + name)
            expected_source[name] = change['after']
    require(len(expected_source) == 143 and local_store['sourceAfter'] == previous.digest(expected_source),
            'Local store source transition differs')
    update = binding['public_update_transition']
    require(set(update) == {'sourceBefore', 'sourceAfter', 'changes'} and
            update['sourceBefore'] == local_store['sourceAfter'] and
            set(update['changes']) == {PUBLIC_UPDATE_MAIN, PUBLIC_UPDATE_SOURCE},
            'Public update predecessor source differs')
    before = read_predecessor_member(HERE / PUBLIC_UPDATE_PREIMAGE)
    require(expected_source[PUBLIC_UPDATE_MAIN] == previous.row(before) and
            PUBLIC_UPDATE_SOURCE not in expected_source, 'Public update preimage differs')
    for name, change in update['changes'].items():
        require(set(change) == {'before', 'after'} and
                change['before'] == installed.get(name) == expected_source.get(name) and
                change['before'] != change['after'] and
                stat.S_IMODE((ROOT / name).lstat().st_mode) == 0o644 and
                stat.S_ISREG((ROOT / name).lstat().st_mode),
                'Public update owner row differs: ' + name)
        installed[name] = expected_source[name] = change['after']
    require(len(expected_source) == 144 and
            previous.digest(expected_source) == update['sourceAfter'],
            'Public update source transition differs')
    runtime = binding['runtime_notice_witness_transition']
    require(set(runtime) == {'sourceBefore', 'sourceAfter', 'changes'} and
            runtime['sourceBefore'] == update['sourceAfter'] and
            set(runtime['changes']) == RUNTIME_NOTICE_WITNESS_CHANGES,
            'Runtime notice and witness change roster differs')
    for name, change in runtime['changes'].items():
        raw = read_predecessor_member(HERE / RUNTIME_NOTICE_WITNESS_PREFIX / name)
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == previous.row(raw) == installed.get(name) and
                change['before'] != change['after'] and type(change['mode']) is int and
                change['mode'] == 0o644, 'Runtime notice or witness owner row differs: ' + name)
        preimages.setdefault(name, (raw, change['mode']))
        installed[name] = change['after']
        if name in RUNTIME_NOTICE_WITNESS_SOURCE_CHANGES:
            require(expected_source[name] == change['before'], 'Runtime packaging source preimage differs: ' + name)
            expected_source[name] = change['after']
    require(len(expected_source) == 144 and runtime['sourceAfter'] == previous.digest(expected_source),
            'Runtime notice and witness source transition differs')
    workflow = binding['workspace_builds_workflow']
    before = read_predecessor_member(HERE / WORKSPACE_BUILDS_WORKFLOW)
    require(set(workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == workflow['before'] and
            workflow['before'] != workflow['after'], 'Workspace builds workflow preimage differs')
    installed[VERIFY_WORKFLOW] = workflow['after']

    inspector = binding['release_inspector_transition']
    require(set(inspector) == {'sourceBefore', 'sourceAfter', 'changes'} and
            inspector['sourceBefore'] == runtime['sourceAfter'] and
            set(inspector['changes']) == RELEASE_INSPECTOR_CHANGES,
            'Release inspector predecessor or change roster differs')
    for name, change in inspector['changes'].items():
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == installed.get(name) and change['before'] != change['after'] and
                type(change['mode']) is int and change['mode'] == 0o644,
                'Release inspector owner row differs: ' + name)
        if name in RELEASE_INSPECTOR_ADDITIONS:
            require(name not in installed, 'Release inspector addition already owned: ' + name)
        else:
            raw = inspector_preimages[name]
            require(previous.row(raw) == change['before'], 'Release inspector predecessor bytes differ: ' + name)
            preimages.setdefault(name, (raw, change['mode']))
        if name in RELEASE_INSPECTOR_SOURCE_CHANGES:
            require(expected_source.get(name) == change['before'], 'Release inspector source preimage differs: ' + name)
            expected_source[name] = change['after']
        installed[name] = change['after']
    require(len(expected_source) == 150 and
            inspector['sourceAfter'] == previous.digest(expected_source) == ICU_NOTICE_PREDECESSOR_SHA256,
            'Release inspector source transition differs')

    icu = binding['icu_notice_transition']
    require(set(icu) == {'sourceBefore', 'sourceAfter', 'changes'} and
            icu['sourceBefore'] == inspector['sourceAfter'] and
            set(icu['changes']) == ICU_NOTICE_CHANGES, 'ICU notice predecessor or change roster differs')
    for name, change in icu['changes'].items():
        raw = read_predecessor_member(HERE / ICU_NOTICE_PREFIX / name)
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == previous.row(raw) and change['before'] != change['after'] and
                type(change['mode']) is int and change['mode'] == 0o644,
                'ICU notice owner row differs: ' + name)
        # The packing test existed at the predecessor revision outside the owner map.
        if name == ICU_NOTICE_TEST:
            require(name not in installed, 'ICU packing test already owned: ' + name)
        else:
            require(change['before'] == installed[name], 'ICU notice owner preimage differs: ' + name)
        if name == ICU_NOTICE_DRIVER:
            require(expected_source[name] == change['before'], 'ICU notice source preimage differs: ' + name)
            expected_source[name] = change['after']
        installed[name] = change['after']
    require(current == expected_source and len(current) == 150 and binding['source'] == {
        'count': len(current), 'manifest': 'current-source-inputs.json',
        'sha256': icu['sourceAfter'],
    } and icu['sourceAfter'] == previous.digest(current), 'ICU notice source transition differs')

    console_workflow = binding['console_build_logs_workflow']
    before = read_predecessor_member(HERE / CONSOLE_BUILD_LOGS_WORKFLOW)
    require(set(console_workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == console_workflow['before'] and
            console_workflow['before'] != console_workflow['after'], 'Console build logs workflow preimage differs')
    installed[VERIFY_WORKFLOW] = console_workflow['after']

    previous.check_rows(ROOT, installed)
    for name, change in icu['changes'].items():
        require(stat.S_IMODE((ROOT / name).lstat().st_mode) == change['mode'],
                'Installed ICU notice owner mode differs: ' + name)
    for name, change in inspector['changes'].items():
        require(stat.S_IMODE((ROOT / name).lstat().st_mode) == change['mode'],
                'Installed release inspector owner mode differs: ' + name)
    for name, change in runtime['changes'].items():
        require(stat.S_IMODE((ROOT / name).lstat().st_mode) == change['mode'],
                'Installed runtime notice or witness owner mode differs: ' + name)
    for name, change in local_store['changes'].items():
        require(stat.S_IMODE((ROOT / name).stat().st_mode) == change['mode'],
                'Installed local store owner mode differs: ' + name)
    for name, change in hydration['changes'].items():
        require(stat.S_IMODE((ROOT / name).stat().st_mode) == change['mode'],
                'Installed hydration owner mode differs: ' + name)
    for name, change in capability['changes'].items():
        require(stat.S_IMODE((ROOT / name).stat().st_mode) == change['mode'],
                'Installed capability archive owner mode differs: ' + name)
        if name in effective and name not in preimages:
            preimages[name] = (capability_preimages[name], change['mode'])
    owner = previous.module('native_archive_actual_collector', ROOT / previous.OWNER)
    profile = owner.load_profile(ROOT)
    pair22 = historical_binding['sdk_transition']['profileAfter']
    adapter_files = {**pair22['adapter_files'], RENDERER: current['native/android/' + RENDERER]}
    expected_profile = {**pair22, 'id': 'mixer.android-source-pair.23', 'adapter_files': adapter_files,
                        'adapter_compatibility_sha256': previous.digest(adapter_files)}
    require(binding['renderer_transition'] == {
                'sourceBefore': CLOSEOUT_SOURCE_SHA256,
                'sourceAfter': PAIR23_SOURCE_SHA256,
                'profileAfter': expected_profile,
            }, 'Archive Pair23 renderer profile differs')
    require(expected_profile['adapter_files'][STARTER_ACTIVITY] ==
            pair24['changes']['native/android/' + STARTER_ACTIVITY]['before'],
            'Pair23 Activity preimage differs')
    adapter_files = {**expected_profile['adapter_files'],
                     STARTER_ACTIVITY: current['native/android/' + STARTER_ACTIVITY]}
    expected_current = {**expected_profile, 'id': 'mixer.android-source-pair.24', 'adapter_files': adapter_files,
                        'adapter_compatibility_sha256': previous.digest(adapter_files)}
    require(pair24['profileAfter'] == expected_current == profile and
            previous.profile_summary(profile) == binding['profile'],
            'Archive Pair24 starter profile differs')
    selector_path = ROOT / 'cli/build-tests/current_android_profile.py'
    selector = previous.module('native_archive_current_selector', selector_path)
    require(selector.load_current_profile(ROOT) == profile, 'Current source-pair selector differs')
    require(owner.source_inputs(profile) == current, 'Actual archive owning source map differs')

    material = {}
    history_paths = set(historical) | (effective.keys() - ADDITIONS) | {
        (PREVIOUS / name).as_posix() for name in (*old_seal['members'], 'seal.json')
    }
    total = 0
    for name in sorted(history_paths):
        if name in preimages:
            raw, mode = preimages[name]
        else:
            path = ROOT / previous.relative(name)
            raw, mode = previous.read(path), stat.S_IMODE(path.stat().st_mode)
        total += len(raw)
        require(total <= 64 * 1024 * 1024, 'Source141 restoration copy budget exceeded')
        material[name] = (raw, mode)
    return binding, current, material


def restore(out, material):
    out = Path(out).absolute()
    require(not out.exists() and not out.is_symlink(), 'Fresh Source141 output required')
    require(not any(p.is_symlink() for p in out.parents), 'Source141 output ancestry symlink')
    out.mkdir(mode=0o700)
    for name, (raw, mode) in material.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(mode)
    spec = importlib.util.spec_from_file_location('restored_source141_authority',
                                                  out / PREVIOUS / 'adopt_sdk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.admit()


def admit():
    binding, selected, material = install_inputs()
    with tempfile.TemporaryDirectory(prefix='native-archive-source141-') as scratch:
        _, (historical, _, source127) = restore(Path(scratch).resolve() / 'source141', material)
    return {**binding, 'sdk_transition': historical['sdk_transition']}, selected, source127


def verify(installed=False):
    binding, selected, _ = admit()
    return {'schema': 1, 'type': TYPE, 'source_count': len(selected),
            'source_sha256': binding['source']['sha256'], 'profile': binding['profile'],
            'predecessor_icu_notice_sha256': binding['icu_notice_transition']['sourceBefore'],
            'predecessor_release_inspector_sha256': binding['release_inspector_transition']['sourceBefore'],
            'predecessor_runtime_notice_witness_sha256': binding['runtime_notice_witness_transition']['sourceBefore'],
            'predecessor_local_store_source141_sha256': binding['local_store_transition']['sourceBefore'],
            'predecessor_pair24_source141_sha256': binding['cancel_cli_transition']['sourceBefore'],
            'predecessor_cancel_cli_source141_sha256': binding['hydration_transition']['sourceBefore'],
            'predecessor_upgraded_pair23_sha256': binding['pair24_transition']['sourceBefore'],
            'predecessor_export_runner_source141_sha256': binding['upgrade_transition']['sourceBefore'],
            'predecessor_starter_lock_source141_sha256': binding['export_runner_transition']['sourceBefore'],
            'predecessor_pair23_source141_sha256': binding['starter_lock_transition']['sourceBefore'],
            'predecessor_closeout_source141_sha256': binding['renderer_transition']['sourceBefore'],
            'predecessor_source141_sha256': binding['sdk_transition']['sourceAfter'],
            'predecessor_source127_sha256': binding['sdk_transition']['sourceBefore'],
            'adoption': False, 'activation': False, 'aggregate': False, 'GA': False, 'holdsReleased': False}


def prepare_source141(out):
    _, _, material = install_inputs()
    _, (binding, _, _) = restore(out, material)
    return {'source141': binding['source']['sha256'], 'files': len(material),
            'source127': binding['sdk_transition']['sourceBefore'], 'out': str(out)}


def prepare_predecessor(out):
    _, _, material = install_inputs()
    with tempfile.TemporaryDirectory(prefix='native-archive-source141-') as scratch:
        previous, _ = restore(Path(scratch).resolve() / 'source141', material)
        return previous.prepare_predecessor(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verify_parser = commands.add_parser('verify')
    verify_parser.add_argument('--workflow-installed', action='store_true')
    for name in ('prepare-source141', 'prepare-predecessor'):
        commands.add_parser(name).add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify(args.workflow_installed)
    elif args.command == 'prepare-source141':
        result = prepare_source141(args.out)
    else:
        result = prepare_predecessor(args.out)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
