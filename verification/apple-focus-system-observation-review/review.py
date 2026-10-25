#!/usr/bin/env python3
"""Independent finite source/host review. No native, Git, or network work."""
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from decimal import Decimal as D

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/apple-focus-system-observation"
EXPECTED_HANDOFF = "5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427"
EXPECTED_ARCHIVE = "d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda"
SHA = lambda b: hashlib.sha256(b).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def write(name, value):
    (HERE / name).write_bytes(stable(value))


checks = []
findings = []
commands = []


def check(name, ok, detail=None):
    item = {"name": name, "passed": ok is True}
    if detail is not None:
        item["detail"] = detail
    checks.append(item)
    if ok is not True:
        raise AssertionError(name)


def run(name, argv, env=None, timeout=55):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    begin = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run(argv, cwd=HERE, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
        out, err, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        out, err, code = exc.stdout or b"", exc.stderr or b"", None
        timed_out = True
    (HERE / (name + ".stdout")).write_bytes(out)
    (HERE / (name + ".stderr")).write_bytes(err)
    commands.append({"name": name, "argv": argv, "cwd": str(HERE),
                     "startedUTC": started, "elapsedSeconds": time.monotonic() - begin,
                     "exitCode": code, "timedOut": timed_out, "timeoutSeconds": timeout,
                     "stdoutSHA256": SHA(out), "stderrSHA256": SHA(err),
                     "explicitEnvironment": {k: env[k] for k in (
                         "PYTHONDONTWRITEBYTECODE", "DEVELOPER_DIR", "LC_ALL", "TMPDIR",
                         "CLANG_MODULE_CACHE_PATH", "SWIFT_MODULECACHE_PATH") if env and k in env}})
    write("commands.json", commands)
    check(name + " exit", code == 0 and not timed_out)


def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_review():
    raw = (PRODUCER / "handoff.json").read_bytes()
    check("selected producer handoff", SHA(raw) == EXPECTED_HANDOFF)
    handoff = json.loads(raw)
    check("177 exact producer bindings", len(handoff["members"]) == 177)
    for name, record in handoff["members"].items():
        path = ROOT / name
        check("sealed member " + name,
              path.is_file() and not path.is_symlink()
              and stat.S_IMODE(path.stat().st_mode) == record["mode"] == 0o444
              and len(path.read_bytes()) == record["bytes"]
              and SHA(path.read_bytes()) == record["sha256"])
    manifest = json.loads((PRODUCER / "review-source-package-manifest.json").read_bytes())
    archive_path = PRODUCER / "review-source-package.tar.gz"
    check("selected candidate archive", SHA(archive_path.read_bytes()) == EXPECTED_ARCHIVE)
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        check("40 unique closed regular archive members", len(members) == len(set(names)) == 40
              and all(member.isfile() and member.mode == 0o444
                      and not pathlib.PurePosixPath(member.name).is_absolute()
                      and ".." not in pathlib.PurePosixPath(member.name).parts for member in members)
              and set(names) == set(manifest["members"]))
        for member in members:
            data = archive.extractfile(member).read()
            record = manifest["members"][member.name]
            check("archive bytes " + member.name,
                  SHA(data) == record["sha256"] and len(data) == record["bytes"]
                  and data == (PRODUCER / "candidate" / member.name).read_bytes())
    old = PRODUCER / "inputs/accepted"
    new = PRODUCER / "candidate/accepted"
    base = {str(p.relative_to(old)): p.read_bytes() for p in old.rglob("*") if p.is_file()}
    candidate = {str(p.relative_to(new)): p.read_bytes() for p in new.rglob("*") if p.is_file()}
    changed = [name for name in sorted(base) if base[name] != candidate[name]]
    check("same exact 40-member source closure", len(base) == 40 and set(base) == set(candidate))
    check("only selected two source files changed", changed == [
        "source/Prototype/DiagnosticTrace.swift", "source/Prototype/main.swift"])
    write("source-closure.json", {"schema": 1, "archiveSHA256": EXPECTED_ARCHIVE,
          "producerHandoffSHA256": EXPECTED_HANDOFF, "members": {
              name: {"bytes": len(data), "sha256": SHA(data), "changed": name in changed}
              for name, data in sorted(candidate.items())}, "changedMembers": changed,
          "unchangedMembers": 38,
          "revisionLabelFromFrozenInput": json.loads((PRODUCER / "receipt.json").read_bytes())["sourceRevisionLabelFromAcceptedFrozenReview"]})
    # Exact inverse edits, separate from the producer's validator.
    main = candidate["source/Prototype/main.swift"].decode()
    weak = """        DiagnosticTrace.shared.focusSystemObserver = { [weak self] site, sequence in
            guard let self else { return }
            FocusSystemObservation.shared.capture(site: site, contextSequence: sequence, stage: self.stage, controller: self,
                                                  controls: [self.toggle, self.referenceButton, self.nextButton])
        }
"""
    check("single installed weak closure", main.count(weak) == 1)
    restored = main.replace(weak, "").replace(
        '        DiagnosticTrace.shared.focusSystemObserver?("snapshot", nil)\n        return [', '        [').replace(
        ', "focusSystemDiagnostic": FocusSystemObservation.shared.value', '')
    check("exact original controller after inverse additions", restored.encode() == base["source/Prototype/main.swift"])
    trace = candidate["source/Prototype/DiagnosticTrace.swift"].decode()
    original_trace, helper = trace.split("\n/// Private, bounded, read-only supplemental observation. Never an oracle input.\n", 1)
    original_trace = original_trace.replace('    var focusSystemObserver: ((String, Int?) -> Void)?\n', '').replace(
        '        focusSystemObserver?(source + "-callback", focusContextRevision)\n', '')
    check("exact original strict trace and context append", original_trace.encode() == base["source/Prototype/DiagnosticTrace.swift"])
    check("read-only focus system selection and pointer identities",
          'let environment: any UIFocusEnvironment = window ?? controller' in helper
          and 'let system = UIFocusSystem.focusSystem(for: environment)' in helper
          and '(item as AnyObject) === $0' in helper and 'if let scene = window?.windowScene' in helper)
    headers = json.loads((PRODUCER / "platform-api-bindings.json").read_bytes())["headers"]
    sdk_bindings = {}
    for name, record in headers.items():
        data = pathlib.Path(name).read_bytes()
        check("pinned SDK header " + pathlib.Path(name).name,
              SHA(data) == record["sha256"] and len(data) == record["bytes"])
        sdk_bindings[name] = {"bytes": len(data), "sha256": SHA(data)}
    swift_interface = pathlib.Path("/Applications/Xcode_26.6.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/System/Library/Frameworks/UIKit.framework/Modules/UIKit.swiftmodule/arm64-apple-ios-simulator.swiftinterface")
    if swift_interface.exists():
        data = swift_interface.read_bytes()
        sdk_bindings[str(swift_interface)] = {"bytes": len(data), "sha256": SHA(data)}
        write("sdk-interface-selection.json", {"lines": [line for line in data.decode().splitlines()
              if "focusSystem(for" in line or "class UIFocusSystem" in line]})
    write("sdk-bindings.json", sdk_bindings)


def make_row(o, sequence, start, source="snapshot", context=None, item="null", system="present"):
    ids = ["ObjectIdentifier(0x100)", "ObjectIdentifier(0x200)", "ObjectIdentifier(0x300)"]
    identity = {"authored": ids[0], "reference": ids[1], "next": ids[2],
                "other": "ObjectIdentifier(0x400)", "null": None}[item]
    matches = [identity == value for value in ids] if system == "present" else [False] * 3
    item_state = ("fixed" if any(matches) else "null" if identity is None else "other") if system == "present" else "unavailable"
    controls = [{"slot": slot, "identity": identity, "isFocused": False,
                 "attachedToWindow": True, "windowIdentity": "ObjectIdentifier(0x500)",
                 "canBecomeFocused": True, "focusGroupIdentifier": None, "focusGroupPriority": 0}
                for slot, identity in zip(o.SLOTS, ids)]
    return {"sequence": sequence, "startedUptime": start, "finishedUptime": start + D(".000001"),
            "site": source, "contextSequence": context, "stage": "reset",
            "environment": {"selection": "window", "identity": "ObjectIdentifier(0x500)", "windowIdentity": "ObjectIdentifier(0x500)"},
            "system": {"state": system, "identity": "ObjectIdentifier(0x600)" if system == "present" else None,
                       "item": {"state": item_state, "identity": identity if system == "present" else None, "fixedMatches": matches}},
            "controls": controls, "scene": {"state": "absent", "identity": None, "systemIdentity": None, "itemIdentity": None}}


def diagnostic(o, rows):
    return {"schema": o.SCHEMA, "authoritative": False, "atomic": False,
            "entries": rows, "dropped": 0, "revision": len(rows), "captureStatus": "complete"}


def fixture(o):
    path = PRODUCER / "inputs/v7"
    before_packet = o.loads((path / "0001-before-1.json").read_bytes())
    after_packet = o.loads((path / "0001-after-1.json").read_bytes())
    witness_packet = o.loads((path / "0001-keyboard-witness-1.json").read_bytes())
    before, after = before_packet["observation"], after_packet["observation"]
    witness, binding = witness_packet["witness"], witness_packet["binding"]
    rows = [make_row(o, 1, before["focusContexts"][0]["uptime"] + D(".00001"), "controller-callback", 1),
            make_row(o, 2, binding["baselineUptime"] - D(".01"))]
    before["focusSystemDiagnostic"] = diagnostic(o, copy.deepcopy(rows))
    for context in after["focusContexts"][1:]:
        rows.append(make_row(o, len(rows) + 1, context["uptime"] + D(".00001"), "controller-callback", context["sequence"]))
    rows.append(make_row(o, len(rows) + 1, witness["after"]["uptime"] + D(".001")))
    after["focusSystemDiagnostic"] = diagnostic(o, rows)
    expected = {key: binding[key] for key in ("case", "generation", "actionIndex")}
    return before, after, witness, binding, expected, after_packet["verdict"]


def host_review():
    o = imported("independent_focus_observation", PRODUCER / "observation.py")
    controls = []

    def accepted(name, values):
        originals = [o.encoded(value) for value in values]
        result = o.join(*values)
        ok = result["supplemental"]["captureStatus"] == "complete" and result["supplemental"]["nativePass"] is False
        check(name, ok, result["supplemental"])
        check(name + " preserves all inputs", originals == [o.encoded(value) for value in values])
        controls.append({"name": name, "expected": "complete", "result": result["supplemental"]})
        return result

    def rejected(name, mutation):
        values = fixture(o)
        mutation(*values)
        original = o.encoded(values[-1])
        result = o.join(*values)
        check(name, result["supplemental"]["captureStatus"].startswith("incomplete-")
              and result["supplemental"]["nativePass"] is False
              and result["originalVerdict"] is values[-1] and o.encoded(values[-1]) == original,
              result["supplemental"])
        controls.append({"name": name, "expected": "incomplete", "result": result["supplemental"]})

    accepted("independent exact frozen join with synthetic diagnostic", fixture(o))
    for item in ("authored", "reference", "next", "other", "null"):
        value = diagnostic(o, [make_row(o, 1, D(1), item=item)])
        check("item identity state " + item, o.validate(value, []) is value)
    value = diagnostic(o, [make_row(o, 1, D(1), system="unavailable")])
    check("nil focus system distinguished", o.validate(value, []) is value)
    for scene in ("absent", "unavailable", "present"):
        row = make_row(o, 1, D(1), system="unavailable")
        row["environment"] = {"selection": "controller", "identity": "ObjectIdentifier(0x700)", "windowIdentity": None}
        row["scene"] = {"state": scene, "identity": None if scene == "absent" else "ObjectIdentifier(0x800)",
                        "systemIdentity": "ObjectIdentifier(0x900)" if scene == "present" else None, "itemIdentity": None}
        for control in row["controls"]:
            control.update(attachedToWindow=False, windowIdentity=None)
        value = diagnostic(o, [row])
        check("windowless nullable scene " + scene, o.validate(value, []) is value)
    rejected("wrong exact action", lambda b, a, w, binding, e, v: binding.update(actionIndex=2))
    rejected("wrong generation type", lambda b, a, w, binding, e, v: binding.update(generation=True))
    rejected("revision above saturation", lambda b, a, *rest: a["focusSystemDiagnostic"].update(revision=o.LIMIT + 1))
    rejected("revision not equal retained complete entries", lambda b, a, *rest: a["focusSystemDiagnostic"].update(revision=5))
    rejected("callback duplicate revision", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][2].update(contextSequence=1))
    rejected("reversed capture interval", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][-1].update(finishedUptime=D(0)))
    rejected("nonfinite capture interval", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][-1].update(finishedUptime=D("NaN")))
    rejected("overflow incomplete cannot complete", lambda b, a, *rest: a["focusSystemDiagnostic"].update(captureStatus="incomplete-counter", dropped=o.LIMIT, revision=o.LIMIT))
    rejected("before after prefix substitution", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][0]["controls"][0].update(isFocused=True))
    rejected("late observation past evaluation boundary", lambda b, a, w, binding, *rest: a["focusSystemDiagnostic"]["entries"][-1].update(finishedUptime=binding["evaluatedUptime"] + D(".001")))
    rejected("UTF8 group size bound", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][-1]["controls"][0].update(focusGroupIdentifier="é" * 65))
    rejected("oversized entry", lambda b, a, *rest: a["focusSystemDiagnostic"]["entries"][-1].update(stage="x" * 4097))
    rejected("129 entries cannot complete", lambda b, a, *rest: a["focusSystemDiagnostic"].update(entries=a["focusSystemDiagnostic"]["entries"] * 22))
    buffer = o.Buffer()
    for sequence in range(1, 129):
        buffer.append(make_row(o, sequence, D(sequence)))
    kept = copy.deepcopy(buffer.entries)
    check("whole object cap including reserved envelope", buffer.status == "incomplete-total-size"
          and len(o.encoded(buffer.value())) <= 65536 and len(kept) < 128,
          {"entries": len(kept), "bytes": len(o.encoded(buffer.value())), "status": buffer.status})
    buffer.append(make_row(o, 129, D(129)))
    check("failed capture never replaces retained prefix", buffer.entries == kept)
    buffer = o.Buffer()
    buffer.revision = buffer.dropped = o.LIMIT
    buffer.append({})
    check("both counters saturate", buffer.revision == buffer.dropped == o.LIMIT and buffer.status == "incomplete-counter")
    parsed = o.loads('{"a":948790.00000000000000001,"b":948790.00000000000000002}')
    check("Decimal order preserved beyond float precision", parsed["a"] < parsed["b"] and float(parsed["a"]) == float(parsed["b"]))

    # Finding controls intentionally assert the observed failure of the contract.
    values = fixture(o)
    frozen_witness = o.encoded(values[2])
    values[2]["after"]["elements"]["authored-toggle"]["hasFocus"] = True
    result = o.join(*values)
    check("reproduce substituted AX endpoint marked complete", result["supplemental"]["captureStatus"] == "complete"
          and o.encoded(values[2]) != frozen_witness
          and values[2] != values[-1]["keyboardWitness"] and result["supplemental"]["nativePass"] is False)
    write("finding-1-ax-substitution.json", o.loads(o.encoded({
        "scope": "synthetic diagnostic joined to frozen V7 input; no runtime evidence",
        "mutation": {"path": "witness.after.elements.authored-toggle.hasFocus", "before": False, "after": True},
        "expected": "incomplete due to exact original witness/AX binding mismatch",
        "observed": result["supplemental"], "originalVerdictPassed": result["originalVerdict"]["passed"],
        "witnessMatchesOriginalVerdictWitness": values[2] == values[-1]["keyboardWitness"]})))
    findings.append({"id": "F1", "priority": "P2", "title": "Supplied witness/AX endpoints are not bound to the trusted original",
                     "source": "verification/apple-focus-system-observation/observation.py:125",
                     "reproduction": "finding-1-ax-substitution.json", "status": "open"})
    values = fixture(o)
    rows = values[1]["focusSystemDiagnostic"]["entries"]
    original_refs = [row["contextSequence"] for row in rows if row["site"] != "snapshot"]
    rows[2]["contextSequence"], rows[3]["contextSequence"] = rows[3]["contextSequence"], rows[2]["contextSequence"]
    # Later finite ordered times cannot repair the impossible append revision order.
    for index, row in enumerate(rows[2:], 2):
        row["startedUptime"] = D("948791") + D(index) / D(100)
        row["finishedUptime"] = row["startedUptime"] + D(".000001")
    result = o.join(*values)
    actual_refs = [row["contextSequence"] for row in rows if row["site"] != "snapshot"]
    check("reproduce reordered callback revisions marked complete", actual_refs == [1, 3, 2, 4]
          and result["supplemental"]["captureStatus"] == "complete"
          and result["supplemental"]["nativePass"] is False)
    (HERE / "finding-2-context-order.json").write_bytes(o.encoded({
        "scope": "synthetic finite callback records; no runtime evidence", "originalCallbackOrder": original_refs,
        "mutatedCallbackOrder": actual_refs, "expected": "incomplete due to callback revision order",
        "observed": result["supplemental"], "mutatedRows": rows[2:]}) + b"\n")
    findings.append({"id": "F2", "priority": "P2", "title": "Callback revision coverage is checked as a set, allowing impossible revision order",
                     "source": "verification/apple-focus-system-observation/observation.py:102",
                     "reproduction": "finding-2-context-order.json", "status": "open"})

    # Exact frozen oracle replay and refusal to turn diagnostic enrichment into a pass.
    oracle = imported("independent_frozen_keyboard_oracle", PRODUCER / "inputs/oracle/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py")
    path = PRODUCER / "inputs/v7"
    b = json.loads((path / "0001-before-1.json").read_bytes())
    a = json.loads((path / "0001-after-1.json").read_bytes())
    w = json.loads((path / "0001-keyboard-witness-1.json").read_bytes())
    before = copy.deepcopy(b["observation"])
    before.update(keyboardWitness=w["witness"], keyboardBinding=w["binding"])
    original = oracle.verdict("diagnostic", w["binding"]["case"], "native-keyboard", before, a["observation"], b["signature"] != a["signature"])
    check("unchanged original oracle exactly replayed", all(original[k] == a["verdict"][k] for k in original))
    check("only original native traversal predicate fails", original["passed"] is False
          and [k for k, v in original["predicates"].items() if not v] == ["actualNativeFocusTraversal"])
    synthetic = fixture(o)
    before["focusSystemDiagnostic"] = json.loads(o.encoded(synthetic[0]["focusSystemDiagnostic"]))
    after = copy.deepcopy(a["observation"])
    after["focusSystemDiagnostic"] = json.loads(o.encoded(synthetic[1]["focusSystemDiagnostic"]))
    check("supplemental enrichment cannot change original oracle", oracle.verdict("diagnostic", w["binding"]["case"], "native-keyboard", before, after, True) == original)
    synthetic[-1]["passed"] = True
    check("claimed pass still cannot grant adapter native pass", o.join(*synthetic)["supplemental"]["nativePass"] is False)
    write("host-controls.json", {"schema": 1, "finiteControls": controls, "findings": findings,
          "originalOracle": original, "nativeAccepted": False})


def typecheck():
    scratch = HERE / ".owned-typecheck"
    check("fresh owned compiler scratch absent", not scratch.exists())
    scratch.mkdir()
    (scratch / "tmp").mkdir()
    (scratch / "cache").mkdir()
    env = os.environ.copy()
    env.update({"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer", "LC_ALL": "C",
                "TMPDIR": str(scratch / "tmp") + "/", "CLANG_MODULE_CACHE_PATH": str(scratch / "cache"),
                "SWIFT_MODULECACHE_PATH": str(scratch / "cache"), "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        for command in json.loads((PRODUCER / "typecheck-attempt-3/commands.json").read_bytes()):
            # Exact producer source closure and flags; only owned compiler scratch changes.
            argv = [arg.replace(str(PRODUCER / ".owned-typecheck"), str(scratch)) for arg in command["argv"]]
            run("independent-" + command["name"], argv, env)
    finally:
        shutil.rmtree(scratch)
        write("cleanup.json", {"schema": 1, "ownedCompilerScratchRemoved": not scratch.exists(),
              "ownedPythonCachesAbsent": not list(HERE.rglob("__pycache__")), "nativeInstancesCreated": 0,
              "nativeQueries": 0, "nativeAttempts": 0, "otherProjectProcessesOrDataTouched": False,
              "scope": "Owned compiler temporary modules/cache/tmp only; no native inventory or instance cleanup claim"})


def main():
    source_review()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run("python-version", [sys.executable, "--version"], env)
    run("producer-seal-verification", [sys.executable, "-B", str(PRODUCER / "verify_seal.py")], env)
    run("producer-host-validation", [sys.executable, "-B", str(PRODUCER / "validate.py")], env)
    host_review()
    typecheck()
    # Independent commands must not alter any sealed producer input.
    source_review()
    write("checks.json", checks)
    write("findings.json", findings)
    write("receipt.json", {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "status": "changes-required", "sourceHostAccepted": False, "findings": findings,
          "checksPassed": len(checks), "checkFailures": 0, "commands": len(commands),
          "producerHandoffSHA256": EXPECTED_HANDOFF, "candidateArchiveSHA256": EXPECTED_ARCHIVE,
          "sourceRevisionLabelFromFrozenInput": "4a28261b333c28b4fce386f370a19b93e735c8d2",
          "scope": "Independent finite source and host review; no app product, native query, native execution, or runtime selection",
          "nativeQueries": 0, "nativeAttempts": 0, "appProducts": 0, "nativeAccepted": False,
          "gaAccepted": False, "physicalPhones": "disconnected-deferred",
          "originalSettingsPassed": True, "originalTabPassed": False,
          "originalFailingPredicates": ["actualNativeFocusTraversal"]})
    print(json.dumps({"status": "changes-required", "checksPassed": len(checks), "findings": findings,
                      "nativeAccepted": False}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write("review-attempt-failure.json", {"type": type(exc).__name__, "message": str(exc),
              "checks": checks, "commands": commands, "scope": "Failed independent host review attempt, not acceptance"})
        raise
