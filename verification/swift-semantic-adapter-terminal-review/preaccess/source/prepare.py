"""Reviewer-owned preaccess custody/corpus generation; old source is data only."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1]
MAX = (1 << 64) - 1


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def command(name, argv):
    directory = OUT / "commands"
    directory.mkdir(exist_ok=True)
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    (directory / (name + ".stdout")).write_bytes(result.stdout)
    (directory / (name + ".stderr")).write_bytes(result.stderr)
    dump(directory / (name + ".json"), {
        "argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
        "stdout_sha256": digest(result.stdout),
        "stderr_sha256": digest(result.stderr),
    })
    if result.returncode:
        raise RuntimeError((name, result.returncode))
    return result.stdout


def verify_seal(name, seal_path, expected, base):
    raw = (ROOT / seal_path).read_bytes()
    assert digest(raw) == expected, name
    data = json.loads(raw)
    total = 0
    for member in data["members"]:
        path = base / member["path"]
        assert path.resolve().is_relative_to(ROOT)
        content = path.read_bytes()
        assert len(content) == member["bytes"], path
        assert digest(content) == member["sha256"], path
        total += len(content)
    return {"name": name, "seal_path": seal_path, "seal_sha256": expected,
            "members_verified": len(data["members"]), "bytes_verified": total}


def snapshot(path):
    original = ROOT / path
    content = original.read_bytes()
    destination = OUT / "original-inputs" / path
    # All executable-looking source snapshots are deliberately suffixed .txt.
    if destination.suffix in {".rs", ".py"}:
        destination = destination.with_name(destination.name + ".txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return {"path": path, "bytes": len(content), "sha256": digest(content),
            "snapshot": str(destination.relative_to(OUT))}


def build_source_obligations():
    analyzer = "verification/swift-semantic-adapter-prerequisite/inputs/13-analyzer.rs"
    envelope = "verification/swift-semantic-adapter-prerequisite/inputs/14-envelope.rs"
    rows = [
        ("A01", analyzer, 108, 122, "Arena allocation/capacity/budget initialization errors propagate from outer core before observation owners."),
        ("A02", analyzer, 165, 180, "Budget construction/setup/report reservation failures have named errors and no aggregate when propagated by outer core."),
        ("A03", analyzer, 199, 222, "Read/EOF finite attempts produce IO zero/error/overreported/exhausted or trailing-input errors; call site decides propagation."),
        ("A04", analyzer, 349, 362, "Coordinate updates occur only after shape/coordinate checks and advance framed count; ordinary Failure kind14 is exempt from body identity equality."),
        ("A05", analyzer, 363, 380, "Footer schema/flags/coordinate errors occur after stored/flags mutation; limited walk omits the final coordinate equality check."),
        ("A06", analyzer, 418, 443, "Initial input/output File metadata, regularity, position and distinct identity failures preserve exact stage/code/offset."),
        ("A07", analyzer, 425, 428, "Stream/profile/context stamp drift returns DRIFT at ADMISSION_STAGE2, offset0/record0/reserved0 at child input layer."),
        ("A08", analyzer, 445, 464, "Report zero/echo/reservation/access and prewrite metadata checks can fail before physical output; no semantic report fields exist."),
        ("A09", analyzer, 465, 485, "Report write/attempt exhaustion/metadata/position/length/identity failures propagate; partial bytes are failed output."),
        ("E01", envelope, 127, 159, "Readability then private spent/debit guards precede prior state reads; absent guard returns poison0, underfunded present returns Steps0."),
        ("E02", envelope, 227, 251, "Existing reason mapping/project uses zero suppressed extent and always preserves p.debit; its16word observation is not the new32word schema."),
        ("E03", envelope, 252, 263, "Existing finalizer first catches input error, then framing coherence, then reply_valid0/other; none grants fixture success."),
        ("E04", envelope, 264, 273, "Poison precedes CAP and any state read; limited poison boundary differs from normal poison; malformed replies yield unavailable."),
        ("E05", envelope, 274, 283, "Existing ordered limited, refusal, CAP, checked expected state, closed/incomplete branches are distinct; CAP returns before expected-state read."),
        ("E06", envelope, 284, 297, "Pending latch is absorbing; actual reply debit audit distinguishes full425 versus prepaid guard0 responses."),
        ("E07", envelope, 298, 315, "Header then setup534/finish47/guard112, Candidate initialization, preflight8192 and combined charge471 precede record read; debit tracks successful payments."),
        ("E08", envelope, 316, 330, "Record read/field/coordinate validation precedes private record construction; reply audit can install poison and later leaf calls stop."),
        ("E09", envelope, 331, 348, "Limited drain/footer/EOF remains bounded and fallible; complete is installed only after successful EOF."),
        ("E10", envelope, 350, 358, "Input metadata/admission/context/profile/walk/stability failures are returned as observe_inputs Result, not automatically outer Err."),
        ("E11", envelope, 360, 369, "Outer Budget/T42/F42/output safety/arena errors use ? before aggregate; no envelope debit is invented."),
        ("E12", envelope, 370, 378, "Child core catches observe_inputs errors as framing Decision/observation and calls envelope finalizer; framing counts are separate."),
        ("E13", envelope, 379, 384, "write_report ? and post-report budget excess propagate outer Err; aggregate exists only after both succeed."),
        ("O01", "verification/swift-semantic-adapter-prerequisite/inputs/26-verification__swift-ordered-retention-diagnostic-rust__observer.rs", 84, 109, "Failure preserves optional source function cursor and payload-derived operation; no requested-function equality may be inferred."),
        ("S01", "verification/swift-semantic-adapter-prerequisite/inputs/24-candidate__src__experimental_swift_reactor__cache.rs", 1926, 1954, "Acquire observation precedes header check/meter pin; a failure can precede requested cursor adoption."),
    ]
    result = []
    for key, path, first, last, obligation in rows:
        content = (ROOT / path).read_bytes()
        excerpt = b"".join(content.splitlines(keepends=True)[first - 1:last])
        assert excerpt
        result.append({"id": key, "path": path, "first_line": first,
                       "last_line": last, "source_sha256": digest(content),
                       "excerpt_sha256": digest(excerpt), "obligation": obligation})
    return result


def build_cases(words):
    assert len(words) == 32
    ix = {word: index for index, word in enumerate(words)}
    zeros = [0] * 32
    # These are independent projector fixtures. A later selector must explicitly
    # choose a projection mode; parameters do not silently fix old R1 ambiguity.
    live = [1, 0, 27, 27, 0, 27, 211, 233, 0, MAX, 2, 95, 0, 9,
            MAX, 0, 0, 0, MAX, MAX, 0, 512 + 256 + 27 * 7680,
            1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    active = live.copy()
    for key, value in {"boundary": 2, "active_operation": 7,
                       "requested_function": 17, "held_pins": 1,
                       "active_plan_cell": 17, "selected_mask": 3,
                       "taken_mask": 1, "committed_mask": 1,
                       "pending_victim": 1, "destination": 0,
                       "tail_unknown": 1}.items():
        active[ix[key]] = value
    suppression_vectors = []
    for name, setup, finish, charged in [("unpaid",0,0,0),
                                       ("finish-only",0,1,0),
                                       ("setup-finish-zero-calls",1,1,0),
                                       ("charged-before-read-no-loan",1,1,1),
                                       ("latched-later-charges",1,1,31)]:
        row = zeros.copy()
        row[0:2] = [0, 3]
        row[21:24] = [512 * setup + 256 * finish + 7680 * charged,
                      setup, finish]
        suppression_vectors.append({"id": "Z-" + name,
                                    "mode": "suppressed",
                                    "boundary_reason_are_projector_parameters": True,
                                    "setup_paid": setup, "finish_paid": finish,
                                    "charged_records": charged,
                                    "expected32": row})
    projection_vectors = suppression_vectors + [
        {"id": "I-distinct-live-idle", "mode": "live-idle",
         "boundary_reason_are_projector_parameters": True, "expected32": live},
        {"id": "C-distinct-live-cap", "mode": "live-active-cap",
         "boundary_reason_are_projector_parameters": True, "expected32": active}]
    rejected = []
    z = suppression_vectors[-1]["expected32"]
    for index in list(range(2, 21)) + [24, 25]:
        bad = z.copy(); bad[index] = 1000 + index
        rejected.append({"id": "stale-suppressed-" + words[index],
                         "mode": "suppressed", "base_vector": suppression_vectors[-1]["id"],
                         "bad32": bad, "expected32": z,
                         "invariant": "suppressed extent word must be zero"})
    for index in range(26, 32):
        for value in [1, MAX]:
            bad = active.copy(); bad[index] = value
            rejected.append({"id": "authority-reserved-" + words[index] + "-" + str(value),
                             "mode": "live-active-cap", "base_vector": "C-distinct-live-cap",
                             "bad32": bad, "expected32": active,
                             "invariant": "four authority and two reserved words are always zero"})
    for index in [8, 9, 14, 18, 19]:
        for value in [0, 17, MAX]:
            if value == live[index]: continue
            bad = live.copy(); bad[index] = value
            rejected.append({"id": "idle-stale-" + words[index] + "-" + str(value),
                             "mode": "live-idle", "base_vector": "I-distinct-live-idle",
                             "bad32": bad, "expected32": live,
                             "invariant": "live Idle uses operation0 and requested/plan/pending/destinationMAX"})
    for fixture in suppression_vectors[1:]:
        for index in [21, 22, 23]:
            if fixture["expected32"][index] == 0: continue
            bad = fixture["expected32"].copy(); bad[index] = 0
            rejected.append({"id": "refund-" + fixture["id"] + "-" + words[index],
                             "mode": "suppressed", "base_vector": fixture["id"],
                             "bad32": bad, "expected32": fixture["expected32"],
                             "invariant": "suppression cannot refund paid public semantic cost or erase paid flags"})
    # Moving two distinct active coordinates is a compact projection-index oracle.
    for a, b in [(2,3),(5,6),(6,7),(8,9),(10,11),(11,12),(12,13),
                 (14,15),(15,16),(17,18),(18,19),(20,21),(22,24)]:
        bad = active.copy(); bad[a], bad[b] = bad[b], bad[a]
        if bad == active: continue
        rejected.append({"id": "word-swap-" + words[a] + "-" + words[b],
                         "mode": "live-active-cap", "base_vector": "C-distinct-live-cap",
                         "bad32": bad, "expected32": active,
                         "invariant": "32word identity and ordering are fixed"})
    scenarios = []
    def add(key, family, given, requirements, unresolved=None):
        scenarios.append({"id": key, "family": family, "given": given,
                          "requirements": requirements,
                          "original_contract_decision_required": unresolved or []})
    for stage in ["Budget", "T42", "F42", "semantic-finish256",
                  "semantic-setup512", "output-safety", "arena-allocation",
                  "arena-capacity", "context", "profile", "header",
                  "envelope-setup534", "envelope-finish47", "G112", "semantic-guard128"]:
        add("early-"+stage, "early-funding", {"failure_at":stage,"semantic_calls":0},
            ["No fabricated state or initialized nonce.",
             "Actual successful reservations determine debit/flags only.",
             "No semantic read/loan without the required owned funding."],
            ["Exact outer Err tuple versus returned suppressed outcome, with old-child behavior documented."])
    for state in ["empty-admitted-stream", "zero-leaf-reply", "absent-private-state",
                  "unreadable-private-state", "stale-private-state",
                  "malformed-status", "contradictory-status-reason", "invalid-reply-debit",
                  "invalid-paid-flags", "nonzero-reserved", "invalid-private-budget"]:
        for finish in ["coherent-complete", "coherent-limited", "CAP"]:
            add("state-"+state+"-"+finish, "state-normalization",
                {"state":state,"finish":finish,"read_trap_on_unavailable":True},
                ["No successful initialized fixture from absent state.",
                 "Poison/unavailable normalization occurs before ineligible state reads.",
                 "Authority/reserved remain0 and paid costs stay exact."],
                ["Exact normalized boundary/reason and zero versus IdleMAX projection for this unavailable state."])
    tails = ["legal-release-phase-tail", "successful-looking-later-reply", "repeated-Failure",
             "envelope-refusal", "envelope-unavailable", "envelope-poison",
             "envelope-invalid-reply-debit", "framing-replay-limit", "framing-IO-limit",
             "CAP", "closed-nonCAP", "late-footer-error", "late-read-error",
             "late-input-drift", "report-write-error"]
    for first in ["ordinary-refusal", "first-Failure"]:
        for tail in tails:
            add("absorbing-"+first+"-"+tail, "terminal-overlap",
                {"checked_snapshot_records":27,"terminal_record":28,
                 "first_terminal":first,"tail":tail,"tail_last_record":31,
                 "charged_records":31,"semantic_calls_after_terminal":0},
                ["No resumed semantic dispatch or silent upgrade to observed completion.",
                 "Failure record is excluded from cache_state_records.",
                 "Late invalidating input/output cannot expose a successful earlier snapshot.",
                 "Coordinate retention/suppression and paid charges are explicit."],
                ["Ordered winner between first terminal and later tail fault, exact32words or exact outerErr/noaggregate."])
    for error in ["read-zero", "read-IO", "read-overreported", "read-exhausted",
                  "footer-schema", "footer-flags", "footer-coordinate", "EOF-trailing",
                  "EOF-exhausted", "stream-drift", "profile-drift", "context-drift",
                  "report-reserve", "report-arena-access", "output-precheck",
                  "write-zero", "write-overreported", "write-IO", "write-exhausted",
                  "postwrite-stamp", "postwrite-position", "postwrite-length-drift",
                  "postwrite-identity-drift", "postreport-used-exceeds-limit"]:
        add("error-"+error,"outer-error-partition",
            {"error":error,"prior_snapshot_records":27,"prior_failure_record":28,
             "partial_report_possible":error.startswith("write") or error.startswith("post")},
            ["Report propagation errors return Err with no aggregate/observation.",
             "A partial/full physical report does not constitute returned success.",
             "Caught input errors must be distinguished from outer Err by actual source path."],
            ["Exact AnalyzerError code/stage/offset/record/reserved and caught-versus-propagated new-boundary choice."])
    for state in ["open-acquire", "open-plan", "open-Take", "open-build", "live-pins"]:
        add("CAP-"+state,"completion-boundary",{"state":state,"CAP":True},
            ["Retain checked synthetic cut; do not close/clear active state or pins.",
             "tail_unknown1; all authority/reserved0."],
            ["Exact active fields and complete32word cut projection."])
    for state in ["Idle-closed", "nonIdle-closed", "flags2", "complete-and-limited",
                  "inputOkFalse-complete", "inputOkTrue-limited", "expected-mask-read-fails"]:
        add("completion-"+state,"completion-boundary",{"state":state},
            ["Invalid coherence cannot become successful CAP/closed observation.",
             "Expected-state reads are branch-eligible and checked.",
             "Live Idle sentinels differ from suppressed all-zero extent."],
            ["Exact ordering/read set/boundary/reason/projection."])
    unresolved = [
        "new-boundary early setup/context/profile/header caught-versus-propagated errors",
        "absent/unreadable/stale/malformed exact boundary/reason and state-read eligibility",
        "first-refusal/Failure versus later envelope poison/refusal/unavailable and framing limitation",
        "late input error aggregate suppression versus additive outer Err",
        "stop/failure coordinate semantics and whether terminal state remains fixture_state_observed",
        "tail_unknown for absence/refusal/poison/limited and CAP after prior latch",
        "OutputUnavailable scope, including no returned observation on outer Err",
    ]
    return {"schema":1,"scope":"independent pre-correction source-contract controls only",
            "word_order":words,"MAX":MAX,
            "projection_vectors":projection_vectors,
            "rejected_full32_counterexamples":rejected,
            "terminal_scenarios":scenarios,
            "unresolved_original_decisions":unresolved,
            "not_Rust_or_product_test_evidence":True,
            "producer_models_or_test_expectations_imported":False}


def main():
    seals = [
        verify_seal("original", "verification/swift-semantic-adapter-prerequisite/seal.json",
                    "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba", ROOT),
        verify_seal("old-preaccess", "verification/swift-semantic-adapter-contract-review/preaccess/seal.json",
                    "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9",
                    ROOT / "verification/swift-semantic-adapter-contract-review/preaccess"),
        verify_seal("old-review-1", "verification/swift-semantic-adapter-contract-review/review-1/seal.json",
                    "d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02",
                    ROOT / "verification/swift-semantic-adapter-contract-review/review-1"),
    ]
    dump(OUT / "original-input-custody-audit.json", seals)
    paths = ["AGENTS.md", "PLAN.md", "mixer-product-plan.md",
             "docs/swift-semantic-adapter-prerequisite.md",
             "docs/swift-semantic-adapter-contract-review.md",
             "verification/swift-semantic-adapter-prerequisite/seal.json",
             "verification/swift-semantic-adapter-prerequisite/contract.json",
             "verification/swift-semantic-adapter-prerequisite/source-seams.json",
             "verification/swift-semantic-adapter-prerequisite/input-manifest.json",
             "verification/swift-semantic-adapter-contract-review/preaccess/seal.json",
             "verification/swift-semantic-adapter-contract-review/preaccess/plan.md",
             "verification/swift-semantic-adapter-contract-review/review-1/seal.json",
             "verification/swift-semantic-adapter-contract-review/review-1/findings.json",
             "verification/swift-semantic-adapter-contract-review/review-1/audit.json"]
    paths += ["verification/swift-semantic-adapter-prerequisite/inputs/" + name for name in [
        "13-analyzer.rs", "14-envelope.rs",
        "23-candidate__src__experimental__cache__borrowed.rs",
        "24-candidate__src__experimental_swift_reactor__cache.rs",
        "25-verification__swift-ordered-retention-diagnostic-rust__writer.rs",
        "26-verification__swift-ordered-retention-diagnostic-rust__observer.rs",
        "27-verification__swift-ordered-retention-diagnostic-rust__source-code-table.json"]]
    inputs = [snapshot(path) for path in paths]
    dump(OUT / "input-manifest.json", inputs)
    bindings = build_source_obligations()
    dump(OUT / "source-obligations.json", bindings)
    # Literal source derivation, independently authored before correction access.
    # Symbolic offset names are tied to the observed call-site variables; the
    # correction must define any deliberate new-boundary changes explicitly.
    child_errors = [
        ("budget-new", [4,1,0,0,0], "outer-Err"),
        ("outer-output-input-stamp", [6,2,0,0,0], "outer-Err"),
        ("outer-output-stamp-position", [6,8,0,0,0], "outer-Err"),
        ("outer-output-ineligible", [16,8,"position",0,0], "outer-Err"),
        ("outer-output-identity", [15,2,0,0,0], "outer-Err"),
        ("arena-allocation", [2,1,0,0,0], "outer-Err"),
        ("arena-capacity", [3,1,0,0,0], "outer-Err"),
        ("context-binding", [15,3,0,0,0], "caught-input-Err-framing-Unavailable"),
        ("input-stable-drift", [14,2,0,0,0], "caught-input-Err-framing-Invalid"),
        ("record-schema", [10,6,"512+128*zero_based_index","index+1",0], "caught-input-Err-framing-Invalid"),
        ("record-coordinate", [12,6,"512+128*zero_based_index","index+1",0], "caught-input-Err-framing-Invalid"),
        ("footer-schema", [10,7,"length-512",0,0], "caught-input-Err-framing-Invalid"),
        ("footer-flags", [13,7,"length-512+72",0,0], "caught-input-Err-framing-Invalid"),
        ("footer-coordinate", [12,7,"length-512",0,0], "caught-input-Err-framing-Invalid"),
        ("input-read-IO", [6,"call_stage","offset+done",0,0], "caught-input-Err-framing-Invalid"),
        ("input-read-zero", [8,"call_stage","offset+done",0,0], "caught-input-Err-framing-Invalid"),
        ("input-read-overreported", [9,"call_stage","offset+done",0,0], "caught-input-Err-framing-Invalid"),
        ("input-read-exhausted", [7,"call_stage","offset+done",0,0], "caught-input-Err-framing-Invalid"),
        ("report-prewrite-stamp-position", [6,8,0,0,0], "outer-Err"),
        ("report-prewrite-ineligible", [16,8,"output_position",0,0], "outer-Err"),
        ("report-reserve", [4,8,0,0,0], "outer-Err"),
        ("report-write-IO", [6,8,"done",0,0], "outer-Err"),
        ("report-write-zero", [8,8,"done",0,0], "outer-Err"),
        ("report-write-overreported", [9,8,"done",0,0], "outer-Err"),
        ("report-write-exhausted", [7,8,"done",0,0], "outer-Err"),
        ("report-postwrite-stamp-position", [6,8,"done",0,0], "outer-Err"),
        ("report-postwrite-drift", [14,8,"done",0,0], "outer-Err"),
        ("report-post-used-budget", [4,8,0,0,0], "outer-Err"),
    ]
    dump(OUT / "accepted-child-error-partition.json", {
        "schema":1,"scope":"source-derived accepted child behavior only; no execution",
        "AnalyzerError_word_order":["code","stage","offset","record","reserved"],
        "source_obligations":["A01","A02","A03","A05","A06","A07","A08","A09","E10","E11","E12","E13"],
        "rows":[{"id":name,"error":error,"child_core_partition":partition,
                 "aggregate_exists_if_report_succeeds":partition.startswith("caught"),
                 "typed_observation_returned_on_outer_Err":False}
                for name,error,partition in child_errors],
        "new_boundary_behavior_must_be_explicitly_reviewed":True,
        "Rust_product_tests":0})
    contract = json.loads((ROOT / "verification/swift-semantic-adapter-prerequisite/contract.json").read_text())
    corpus = build_cases(contract["observation"]["words"])
    dump(OUT / "cases.json", corpus)
    versions = {}
    for name, argv in [("python-version", [sys.executable, "--version"]),
                       ("git-version", ["git", "--version"]),
                       ("revision", ["git", "rev-parse", "HEAD"]),
                       ("platform", ["uname", "-a"])]:
        versions[name] = command(name, argv).decode().strip()
    # These are read-only raw source inspections, not old-code execution.
    for name, path in [("original-contract", paths[6]),
                       ("accepted-analyzer", "verification/swift-semantic-adapter-prerequisite/inputs/13-analyzer.rs"),
                       ("accepted-envelope", "verification/swift-semantic-adapter-prerequisite/inputs/14-envelope.rs")]:
        command(name, ["cat", path])
    tree = digest("".join(item["path"] + "\0" + item["sha256"] + "\n"
                          for item in sorted(inputs, key=lambda row: row["path"])).encode())
    receipt = {"schema":1,"phase":"preaccess-not-correction-review",
               "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "model":"gpt-6.1-sol","reasoning_effort":"xhigh","context":"fresh",
               "versions":versions,"context_revision":versions["revision"],
               "context_revision_is_not_a_live_source_closure":True,
               "input_tree_digest_sha256":tree,"inputs":len(inputs),
               "original_seals_verified":seals,
               "terminal_scenarios":len(corpus["terminal_scenarios"]),
               "numeric_projection_vectors":len(corpus["projection_vectors"]),
               "full32_rejected_counterexamples":len(corpus["rejected_full32_counterexamples"]),
               "actual_child_source_obligations":len(bindings),
               "correction_contents_accessed":False,
               "producer_model_imports_or_execution":False,
               "Rust_product_tests":0,"native_device_GA":False,
               "live_VM_read_or_run":False,
               "process_discovery_or_UI_capture_native_calls":0,
               "git_index_commit_push_mutations":0,
               "cleanup":"No builds, native/capture instances, or owned persistent processes started; only synchronous read/custody/finite-review commands."}
    dump(OUT / "receipt.json", receipt)
    print(json.dumps({key:receipt[key] for key in ["inputs","input_tree_digest_sha256",
         "terminal_scenarios","numeric_projection_vectors","full32_rejected_counterexamples",
         "actual_child_source_obligations","Rust_product_tests","correction_contents_accessed"]},indent=2))


if __name__ == "__main__":
    main()
