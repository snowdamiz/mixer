#!/usr/bin/env python3
"""Audit immutable evidence, remove five owned outputs, and seal the review."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import re
import sys

P = Path(__file__).resolve().parent
R = P.parents[1]
PRODUCER = R / "verification/swift-guarded-snapshot-root-result-lifetime-implementation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path, base=P):
    data = path.read_bytes()
    return {"path": str(path.relative_to(base)), "bytes": len(data), "sha256": sha(data)}


def write(name, value):
    with (P / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def verify_members(base, members):
    for member in members:
        data = (base / member["path"]).read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], member["path"]


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True


assert sha((PRODUCER / "seal.json").read_bytes()) == "7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4"
producer_seal = json.loads((PRODUCER / "seal.json").read_text())
verify_members(PRODUCER, producer_seal["members"])
assert len(producer_seal["members"]) == 336
assert sha((P / "proposed-command-roster.json").read_bytes()) == "c307bb5a6bf6f1abbf1c4508d0a66c696e30d99ab79011eac73c640facc11d42"
assert sha((P / "command-freeze.json").read_bytes()) == "f7768b2f7f29515e43a853d75daacf2afacbc57aa46690ae53091b4b279f8224"
verify_members(P, json.loads((P / "command-freeze.json").read_text())["members"])
for name, sub in [("independent-vm-manifest.json", "vm"), ("independent-host-manifest.json", "host")]:
    manifest = json.loads((P / name).read_text())
    verify_members(P / "source" / sub, manifest["members"])
    assert len([f for f in (P / "source" / sub).rglob("*") if f.is_file()]) == manifest["member_count"]
instrumentation = json.loads((P / "instrumentation.json").read_text())
loader = "src/experimental_swift_reactor/retained_profile_loader_v1.rs"
assert (P / "source/vm" / loader).read_text().replace(instrumentation["insertion"], "") == (PRODUCER / "source/vm" / loader).read_text()
release = R / "verification/swift-semantic-adapter-root-review/guarded-snapshot-root-result-lifetime-independent-execution-release.json"
assert sha(release.read_bytes()) == "6d3f033e1cffa2b2f55a3ad8c055102c94cd5c5fc8d619a9ff9629a5ed54387c"
roster = json.loads((P / "proposed-command-roster.json").read_text())
assert sorted(f.name for f in (P / "commands").iterdir()) == sorted(c["id"] for c in roster["commands"])
receipts = []
diagnostics = []
semantic = {
    "IN02-static": "The genuine facade return requires original 'root to outlive 'static. This is the intended original-root constraint, not a missing generic/name/cfg or startup refusal.",
    "IN03-foreign-substitution": "Actual returned data is 'original while signature demands unrelated 'foreign. The compiler explicitly suggests the absent original:foreign outlives bound. P01's correct original-root foreign-expected helper compiles.",
    "IN04-lexical-core": "E0597 points to borrowing original_root for actual admission. The original inner ledger is dropped while the same actual generic-core refusal/proof/guard result is stored outside; foreign root remains alive. Acquisition owner was consumed before attempted return. No alternate ownership machine or product File owner fabrication.",
    "IN05-short-borrow": "View is 'view but requested return is 'root; the compiler requires the absent view:root reverse bound. P01 returns the legitimate short view and references to actual originals.",
    "IN06-own-leaf-ok": "E0507 rejects moving the original SnapshotScopeFinishV1 out of the shared primary borrow after the genuine fixed consuming operation. Actual type is neither Copy nor Clone; P01 permits its shared reference. This is compile-only, not a leaf Ok runtime witness.",
    "IN07-own-leaf-err": "E0507 rejects moving original SnapshotPreScopeFailureV1 out of the shared primary borrow after the genuine fixed consuming operation. Actual type is neither Copy nor Clone; P01 permits its shared reference. This is compile-only, not a leaf Err/adoption runtime witness.",
}
for command in roster["commands"]:
    directory = P / "commands" / command["id"]
    receipt = json.loads((directory / "receipt.json").read_text())
    plan = json.loads((directory / "plan.json").read_text())
    assert receipt["success"] and not receipt["failure_classifications"]
    assert receipt["child_reaped"] and receipt["exact_owned_group_absent"] and receipt["postrun_pins_verified"]
    assert receipt["seconds"] <= 55 and receipt["captured_bytes_within_caps"]
    assert group_absent(receipt["owned_pgid"])
    assert plan["argv"] == command["argv"]
    assert plan["roster_sha256"] == sha((P / "proposed-command-roster.json").read_bytes())
    for name in ["stdout", "stderr"]:
        data = (directory / name).read_bytes()
        assert len(data) == receipt["outputs"][name]["bytes"] and sha(data) == receipt["outputs"][name]["sha256"]
    receipts.append({"id": command["id"], "kind": command["kind"], "exit": receipt["exit"], "seconds": receipt["seconds"], "receipt": row(directory / "receipt.json"), "owned_group_absent_rechecked": True})
    if command["id"] in semantic:
        text = (directory / "stderr").read_text()
        assert "could not find" not in text and "not found in this scope" not in text
        diagnostics.append({"id": command["id"], "status": "intended-semantic-boundary-independently-reviewed", "stderr": row(directory / "stderr"), "error_codes": re.findall(r"error\[(E[0-9]+)\]", text), "semantic_review": semantic[command["id"]]})
history_stderr = (P / "commands/IN01-history/stderr").read_text()
assert json.loads((P / "commands/IN01-history/receipt.json").read_text())["exit"] == 0
assert "the same lifetime is hidden here" in history_stderr and "OwnedCorrelationOutcomeV1<'root>" in history_stderr

host_reviews = []
producer_host_reviews = json.loads((PRODUCER / "host-review.json").read_text())["runs"]
for mode in ["debug", "opt2"]:
    directory = P / "commands" / ("run-" + mode)
    stdout = (directory / "stdout").read_text()
    stderr = (directory / "stderr").read_text()
    assert "42 passed; 0 failed; 0 ignored; 0 measured; 470 filtered out" in stdout
    names = [line[5:-7] for line in stdout.splitlines() if line.startswith("test ") and line.endswith(" ... ok")]
    assert len(names) == 42 and len(set(names)) == 42
    independent_names = [name for name in names if "::independent_ir02_" in name]
    assert len(independent_names) == 4
    previous = next(x for x in producer_host_reviews if x["mode"] == mode)
    assert sorted(name for name in names if name not in independent_names) == sorted(previous["test_names"])
    cases = [line for line in stderr.splitlines() if line.startswith("INDEPENDENT_IR02 ")]
    assert len(cases) == 22
    assert {kind: sum(line.startswith("INDEPENDENT_IR02 " + kind + " ") for line in cases) for kind in ["matched", "diagnostic", "refused", "forgotten"]} == {"matched": 4, "diagnostic": 4, "refused": 6, "forgotten": 8}
    assert all("product_leaf_calls=0" in line for line in cases)
    host_reviews.append({"mode": mode, "passed": 42, "failed": 0, "filtered": 470, "independent_tests": independent_names, "independent_subcases": cases, "producer38_replayed_exact_test_names": True, "stdout": row(directory / "stdout"), "stderr": row(directory / "stderr")})

# Verify the full producer MIR, then the entire contiguous4237-item inventory.
archive = PRODUCER / "mir/complete-production.mir.gz"
assert sha(archive.read_bytes()) == "d51faa88b6c44978f14e3a029c56e32accd90840c7140279e1c20439e8660ba7"
mir = gzip.decompress(archive.read_bytes())
assert len(mir) == 84594785 and sha(mir) == "450b0086b2db3c4df1d9da7e0fc66c1d71e8db2bdf5aab23ef1b44eefbaebcb6"
inventory = json.loads((PRODUCER / "complete-mir-item-inventory.json").read_text())
assert inventory["item_count"] == 4237
end = inventory["preamble_bytes"]
for item in inventory["items"]:
    assert item["byte_start"] == end
    body = mir[item["byte_start"]:item["byte_end_exclusive"]]
    assert len(body) == item["bytes"] and sha(body) == item["sha256"]
    end = item["byte_end_exclusive"]
assert end == len(mir)
selected = [x["item"]["index"] for x in json.loads((PRODUCER / "mir-function-inventory.json").read_text())["items_containing_new_types"]]
assert len(selected) == 38
selected += [3656, 3657, 3662, 3677]
assert len(set(selected)) == 42
mir_review = {
    "schema": 1, "status": "complete-producer-MIR-verified-selected-complete-bodies-independently-reviewed-for-accessible-lifetime-only",
    "producer_archive": row(archive, PRODUCER), "complete_decompressed_bytes": len(mir), "complete_decompressed_sha256": sha(mir),
    "contiguous_top_level_item_hashes_verified": 4237,
    "selected_complete_body_items": [inventory["items"][index] for index in sorted(selected)],
    "semantic_review": [
        "Scope MIR copies the actual acquisition reservation reference after sticky Cell set; original_root simply copies attempt field3; File scope delegates unchanged.",
        "Generic correlation _4 comes exclusively from attempt field3. All three normal returns build RootBound payload plus reborrow of _4. Foreign expected reference participates only in identity refusal checks, never root assignment.",
        "into_result and split_pair move whole payloads while copying/reborrowing the same root; into_selected moves the complete bound selection unchanged.",
        "File facade MIR consumes complete selected/files/usage before correlation; both outcome paths rebuild all original File slots and optional executable. Refused original receives the actual selected/error before bound return. Cleanup edges drop remaining originals and do not publish raw output.",
        "Fixed fixture MIR has root locals _4/_47/_14, whole selected bundle and raw scope/run locals; matched branch calls existing into_snapshot_scope, construct, outer and finish in order. Both actual Err and Ok move into RawFixturePrimary::Leaf before primary/files/usage/root join. Sole normal return moves every fixture owner into RootBoundFixtureOutcome. Unwind edges drop raw run or selected and sibling owners, then resume; no raw return/callback escape.",
        "Cache prepaid MIR obtains original root before setup, moves the complete SetupOutcome into its bound refused return, and loaded complete into a bound loaded return. Child dispatch closure captures fixture, actual attempt and expected view; output retains independent child/root carrier types.",
        "Admitted observe MIR returns only discriminants/scalar usage and shared references; destroy delegates the whole child to the unchanged destruction operation. Current outer destroys child and releases token before acquisition retirement and scalar return; its particular ordering does not establish arbitrary caller funding.",
        "Twenty-four constructor/shim MIR items are direct argument-to-constructor moves or shared-reference moves followed by return. Their privacy is a source boundary; raw constructor MIR is not a claim raw File/selected has a root lifetime.",
    ],
    "not_accepted": ["MIR source-place price or layout", "private-place funding", "root shutdown or durable forgotten funding", "actual File/leaf/native execution", "full joint retirement"],
}

producer_commands = []
producer_roster = json.loads((PRODUCER / "proposed-command-roster-v2.json").read_text())
for command in producer_roster["commands"]:
    directory = PRODUCER / "commands-v2" / command["id"]
    receipt = json.loads((directory / "receipt.json").read_text())
    assert receipt["success"] and receipt["child_reaped"] and receipt["exact_owned_group_absent"] and receipt["postrun_source_and_tool_pins_verified"]
    assert json.loads((directory / "plan.json").read_text())["argv"] == command["argv"]
    producer_commands.append({"id": command["id"], "exit": receipt["exit"], "seconds": receipt["seconds"], "receipt": row(directory / "receipt.json", PRODUCER)})
producer_review = {
    "schema": 1, "producer_seal_sha256": sha((PRODUCER / "seal.json").read_bytes()), "all_producer_members_verified": 336,
    "commands": producer_commands, "compiler_commands": 21, "version_queries": 1, "host_runs": 2, "passed_per_mode": 38,
    "diagnostic_review": "All18 actual stderr diagnostics inspected. Lifetime refusals N01-N07/N11-N14 point at true local original-root borrows, N15 at moving the actual carrier while borrowed. N08 identifies existing-but-inaccessible private selected type, N09 private opaque tuple field, N10 missing bare extractor, N16 actual generic-core privacy, N17 absent map via missing Iterator, N18 absent Deref/DerefMut. These are intended source/API domains with compiled controls, not accidental missing imports/cfg/startup failures.",
    "distinctness_limit": "18 compiler commands are not18 independent runtime scenarios. Several whole-family lifetime probes share equivalent generic return constraints; no optional/leaf/setup arm execution is inferred.",
    "host_limit": "Producer38 tests are actual generic production core with guards/validator plus unchanged child-account guards and Pending selector. Historical460-vector mapping is not newly executed;46 actual mutation vectors are source and producer-host evidence.",
    "scope": "Producer evidence explicitly reused as producer; independent11 compiler and2 host commands are separately recorded.",
}

build = P / "build"
expected_generated = ["P01-facade.rmeta", "P02-cache.rmeta", "IN01-history.rmeta", "tests-debug", "tests-opt2"]
assert sorted(f.name for f in build.iterdir()) == sorted(expected_generated)
generated = [row(build / name) for name in expected_generated]

write("semantic-diagnostic-review.json", {
    "schema": 1, "status": "independent-semantic-review-complete-for-frozen-probes", "negative_boundaries": diagnostics,
    "positive_controls": ["P01 facade return, foreign expected correct original-root return, final return and legitimate short original diagnostics", "P02 separate child/root result after owner retirement and child-only destruction token"],
    "historical_observation": {"id": "IN01-history", "exit": 0, "stderr": row(P / "commands/IN01-history/stderr"), "review": "Compiler explicitly identifies the same named root as hidden in return and suggests OwnedCorrelationOutcomeV1<'root>. Exact helper is accepted with an implicitly rooted return; preaccess syntactic rejection was overstrict and corrected before launch with root approval. No source defect or escaped payload is inferred."},
    "no_extra_or_retry_compiler_commands": True,
})
write("host-evidence-review.json", {
    "schema": 1, "runs": host_reviews, "new_tests_per_mode": 4, "new_finite_subcases_per_mode": 22,
    "witnesses": ["matched Some/None and both destruction orders preserve actual1947-byte validator proof pointer, complete guards20..23 and usage", "original custom io payload pointer/id and exact-once Drop survive owner destruction; scalar Copy validation diagnostic retains every field", "provenance/association/cross-owner refusals preserve exact originals and supplying attempt root in Some/None shapes, both ledgers remain charged", "forgotten matched/error/provenance/association results retain sticky live-ledger charge while original root is still observable"],
    "validation_copy_limit": "SwiftValidationFailure is Copy scalar data with no allocation backing; equality verifies all fields. False io-pointer flags on validation-only rows mean not applicable, not failed identity.",
    "scope": "No native File owner/loader/setup prefix, actual VM fixture, fixed product leaf/adoption or child File destruction was executed. No mini-leaf or alternate ownership machine introduced. Forgotten obligations after lexical root end remain unqualified.",
})
write("producer-evidence-review.json", producer_review)
write("mir-evidence-review.json", mir_review)
for name in expected_generated:
    (build / name).unlink()
assert not list(build.iterdir())
write("generated-artifact-cleanup.json", {
    "schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).relative_to(R))], "tool_version": sys.version,
    "removed_only_these_owned_generated_outputs_after_terminal_use": generated,
    "build_directory_empty": True, "all_13_owned_groups_rechecked_absent_before_removal": True,
    "no_other_lane_or_canonical_files_touched": True,
})
write("result.json", {
    "schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "disposition": "recommend-accept-selected-minimum-accessible-original-root-result-lifetime-source-slice",
    "source146_tree_sha256": "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f",
    "host11_tree_sha256": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
    "instrumented_test_only_source_tree_sha256": "a4089a9d0c5c991aba41b19c20fbdde656402bf342fc60887d6864039ce25343",
    "independent_commands": receipts, "independent_compiler_commands": 11, "independent_semantic_negatives": 6, "positive_companions": 2, "historical_compatibility_observations": 1, "host_runs": 2, "passed_per_mode": 42, "new_host_tests": 4, "new_finite_host_subcases_per_mode": 22,
    "max_command_seconds": max(x["seconds"] for x in receipts),
    "accepted_evidence_scope": ["Original supplying root is explicit and independent of owner/foreign expected/child account", "Accessible complete admitted correlation/final/child carrier and short original diagnostic views cannot outlive original root through reviewed safe facade", "Owner may retire before result with live original root", "Private fixed raw selected/adoption/scope/run/finish operation has no production raw return bypass in reviewed finite source/MIR bodies", "IR01 permanent issued-scope no-Complete/no-refund barrier retained"],
    "concrete_source_defects_found": [],
    "private_N12_N13": "Finite private construction/destructure/return source plus complete selected MIR review; not a compiler theorem that raw File/Selected/diagnostic values intrinsically borrow root.",
    "historical_signature": "Compiled through lifetime elision, explicitly observed and preexecution corrected; does not grant static return or lexical-root escape.",
    "still_pending": ["actual native File setup partial prefixes and correlation", "actual File child destruction/token path", "actual VM/adoption/leaf Ok/Err/unwind runtime evidence", "forgotten-result/root durable funding", "complete root shutdown", "full root/result charge lifetime", "useful joint retirement", "all new source/MIR/layout/funding prices", "production selector/startup/allocator/custody/native healthy close", "paused UI/capture/native runtime and physical-device acceptance", "immutable external FieldLog packages", "OTA", "GA"],
    "root_integrates_source_status_and_delivery": True, "canonical_or_producer_edits": False, "Git_mutation": False,
})
result_text = """# Independent accessible-result lifetime review

The frozen minimum accessible-result source repair is independently supported.
The recommendation is limited to original-root lifetime propagation through the
reviewed admitted family and the conservative IR01 barrier. No concrete source
defect was found. Root remains responsible for integration and acceptance.

Expectations were adopted before candidate access. Exact source146 remains
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`;
host11 remains `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
The independent source copy adds only two cfg(test) include sites; removing them
reproduces the producer source exactly. No canonical/producer file was changed.

All 13 root-released command IDs ran once: 11 compiler commands and two host
runs. Two positive companions compiled. Six semantic negative commands rejected
static/root substitution, lexical original-root escape in the actual generic
production core, diagnostic borrow promotion, and ownership extraction of both
leaf result types. Actual diagnostics were reviewed beyond phrase matching.
Both Debug and opt-level2 passed 42 tests: the exact producer38 replay and four
fresh tests with 22 finite Some/None subcases. These retain actual validator
proof/error identity and original guard resources; they execute no product leaf.

The exact historical helper compiled because its return lifetime is elided from
the original root input. The compiler explicitly identifies that same lifetime.
Root approved observational interpretation before execution. This is compatible
rooted spelling, not a naked result escape or a requirement for API churn.

The entire producer MIR archive and all 4,237 contiguous item hashes were
verified. The 38 new-family items plus four root-origin/retirement items were
reviewed as complete bodies. Raw selected/runtime transitions remain inside the
fixed synchronous operation and both typed result arms return bound. Private
raw payloads do not intrinsically borrow root: the finite source/MIR boundary,
not an external privacy error, supports the private N12/N13 interpretation.

Every owned child was reaped and its exact group absent, including final exact
group checks. Only this review's five generated metadata/binary outputs were
hashed and removed after terminal use. The build directory is empty. No retry,
native File/VM fixture, UI/capture, phone, network, global process inventory,
Git mutation, or other-lane change occurred.

Actual native File setup partial-prefix/correlation/child destruction, actual
VM/adoption/leaf Ok/Err/unwind, forgotten-result/root durable funding, complete
root shutdown, full charge lifetime, useful joint retirement, every new
price/layout/funding qualification, native selector/custody/healthy close,
physical acceptance, FieldLog, OTA and GA remain Pending. Native runtime and
capture remain Paused/Pending. A forgotten accessible handle may let the lexical
root end; a vanished stack counter is not durable funding.

Earlier source-checkpoint files and the command proposal intentionally preserve
their preexecution phase statements. `result.json`, the semantic/host/MIR
reviews and cleanup receipt record the completed released pass.
"""
with (P / "RESULT.md").open("x") as stream:
    stream.write(result_text)
members = [row(file) for file in sorted(P.rglob("*")) if file.is_file() and file.name != "seal.json"]
write("seal.json", {
    "schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "immutable-independent-minimum-accessible-result-lifetime-review-complete",
    "members": members, "member_count": len(members),
    "source146_tree_sha256": "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f",
    "host11_tree_sha256": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
    "forgotten_funding_shutdown_full_ownership_joint_retirement_prices_GA_accepted": False,
})
print(json.dumps({"seal_sha256": sha((P / "seal.json").read_bytes()), "members": len(members), "compiler_lane_free": True, "host_passed_each_mode": 42, "semantic_negatives": 6, "historical_observation_exit": 0, "generated_outputs_removed": len(generated), "build_empty": True}))
