#!/usr/bin/env python3
"""Static, source-only G6 core audit. Never imports or executes product code."""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
C2 = ROOT / "verification/swift-cache-state-implementation/correction-2"
FROZEN = C2 / "source/library/cache_state.rs"
EXPECTED = {
    "verification/swift-cache-state-implementation/correction-2/candidate-repo-seal.json": "26e6ece9d86f054a57e335c6b170595aa1d21e3081b45db4eda167e59abe52fb",
    "verification/swift-cache-state-implementation/correction-2/source/library/cache_state.rs": "6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00",
    "verification/swift-cache-state-implementation/correction-2/source/library/analyzer.rs": "ad039daac5de9ea811da70261ae6591dfe6846e23bea1a87fc013755b502af6e",
    "verification/swift-cache-state-implementation/correction-2/source/library/envelope.rs": "11aee91058837ba13a9000c44d30e93049f3011be46ea9493110bb81b8ab4798",
    "verification/swift-cache-state-accounting-independent-review/seal.json": "706e1ab2a1caa6b14cf588d40545a086ea32fc1a7a23a7eb5c1b1f5a48dfacd8",
    "docs/swift-semantic-adapter-prerequisite.md": "c818e47d15d541731df98cdf79032846cb4e4aa28aad2eee7e25ac36cb1c7f41",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: str, data: object) -> None:
    target = OWN / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n")


def record(path: Path) -> dict:
    b = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(b), "sha256": sha(b)}


def verify_input_seal(path: Path) -> dict:
    seal = json.loads(path.read_text())
    for row in seal["members"]:
        actual = record(ROOT / row["path"])
        assert actual["bytes"] == row["bytes"] and actual["sha256"] == row["sha256"], row["path"]
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path.read_bytes()),
            "verified_members": len(seal["members"]),
            "verified_bytes": sum(x["bytes"] for x in seal["members"])}


def main() -> None:
    for name, expected in EXPECTED.items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    seals = [verify_input_seal(ROOT / x) for x in EXPECTED if x.endswith("/seal.json") or x.endswith("candidate-repo-seal.json")]
    assert seals[0]["verified_members"] == 570 and seals[0]["verified_bytes"] == 15269154
    assert seals[1]["verified_members"] == 13 and seals[1]["verified_bytes"] == 115581
    source = FROZEN.read_text()
    lines = source.splitlines()
    source_sha = sha(source.encode())
    at = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, "-B", str(Path(__file__).resolve())]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    inputs = {
        "schema": 1, "at": at, "command": command, "python": sys.version,
        "platform": platform.platform(), "repository_HEAD_observed": head,
        "source_tree_identity": "Frozen570-member C2 seal, not mutable checkout HEAD alone",
        "sources": [record(ROOT / n) for n in EXPECTED], "input_seals": seals,
        "scope": "Immutable source/proof reads and this owned static tool only; zero product/compiler/runtime tests",
        "not_used": ["native UI", "capture", "simulator", "emulator", "phone", "process inventory", "hosted authority", "callbacks"],
        "no_staging_commit_or_push": True,
    }
    dump("inputs.json", inputs)

    core_text = [
        "i scalar source -> multiplication operand",
        "literal8 source -> multiplication operand",
        "multiply i*8",
        "multiplication result source -> local at binding",
        "at source -> destination Range.start source field",
        "at scalar source -> endpoint-addition operand",
        "literal8 source -> endpoint-addition operand",
        "add at+8",
        "addition result source -> destination Range.end source field",
        "Range.start source field -> received index start field",
        "Range.end source field -> received index end field",
        "destination ordered-range predicate start<=end",
        "destination upper-bound predicate end<=Candidate length",
        "destination address formation from Candidate base and start",
        "destination view length formation end-start",
        "destination view.data source -> received copy receiver.data",
        "destination view.len source -> received copy receiver.len",
        "shared zero source address -> source slice argument.data",
        "literal8 source -> source slice argument.len",
        "copy_from_slice destination/source length equality predicate",
        "copy_from_slice unit/control return -> actual caller continuation",
    ]
    core = [{"id": f"C{i:02}", "source_lines": [783, 784], "operation": name,
             "named_scalar_operations": 1} for i, name in enumerate(core_text, 1)]
    model = {
        "schema": 1, "source_sha256": source_sha,
        "status": "Explicit component-atomized qualified lower/core model; NOT a complete upper or binding-implied numeric overrun",
        "binding_caps": [256, 2560, 2568, 768, 640, 640, 248],
        "rules": [
            "One named scalar operation handles at most one machine scalar word or one primitive predicate/arithmetic/control operation.",
            "One transfer edge owns both its named source and its received destination; they are not two transfer debits.",
            "A distinct explicit initializer/source field followed by a later by-value receive is two different edges, each named once.",
            "A Range<usize>16 is two word fields; a slice view16 is pointer and length. Neither is treated as one scalar.",
            "A scalar literal-to-operand/field is a named source edge, not a free implicit argument or an extra duplicated receive.",
            "One fixed-copy debit owns one distinct complete payload movement of at most128B. Unrelated copies are not byte-packed together.",
            "All core scalar operations may be partitioned in source order across G6 in blocks of16; no site-local rounding assumption.",
            "Copy operations are independent of the scalar stream and cannot consume partial scalar-block capacity.",
            "Array8 LE return-to-temporary and temporary-to-destination are distinct payload movements; no optimizer elision.",
            "This is not a Rust machine-instruction count and does not prove runtime slowness or an unconditional cap overrun.",
        ],
        "clear_body_core": core,
        "clear_body_core_count": len(core), "iterations": 256,
        "excluded_from_core_and_not_free": [
            "clear loop Range/IntoIterator/iterator construction and complete component transfers",
            "all257 next calls, Some/None construction/received Option/branch, i binding and iterator advance",
            "Candidate receiver/borrow transfer into indexing, source borrow construction and source view construction beyond named edges",
            "copy call entry and any remaining function/trait control or intermediate source/view places",
            "all non-clear helper/caller scalar operations and administration",
            "zero8 initializer scalar inputs and cleanup call/return/guard",
        ],
        "qualification": "The binding passage does not supply a formal primitive grammar. A reviewer must accept this listed component grammar before interpreting its665 core numerically. No complete upper follows from the core.",
    }
    dump("component-core.json", model)

    # Explicit source-site inventory. The static tool checks every listed anchor.
    sites: list[dict] = []
    def site(id: str, kind: str, line: int, expr: str, paths: list[str], repeat: int = 1, width: int = 8) -> None:
        assert kind in ("st", "sq", "copy", "load")
        anchor = {"st": "st(", "sq": "sq(", "copy": "copy_", "load": "ld("}[kind]
        assert anchor in "\n".join(lines[line-1:line+3]), (id, line, anchor)
        copies = 2 if kind in ("st", "sq") else 1
        sites.append({"id": id, "kind": kind, "source_line": line,
                      "caller_expression": expr, "paths": paths,
                      "repetitions": repeat, "copy_width": width,
                      "payload_movements_per_repetition": copies,
                      "payload_groups": copies * repeat})

    names = ["1", "2", "3", "4-reuse", "4-new", "5", "6", "7", "8", "9", "10", "11-hit", "11-built", "12", "13"]
    for n, line in enumerate(range(454, 463)):
        site(f"event1.sq{line}", "sq", line, lines[line-1].strip(), ["1"])
    for line in [474, 475]:
        site(f"event2.sq{line}", "sq", line, lines[line-1].strip(), ["2"])
    site("event4.plan-st", "st", 498, "c;1648+i*8;if i==0 {w[6]} else if i<4 {w[6+i]} else {0}", ["4-new"], 5)
    site("event5.plan-copy", "copy", 534, lines[533].strip(), ["5"], width=40)
    for line, kind in [(535, "st"), (537, "sq"), *[(n, "sq") for n in range(562, 568)]]:
        site(f"event5.{kind}{line}", kind, line, lines[line-1].strip(), ["5"])
    site("event6.sq587", "sq", 587, lines[586].strip(), ["6"])
    site("event6.pending-st766", "st", 766, lines[765].strip(), ["6"])
    site("event7.tail-copy", "copy", 596, lines[595].strip(), ["7"], width=64)
    for line, kind in [(597, "st"), (599, "sq"), (600, "sq"), (601, "sq")]:
        site(f"event7.{kind}{line}", kind, line, lines[line-1].strip(), ["7"])
    for line in [610, 611]:
        site(f"event8.sq{line}", "sq", line, lines[line-1].strip(), ["8"])
    site("event11.hit-row-copy", "copy", 635, "c[1536..1600] <- arena resident64", ["11-hit"], width=64)
    site("event11.built-tail-copy", "copy", 642, lines[641].strip(), ["11-built"], width=64)
    for line, kind in [(643, "st"), (644, "st"), (645, "st"), (646, "st"), (647, "sq"), (651, "sq")]:
        site(f"event11.built-{kind}{line}", kind, line, lines[line-1].strip(), ["11-built"])
    site("event11.prior-pins-ld", "load", 653, "ld(c,1560)8 array source -> from_le_bytes by-value received8; result u64/binding scalar", ["11-hit", "11-built"])
    for line in range(660, 668):
        site(f"event11.st{line}", "st", line, lines[line-1].strip(), ["11-hit", "11-built"])
    for line in [670, 671]:
        site(f"event11.sq{line}", "sq", line, lines[line-1].strip(), ["11-hit", "11-built"])
    site("event12.resident-copy", "copy", 692, "c[1536..1600] <- arena resident64", ["12"], width=64)
    site("event12.st694", "st", 694, lines[693].strip(), ["12"])
    site("event12.pin-st696", "st", 696, lines[695].strip(), ["12"], repeat=6)
    site("event12.sq700", "sq", 700, lines[699].strip(), ["12"])
    for line in [707, 708, 709, 728, 729, 730]:
        site(f"final.sq{line}", "sq", line, lines[line-1].strip(), names)
    site("commit.resident64", "copy", 736, lines[735].strip(), ["7", "11-hit", "11-built", "12"], width=64)
    site("commit.pin48", "copy", 747, lines[746].strip(), ["11-hit", "11-built", "12"], width=48)
    site("commit.plan40", "copy", 751, lines[750].strip(), ["4-new", "5"], width=40)
    for n, line in enumerate(range(753, 765)):
        site(f"commit.scalar{n:02}", "copy", line, lines[line-1].strip(), names)
    site("clear.payload", "copy", 784, "c[i*8..i*8+8] <- zero8", names, repeat=256)
    for n, line in enumerate(range(786, 798)):
        site(f"restore.scalar{n:02}", "copy", line, lines[line-1].strip(), names)
    dump("source-sites.json", {
        "schema": 1, "source_sha256": source_sha,
        "coverage": "Every G6 event/final staging store and fixed payload copy plus staged prior-pins load. Not an exhaustive scalar upper.",
        "zero_initializer": {"source_line": 781, "id": "clear.zero-initializer", "source_bytes": 8, "received_bytes": 8, "payload_groups": 1},
        "sites": sites,
        "nonduplicated_call_edge_rule": "sq outer argument edges belong to sq; its forwarded st argument edges belong to the nested st instance. Caller expressions/conditionals/index checks are additional obligations, never another copy of the same receive edge.",
    })

    paths = []
    for name in names:
        active = [s for s in sites if name in s["paths"]]
        count = sum(s["payload_groups"] for s in active) + 1
        paths.append({"path": name, "active_site_ids": [s["id"] for s in active],
                      "payload_copy_groups": count,
                      "clear_scalar_core": 21 * 256,
                      "globally_pooled_core_scalar_groups": math.ceil(21 * 256 / 16),
                      "qualified_core_groups": count + math.ceil(21 * 256 / 16),
                      "is_complete_upper": False})
    built = next(p for p in paths if p["path"] == "11-built")
    assert built["payload_copy_groups"] == 329 and built["qualified_core_groups"] == 665
    assert [p["payload_copy_groups"] for p in paths] == [311,297,293,293,304,311,297,303,297,293,293,317,329,312,293]
    dump("paths.json", {
        "schema": 1, "source_sha256": source_sha, "ordinary_success_paths": paths,
        "largest_count_breakdown": {"event11-built-stores-and-row-source": 33,
            "event11-staged-prior-pins-array-load": 1, "final-six-sq": 12,
            "resident-and-pin-commits": 2, "literal-scalar-commits": 12,
            "zero-initializer-plus256clear-copies": 257, "literal-restores": 12},
        "non_success_paths": [
            {"path": "no semantic loan", "G6_payload_copies": 0, "owner": "pre-loan admission G1; full reply/latch/scheduling G7; no cleanup invocation"},
            {"path": "loan then zero-debit semantic guard return", "G6_payload_copies_if_cleanup_exact_length": 269,
             "owner": "semantic guard computation G128; complete reply return G7; actual cleanup still G6 under already prepaid combined record, never free G128 carry"},
            {"path": "ordinary refusal before any G6 stage", "G6_payload_copies": 269, "owner": "all clear/restore G6; full rejection SemanticReply24 and caller receive G7"},
            {"path": "built publication sum overflow after sq6", "G6_payload_copies": 280,
             "derivation": "11 event payload groups through line647 +269 cleanup; Option/refusal scalar work not free"},
            {"path": "built publication pin overflow/pin predicate refusal", "G6_payload_copies": 283,
             "derivation": "13 staged store groups through line651 +1 ld(c,1560) array load +269 cleanup"},
            {"path": "hit publication pin overflow/pin predicate refusal", "G6_payload_copies": 271,
             "derivation": "1 resident source copy +1 prior-pins array load +269 cleanup"},
            {"path": "MissReady prefix refusal after initial G6 stage", "G6_payload_copies": 274,
             "derivation": "plan40 copy +st1680 two copies +sq18 two copies +269cleanup; prefix G5 stays separate"},
            {"path": "private commit failure after first resident commit, built path", "G6_payload_copies": 316,
             "derivation": "34event +12final +1resident +269cleanup; later pin/scalar commits skipped; reply G7"},
            {"path": "cleanup exact-length failure", "G6_cleanup_payload_copies": 0,
             "owner": "cleanup guard/returned bool/caller ! branch G6; conditional poison latch G7; no assertion restored"},
            {"path": "private post-restore cleanup fault", "G6_ordinary_cleanup_copies": 269,
             "additional_test_only_work": "CLEANUP_FAULT.swap, conditional c[0]=0x51 and false return must have a separate test-artifact ledger; excluded from production primitive bound and never a free production operation"},
        ],
        "all_refusals_are_prefixes": "G6 stage prefixes are followed by cleanup. Refusal never executes six final sq or arena commit. The listed partial-stage refusal paths are the ones occurring after G6 staging starts; earlier event/probe refusals have269 cleanup payload groups.",
        "qualified_core_only": True, "complete_G6_upper_accepted": False,
        "unconditional_numeric_overrun_asserted": False,
    })

    ordered = [f"G6.clear[{i:03}].C{j:02}" for i in range(256) for j in range(1, 22)]
    blocks = [ordered[i:i+16] for i in range(0, len(ordered), 16)]
    assert len(blocks) == 336 and all(len(x) == 16 for x in blocks)
    assert len(set(sum(blocks, []))) == len(ordered)
    dump("core-partition.json", {
        "schema": 1, "source_sha256": source_sha,
        "ordered_scalar_ids": "G6.clear[i:03].C[j:02], i=0..255 outer, j=1..21 inner",
        "partition": "B[k] owns ordered_scalar_ids[16*k : 16*k+16], k=0..335",
        "scalar_operation_count": len(ordered), "scalar_block_count": len(blocks),
        "each_block_operations": 16,
        "ordered_scalar_ids_sha256_newline_terminated": sha(("\n".join(ordered)+"\n").encode()),
        "first_block": blocks[0], "last_block": blocks[-1],
        "cross_site_pooling_allowed": True, "cross_G1_G7_pooling_allowed": False,
        "copy_stream": "329 distinct built-path payload movements from source-sites.json/paths.json, each one group; independent of scalar partition",
        "qualified_core_total": 329 + len(blocks),
        "remaining_operations_have_no_credit_here": True,
    })

    def rows(prefix: str, texts: list[str]) -> list[dict]:
        return [{"id": f"{prefix}{i:02}", "obligation": t} for i, t in enumerate(texts, 1)]

    obligations = {
        "schema": 1, "source_sha256": source_sha,
        "status": "Exhaustive source-region/caller-boundary obligation inventory; unresolved atomization means NOT a complete numerical ledger",
        "st_lines156_158": rows("S", [
            "caller b source -> st received b.data and b.len as2 component edges; at and n source -> received scalar parameters once each",
            "n received scalar -> to_le_bytes self; conversion; returned8-array source -> received8 temporary COPY1",
            "at and literal8 operands; add; Range.start/end source-field construction;2 component source->received index transfers",
            "b indexing receiver pointer/length transfers; ordered/upper range guards; address and view length arithmetic",
            "exclusive destination view construction; pointer/length source->copy receiver transfers; no whole16B view scalar shortcut",
            "shared LE array reference creation; array-to-slice pointer/length construction;2 source->argument component transfers",
            "copy length guard; source temporary8 -> destination8 COPY2; unit/control returned and received; st unit/control returned and received",
            "every actual caller n/i/at literal, indexed value/check/address/read, arithmetic/cast and conditional branch must be instantiated separately at source-sites.json site",
        ]),
        "sq_lines162_164": rows("Q", [
            "caller Candidate pointer/i/n sources -> sq received parameters once; borrow construction and caller expressions separately",
            "8 literal/i operands; multiplication; SC literal/addition; offset result source -> nested st at received edge owned in nested st S01",
            "Candidate thin pointer -> slice pointer/length construction; nested st source->received b components owned by nested S01",
            "n source -> nested st n receive owned by nested S01; nested st two payload movements and body S02..S07 exactly once",
            "nested st unit/control returned/received is S07; sq outer unit/control returned/received separately",
        ]),
        "ld_lines149_155_for_staged_pin": rows("L", [
            "caller c Candidate coercion to slice pointer/length and literal1560; b/at source->received components",
            "at+8 operands/arithmetic; Range2 field construction/2 transfers; both range predicates; view address/length and borrow",
            "first_chunk8 literal generic width control; receiver pointer/length; length predicate; returned Option<&array8> complete pointer/tag representation",
            "static expect message pointer/length source and received components; Option/expect branch and unwrapped thin reference source/received",
            "dereferenced full array8 source -> from_le_bytes received8 argument COPY1; conversion; u64 result -> ld output -> caller initializer -> prior_pins binding",
            "prior_pins.checked_add(1): receiver and literal1 edges, checked addition, complete Option<u64> tag/payload source and received components; Some/None pattern branch; pins binding",
            "pins staging predicate inputs/checked indexed reads and refusal conditions at657; final st pin value edge owned by its S01",
        ]),
        "administration": rows("A", [
            "G6 final stage: checked w[1] index/read; closed match dispatch; case2 checked w[13]/literal1 comparison/branch; selected stage literal/binding",
            "two stage==0 sites at729/730 each have literal/comparison/branch; selected 0/ABSENT or checked w[3]/w[6] source to sq arg owned once",
            "resident_delta/pin_delta/plan_delta ABSENT source/comparison/branch; actual row cast/multiply/base fieldcopy/add/at binding; row destination/source Range2 and fatview2 components, predicates and full payload",
            "commit_succeeded() production call true source/return/receive, caller ! and branch; full poison SemanticReply construction/return/receive G7",
            "w[1] checked read ==6 comparison/branch; optional pending destination SCALAR.base fieldcopy, literal138/literal8/multiply/add and w[13] checked source then nested st",
            "cleanup caller b shared source/received pointer+length and c exclusive thin source/received plus borrow construction; call entry",
            "cleanup b.len field read, ARENA_BYTES literal edge, != comparison/branch; false source/return/received and caller !/branch on refusal",
            "zero initializer0/repeat8 scalar source edges, complete source8->received zero8 COPY1; source/received lifetime not elided",
            "for0..256: Range start/end literals and field constructions, complete2component transfers through IntoIterator and iterator binding; exact source primitive proof still required",
            "each257 iterator next calls: iterator borrow/received, start/end reads/check/branch,256 increments, returned Some/None complete Option<usize> source/received/pattern and i binding; no loop keyword treated free",
            "clear body C01..C21 core exactly once; all additional receiver/borrow/call/intermediate component transfers named outside that core",
            "12 literal commits and12 literal restores each require2 Range components on each side, actual literal fields, index receiver transfers,2 bounds checks each side, view pointer/length, borrows, copy receiver/source components, length guard, fixed8payload, unit/caller continuation",
            "cleanup true source/return/receive, caller ! and branch belong G6; conditional latch_terminal(16) source/call/packed state update belongs G7",
            "event4 and12 st loops: range/iterator/Option/guard/advance/final-next and per-body address/index/conditional source edges, not shared with the deleted commit/restore loops",
            "resident_delta/pin_delta/plan_delta assignment source casts/indexed values/moves; values computed for event store arguments and complete Option pattern work belong G6 conservatively",
        ]),
        "boundary": {
            "G1": "Only initial prior snapshot staging/admission and event identity preconditions already assigned by the global schedule; G6 staging computations must be removed from any overlapping G1 claim.",
            "G2": "Resident/token probes and seed stores only, not G6 delta stores.",
            "G3_G4_G5": "Sort comparator, transfer and selected-prefix arithmetic separate; final selected-prefix writes at562..567 are G6.",
            "G6": "All delta outputs, staging arithmetic/checks including prior_pins ld/checked_add/Option/pins, row controls/copies,12 scalar commits, pending store, actual cleanup and cleanup return/caller ! branch.",
            "G7": "Every full SemanticReply24 constructor/return/received/caller audit (success/refusal/poison), p.calls, q snapshot extraction, first-pin header update, conditional poison latch and later dispatch disablement. G6 never borrows spare G7 credit.",
            "G128": "Only private zero-debit guard computations/return branch source work assigned there; complete reply movement remains explicitly G7; loan cleanup source work remains G6 under actual combined prepayment.",
            "full_Result": "No Result is created by st/sq/cleanup. checked_add produces complete Option<u64>16, accounted by fields or a full fixed-copy debit. Outer Result<bool,AnalyzerError>40 and final aggregate Result belong existing wrapper/finish ownership, not G6.",
            "cfg_test": "COMMIT_FAULT/CLEANUP_FAULT injected code is an additional test-artifact branch. No product/compiler/runtime tests ran here; test-instrumented full source-cost acceptance is not claimed.",
        },
        "not_closed": ["complete G6 upper <=640", "all source primitive/standard loop lowering atomization", "all G1/G6 overlap removal in a global ledger", "full role union29344", "native/device/store/operational/GA gates"],
    }
    dump("helpers-and-obligations.json", obligations)

    old = """    let zero = [0u8; 8];
    for i in 0..256 {
        let at = i * 8;
        c[at..at + 8].copy_from_slice(&zero);
    }
"""
    assert source.count(old) == 1
    new = "    {\n        let zero = [0u8; 128];\n" + "".join(
        f"        c[{i}..{i+128}].copy_from_slice(&zero);\n" for i in range(0, 2048, 128)
    ) + "    }\n"
    old_comment = "// Explicit zero-word stores avoid a second2048-byte temporary source owner."
    new_comment = "// Explicit bounded stores avoid a second2048-byte temporary source owner."
    assert source.count(old_comment) == 1
    proposal = source.replace(old, new, 1).replace(old_comment, new_comment, 1)
    pdir = OWN / "proposal-clear128"
    (pdir / "cache_state.rs").write_text(proposal)
    diff = "".join(difflib.unified_diff(source.splitlines(True), proposal.splitlines(True),
        fromfile="frozen-correction2/cache_state.rs", tofile="unselected-source-only-clear128/cache_state.rs"))
    (pdir / "selected-product.diff").write_text(diff)
    ranges = [(i, i+128) for i in range(0, 2048, 128)]
    flat = [i for lo, hi in ranges for i in range(lo, hi)]
    assert flat == list(range(2048)) and len(set(flat)) == 2048
    assert proposal.replace(new, old, 1).replace(new_comment, old_comment, 1) == source
    assert proposal.count("let zero = [0u8; 128];") == 1
    assert proposal.count("let zero = [0u8; 2048]") == 0
    assert proposal[proposal.index("    c[888..896].copy_from_slice"):].encode() == source[source.index("    c[888..896].copy_from_slice"):].encode()
    receipt = {
        "schema": 1, "status": "SEALED UNSELECTED source-only repair proposal; no code selection, product compile/test, or implementation acceptance",
        "before_sha256": source_sha, "proposed_sha256": sha(proposal.encode()),
        "only_change": "Replace cleanup zero8/256-iteration clear comment/block with lexical zero128/16 explicit128-byte copies; all other product source bytes exact",
        "literal_clear_ranges": ranges, "complete2048_coverage_once": True,
        "semantic_equivalence_scope": "For any pre-clear Candidate, each of2048 bytes becomes0 before the byte-identical12 restores and fault-hook suffix. This is a static pointwise argument, not runtime or compiler evidence.",
        "no_loop_in_replacement": True, "no_2048_initializer_or_return": True,
        "distinct_clear_payload_groups_before": 257, "distinct_clear_payload_groups_after": 17,
        "payload_group_reduction_only": 240,
        "built_path_payload_copy_core_after": 329 - 240,
        "new_scalar_upper_bound_claimed": False,
        "scalar_work_still_required": "Literal and range/view2component initialization/argument/receiver edges for all16 stores; zero repeat initializer scalar inputs; block/caller controls. No optimizer or free site reuse.",
        "caps_unchanged": [256,2560,2568,768,640,640,248],
        "local_zero_places": {
            "old_initializer_source": 8, "old_received_local": 8, "old_binding_peak": 16,
            "new_initializer_source": 128, "new_received_local": 128, "new_binding_peak": 256,
            "binding_peak_increase": 240, "steady_local_increase": 120,
            "complete_array_copy_at_binding": "one128B source->received movement; do not count both as two payload copies",
            "lexical_scope": "new zero128 local belongs to an explicit block ending before the12 restores",
            "other_places": "Candidate remains same2048 owner; per-store ranges/views have pointer/length fields and still require local inventory; no full29344 role union proof here",
        },
        "required_before_selection_or_acceptance": [
            "independent review of source equivalence and accepted primitive grammar",
            "complete whole-G6 exact-once operation ledger and ordered <=16 partitions under unchanged640",
            "complete local and global lifetime/reconciliation without optimizer elision",
            "fresh host/compiler/product validation after root explicitly selects source repair; native checks remain paused/pending",
        ],
    }
    dump("proposal-clear128/receipt.json", receipt)
    proposal_members = [record(p) for p in sorted(pdir.iterdir()) if p.name != "seal.json"]
    dump("proposal-clear128/seal.json", {"schema": 1, "at": at,
        "status": "separate immutable unselected source-only repair proposal", "command": command,
        "python": sys.version, "before_source_sha256": source_sha,
        "members": proposal_members, "member_count": len(proposal_members),
        "member_bytes": sum(x["bytes"] for x in proposal_members)})

    readme = """# G6 source-only qualified core and unselected clear repair

Frozen correction2 is not accepted by this audit. No complete G6 upper bound is
claimed. The binding caps remain unchanged, including G6=640. This lane never ran
product, compiler, native, simulator, emulator, device, UI or capture tests and
did not stage, commit or push.

`source-sites.json` enumerates actual G6 payload sites and every ordinary event
path. Built publication has329 distinct payload movements under the explicit
model:33 event store/source copies,1 staged prior-pins load,12 final sq copies,
2 row commits,12 scalar commits,257 clear copies/initializer and12 restores.
Every st/sq has two distinct8-byte array movements. The prior-pins ld contributes
one; it computes a new staged pin value and is conservatively G6-owned.

`component-core.json` gives21 named scalar operations in each clear body,
including literals/bindings and separate Range/view fields. `core-partition.json`
partitions all5376 such operations globally within G6 into336 ordered blocks
of16, without site-local rounding. Together these give a qualified665-group
lower/core (329+336), before the explicitly uncounted loop/helper/admin work.
The weaker store-only core is664. These numbers depend on the listed primitive
grammar: the binding passage does not define that grammar. They are not an
unconditional cap-overrun assertion, machine instruction count, runtime result,
or complete upper bound. The former637 claim is not inherited.

`helpers-and-obligations.json` explicitly lists the remaining source/receiver,
loop/Option, helper, scalar/admin and G1/G6/G7/G128 boundary obligations. All
complete SemanticReply24 movements are G7; cleanup itself and returned bool plus
the caller's !/branch are G6; the conditional poison latch is G7. A loan's zero
debit guard return still executes actual G6 cleanup under the already prepaid
combined record. No other group's spare credit closes this lane's proof.

`proposal-clear128/` is separately sealed and UNSELECTED. It replaces only the
zero8/256-store loop with one lexical zero128 and16 explicit128-byte stores.
Static byte coverage is exact and the restore/fault suffix is byte-identical.
It reduces clear payload groups257->17 and removes this dynamic loop, while
introducing a128-byte initializer source and128-byte received local. Their
binding peak grows16->256 bytes (+240); steady local growth is120 bytes and the
new lexical block ends before restores. Global29344-role lifetime acceptance is
not claimed. New literal/index/view/caller work still needs a full ledger.

Reproduce with `python3 -B verification/swift-cache-state-g6-accounting/build_accounting.py`.
The tool validates immutable570-member C2 and13-member independent-review seals,
checks source-site anchors, recomputes all path-copy totals and the partition,
and writes only this owned directory. It never imports or executes product code.
`inputs.json` records command, Python version, source hashes, tree seal and HEAD.
`seal.json` binds this audit; the proposal has its own seal. Static arithmetic
and equivalence checks do not qualify implementation, lifetime, native, release,
dogfood, operational, or GA gates.
"""
    (OWN / "README.md").write_text(readme)
    validation = {"schema": 1, "at": at, "command": command, "python": sys.version,
        "frozen570_members_verified": True, "prior13_members_verified": True,
        "source_hashes_and_site_anchors_checked": True,
        "ordinary_path_count": len(paths), "largest_payload_copy_core": 329,
        "clear_scalar_core": len(ordered), "all16_partitions_count": len(blocks),
        "qualified_core_total": 665, "proposal_pointwise_coverage_checked": True,
        "proposal_other_bytes_unchanged": True, "product_compiler_runtime_tests_run": 0,
        "implementation_acceptance": False, "proposal_selected": False,
        "limitations": "Static artifact validation only; complete G6 upper and29344 lifetime union remain pending"}
    dump("static-validation.json", validation)
    members = [record(p) for p in sorted(OWN.rglob("*")) if p.is_file() and p != OWN / "seal.json"]
    dump("seal.json", {"schema": 1, "at": at, "command": command, "python": sys.version,
        "status": "sealed source-only qualified G6 lower/core plus separately sealed unselected repair; zero runtime acceptance",
        "owned_scope": ["verification/swift-cache-state-g6-accounting/**"],
        "source_sha256": source_sha, "members": members,
        "member_count": len(members), "member_bytes": sum(x["bytes"] for x in members)})
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
