#!/usr/bin/env python3
"""Guarded source/data controls. These do not compile or execute the VM."""
from offline_guard import install
install()

import ast
import collections
import difflib
import io
import json
import os
import re
import signal
import socket
import subprocess
import sys
import unittest
from pathlib import Path

import offline_guard
import prepare

HERE, ROOT, ACTUAL = prepare.HERE, prepare.ROOT, prepare.ACTUAL
ASSERTIONS = 0
INVENTORY = {}


def check(value, message="source/data assertion"):
    global ASSERTIONS
    ASSERTIONS += 1
    if not value:
        raise AssertionError(message)


def load(name):
    return json.loads((HERE / name).read_text())


def texts():
    manifest = load("manifest.json")
    old = {n: (prepare.FORMATTED / n if n in prepare.FORMATTED_PATHS else ROOT / "vm" / n).read_text() for n in manifest["overlayPaths"]}
    new = {n: (HERE / "candidate/vm" / n).read_text() for n in manifest["overlayPaths"]}
    return old, new


class Controls(unittest.TestCase):
    def test_01_preimport_guard_and_denied_live_apis(self):
        for name in ("prepare.py", "inspect_actual.py", "test_controls.py", "finalize.py"):
            tree = ast.parse((HERE / name).read_text())
            body = tree.body[1:] if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) else tree.body
            check(isinstance(body[0], ast.ImportFrom) and body[0].module == "offline_guard", name)
            check(isinstance(body[1], ast.Expr) and isinstance(body[1].value, ast.Call) and body[1].value.func.id == "install", name)
        apis = [subprocess.Popen, subprocess.run, subprocess.check_output, socket.socket,
                socket.create_connection, os.kill, os.killpg, os.waitpid, os.setsid,
                os.setpgid, os.getpgid, os.getsid, signal.signal, signal.raise_signal]
        for api in apis:
            check(api is offline_guard.denied)
            with self.assertRaisesRegex(AssertionError, "denied"):
                api()
        check(sys.dont_write_bytecode)

    def test_02_complete_canonical_and_candidate_closures(self):
        m = load("manifest.json")
        check(len(m["baselineFiles"]) == len(m["candidateFiles"]) == 136)
        for n, expected in m["baselineFiles"].items():
            check(prepare.row(ROOT / "vm" / n) == expected, n)
        check(prepare.closure(m["baselineFiles"]) == prepare.BASELINE_TREE)
        for n, expected in m["candidateFiles"].items():
            check(prepare.row(ROOT / m["materializationPaths"][n]) == expected, n)
        check(prepare.closure(m["candidateFiles"]) == m["candidateTreeSHA256"])
        check(set(m["candidateFiles"]) == set(m["baselineFiles"]))
        check(len(m["overlayPaths"]) == 15)
        check(all(n in m["candidateFiles"] for n in m["overlayPaths"]))
        check(m["candidateFiles"]["Cargo.toml"] == m["baselineFiles"]["Cargo.toml"])
        check(m["candidateFiles"]["Cargo.lock"] == m["baselineFiles"]["Cargo.lock"])

    def test_03_exact_frozen_inputs_and_actual_review(self):
        bindings = load("actual-bindings.json")
        for p, expected in bindings["files"].items():
            check(prepare.row(ROOT / p) == expected, p)
        check(bindings["runID"] == 40814738980 and bindings["rawFilesLocalOnly"])
        for name, digest in {
            "sanitized-result.json": "0e30665d7a380ba1eb757fbf152b9ceed88886c4a9f7286e334b2fa7ef1011a5",
            "seal.json": "27a5648252f940c34d41e15934da20b1dc5dac1a32ae094cbdd8c0ec2c87a2e4",
        }.items():
            check(prepare.row(ROOT / "verification/clock-format-actual-results" / name)["sha256"] == digest)
        source = json.loads((ACTUAL / "source-manifest.json").read_text())
        rows = dict(source["candidateFiles"])
        for n in prepare.FORMATTED_PATHS:
            check(prepare.row(ACTUAL / "format/candidate/before" / n) == rows[n], n)
            rows[n] = prepare.row(prepare.FORMATTED / n)
        check(prepare.closure(rows) == prepare.FORMATTED_TREE)
        check(rows == load("manifest.json")["priorFormattedFiles"])

    def test_04_observed_diagnostic_union_without_causal_attribution(self):
        counts = {}
        for arm, total in (("baseline", 50), ("candidate", 46)):
            doc = json.loads((ACTUAL / f"clippy-{arm}.json").read_text())
            check(doc["exit"] == 101 and not doc["lintPassed"] and not doc["buildFinished"])
            count = collections.Counter()
            for d in doc["diagnostics"]:
                if d.get("level") == "error" and d.get("code"):
                    paths = tuple(sorted({s["file_name"] for s in d["spans"] if s["is_primary"]}))
                    count[(d["code"]["code"], paths)] += 1
            check(sum(count.values()) == total)
            counts[arm] = count
        shared = counts["baseline"] & counts["candidate"]
        union = counts["baseline"] | counts["candidate"]
        check(sum(shared.values()) == 45)
        check(sum(union.values()) == 51)
        check(len({key[0] for key in union}) == 16)
        check(sum((counts["baseline"] - counts["candidate"]).values()) == 5)
        check(sum((counts["candidate"] - counts["baseline"]).values()) == 1)
        check(not load("diagnostic-index.json")["comparison"]["candidateOnlyIsSemanticAttribution"])
        INVENTORY["diagnosticCategories"] = dict(sorted(collections.Counter({code: sum(v for (c, _), v in union.items() if c == code) for code, _ in union}).items()))

    def test_05_exact_edit_replay_and_path_authority(self):
        old, new = texts()
        replay = dict(old)
        edits = load("edit-log.json")["edits"]
        m = load("manifest.json")
        check(len(edits) == 199)
        for e in edits:
            n, before, after = e["path"], e["before"], e["after"]
            check(n in m["observedDiagnosticPaths"] or n == prepare.DEPENDENCY)
            check(bool(e["reason"]))
            if "position" in e:
                pos = e["position"]
                check(replay[n][pos:pos + len(before)] == before, e["reason"])
                replay[n] = replay[n][:pos] + after + replay[n][pos + len(before):]
            else:
                check(replay[n].count(before) == e["count"], e["reason"])
                replay[n] = replay[n].replace(before, after)
        check(replay == new)
        dependency_edits = [e for e in edits if e["path"] == prepare.DEPENDENCY]
        check(len(dependency_edits) == 1 and "mechanical output-slot" in dependency_edits[0]["reason"])
        check(m["directCompatibilityDependency"]["canonicalPreimage"] == m["baselineFiles"][prepare.DEPENDENCY])
        check(m["directCompatibilityDependency"]["rootAuthorized"])

    def test_06_test_assertion_and_error_literal_inventories(self):
        old, new = texts()
        inventory = {}
        for n in old:
            methods = lambda s: re.findall(r"#\[test\]\s*fn\s+(\w+)", s)
            macros = lambda s: collections.Counter(re.findall(r"\b(assert(?:_eq|_ne)?)\s*!", s))
            errors = lambda s: collections.Counter(re.findall(r'"((?:swift_|memory_|wrong_|owner_)[^"\n]*)"', s))
            check(methods(old[n]) == methods(new[n]), n)
            check(macros(old[n]) == macros(new[n]), n)
            check(errors(old[n]) == errors(new[n]), n)
            inventory[n] = {"tests": len(methods(new[n])), "assertions": dict(macros(new[n])), "preservedErrorLiterals": sum(errors(new[n]).values())}
        INVENTORY["preservedSourceInventories"] = inventory
        life = prepare.REA + "lifecycle_tests.rs"
        # The SL13/SL14 corrected regression source remains exact; SL21 alone
        # gains a const block around its two existing constant assertions.
        for number in ("13", "14"):
            for m in re.finditer(r"fn (swift_lifecycle_sl" + number + r"\w*)\([^)]*\)\s*\{", old[life]):
                end = prepare.closing(old[life], m.end() - 1)
                body = old[life][m.start():end + 1]
                check(body in new[life], m[1])

    def test_07_production_bitmap_and_numeric_authorities_unchanged(self):
        old, new = texts()
        borrowed = "src/experimental/cache/borrowed.rs"
        check(old[borrowed] == new[borrowed])
        cache = prepare.REA + "cache.rs"
        before, after = old[cache], new[cache]
        boundary = "#[cfg(test)]\npub(super) mod inspection {"
        check(before.split(boundary)[0] == after.split(boundary)[0])
        check(after.replace('.expect_err("malformed scan must fail")', '.err()\n        .expect("malformed scan must fail")') == before)
        check("#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]\npub(crate) struct Counts" in (ROOT / "vm/src/experimental/cache/decode.rs").read_text())
        for n in ("src/experimental/policy.rs", "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/lifecycle.rs", "src/experimental_swift_reactor/execution.rs", "src/experimental_swift_reactor/frame_operations.rs"):
            check(n not in load("manifest.json")["overlayPaths"], n)

    def test_08_opcode_and_integer_boundary_equivalence(self):
        old_set = set(range(0x45, 0x5b)) | set(range(0x67, 0x8b)) | {0xa7, 0xac, 0xad} | set(range(0xc0, 0xc5)) | set(range(0x5b, 0x67)) | set(range(0x8b, 0xa7)) | set(range(0xa8, 0xac)) | set(range(0xae, 0xc0))
        for opcode in range(256):
            check((opcode in old_set) == (0x45 <= opcode <= 0xc4))
        for value in range(-2, 258):
            check((value >= 4 and value <= 7) == (value in range(4, 8)))
            check((value >= 34 and value < 164) == (value in range(34, 164)))
            check((value >= 34 and value < 63) == (value in range(34, 63)))
        page = 65_536
        growth = (584 + 585) * page
        check(growth < 2**64 - 1)
        allowed = list(range(65_537)) + [growth - 1, growth, growth + 1, growth + 2, 2**32 - 1, 2**64 - 1]
        for a in allowed:
            check((a >= 1 + growth) == (a > growth))
        seed_cases = 0
        for bits in (32, 64):
            for value in list(range(4096)) + [2**bits - 1, 2**bits - 2]:
                product = value * 37 % 2**bits
                # Original unparenthesized and candidate grouped forms, with
                # an independent low-byte bitwise oracle to catch a regrouping.
                legacy = (product ^ value // 251) & 255
                candidate = (product ^ (value // 251)) & 255
                quotient = value // 251
                oracle = sum(1 << bit for bit in range(8) if (product >> bit & 1) != (quotient >> bit & 1))
                check(legacy == candidate == oracle)
                seed_cases += 1
        INVENTORY["integerEquivalenceCases"] = {"opcodes": 256, "rangePredicates": 780, "growthThresholds": len(allowed), "seedValues": seed_cases, "growthwork": growth}

    def test_09_rows_and_word_enumeration_retain_complete_observations(self):
        for length in list(range(257)) + [2_560_000, 2_560_001, 2_560_031]:
            old_rows = [(at, at + 32) for at in range(0, length - length % 32, 32)]
            new_rows = [(index * 32, (index + 1) * 32) for index in range(length // 32)]
            check(old_rows == new_rows)
        words = list(range(100, 164))
        for i, word in enumerate(words):
            check(word == words[i])
            check((i not in [35, 38, 50]) == (i not in {35, 38, 50}))
        old, new = texts()
        diag = prepare.REA + "diagnostic_result_v1_tests.rs"
        check("words::<64>" in old[diag] and "w.iter().enumerate()" in new[diag])
        check("assert_eq!(*word, 100 + i as u64);" in new[diag])

    def test_10_output_slots_preserve_error_precedence_without_boxing(self):
        old, new = texts()
        cache = new[prepare.REA + "cache_tests.rs"]
        execution = new[prepare.REA + "execution_tests.rs"]
        check("outcome: &mut Option<Result<SwiftFunctionCache, SwiftRunFailure>>" in cache)
        check("outcome: &mut Option<Result<SwiftFunctionPin, SwiftRunFailure>>" in cache)
        check("outcome: &mut Option<Result<SwiftReactorInstance, ConstructionFailure>>" in execution)
        check("Ok(()) => result,\n                Err(failure) => Err(failure)" in cache)
        check("*outcome = Some(Err(cleanup_failure));\n        return;" in cache)
        check("phase.complete(returned)?" not in cache[:cache.index("fn cleanup(")])
        edits = load("edit-log.json")["edits"]
        measured = [e for e in edits if "measured closure" in e["reason"]]
        check(len(measured) == 15)
        for e in measured:
            check("let ((), " in e["after"] and " = None;" in e["after"])
            check(".unwrap();" in e["after"])
        for e in edits:
            for token in ("Box::", "boxed", "#[allow", "#[expect", "#![allow", "-A warnings"):
                check(token not in e["after"], token)
        # Finite independent state/control-flow table for the exact former ?
        # precedence. Payload objects retain identity, including cleanup tails.
        for prepared in (False, True):
            for constructed in (False, True):
                for completed in (False, True):
                    for refunded in (False, True):
                        owner, construct_error, complete_error, prepare_error, refund_error = [object() for _ in range(5)]
                        expected = {
                            (False, False): ("err", refund_error),
                            (False, True): ("err", prepare_error),
                            (True, False): ("err", complete_error),
                            (True, True): ("ok", owner) if constructed else ("err", construct_error),
                        }[(prepared, completed if prepared else refunded)]
                        slot, trace = [None], ["prepare"]
                        if not prepared:
                            trace.append("drop_original_proof")
                            if not refunded:
                                slot[0] = ("err", refund_error)
                            else:
                                slot[0] = ("err", prepare_error)
                        else:
                            trace.append("construct")
                            result = ("ok", owner) if constructed else ("err", construct_error)
                            trace.append("complete")
                            if completed:
                                slot[0] = result
                            else:
                                slot[0] = ("err", complete_error)
                        check(slot[0][0] == expected[0] and slot[0][1] is expected[1])
                        check(trace == (["prepare", "construct", "complete"] if prepared else ["prepare", "drop_original_proof"]))

    def test_11_scopes_and_pointer_contract_preserve_invalid_inputs(self):
        old, new = texts()
        for rel, name in ((prepare.REA + "cache_tests.rs", "_phase"), (prepare.REA + "cache_tests.rs", "_operation"), (prepare.REA + "execution_tests.rs", "_original")):
            check("let " + name in new[rel])
        control = (ROOT / "vm/src/experimental_swift_reactor/control.rs").read_text()
        check("pub(crate) struct ReservationTicket {\n    owner: u64,\n    category: SwiftReservationCategory,\n    bytes: usize," in control)
        check("impl Drop for ReservationTicket" not in control)
        ptr = "tests/experimental_guest_ui_validation.rs"
        check(old[ptr].count("1usize as *const u8") == 1)
        check(new[ptr].count("ptr::with_exposed_provenance::<u8>(1)") == 1)
        for expression in ("usize::MAX as *const u8", "usize::MAX as *const MixerVmLimits", "storage.as_mut_ptr().add(1025).cast::<MixerVmReport>()", "4 * 1024 * 1024 + 1"):
            check(old[ptr].count(expression) == new[ptr].count(expression) > 0, expression)
        # ptr::with_exposed_provenance documents exact equivalence to addr as
        # *const T. u8 alignment is1; the selected test address is still exactly1.
        check(1 % 1 == 0)

    def test_12_diff_reproducibility_and_pending_boundaries(self):
        m = load("manifest.json")
        old, new = texts()
        for name, before in (("formatted-to-candidate.diff", old), ("canonical-to-candidate.diff", {n: (ROOT / "vm" / n).read_text() for n in m["overlayPaths"]})):
            expected = "".join("".join(difflib.unified_diff(before[n].splitlines(keepends=True), new[n].splitlines(keepends=True), fromfile=name.split("-to-")[0] + "/vm/" + n, tofile="candidate/vm/" + n)) for n in m["overlayPaths"])
            check((HERE / name).read_text() == expected)
        check(not m["canonicalProductFilesEdited"] and not m["priorFrozenPacketsEdited"])
        check(not m["hostHarnessChanged"] and not m["newDispatchSelected"])
        check("pending" in m["runtimeFormattingLintStatus"])
        check("rust-version" not in (ROOT / "vm/Cargo.toml").read_text())
        for p in (ROOT / "README.md", ROOT / "vm/README.md", ROOT / "contracts/vm-profile-v1.json", ROOT / "release/toolchain-candidate.json"):
            check(not re.search(r"(?:MSRV|minimum supported Rust|rust-version)", p.read_text()))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    stream = io.StringIO()
    result = unittest.TextTestRunner(verbosity=2, stream=stream).run(suite)
    output = {"schema": 1, "scope": "guarded source/data controls only; no actual Rust compiler, rustfmt, Clippy, VM, native, UI or capture execution",
              "command": "python3 -B verification/swift-pin-bitmap-lint-correction/test_controls.py", "pythonVersion": sys.version,
              "passed": result.testsRun - len(result.failures) - len(result.errors), "failed": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "assertions": ASSERTIONS, "guardInstalledBeforeImplementationImports": True,
              "realNestedProcessesSessionsGroupsSignalsWaitsSockets": 0, "candidateTreeSHA256": load("manifest.json")["candidateTreeSHA256"],
              "inventories": INVENTORY, "pending": ["Independent source review", "Fresh hosted formatting and all-target Clippy", "Fresh full Debug and Release regression", "Canonical integration", "Native, physical-device, published-package FieldLog and GA acceptance"]}
    prepare.save(HERE / "pure-result.json", output)
    summary = json.dumps({k: output[k] for k in ("passed", "failed", "errors", "assertions", "candidateTreeSHA256")})
    (HERE / "local").mkdir(exist_ok=True)
    (HERE / "local/pure-controls.stderr").write_text(stream.getvalue())
    (HERE / "local/pure-controls.stdout").write_text(summary + "\n")
    print(stream.getvalue(), end="", file=sys.stderr)
    print(summary)
    sys.exit(not result.wasSuccessful())
