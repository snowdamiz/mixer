#!/usr/bin/env python3
"""Bounded independently authored source-only G5 necessary-work witness.

No Rust, producer Python, native process, or broad harness is loaded or run.
This deliberately stops at a necessary subtrace, not a complete upper bound.
"""
import copy
import gzip
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
U64 = (1 << 64) - 1
SOURCE = "a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1"
G5_CAP = 640


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class Trace:
    def __init__(self):
        self.events = []

    def scalar(self, site, *names):
        for name in names:
            self.events.append({"id": f"G5.{len(self.events):06}", "site": site,
                                "kind": "scalar", "bytes": 0, "operation": name})

    def payload(self, site, name, size):
        self.events.append({"id": f"G5.{len(self.events):06}", "site": site,
                            "kind": "copy", "bytes": size, "operation": name})

    def value(self, site, name, target):
        self.scalar(site, f"{name} source -> {target}")

    def field(self, site, name, target):
        self.scalar(site, f"{name} owner pointer -> projection operand",
                    f"{name} field address projection", f"{name} field source -> {target}")

    def binary(self, site, op, left, right, target):
        # left/right callbacks emit their actual source expression into operands.
        left(f"{op} left operand")
        right(f"{op} right operand")
        self.scalar(site, f"primitive {op}", f"{op} result source -> {target}")

    def cast(self, site, name, target_type, target):
        self.value(site, name, f"cast {target_type} received operand")
        self.scalar(site, f"primitive cast {target_type}", f"cast result source -> {target}")

    def index(self, site, base, index, target, width, fat=False):
        index("Index received index")
        self.scalar(site, f"{base} Index receiver borrow", f"{base} pointer -> Index received receiver")
        if fat:
            self.scalar(site, f"{base} length -> Index received receiver.length")
        self.scalar(site, "Index entry control", "received index -> upper predicate left",
                    f"{'received' if fat else 'fixed'} length -> upper predicate right",
                    "index<length predicate", "index check branch",
                    "received pointer -> address operand", "received index -> scale operand",
                    f"element width{width} -> scale operand", "index*width",
                    "scaled offset -> pointer-add operand", "received pointer -> pointer-add operand",
                    "element address formation", "element address -> returned reference source",
                    "indexed reference loan creation", "returned reference -> caller received reference",
                    "Index return control", "received reference -> dereference address operand",
                    f"dereferenced source projection -> {target}")

    def compare(self, site, op, left, right):
        self.binary(site, op, left, right, "condition source")
        self.scalar(site, "condition result source -> predicate", "condition branch")


def necessary_trace():
    t = Trace()
    # Entire actual headroom expression. No other prelude is counted.
    site = "headroom"
    t.binary(site, "-",
             lambda dst: t.binary(site, "-", lambda dst2: t.field(site, "f.capacity", dst2),
                                  lambda dst2: t.field(site, "f.base", dst2), dst),
             lambda dst: t.index(site, "w", lambda dst2: t.value(site, "literal13", dst2), dst, 8),
             "headroom binding")
    need(len(t.events) == 31, "headroom source equation")
    per_iteration = []
    for i in range(64):
        start = len(t.events)
        site = f"prefix[{i}]"
        v = lambda n: lambda dst: t.value(site, n, dst)
        # Includes each of the64 actual successful while conditions.
        t.compare(site, "<", v("i"), v("literal64"))
        # remaining>headroom: && short-circuits before destination!=ABSENT.
        t.binary(site, "<=", v("remaining"), v("headroom"), "and left source")
        t.scalar(site, "and short-circuit branch", "and result source -> if predicate", "if branch")
        t.index(site, "c", lambda dst: t.binary(site, "+", v("literal512"), v("i"), dst),
                "slot_byte binding", 1)
        t.compare(site, "==", v("slot_byte"), v("literal u8::MAX"))
        t.cast(site, "slot_byte", "u64", "slot binding")

        def word_index(dst):
            t.binary(site, "+", lambda dst2: t.binary(
                site, "+", v("resident_word_base"),
                lambda dst3: t.binary(site, "*", lambda dst4: t.cast(site, "slot", "usize", dst4),
                                      v("literal8"), dst3), dst2), v("literal2"), dst)

        t.index(site, "arena_words", word_index, "array8 source address", 8, fat=True)
        t.payload(site, "indexed complete array8 source -> from_le_bytes received array8", 8)
        t.scalar(site, "from_le_bytes entry control", "from_le_bytes conversion",
                 "decoded scalar -> designated return", "from_le_bytes return control",
                 "returned scalar -> bytes binding")
        t.value(site, "remaining", "checked_sub received receiver")
        t.value(site, "bytes", "checked_sub received argument")
        t.scalar(site, "checked_sub entry control", "checked subtraction arithmetic",
                 "underflow predicate", "underflow branch", "Some tag source construction",
                 "arithmetic result -> Some payload source")
        t.payload(site, "complete Option16 constructor -> designated return Option16", 16)
        t.payload(site, "complete designated return Option16 -> caller received Option16", 16)
        t.scalar(site, "checked_sub return control", "received Option tag -> pattern operand",
                 "Some pattern predicate", "let-else pattern branch", "received Some payload -> next binding")
        t.value(site, "next", "remaining assignment")
        t.binary(site, "|", v("mask"), lambda dst: t.binary(site, "<<", v("literal1"), v("slot"), dst),
                 "mask assignment")
        t.value(site, "slot", "destination assignment")
        t.binary(site, "+", v("i"), v("literal1"), "i assignment")
        t.scalar(site, "while body implicit unit construction", "while back control")
        part = t.events[start:]
        need(sum(e["kind"] == "scalar" for e in part) == 112, "iteration scalar equation")
        need([e["bytes"] for e in part if e["kind"] == "copy"] == [8, 16, 16], "iteration full payloads")
        per_iteration.append({"iteration": i, "first": start, "events": len(part), "scalars": 112,
                              "copies": 3, "copy_bytes": [8, 16, 16]})
    return t.events, per_iteration


def pack(events):
    scalars = [e for e in events if e["kind"] == "scalar"]
    copies = [e for e in events if e["kind"] == "copy"]
    return ([{"kind": "scalar", "events": scalars[i:i+16]} for i in range(0, len(scalars), 16)] +
            [{"kind": "copy", "events": [e]} for e in copies])


def validate(groups):
    ids = []
    scalars = copies = 0
    for g in groups:
        need(g["kind"] in ("scalar", "copy") and bool(g["events"]), "group grammar")
        if g["kind"] == "scalar":
            need(len(g["events"]) <= 16, "scalar group exceeds16")
            need(all(e["kind"] == "scalar" and e["bytes"] == 0 for e in g["events"]), "scalar payload grammar")
            scalars += len(g["events"])
        else:
            need(len(g["events"]) == 1, "copy pooled with another event")
            e = g["events"][0]
            need(e["kind"] == "copy" and 0 < e["bytes"] <= 128, "copy width grammar")
            copies += 1
        ids.extend(e["id"] for e in g["events"])
    need(len(ids) == len(set(ids)), "duplicate event id")
    expected, _ = necessary_trace()
    actual = {e["id"]: e for g in groups for e in g["events"]}
    need(actual == {e["id"]: e for e in expected}, "required source edge missing or changed")
    return {"scalars": scalars, "copies": copies, "scalar_groups": (scalars+15)//16,
            "groups": (scalars+15)//16 + copies, "cap": G5_CAP}


def witness():
    # Complete resident/pin state for the actual G2/admission/miss predicates.
    # This is a source-level state, not a public File or native execution receipt.
    return {"fixture": {"slots": 64, "pins": 1, "base": 0, "capacity": 64, "entry": 64},
            "resident_rows": [[1, i, 1, 0, 0, 1, 0, 0] for i in range(64)],
            "pin_rows": [[U64, 0, 0, 0, 0, 0] for _ in range(64)],
            "progress": {"latch": 0, "calls": 1000, "q": [1000, 1, 1, 5, 1, 64, 64, 64, 0, 65, 0, 0, 0, U64, U64, 0]},
            "record_words": [1001, 5, 0, 1, 2, 2, 64, 7, 8, 9, U64, U64, U64, 64, 0, 64],
            "requested_function_defined": 1,
            "requested_plan": [64, 7, 8, 9, 0], "budget": {"remaining": 7680, "spent": 0},
            "arena_bytes": 8388608}


def model(w):
    f, rows, pins = w["fixture"], w["resident_rows"], w["pin_rows"]
    p, r = w["progress"], w["record_words"]
    need(w["arena_bytes"] == 8388608 and w["budget"] == {"remaining": 7680, "spent": 0}, "semantic prepay admission")
    need(1 <= f["slots"] <= 64 and 1 <= f["pins"] <= 64 and p["latch"] == 0 and p["q"][3] <= 10, "semantic shape admission")
    total = count = resident_pins = live = 0
    found = first_empty = U64
    timestamps = [0]*64
    eligibility = 0
    for i, row in enumerate(rows[:f["slots"]]):
        occupied, function, size, pinc = row[:4]
        need(occupied <= 1 and pinc <= f["pins"] and row[6] == 0 and row[7] == 0, "G2 resident header")
        if occupied == 1:
            resident_pins += pinc
            need(function < 80000 and 0 < size <= f["entry"] and total + size <= U64, "G2 occupied body")
            total += size
            count += 1
            if function == r[6]:
                need(found == U64, "G2 duplicate requested resident")
                found = i
        else:
            need(function == U64 and size == 0 and pinc == 0, "G2 empty shape")
            if first_empty == U64:
                first_empty = i
        timestamps[i] = row[4]
        if occupied == 1 and pinc == 0:
            eligibility |= 1 << i
    for entry, nonce, *_ in pins[:f["pins"]]:
        if entry == U64:
            need(nonce == 0, "G2 empty pin")
        else:
            need(entry < f["slots"] and 0 < nonce < p["q"][9], "G2 live pin header")
            need(rows[entry][0] == 1 and rows[entry][3] != 0, "G2 live pin backlink")
            live += 1
    need((count, total, resident_pins, live) == (p["q"][6], p["q"][7], p["q"][8], p["q"][8]), "G2 aggregate post-checks")
    need(p["q"][8] <= f["pins"] and p["q"][9] != 0, "G2 remaining post-checks")
    need(r[1] == 5 and r[6] < 80000 and w["requested_function_defined"] == 1 and found == U64, "source dispatch/function")
    plan = w["requested_plan"]
    need(plan[:4] == r[6:10] and (plan[4] == 0 or plan[4] == r[13]), "miss plan admission")
    need(0 < r[13] <= f["entry"] and r[14] == f["base"] and r[15] == f["capacity"] and f["base"] + r[13] <= f["capacity"], "miss request admission")
    # Independently transcribed production merge semantics, no operation credit.
    # Actual first pass emits B1024; five later fixed passes end at A512.
    order = []
    for lo in range(0, 64, 2):
        left = lo if eligibility & (1 << lo) else 255
        right = lo+1 if eligibility & (1 << (lo+1)) else 255
        take_left = right == 255 or (left != 255 and timestamps[lo] <= timestamps[lo+1])
        order.extend([left, right] if take_left else [right, left])
    pass_destinations = [1024]
    for pass_number, width in enumerate([2, 4, 8, 16, 32], 1):
        output = []
        for base in range(0, 64, 2*width):
            lp, le, rp, re = base, base+width, base+width, base+2*width
            li, ri = order[lp], order[rp]
            for _ in range(2*width):
                take_left = li != 256 if ri >= 255 else (li < 255 and timestamps[li] <= timestamps[ri])
                if take_left:
                    output.append(li)
                    lp += 1
                    li = order[lp] if lp < le else 256
                else:
                    output.append(ri)
                    rp += 1
                    ri = order[rp] if rp < re else 256
        order = output
        pass_destinations.append(512 if pass_number % 2 else 1024)
    reference = sorted([i for i in range(64) if eligibility & (1 << i)], key=lambda i: (timestamps[i], i))
    need(order == reference and len(order) == len(set(order)) == 64, "actual merge ordering/permutation")
    need(pass_destinations == [1024, 512, 1024, 512, 1024, 512], "actual Candidate destination sequence")
    headroom = f["capacity"] - f["base"] - r[13]
    remaining, mask, destination = total, 0, first_empty
    path = []
    for i in range(64):
        need(not (remaining <= headroom and destination != U64), "prefix premature break")
        slot_byte = order[i]
        need(slot_byte != 255 and 0 <= slot_byte < 64, "prefix sentinel or slot bound")
        slot = slot_byte
        size = rows[slot][2]
        need(remaining >= size, "checked_sub refusal")
        before = remaining
        remaining -= size
        mask |= 1 << slot
        destination = slot
        path.append({"i": i, "slot": slot, "bytes": size, "remaining_before": before,
                     "remaining_after": remaining, "first_and_operand": before <= headroom,
                     "destination_rhs_evaluated": before <= headroom, "checked_sub_tag": "Some"})
    need(remaining == headroom == 0 and mask == U64 and destination == 63, "full64 victim witness")
    return {"source_admitted": True, "public_file_reachability_proved": False,
            "Rust_or_native_executed": False, "eligibility": eligibility,
            "sort_destinations": pass_destinations, "sorted_slots": order, "path": path,
            "final": {"remaining": remaining, "headroom": headroom, "mask": mask,
                      "destination": destination, "feasible": destination != U64 and remaining <= headroom}}


def source_check(data):
    need(digest(data) == SOURCE, "exact proposed source changed")
    text = data.decode()
    start = text.index("            let headroom = f.capacity - f.base - w[13];")
    end = text.index("            sq(c, 10, mask);", start)
    excerpt = text[start:end]
    need(excerpt == (HERE / "source-g5.rs.txt").read_text(), "G5 exact source excerpt")
    call_end = text.index("\n        }", end)
    calls = text[end:call_end]
    need(calls == (HERE / "source-G6-six-calls.rs.txt").read_text(), "G6 exact six-call boundary")
    old = ROOT / "verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs"
    olddata = old.read_bytes()
    need(digest(olddata) == "0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8", "selected old C3 source changed")
    need(olddata.decode().count(calls) == 1, "six G6 calls differ from selected C3")
    # Whole bytes and manual source audit bind semantics; text anchors only fix scope.
    return {"source_sha256": SOURCE, "G5_excerpt_sha256": digest(excerpt.encode()),
            "G5_start_line": text[:start].count("\n")+1, "G5_end_line": text[:end].count("\n"),
            "G6_six_calls_sha256": digest(calls.encode()), "G6_six_calls_byte_identical_to_C3": True}


def expect_rejection(name, fn):
    try:
        fn()
    except (ValueError, KeyError, IndexError, TypeError):
        return {"name": name, "rejected": True}
    raise ValueError("negative control accepted: " + name)


def main():
    bindings = json.loads((HERE / "input-bindings.json").read_text())
    for b in bindings["files"]:
        need(digest((ROOT / b["path"]).read_bytes()) == b["sha256"], "input custody: " + b["path"])
    source = (ROOT / bindings["source_path"]).read_bytes()
    custody = source_check(source)
    state = json.loads((HERE / "witness.json").read_text())
    need(state == witness(), "witness data changed")
    path = model(state)
    events, parts = necessary_trace()
    groups = pack(events)
    totals = validate(groups)
    need(totals == {"scalars": 7199, "copies": 192, "scalar_groups": 450, "groups": 642, "cap": 640}, "necessary arithmetic")
    controls = []
    bad = copy.deepcopy(groups); bad[0]["events"].append(bad[1]["events"].pop())
    controls.append(expect_rejection("17-scalar group", lambda: validate(bad)))
    bad = copy.deepcopy(groups); bad[-1]["events"][0]["bytes"] = 129
    controls.append(expect_rejection("129-byte copy", lambda: validate(bad)))
    bad = copy.deepcopy(groups); bad[-1]["events"][0]["bytes"] = 8
    controls.append(expect_rejection("narrow full Option16", lambda: validate(bad)))
    bad = copy.deepcopy(groups); bad.pop(-1)
    controls.append(expect_rejection("missing designated Option16 return transfer", lambda: validate(bad)))
    bad = copy.deepcopy(groups); bad[1]["events"][0]["id"] = bad[0]["events"][0]["id"]
    controls.append(expect_rejection("duplicate source event", lambda: validate(bad)))
    bad = copy.deepcopy(groups)
    for g in bad:
        g["events"] = [e for e in g["events"] if e["operation"] != "arena_words length -> Index received receiver.length"]
    controls.append(expect_rejection("fat slice collapsed to thin fixed receiver", lambda: validate(bad)))
    controls.append(expect_rejection("exact source changed", lambda: source_check(source+b"\n")))
    bad = copy.deepcopy(state); bad["resident_rows"][63][2] = 2
    controls.append(expect_rejection("mismatched aggregate source state", lambda: model(bad)))
    bad = copy.deepcopy(state); bad["fixture"]["capacity"] = 65
    controls.append(expect_rejection("changed headroom witness", lambda: model(bad)))
    payload = {"schema": 1, "scope": "necessary G5 subtrace only", "events": events,
               "groups": groups, "parts": parts, "totals": totals}
    (HERE / "necessary-ledger.json.gz").write_bytes(gzip.compress(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    write("witness-path.json", path)
    result = {"schema": 1, "status": "exact proposed source has a necessary G5 over-cap witness",
              "source": custody, "totals": totals, "over_cap_at_least": 2,
              "negative_controls": controls, "python": sys.version, "optimized": not __debug__,
              "G3_G4_G5_complete_upper_built": False, "whole_lifetime_union_accepted": False,
              "source_changed": False, "implementation_accepted": False, "GA_qualified": False,
              "native_UI_capture_process_inventory_or_Git_executed": False}
    write("check-result-optimized.json" if not __debug__ else "check-result.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
