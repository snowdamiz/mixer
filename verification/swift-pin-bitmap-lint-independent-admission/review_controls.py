#!/usr/bin/env python3
"""Independent finite source/data replay, not Rust execution or acceptance."""
import offline
offline.install()
import ast
import collections
import difflib
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKET = ROOT / "verification/swift-pin-bitmap-lint-correction"
ACTUAL = ROOT / "verification/clock-format-actual-results/local/format-extract/_temp/pin-bitmap-format-lint-v1-evidence"
BASELINE = "af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b"
CANDIDATE = "7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748"
CHECKS = 0
EVIDENCE = {}


def check(value, label):
    global CHECKS
    CHECKS += 1
    if not value:
        raise AssertionError(label)


def row(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def closure(rows):
    return hashlib.sha256("".join(n + "\0" + rows[n]["sha256"] + "\n" for n in sorted(rows)).encode()).hexdigest()


def load(name):
    return json.loads((PACKET / name).read_text())


def texts():
    m = load("manifest.json")
    old = {n: (ACTUAL / "format/candidate/after" / n if (ACTUAL / "format/candidate/after" / n).exists() else ROOT / "vm" / n).read_text() for n in m["overlayPaths"]}
    new = {n: (ROOT / m["materializationPaths"][n]).read_text() for n in m["overlayPaths"]}
    return old, new


class Review(unittest.TestCase):
    def test_seal_and_complete_source_closures(self):
        check(row((PACKET / "seal.json").read_bytes())["sha256"] == "89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052", "exact producer seal")
        seal = load("seal.json")
        check(len(seal["files"]) == 31, "31 sealed members")
        for name, expected in seal["files"].items():
            check(row((PACKET / name).read_bytes()) == expected, name)
        m = load("manifest.json")
        for key, path in (("baselineFiles", lambda n: ROOT / "vm" / n), ("candidateFiles", lambda n: ROOT / m["materializationPaths"][n])):
            check(len(m[key]) == 136, key)
            for n, expected in m[key].items():
                check(row(path(n).read_bytes()) == expected, n)
        check(closure(m["baselineFiles"]) == BASELINE, "baseline closure")
        check(closure(m["candidateFiles"]) == CANDIDATE, "candidate closure")
        check(set(m["candidateFiles"]) == set(m["baselineFiles"]), "source roster")
        check(len(m["overlayPaths"]) == 15, "15 overlays")
        check({n for n in m["candidateFiles"] if m["candidateFiles"][n] != m["baselineFiles"][n]} == set(m["overlayPaths"]), "exact overlay membership")
        EVIDENCE["source"] = {"members": 136, "overlays": 15, "baseline": BASELINE, "candidate": CANDIDATE}

    def test_actual_bindings_and_observed_lint_union(self):
        for n, expected in load("actual-bindings.json")["files"].items():
            check(row((ROOT / n).read_bytes()) == expected, n)
        counts = []
        for arm, expected in (("baseline", 50), ("candidate", 46)):
            actual = json.loads((ACTUAL / ("clippy-" + arm + ".json")).read_text())
            check(actual["exit"] == 101 and not actual["lintPassed"] and not actual["buildFinished"], arm)
            counter = collections.Counter()
            for d in actual["diagnostics"]:
                if d["level"] == "error":
                    counter[(d["code"]["code"], d["message"], tuple(sorted({s["file_name"] for s in d["spans"] if s["is_primary"]})))] += 1
            check(sum(counter.values()) == expected, arm)
            counts.append(counter)
        check(sum((counts[0] & counts[1]).values()) == 45, "shared")
        check(sum((counts[0] | counts[1]).values()) == 51, "union")
        EVIDENCE["lint"] = {"baseline": 50, "candidate": 46, "shared": 45, "union": 51, "causalAttribution": False, "exhaustive": False}

    def test_exact_replay_and_diff(self):
        old, new = texts()
        replay = dict(old)
        edits = load("edit-log.json")["edits"]
        check(len(edits) == 199, "199 ledger edits")
        for e in edits:
            n, before, after = e["path"], e["before"], e["after"]
            if "position" in e:
                p = e["position"]
                check(replay[n][p:p + len(before)] == before, "edit preimage")
                replay[n] = replay[n][:p] + after + replay[n][p + len(before):]
            else:
                check(replay[n].count(before) == e["count"], "edit cardinality")
                replay[n] = replay[n].replace(before, after)
        check(replay == new, "complete replay")
        diff = "".join("".join(difflib.unified_diff(old[n].splitlines(keepends=True), new[n].splitlines(keepends=True), fromfile="formatted/vm/" + n, tofile="candidate/vm/" + n)) for n in sorted(old))
        check(diff == (PACKET / "formatted-to-candidate.diff").read_text(), "exact diff")

    def test_mechanical_callers_and_measured_slots(self):
        edits = load("edit-log.json")["edits"]
        mechanical = [e for e in edits if "mechanical output-slot" in e["reason"]]
        check(len(mechanical) == 147, "147 ordinary caller rewrites")
        for e in mechanical:
            expected = "{letmutreturned=None;" + e["before"][:-1] + ",&mutreturned);returned.unwrap()}"
            check(re.sub(r"\s+", "", e["after"]) == re.sub(r"\s+", "", expected), "mechanical stack wrapper")
        measured = [e for e in edits if "measured closure" in e["reason"]]
        check(len(measured) == 15, "15 measured slots")
        for e in measured:
            check("let (()," in e["after"] and " = None;" in e["after"] and ".unwrap();" in e["after"], "unit observer output")
            check(not any(x in e["after"] for x in ("Box", "Vec", "clone", "unsafe", "forget")), "no extra allocation or escape")
        old, new = texts()
        for n in new:
            if "construct_owned" in new[n]:
                EVIDENCE.setdefault("constructOwnedPaths", []).append(n)
        check(set(EVIDENCE["constructOwnedPaths"]) == {"src/experimental_swift_reactor/execution_tests.rs", "src/experimental_swift_reactor/value_operation_tests.rs"}, "complete imported helper paths")
        for n in load("manifest.json")["candidateFiles"]:
            if n.endswith(".rs") and n not in new:
                check("construct_owned" not in (ROOT / "vm" / n).read_text(), "no unadapted external caller")
        observer = (ROOT / "vm/src/experimental_swift_reactor/allocation_tests.rs").read_text()
        check("let result = body();\n    drop(reset);\n    (result, STATS.with(Cell::get))" in observer, "observer cutoff unchanged")

    def test_assertions_tests_literals_and_sl_bodies(self):
        old, new = texts()
        totals = [0, 0, 0]
        for n in old:
            patterns = (r"#\[test\]\s*fn\s+(\w+)", r"\b(assert(?:_eq|_ne)?)\s*!", r'"((?:swift_|memory_|wrong_|owner_)[^"\n]*)"')
            for i, p in enumerate(patterns):
                a, b = re.findall(p, old[n]), re.findall(p, new[n])
                check(a == b, "ordered inventory " + n)
                totals[i] += len(b)
        check(totals == [271, 2225, 95], "preserved inventories")
        EVIDENCE["preservedInventory"] = dict(zip(("tests", "assertions", "diagnosticLiterals"), totals))
        for n in new:
            check(new[n].count("#[allow") == old[n].count("#[allow"), "no new allow")
            check(new[n].count("#[expect") == old[n].count("#[expect"), "no new expect")

    def test_production_boundary_and_pointer_fixture(self):
        old, new = texts()
        borrowed = "src/experimental/cache/borrowed.rs"
        cache = "src/experimental_swift_reactor/cache.rs"
        check(old[borrowed] == new[borrowed], "formatted borrowed exact")
        boundary = "#[cfg(test)]\npub(super) mod inspection {"
        check(old[cache].split(boundary)[0] == new[cache].split(boundary)[0], "production cache prefix")
        pointer = "tests/experimental_guest_ui_validation.rs"
        check("ptr::with_exposed_provenance::<u8>(1)" in new[pointer], "address one exposed provenance")
        check("usize::MAX as *const u8" in new[pointer] and "4 * 1024 * 1024 + 1" in new[pointer], "other invalid pointer bounds")
        for n in ("Cargo.toml", "Cargo.lock", "src/experimental/policy.rs", "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/lifecycle.rs", "src/experimental_swift_reactor/execution.rs", "src/experimental_swift_reactor/frame_operations.rs"):
            check(n not in new, "unchanged production authority " + n)

    def test_integer_row_and_failure_precedence_contracts(self):
        sets = [range(0x45, 0x5b), range(0x67, 0x8b), [0xa7, 0xac, 0xad], range(0xc0, 0xc5), range(0x5b, 0x67), range(0x8b, 0xa7), range(0xa8, 0xac), range(0xae, 0xc0)]
        accepted = set().union(*sets)
        for op in range(256):
            check((op in accepted) == (0x45 <= op <= 0xc4), "opcode set")
        growth = (584 + 585) * 65536
        for value in (0, 1, growth - 1, growth, growth + 1, growth + 2, 2**32 - 1, 2**64 - 1):
            check((value >= 1 + growth) == (value > growth), "finite threshold")
        for length in range(129):
            check(list(range(0, length - length % 32, 32)) == [32 * n for n in range(length // 32)], "complete row starts")
        # Independent tagged value truth table: full identity and precedence,
        # not a Rust execution or a substitute for borrow/type checking.
        for prepare_ok in (False, True):
            for operation_ok in (False, True):
                for cleanup_ok in (False, True):
                    result, prep_error, cleanup_error = object(), object(), object()
                    original = (result if operation_ok else prep_error) if prepare_ok and cleanup_ok else (cleanup_error if not cleanup_ok else prep_error)
                    slot = (result if operation_ok else prep_error) if prepare_ok else prep_error
                    if not cleanup_ok:
                        slot = cleanup_error
                    check(slot is original, "completion or refund failure precedence")

    def test_nine_node_oracles_are_exact_and_do_not_detach(self):
        names = {}
        for name in ("differential", "experimental_oracle", "float_differential", "table_memory_differential"):
            source = (ROOT / "vm/tests" / (name + ".rs")).read_text()
            names[name] = re.findall(r"#\[ignore[^\n]*\]\s*fn\s+(\w+)", source)
            check(not any(x in source for x in ("setsid", "setpgid", "pre_exec", "process_group", "detached", "CommandExt")), "no source detachment")
            check(".wait_with_output()" in source and ".stdin\n        .take()" in source, "pipe ownership consumed and child waited")
            check("node:child_process" not in source and "require('node:net')" not in source, "no nested script process/network API")
        check([len(names[n]) for n in names] == [3, 1, 3, 2], "9 oracle roster")
        all_ignored = []
        for n in load("manifest.json")["candidateFiles"]:
            if n.endswith(".rs"):
                source = (ROOT / load("manifest.json")["materializationPaths"][n]).read_text()
                all_ignored += [(n, s) for s in re.findall(r"#\[ignore[^\n]*\]", source)]
        check(len(all_ignored) == 9, "no hidden ignored tests")
        EVIDENCE["nodeOracles"] = names


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Review))
    report = {"schema": 1, "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped), "dataAssertions": CHECKS, "pythonVersion": sys.version, "guardBeforeSubjectImports": True, "producerModulesExecuted": False, "liveApiAttempts": offline.ATTEMPTS, "RustRuns": 0, "evidence": EVIDENCE}
    (HERE / "review-controls-result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    if not result.wasSuccessful():
        raise SystemExit(1)
