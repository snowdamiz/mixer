#!/usr/bin/env python3
"""Prepare a thin source overlay from immutable observed diagnostic inputs."""
from offline_guard import install
install()

import collections
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ACTUAL = ROOT / "verification/clock-format-actual-results/local/format-extract/_temp/pin-bitmap-format-lint-v1-evidence"
FORMATTED = ACTUAL / "format/candidate/after"
BASELINE_TREE = "af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b"
FORMATTED_TREE = "ffbc544201cf3d6ddf303b49f952c0e4b839bdfaf42e18588074d6c4c169b971"
REVISION = "6d57e05e58e6d614e58a0a4dc0fad661264fb46f"
REA = "src/experimental_swift_reactor/"
FORMATTED_PATHS = ["src/experimental/cache/borrowed.rs", REA + "cache.rs", REA + "cache_tests.rs", REA + "lifecycle_tests.rs"]
DEPENDENCY = REA + "value_operation_tests.rs"
EDITS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}


def closure(rows):
    return sha("".join(n + "\0" + rows[n]["sha256"] + "\n" for n in sorted(rows)).encode())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def edit(text, rel, old, new, reason, count=1):
    assert old != new
    assert text.count(old) == count, (rel, reason, text.count(old), count, old)
    EDITS.append({"path": rel, "reason": reason, "count": count, "before": old, "after": new})
    return text.replace(old, new)


def closing(text, start):
    """Balance a Rust call's delimiters; relevant helper arguments have no raw strings."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [pairs[text[start]]]
    at = start + 1
    while stack:
        c = text[at]
        if text.startswith("//", at):
            at = text.index("\n", at) + 1
            continue
        if text.startswith("/*", at):
            end = text.index("*/", at + 2)
            at = end + 2
            continue
        if c == '"':
            at += 1
            while text[at] != '"':
                at += 2 if text[at] == "\\" else 1
        elif c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            assert stack.pop() == c
        at += 1
    return at - 1


def measured_slots(text, rel, diagnostics):
    selected = []
    for d in diagnostics:
        if d.get("code", {}).get("code") != "clippy::result_large_err" or "closure" not in d["message"]:
            continue
        s = next(s for s in d["spans"] if s["is_primary"])
        if s["file_name"] != rel:
            continue
        begin, end = s["byte_start"], s["byte_end"]
        raw = text.encode()
        # Every selected source is ASCII before these spans. Still convert byte
        # locations explicitly rather than treating UTF-8 positions as characters.
        begin = len(raw[:begin].decode())
        end = len(raw[:end].decode())
        assert text[begin:begin + 2] == "||"
        expr = text[begin + 2:end].strip()
        matches = list(re.finditer(r"(?m)^([ \t]*)let \((\w+), (\w+)\) =\s*(measure(?:_extended)?\()", text[:begin]))
        m = matches[-1]
        assert "\n\n" not in text[m.end():begin]
        assert text[end:end + 2] == ");", repr(text[end:end + 20])
        indent, result, stats = m[1].split("\n")[-1], m[2], m[3]
        callee_prefix = text[m.start():begin]
        callee = callee_prefix[callee_prefix.index("measure"):]
        helper = next((n for n in ("construct", "pin", "construct_owned") if expr.startswith(n + "(") and closing(expr, len(n)) == len(expr) - 1), None)
        if helper:
            body = expr[:-1] + ", &mut " + result + ")"
        else:
            body = "{ " + result + " = Some(" + expr + "); }"
        old = text[m.start():end + 2]
        new = (indent + "let mut " + result + " = None;\n" + indent + "let ((), " + stats + ") = " + callee + "|| " + body + ");\n" + indent + "let " + result + " = " + result + ".unwrap();")
        selected.append((m.start(), old, new))
    for pos, old, new in sorted(selected, reverse=True):
        assert text[pos:pos + len(old)] == old
        EDITS.append({"path": rel, "reason": "result_large_err: measured closure writes complete result to caller-owned slot", "count": 1, "position": pos, "before": old, "after": new})
        text = text[:pos] + new + text[pos + len(old):]
    return text


def helper_calls(text, rel, names):
    """Adapt only free helper calls, never method calls or declarations."""
    changes = []
    for name, original_arity in names.items():
        for m in re.finditer(r"(?<![\w.:])" + name + r"\(", text):
            if re.search(r"fn\s+$", text[max(0, m.start() - 12):m.start()]):
                continue
            end = closing(text, m.end() - 1)
            old = text[m.start():end + 1]
            # Calls emitted for measured result slots already have their extra
            # explicit output argument and are not wrapped a second time.
            if re.search(r",\s*&mut\s+\w+\s*\)$", old):
                continue
            indent = re.match(r"\s*", text[text.rfind("\n", 0, m.start()) + 1:m.start()])[0]
            new = ("{\n" + indent + "    let mut returned = None;\n" + indent + "    " + old[:-1].rstrip().rstrip(",") + ", &mut returned);\n" + indent + "    returned.unwrap()\n" + indent + "}")
            changes.append((m.start(), old, new))
    for _, old, new in sorted(changes, reverse=True):
        # Many identical calls exist. Replace by exact character position so each
        # call remains bound to its source occurrence, not a global substitution.
        pos = _
        assert text[pos:pos + len(old)] == old
        EDITS.append({"path": rel, "reason": "result_large_err: mechanical output-slot helper call", "count": 1, "position": pos, "before": old, "after": new})
        text = text[:pos] + new + text[pos + len(old):]
    return text


def main():
    upstream = json.loads((ACTUAL / "source-manifest.json").read_text())
    assert len(upstream["baselineFiles"]) == len(upstream["candidateFiles"]) == 136
    assert upstream["baselineTreeSHA256"] == BASELINE_TREE
    canonical_paths = {n: ROOT / "vm" / n for n in upstream["baselineFiles"]}
    canonical = {n: row(p) for n, p in canonical_paths.items()}
    assert canonical == upstream["baselineFiles"]
    assert closure(canonical) == BASELINE_TREE
    prior_paths = {n: ROOT / p for n, p in upstream["materializationPaths"].items()}
    assert {n: row(p) for n, p in prior_paths.items()} == upstream["candidateFiles"]
    formatted_paths = dict(prior_paths)
    formatted_paths.update({n: FORMATTED / n for n in FORMATTED_PATHS})
    formatted = {n: row(p) for n, p in formatted_paths.items()}
    assert closure(formatted) == FORMATTED_TREE
    source = {n: p.read_text() for n, p in formatted_paths.items() if n.endswith(".rs")}
    original = dict(source)
    arms = {a: json.loads((ACTUAL / f"clippy-{a}.json").read_text()) for a in ("baseline", "candidate")}
    observed_paths = set()
    for arm in arms.values():
        assert arm["exit"] == 101 and not arm["lintPassed"]
        for d in arm["diagnostics"]:
            if d.get("level") == "error" and d.get("code"):
                observed_paths.update(s["file_name"] for s in d["spans"] if s["is_primary"])
    for rel in (REA + "cache_tests.rs", REA + "execution_tests.rs"):
        source[rel] = measured_slots(source[rel], rel, arms["candidate"]["diagnostics"])

    def sub(rel, old, new, reason, count=1):
        source[rel] = edit(source[rel], rel, old, new, reason, count)

    sub(REA + "cache_tests.rs", """    wasi: Option<&AccountedWasi>,
) -> Result<SwiftFunctionCache, SwiftRunFailure> {""", """    wasi: Option<&AccountedWasi>,
    outcome: &mut Option<Result<SwiftFunctionCache, SwiftRunFailure>>,
) {""", "result_large_err: constructor fills caller-owned result slot")
    sub(REA + "cache_tests.rs", """            phase.complete(returned)?;
            return result;""", """            *outcome = Some(match phase.complete(returned) {
                Ok(()) => result,
                Err(failure) => Err(failure),
            });
            return;""", "result_large_err: preserve completion error precedence and owner drop")
    sub(REA + "cache_tests.rs", """    control.drop_proof_with_wasi(adopted, wasi.map(AccountedWasi::usage))?;
    Err(failure)""", """    if let Err(cleanup_failure) = control.drop_proof_with_wasi(adopted, wasi.map(AccountedWasi::usage)) {
        *outcome = Some(Err(cleanup_failure));
        return;
    }
    *outcome = Some(Err(failure));""", "result_large_err: preserve rejected-proof cleanup and error precedence")
    sub(REA + "cache_tests.rs", """    wasi: Option<&AccountedWasi>,
) -> Result<SwiftFunctionPin, SwiftRunFailure> {
    let mut phase = cache.prepare_operation(control, wasi, cache_cursor())?;""", """    wasi: Option<&AccountedWasi>,
    outcome: &mut Option<Result<SwiftFunctionPin, SwiftRunFailure>>,
) {
    let mut phase = match cache.prepare_operation(control, wasi, cache_cursor()) {
        Ok(phase) => phase,
        Err(failure) => {
            *outcome = Some(Err(failure));
            return;
        }
    };""", "result_large_err: pin helper fills caller-owned result slot")
    sub(REA + "cache_tests.rs", """    phase.complete(returned)?;
    result
}
fn cleanup(""", """    *outcome = Some(match phase.complete(returned) {
        Ok(()) => result,
        Err(failure) => Err(failure),
    });
}
fn cleanup(""", "result_large_err: preserve pin completion error precedence")
    source[REA + "cache_tests.rs"] = helper_calls(source[REA + "cache_tests.rs"], REA + "cache_tests.rs", {"construct": 3, "pin": 4})

    sub(REA + "execution_tests.rs", """    pair: &mut Option<(RuntimeControl, AdoptedProof)>,
) -> Result<SwiftReactorInstance, ConstructionFailure> {
    SwiftReactorInstance::construct(""", """    pair: &mut Option<(RuntimeControl, AdoptedProof)>,
    outcome: &mut Option<Result<SwiftReactorInstance, ConstructionFailure>>,
) {
    *outcome = Some(SwiftReactorInstance::construct(""", "result_large_err: owned constructor fills caller-owned result slot")
    sub(REA + "execution_tests.rs", """        construction_cursor(),
    )
}
fn construct_failed""", """        construction_cursor(),
    ));
}
fn construct_failed""", "result_large_err: owned constructor slot closes without boxing")
    source[REA + "execution_tests.rs"] = helper_calls(source[REA + "execution_tests.rs"], REA + "execution_tests.rs", {"construct_owned": 1})
    source[DEPENDENCY] = helper_calls(source[DEPENDENCY], DEPENDENCY, {"construct_owned": 1})

    # Every remaining edit below corresponds to an actual observed diagnostic.
    sub(REA + "cache.rs", '.err()\n        .expect("malformed scan must fail")', '.expect_err("malformed scan must fail")', "err_expect: Counts implements Debug; identical success refusal and full scan error")
    sub(REA + "cache_tests.rs", "0x45..=0x5a|0x67..=0x8a|0xa7|0xac|0xad|0xc0..=0xc4|0x5b..=0x66|0x8b..=0xa6|0xa8..=0xab|0xae..=0xbf", "0x45..=0xc4", "manual_range_patterns: byte-for-byte opcode set equality", 2)
    sub(REA + "cache_tests.rs", "i.operation.clone()", "i.operation", "clone_on_copy: Operation derives Copy", 2)
    sub(REA + "cache_tests.rs", "x.operation.clone()", "x.operation", "clone_on_copy: Operation derives Copy")
    sub(REA + "cache_tests.rs", """    let phase = SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap();
    drop(phase);""", """    {
        let _phase = SwiftFunctionCache::prepare(&mut c, None, &a, cache_cursor()).unwrap();
    }""", "drop_non_drop: same borrow-ending scope; omitted completion keeps charge")
    sub(REA + "cache_tests.rs", """    let operation = cache
        .prepare_operation(&mut c, None, cache_cursor())
        .unwrap();
    drop(operation);""", """    {
        let _operation = cache
            .prepare_operation(&mut c, None, cache_cursor())
            .unwrap();
    }""", "drop_non_drop: same operation scope and retained construction charge")
    sub(REA + "execution_tests.rs", """    let original = control
        .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
        .unwrap();
    let foreign = other
        .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
        .unwrap();
    control.drop_proof(proof).unwrap();
    other.drop_proof(other_proof).unwrap();
    // Test-only intentional ownership loss. The original charge must remain;
    // no test can manufacture a matching replacement token or erase the ledger.
    drop(original);""", """    let foreign = {
        let _original = control
            .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
            .unwrap();
        let foreign = other
            .admit(SwiftReservationCategory::State, bytes, Cursor::adoption())
            .unwrap();
        control.drop_proof(proof).unwrap();
        other.drop_proof(other_proof).unwrap();
        // Test-only intentional ownership loss. The original charge must remain;
        // no test can manufacture a matching replacement token or erase the ledger.
        foreign
    };""", "drop_non_drop: original ticket ends at same effect boundary; original charge assertions retained")
    sub("src/experimental_wasi/accounted_tests.rs", """    let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
    let owner = phase
        .construct(grants(), small(), Instant::now(), cursor())
        .unwrap();
    drop(phase);""", """    let owner = {
        let mut phase = AccountedWasi::prepare(&mut control, cursor()).unwrap();
        phase
            .construct(grants(), small(), Instant::now(), cursor())
            .unwrap()
    };""", "drop_non_drop: end borrowed phase before cleanup without completing it")
    sub("src/experimental_wasi/accounted_tests.rs", "            let result = match point {", "            match point {", "let_and_return: return original match directly")
    sub("src/experimental_wasi/accounted_tests.rs", """                _ => unreachable!(),
            };
            result
        });""", """                _ => unreachable!(),
            }
        });""", "let_and_return: same match value and effect order")
    sub(REA + "control_operations_tests.rs", "drop(completed);", "let _ = completed;", "dropping_copy_types: Copy completion has no destructor", 2)
    sub(REA + "memory_operations_tests.rs", "case>=4&&case<=7", "(4..=7).contains(&case)", "manual_range_contains: inclusive integer set unchanged")
    sub(REA + "memory_operations_tests.rs", "}if cancel{hooks(Hooks{push_fault:6", "}\n if cancel{hooks(Hooks{push_fault:6", "possible_missing_else: separate independent if statements with newline")
    sub(REA + "bulk_memory_operations_tests.rs", "i.wrapping_mul(37)^i/251", "i.wrapping_mul(37)^(i/251)", "precedence: explicit grouping preserves division precedence")
    sub(REA + "bulk_memory_operations_tests.rs", "}if fault==8{p.phase.parts.memory.push(0);}", "}\nif fault==8{p.phase.parts.memory.push(0);}", "possible_missing_else: independent restoration branch")
    sub(REA + "bulk_memory_operations_tests.rs", "}if fault==5{assert_eq!(observed(p).instruction_fuel", "}\nif fault==5{assert_eq!(observed(p).instruction_fuel", "possible_missing_else: independent failure assertions")
    sub(REA + "bulk_memory_operations_tests.rs", "}if let Some(old)=old{p.phase.operation.control.test_replace_execution_work_limit(old);}", "}\nif let Some(old)=old{p.phase.operation.control.test_replace_execution_work_limit(old);}", "possible_missing_else: independent original-limit restoration")
    sub(REA + "memory_growth_operations_tests.rs", "allowed >= 1 + growthwork", "allowed > growthwork", "int_plus_one: finite source-derived growthwork is below u64::MAX")
    sub(REA + "diagnostic_profile_tests.rs", "bytes.chunks_exact(32)", "bytes.as_chunks::<32>().0.iter()", "chunks_exact_to_as_chunks: same nonoverlapping complete rows, remainder ignored")
    sub(REA + "diagnostic_profile_tests.rs", "absolute >= 34 && absolute < 164", "(34..164).contains(&absolute)", "manual_range_contains: same half-open row interval")
    sub(REA + "diagnostic_profile_tests.rs", "n >= 34 && n < 63", "(34..63).contains(&n)", "manual_range_contains: same half-open row interval")
    sub(REA + "diagnostic_result_v1_tests.rs", """    for i in 0..64 {
        if ![35, 38, 50].contains(&i) {
            assert_eq!(w[i], 100 + i as u64);""", """    for (i, word) in w.iter().enumerate() {
        if ![35, 38, 50].contains(&i) {
            assert_eq!(*word, 100 + i as u64);""", "needless_range_loop: enumerate same 64 words and original expected values")
    sub(REA + "diagnostic_result_v1_tests.rs", "    assert!(usize::BITS <= 64);", "    const { assert!(usize::BITS <= 64) };", "assertions_on_constants: preserve exact predicate as compile-time assertion")
    sub(REA + "lifecycle_tests.rs", """    assert!(super::PERMANENT_BYTES > 0);
    assert!(super::ACTIVE_BYTES > 0);""", """    const {
        assert!(super::PERMANENT_BYTES > 0);
        assert!(super::ACTIVE_BYTES > 0);
    }""", "assertions_on_constants: preserve exact formula predicates as compile-time assertions")
    for field, value in [("unknown_import", "true"), ("start_section", "true"), ("memory", "Some(vec![1, 1, 0, 0])"), ("memory", "Some(memory)")]:
        sub("tests/experimental_guest_ui_validation.rs", f"let mut p = Program::default();\n    {'    ' if value == 'Some(memory)' else ''}p.{field} = {value};", "let " + ("" if value == "Some(memory)" or field == "start_section" else "mut ") + "p = Program { " + field + ": " + value + ", ..Program::default() };", "field_reassign_with_default: same Program default and field override")
    sub("tests/experimental_guest_ui_allocations.rs", """    let mut p = fixture::Program::default();
    p.memory = Some(vec![1, 1, 32, 32]);""", """    let p = fixture::Program {
        memory: Some(vec![1, 1, 32, 32]),
        ..fixture::Program::default()
    };""", "field_reassign_with_default: preserve 32-page allocation fixture")
    sub("tests/experimental_guest_ui_validation.rs", "1usize as *const u8", "ptr::with_exposed_provenance::<u8>(1)", "manual_dangling_ptr: preserve exact address 1, u8 alignment and original cast provenance")

    changed = {n for n in source if source[n] != original[n]}
    assert changed <= observed_paths | {DEPENDENCY}
    overlays = sorted(changed | set(FORMATTED_PATHS))
    assert len(overlays) == 15
    files = dict(formatted)
    materialization = {n: "vm/" + n for n in files}
    for n in overlays:
        dest = HERE / "candidate/vm" / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(source[n])
        files[n] = row(dest)
        materialization[n] = str(dest.relative_to(ROOT))
    for name, bases in [("canonical-to-candidate.diff", canonical_paths), ("formatted-to-candidate.diff", formatted_paths)]:
        diff = "".join("".join(difflib.unified_diff(bases[n].read_text().splitlines(keepends=True), source[n].splitlines(keepends=True), fromfile=name.split("-to-")[0] + "/vm/" + n, tofile="candidate/vm/" + n)) for n in overlays)
        (HERE / name).write_text(diff)
    union = {}
    for arm, doc in arms.items():
        for index, d in enumerate(doc["diagnostics"]):
            if d.get("level") != "error" or not d.get("code"):
                continue
            spans = [s for s in d["spans"] if s["is_primary"]]
            key = (d["code"]["code"], tuple((s["file_name"], s["line_start"], s["column_start"]) for s in spans))
            # Byte/line changes from four-file rustfmt do not imply a new finding.
            # Persist both arm references; comparison.json is the authoritative
            # code/level/message/file multiset comparison.
            union.setdefault(str(key), {"code": d["code"]["code"], "message": d["message"], "paths": sorted({s["file_name"] for s in spans}), "references": []})["references"].append({"arm": arm, "diagnosticIndex": index, "primaryLocations": [{k: s[k] for k in ("file_name", "line_start", "line_end", "column_start", "column_end", "byte_start", "byte_end")} for s in spans]})
    actual_files = [ACTUAL / n for n in ("source-manifest.json", "clippy-baseline.json", "clippy-candidate.json", "comparison.json")]
    actual_files += [ROOT / "verification/clock-format-actual-results" / n for n in ("sanitized-result.json", "seal.json")]
    for arm in ("baseline", "candidate"):
        actual_files += sorted(p for p in (ACTUAL / "format" / arm).rglob("*") if p.is_file())
    bindings = {str(p.relative_to(ROOT)): row(p) for p in actual_files}
    save(HERE / "edit-log.json", {"schema": 1, "edits": EDITS})
    save(HERE / "actual-bindings.json", {"schema": 1, "runID": 40814738980, "rawFilesLocalOnly": True, "bindingsContainHashesAndPathsOnly": True, "files": bindings})
    save(HERE / "diagnostic-index.json", {"schema": 1, "scope": "actual baseline/candidate observations; fail-fast output is not exhaustive", "observationsByArm": {a: sum(d.get("level") == "error" and bool(d.get("code")) for d in doc["diagnostics"]) for a, doc in arms.items()}, "comparison": json.loads((ACTUAL / "comparison.json").read_text()), "paths": sorted(observed_paths), "index": list(union.values())})
    save(HERE / "manifest.json", {
        "schema": 1, "scope": "Source-only bitmap candidate with actual standard-format overlays and narrow observed Clippy corrections",
        "currentRevisionParentSupplied": REVISION, "baselineTreeSHA256": BASELINE_TREE,
        "priorCandidateTreeSHA256": upstream["candidateTreeSHA256"], "formattedCandidateTreeSHA256": FORMATTED_TREE,
        "candidateTreeSHA256": closure(files), "treeDigestFormat": "sha256(sorted(path + NUL + fileSHA256 + LF))",
        "baselineFiles": canonical, "priorFormattedFiles": formatted, "candidateFiles": files,
        "overlayPaths": overlays, "lintChangedPaths": sorted(changed), "materializationPaths": materialization,
        "observedDiagnosticPaths": sorted(observed_paths),
        "directCompatibilityDependency": {"path": DEPENDENCY, "reason": "sole imported construct_owned call must pass its caller-owned output slot", "rootAuthorized": True, "canonicalPreimage": canonical[DEPENDENCY]},
        "protectedFiles": upstream["protectedFiles"],
        "canonicalProductFilesEdited": False, "priorFrozenPacketsEdited": False, "hostHarnessChanged": False, "newDispatchSelected": False,
        "runtimeFormattingLintStatus": "pending fresh hosted execution; no local compiler or product runtime used",
    })
    summary = json.dumps({"pythonVersion": sys.version, "overlays": len(overlays), "edits": len(EDITS), "sourceMembers": len(files), "candidateTreeSHA256": closure(files), "runtime": "pending"})
    (HERE / "local").mkdir(exist_ok=True)
    (HERE / "local/prepare.stdout").write_text(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main()
