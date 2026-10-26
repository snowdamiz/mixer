#!/usr/bin/env python3
"""Author an unexecuted source/funding proposal. No producer code is imported."""
from pathlib import Path
import copy
import difflib
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = "verification/swift-ordered-retention-analyzer-envelope-correction"
sha = lambda b: hashlib.sha256(b).hexdigest()
def read(name):
    return (ROOT / name).read_bytes()
def obj(name):
    return json.loads(read(name))
def write(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def identity(name):
    data = read(name)
    return {"path": name, "bytes": len(data), "sha256": sha(data)}
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

EXPECTED = {
    BASE + "/src/envelope.rs": "7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1",
    BASE + "/src/analyzer.rs": "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b",
    BASE + "/seal.json": "4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1",
    BASE + "/step-inventory.json": "6b7206d61440775f568d983b0aa2473d96eed1d0838c91a4035cc59fb9a9845a",
    BASE + "/complete-transfer-edge-inventory.json": "8be91fc764715a227deba3459a7c53ec8804195f4e98cb7f8097fb636f1e0e46",
    BASE + "/logical-inventory.json": "a4dfaf40c9f27ef2353a070405143195abc48ef9da2cf856b4aa3ab8d72fd6f9",
    BASE + "/actual-complete-layouts.json": "685bc6ff0ecc7f683aa83d3498d98b7b819de42508aa13723e1ed1a1479e29b1",
    BASE + "/finalization-funding-table.json": "9899e1008c6fe39fbe830cf589362645623194e14c4f1d67e77eed709874ef5d",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/seal.json": "ee8b9ec9ef3b894e6bc40036aa8951528401414933097849f0c2e4a8aa879cff",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/finding-R2.json": "8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/seal.json": "929593356ebb871f4089e04ad1b71d216880d90a3da5151a5421c50553b985e8",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/findings.json": "2690663a6fec5e4a8829c23a21f6cf4377d0293c851ecc63287f8574b25c0e7e",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/commands/closure-1/absence-guard-funding-boundary.json": "ae74db6ec56cee3239bb9dccb49848fd10632b1c4009a9e506c59f5b009a97ba",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json": "242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json": "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c",
    "verification/swift-envelope-absent-state-accounting-review/preparation/seal.json": "4bbf4fcd7ffeee393f2e79ffd7d549adda148da74d557cb99db4aa1a7feb3b35",
    "verification/swift-envelope-absent-state-accounting-review/preparation/obligations.json": "a533bcf5ee73d46a98829ecd513fc11d395d42bdd4af235dac4e1c273dfbec08",
}
for name, expected in EXPECTED.items():
    assert sha(read(name)) == expected, name
seal_summaries = []
for name, count, size in [
    (BASE + "/seal.json", 306, 44895898),
    ("verification/swift-analyzer-envelope-correction-behavior-review/final-review/seal.json", 118, 2032748),
    ("verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/seal.json", 248, 43000105),
]:
    data = obj(name)
    assert len(data["members"]) == count
    assert sum(m["bytes"] for m in data["members"]) == size
    seal_summaries.append({**identity(name), "listed_member_count": count, "listed_member_bytes": size,
        "verification_scope": "seal hash and named consumed inputs only; complete packet admission belongs to root"})
write("admission.json", {"schema": 1, "status": "named-inputs-hash-checked",
    "inputs": [identity(n) for n in EXPECTED], "seal_summaries": seal_summaries,
    "full_upstream_packet_reverified_by_this_lane": False,
    "upstream_archives_or_harnesses_copied_or_executed": False})

before = read(BASE + "/src/envelope.rs").decode()
old_entry = """    // Selected orchestration prepays425. Its separate fixed112-credit guard,
    // reserved before candidate mutation, pays these reads and the complete
    // Steps reply if a private caller supplies fewer credits. It can run only
    // once through the orchestrator: its Refused reply latches.
    let underfunded = steps.remaining < RECORD_ENVELOPE;
    if steps.spent != 0 { return poisoned(0); }
    if !underfunded { steps.remaining -= RECORD_ENVELOPE; steps.spent = RECORD_ENVELOPE; }
    // One length preflight proves all twelve fixed8-byte source/destination ranges.
    // The same exclusive slice and its length survive through commit.
    if arena.len() < 7_731_056 { return poisoned(if underfunded { 0 } else { RECORD_ENVELOPE }); }
"""
new_entry = """    // The separately prepaid112 guard owns terminal absent-state/invalid-budget
    // poison0 and present-state Steps0. Main B471/public425 remains paid.
    // Its complete terminal reply latches before any later orchestrated leaf.
    // Check readability before any private budget access, prior read or mutation.
    // This same exclusive slice and length survive through every commit write.
    if arena.len() < 7_731_056 { return poisoned(0); }
    if steps.spent != 0 { return poisoned(0); }
    let underfunded = steps.remaining < RECORD_ENVELOPE;
    if !underfunded { steps.remaining -= RECORD_ENVELOPE; steps.spent = RECORD_ENVELOPE; }
"""
old_validator = """fn reply_debit_valid(reply: &FixtureEnvelopeReplyV1, steps: &StepBudget) -> bool {
    (steps.remaining == 0 && steps.spent == RECORD_ENVELOPE && reply.words[13] == RECORD_ENVELOPE)
        || (steps.remaining < RECORD_ENVELOPE && steps.spent == 0 && reply.words[0] == 2 && reply.words[1] == 1 && reply.words[13] == 0)
}
"""
new_validator = """fn reply_debit_valid(reply: &FixtureEnvelopeReplyV1, steps: &StepBudget) -> bool {
    if steps.spent == RECORD_ENVELOPE {
        return steps.remaining == 0 && reply.words[13] == RECORD_ENVELOPE;
    }
    if steps.spent != 0 || reply.words[13] != 0 { return false; }
    if reply.words[1] == 15 { return reply.words[0] == 3; }
    reply.words[1] == 1 && reply.words[0] == 2 && steps.remaining < RECORD_ENVELOPE
}
"""
assert before.count(old_entry) == 1
assert before.count(old_validator) == 1
after = before.replace(old_entry, new_entry).replace(old_validator, new_validator)
(OUT / "src").mkdir(exist_ok=True)
(OUT / "src/envelope.rs").write_text(after)
(OUT / "src/analyzer.rs").write_bytes(read(BASE + "/src/analyzer.rs"))
patch = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
    fromfile=BASE + "/src/envelope.rs", tofile=str((OUT / "src/envelope.rs").relative_to(ROOT))))
(OUT / "envelope.diff").write_text(patch)
def lines(fragment):
    start = after[:after.index(fragment)].count("\n") + 1
    return [start, start + fragment.count("\n")]
write("source-binding.json", {"schema": 1, "baseline": identity(BASE + "/src/envelope.rs"),
    "candidate": identity(str((OUT / "src/envelope.rs").relative_to(ROOT))),
    "parent": identity(str((OUT / "src/analyzer.rs").relative_to(ROOT))),
    "diff": identity(str((OUT / "envelope.diff").relative_to(ROOT))),
    "exact_replacements": [{"before": old_entry, "after": new_entry},
                           {"before": old_validator, "after": new_validator}],
    "changed_function_spans": {"entry": lines(new_entry), "validator": lines(new_validator)},
    "otherwise_byte_identical": True, "compiled": False, "executed": False})

baseline = obj(BASE + "/step-inventory.json")
edges = obj(BASE + "/complete-transfer-edge-inventory.json")
assert len(baseline["rows"]) == 116 and len(edges["edges"]) == 108
byid = {r["id"]: r for r in baseline["rows"]}
def row(rid, atoms, groups=None, note="", source=""):
    total = sum(n for _, n in atoms)
    return {"id": rid, "phase": "debit-audit", "source": source,
        "scalar_atoms": [{"operation": s, "count": n} for s, n in atoms],
        "scalar_operations": total, "scalar_groups": (total + 15) // 16,
        "copies": [], "copy_groups": 0, "repeat": 1,
        "groups": groups if groups is not None else (total + 15) // 16, "note": note}
new_rows = [
    row("DV00", [("two native reference parameter receiving/binding operations", 2),
        ("steps.spent member/address selection and scalar load", 2),
        ("RECORD_ENVELOPE source, equality and if branch", 3)],
        source="reply_debit_valid entry and spent==425 dispatch"),
    row("DV01", [("steps.remaining member/address selection and scalar load", 2),
        ("zero source, equality and short-circuit conjunction", 3),
        ("reply.words[13] indexed read primitive6 plus member selection1", 7),
        ("RECORD_ENVELOPE source, equality and boolean return", 3)],
        source="reply_debit_valid paid return"),
    row("DV02", [("steps.spent member/address selection and scalar load", 2),
        ("zero source, inequality and short-circuit disjunction", 3),
        ("reply.words[13] indexed read primitive6 plus member selection1", 7),
        ("zero source, inequality and if branch", 3)],
        note="Upper15 includes both operands even if the first rejects early. Return false is separately DV02R only on that terminal branch.",
        source="reply_debit_valid unpaid consistency predicate"),
    row("DV02R", [("false materialization and boolean return", 2)],
        source="reply_debit_valid consistency rejection"),
    row("DV03", [("reply.words[1] indexed read primitive6 plus member selection1", 7),
        ("fifteen source, equality and if branch", 3)],
        source="reply_debit_valid poison reason dispatch"),
    row("DV04", [("reply.words[0] indexed read primitive6 plus member selection1", 7),
        ("three source, equality and boolean return", 3)],
        source="reply_debit_valid poison status return"),
    row("DV05", [("reply.words[1] indexed read primitive6 plus member selection1", 7),
        ("one source, equality and short-circuit conjunction", 3),
        ("reply.words[0] indexed read primitive6 plus member selection1", 7),
        ("two source, equality and short-circuit conjunction", 3),
        ("steps.remaining member/address selection and scalar load", 2),
        ("RECORD_ENVELOPE source, less-than and boolean return", 3)],
        note="Two scalar groups: first reason predicate10; remaining status/remaining predicates15. Every short-circuit execution is a prefix of this25-operation sequence.",
        source="reply_debit_valid Steps return"),
]
new_l01 = copy.deepcopy(byid["L01"])
new_l01["source"] = "candidate envelope entry: length preflight -> spent check -> threshold/debit; no prior/candidate access"
new_l01["scalar_atoms"] = [
    {"operation": "four native parameter receiving/binding operations", "count": 4},
    {"operation": "arena native receiver/length return, bound materialize, comparison, branch", "count": 5},
    {"operation": "steps.spent load, zero materialize, compare, branch", "count": 4},
    {"operation": "steps.remaining load, threshold load, comparison, underfunded binding", "count": 4},
    {"operation": "!underfunded and branch", "count": 2},
    {"operation": "remaining load, threshold load, subtraction, remaining store", "count": 4},
    {"operation": "threshold load and spent store", "count": 2},
]
new_l01["note"] = "Same25 scalar operations/two groups in new order; absence projects first9 only, invalid spent first13 only. Both return via exact RH02 and L14 subset."
new_w08 = copy.deepcopy(byid["W08"])
new_w08.update(source="reply_debit_valid DV00..DV05 path maximum", linked_groups=5,
    note="One function call has one of four terminal paths. Reserve max(2,3,4,5)=5; no sum over incompatible returns, no credit reused.")
remove = ["DV01", "DV02"]
replace = {"L01": new_l01, "W08": new_w08}
paths = [
    {"id": "paid", "rows": ["DV00", "DV01"], "groups": 2},
    {"id": "unpaid-inconsistent", "rows": ["DV00", "DV02", "DV02R"], "groups": 3},
    {"id": "unpaid-poison-reason", "rows": ["DV00", "DV02", "DV03", "DV04"], "groups": 4},
    {"id": "unpaid-Steps-or-reject", "rows": ["DV00", "DV02", "DV03", "DV05"], "groups": 5},
]
unchanged = [r for r in baseline["rows"] if r["id"] not in set(remove) | set(replace)]
write("ledger-delta.json", {"schema": 1, "status": "unselected-precise-delta",
    "baseline": identity(BASE + "/step-inventory.json"),
    "candidate_source_sha256": sha(after.encode()), "baseline_rows": 116,
    "unchanged_rows": [{"id": r["id"], "canonical_sha256": sha(canonical(r))} for r in unchanged],
    "removed_rows": [{"id": rid, "canonical_sha256": sha(canonical(byid[rid]))} for rid in remove],
    "replaced_rows": [{"id": rid, "old_canonical_sha256": sha(canonical(byid[rid])), "new": val} for rid, val in replace.items()],
    "added_rows": new_rows, "result_row_count": 121,
    "unchanged_row_source_line_numbers": "Historical line annotations are baseline coordinates. Only two exact replacements occur; entry reads/stages/commits retain byte identity with a one-line offset and later unchanged bodies with a three-line offset. Source-binding exact diff resolves coordinates.",
    "validator_path_composition": paths, "validator_max_groups": 5,
    "composition": copy.deepcopy(baseline["charge_composition"]),
    "composition_rule": "L/W/S/T/E/F totals sum their named top-level rows once. W08 is the explicit terminal-path maximum above; linked child DV rows are explanatory, never charged a second time.",
    "same_selected_totals_proposed": {"leaf": 425, "W": 24, "framing": 22, "B": 471, "G": 112, "setup_actual": 329, "setup_selected": 534, "T": 42, "finish": 47, "F": 42},
    "independent_source_accounting_still_required": True})
write("copy-edge-delta.json", {"schema": 1, "baseline": identity(BASE + "/complete-transfer-edge-inventory.json"),
    "candidate_source_sha256": sha(after.encode()), "baseline_edge_count": 108,
    "added": [], "removed": [], "changed": [], "result_edge_count": 108,
    "all_edge_canonical_sha256": sha(canonical(edges["edges"])),
    "unchanged_edge_ids": [{"row": e["row"], "index": e["index"], "canonical_sha256": sha(canonical(e))} for e in edges["edges"]],
    "reason": "Length/spent/threshold reorder and scalar control-flow validator rewrite introduce no aggregate, slice, Range, native16 handle or other fixed transfer. Existing W07 native8 borrows/call handling, W06 install, W09 fallback and L14/RH02 returns remain counted.",
    "group_rule": "One actual fixed transfer<=128B costs one copy group; complete source and destination both remain live for memory, never charged as two work edges."})

write("guard-funding-proposal.json", {"schema": 1, "status": "root-selection-required-before-runtime",
    "candidate_source_sha256": sha(after.encode()), "amount_proposed_unchanged": 112,
    "existing_scope": "selected underfunded prior-state/Steps guard only",
    "requested_scope": "One terminal unpaid leaf among absent backing at any remaining, nonzero entry spent, or readable prior-state underfunding. Existing G reservation remains a single112, not one per call.",
    "reservation": {"source": "unchanged walk budget.report(UNDERFUNDED_GUARD)? before candidate initialization and every record",
        "failure": "returns input Err before candidate/prior initialization; public setup534/finish47 stay paid if their reservations succeeded; outer F05 owns error finalization"},
    "paths": [
        {"id": "absent", "predicate": "arena.len()<7731056, regardless of remaining or spent",
         "G_owned": [{"source_row": "L01", "scalar_operations": 9, "groups": 1, "projection": "four receiving operations plus5 readability operations; no StepBudget access"},
                     {"source_row": "L14/RH02", "groups": 6, "projection": "conservative existing call operands/control10 ->1, complete leaf return copy128 ->1, actual RH02 helper4"}],
         "G_groups": 7, "private_debit": 0, "private_budget_mutation": False, "arena_candidate_mutation": False},
        {"id": "invalid-entry-spent", "predicate": "readable arena and steps.spent!=0",
         "G_owned": [{"source_row": "L01", "scalar_operations": 13, "groups": 1, "projection": "receiving4+readability5+spent check4"},
                     {"source_row": "L14/RH02", "groups": 6, "projection": "same complete poison call/helper/leaf return edges as absent"}],
         "G_groups": 7, "private_debit": 0, "private_budget_mutation": False, "arena_candidate_mutation": False},
        {"id": "present-underfunded", "predicate": "readable arena, entry spent0, remaining<425",
         "G_owned": [{"source_row": r, "groups": byid[r]["groups"]} for r in ["L01", "L02", "L03", "L04", "L14"]],
         "G_groups": 112, "private_debit": 0, "private_budget_mutation": False, "arena_candidate_mutation": False,
         "reply": "actual reply(2,1,&prior,0); G retains full conservative L01 and L14 maxima, no subtraction/refund of unexecuted atoms"},
        {"id": "present-funded", "predicate": "readable arena, entry spent0, remaining>=425",
         "G_groups": 0, "owner": "prepaid leaf425 owns full L01..L14 including precharge checks; main B prepaid before entry",
         "private_debit": 425, "remaining_effect": "entry remaining minus425", "spent_effect": 425}
    ],
    "caller_work_owner_independent_of_private_debit": {
        "W01": "Main B471 prepays24 wrapper groups and425 public debit before decode/framing/leaf decisions.",
        "W02": "leaf_pending call and next-record latch dispatch; every later successful B pays its own W even when leaf is skipped.",
        "W03_W04_W05": "record/StepBudget construction and native arguments",
        "W06": "complete received Reply128 -> progress installation then reply_valid1",
        "W07_W08": "validator arguments/control and bounded body max5",
        "W09": "invalid-reply paid poison construction/install via RH02; always prepaid by this record W",
        "not_G_work": "These W rows remain owned by per-record W24, not by G or private reply debit; L14 leaf-return -> received is owned once by selected leaf or G path."},
    "single_use_proof": [
        "Progress.reply_valid begins0 and is installed1 only after a complete actual return.",
        "Each unpaid terminal result is status3/reason15 or status2/reason1; coherent new zero forms pass validator; inconsistent forms are replaced by status3/reason15 paid poison under W09.",
        "leaf_pending returnsfalse for any status3 or reason15, and for status2; therefore any terminal guard latches before every later record.",
        "Earlier successful status1/reason0 calls consume their own paid leaf425; a later guard is still at most one and ends all later leaf calls.",
        "This proof is only for unchanged orchestration. Arbitrarily repeated direct private invocations are test controls, not funded by one G."],
    "public_debit": "534*S_paid+47*F_paid+425*N_B; successful main B471 always increases N_B and keeps425 even for private0, decode/framing failure or skipped later leaf. No refund.",
    "no_inactive_credit_or_margin_reassignment": True,
    "root_selection": False})

truth = []
def case(name, spent, remaining, status, reason, debit, accepted, downstream, reserved="arbitrary; debit audit does not inspect words14/15"):
    truth.append({"case": name, "spent": spent, "remaining": remaining, "status": status, "reason": reason,
        "private_debit": debit, "reserved14_15": reserved, "debit_validator_accepts": accepted,
        "caller_install": "received retained; reply_valid1" if accepted else "received installed then replaced with poisoned425; reply_valid1",
        "dispatch_and_finalizer": downstream})
case("normal-paid-observed",425,0,1,0,425,True,"leaf_pendingtrue; finalizer retains existing phase/state/closure/coordinate checks; no semantic flag becomes true","0,0 from actual helper")
case("normal-paid-refusal",425,0,2,"1..14",425,True,"leaf_pendingfalse; existing finalizer shape checks precede refusal/limited projection","0,0 from actual helper")
case("normal-paid-poison",425,0,3,15,425,True,"leaf_pendingfalse; finalizer poison priority and extentfalse","0,0 from actual helper")
case("absent-underfunded",0,"0,1,424",3,15,0,True,"leaf_pendingfalse; poison priority; extentfalse","0,0 from poisoned helper")
case("absent-funded",0,"425,426 or anyu64",3,15,0,True,"leaf_pendingfalse; poison priority; extentfalse; public425 remains paid","0,0 from poisoned helper")
case("readable-Steps",0,"0..424",2,1,0,True,"leaf_pendingfalse; actual prior projection only; existing finalizer shape checks apply","0,0 from reply helper")
case("Steps0-with-funded-remaining",0,"425..u64MAX",2,1,0,False,"fallback poison latches; extentfalse")
case("zero-Observed-is-never-accepted",0,"any",1,0,0,False,"fallback poison; no fabricated observed reply")
case("zero-mixed-poison-status1",0,"any",1,15,0,False,"fallback poison latches")
case("zero-mixed-poison-status2",0,"any",2,15,0,False,"fallback poison latches")
case("zero-mixed-poison-reason",0,"any",3,"not15",0,False,"fallback poison latches")
case("zero-unsupported-status",0,"any","0,4,u64MAX","any",0,False,"fallback poison latches")
case("zero-unsupported-reason",0,"any","1,2,3","0,2..14,16,u64MAX except accepted tags",0,False,"fallback poison latches")
case("spent-contradiction", "1..424,426..u64MAX","any","any","any","any",False,"fallback poison; returned private poison0 for reused spent is rejected, preserving fail-closed caller audit")
case("paid-nonzero-remaining",425,"1..u64MAX","any","any",425,False,"fallback poison; raw private funded426 leaf may leave1 but orchestration always supplies exactly425")
case("paid-wrong-debit",425,0,"any","any","not425",False,"fallback poison latches")
case("zero-spent-nonzero-debit",0,"any","any","any","not0",False,"fallback poison latches")
case("paid-mixed-poison",425,0,"3 or any status with reason15","any or15",425,True,"debit audit intentionally unchanged; leaf_pendingfalse if status3 or reason15; finalizer poison priority suppresses all extent")
case("paid-other-malformed-tag",425,0,"0,4,u64MAX or1 with reason1..14","unsupported",425,True,"paid debit predicate unchanged; existing finalizer returns UnavailableState when neither poison marker applies. Malformed status1/nonzero nonpoison reason is not produced by source; direct test fabrication is outside actual reply-form provenance.")
case("poison-nonzero-extent-or-reserved",0,"any",3,15,0,True,"debit audit checks tags/debit/budget only; poison priority prevents scheduling and suppresses extent; project hardcodes public acceptance flags0. Actual poisoned helper writes all other words0.")
write("validator-truth-table.json", {"schema": 1, "source": new_validator,
    "candidate_source_sha256": sha(after.encode()),
    "accepted_debit_forms": [
        "spent425 AND remaining0 AND debit425 (existing paid predicate; no shape authority)",
        "spent0 AND debit0 AND status3 AND reason15, independent of remaining",
        "spent0 AND debit0 AND reason1 AND status2 AND remaining<425"],
    "all_other_budget_debit_forms_rejected": True,
    "shape_and_provenance_boundary": "This private debit audit does not certify state shape or reserve words. Paid predicate is byte-for-byte equivalent to previous meaning. Actual reply/poison helpers deterministically set tags and reserve words; no external constructors or raw serializer exist. Existing leaf_pending/finalize guards remain byte-identical. Unsupported fabricated paid forms retain those exact existing semantics; this proposal does not assert that debit_valid implies semantic validity.",
    "cases": truth, "public_main_debit_ever_refunded": False})

inventory = obj(BASE + "/logical-inventory.json")
layouts = obj(BASE + "/actual-complete-layouts.json")
write("type-lifetime-delta.json", {"schema": 1, "baseline_inventory": identity(BASE + "/logical-inventory.json"),
    "baseline_layout_receipt": identity(BASE + "/actual-complete-layouts.json"),
    "candidate_source_sha256": sha(after.encode()), "fresh_candidate_layout_run": False,
    "type_declarations_changed": [], "new_locals_or_value_owners": [],
    "same_complete_types": layouts["layouts"],
    "new_control_values": "No named local added. Native scalar/member/index/boolean temporaries stay within existing debit-validator128 lease (two8-byte references, bool source/return/caller3, existing109 control/index/scalar bytes). Each new validator basic block has at most the existing predicate/one bool result live; branches end before the next. No tuple/array/Result/Option/slice value is added.",
    "shortened_lifetime": "underfunded bool is now formed only after arena readability and entry-spent checks; absent path never initializes prior96/word8 or any candidate payload.",
    "existing_leaf_subroles": {"actual":936,"lease":1152},
    "existing_walk_subroles": {"actual":240,"lease":256},
    "groups": inventory["named_role_upper_by_group"], "named_total":24656,
    "reservation":41984,"ceiling":65536,"unassigned_margin_unused":23552,
    "candidate": "one retained2048, payload888..983; no move/embed/per-record reset",
    "commit": "twelve prior reads/stage/commit ranges remain byte-identical; same exclusive arena slice and length; first new return is before any read/write; no allocation/I/O/callback/raw pointer or fallible commit is introduced",
    "global_limits": {"step":268435456,"setup":65536,"report":3000000,"IO":263584,"preflight":8192,"arena":8388608,"report_binary":49152,"future_host_text":8192},
    "physical_stack_RSS_CPU_or_native_qualification": False})
write("test-plan.json", {"schema": 1, "status": "planned-only-unselected-no-compilation-or-candidate-runtime",
    "candidate_source_sha256": sha(after.encode()),
    "required_after_root_selection": [
        {"id":"T01","controls":"length0/32 x credits0/1/424/425/426; snapshot full existing arena/candidate and StepBudget; expect all ten status3/reason15/debit0/spent0, remaining unchanged, no reads/writes beyond length"},
        {"id":"T02","controls":"length7731055/7731056 boundary x credits0/424/425/426; short path poison0 independent of deliberately malformed record; readable path selected prior/threshold semantics"},
        {"id":"T03","controls":"readable present state underfunded first and later calls; valid prior fields; record shape/coordinates deliberately invalid to prove Steps priority and actual prior projection; no arena/candidate mutation"},
        {"id":"T04","controls":"finite validator table over remaining0/1/424/425/426/u64MAX, spent0/1/424/425/426/u64MAX, status0/1/2/3/4/u64MAX, reason0/1/2/14/15/16/u64MAX, debit0/1/424/425/426/u64MAX and separate reserved/extents canaries; compare source to independent explicit three-form predicate, preserve stage-specific malformed behavior"},
        {"id":"T05","controls":"actual guard result installation/validator/leaf_pending/finalize for funded absence, underfunded prior, nonzero spent and deliberately malformed zero reply; subsequent record cannot schedule after terminal guard; mixed poison markers suppress extent"},
        {"id":"T06","controls":"unchanged public safe-File regression set and counters, successful B before decode/framing failure, latch skip after refusal/poison, inputErr/Ok/CAP, setup/finish/G failures and zero-call581; assert every successful B keeps425 independently of private0"},
        {"id":"T07","controls":"complete32 type layouts, public API positive and negative compilation controls, parent/source hash binding, unchanged binary49152/text8192 caps and all three false validity flags"},
        {"id":"T08","controls":"present-state finite transition oracle and selected budget controls, compare untouched semantics; historical model immutable, derived source/debit parameter explicit if used"},
        {"id":"T09","controls":"fresh independent behavior and final source accounting review against exact selected source, including any resulting diff from this frozen proposal"}],
    "future_command_custody": "Fresh direct-Rust host runner only after root selection. Record exact argv/tool versions/source tree/stdout/stderr. Every owned child starts new session with bounded deadline, kill/reap only own child group on timeout, preserve failures/partial streams, clean only owned scratch after return. Do not invoke frozen broad harness/hosted inspection.",
    "pending": ["all candidate Rust compilation/runtime/layout/API controls","independent review","root scope selection","native/UI/capture/device checks paused","phones disconnected","product/OTA/store/FieldLog/GA acceptance"],
    "historical_R2": "retained as failure; never relabeled as this candidate evidence"})
write("proposal-status.json", {"schema":1,"status":"frozen-proposal-awaiting-independent-accounting-and-root-selection",
    "source_authority":"isolated fixture only","corrected_candidate_compiled":False,"corrected_candidate_executed":False,
    "new_dependencies":[],"parent_changed":False,"public_API_ABI_report_changed":False,
    "root_selection":False,"implementation_accepted":False,"fullReplayAccepted":False,
    "storedPrefixValidated":False,"semanticMetricsValid":False,"GA_qualified":False,
    "native_processes_or_capture_started":False,"unowned_process_discovery_or_changes":False,
    "old_packets_mutated":False})
print(json.dumps({"status":"proposal-authored-not-executed","candidate_source_sha256":sha(after.encode()),
    "ledger_rows_after_delta":121,"copy_edges":108,"selected_totals_proposed_unchanged":True},sort_keys=True))
