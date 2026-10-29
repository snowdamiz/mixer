"""One exact frozen-path commit and nonforce origin/main push; no retries."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('android_host_followup_delivery_common', Path(__file__).with_name('selection_common_delivery_followup_v4.py'))
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
import hashlib
import json
import stat
for name in ('StrictCommands','BASE','TREE','S','SELECTION','ROWS','SELECTED','PROTECTED','ROOT','OUT','now','row','save','fingerprint','preserved_entry','raw_rows','collapsed','check_sources','accepted_preflight','ACCEPTED_PREFLIGHT_SEAL','ACCEPTED_PREFLIGHT_ROWS','selected_row'): globals()[name] = getattr(common,name)
PARALLEL_SUPPLEMENT_ROW = {"path":"verification/github-delivery-android-host-followup/parallel-output-supplement.json","bytes":2245,"sha256":"e55b7d64c53955137d3c03d1f83b9a8d3cd16a96275a90d4ecdf1409f74df73e"}
PARALLEL_PATH = 'verification/android-axis-canonical-integration-handoff-2026-10-29/'
assert row(ROOT / PARALLEL_SUPPLEMENT_ROW['path']) == PARALLEL_SUPPLEMENT_ROW
PARALLEL_SUPPLEMENT = json.loads((ROOT / PARALLEL_SUPPLEMENT_ROW['path']).read_bytes())
assert PARALLEL_SUPPLEMENT['schema'] == 1 and PARALLEL_SUPPLEMENT['selectedForCommit'] is False
assert PARALLEL_SUPPLEMENT['commandsExecuted'] == 0 and PARALLEL_SUPPLEMENT['dispatchAuthority'] is False
assert PARALLEL_SUPPLEMENT['preflight'] == ACCEPTED_PREFLIGHT_ROWS[0] and PARALLEL_SUPPLEMENT['rootReview'] == ACCEPTED_PREFLIGHT_SEAL
assert PARALLEL_SUPPLEMENT['directory'] == {'path': PARALLEL_PATH, 'mode': 493, 'type': 16384, 'inode': 165203741, 'device': 16777233}
assert PARALLEL_SUPPLEMENT['additionalCollapsedUntrackedAllowed'] == [PARALLEL_PATH]
assert PARALLEL_SUPPLEMENT['priorCollapsedEntries'] == 2398 and len(PARALLEL_SUPPLEMENT['files']) == 4
assert not any(value == PARALLEL_PATH.rstrip('/') or value.startswith(PARALLEL_PATH) for value in SELECTED)


def check_parallel_output():
    assert row(ROOT / PARALLEL_SUPPLEMENT_ROW['path']) == PARALLEL_SUPPLEMENT_ROW
    assert preserved_entry(PARALLEL_PATH) == PARALLEL_SUPPLEMENT['directory']
    for expected in PARALLEL_SUPPLEMENT['files']:
        assert expected['path'].startswith(PARALLEL_PATH)
        assert selected_row(expected) == expected


WHITESPACE_SCOPE_ROW = {"path":"verification/github-delivery-android-host-followup/immutable-evidence-whitespace-scope.json","bytes":29245,"sha256":"ea91660fb2bd71bcadea0bedc1b36bdb5cf610186f472fb3ab9a17010daf1a31"}
assert row(ROOT / WHITESPACE_SCOPE_ROW['path']) == WHITESPACE_SCOPE_ROW
WHITESPACE_SCOPE = json.loads((ROOT / WHITESPACE_SCOPE_ROW['path']).read_bytes())
assert WHITESPACE_SCOPE['schema'] == 1 and WHITESPACE_SCOPE['selection'] == row(ROOT / SELECTION)
assert WHITESPACE_SCOPE['selectedPaths'] == 256 and WHITESPACE_SCOPE['unchangedContentAndBlobModeProofPaths'] == 256
assert WHITESPACE_SCOPE['whitespaceCheckedPaths'] == 249
FORMATTING = WHITESPACE_SCOPE['whitespaceCheckedExactPaths']
IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS = [{key: value[key] for key in ('path', 'bytes', 'sha256', 'mode')} for value in WHITESPACE_SCOPE['exemptEvidence']]
assert len(IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS) == 7
assert len({value['path'] for value in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS}) == 7
assert FORMATTING == sorted(SELECTED - {value['path'] for value in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS}) and len(FORMATTING) == 249
assert set(FORMATTING) | {value['path'] for value in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS} == SELECTED
for expected in IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS:
    assert selected_row(expected) == expected


AUTHORED = [".github/workflows/android-axis-refusal-host.yml",".github/workflows/android-view-api-package-runtime-focused-admission.yml","PLAN.md","STATUS.md","gates/ga.json","verification/android-axis-host-selection-2026-10-29/.gitignore","verification/android-axis-host-selection-2026-10-29/README.md","verification/android-axis-host-selection-2026-10-29/root-review.json","verification/android-axis-refusal-host-admission-result-correction/.gitignore","verification/android-axis-refusal-host-admission-result-correction/README.md","verification/android-axis-refusal-host-admission-result-correction/admission-manifest.json","verification/android-axis-refusal-host-admission-result-correction/controls.mjs","verification/android-axis-refusal-host-admission-result-correction/receipt.json","verification/android-axis-refusal-host-admission-result-correction/required-tests.json","verification/android-axis-refusal-host-admission-result-correction/root-selection.template.json","verification/android-axis-refusal-host-admission-result-correction/source-checks.json","verification/android-axis-refusal-host-admission-result-correction/verify-file-limit.py","verification/android-axis-refusal-host-admission-result-correction/verify.mjs","verification/android-axis-refusal-host-admission-result-correction/workflow.draft.yml","verification/android-axis-refusal-host-admission-review/correction-supplement.json","verification/android-axis-refusal-host-admission-review/findings.md","verification/android-axis-refusal-host-admission-review/receipt.json","verification/android-axis-refusal-host-admission-review/source-checks.json","verification/android-axis-refusal-host-admission/.gitignore","verification/android-axis-refusal-host-admission/README.md","verification/android-axis-refusal-host-admission/admission-manifest.json","verification/android-axis-refusal-host-admission/controls.mjs","verification/android-axis-refusal-host-admission/receipt.json","verification/android-axis-refusal-host-admission/required-tests.json","verification/android-axis-refusal-host-admission/root-selection.template.json","verification/android-axis-refusal-host-admission/source-checks.json","verification/android-axis-refusal-host-admission/verify-file-limit.py","verification/android-axis-refusal-host-admission/verify.mjs","verification/android-axis-refusal-host-admission/workflow.draft.yml","verification/android-axis-refusal-host-preparation/package/Package.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerAndroidRuntime/DocumentSession.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerAndroidRuntime/SessionRegistry.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerCore/FeatureStore.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerCore/JSONInputGuard.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerCore/Lifecycle.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerCore/Navigation.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerCore/Resources.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceDefaultV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceDefaultV2.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceDescriptorV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceDescriptorV2.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceGeometryV2.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceMetricMathV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceResolutionV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceResolutionV2.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceValuesV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/AppearanceValuesV2.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/Authoring.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/NativePacketV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/Protocol.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/Reconciliation.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/SharedTextProfilesV1.swift","verification/android-axis-refusal-host-preparation/package/Sources/MixerUI/Validation.swift","verification/android-axis-refusal-host-preparation/package/Tests/MixerAndroidRuntimeTests/AndroidTextFieldAxisRefusalTests.swift","verification/android-axis-refusal-host-preparation/package/Tests/MixerAndroidRuntimeTests/RuntimeTests.swift","verification/android-axis-refusal-host-preparation/package/Tests/MixerAndroidRuntimeTests/TransactionTests.swift","verification/android-axis-refusal-host-preparation/proposal.md","verification/android-axis-refusal-host-preparation/receipt.json","verification/android-axis-refusal-host-preparation/source-manifest.json","verification/android-axis-refusal-host-review/findings.md","verification/android-axis-refusal-host-review/receipt.json","verification/android-axis-refusal-host-review/source-checks.json","verification/android-host-followup-selection-2026-10-29/.gitignore","verification/android-host-followup-selection-2026-10-29/README.md","verification/android-host-followup-selection-2026-10-29/helper-review.json","verification/android-host-followup-selection-2026-10-29/root-review.json","verification/android-host-followup-selection-2026-10-29/selection.json","verification/android-jdk-comparison-challenge/ACTUAL-RESULT-REVIEW.md","verification/android-jdk-comparison-challenge/DIRECTORY-SUFFIX-SUPPLEMENT.md","verification/android-jdk-comparison-challenge/REVIEW.md","verification/android-jdk-comparison-challenge/actual-result-review-local-correction.json","verification/android-jdk-comparison-challenge/actual-result-review-seal.json","verification/android-jdk-comparison-challenge/actual-result-review.json","verification/android-jdk-comparison-challenge/actual_result_review.mjs","verification/android-jdk-comparison-challenge/actual_result_review_v2.mjs","verification/android-jdk-comparison-challenge/audit_metadata.mjs","verification/android-jdk-comparison-challenge/challenge-receipt.json","verification/android-jdk-comparison-challenge/directory-suffix-supplement-seal.json","verification/android-jdk-comparison-challenge/directory-suffix-supplement.json","verification/android-jdk-comparison-challenge/seal.json","verification/android-jdk-data-outcome-2026-10-29/README.md","verification/android-jdk-data-outcome-2026-10-29/observation.json","verification/android-jdk-data-outcome-2026-10-29/ordinary-ci.json","verification/android-package-jdk-host-selection-2026-10-29/.gitignore","verification/android-package-jdk-host-selection-2026-10-29/README.md","verification/android-package-jdk-host-selection-2026-10-29/pure-controls.json","verification/android-package-jdk-host-selection-2026-10-29/root-review.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/SOURCE-REVIEW.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/check_source_data.js","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/compare_data.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/contract.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/observed-binding-template.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/source-data-checks.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-preparation/source-manifest.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/CP437-SETUP-CORRECTION.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/REVIEW.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/.gitignore","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/compare_actual_data_cpu_bound.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/compare_actual_data_portable_limits.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/context-refusal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/context-selection.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/directory-suffix-controls.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/directory-suffix-selection.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/empty-directory-name-pairs.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/first-execution-refusal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/portable-selection.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/result-summary.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/second-execution-refusal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-data-execution/selection.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-bound-preparation/PREPARATION.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-bound-preparation/binding-complete.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-bound-preparation/compare_actual_data.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-bound-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-bound-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-preparation/PREPARATION.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-preparation/binding-unbound.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-preparation/compare_actual_data.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/actual-wrapper-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/check_synthetic.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/check_synthetic_cp437.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/cp437-setup-correction-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/cp437-setup-correction-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/REVIEW.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/check_synthetic_directory_suffix.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/compare_actual_data_directory_suffix.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/compare_data.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/directory-slash-correction-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/REVIEW.md","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/compare_actual_data_failure_context.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/compare_data.py","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/failure-context-wrapper-preparation/static-evidence.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/review-receipt.json","verification/android-view-api-focused-actual-review/jdk-archive-comparison-review/review-seal.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/.gitignore","verification/android-view-api-focused-actual-review/jdk-data-actual-review/ACTUAL-REVIEW.md","verification/android-view-api-focused-actual-review/jdk-data-actual-review/REVIEW.md","verification/android-view-api-focused-actual-review/jdk-data-actual-review/actual-review-receipt.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/actual-review-seal.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/audit-compatibility-preparation.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/audit-compatibility-selection.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/audit-source-review.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/audit_outer_data.py","verification/android-view-api-focused-actual-review/jdk-data-actual-review/audit_outer_data_compat.py","verification/android-view-api-focused-actual-review/jdk-data-actual-review/corrected-consumer-preparation/SOURCE-REVIEW.md","verification/android-view-api-focused-actual-review/jdk-data-actual-review/corrected-consumer-preparation/consume_selected_artifact.js","verification/android-view-api-focused-actual-review/jdk-data-actual-review/corrected-consumer-preparation/preparation-receipt.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/corrected-consumer-preparation/preparation-seal.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/original-transfer-abort-receipt.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/recovery-selection.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/review-receipt.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/review-seal.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/source-inspection-seal.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/source-inspection-supplement.json","verification/android-view-api-focused-actual-review/jdk-data-actual-review/transfer-control.redacted.js","verification/android-view-api-package-runtime-host-preparation/.gitignore","verification/android-view-api-package-runtime-host-preparation/README.md","verification/android-view-api-package-runtime-host-preparation/admission.json","verification/android-view-api-package-runtime-host-preparation/baseline.json","verification/android-view-api-package-runtime-host-preparation/collect.py","verification/android-view-api-package-runtime-host-preparation/custody.py","verification/android-view-api-package-runtime-host-preparation/input-manifest.json","verification/android-view-api-package-runtime-host-preparation/inspector-review.json","verification/android-view-api-package-runtime-host-preparation/jdk-runtime-members.json","verification/android-view-api-package-runtime-host-preparation/linux-signal-abi-source-receipt.json","verification/android-view-api-package-runtime-host-preparation/node-data-checks.json","verification/android-view-api-package-runtime-host-preparation/preparation-receipt.json","verification/android-view-api-package-runtime-host-preparation/seal.json","verification/android-view-api-package-runtime-host-preparation/selection-template.json","verification/android-view-api-package-runtime-host-preparation/source-data-attempts.json","verification/android-view-api-package-runtime-host-preparation/source-delta.json","verification/android-view-api-package-runtime-host-preparation/test_preparation.py","verification/android-view-api-package-runtime-host-preparation/tool-profile-historical-macos.json","verification/android-view-api-package-runtime-host-preparation/tool-profile.json","verification/android-view-api-package-runtime-host-preparation/workflow-actions.json","verification/android-view-api-package-runtime-host-preparation/workflow.DRAFT.yml","verification/android-view-api-package-runtime-host-review/REVIEW.md","verification/android-view-api-package-runtime-host-review/receipt.json","verification/android-view-api-package-runtime-host-review/seal.json","verification/github-delivery-android-host-followup/.gitignore","verification/github-delivery-android-host-followup/baseline-repin.diff","verification/github-delivery-android-host-followup/owned.py","verification/github-delivery-android-host-followup/preflight_selected.py.template","verification/github-delivery-android-host-followup/preparation.json","verification/github-delivery-android-host-followup/two-workflow-feasibility.json","verification/github-delivery-android-jdk-observation/.gitignore","verification/github-delivery-android-jdk-observation/CORRECTION.md","verification/github-delivery-android-jdk-observation/HELPER-BASELINE.diff","verification/github-delivery-android-jdk-observation/argv-ci-binding-selected-corrected.json","verification/github-delivery-android-jdk-observation/argv-ci-binding-selected.json","verification/github-delivery-android-jdk-observation/argv-delivery-selected-corrected.json","verification/github-delivery-android-jdk-observation/argv-delivery-selected.json","verification/github-delivery-android-jdk-observation/argv-dispatch-selected-corrected.json","verification/github-delivery-android-jdk-observation/argv-dispatch-selected.json","verification/github-delivery-android-jdk-observation/argv-preflight-selected.json","verification/github-delivery-android-jdk-observation/authority-snapshot-ci-binding-selected-corrected.json","verification/github-delivery-android-jdk-observation/authority-snapshot-delivery-selected-corrected.json","verification/github-delivery-android-jdk-observation/authority-snapshot-dispatch-selected-corrected.json","verification/github-delivery-android-jdk-observation/authority-snapshot-preflight-selected.json","verification/github-delivery-android-jdk-observation/bind_ci_selected.py","verification/github-delivery-android-jdk-observation/bind_ci_selected_corrected.py","verification/github-delivery-android-jdk-observation/ci-binding-selected-corrected.json","verification/github-delivery-android-jdk-observation/committed-selected-corrected-objects.json","verification/github-delivery-android-jdk-observation/committed-selected-corrected.json","verification/github-delivery-android-jdk-observation/deliver_selected.py","verification/github-delivery-android-jdk-observation/deliver_selected_corrected.py","verification/github-delivery-android-jdk-observation/delivery-ci-dispatch-actual.seal.json","verification/github-delivery-android-jdk-observation/delivery-selected-corrected-once.json","verification/github-delivery-android-jdk-observation/delivery-selected-corrected-receipt.json","verification/github-delivery-android-jdk-observation/delivery-source-correction-packet.json","verification/github-delivery-android-jdk-observation/delivery-source-correction-packet.seal.json","verification/github-delivery-android-jdk-observation/delivery-source-packet.json","verification/github-delivery-android-jdk-observation/delivery-source-packet.seal.json","verification/github-delivery-android-jdk-observation/dispatch_selected.py","verification/github-delivery-android-jdk-observation/dispatch_selected_corrected.py","verification/github-delivery-android-jdk-observation/driver-preparation.json","verification/github-delivery-android-jdk-observation/manifest-selected.json","verification/github-delivery-android-jdk-observation/manual-dispatch-selected-corrected-input.json","verification/github-delivery-android-jdk-observation/manual-dispatch-selected-corrected-once.json","verification/github-delivery-android-jdk-observation/manual-dispatch-selected-corrected-submitted.json","verification/github-delivery-android-jdk-observation/owned.py","verification/github-delivery-android-jdk-observation/preflight-selected.json","verification/github-delivery-android-jdk-observation/preflight-selected.seal.json","verification/github-delivery-android-jdk-observation/preflight-source-packet.json","verification/github-delivery-android-jdk-observation/preflight-source-packet.seal.json","verification/github-delivery-android-jdk-observation/preflight_selected.py","verification/github-delivery-android-jdk-observation/preparation.json","verification/github-delivery-android-jdk-observation/push-selected-corrected-once.json","verification/github-delivery-android-jdk-observation/review/delivery-ci-dispatch-actual-data-controls.json","verification/github-delivery-android-jdk-observation/review/delivery-ci-dispatch-actual-review.json","verification/github-delivery-android-jdk-observation/review/delivery-ci-dispatch-actual-review.seal.json","verification/github-delivery-android-jdk-observation/review/delivery-final-data-controls.json","verification/github-delivery-android-jdk-observation/review/delivery-final-review.json","verification/github-delivery-android-jdk-observation/review/delivery-final-review.seal.json","verification/github-delivery-android-jdk-observation/review/delivery-review-attempt-001.json","verification/github-delivery-android-jdk-observation/review/guarded-draft-diffs.json","verification/github-delivery-android-jdk-observation/review/guarded-draft-review.json","verification/github-delivery-android-jdk-observation/review/preflight-actual-evidence-review.json","verification/github-delivery-android-jdk-observation/review/preflight-final-data-controls.json","verification/github-delivery-android-jdk-observation/review/preflight-final-review.json","verification/github-delivery-android-jdk-observation/review/preflight-final-review.seal.json","verification/github-delivery-android-jdk-observation/selection_common_delivery.py","verification/github-delivery-android-jdk-observation/selection_common_delivery_corrected.py","verification/github-delivery-android-jdk-observation/selection_common_preflight.py","verification/github-delivery-android-jdk-observation/stage-selected-corrected-pathspec-admission.json","work-graph.json"]
pre, preservation = accepted_preflight()
assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF']
assert pre['head'] == BASE and pre['tree'] == TREE and pre['selectedPaths'] == len(SELECTED)
assert len(preservation['untrackedCollapsed']) == PARALLEL_SUPPLEMENT['priorCollapsedEntries']
assert PARALLEL_PATH not in {value['path'] for value in preservation['untrackedCollapsed']}
check_parallel_output()
assert not (OUT / 'delivery-followup-once.json').exists()
with (OUT / 'paths-followup.nul').open('xb') as handle:
    handle.write(b''.join(value.encode() + b'\0' for value in sorted(SELECTED)))


def check_preservation(commands, label):
    check_sources()
    assert row(ROOT / WHITESPACE_SCOPE_ROW['path']) == WHITESPACE_SCOPE_ROW
    check_parallel_output()
    for expected in preservation['tracked']:
        assert fingerprint(expected['path']) == expected, expected['path']
    for expected in preservation['protectedSnapshots']:
        assert fingerprint(expected['path']) == expected, expected['path']
    assert fingerprint('.wrangler') == preservation['wrangler']
    assert not (ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex').exists()
    raw = raw_rows(commands.run(label + '-diff', ['git', 'diff', '--raw', '--no-abbrev', '--no-renames', '-z']))
    outside = [value for value in raw if value['path'] not in SELECTED]
    assert outside == preservation['otherDirtyTracked'], 'Dirty tracked diff outside selection changed'
    for expected in preservation['untrackedCollapsed']:
        assert preserved_entry(expected['path']) == expected, expected['path']


c = StrictCommands('delivery-followup')
assert c.authority['preservationSupplement'] == PARALLEL_SUPPLEMENT_ROW
assert c.authority['immutableEvidenceWhitespaceScope'] == WHITESPACE_SCOPE_ROW
assert c.run('head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [BASE, TREE]
assert c.run('branch', ['git', 'branch', '--show-current']).decode().strip() == 'main'
assert c.run('origin', ['git', 'remote', 'get-url', 'origin']).decode().strip() == pre['origin']
assert c.run('push-url-before-stage', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
assert c.run('remote-before', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert not c.run('index-before', ['git', 'diff', '--cached', '--name-only', '-z'])
check_preservation(c, 'before')
save('delivery-followup-once.json', {'at': now(), 'selection': row(ROOT / SELECTION), 'paths': len(SELECTED),
    'oneCommitNonforcePushAuthorized': True, 'retryOnUnknownOutcome': False})
c.run('stage', ['git', 'add', '--pathspec-from-file=' + str(OUT / 'paths-followup.nul'), '--pathspec-file-nul'])
entries = c.run('index-selected', ['git', 'ls-files', '--stage', '-z', '--', *AUTHORED]).split(b'\0')
objects = {}
for entry in entries:
    if not entry:
        continue
    meta, value = entry.split(b'\t', 1)
    fields, value = meta.decode().split(), value.decode()
    assert len(fields) == 3 and fields[2] == '0' and value in SELECTED and value not in objects
    payload = (ROOT / value).read_bytes()
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    mode = '100755' if stat.S_IMODE((ROOT / value).stat().st_mode) & 0o111 else '100644'
    assert fields[0] == mode and fields[1] == oid, value
    objects[value] = {'oid': oid, 'mode': mode}
assert set(objects) == SELECTED
selected_object_rows = [{'path': value, **objects[value]} for value in sorted(objects)]
selected_object_digest = hashlib.sha256(json.dumps(selected_object_rows, separators=(',', ':')).encode()).hexdigest()
assert selected_object_digest == 'fa3e65baa251181cbe2a027ca7e1914b4d680ab3274f682836e09e756763d548'
save('staged-followup-all-index-objects-local.json', objects)
parts = c.run('staged-objects', ['git', 'diff', '--cached', '--raw', '--no-abbrev', '--no-renames', '-z']).split(b'\0')
assert len(parts) % 2 == 1
changed_objects = {}
for index in range(0, len(parts) - 1, 2):
    fields, value = parts[index].decode().split(), parts[index + 1].decode()
    assert len(fields) == 5 and fields[-1] in ('A', 'M') and value in SELECTED and value not in changed_objects
    assert {'oid': fields[3], 'mode': fields[1]} == objects[value], value
    changed_objects[value] = objects[value]
assert changed_objects and set(changed_objects).issubset(SELECTED)
save('staged-followup-changed-objects-local.json', changed_objects)
c.run('authored-check', ['git', 'diff', '--cached', '--check', '--',
    *FORMATTING])
check_preservation(c, 'staged')
c.run('commit', ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
    'commit', '-m', 'Deliver reviewed Android host followup and bounded workflow admissions'])
head, tree, parent = c.run('committed-head', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}', 'HEAD^']).decode().splitlines()
assert parent == BASE
c.bind_committed_sha(head)
save('committed-followup.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent, 'paths': len(SELECTED)})
committed_raw = c.run('committed-objects', ['git', 'diff-tree', '--no-commit-id', '--raw', '--no-abbrev', '--no-renames', '-r', '-z', BASE, head])
committed_parts = committed_raw.split(b'\0')
assert len(committed_parts) % 2 == 1
committed_objects = {}
for index in range(0, len(committed_parts) - 1, 2):
    fields, value = committed_parts[index].decode().split(), committed_parts[index + 1].decode()
    assert len(fields) == 5 and fields[-1] in ('A', 'M') and value in SELECTED and value not in committed_objects
    committed_objects[value] = {'oid': fields[3], 'mode': fields[1]}
assert committed_objects == changed_objects, 'Committed diff differs from the verified changed-selected subset'
assert set(committed_objects).issubset(SELECTED)
save('committed-followup-objects.json', committed_objects)
check_sources()
assert c.run('remote-prepush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [BASE, 'refs/heads/main']
assert c.run('push-url-prepush', ['git', 'remote', 'get-url', '--push', '--all', 'origin']).decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
save('push-followup-once.json', {'at': now(), 'head': head, 'tree': tree, 'parent': parent,
    'remote': 'origin', 'ref': 'refs/heads/main', 'force': False,
    'reservationConsumedBeforeSubmit': True, 'retryOnUnknownOutcome': False})
c.run('push', ['git', '-c', 'core.hooksPath=/dev/null', 'push', '--signed=false', '--no-follow-tags', '--recurse-submodules=no', 'origin', head + ':refs/heads/main'], seconds=45)
assert c.run('remote-postpush', ['git', 'ls-remote', 'origin', 'refs/heads/main']).decode().split() == [head, 'refs/heads/main']
assert not c.run('index-after', ['git', 'diff', '--cached', '--name-only', '-z'])
check_preservation(c, 'after')
after = collapsed(c.run('collapsed-status-after', ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=normal']))
after_untracked = [preserved_entry(value['path']) for value in after if value['status'] == '??']
before_paths = {value['path'] for value in preservation['untrackedCollapsed']}
after_paths = {value['path'] for value in after_untracked}
removed = sorted(before_paths - after_paths)
added = sorted(after_paths - before_paths)
for value in removed:
    assert any(p == value.rstrip('/') or p.startswith(value) for p in SELECTED), ('Unrelated collapsed entry disappeared', value)
for value in added:
    assert value == PARALLEL_PATH or any(prior.endswith('/') and value.startswith(prior) for prior in before_paths), ('Unrelated collapsed entry appeared', value)
assert PARALLEL_PATH in added, 'Exact preserved root parallel-output collapsed entry is required'
save('preservation-followup-after-local.json', {'at': now(), 'statusCollapsed': after, 'untrackedCollapsed': after_untracked,
    'selectedTrackingCollapsedTransitions': {'removed': removed, 'added': [value for value in added if value != PARALLEL_PATH]},
    'parallelRootOutputSupplement': PARALLEL_SUPPLEMENT_ROW, 'parallelRootOutputAdditionalCollapsedEntries': [PARALLEL_PATH],
    'allPreexistingCollapsedEntryIdentityModesPreserved': True})
c.complete()
save('delivery-followup-receipt.json', {'schema': 1, 'at': now(), 'head': head, 'tree': tree, 'parent': parent,
    'pushed': True, 'force': False, 'selectedPaths': len(SELECTED), 'selection': row(ROOT / SELECTION),
    'manifest': row(OUT / 'manifest-followup.json'), 'preflight': ACCEPTED_PREFLIGHT_ROWS[0],
    'preservationBefore': ACCEPTED_PREFLIGHT_ROWS[1], 'preflightSeal': ACCEPTED_PREFLIGHT_SEAL,
    'committedChangedObjects': row(OUT / 'committed-followup-objects.json'),
    'selectedIndexObjectsLocal': row(OUT / 'staged-followup-all-index-objects-local.json'),
    'allSelectedIndexBlobModesVerified': True, 'selectedIndexBlobModeDigestSHA256': selected_object_digest,
    'changedSelectedPaths': len(changed_objects), 'unchangedSelectedPaths': len(SELECTED) - len(changed_objects),
    'unchangedSelectedMembersBoundByParentTreeAndExactCommittedDiff': True,
    'pushURL': 'https://github.com/snowdamiz/mixer.git', 'explicitNoTagsSigningOrSubmodulePush': True,
    'protected': PROTECTED, 'protectedByteModesUnchanged': True,
    'cleanTrackedBoundByBaselineTreeAndCompleteRawDiff': True,
    'allCleanTrackedFilesIndependentlyHashed': False,
    'outsideSelectionDirtyByteModeSnapshotsPreserved': len(preservation['tracked']),
    'preexistingCollapsedEntryIdentityModesPreserved': len(preservation['untrackedCollapsed']),
    'afterCollapsedUntrackedEntries': len(after_untracked), 'collapsedSelectedTransitions': {'removed': len(removed), 'added': len(added) - 1},
    'parallelRootOutputSupplement': PARALLEL_SUPPLEMENT_ROW, 'parallelRootOutputDirectoryIdentityModePreserved': True,
    'parallelRootOutputNamedFilesByteModesPreserved': len(PARALLEL_SUPPLEMENT['files']), 'parallelRootOutputAdditionalCollapsedEntries': [PARALLEL_PATH],
    'wranglerUntouched': True, 'artifactsStoreAbsent': True, 'indexEmpty': True, 'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row,
    'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
    'whitespaceCheckScope': WHITESPACE_SCOPE_ROW, 'whitespaceCheckedPaths': len(FORMATTING),
    'immutableEvidenceFormattingExclusions': IMMUTABLE_EVIDENCE_FORMATTING_EXCLUSIONS,
    'unchangedContentAndBlobModeProofPaths': len(SELECTED),
    'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
    'rawHelperInventoriesCommitted': False, 'manualDispatchesPending': 2, 'manualWorkflowDispatchesAuthorized': 0, 'separatelySelectedManualDispatchCeiling': 2, 'manualHostKeys': ['axis', 'package'],
    'canonicalAndroidChanges': 0, 'productionDefaultsChanged': False, 'allExistingHoldsUntouched': True,
    'runtimeCompilerNativeUICaptureProcessInventoryHeldProbesStarted': False,
    'fieldlogRepositoryOperations': 0, 'releaseTagOrGAPromotion': False})
print(json.dumps({'head': head, 'tree': tree, 'parent': parent, 'pushed': True,
                  'paths': len(SELECTED), 'closedCommands': len(c.records)}))
