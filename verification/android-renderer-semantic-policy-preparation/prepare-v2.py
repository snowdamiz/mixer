"""Prepare source-specific renderer obligations; execute no product or witness."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "verification/android-source-pair5-coherent-integration-preparation/source"
CHECKLIST = REPO / "verification/android-editor-membership-qualification-independent/semantic-applicability/applicability-checklist.json"
CLASSES = REPO / "verification/android-editor-membership-qualification-independent/v1-positive-preparation/run-1/classes"
NATIVE = "native/android/app/src/dev/mixer/android/NativeRenderer.java"
TESTS = "native/android/tests/NativeEditorPreservationHostControls/"
CALLBACK_STATES = ["clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry", "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback"]
HOOKED_LEAVES = {"getWidth", "getHeight", "getText", "getLocationInWindow"}
NATIVE_ORACLES = {
    "getWidth": "int equal to independently configured right-left at the selected receiver's result computation",
    "getHeight": "int equal to independently configured bottom-top at the selected receiver's result computation",
    "getText": "same Editable reference held at actual getter computation; copy UTF-16 units, ordered span identities/types/flags/ranges and selection-related content at return, not after later callbacks",
    "getLocationInWindow": "void; exact supplied int[2] identity updated to left/top plus each View ancestor left/top minus ancestor scrollX/scrollY in actual order; assert both immutable output elements before later mutation",
    "getComposingSpanStart": "int equal to first composing span start in the configured ordered Spanned.getSpans result, else -1; custom span getter behavior needs a separate actual enclosing witness",
    "isTextSelectable": "boolean equal to independently configured selectable field",
    "getSelectionStart": "int equal to independently configured selectionStart, preserving -1 and legal boundary values",
    "getSelectionEnd": "int equal to independently configured selectionEnd, preserving -1 and legal boundary values",
    "getDrawableState": "fresh int array of configured enabled,pressed,focused state constants in exactly that order, omitting false flags; constructor subsequently clones it, so retain both identity separation and immutable element values",
    "getLeft": "int equal to configured left", "getTop": "int equal to configured top",
    "getRight": "int equal to configured right", "getBottom": "int equal to configured bottom",
    "getMeasuredWidth": "int equal to configured measuredWidth", "getMeasuredHeight": "int equal to configured measuredHeight",
    "isEnabled": "boolean equal to configured enabled", "isPressed": "boolean equal to configured pressed",
    "hasFocus": "boolean equal to configured focused", "getScrollX": "int equal to configured scrollX",
    "getScrollY": "int equal to configured scrollY", "isChecked": "boolean equal to configured checked",
}
OWNED_CLASSES = {"dev/mixer/android/NativeRenderer", "dev/mixer/android/NativeRenderer$2", "dev/mixer/android/NativeRenderer$AttachmentJournal", "dev/mixer/android/NativeRenderer$NativeState", "dev/mixer/android/NativeRenderer$PreservationMembership"}


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def copy_input(path, name):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    target = HERE / "inputs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return data


# Explicit source-reviewed descriptions, keyed by exact selected method owner/name.
# Each tuple is applicability, finite result/state oracle, identity/count/error oracle,
# and candidate original control arguments. These are requirements, not observed results.
P = {
"NativeRenderer$2#editorDispatchAvailable": (
 "guarded-scalar-admission", "On main thread return exactly replacement-absent AND retainedEditorV2(record). False must not acquire a count or authorize another record. Wrong thread refuses before renderer access.",
 "Record/view/fence and current renderer retention are exact references. Keep replacement, shared count and lease fields unchanged on either Boolean result.", ["identity-matrix", "foreign-replay"]),
"NativeRenderer$2#editorLossObservation": (
 "guarded-counter-with-terminal-overflow", "Below Long.MAX_VALUE return the exact current long without increment. At MAX_VALUE create and throw the same IllegalStateException passed to terminalV2; no wraparound or successful long return.",
 "Main-thread guard precedes reads. Overflow terminal/cleanup effects must preserve original primary/first Error semantics in actual enclosing terminalV2 execution; helper callbacks need their own joins.", ["fatal-chronology", "getter-suffix-matrix"]),
"NativeRenderer$2#editorLossObserved": (
 "guarded-loss-update-with-terminal-overflow", "Foreign/null/non-field/fence-invalid or uncaptured suffix refuses before increment. Valid retained or construction record increments serial exactly once and marks the same active replacement lost. MAX and MAX-1 exhaustion paths terminate and throw without wraparound.",
 "Own/foreign capture identity and original suffix remain distinct from successor authority. Invalid provenance changes no counters or replacement flags. Preserve terminal failure identity and every already-observed prefix.", ["getter-suffix-matrix", "identity-matrix"]),
"NativeRenderer$2#fieldPreservationBegin": (
 "guarded-preservation-acquisition", "All provenance, CAPTURED phase, no hooks/callbacks/checking, live original mutation, exact cohort and integer bounds are validated before the scalar tail. Success returns void with entered/count true, phase ATTACHING and all three counts incremented once.",
 "Same renderer/candidate/journal/record/field/input/original/token and registered scope required. Refusal preserves pre-entry flags/counts. Called needs/current helpers may reenter and require exact enclosing callback evidence; no synthetic callback is assigned to the scalar tail.", ["captured-A-refusal", "partial-A-entered-C-refusal", "constructor-before-registration", "progress-states", "identity-matrix"]),
"NativeRenderer$2#fieldPreservationEnd": (
 "guarded-preservation-release", "Only exact identity, end-ready phase/state and funded valid cohort may return void. Then counted=false, released=true, phase RELEASED and each of the three counts decrements once. Malformed/repeated/unfunded end refuses before this tail.",
 "Release original counted obligation only. No foreign or successor scope may consume it. Retain negative/underfunded failure state honestly; this body does not call a native target close.", ["foreign-replay", "progress-states", "cohort-preflight"]),
"NativeRenderer$2#replacementEvent": (
 "guarded-event-delivery-with-getter-reentry", "Reject bad completed-replacement provenance before same-operation exclusion. Evaluating/already-claimed same operation returns void without send. Eligible path brackets getters with eventEvaluating finally-reset, claims once, performs interaction, rechecks original current/loss, then sends one exact textChange packet.",
 "Original field/record/generation/eventValue and mutation/fence must match. Getter loss/reentry cannot claim successor authority. Once delivery returns there is no fabricated native postcheck. Ordinary/Error propagation and prior claim state reflect the actual boundary reached.", ["identity-matrix", "getter-suffix-matrix"]),
"NativeRenderer$2#editorEnter": (
 "guarded-count-acquisition", "Valid exact fresh lease increments outstandingEditorNativeCalls once and returns void; null/foreign/entered/ended/unretained/MAX cases refuse without increment. Main thread is mandatory.",
 "This endpoint does not itself set lease.entered; the enclosing lease protocol must bind that transition and balance exit. Do not infer standalone repeated-call idempotence from a flag written by the caller.", ["progress-states", "identity-matrix"]),
"NativeRenderer$2#editorLeave": (
 "guarded-count-release", "Valid matching entered-and-ended lease with positive count decrements exactly once; invalid identity, phase or count refuses. Main-thread guard precedes state.",
 "Caller owns once-only lease completion. No manufactured target close occurs here; the original lease/callback/cleanup chain must establish that the decremented count is its own funded obligation.", ["progress-states", "foreign-replay"]),
"NativeRenderer$2#editorCloseAllowed": (
 "guarded-scalar-cleanup-permission", "Return true exactly when shared count is zero, commitFinish false, operation null and either no replacement or exact predecessor permission. Return false for each denied gate without closing anything.",
 "Exact record/attempt/replacement predecessor relationships matter; wrong thread refuses. Boolean permission is not a close receipt or proof of another owner's release.", ["progress-states", "foreign-replay"]),
"NativeRenderer$2#editorDrainBegin": (
 "guarded-cleanup-lease-acquisition", "Only absent drain, valid nonnull lease, exact record/field, retained ownership and close permission may store that exact lease and return void; invalid entry preserves existing drain.",
 "No native close or numeric count update occurs in this body. Main-thread guard, predecessor permission and actual enclosing cleanup must remain bound to the original lease.", ["progress-states", "foreign-replay"]),
"NativeRenderer$2#editorDrainEnd": (
 "guarded-cleanup-lease-release", "Matching nonnull current drain and record clears editorDrain and returns void; mismatch refuses without clearing another lease. A null/null direct misuse must not be labeled successful balanced release.",
 "Exact lease identity, main-thread guard and original record apply. Actual native cleanup completion comes from the enclosing protocol, not this scalar field clear.", ["progress-states", "foreign-replay"]),
"NativeRenderer$AttachmentJournal#<init>": (
 "callback-bearing-ordered-journal-construction", "Capture exact candidate, baseRecords iteration order, one NativeState per original record with position equal to preceding size; freeze states/count, parent snapshots, root children/width/height and old gate/canvas values.",
 "Constructor identity survives actual nested native getters. Capture result values at return, preserve arrays/order/content and old gate reference. No partially constructed journal may grant release authority. Allocation failure remains source-order-only until actual runtime witness exists.", ["constructor-before-registration", "journal-membership", "cohort-preflight"]),
"NativeRenderer$NativeState#<init>": (
 "callback-bearing-native-snapshot-construction", "Capture exact journal/position/record/binding/geometry and branch-dependent active Boolean; actual editable reference plus immutable text/composition, cloned drawable array, filled window position, bounds/measurements/enabled, selections/default -1, scroll/toggle/focus/pressed values.",
 "Typed mutable content must be copied at observation time, never derived later from a live reference. Constructor receiver/record identities stay exact across every real getter boundary; failed prefix cannot publish a complete capture or erase first fatal.", ["constructor-before-registration", "journal-membership", "getter-suffix-matrix"]),
"NativeRenderer$PreservationMembership#<init>": (
 "local-reference-pair-construction", "Return a fresh object whose final state and scope are exactly the supplied references. The body assigns both after Object initialization and performs no validation/native operation; null arguments are data at this constructor boundary.",
 "Construction alone grants no authority: later exact membership predicate must reject malformed pairing. Allocation precedes publication/registration/count acquisition; allocation-failure runtime injection remains pending.", ["constructor-before-registration", "journal-membership"]),
"NativeRenderer#beginFieldPreservationsV2": (
 "ordered-preservation-cohort-construction", "Require the original mutation; iterate previous states in order and skip non-field/unneeded preservation. Validate untouched membership/current targets/shadow/binding/base, allocate scope then membership before publishing references, acquire count, capture and revalidate exact base.",
 "Publish exact state/member/scope relationships once before callbacks. Catch RuntimeException/Error from begin/capture/exact, remember exact original failure and rethrow it. All earlier funded members survive partial failure; no later release or callback may run with an incomplete/foreign roster.", ["captured-A-refusal", "partial-A-entered-C-refusal", "constructor-before-registration", "fatal-chronology", "journal-membership"]),
"NativeRenderer#preservationMembershipV2": (
 "pure-ordered-membership-predicate", "Return false for null journal/states, length-count mismatch, null/wrong-journal/wrong-position state, scope without membership, forward flag without membership, mismatched state/scope/record/journal or missing forward flag; otherwise true in exact order, including a valid empty roster.",
 "Do not strengthen this scalar predicate into current-mutation authority. No fields/counts/callbacks change. Duplicate/reordered state tests must use actual position and reference identities, not equal metadata.", ["journal-membership", "malformed-custody"]),
"NativeRenderer#fieldPreservationCapturedV2": (
 "pure-captured-authority-predicate", "Return true only for exact renderer/candidate/journal/scope/record/field/input/editorFence and the identical candidate original TRANSACTION mutation, fence/token, with all nested leases null. Any listed mismatch returns false without mutation.",
 "An equal-token substitute original object is still foreign. Captured ownership is separate from current authority, counted state and completion permission. No native callbacks occur in the emitted body.", ["identity-matrix", "foreign-replay"]),
"NativeRenderer#preservationProvenanceV2": (
 "pure-foreign-versus-own-provenance-classifier", "Null states returns true only to classify malformed-own custody, never to authorize release. Skip null/wrong-journal state for this classifier; reject foreign captured member/scope or conflicting live field scope; return true for own malformed cases left to membership validation.",
 "Do not silently replace this predicate with full membership validity. Own malformed completion must take its terminal/funded failure path; foreign replay must remain inert. Preserve existing counts and references.", ["foreign-replay", "malformed-custody", "journal-membership"]),
"NativeRenderer#fieldPreservationIdentityV2": (
 "pure-captured-and-roster-identity-predicate", "Require captured-authority predicate and complete ordered membership predicate, then locate the exact record and return its forward flag AND exact same scope. Missing record returns false.",
 "Exact scope identity rather than equal captured metadata is mandatory. This body grants no fresh count and performs no callback or close; callers must separately validate current mutation and phase.", ["identity-matrix", "journal-membership", "foreign-replay"]),
"NativeRenderer#preservationCohortV2": (
 "pure-exact-count-cohort-predicate", "After valid membership count represented counted scopes; require candidate.heldPreservations==represented and global outstandingFieldPreservations==represented, represented within roster bounds, and shared native count>=represented.",
 "Test each equality and both bounds independently, including zero cohort and extra unrelated native work. Boolean true is not evidence that an uncounted scope was released or a target closed.", ["cohort-preflight", "progress-states", "no-scope"]),
"NativeRenderer#preservationFailureFundedV2": (
 "pure-held-failure-funding-predicate", "After valid membership count represented scopes; allow held>=represented while held remains nonnegative and <=roster count, global preservation count exactly held, and shared native count>=held.",
 "Held failure is deliberately weaker than a healthy exact cohort and must retain funded obligations. Do not collapse represented into held, erase unreleased counts, or label accepted funding as successful cleanup.", ["malformed-custody", "progress-states", "outcome-failures"]),
"NativeRenderer#finishV2": (
 "scalar-commit-tail-after-complete-preflight", "Reject wrong/used/unattached candidate or journal state before mutation, and reject foreign preservation provenance inertly. Evaluate complete membership/current operation/cohort and every scope's phase/flags/hooks/loss before the tail. Invalid own state terminalizes/gates/seals then throws; no partial success release.",
 "Success sets SUCCESS_IN_PROGRESS, marks all scopes committed/ended, publishes exact candidate packet/bytes/targets/plan/gate/environment/roster, retires candidate/pending/open state, releases every counted obligation once and sets SUCCESS_DONE. No native callback occurs in the successful scalar tail. Preserve original first fatal in actual caller cleanup.", ["three-success", "foreign-replay", "cohort-preflight", "journal-membership", "malformed-custody"]),
"NativeRenderer#validateAttachedV2": (
 "callback-precommit-validation-and-final-scalar-cohort-check", "Validate candidate/journal, then each actual scope.exact and original.current under its captured identities. Recheck complete cohort after all callable getters, then every final scalar identity/binding/phase/hook/loss before marking all scopes PRECOMMIT_READY.",
 "A getter's loss/reentry must not authorize the next record or successor mutation. No scope is marked ready until full validation succeeds; invalid snapshot/value/selection/composition/token must fail before commit and preserve original failure/cleanup obligations.", ["cohort-preflight", "getter-suffix-matrix", "identity-matrix", "journal-membership"]),
"NativeRenderer#rememberV2": (
 "local-first-primary-and-first-error-ledger", "Null is inert. First nonnull Throwable becomes primary; later failures never replace it. Independently, first Error becomes firstFatal; later Error never replaces it. Return void without native cleanup.",
 "Use exact exception references, including ordinary-before-Error and multiple-Error orders. This scalar ledger does not itself throw, close a target, release busy counts or establish enclosing cleanup order.", ["fatal-chronology", "outcome-failures"]),
}

assert __debug__ and not (HERE / "proposal.json").exists()
raw = copy_input(CHECKLIST, "complete-280-checklist.json")
roster = json.loads(raw)
subjects = [row for row in roster["subjects"] if row["class"] in OWNED_CLASSES]
assert len(subjects) == len(P) == 24
source = copy_input(SOURCE / NATIVE, "NativeRenderer.java")
test_name = "SelectedIdentityMembershipReviewControls"
test_bytes = copy_input(SOURCE / (TESTS + test_name + ".java"), test_name + ".java")
test_lines = test_bytes.decode().splitlines()
assertions = [{"line": i + 1, "text": line} for i, line in enumerate(test_lines) if "check(" in line or "refusedWithoutEffects(" in line]
copy_input(SOURCE / "verification/android-default-appearance-packaging/run-2/created-descriptor.json", "descriptor.json")
for leaf in ("android/view/View.java", "android/widget/TextView.java", "android/widget/EditText.java", "android/widget/Switch.java", "android/view/inputmethod/BaseInputConnection.java"):
    copy_input(SOURCE / ("native/android/tests/NativeOwnerV2ConcreteHostLeaves/" + leaf), "selected-leaves/" + leaf)
class_map = {}
for name in sorted(OWNED_CLASSES):
    class_map[name] = digest(copy_input(CLASSES / (name + ".class"), "classes/" + name + ".class"))
out = []
for row in subjects:
    key = row["class"].rsplit("/", 1)[1] + "#" + row["method"]
    applicability, result_oracle, identity_oracle, controls = P[key]
    assert digest(source)["sha256"] == row["source_sha256"]
    assert class_map[row["class"]]["sha256"] == row["class_sha256"]
    native_sites = []
    for invocation in row["actual_invocations"]:
        if invocation["target"]["owner"].startswith("android/"):
            target = invocation["target"]
            sid = row["id"] + "@" + str(invocation["bci"]) + ":" + invocation["mnemonic"] + ":" + target["owner"] + "#" + target["name"] + target["descriptor"]
            native_sites.append({"id": sid, "class": row["class"], "method": row["method"], "descriptor": row["descriptor"], "bci": invocation["bci"], "opcode": invocation["mnemonic"], "callee": target,
                                 "callback_applicability": "selected-leaf-callback-requires-exact-final-join" if target["name"] in HOOKED_LEAVES else "unhooked-finite-helper",
                                 "typed_result_oracle": NATIVE_ORACLES[target["name"]],
                                 "oracle_independence": "Populate expected literal fields/reference tokens from controlled fixture configuration before execution. Never derive expected values from emitted observed rows. Resolve actual receiver implementation; no method-name-only dispatch transfer."})
    candidates = []
    for control in controls:
        dispatch = [{"line": i + 1, "text": line} for i, line in enumerate(test_lines) if 'case "' + control + '"' in line]
        assert len(dispatch) == 1, (key, control)
        candidates.append({"test_source_sha256": digest(test_bytes)["sha256"], "test_source": "inputs/" + test_name + ".java",
                           "entry_class": "dev.mixer.android." + test_name, "entry_method": "main", "entry_descriptor": "([Ljava/lang/String;)V",
                           "args": [control, "<selected-descriptor-path>"],
                           "assertion_source_evidence": {"dispatch": dispatch, "assertion_index": "witness-assertion-index.json", "scope": "Exact original control source candidate only; assertions are not treated as coverage without actual method/case execution joins"}})
    direct_callback_ids = [site["id"] for site in native_sites if site["callback_applicability"].startswith("selected-leaf")]
    unhooked_ids = [site["id"] for site in native_sites if site["callback_applicability"] == "unhooked-finite-helper"]
    base = {"oracle": {"typed_result": result_oracle, "identity_relations": identity_oracle,
                       "count_gate_cleanup_fatal_requirements": "Require actual before/after original subject identities and exact counters; preserve first primary/first Error and held failures where this method participates. Do not manufacture callbacks, close effects or runtime allocation-failure evidence for scalar bodies."},
            "witness_candidates": candidates, "execution_join": None,
            "pending_reason": "Fresh final selected producer must execute the exact control, observe this exact subject/context and assert independent typed/result/state oracles; candidate source references alone confer no behavior acceptance."}
    cases = [{"id": "renderer-finite-source-invariants", "kind": "finite-invariant", "required_states": ["exact-valid-reference-and-value", "each-source-guard-or-branch", "unchanged-original-failure-identity"],
              "applicable_native_site_ids": unhooked_ids, "expected_outcome_scope": "actual-enclosing-typed-outcome" if native_sites else "finite-scalar",
              "no_own_native_callback_rationale": None if native_sites else "No direct Android invocation in this exact emitted method; helper/event calls remain explicit enclosing obligations.", **base}]
    if direct_callback_ids:
        cases.append({"id": "renderer-actual-native-constructor-boundaries", "kind": "callback-state", "required_states": CALLBACK_STATES,
                      "applicable_native_site_ids": direct_callback_ids, "expected_outcome_scope": "native-return", **base})
    cases.append({"id": "renderer-original-cohort-control", "kind": "enclosing-original-control", "required_states": ["fresh-original-control-with-exact-subject-join"],
                  "applicable_native_site_ids": [], "expected_outcome_scope": "actual-enclosing-typed-outcome",
                  "no_own_native_callback_rationale": "Original cohort/authority/cleanup control is an enclosing proof obligation. Any transitive native callback must be resolved to its own exact emitted tuple and all seven states, never transferred by source line or method name.", **base})
    out.append({k: row[k] for k in ("id", "class", "method", "descriptor", "source_sha256", "class_sha256")} | {
        "applicability": applicability, "required_cases": cases, "native_sites": native_sites,
        "source_rationale": {"source_witness": row["source_witness"], "full_selected_source": "inputs/NativeRenderer.java", "actual_invocations": row["actual_invocations"], "actual_instructions": row["actual_instructions"], "manual_disposition": result_oracle + " " + identity_oracle},
        "original_categories": row["categories"], "original_required_case_ids": row["required_semantic_cases"],
        "original_case_dispositions": [{"id": old, "status": "retained-needs-source-specific-finite-or-enclosing-join", "required_by": [case["id"] for case in cases], "not_deleted_or_runtime_accepted": True} for old in row["required_semantic_cases"]],
        "transitive_native_and_event_site_resolution_pending": any(i["target"]["owner"].startswith("dev/mixer/") for i in row["actual_invocations"]),
        "runtime_allocation_failure_evidence": "pending; source ordering is not a runtime injection pass"})
save("witness-assertion-index.json", {"test_source": digest(test_bytes), "assertions": assertions, "scope": "Retained whole-source assertion locations, not execution coverage"})
proposal = {"schema": 1, "status": "source-specific-24-renderer-obligation-proposal-review-pending", "source_context": "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd",
            "source_revision_context": "6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2", "exact_original_subject_ids_preserved": True, "subjects": out,
            "callback_states": CALLBACK_STATES, "input_checklist": digest(raw), "input_overlay_seal_sha256": "0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b",
            "limitations": ["No product, compiler or control executed by this preparation", "Every runtime join remains null", "No subject/case is removed from the280 roster", "No authority or release is granted by static source/bytecode matching", "Original allocation failures remain pending actual runtime evidence", "Indirect helpers/events require exact callback or enclosing-outcome joins; scalar names do not create native callback claims"],
            "initial_draft_correction": "Initial source proposal overclassified unhooked getters as callbacks. Direct inspection of the exact selected leaves narrows callback-bearing leaf names to getWidth/getHeight/getText/getLocationInWindow and adds independent typed per-site value/content oracles. Initial draft is retained and unselected.",
            "full_policy_matrix_canonical_native_OTA_GA_accepted": False, "python": sys.version,
            "command": [sys.executable, "-B", str(Path(__file__).relative_to(REPO))], "preparer": digest(Path(__file__).read_bytes())}
save("proposal.json", proposal)
print(json.dumps({"subjects": len(out), "required_cases": sum(len(s["required_cases"]) for s in out), "direct_native_sites": sum(len(s["native_sites"]) for s in out), "runtime_joins": 0, "proposal": digest((HERE / "proposal.json").read_bytes())}))
