#!/usr/bin/env python3
"""Prospective job binding; delegate the unchanged sealed compiler/fixture policy."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HISTORICAL = ROOT / 'verification/envelope-rust-1991-default-ci-adoption'
WORKFLOW = ROOT / '.github/workflows/verify.yml'
CALLER_BEFORE = "          swift test --package-path cli\n"
CALLER_AFTER = "          MIXER_CLI_HOST_ROOT=\"$RUNNER_TEMP/cli-host-${{ github.job }}-${{ github.run_id }}-${{ github.run_attempt }}\"\n          python3 -I -B -S scripts/ci/prepare-cli-host-tests.py \\\n            --toolchain-receipt \"$RUNNER_TEMP/apple-toolchain.json\" \\\n            --output \"$MIXER_CLI_HOST_ROOT\"\n          (\n            source \"$MIXER_CLI_HOST_ROOT/environment.sh\"\n            swift build --package-path cli --product mixer -j 2\n            MIXER_STORE_CLI_BIN_DIR=\"$(swift build --package-path cli --product mixer -j 2 --show-bin-path)\"\n            test -x \"$MIXER_STORE_CLI_BIN_DIR/mixer\"\n            MIXER_STORE_TEST_CLI=\"$MIXER_STORE_CLI_BIN_DIR/mixer\" swift test --package-path cli -j 2\n          )\n"

def load():
    spec = importlib.util.spec_from_file_location('sealed_envelope_caller_base', HISTORICAL / 'adopt_envelope.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



SDK_FIXTURE_TRANSITION = json.loads("{\"schema\":1,\"type\":\"EXACT_SDK_READY_INPUT_AND_FULL_CI_FIXTURE_SUCCESSOR\",\"scope\":\"exact seven accepted SDK/capability afterimages and independently accepted full-CI fixture; source/caller composition only\",\"predecessor\":{\"source113\":\"0647086ea204e5a3c9b89f11303df933cd426fb5ff81cb001cce0ca1ed493d71\",\"sourceCount\":113,\"bootstrap\":{\"bytes\":18124,\"sha256\":\"365f94581903eeec3978b2c1e905f334bbf9c7ca04ae4a1f4889a9d143fb4305\"},\"callerAuthority\":{\"bytes\":1666,\"sha256\":\"ea6720c24905f48167eee34e977039e1a66835c75e9e97b36e539a6348bb0a3c\"},\"runtimeSeal\":{\"bytes\":4466,\"sha256\":\"fd4dff20b830a3b9734107cb1ccd727c6b281bdeb04d84c5df034fe663a8d412\"},\"runtimeMembers\":28},\"current\":{\"source113\":\"1b7562e0f209d973ae5a1b0bf96e9545c7c5d333cfc44da0b0538a8e5cfcf854\",\"sourceCount\":113,\"bootstrap\":{\"bytes\":18124,\"sha256\":\"81cfebd96cca0bbae8bb503842f2216c62d6208fdbbd0f4bd5821923a17f3b89\"},\"callerAuthority\":{\"bytes\":1666,\"sha256\":\"2cff3508e0c461a7cefddcd773cd58d5df9e74e0c1ff1a3248ff27eb56464178\"}},\"sdk\":[{\"path\":\"capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartControl.swift\",\"before\":{\"bytes\":16078,\"sha256\":\"68bdac5bbe63a48599aec58186242a58515b5dd5fa736c01d3305e6d882756e6\"},\"after\":{\"bytes\":16252,\"sha256\":\"786cff00121906ddc6ada800526c84ac6be3375cf4406998a4a5e5351000eb7e\"},\"owning113\":false},{\"path\":\"capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIPresentation.swift\",\"before\":{\"bytes\":16789,\"sha256\":\"2fe7404fa6a27e59a59d4c91bfd6f250156a0666ad91da50a36c8eb2578577b7\"},\"after\":{\"bytes\":20283,\"sha256\":\"2cbffaba4792ad78b22250a4810474149b9c595241eae872400f68650452110b\"},\"owning113\":false},{\"path\":\"capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift\",\"before\":{\"bytes\":6313,\"sha256\":\"b3295dc6d1f97b5f13bc55b8038483814c66f66c262983fda32607da1ee4e29f\"},\"after\":{\"bytes\":6379,\"sha256\":\"796dc7e4167aea60a1e77150574802ebadea28b2c831478b91506a39cec07b92\"},\"owning113\":false},{\"path\":\"capability-activation/Tests/MixerCapabilityActivationTests/GuestUIReadyInputTests.swift\",\"before\":null,\"after\":{\"bytes\":25403,\"sha256\":\"549109d75a25ce46c0a44587710772a1d9e1038262d0f4071973a89cacc410f1\"},\"owning113\":false},{\"path\":\"capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedRuntimeTests.swift\",\"before\":{\"bytes\":15600,\"sha256\":\"37846a30df32bbc56ae909e99f4fb504cc3e7aac0c91c59e917482d175117bcf\"},\"after\":{\"bytes\":20041,\"sha256\":\"0af2d69a886d53c01c3923138c11d634421c1b4e5be43932717a4e75d99071b9\"},\"owning113\":false},{\"path\":\"sdk/Sources/MixerGuest/GuestUIExchangeV1.swift\",\"before\":{\"bytes\":20951,\"sha256\":\"54665138a14e94292eddb838140feaf9dae673134aecc391dbb02b046e1b35a4\"},\"after\":{\"bytes\":23389,\"sha256\":\"ab3b988e83d24348224353c043a1b2697219d9410899c883725e483f93aac42e\"},\"owning113\":true},{\"path\":\"sdk/Sources/MixerGuest/GuestUIProtocolV1.swift\",\"before\":{\"bytes\":5302,\"sha256\":\"8192ec89236e2b799a25b05eba3913af5fea6a73e96129335f28546c7029f277\"},\"after\":{\"bytes\":5674,\"sha256\":\"e60b6e3ee4e9ab378fef4758bd5342e56ff049f976802400f08e88a75ecd2461\"},\"owning113\":true}],\"sdkPatch\":{\"sha256\":\"3b55f27e6b0358e11a1fa21f7fe77263a038fe1129c9f4dc2b1184b5c35fefc1\"},\"fixture\":{\"path\":\"scripts/ci/tests/test_android_generated_java_runner.py\",\"before\":{\"bytes\":59496,\"sha256\":\"492c7a8539b1cb52cc55b1a45ca93e9042670840b45132d2935b406bbe2bf1e9\"},\"after\":{\"bytes\":63620,\"sha256\":\"04c22f2170953fdb303de18b8d7bd83c35652c07becaf980f85f635e2a212b04\"},\"patch\":{\"bytes\":5844,\"sha256\":\"bf8831eb896ad22ed87a057a57c76d8f2685ea2877a51bb87d3dba7c9b16a686\"},\"outsideSource113\":true},\"reviews\":[{\"member\":\"sdk-ready-input-review.json\",\"identity\":{\"bytes\":4190,\"sha256\":\"d5a62c0ae7edf53135e7a4c5279ff5a6f154d3d6c88dac6b4efcf592cf258532\"},\"semantic\":{\"decision\":\"ACCEPT_EXACT_SDK_READY_INPUT_OWNER_RETIREMENT_SOURCE_HOST\",\"scope\":\"Exact seven R6 afterimages and exact existing R6 debug macOS host binaries only\",\"sourceDecision\":\"CLEAN_EXACT_SOURCE_INSPECTION\",\"exactSubject\":{\"producer\":\"/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/capability-foreign-callback-invalidation-fix-r6\",\"fullPatchSHA256\":\"3b55f27e6b0358e11a1fa21f7fe77263a038fe1129c9f4dc2b1184b5c35fefc1\",\"incrementSHA256\":\"a52daeda76df442bc8a111c4af6badb5e0ad52703075d2b342a805abd755b32b\",\"R4PatchSHA256\":\"2cd9dc04fae50febd70465ffa82253ae9b96aea434ae4294eb3a6fe157acb803\",\"XCTestSHA256\":\"838f95cf9be1c0ad361121ac9f1da46b9184aa3d4407bbf1b970a8acdf965fb5\",\"SwiftTestingSHA256\":\"d20f4406eb46417b3734fca118eb515b961efb343f7ac0ff49e38472f9d47c07\"},\"canonicalAdoptionAuthorized\":false,\"historicalHostedCause\":\"UNPROVEN\",\"primaryProviderEscapedAbsenceProven\":false}},{\"member\":\"full-ci-fixture-review.json\",\"identity\":{\"bytes\":7576,\"sha256\":\"3ad9c4f36df6509b9ffe88a6f16315065b974372d57b2bf218f643d4ed46de31\"},\"semantic\":{\"verdict\":\"ACCEPT_EXACT_FULL_CI_CUSTODY_FIXTURE_SOURCE_HOST\",\"gate\":\"EXACT_FULL_CI_CUSTODY_FIXTURE_SOURCE_HOST\",\"scope\":\"Exact fixture source and focused host behavior only. Root typed binding and all subsequent complete-suite/integration gates remain pending.\",\"candidate\":{\"path\":\"scripts/ci/tests/test_android_generated_java_runner.py\",\"bytes\":63620,\"sha256\":\"04c22f2170953fdb303de18b8d7bd83c35652c07becaf980f85f635e2a212b04\"},\"parent\":{\"bytes\":59496,\"sha256\":\"492c7a8539b1cb52cc55b1a45ca93e9042670840b45132d2935b406bbe2bf1e9\"},\"patch\":{\"path\":\"test-only.patch\",\"bytes\":5844,\"sha256\":\"bf8831eb896ad22ed87a057a57c76d8f2685ea2877a51bb87d3dba7c9b16a686\",\"exactGeneratedDiffVerifiedInBothModes\":true},\"checker\":{\"path\":\"scripts/ci/check-android-generated-java.py\",\"bytes\":65563,\"sha256\":\"917750f95ca0d02780324a9ef255ef0426eab79ee84ed4f330990d43a9026866\"},\"source113\":{\"count\":113,\"sha256\":\"0647086ea204e5a3c9b89f11303df933cd426fb5ff81cb001cce0ca1ed493d71\"},\"profile\":{\"id\":\"mixer.android-source-pair.10\",\"sdkCount\":24,\"adapterCount\":25,\"javaCount\":19,\"sdkDigest\":\"dd67ffdb0458b2a546dcac8660e039364668f15c3a270ab417db7e7c2181ce47\",\"adapterDigest\":\"b6d5d6ae71227373cbffa862cc691aaa52f4ea81b8e4f85cf74ee612c5f15a3e\"},\"namedUnlock\":\"Root minimal typed fixture-binding followup preserving historical49ef review/current ea6720 caller authority; then separately admitted fresh complete affected units and consumers/CI after exact bindings match.\"}}],\"profile\":{\"id\":\"mixer.android-source-pair.10\",\"sdk_count\":24,\"sdk_sha256\":\"dd67ffdb0458b2a546dcac8660e039364668f15c3a270ab417db7e7c2181ce47\",\"adapter_count\":25,\"adapter_sha256\":\"b6d5d6ae71227373cbffa862cc691aaa52f4ea81b8e4f85cf74ee612c5f15a3e\",\"java_sources\":19},\"combinedAccepted\":false,\"canonicalApplied\":false,\"actualSixConsumers\":false,\"completeAffectedUnits\":false,\"ordinaryCI\":false,\"compilerPass\":false,\"nativePass\":false,\"runtimePass\":false,\"releaseQualified\":false,\"gaPass\":false,\"historicalHoldsReleased\":false,\"wholeCopiedSDKDigestRecreationRequired\":true}")

def same_json(actual, expected):
    """Match a closed JSON literal without Python boolean/number aliases."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return (all(type(key) is str for key in actual)
                and actual.keys() == expected.keys()
                and all(same_json(actual[key], value) for key, value in expected.items()))
    if type(expected) is list:
        return len(actual) == len(expected) and all(same_json(a, e) for a, e in zip(actual, expected))
    if type(expected) is bool or expected is None:
        return actual is expected
    if type(expected) is float:
        return math.isfinite(actual) and math.isfinite(expected) and actual == expected
    return type(expected) in (str, int) and actual == expected


APPLE_ACCESSIBILITY_TRANSITION = json.loads("{\"schema\":1,\"type\":\"EXACT_APPLE_ACCESSIBILITY_CONTAINER_SOURCE\",\"path\":\"sdk/Sources/MixerApple/MixerNativeView.swift\",\"before\":{\"bytes\":7611,\"sha256\":\"6f8ddefbf8be4a8a9aaf149e18afe09164de3a1f76c967263c3afba2dc5826df\"},\"after\":{\"bytes\":7934,\"sha256\":\"184547e4e5e11c336b0e9e968bd94eb4607eb1dca08bbfe79caa9abacd8c4d8f\"},\"sourceBefore\":\"1b7562e0f209d973ae5a1b0bf96e9545c7c5d333cfc44da0b0538a8e5cfcf854\",\"sourceAfter\":\"30344a0c5b00023cbc27fc793e67db7dec85d72a5aef0cd76573e2512f0b2ef8\",\"review\":{\"member\":\"apple-accessibility-review.md\",\"bytes\":4100,\"sha256\":\"e0376ab4d853ab934a87c1851cecdccb609deaf774b9896a9c7807adecdc785d\"},\"scope\":\"reviewed iOS headless FieldLog child-identity and save/reopen development fix; no qualification transfer\"}")


def apple_accessibility_successor(base, binding, actual, owner):
    transition = APPLE_ACCESSIBILITY_TRANSITION
    base.need(same_json(binding.get("apple_accessibility_transition"), transition), "Apple accessibility transition differs")
    base.need(actual.get(transition["path"]) == transition["after"] and owner.source_digest(actual) == transition["sourceAfter"], "Apple accessibility current source differs")
    review = base.regular(HERE / transition["review"]["member"]).read_bytes()
    base.need({"bytes":len(review), "sha256":hashlib.sha256(review).hexdigest()} == {k:transition["review"][k] for k in ("bytes", "sha256")}, "Apple accessibility review identity differs")
    predecessor = dict(actual)
    predecessor[transition["path"]] = transition["before"]
    base.need(owner.source_digest(predecessor) == transition["sourceBefore"], "Apple accessibility predecessor differs")
    return predecessor


CI_TEMP_ROOT_FIXTURE = json.loads("{\"schema\":1,\"path\":\"scripts/ci/tests/test_android_generated_java_runner.py\",\"before\":{\"bytes\":63620,\"sha256\":\"04c22f2170953fdb303de18b8d7bd83c35652c07becaf980f85f635e2a212b04\"},\"after\":{\"bytes\":63641,\"sha256\":\"7583cf6ca11a669eadf21be4a3e949218b633b1938819fdb4799e0a83e431b18\"},\"scope\":\"test-only: canonicalize the owned TemporaryDirectory path before entering the private receipt writer boundary; production checker unchanged\"}")


def sdk_fixture_successor(base, binding, actual, owner):
    transition = SDK_FIXTURE_TRANSITION
    base.need(same_json(binding.get('sdk_fixture_transition'), transition), 'SDK fixture typed transition differs')
    predecessor = base.regular(HERE / 'predecessor-runtime-seal.json').read_bytes()
    base.need({'bytes':len(predecessor),'sha256':hashlib.sha256(predecessor).hexdigest()} == transition['predecessor']['runtimeSeal'], 'Frozen predecessor runtime identity differs')
    frozen_seal = json.loads(predecessor, object_pairs_hook=base.unique_object)
    base.need(frozen_seal['member_count'] == 28 and frozen_seal['tree_sha256'] == base.tree(frozen_seal['members']), 'Frozen predecessor runtime closure differs')
    caller_row = next(r for r in frozen_seal['members'] if r['path'] == 'caller-inputs.json')
    base.need({k:caller_row[k] for k in ('bytes','sha256')} == transition['predecessor']['callerAuthority'], 'Frozen predecessor caller authority differs')
    for spec in transition['reviews']:
        raw = base.regular(HERE / spec['member']).read_bytes()
        base.need({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} == spec['identity'], 'Accepted SDK fixture raw review identity differs: ' + spec['member'])
        review = json.loads(raw, object_pairs_hook=base.unique_object)
        base.need(all(review.get(k) == v for k,v in spec['semantic'].items()), 'Accepted SDK fixture review semantic scope differs')
    predecessor_inputs = dict(actual)
    for row in transition['sdk']:
        raw = base.regular(ROOT / row['path']).read_bytes()
        base.need({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} == row['after'], 'Accepted SDK afterimage differs: ' + row['path'])
        if row['owning113']:
            base.need(actual.get(row['path']) == row['after'] and row['before'] is not None, 'SDK owning transition differs')
            predecessor_inputs[row['path']] = row['before']
        else:
            base.need(row['path'] not in actual, 'Capability input entered source113')
    base.need(len(actual) == 113 and owner.source_digest(actual) == transition['current']['source113'], 'SDK current owning digest differs')
    base.need(owner.source_digest(predecessor_inputs) == transition['predecessor']['source113'], 'SDK reverse Guest2 predecessor differs')
    fixture = transition['fixture']
    base.need(same_json(binding.get('ci_temp_root_transition'), CI_TEMP_ROOT_FIXTURE)
              and fixture['path'] == CI_TEMP_ROOT_FIXTURE['path']
              and fixture['after'] == CI_TEMP_ROOT_FIXTURE['before'], 'Owned temp-root fixture transition differs')
    raw = base.regular(ROOT / fixture['path']).read_bytes()
    base.need({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} == CI_TEMP_ROOT_FIXTURE['after'] and fixture['path'] not in actual, 'Accepted full CI fixture afterimage differs')
    return predecessor_inputs


def bind():
    base = load()
    historical_verify = base.verify
    def verify(installed=False):
        proof = historical_verify(False)
        seal = json.loads(base.regular(HERE / 'seal.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(HERE, seal['members'])
        base.need(seal['member_count'] == 32 and [r['path'] for r in seal['members']] == ["accepted-swift-job.yml","adopt_envelope.py","apple-accessibility-review.md","baseline-runtime-seal.json","binding.json","caller-inputs.json","command-lifetime-review.json","current-swift-job.yml","current-verify.yml","failure-current.json","failure-evidence.json","full-ci-fixture-review.json","full.patch","historical-closure.json","identity-deltas.json","incremental.patch","inspection-digest-review.json","inspection-review.json","job-changes.json","metadata_guard.py","predecessor-runtime-seal.json","runner-fixture-review.json","sdk-ready-input-review.json","source-inputs.json","swift-job.yml","test_binding.py","test_combined.py","test_ownership.py","test_rebind.py","test_source113.py","verify.yml.candidate","workflow.patch"] and seal['tree_sha256'] == base.tree(seal['members']), 'Successor seal differs')
        ignored = {'control-scratch', '__pycache__'}
        base.need(not any(p.is_symlink() for p in HERE.rglob('*') if p.relative_to(HERE).parts[0] not in ignored), 'Successor shipping symlink forbidden')
        observed = sorted(p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ignored and p.relative_to(HERE).as_posix() != 'seal.json')
        base.need(observed == [r['path'] for r in seal['members']], 'Successor shipping closure differs')
        history = json.loads(base.regular(HERE / 'historical-closure.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, history)
        prior = HERE.parent / 'source113-sparse-closure-fix-r2'
        prior_seal = json.loads(base.regular(prior / 'seal.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(prior, prior_seal['members'])
        base.need(prior_seal['member_count'] == 18 and prior_seal['tree_sha256'] == base.tree(prior_seal['members']), 'Historical source113 seal differs')
        frozen = json.loads(base.regular(HERE / 'source-inputs.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, [dict(path=p, **r) for p,r in sorted(frozen.items())])
        owner = base.module_at('combined_source113_owner', ROOT / 'scripts/ci/check-android-generated-java.py')
        profile = owner.load_profile(ROOT)
        actual = owner.source_inputs(profile)
        base.need(actual == frozen, 'Current owning source closure differs')
        binding = json.loads(base.regular(HERE / 'binding.json').read_bytes(), object_pairs_hook=base.unique_object)
        base.need(same_json(binding.get('schema'), 1), 'Binding schema differs')
        digest = owner.source_digest(actual)
        raw_review = base.regular(HERE / 'inspection-review.json').read_bytes()
        base.need(hashlib.sha256(raw_review).hexdigest() == '6b51eafe93f29e05c9bf527a5d39625e8a2cffbcdfd1fbb4799ac80adb7a3de6', 'Accepted R3 raw review hash differs')
        review = json.loads(raw_review, object_pairs_hook=base.unique_object)
        accepted = review.get('candidate', {})
        baseline_digest = '524e7e2934c34501ff23dae13e448cc13ae53a874d78e86fefeba556e2a65292'
        base.need(review.get('verdict') == 'ACCEPT'
                  and review.get('scope') == 'EXACT_R5_CHECKER_REAL_TOOL_TMP_SOURCE_PROTOCOL_ONLY'
                  and accepted == {'source113Proposed': baseline_digest,
                                   'patchSHA256': 'da94deb88a987e294c7ac830ecae32dd060e2a25035001ae92977e2a91236b04',
                                   'checkerSHA256': '6103a13c065181ccd5dd76d6c6ee7d827dd091354b1aed3eea11887895bc2822'}, 'Accepted R3 inspection identity differs')
        base.need(binding.get('upstream_inspection') == {'member':'inspection-review.json', 'sha256':hashlib.sha256(raw_review).hexdigest(), 'source113':baseline_digest, 'patchSHA256':accepted['patchSHA256'], 'checkerSHA256':accepted['checkerSHA256'], 'scope':'accepted R5 real-tool temporary-directory source protocol only; no qualification transfer'}, 'Upstream inspection binding differs')
        transition = json.loads("{\"schema\":1,\"type\":\"EXACT_COMBINED_CLI_INSPECTION_LIFETIME_FIXTURE_SOURCE_CALLER\",\"baseline_source113\":\"524e7e2934c34501ff23dae13e448cc13ae53a874d78e86fefeba556e2a65292\",\"current_source113\":\"0647086ea204e5a3c9b89f11303df933cd426fb5ff81cb001cce0ca1ed493d71\",\"source_count\":113,\"owning_changes\":[{\"path\":\"cli/Sources/MixerBuild/Resources/android-build.py\",\"preimage\":{\"bytes\":30638,\"sha256\":\"df87f377dee8a167f559eb43ea22d15e692f299dc715aff74454ea5747573cf2\"},\"candidate\":{\"bytes\":32563,\"sha256\":\"7c1e092c8d2123b9ee4868db1146349fa2a15e8d16463f546337bb71af6aee55\"}},{\"path\":\"scripts/ci/check-android-generated-java.py\",\"preimage\":{\"bytes\":63363,\"sha256\":\"6103a13c065181ccd5dd76d6c6ee7d827dd091354b1aed3eea11887895bc2822\"},\"candidate\":{\"bytes\":65563,\"sha256\":\"917750f95ca0d02780324a9ef255ef0426eab79ee84ed4f330990d43a9026866\"}}],\"fixture\":{\"path\":\"scripts/ci/tests/test_android_generated_java_runner.py\",\"preimage\":{\"bytes\":50168,\"sha256\":\"9bccedc54d7590a8190142e5fa63e6370efb11e8b0d2869aef46c6a6cc47bc91\"},\"candidate\":{\"bytes\":59496,\"sha256\":\"492c7a8539b1cb52cc55b1a45ca93e9042670840b45132d2935b406bbe2bf1e9\"},\"outside_source113\":true},\"reviews\":[{\"member\":\"inspection-digest-review.json\",\"sha256\":\"059cfcea9fc7d1d63bf3812ce4ca2950fb978665b348f92c90f255e301f90055\",\"scope\":\"ACCEPT_EXACT_OPERATION_SCOPED_ANDROID_INSPECTION_DIGEST_SOURCE\"},{\"member\":\"command-lifetime-review.json\",\"sha256\":\"cf75c00076de578dd0ded073a6c2aff9c8e0986c7f41c84ff088272f3038c233\",\"scope\":\"EXACT_OUTER_COMMAND_LIFETIME_SOURCE_HOST\"},{\"member\":\"runner-fixture-review.json\",\"sha256\":\"49ef08e13d303f42dc6d933f92a166a85e1bde16ed28efce30ceeac0afccd193\",\"scope\":\"SAFE_CI_SELECTION_NEGATIVE_CONTROL_FIXTURE\"}],\"profile\":{\"id\":\"mixer.android-source-pair.10\",\"sdk_count\":24,\"sdk_sha256\":\"dd67ffdb0458b2a546dcac8660e039364668f15c3a270ab417db7e7c2181ce47\",\"adapter_count\":25,\"adapter_sha256\":\"b6d5d6ae71227373cbffa862cc691aaa52f4ea81b8e4f85cf74ee612c5f15a3e\",\"java_sources\":19},\"baseline_runtime_seal\":{\"bytes\":3815,\"sha256\":\"a4037e0c171fdac8ca003971aeba2d23c65f37c54349e6529fc6b3e176646626\"},\"combinedAccepted\":false,\"canonicalApplied\":false,\"actualSixConsumers\":false,\"hostedTimeoutResolved\":false,\"runtimePass\":false,\"gaPass\":false}")
        base.need(same_json(binding.get('combined_cli_transition'), transition), 'Combined transition binding differs')
        predecessor_inputs = sdk_fixture_successor(base, binding, apple_accessibility_successor(base, binding, actual, owner), owner)
        baseline_inputs = dict(predecessor_inputs)
        base.need(len(actual) == 113 and set(actual) == set(frozen), 'Combined owning roster differs')
        for change in transition['owning_changes']:
            base.need(actual.get(change['path']) == change['candidate'], 'Combined candidate owning row differs')
            baseline_inputs[change['path']] = change['preimage']
        base.need(owner.source_digest(baseline_inputs) == baseline_digest, 'Combined two-row baseline differs')
        base.need(owner.source_digest(predecessor_inputs) == transition['current_source113'], 'Combined current source differs')
        baseline_seal = base.regular(HERE / 'baseline-runtime-seal.json').read_bytes()
        base.need({'bytes':len(baseline_seal), 'sha256':hashlib.sha256(baseline_seal).hexdigest()} == transition['baseline_runtime_seal']
                  and json.loads(baseline_seal)['member_count'] == 24, 'Baseline runtime seal history differs')
        reviews = {}
        for spec in transition['reviews']:
            raw = base.regular(HERE / spec['member']).read_bytes()
            base.need(hashlib.sha256(raw).hexdigest() == spec['sha256'], 'Accepted combined raw review hash differs: ' + spec['member'])
            reviews[spec['member']] = json.loads(raw, object_pairs_hook=base.unique_object)
        resource_review = reviews['inspection-digest-review.json']
        resource_change, checker_change = transition['owning_changes']
        base.need(base.sha(ROOT / checker_change['path']) == checker_change['candidate']['sha256'], 'Accepted current checker identity differs')
        base.need(resource_review.get('decision') == 'ACCEPT_EXACT_OPERATION_SCOPED_ANDROID_INSPECTION_DIGEST_SOURCE'
                  and resource_review.get('status') == 'PASS'
                  and resource_review.get('target') == resource_change['path']
                  and resource_review.get('baselineRevision') == '4a4dd6ce5c92e06ac6e49c97df8db6a59e67495b'
                  and resource_review.get('baselineSource113') == baseline_digest
                  and resource_review.get('currentPreimage') == resource_change['preimage']
                  and resource_review.get('candidate') == resource_change['candidate']
                  and resource_review.get('patch') == {'bytes':4955,'sha256':'89dac947f6e1cb88297bf16f1b34e3a4ff7beb9d061fe1f3f6434708fc53f733'}
                  and resource_review.get('canonicalApplied') is False
                  and resource_review.get('hostedTimeoutResolved') is False
                  and resource_review.get('nextSource113') is None
                  and resource_review.get('nativeDeviceGAQualified') is False, 'Accepted resource review scope differs')
        lifetime_review = reviews['command-lifetime-review.json']
        base.need(lifetime_review.get('verdict') == 'ACCEPT'
                  and lifetime_review.get('scope') == 'EXACT_OUTER_COMMAND_LIFETIME_SOURCE_HOST'
                  and lifetime_review.get('decision') == 'ACCEPT_EXACT_OUTER_COMMAND_LIFETIME_SOURCE_HOST'
                  and lifetime_review.get('candidate') == {'checkerSHA256':checker_change['candidate']['sha256'],'bytes':checker_change['candidate']['bytes'],'patchSHA256':'65db5e9b1c43ae71b7277e4127b0b46fb5424e56ee61914597964196c74bfc25','source113Proposed':'aede2b4db8202a0bfbc1db87e00e82b4e02617bb3fc72e278f0130af675ade46'}
                  and lifetime_review.get('preimage') == {'checkerSHA256':checker_change['preimage']['sha256'],'bytes':checker_change['preimage']['bytes'],'source113':baseline_digest,'rows':113}
                  and all(lifetime_review.get(k) is False for k in ('canonicalAdopted','actualSixConsumersPassed','runtimePass','gaPass')), 'Accepted lifetime review scope differs')
        checker_only = dict(baseline_inputs)
        checker_only[checker_change['path']] = checker_change['candidate']
        base.need(owner.source_digest(checker_only) == lifetime_review['candidate']['source113Proposed'], 'Lifetime checker-only context differs')
        fixture_review = reviews['runner-fixture-review.json']
        fixture = transition['fixture']
        fixture_raw = base.regular(ROOT / fixture['path']).read_bytes()
        base.need({'bytes':len(fixture_raw),'sha256':hashlib.sha256(fixture_raw).hexdigest()} == CI_TEMP_ROOT_FIXTURE['after']
                  and fixture['path'] not in actual, 'Accepted fixture candidate differs')
        base.need(fixture_review.get('verdict') == 'ACCEPT_EXACT_SYNTHETIC_RUNNER_FIXTURE_SOURCE'
                  and fixture_review.get('gate') == 'SAFE_CI_SELECTION_NEGATIVE_CONTROL_FIXTURE'
                  and {k:fixture_review.get('candidate',{}).get(k) for k in ('bytes','sha256')} == fixture['candidate']
                  and fixture_review.get('patches',[{}])[0] == {'name':'canonical full patch','requiredBeforeSHA256':fixture['preimage']['sha256'],'patch':'reviewed-artifacts/test-only.patch','patchSHA256':'852ea46271a5a3d7b23fe1cbeaf56d397aafdc8725c9f6efa8fb0d3c623f5309','exactReplayVerified':True}
                  and fixture_review.get('subjects') == {'canonicalOwningDigest':baseline_digest,'modernExecutedOwningDigest':lifetime_review['candidate']['source113Proposed'],'canonicalCheckerSHA256':checker_change['preimage']['sha256'],'modernCheckerSHA256':checker_change['candidate']['sha256'],'fixtureSHA256':fixture['candidate']['sha256'],'fixtureBytes':fixture['candidate']['bytes']}, 'Accepted fixture review scope differs')
        base.need(len(profile['sdk_files']) == 24 and profile['sdk_compatibility_sha256'] == 'dd67ffdb0458b2a546dcac8660e039364668f15c3a270ab417db7e7c2181ce47'
                  and len(profile['adapter_files']) == 25 and profile['adapter_compatibility_sha256'] == 'b6d5d6ae71227373cbffa862cc691aaa52f4ea81b8e4f85cf74ee612c5f15a3e'
                  and len(owner.java_roster(profile)) == 19, 'Combined profile differs')
        base.need(same_json(binding.get('fixture_dispatch'), {'host_rust_fixture_after_exact_checks':True, 'scope':'host fixture only; installed source/job/seal/raw accepted R5 checks precede dispatch', 'combinedAccepted':False, 'runtime':False, 'GA':False, 'exactWindow':False}), 'Host-only fixture dispatch contract differs')
        base.need(same_json(binding.get('adoption'), {'allowed':False, 'status':'CANDIDATE_PENDING_COMBINED_REVIEW', 'canonicalAdopted':False})
                  and same_json(binding.get('qualification'), {'compiler':False, 'native':False, 'CLI87':False, 'TestFlight':False, 'release':False, 'GA':False}), 'Candidate authority must remain pending')
        base.need(len(actual) == 113 and digest == '30344a0c5b00023cbc27fc793e67db7dec85d72a5aef0cd76573e2512f0b2ef8' and binding['source']['count'] == 113 and binding['source']['sha256'] == digest, 'Bound source closure differs')
        base.need(binding['profile'] == {'id':profile['id'], 'sdk_count':len(profile['sdk_files']), 'sdk_sha256':profile['sdk_compatibility_sha256'], 'adapter_count':len(profile['adapter_files']), 'adapter_sha256':profile['adapter_compatibility_sha256'], 'java_sources':len(owner.java_roster(profile))}, 'Accepted profile binding differs')
        caller_raw = base.regular(HERE / 'caller-inputs.json').read_bytes()
        base.need(len(caller_raw) == 1666 and hashlib.sha256(caller_raw).hexdigest() == 'abeb436445aad13ac9d175907031b004304971ee70f2959a3b675d7f7881340f', 'Accepted caller authority bytes differ')
        callers = json.loads(caller_raw, object_pairs_hook=base.unique_object)
        base.check_rows(ROOT, callers)
        expected = base.regular(HERE / 'current-swift-job.yml').read_text()
        base.need(expected == base.regular(prior / 'swift-job.yml').read_text(), 'Historical predecessor job differs')
        accepted = base.regular(HERE / 'accepted-swift-job.yml').read_text()
        base.need(hashlib.sha256(accepted.encode()).hexdigest() == binding['accepted_caller_job_sha256'], 'Accepted caller whole-job differs')
        for change in json.loads(base.regular(HERE / 'job-changes.json').read_bytes(), object_pairs_hook=base.unique_object):
            base.need(expected.count(change['before']) == change['count'], 'Successor edit preimage differs')
            expected = expected.replace(change['before'], change['after'])
        base.need(expected == base.regular(HERE / 'swift-job.yml').read_text(), 'Successor job derivation differs')
        base.need(CALLER_AFTER in expected and 'scripts/ci/prepare-cli-host-tests.py' in expected, 'Accepted caller missing')
        if installed:
            base.need(base.job_text(base.regular(WORKFLOW).read_text()) == expected, 'Installed ordinary Swift job differs from successor candidate')
        return {**proof, 'historical_workflow_job_sha256':proof['workflow_job_sha256'], 'workflow_job_sha256':hashlib.sha256(expected.encode()).hexdigest(), 'installed_job_verified':installed, 'caller_binding_seal_sha256':base.sha(HERE / 'seal.json'), 'source_count':len(actual), 'source_sha256':digest, 'profile':binding['profile'], 'historical_closure_sha256':base.sha(HERE / 'historical-closure.json')}
    base.verify = verify
    return base


class FreshOutput:
    """Observe successful historical admission; never infer it from an existing path."""
    def __init__(self, base):
        self.base = base
        self.fd = None
        self.runner = None
        self.restores = []

    def observe(self, runner):
        fresh = runner.fresh_output
        def admitted(*args, **kwargs):
            out = fresh(*args, **kwargs)
            self.base.need(self.fd is None, 'Duplicate fresh output admission')
            runner.no_symlinks(out)
            identity = runner.scratch_identity(out)
            ancestors = [(p, (p.stat().st_dev, p.stat().st_ino)) for p in out.parents]
            marker = self.base.regular(out / 'output-ownership.json')
            marker_bytes = marker.read_bytes()
            marker_identity = (marker.stat().st_dev, marker.stat().st_ino)
            fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                stat = os.fstat(fd)
                self.base.need([stat.st_dev, stat.st_ino, stat.st_uid] == identity,
                               'Admitted output identity changed')
                self.out, self.identity = out, identity
                self.ancestors = ancestors
                self.marker_bytes, self.marker_identity = marker_bytes, marker_identity
                self.runner, self.fd = runner, fd
                self.validate()
            except BaseException:
                self.fd = None
                os.close(fd)
                raise
            return out
        runner.fresh_output = admitted
        self.restores.append((runner, fresh))

    def validate(self):
        self.base.need(self.fd is not None, 'No positive fresh output admission')
        self.base.need(self.runner.scratch_identity(self.out) == self.identity,
                       'Admitted output identity changed')
        for parent, identity in self.ancestors:
            self.base.need((parent.stat().st_dev, parent.stat().st_ino) == identity,
                           'Admitted output ancestry changed')
        marker = self.base.regular(self.out / 'output-ownership.json')
        self.base.need((marker.stat().st_dev, marker.stat().st_ino) == self.marker_identity
                       and marker.read_bytes() == self.marker_bytes, 'Admitted output marker changed')

    def persist(self, files):
        self.validate()
        for name in files:
            self.base.need(not os.path.lexists(self.out / name), 'Successor evidence collision')
        for name, data in files.items():
            self.validate()
            # The descriptor remains bound to the admitted inode even if a path
            # is replaced between validation and the exclusive file creation.
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o666, dir_fd=self.fd)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)

    def close(self):
        for runner, fresh in reversed(self.restores):
            runner.fresh_output = fresh
        if self.fd is not None:
            os.close(self.fd)


def run_fixture(base, output, rustc):
    proof = base.verify(True)
    snapshots = {p: base.regular(HERE / p).read_bytes() for p in
                 ('adopt_envelope.py', 'seal.json', 'swift-job.yml', 'job-changes.json', 'source-inputs.json', 'binding.json', 'historical-closure.json')}
    status = None
    # Original runner retains original snapshots and complete failure evidence;
    # retain this prospective authority separately, including on fixture failure.
    errors = []
    ownership = FreshOutput(base)
    load_runner = base.load_runner
    def observed_runner():
        runner, ordinary, runner_proof = load_runner()
        ownership.observe(runner)
        return runner, ordinary, runner_proof
    base.load_runner = observed_runner
    try:
        status = base.run_fixture(output, rustc)
    except BaseException as error:
        errors.append({'phase': 'historical-fixture', 'type': type(error).__name__, 'message': str(error)})
    finally:
        base.load_runner = load_runner
    try:
        base.verify(True)
        for name, data in snapshots.items():
            base.need(base.regular(HERE / name).read_bytes() == data, 'Successor source changed: ' + name)
    except BaseException as error:
        errors.append({'type': type(error).__name__, 'message': str(error)})
    result = {
        'proof': proof, 'fixture_return_status': status, 'errors': errors,
        'source_snapshots': {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()},
        'scope': 'Prospective job binding only; original compiler, commands, limits and terminal replay unchanged'
    }
    try:
        files = {'executed-caller-binding-' + name: data for name, data in snapshots.items()}
        files['caller-binding-result.json'] = (json.dumps(result, indent=2) + '\n').encode()
        ownership.persist(files)
    except BaseException as error:
        errors.append({'phase': 'successor-evidence', 'type': type(error).__name__, 'message': str(error)})
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
    finally:
        ownership.close()
    return status if not errors and status is not None else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--workflow-installed', action='store_true')
    run = sub.add_parser('run')
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--rustc', required=True)
    args = parser.parse_args()
    base = bind()
    if args.command == 'verify':
        print(json.dumps(base.verify(args.workflow_installed), sort_keys=True))
        return 0
    # Verify every installed authority before resource acquisition or fixture dispatch.
    base.verify(True)
    admission = json.loads(base.regular(HERE / 'binding.json').read_bytes())['fixture_dispatch']
    base.need(admission['host_rust_fixture_after_exact_checks'] is True, 'Host fixture dispatch disabled')
    return run_fixture(base, args.out, args.rustc)


if __name__ == '__main__':
    sys.exit(main())
