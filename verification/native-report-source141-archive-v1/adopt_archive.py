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
REGISTRATION_WORKFLOW = 'application-registration-predecessor-bytes/' + VERIFY_WORKFLOW
SOURCE_STARTER_WORKFLOW = 'source-starter-selection-predecessor-bytes/' + VERIFY_WORKFLOW
PHOENIX_CI_WORKFLOW = 'phoenix-ci-predecessor-bytes/' + VERIFY_WORKFLOW
STARTER_PACKAGE_CLOSURE_WORKFLOW = 'starter-package-closure-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V41_WORKFLOW = 'hosted-v41-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V41_NOTICES = 'hosted-v41-predecessor-bytes/THIRD_PARTY.yml'
HOSTED_V42_WORKFLOW = 'hosted-v42-predecessor-bytes/' + VERIFY_WORKFLOW
FIXTURE_RUST_PIN_WORKFLOW = 'fixture-rust-pin-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V43_WORKFLOW = 'hosted-v43-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V44_WORKFLOW = 'hosted-v44-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V45_WORKFLOW = 'hosted-v45-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V46_WORKFLOW = 'hosted-v46-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V47_WORKFLOW = 'hosted-v47-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V48_WORKFLOW = 'hosted-v48-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V49_WORKFLOW = 'hosted-v49-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V50_WORKFLOW = 'hosted-v50-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V51_WORKFLOW = 'hosted-v51-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V52_WORKFLOW = 'hosted-v52-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V53_WORKFLOW = 'hosted-v53-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V54_WORKFLOW = 'hosted-v54-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V55_WORKFLOW = 'hosted-v55-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V56_WORKFLOW = 'hosted-v56-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V57_WORKFLOW = 'hosted-v57-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V58_WORKFLOW = 'hosted-v58-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V59_WORKFLOW = 'hosted-v59-predecessor-bytes/' + VERIFY_WORKFLOW
HOSTED_V60_WORKFLOW = 'hosted-v60-predecessor-bytes/' + VERIFY_WORKFLOW
APPLE_RENDERER = 'sdk/Sources/MixerApple/MixerNativeView.swift'
APPLE_PREIMAGE = 'apple-section-predecessor-bytes/sdk/Sources/MixerApple/MixerNativeView.swift'
APPLE_SECTION_SOURCE_SHA256 = '1d2ebd6883fff9147aeec6d558b3ce1b2ec8f7dffc22b99c12ec5a85ab19b438'
APPLE_TEXT_PREIMAGE = 'apple-text-predecessor-bytes/' + APPLE_RENDERER
APPLE_TEXT_SOURCE_SHA256 = '0e7595225ba6fed59d49f6623ace68fa8e22b69c96b70ef3a504ede9d9ff5f00'
CAPABILITY_IDENTITY = 'sdk/Sources/MixerCapabilities/GeneratedIdentity.swift'
CAPABILITY_IDENTITY_PREIMAGE = 'capability-identity-predecessor-bytes/' + CAPABILITY_IDENTITY
CAPABILITY_IDENTITY_SOURCE_SHA256 = '039ef48877383861160dbe0a5dd639f0bba08d0076c254e7035caf812387cc49'
GUEST_CUTOFF = 'sdk/Sources/MixerGuest/GuestUIExchangeCore.swift'
GUEST_CUTOFF_PREIMAGE = 'guest-cutoff-predecessor-bytes/' + GUEST_CUTOFF
GUEST_CUTOFF_SOURCE_SHA256 = '515091e8069c5115c340943da3d0fba525f7a05b90c813d813392680704a6334'
STORE_PLATFORM_IDENTITY_PREFIX = 'store-platform-identity-predecessor-bytes/'
STORE_PLATFORM_IDENTITY_SOURCE_SHA256 = '3d752fc0388f791368d4623078561858d4a1c39226806c50538afa87ff1283be'
STORE_PLATFORM_IDENTITY_INPUTS = {
    'cli/Sources/MixerBuild/Configuration.swift',
    'cli/Sources/MixerBuild/LocalStoreSubmission.swift',
    'cli/Sources/MixerBuild/StoreReconciliation.swift',
    'cli/Sources/MixerCLI/main.swift',
}
WORKER_SWIFT_PROBE = 'cli/Sources/MixerBuild/ProjectGenerator.swift'
WORKER_SWIFT_PROBE_PREIMAGE = 'worker-swift-probe-predecessor-bytes/' + WORKER_SWIFT_PROBE
WORKER_SWIFT_PROBE_SOURCE_SHA256 = 'a26f01a1ed80fbaaae03776d37e8ecce194c52adb28ff9770be9c608f136db1b'
ANDROID_OUTPUT_PREFIX = 'android-retained-output-predecessor-bytes/'
ANDROID_OUTPUT_SOURCE_SHA256 = 'de48670cd6bf7a0830b8793d3622e317da018df460c4850b1793d727416517b0'
ANDROID_OUTPUT_ADDITION = 'cli/Sources/MixerBuild/AndroidBuildOutput.swift'
ANDROID_OUTPUT_CHANGES = {
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/NativeBuildOutput.swift',
    'cli/Sources/MixerBuild/NativeProductCapture.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Sources/MixerCLI/main.swift',
}
ANDROID_OUTPUT_CORRECTION_PREFIX = 'android-retained-output-correction-predecessor-bytes/'
ANDROID_OUTPUT_CORRECTION_SOURCE_SHA256 = '06a3f1fada7ddbe9e4f30b987760d208c9bd2645284860574bf5ac249df4b201'
ANDROID_OUTPUT_CORRECTION_CHANGES = {
    'cli/Sources/MixerProcessIO/include/MixerProcessIO.h',
    'cli/Sources/MixerProcessIO/process.c',
    ANDROID_OUTPUT_ADDITION,
    'cli/Sources/MixerBuild/NativeBuildOutput.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
}
ANDROID_OUTPUT_CORRECTION_TEST = 'cli/build-tests/test_android_public_host.py'
MANAGED_ANDROID_PREFIX = 'managed-android-retained-predecessor-bytes/'
MANAGED_ANDROID_SOURCE_SHA256 = 'b63abaaad38808250ee3f4273224412b7428e52f0e42af2031df10e45f917718'
MANAGED_ANDROID_CHANGES = {
    'cli/Sources/MixerBuild/AndroidBuildOutput.swift',
    'cli/Sources/MixerBuild/AndroidProject.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'cli/Sources/MixerCLI/main.swift',
}
PAIR25_PREFIX = 'pair25-predecessor-bytes/'
PAIR25_PREDECESSOR_REVISION = '89429afd8854cc4b8a0f734235762f55833a28d6'
PAIR25_SOURCE_SHA256 = '6a0db1b665c429448d665a7a755f186772bd9fac0126abc6ee660843c27a0d92'
PAIR25_SOURCE_CHANGES = {
    'native/android/' + RENDERER,
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    EXPORT_RUNNER,
}
PAIR25_CHANGES = PAIR25_SOURCE_CHANGES | {
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/Tests/MixerBuildTests/GeneratedPublicAndroidV4Tests.swift',
    ACTIVITY_TESTS + 'EditorTransactionHostTests.java',
    ACTIVITY_TESTS + 'private-owner-barrier-bindings.json',
    ACTIVITY_TESTS + 'private-owner-barrier-map.json',
    ACTIVITY_TESTS + 'run-private-owner-crosscompile.py',
    JAVA + 'bootstrap.py',
    JAVA + 'test_bootstrap.py',
}
SWIFT_VERSION_PREFIX = 'swift-version-predecessor-bytes/'
SWIFT_VERSION_SOURCE_CHANGES = {
    'cli/Sources/MixerBuild/OwnedCommand.swift',
    'cli/Sources/MixerBuild/POSIXCommandControl.swift',
    'cli/Sources/MixerBuild/ProcessRunner.swift',
    'cli/Sources/MixerBuild/ProjectGenerator.swift',
}
SWIFT_VERSION_CHANGES = SWIFT_VERSION_SOURCE_CHANGES | {'cli/build-tests/test_public_export.py'}
CLI_NONREGULAR_INPUT_TEST = 'cli/Tests/MixerBuildTests/UpdateHardeningTests.swift'
CLI_NONREGULAR_INPUT_TEST_PREIMAGE = 'cli-nonregular-input-test-predecessor-bytes/' + CLI_NONREGULAR_INPUT_TEST
SIGNED_APPLE_OVERFLOW_TEST = 'capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedRuntimeTests.swift'
SIGNED_APPLE_OVERFLOW_TEST_PREIMAGE = 'signed-apple-overflow-test-predecessor-bytes/' + SIGNED_APPLE_OVERFLOW_TEST
SPARSE_CHECKOUT_TEST = JAVA + 'test_sparse_checkout.py'
SPARSE_CHECKOUT_TEST_PREIMAGE = 'sparse-checkout-test-predecessor-bytes/' + SPARSE_CHECKOUT_TEST
HALT_CLI_PREFIX = 'halt-cli-predecessor-bytes/'
SOURCE150_SHA256 = '4a202d6aa4f6b81884df32cd0fe67cc8ce9847e8d4ae2ebea8b2cf1d4711a6f8'
HALT_CLI_SOURCE_CHANGES = {PUBLIC_UPDATE_MAIN, PUBLIC_UPDATE_SOURCE}
HALT_CLI_CHANGES = HALT_CLI_SOURCE_CHANGES | {VERIFY_WORKFLOW, JAVA + 'test_sparse_checkout.py'}
MEMBERS = {PUBLIC_UPDATE_PREIMAGE, HOSTED_V32_WORKFLOW, WORKSPACE_BUILDS_WORKFLOW, CONSOLE_BUILD_LOGS_WORKFLOW, REGISTRATION_WORKFLOW, SOURCE_STARTER_WORKFLOW, PHOENIX_CI_WORKFLOW, 'adopt_archive.py', 'binding.json', 'current-source-inputs.json'} | {
    APPLE_PREIMAGE, APPLE_TEXT_PREIMAGE, CAPABILITY_IDENTITY_PREIMAGE, STARTER_PACKAGE_CLOSURE_WORKFLOW,
    HOSTED_V41_WORKFLOW, HOSTED_V41_NOTICES, HOSTED_V42_WORKFLOW, FIXTURE_RUST_PIN_WORKFLOW,
    HOSTED_V43_WORKFLOW, HOSTED_V44_WORKFLOW, HOSTED_V45_WORKFLOW, HOSTED_V46_WORKFLOW, HOSTED_V47_WORKFLOW, HOSTED_V48_WORKFLOW, HOSTED_V49_WORKFLOW, HOSTED_V50_WORKFLOW, HOSTED_V51_WORKFLOW, HOSTED_V52_WORKFLOW, HOSTED_V53_WORKFLOW, HOSTED_V54_WORKFLOW, HOSTED_V55_WORKFLOW, HOSTED_V56_WORKFLOW, HOSTED_V57_WORKFLOW,
    HOSTED_V58_WORKFLOW, HOSTED_V59_WORKFLOW, HOSTED_V60_WORKFLOW, GUEST_CUTOFF_PREIMAGE, WORKER_SWIFT_PROBE_PREIMAGE, CLI_NONREGULAR_INPUT_TEST_PREIMAGE,
    SIGNED_APPLE_OVERFLOW_TEST_PREIMAGE, SPARSE_CHECKOUT_TEST_PREIMAGE,
} | {STORE_PLATFORM_IDENTITY_PREFIX + name for name in STORE_PLATFORM_IDENTITY_INPUTS} | {
    ANDROID_OUTPUT_PREFIX + name for name in ANDROID_OUTPUT_CHANGES
} | {
    ANDROID_OUTPUT_CORRECTION_PREFIX + name
    for name in ANDROID_OUTPUT_CORRECTION_CHANGES | {ANDROID_OUTPUT_CORRECTION_TEST}
} | {
    MANAGED_ANDROID_PREFIX + name for name in MANAGED_ANDROID_CHANGES
} | {
    PAIR25_PREFIX + name for name in PAIR25_CHANGES
} | {
    SWIFT_VERSION_PREFIX + name for name in SWIFT_VERSION_CHANGES
} | {
    HALT_CLI_PREFIX + name for name in HALT_CLI_CHANGES
} | {
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
                             'release_inspector_transition', 'icu_notice_transition',
                             'console_build_logs_workflow', 'halt_cli_transition',
                             'apple_section_accessibility_transition', 'apple_synchronous_text_transition',
                             'application_registration_workflow', 'source_starter_selection_workflow',
                             'phoenix_ci_workflow', 'starter_package_closure_workflow',
                             'capability_identity_transition', 'guest_cutoff_transition', 'hosted_v41_workflow', 'hosted_v41_notices',
                             'hosted_v42_workflow', 'store_platform_identity_transition',
                             'worker_swift_probe_transition', 'android_retained_output_transition',
                             'android_retained_output_correction_transition',
                             'managed_android_retained_transition', 'pair25_transition', 'swift_version_transition',
                             'cli_nonregular_input_test_transition', 'signed_apple_overflow_test_transition',
                             'sparse_checkout_test_transition',
                             'fixture_rust_pin_workflow', 'hosted_v43_workflow',
                             'hosted_v44_workflow', 'hosted_v45_workflow', 'hosted_v46_workflow', 'hosted_v47_workflow', 'hosted_v48_workflow', 'hosted_v49_workflow', 'hosted_v50_workflow', 'hosted_v51_workflow', 'hosted_v52_workflow', 'hosted_v53_workflow', 'hosted_v54_workflow', 'hosted_v55_workflow', 'hosted_v56_workflow', 'hosted_v57_workflow',
                             'hosted_v58_workflow', 'hosted_v59_workflow', 'hosted_v60_workflow'} and
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
    android_output_preimages = {
        name: read_predecessor_member(HERE / ANDROID_OUTPUT_PREFIX / name)
        for name in ANDROID_OUTPUT_CHANGES
    }
    pair25 = binding['pair25_transition']
    require(set(pair25) == {'baseRevision', 'sourceBefore', 'sourceAfter', 'changes', 'profileAfter'} and
            pair25['baseRevision'] == PAIR25_PREDECESSOR_REVISION and
            pair25['sourceBefore'] == MANAGED_ANDROID_SOURCE_SHA256 and
            set(pair25['changes']) == PAIR25_CHANGES, 'Pair25 transition roster differs')
    pair25_preimages = {
        name: previous.read(HERE / (PAIR25_PREFIX + name)) for name in PAIR25_CHANGES
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
                raw = android_output_preimages.get(name)
            if raw is None:
                raw = pair25_preimages.get(name)
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
    require(len(expected_source) == 150 and
            previous.digest(expected_source) == icu['sourceAfter'] == SOURCE150_SHA256,
            'ICU notice source transition differs')

    console_workflow = binding['console_build_logs_workflow']
    before = read_predecessor_member(HERE / CONSOLE_BUILD_LOGS_WORKFLOW)
    require(set(console_workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == console_workflow['before'] and
            console_workflow['before'] != console_workflow['after'], 'Console build logs workflow preimage differs')
    installed[VERIFY_WORKFLOW] = console_workflow['after']

    halt = binding['halt_cli_transition']
    require(set(halt) == {'sourceBefore', 'sourceAfter', 'changes'} and
            halt['sourceBefore'] == SOURCE150_SHA256 and
            set(halt['changes']) == HALT_CLI_CHANGES, 'Halt CLI predecessor or change roster differs')
    for name, change in halt['changes'].items():
        raw = read_predecessor_member(HERE / HALT_CLI_PREFIX / name)
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == previous.row(raw) == installed[name] and
                change['before'] != change['after'] and
                type(change['mode']) is int and change['mode'] == 0o644,
                'Halt CLI owner row differs: ' + name)
        if name in HALT_CLI_SOURCE_CHANGES:
            require(expected_source[name] == change['before'], 'Halt CLI source preimage differs: ' + name)
            expected_source[name] = change['after']
        installed[name] = change['after']
    require(len(expected_source) == 150 and halt['sourceAfter'] == previous.digest(expected_source),
            'Halt CLI source transition differs')

    registration_workflow = binding['application_registration_workflow']
    before = read_predecessor_member(HERE / REGISTRATION_WORKFLOW)
    require(set(registration_workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == registration_workflow['before'] and
            registration_workflow['before'] != registration_workflow['after'],
            'Application registration workflow preimage differs')
    installed[VERIFY_WORKFLOW] = registration_workflow['after']

    source_starter_workflow = binding['source_starter_selection_workflow']
    before = read_predecessor_member(HERE / SOURCE_STARTER_WORKFLOW)
    require(set(source_starter_workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == source_starter_workflow['before'] and
            source_starter_workflow['before'] != source_starter_workflow['after'],
            'Source starter selection workflow preimage differs')
    installed[VERIFY_WORKFLOW] = source_starter_workflow['after']

    phoenix_ci_workflow = binding['phoenix_ci_workflow']
    before = read_predecessor_member(HERE / PHOENIX_CI_WORKFLOW)
    require(set(phoenix_ci_workflow) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == phoenix_ci_workflow['before'] and
            phoenix_ci_workflow['before'] != phoenix_ci_workflow['after'], 'Phoenix CI workflow preimage differs')
    installed[VERIFY_WORKFLOW] = phoenix_ci_workflow['after']

    starter_package_closure = binding['starter_package_closure_workflow']
    before = read_predecessor_member(HERE / STARTER_PACKAGE_CLOSURE_WORKFLOW)
    require(set(starter_package_closure) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == starter_package_closure['before'] and
            starter_package_closure['before'] != starter_package_closure['after'],
            'Starter package closure workflow preimage differs')
    installed[VERIFY_WORKFLOW] = starter_package_closure['after']

    hosted_v41 = binding['hosted_v41_workflow']
    before = read_predecessor_member(HERE / HOSTED_V41_WORKFLOW)
    require(set(hosted_v41) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v41['before'] and
            hosted_v41['before'] != hosted_v41['after'], 'Hosted v41 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v41['after']

    hosted_v42 = binding['hosted_v42_workflow']
    before = read_predecessor_member(HERE / HOSTED_V42_WORKFLOW)
    require(set(hosted_v42) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v42['before'] and
            hosted_v42['before'] != hosted_v42['after'], 'Hosted v42 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v42['after']

    fixture_rust_pin = binding['fixture_rust_pin_workflow']
    before = read_predecessor_member(HERE / FIXTURE_RUST_PIN_WORKFLOW)
    require(set(fixture_rust_pin) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == fixture_rust_pin['before'] and
            fixture_rust_pin['before'] != fixture_rust_pin['after'], 'Fixture Rust pin workflow preimage differs')
    installed[VERIFY_WORKFLOW] = fixture_rust_pin['after']

    hosted_v43 = binding['hosted_v43_workflow']
    before = read_predecessor_member(HERE / HOSTED_V43_WORKFLOW)
    require(set(hosted_v43) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v43['before'] and
            hosted_v43['before'] != hosted_v43['after'], 'Hosted v43 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v43['after']

    hosted_v44 = binding['hosted_v44_workflow']
    before = read_predecessor_member(HERE / HOSTED_V44_WORKFLOW)
    require(set(hosted_v44) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v44['before'] and
            hosted_v44['before'] != hosted_v44['after'], 'Hosted v44 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v44['after']

    hosted_v45 = binding['hosted_v45_workflow']
    before = read_predecessor_member(HERE / HOSTED_V45_WORKFLOW)
    require(set(hosted_v45) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v45['before'] and
            hosted_v45['before'] != hosted_v45['after'], 'Hosted v45 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v45['after']

    hosted_v46 = binding['hosted_v46_workflow']
    before = read_predecessor_member(HERE / HOSTED_V46_WORKFLOW)
    require(set(hosted_v46) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v46['before'] and
            hosted_v46['before'] != hosted_v46['after'], 'Hosted v46 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v46['after']

    hosted_v47 = binding['hosted_v47_workflow']
    before = read_predecessor_member(HERE / HOSTED_V47_WORKFLOW)
    require(set(hosted_v47) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v47['before'] and
            hosted_v47['before'] != hosted_v47['after'], 'Hosted v47 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v47['after']

    hosted_v48 = binding['hosted_v48_workflow']
    before = read_predecessor_member(HERE / HOSTED_V48_WORKFLOW)
    require(set(hosted_v48) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v48['before'] and
            hosted_v48['before'] != hosted_v48['after'], 'Hosted v48 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v48['after']

    hosted_v49 = binding['hosted_v49_workflow']
    before = read_predecessor_member(HERE / HOSTED_V49_WORKFLOW)
    require(set(hosted_v49) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v49['before'] and
            hosted_v49['before'] != hosted_v49['after'], 'Hosted v49 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v49['after']

    hosted_v50 = binding['hosted_v50_workflow']
    before = read_predecessor_member(HERE / HOSTED_V50_WORKFLOW)
    require(set(hosted_v50) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v50['before'] and
            hosted_v50['before'] != hosted_v50['after'], 'Hosted v50 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v50['after']

    hosted_v51 = binding['hosted_v51_workflow']
    before = read_predecessor_member(HERE / HOSTED_V51_WORKFLOW)
    require(set(hosted_v51) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v51['before'] and
            hosted_v51['before'] != hosted_v51['after'], 'Hosted v51 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v51['after']

    hosted_v52 = binding['hosted_v52_workflow']
    before = read_predecessor_member(HERE / HOSTED_V52_WORKFLOW)
    require(set(hosted_v52) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v52['before'] and
            hosted_v52['before'] != hosted_v52['after'], 'Hosted v52 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v52['after']

    hosted_v53 = binding['hosted_v53_workflow']
    before = read_predecessor_member(HERE / HOSTED_V53_WORKFLOW)
    require(set(hosted_v53) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v53['before'] and
            hosted_v53['before'] != hosted_v53['after'], 'Hosted v53 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v53['after']

    hosted_v54 = binding['hosted_v54_workflow']
    before = read_predecessor_member(HERE / HOSTED_V54_WORKFLOW)
    require(set(hosted_v54) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v54['before'] and
            hosted_v54['before'] != hosted_v54['after'], 'Hosted v54 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v54['after']

    hosted_v55 = binding['hosted_v55_workflow']
    before = read_predecessor_member(HERE / HOSTED_V55_WORKFLOW)
    require(set(hosted_v55) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v55['before'] and
            hosted_v55['before'] != hosted_v55['after'], 'Hosted v55 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v55['after']

    hosted_v56 = binding['hosted_v56_workflow']
    before = read_predecessor_member(HERE / HOSTED_V56_WORKFLOW)
    require(set(hosted_v56) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v56['before'] and
            hosted_v56['before'] != hosted_v56['after'], 'Hosted v56 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v56['after']

    hosted_v57 = binding['hosted_v57_workflow']
    before = read_predecessor_member(HERE / HOSTED_V57_WORKFLOW)
    require(set(hosted_v57) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v57['before'] and
            hosted_v57['before'] != hosted_v57['after'], 'Hosted v57 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v57['after']

    hosted_v58 = binding['hosted_v58_workflow']
    before = read_predecessor_member(HERE / HOSTED_V58_WORKFLOW)
    require(set(hosted_v58) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v58['before'] and
            hosted_v58['before'] != hosted_v58['after'], 'Hosted v58 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v58['after']

    hosted_v59 = binding['hosted_v59_workflow']
    before = read_predecessor_member(HERE / HOSTED_V59_WORKFLOW)
    require(set(hosted_v59) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v59['before'] and
            hosted_v59['before'] != hosted_v59['after'], 'Hosted v59 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v59['after']

    hosted_v60 = binding['hosted_v60_workflow']
    before = read_predecessor_member(HERE / HOSTED_V60_WORKFLOW)
    require(set(hosted_v60) == {'before', 'after'} and
            installed[VERIFY_WORKFLOW] == previous.row(before) == hosted_v60['before'] and
            hosted_v60['before'] != hosted_v60['after'], 'Hosted v60 workflow preimage differs')
    installed[VERIFY_WORKFLOW] = hosted_v60['after']

    notices = binding['hosted_v41_notices']
    before = read_predecessor_member(HERE / HOSTED_V41_NOTICES)
    require(set(notices) == {'before', 'after'} and
            installed['THIRD_PARTY.yml'] == previous.row(before) == notices['before'] and
            notices['before'] != notices['after'], 'Hosted v41 notice preimage differs')
    preimages.setdefault('THIRD_PARTY.yml', (before, 0o644))
    installed['THIRD_PARTY.yml'] = notices['after']

    apple = binding['apple_section_accessibility_transition']
    raw = read_predecessor_member(HERE / APPLE_PREIMAGE)
    require(set(apple) == {'sourceBefore', 'before', 'after'} and
            apple['sourceBefore'] == halt['sourceAfter'] and
            apple['before'] == previous.row(raw) == installed[APPLE_RENDERER] == expected_source[APPLE_RENDERER] and
            apple['before'] != apple['after'],
            'Apple section accessibility predecessor differs')
    require(stat.S_IMODE((ROOT / APPLE_RENDERER).lstat().st_mode) == 0o644,
            'Installed Apple section accessibility renderer mode differs')
    preimages[APPLE_RENDERER] = (raw, 0o644)
    installed[APPLE_RENDERER] = expected_source[APPLE_RENDERER] = apple['after']
    require(previous.digest(expected_source) == APPLE_SECTION_SOURCE_SHA256,
            'Apple section accessibility source transition differs')

    text = binding['apple_synchronous_text_transition']
    section_renderer = read_predecessor_member(HERE / APPLE_TEXT_PREIMAGE)
    require(set(text) == {'sourceBefore', 'before', 'after'} and
            text['sourceBefore'] == APPLE_SECTION_SOURCE_SHA256 and
            text['before'] == previous.row(section_renderer) == installed[APPLE_RENDERER] ==
            expected_source[APPLE_RENDERER] and text['before'] != text['after'],
            'Apple synchronous text predecessor differs')
    installed[APPLE_RENDERER] = expected_source[APPLE_RENDERER] = text['after']
    require(previous.digest(expected_source) == APPLE_TEXT_SOURCE_SHA256,
            'Apple synchronous text source transition differs')
    identity = binding['capability_identity_transition']
    raw_identity = read_predecessor_member(HERE / CAPABILITY_IDENTITY_PREIMAGE)
    require(set(identity) == {'sourceBefore', 'before', 'after'} and
            identity['sourceBefore'] == APPLE_TEXT_SOURCE_SHA256 and
            identity['before'] == previous.row(raw_identity) == installed[CAPABILITY_IDENTITY] ==
            expected_source[CAPABILITY_IDENTITY] and identity['before'] != identity['after'],
            'Capability identity predecessor differs')
    installed[CAPABILITY_IDENTITY] = expected_source[CAPABILITY_IDENTITY] = identity['after']
    preimages.setdefault(CAPABILITY_IDENTITY, (raw_identity, 0o644))
    require(previous.digest(expected_source) == CAPABILITY_IDENTITY_SOURCE_SHA256,
            'Capability identity source transition differs')

    guest_cutoff = binding['guest_cutoff_transition']
    raw_guest_cutoff = read_predecessor_member(HERE / GUEST_CUTOFF_PREIMAGE)
    require(set(guest_cutoff) == {'sourceBefore', 'before', 'after'} and
            guest_cutoff['sourceBefore'] == CAPABILITY_IDENTITY_SOURCE_SHA256 and
            guest_cutoff['before'] == previous.row(raw_guest_cutoff) == installed[GUEST_CUTOFF] ==
            expected_source[GUEST_CUTOFF] and guest_cutoff['before'] != guest_cutoff['after'],
            'Guest cutoff predecessor differs')
    require(stat.S_IMODE((ROOT / GUEST_CUTOFF).lstat().st_mode) == 0o644,
            'Installed guest cutoff owner mode differs')
    installed[GUEST_CUTOFF] = expected_source[GUEST_CUTOFF] = guest_cutoff['after']
    preimages.setdefault(GUEST_CUTOFF, (raw_guest_cutoff, 0o644))
    require(previous.digest(expected_source) == GUEST_CUTOFF_SOURCE_SHA256,
            'Guest cutoff source transition differs')

    store_identity = binding['store_platform_identity_transition']
    require(set(store_identity) == {'sourceBefore', 'sourceAfter', 'changes'} and
            store_identity['sourceBefore'] == GUEST_CUTOFF_SOURCE_SHA256 and
            set(store_identity['changes']) == STORE_PLATFORM_IDENTITY_INPUTS,
            'Store platform identity transition roster differs')
    for name, change in store_identity['changes'].items():
        raw = read_predecessor_member(HERE / (STORE_PLATFORM_IDENTITY_PREFIX + name))
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] == expected_source[name] and
                change['before'] != change['after'], 'Store platform identity predecessor differs: ' + name)
        require(stat.S_IMODE((ROOT / name).lstat().st_mode) == 0o644,
                'Installed store platform identity mode differs: ' + name)
        installed[name] = expected_source[name] = change['after']
        preimages.setdefault(name, (raw, 0o644))
    require(previous.digest(expected_source) == store_identity['sourceAfter'] == STORE_PLATFORM_IDENTITY_SOURCE_SHA256,
            'Store platform identity source transition differs')

    worker_swift = binding['worker_swift_probe_transition']
    raw_worker_swift = read_predecessor_member(HERE / WORKER_SWIFT_PROBE_PREIMAGE)
    require(set(worker_swift) == {'sourceBefore', 'before', 'after'} and
            worker_swift['sourceBefore'] == STORE_PLATFORM_IDENTITY_SOURCE_SHA256 and
            worker_swift['before'] == previous.row(raw_worker_swift) == installed[WORKER_SWIFT_PROBE] ==
            expected_source[WORKER_SWIFT_PROBE] and worker_swift['before'] != worker_swift['after'],
            'Worker Swift probe predecessor differs')
    require(stat.S_IMODE((ROOT / WORKER_SWIFT_PROBE).lstat().st_mode) == 0o644,
            'Installed worker Swift probe owner mode differs')
    installed[WORKER_SWIFT_PROBE] = expected_source[WORKER_SWIFT_PROBE] = worker_swift['after']
    preimages.setdefault(WORKER_SWIFT_PROBE, (raw_worker_swift, 0o644))
    require(len(expected_source) == 150 and previous.digest(expected_source) == WORKER_SWIFT_PROBE_SOURCE_SHA256,
            'Worker Swift probe source transition differs')

    android_output = binding['android_retained_output_transition']
    require(set(android_output) == {'sourceBefore', 'changes', 'addition'} and
            android_output['sourceBefore'] == WORKER_SWIFT_PROBE_SOURCE_SHA256 and
            set(android_output['changes']) == ANDROID_OUTPUT_CHANGES and
            set(android_output['addition']) == {ANDROID_OUTPUT_ADDITION},
            'Android retained output transition roster differs')
    for name, change in android_output['changes'].items():
        raw = android_output_preimages[name]
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] == expected_source[name] and
                change['before'] != change['after'],
                'Android retained output predecessor differs: ' + name)
        installed[name] = expected_source[name] = change['after']
        preimages.setdefault(name, (raw, 0o644))
    require(ANDROID_OUTPUT_ADDITION not in installed, 'Android retained output addition already exists')
    installed.update(android_output['addition'])
    expected_source.update(android_output['addition'])
    for name in ANDROID_OUTPUT_CHANGES | {ANDROID_OUTPUT_ADDITION}:
        require(stat.S_ISREG((ROOT / name).lstat().st_mode) and
                stat.S_IMODE((ROOT / name).lstat().st_mode) == 0o644,
                'Android retained output owner mode differs: ' + name)
    require(len(expected_source) == 151 and previous.digest(expected_source) == ANDROID_OUTPUT_SOURCE_SHA256,
            'Android retained output source transition differs')

    correction = binding['android_retained_output_correction_transition']
    require(set(correction) == {'sourceBefore', 'sourceAfter', 'changes'} and
            correction['sourceBefore'] == ANDROID_OUTPUT_SOURCE_SHA256 and
            set(correction['changes']) == ANDROID_OUTPUT_CORRECTION_CHANGES | {ANDROID_OUTPUT_CORRECTION_TEST},
            'Android retained output correction transition roster differs')
    for name, change in correction['changes'].items():
        raw = read_predecessor_member(HERE / (ANDROID_OUTPUT_CORRECTION_PREFIX + name))
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] and
                change['before'] != change['after'],
                'Android retained output correction predecessor differs: ' + name)
        installed[name] = change['after']
        if name in ANDROID_OUTPUT_CORRECTION_CHANGES:
            require(expected_source[name] == change['before'], 'Android correction source preimage differs: ' + name)
            expected_source[name] = change['after']
        preimages.setdefault(name, (raw, 0o644))
    require(len(expected_source) == 151 and
            previous.digest(expected_source) == correction['sourceAfter'] == ANDROID_OUTPUT_CORRECTION_SOURCE_SHA256,
            'Android retained output correction source transition differs')

    managed_android = binding['managed_android_retained_transition']
    require(set(managed_android) == {'sourceBefore', 'sourceAfter', 'changes'} and
            managed_android['sourceBefore'] == ANDROID_OUTPUT_CORRECTION_SOURCE_SHA256 and
            set(managed_android['changes']) == MANAGED_ANDROID_CHANGES,
            'Managed Android retained output transition roster differs')
    for name, change in managed_android['changes'].items():
        raw = read_predecessor_member(HERE / (MANAGED_ANDROID_PREFIX + name))
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] == expected_source[name] and
                change['before'] != change['after'],
                'Managed Android retained output predecessor differs: ' + name)
        installed[name] = expected_source[name] = change['after']
        preimages.setdefault(name, (raw, 0o644))
    require(previous.digest(expected_source) == managed_android['sourceAfter'] == MANAGED_ANDROID_SOURCE_SHA256,
            'Managed Android retained output source transition differs')

    for name, change in pair25['changes'].items():
        raw = pair25_preimages[name]
        require(set(change) == {'before', 'after', 'mode'} and
                change['before'] == previous.row(raw) == installed[name] and
                change['before'] != change['after'] and
                change['mode'] == 0o644 == stat.S_IMODE((ROOT / name).lstat().st_mode),
                'Pair25 predecessor owner or installed mode differs: ' + name)
        installed[name] = change['after']
        if name in PAIR25_SOURCE_CHANGES:
            require(expected_source[name] == change['before'], 'Pair25 source preimage differs: ' + name)
            expected_source[name] = change['after']
        preimages.setdefault(name, (raw, change['mode']))
    require(previous.digest(expected_source) == pair25['sourceAfter'] == PAIR25_SOURCE_SHA256,
            'Pair25 source transition differs')

    swift_version = binding['swift_version_transition']
    require(set(swift_version) == {'sourceBefore', 'sourceAfter', 'changes'} and
            swift_version['sourceBefore'] == PAIR25_SOURCE_SHA256 and
            set(swift_version['changes']) == SWIFT_VERSION_CHANGES, 'Swift version change roster differs')
    for name, change in swift_version['changes'].items():
        raw = read_predecessor_member(HERE / (SWIFT_VERSION_PREFIX + name))
        require(set(change) == {'before', 'after'} and
                change['before'] == previous.row(raw) == installed[name] and
                change['before'] != change['after'] and
                stat.S_IMODE((ROOT / name).lstat().st_mode) == 0o644,
                'Swift version predecessor or installed mode differs: ' + name)
        installed[name] = change['after']
        if name in SWIFT_VERSION_SOURCE_CHANGES:
            require(expected_source[name] == change['before'], 'Swift version source preimage differs: ' + name)
            expected_source[name] = change['after']
        preimages.setdefault(name, (raw, 0o644))
    require(current == expected_source and len(current) == 151 and binding['source'] == {
        'count': len(current), 'manifest': 'current-source-inputs.json', 'sha256': swift_version['sourceAfter'],
    } and previous.digest(current) == swift_version['sourceAfter'], 'Swift version source transition differs')

    cli_test = binding['cli_nonregular_input_test_transition']
    raw = read_predecessor_member(HERE / CLI_NONREGULAR_INPUT_TEST_PREIMAGE)
    require(set(cli_test) == {'before', 'after'} and CLI_NONREGULAR_INPUT_TEST not in current and
            cli_test['before'] == previous.row(raw) == installed[CLI_NONREGULAR_INPUT_TEST] ==
            historical[CLI_NONREGULAR_INPUT_TEST] and cli_test['before'] != cli_test['after'],
            'CLI nonregular input test predecessor differs')
    require(stat.S_IMODE((ROOT / CLI_NONREGULAR_INPUT_TEST).lstat().st_mode) == 0o644,
            'Installed CLI nonregular input test mode differs')
    installed[CLI_NONREGULAR_INPUT_TEST] = cli_test['after']
    preimages.setdefault(CLI_NONREGULAR_INPUT_TEST, (raw, 0o644))

    overflow_test = binding['signed_apple_overflow_test_transition']
    raw = read_predecessor_member(HERE / SIGNED_APPLE_OVERFLOW_TEST_PREIMAGE)
    require(set(overflow_test) == {'before', 'after'} and SIGNED_APPLE_OVERFLOW_TEST not in current and
            overflow_test['before'] == previous.row(raw) == installed[SIGNED_APPLE_OVERFLOW_TEST] ==
            historical[SIGNED_APPLE_OVERFLOW_TEST] and overflow_test['before'] != overflow_test['after'],
            'Signed Apple overflow test predecessor differs')
    require(stat.S_IMODE((ROOT / SIGNED_APPLE_OVERFLOW_TEST).lstat().st_mode) == 0o644,
            'Installed signed Apple overflow test mode differs')
    installed[SIGNED_APPLE_OVERFLOW_TEST] = overflow_test['after']
    preimages.setdefault(SIGNED_APPLE_OVERFLOW_TEST, (raw, 0o644))

    sparse_test = binding['sparse_checkout_test_transition']
    raw = read_predecessor_member(HERE / SPARSE_CHECKOUT_TEST_PREIMAGE)
    require(set(sparse_test) == {'before', 'after'} and SPARSE_CHECKOUT_TEST not in current and
            sparse_test['before'] == previous.row(raw) == installed[SPARSE_CHECKOUT_TEST] and
            sparse_test['before'] != sparse_test['after'], 'Sparse checkout test predecessor differs')
    require(stat.S_IMODE((ROOT / SPARSE_CHECKOUT_TEST).lstat().st_mode) == 0o644,
            'Installed sparse checkout test mode differs')
    installed[SPARSE_CHECKOUT_TEST] = sparse_test['after']
    preimages.setdefault(SPARSE_CHECKOUT_TEST, (raw, 0o644))

    previous.check_rows(ROOT, installed)
    for name, change in halt['changes'].items():
        require(stat.S_IMODE((ROOT / name).lstat().st_mode) == change['mode'],
                'Installed halt CLI owner mode differs: ' + name)
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
    adapter_files = {**pair22['adapter_files'], RENDERER: pair23_source['native/android/' + RENDERER]}
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
    expected_pair24 = {**expected_profile, 'id': 'mixer.android-source-pair.24', 'adapter_files': adapter_files,
                       'adapter_compatibility_sha256': previous.digest(adapter_files)}
    require(pair24['profileAfter'] == expected_pair24, 'Archive Pair24 starter profile differs')
    require(adapter_files[RENDERER] == pair25['changes']['native/android/' + RENDERER]['before'],
            'Pair24 renderer preimage differs')
    adapter_files = {**adapter_files, RENDERER: current['native/android/' + RENDERER]}
    expected_current = {**expected_pair24, 'id': 'mixer.android-source-pair.25', 'adapter_files': adapter_files,
                        'adapter_compatibility_sha256': previous.digest(adapter_files)}
    require(pair25['profileAfter'] == expected_current == profile and
            previous.profile_summary(profile) == binding['profile'],
            'Archive Pair25 renderer profile differs')
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
            'predecessor_swift_version_sha256': binding['swift_version_transition']['sourceBefore'],
            'predecessor_pair24_source151_sha256': binding['pair25_transition']['sourceBefore'],
            'predecessor_managed_android_retained_sha256': binding['managed_android_retained_transition']['sourceBefore'],
            'predecessor_android_retained_output_correction_sha256': binding['android_retained_output_correction_transition']['sourceBefore'],
            'predecessor_android_retained_output_sha256': binding['android_retained_output_transition']['sourceBefore'],
            'predecessor_guest_cutoff_sha256': binding['guest_cutoff_transition']['sourceBefore'],
            'predecessor_capability_identity_sha256': binding['capability_identity_transition']['sourceBefore'],
            'predecessor_apple_synchronous_text_sha256': binding['apple_synchronous_text_transition']['sourceBefore'],
            'predecessor_apple_section_accessibility_sha256': binding['apple_section_accessibility_transition']['sourceBefore'],
            'predecessor_source150_sha256': binding['halt_cli_transition']['sourceBefore'],
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
