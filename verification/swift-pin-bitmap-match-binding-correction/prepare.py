#!/usr/bin/env python3
"""One bounded guarded source/data bootstrap; imports no subject implementation."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATTEMPTS = []

def deny(*args, **kwargs):
    ATTEMPTS.append("denied-live-api")
    raise AssertionError("match binding packet denies live process/session/group/signal/timer/wait/socket effects")

def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.", "ctypes.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.chdir",
    }:
        deny()
    if event == "open":
        name, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+")
        writing |= isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and (not isinstance(name, (str, bytes, os.PathLike)) or not Path(os.fsdecode(name)).resolve().is_relative_to(HERE)):
            deny()
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.chmod", "os.symlink", "os.link"}:
        targets = args[:2] if event in {"os.rename", "os.link"} else args[1:2] if event == "os.symlink" else args[:1]
        for target in targets:
            if not Path(os.fsdecode(target)).resolve().is_relative_to(HERE):
                deny()

sys.dont_write_bytecode = True
sys.addaudithook(audit)
# Only standard-library guard plumbing precedes attribute denial. No subject code
# is imported at any point. REPL infrastructure and its timers are never patched.
import signal
import socket
import subprocess
import threading
import _thread
import time
import resource
subprocess.Popen = subprocess.run = subprocess.call = subprocess.check_call = subprocess.check_output = deny
socket.socket = socket.create_connection = socket.socketpair = deny
for name in dir(os):
    if name.startswith(("exec", "spawn", "posix_spawn")) or name in {
        "system", "fork", "forkpty", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "waitid",
        "popen", "setsid", "setpgid", "getpgid", "getsid",
    }:
        setattr(os, name, deny)
for name in ("signal", "setitimer", "getitimer", "alarm", "getsignal", "raise_signal", "pthread_kill", "sigwait", "sigwaitinfo", "sigtimedwait", "pause", "pthread_sigmask", "sigpending"):
    if hasattr(signal, name):
        setattr(signal, name, deny)
resource.getrusage = deny
threading.Thread.start = threading.Timer.start = _thread.start_new_thread = time.sleep = deny
resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 * 1024, 4 * 1024 * 1024))

import collections
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone

PRIOR = ROOT / "verification/swift-pin-bitmap-lint-correction"
REVIEW = ROOT / "verification/swift-pin-bitmap-lint-actual-review"
ACTUAL = REVIEW / "local/extract/_temp/pin-bitmap-lint-regression-v1-evidence"
AFTER = ACTUAL / "format/candidate/after"
TARGET = "src/experimental_swift_reactor/cache_tests.rs"
BASELINE = "af0db424af7b08f013d2c6a8894f4d156f76bc5f493620c6f2c0b85d3bf4c48b"
ORIGINAL = "7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748"
FORMATTED = "1c24099923de0e10835957cb7a8cdc744750014aae360dac5ffe8dccb3f9b60a"
REVISION = "88c32d7fe9a5596d269ad29eb63c380dc5e820b4"
GIT_TREE = "6bca344641b9b4c9e928a460b801f8c93d2a90ad"
OLD = """        match {
            let mut returned = None;
            construct(&mut c, a, None, &mut returned);
            returned.unwrap()
        } {"""
NEW = """        let construction_result = {
            let mut returned = None;
            construct(&mut c, a, None, &mut returned);
            returned.unwrap()
        };
        match construction_result {"""
CHECKS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def row(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}

def read(p):
    if p.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("source/data file read cap")
    return p.read_bytes()

def file_row(p):
    return row(read(p))

def closure(rows):
    return sha("".join(n + "\0" + rows[n]["sha256"] + "\n" for n in sorted(rows)).encode())

def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + str(key))
        result[key] = value
    return result

def load(p):
    return json.loads(read(p), object_pairs_hook=unique, parse_constant=lambda s: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + s)))

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")

def check(name, condition, detail=None):
    record = {"name": name, "passed": bool(condition)}
    if detail is not None:
        record["detail"] = detail
    CHECKS.append(record)
    if not condition:
        raise AssertionError(name)

def safe_rel(name):
    p = Path(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and "\\" not in name and "\0" not in name

def inventory(text):
    # Lexical inventories are adjuncts to exact inverse-byte equality below;
    # they neither execute Rust nor authorize a release.
    return {
        "testMethods": re.findall(r"#\[test\]\s*(?:#\[[^\n]*\]\s*)*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?fn\s+([A-Za-z_]\w*)", text),
        "assertionLines": [line for line in text.splitlines() if re.search(r"\b(?:debug_)?assert(?:_eq|_ne)?!\s*[\(\{\[]", line)],
        "quotedLiterals": re.findall(r'"(?:\\.|[^"\\])*"', text),
        "numericLexemes": re.findall(r"(?<![\w])(?:0x[0-9A-Fa-f_]+|0b[01_]+|0o[0-7_]+|[0-9][0-9_]*(?:\.[0-9_]+)?)(?:[uif](?:8|16|32|64|128|size))?(?![\w])", text),
        "lintDirectives": re.findall(r"#\[(?:allow|expect|warn|deny|forbid)\([^\n]*", text),
    }

# Negative controls call only already-denied attributes; no real syscall occurs.
control_apis = [subprocess.Popen, subprocess.run, os.system, os.setsid, os.setpgid,
                os.getpgid, os.kill, os.waitpid, signal.signal, signal.setitimer,
                socket.socket, threading.Thread.start, threading.Timer.start, time.sleep]
for api in control_apis:
    check("guard installed on " + str(len(CHECKS) + 1), api is deny)
    try:
        api()
    except AssertionError as error:
        check("negative live-effect control " + str(len(CHECKS) + 1), "denies live" in str(error))
    else:
        raise AssertionError("live guard did not refuse")
control_attempts = len(ATTEMPTS)
check("all guarded negative controls refused", control_attempts == 14)
ATTEMPTS.clear()

prior = load(PRIOR / "manifest.json")
actual = load(ACTUAL / "source-manifest.json")
formatted = load(ACTUAL / "formatted-source-manifest.json")
review = load(REVIEW / "sanitized-result.json")
diagnostic = load(ACTUAL / "clippy-candidate.json")
seal = load(PRIOR / "seal.json")
check("prior manifest equals dispatched source manifest", prior == actual)
check("source roster has 136 distinct members", len(prior["baselineFiles"]) == len(prior["candidateFiles"]) == len(formatted["files"]) == 136 and set(prior["baselineFiles"]) == set(prior["candidateFiles"]) == set(formatted["files"]))
check("overlay roster is 15 distinct safe paths", len(prior["overlayPaths"]) == len(set(prior["overlayPaths"])) == 15 and all(safe_rel(n) for n in prior["overlayPaths"]))
check("all source member paths are safe", all(safe_rel(n) for n in prior["baselineFiles"]))
check("frozen prior candidate closure", closure(prior["candidateFiles"]) == prior["candidateTreeSHA256"] == ORIGINAL)
check("frozen baseline closure", closure(prior["baselineFiles"]) == prior["baselineTreeSHA256"] == BASELINE)
check("frozen actual formatted closure", closure(formatted["files"]) == formatted["treeSHA256"] == FORMATTED)
check("selected failure identity", review["run"]["id"] == 40822264739 and review["run"]["head"] == REVISION and review["run"]["attempt"] == 1)
check("selected failure remains a failure", review["decision"] == "failed-host-attempt-with-verified-Clippy-refusal" and review["failures"] == [] and review["commands"][-1]["exit"] == 101)
check("artifact ZIP binding", file_row(REVIEW / "local/artifact.zip") == {"bytes": 394698, "sha256": "c56be30a98b59e7b300ae981a04ebfe26f80806b0070a8ab47bb44691a3acf4a"})
check("one strict Clippy diagnostic among 39 records", len(diagnostic["diagnostics"]) == 1 and sum(diagnostic["recordReasons"].values()) == 39 and diagnostic["exit"] == 101 and diagnostic["buildFinished"] is False)
d = diagnostic["diagnostics"][0]
check("remaining diagnostic is observed block condition", d["code"]["code"] == "clippy::blocks_in_conditions" and d["spans"][0]["file_name"] == TARGET and d["spans"][0]["line_start"] == 1219 and d["spans"][0]["line_end"] == 1223)
suggestion = next(c for c in d["children"] if c["message"] == "try")["spans"][0]
check("observed suggestion binds the unchanged block", suggestion["suggestion_applicability"] == "MachineApplicable" and suggestion["suggested_replacement"] == NEW.strip().replace("construction_result", "res").replace(";\n        match res", "; match res").removesuffix(" {"))
check("prior packet seal matches supplied hash", sha((PRIOR / "seal.json").read_bytes()) == "89505e8f873e5c225d711f8ae923bd8149db30a74603c49dddb523639cb11052")
for name, expected in seal["files"].items():
    check("frozen prior packet " + name, file_row(PRIOR / name) == expected)

protected = {name: file_row(ROOT / name) for name in prior["protectedFiles"]}
check("protected source contracts unchanged", protected == prior["protectedFiles"])
canonical = {}
seed = {}
for name, expected in prior["baselineFiles"].items():
    raw = read(ROOT / "vm" / name)
    canonical[name] = row(raw)
    check("canonical source exact " + name, canonical[name] == expected)
    original_raw = read(ROOT / prior["materializationPaths"][name])
    check("prior source exact " + name, row(original_raw) == prior["candidateFiles"][name])
    seed_raw = read(AFTER / name) if name in prior["overlayPaths"] else raw
    check("actual formatted source exact " + name, row(seed_raw) == formatted["files"][name])
    seed[name] = seed_raw
check("canonical closure remains exact", closure(canonical) == BASELINE)
check("complete actual formatted seed closure", closure({n: row(raw) for n, raw in seed.items()}) == FORMATTED)
seed_text = seed[TARGET].decode()
check("one exact observed preimage", seed_text.count(OLD) == 1)
check("local binding introduces no collision", "construction_result" not in seed_text)
changed_text = seed_text.replace(OLD, NEW)
check("exact inverse restores all original bytes", changed_text.count(NEW) == 1 and changed_text.replace(NEW, OLD).encode() == seed[TARGET])
check("block body evaluation stays byte exact", OLD.split("{", 1)[1].rsplit("}", 1)[0] == NEW.split("{", 1)[1].split("};", 1)[0])
check("no constructor slot/error/assertion/ownership/counter/limit text changed", changed_text.replace(NEW, OLD) == seed_text)
check("all lexical test/assertion/literal/numeric/lint inventories unchanged", inventory(seed_text) == inventory(changed_text))

candidate_files = dict(formatted["files"])
materialization = {}
overlay_rows = {}
for name in sorted(seed):
    if name in prior["overlayPaths"]:
        destination = HERE / "candidate/vm" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(changed_text.encode() if name == TARGET else seed[name])
        raw = destination.read_bytes()
        candidate_files[name] = row(raw)
        overlay_rows[name] = row(raw)
        materialization[name] = str(destination.relative_to(ROOT))
        check("overlay exact " + name, raw == (changed_text.encode() if name == TARGET else seed[name]))
    else:
        materialization[name] = "vm/" + name
        check("nonoverlay uses canonical source " + name, candidate_files[name] == canonical[name])
changed = [n for n in sorted(candidate_files) if candidate_files[n] != formatted["files"][n]]
check("only cache_tests changed against actual formatted closure", changed == [TARGET])
check("fourteen actual formatted overlays retained byte exactly", sum(candidate_files[n] == formatted["files"][n] for n in prior["overlayPaths"]) == 14)
check("materialization interface complete", len(materialization) == len(candidate_files) == 136 and set(materialization) == set(candidate_files))
check("materialized candidate roster closure exact", closure({n: file_row(ROOT / p) for n, p in materialization.items()}) == closure(candidate_files))

def validate_rows(rows, mat):
    return len(rows) == len(mat) == 136 and set(rows) == set(mat) == set(canonical) and closure(rows) == closure(candidate_files) and all(safe_rel(p) for p in mat.values())

bad_rows = dict(candidate_files)
bad_rows[TARGET] = {"bytes": candidate_files[TARGET]["bytes"], "sha256": "0" * 64}
check("mutation control rejects changed candidate digest", not validate_rows(bad_rows, materialization))
check("mutation control rejects missing source member", not validate_rows({n:r for n,r in candidate_files.items() if n != TARGET}, materialization))
check("mutation control rejects unsafe materialization", not validate_rows(candidate_files, {**materialization, TARGET: "../forbidden"}))

candidate_tree = closure(candidate_files)
manifest = {
    "schema": 1,
    "scope": "Source-only match-block binding correction seeded from actual formatted attempt 40822264739-1",
    "currentRevisionParentSupplied": REVISION,
    "currentGitTreeParentSupplied": GIT_TREE,
    "baselineTreeSHA256": BASELINE,
    "priorCandidateTreeSHA256": ORIGINAL,
    "formattedCandidateTreeSHA256": FORMATTED,
    "candidateTreeSHA256": candidate_tree,
    "treeDigestFormat": "sha256(sorted(path + NUL + fileSHA256 + LF))",
    "baselineFiles": canonical,
    "priorFormattedFiles": formatted["files"],
    "candidateFiles": candidate_files,
    "overlayPaths": prior["overlayPaths"],
    "lintChangedPaths": [TARGET],
    "materializationPaths": materialization,
    "observedDiagnosticPaths": [TARGET],
    "directCompatibilityDependency": prior["directCompatibilityDependency"],
    "protectedFiles": protected,
    "canonicalProductFilesEdited": False,
    "priorFrozenPacketsEdited": False,
    "hostHarnessChanged": False,
    "newDispatchSelected": False,
    "runtimeFormattingLintStatus": "New formatting, strict Clippy, Debug and Release remain pending; failed attempt 40822264739-1 is immutable",
}
save("manifest.json", manifest)
diff = "".join(difflib.unified_diff(seed_text.splitlines(True), changed_text.splitlines(True), fromfile="actual-formatted/" + TARGET, tofile="candidate/" + TARGET))
(HERE / "formatted-to-candidate.diff").write_text(diff)
check("narrow diff has exactly one hunk", sum(line.startswith("@@") for line in diff.splitlines()) == 1)
check("narrow diff has expected removed and added lines", [s for s in diff.splitlines() if s.startswith("-") and not s.startswith("---")] == ["-        match {", "-        } {"] and [s for s in diff.splitlines() if s.startswith("+") and not s.startswith("+++")] == ["+        let construction_result = {", "+        };", "+        match construction_result {"])

input_paths = {
    "priorManifest": PRIOR / "manifest.json", "priorSeal": PRIOR / "seal.json",
    "actualSanitizedReview": REVIEW / "sanitized-result.json", "artifactZIP": REVIEW / "local/artifact.zip",
    "actualSourceManifest": ACTUAL / "source-manifest.json", "actualFormattedManifest": ACTUAL / "formatted-source-manifest.json",
    "actualClippyDiagnostic": ACTUAL / "clippy-candidate.json",
}
binding = {
    "schema": 1, "headParentSupplied": REVISION, "gitTreeParentSupplied": GIT_TREE,
    "baselineTreeSHA256": BASELINE, "priorCandidateTreeSHA256": ORIGINAL,
    "actualFormattedTreeSHA256": FORMATTED, "candidateTreeSHA256": candidate_tree,
    "inputBindings": {label: {"path": str(p.relative_to(ROOT)), **file_row(p)} for label, p in input_paths.items()},
    "rawEvidenceCopied": False, "run": {"id": 40822264739, "attempt": 1, "conclusion": "failure", "clippyExit": 101, "clippySeconds": 8.642611, "recordCount": 39, "diagnosticCount": 1, "artifactID": 12874169678},
    "diagnostic": {"code": d["code"]["code"], "path": TARGET, "lineStart": 1219, "lineEnd": 1223, "suggestionApplicability": suggestion["suggestion_applicability"]},
    "correction": {"old": OLD, "new": NEW, "preimage": row(seed[TARGET]), "result": candidate_files[TARGET], "byteDelta": len(changed_text.encode()) - len(seed[TARGET]), "unchangedOverlayCount": 14},
    "manualAllowance": "Prior sole manual allowance spent by immutable failed run; this packet selects no further attempt",
}
save("actual-bindings.json", binding)

# Recheck all inputs and protected sources after writes. Earlier failures and holds
# are immutable; no probe is made against them.
check("protected files still exact after materialization", {n: file_row(ROOT / n) for n in protected} == protected)
check("canonical sources still exact after materialization", {n: file_row(ROOT / "vm" / n) for n in canonical} == canonical)
check("no unexpected live-effect API attempts", ATTEMPTS == [])
all_inventory = collections.Counter()
for name in prior["overlayPaths"]:
    old_inv = inventory(seed[name].decode())
    new_inv = inventory((ROOT / materialization[name]).read_text())
    check("overlay inventory exact " + name, old_inv == new_inv)
    all_inventory.update({key: len(value) for key, value in old_inv.items()})
result = {
    "schema": 1, "status": "passed-source-data-only", "checkCount": len(CHECKS), "failures": [], "checks": CHECKS,
    "candidateTreeSHA256": candidate_tree, "sourceMembers": 136, "overlays": 15,
    "changedFromActualFormatted": changed, "unchangedActualFormattedOverlays": 14,
    "lexicalOverlayInventoryCounts": dict(all_inventory),
    "inventoryScope": "Supplementary lexical checks plus exact inverse-byte proof, not a Rust parser or executable test result",
    "guard": {"installedBeforeSubjectImports": True, "subjectImports": 0, "negativeControlsRefused": control_attempts, "unexpectedAttempts": ATTEMPTS, "realNestedProcessSessionGroupSignalTimerWaitSocketCalls": 0},
    "resourceBounds": {"cpuSeconds": 20, "fileWriteBytes": 4194304, "individualReadBytes": 33554432, "sourceMembers": 136, "overlays": 15, "addressSpaceSetter": "macOS unsupported; preparation-history.json retains first failure"},
    "commands": [{"command": "python3 -B verification/swift-pin-bitmap-match-binding-correction/prepare.py", "pythonVersion": sys.version, "exit": 0}],
    "runtimeChecks": {"formatting": "pending", "strictClippy": "pending", "Debug": "pending", "Release": "pending"},
}
save("pure-result.json", result)
receipt = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
    "decision": "Narrow source correction prepared and guarded; independent review and fresh hosted formatting/Clippy/Debug/Release pending",
    "ownership": "verification/swift-pin-bitmap-match-binding-correction/ only",
    "sourceRevisionParentSupplied": REVISION, "sourceGitTreeParentSupplied": GIT_TREE,
    "baselineTreeSHA256": BASELINE, "actualFormattedTreeSHA256": FORMATTED, "candidateTreeSHA256": candidate_tree,
    "manifest": "manifest.json", "bindings": "actual-bindings.json", "narrowDiff": "formatted-to-candidate.diff", "checks": "pure-result.json",
    "guardedSourceDataChecks": len(CHECKS), "failures": 0, "sourceMembers": 136, "overlays": 15,
    "changedOverlay": TARGET, "other14OverlaysRetainedExactly": True,
    "blockBodyAndOtherSourceBytesRetainedExactly": True,
    "canonicalProductFilesEdited": False, "priorFrozenPacketsEdited": False, "workflowHarnessFlagsLimitsEdited": False,
    "newDispatchSelected": False, "soleManualAllowanceSpentByPriorFailedRun": True,
    "localCompilerRustSwiftElixirProductNodeOracleRuntimeRuns": 0, "GitGhActions": 0,
    "nativeUICapturePhoneRuns": 0, "processInventoryOrHeldProbes": 0, "extraAgents": 0,
    "localHoldsPreservedWithoutProbes": [20745, 20770, 20780, 20817, 20842, 20851, 20866],
    "remoteFieldLogHoldPreservedWithoutProbes": {"runID": 40802230894, "PGID": 2424, "PID": 2621},
    "ownedInstancesStarted": 0, "rawCIArtifactsRemainOnlyInActualReviewLocal": True,
    "publicSignedOTAFieldLogGAQualified": False,
    "cleanup": "No owned subject child/session/socket/native/capture instance started; source/data packet only",
    "pending": ["Independent source review", "Fresh hosted formatting and strict all-target Clippy", "Full Debug and Release regression with nine Node oracles", "Canonical integration", "Native, physical-device, immutable published-package FieldLog, store/customer and GA acceptance"],
}
save("receipt.json", receipt)
files = {str(p.relative_to(HERE)): file_row(p) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json" and "local" not in p.relative_to(HERE).parts}
save("seal.json", {"schema": 1, "scope": "Frozen source-only actual-format match-binding correction; remote execution unselected", "candidateTreeSHA256": candidate_tree, "files": files, "treeSHA256": closure(files), "rawLogsLocalOnly": True})
print(json.dumps({"decision": receipt["decision"], "candidateTreeSHA256": candidate_tree, "checks": len(CHECKS), "changedFromActualFormatted": changed, "sealSHA256": sha((HERE / "seal.json").read_bytes()), "packetFiles": len(files) + 1}, indent=2))
