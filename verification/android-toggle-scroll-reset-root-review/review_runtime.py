"""Review retained actual API37 evidence; never executes native tools."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "verification/android-toggle-scroll-reset-fix/runtime/runtime-1"
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

seal = read(RUN / "artifact-seal.json")
assert {str(p.relative_to(RUN)) for p in RUN.rglob("*") if p.is_file()} == set(seal) | {"artifact-seal.json"}
for name, binding in seal.items():
    assert sha(RUN / name) == binding["sha256"]
    assert (RUN / name).stat().st_size == binding["bytes"]
receipt = read(RUN / "receipt.json")
native = read(RUN / "toggle-supplement-results.json")
assert (RUN / "toggle-supplement-results.json").read_bytes() == (RUN / "native-results-export.log").read_bytes()
assert receipt["status"] == "failed-native-attempt-retained"
assert receipt["failure"] == "ValueError('supplement schema')"
assert native["status"] == "failed-retained"
assert native["failure"] == "java.lang.AssertionError: native focus admitted"
assert len(native["cases"]) == 39
assert [c["id"] for c in native["cases"]] == list(range(1, 40))
assert all(c["status"] == "passed-component-native" for c in native["cases"])
assert (native["assertions"], native["addedSetupAssertions"], native["originalAssertionCounter"], native["events"]) == (189, 6, 183, 114)
assert native["assertions"] == native["addedSetupAssertions"] + native["originalAssertionCounter"]
assert native["authoritativeCommits"] is native["rawCheckedListenerCallbacks"] is None
assert native["apkSHA256"] == receipt["apkSHA256"] == "04fc45b28ea77a1a246f4b0b7675ecef7440966f2d5954be4b4bf360737a3dbb"
assert native["sourceClosureSHA256"] == receipt["sourceClosureSHA256"] == "186ed27e31975f4033059adc0c166098a6790bd31e30e12c2ede2a173c6dccc5"
instrument = (RUN / "actual-native-component.log").read_text()
assert "exportSHA256=" + sha(RUN / "native-results-export.log") in instrument
assert "diagnosticSHA256=" + sha(RUN / "diagnostic-private-fixture.log") in instrument
assert receipt["diagnostics"]["fixtureDiagnosticBindingVerified"]
for row in receipt["commands"] + receipt["diagnostics"]["captures"] + receipt["scrollDiagnostics"]["captures"]:
    assert sha(RUN / row["output"]) == row["sha256"]
    assert not row["ownedCommandGroupCleanup"]["after"]
    assert not row.get("truncated", False)
assert receipt["scrollDiagnostics"]["traceValid"] and receipt["scrollDiagnostics"]["instrumentationHashVerified"]
trace = read(RUN / "scroll-private-trace.log")
assert len(trace["entries"]) == 162 and trace["dropped"] == trace["observerFailures"] == 0
assert trace["listenerConsumes"] is False
assert [e["sequence"] for e in trace["entries"]] == list(range(162))
cases = []
for case_id in (18, 19):
    entries = [e for e in trace["entries"] if e["case"] == case_id]
    one = lambda stage: next(e for e in entries if e["stage"] == stage)
    setup = one("scroll.input.preconditions")
    geometry = setup["geometry"]
    assert geometry["contentHeight"] == 6000 and geometry["viewportHeight"] == 2622
    assert geometry["positiveContentExtent"] and geometry["canScrollDown"]
    assert setup["state"]["scrollY"] == 0
    assert all(setup["ownedInput"][k] for k in ("admitted", "windowOwned", "firstOnVisibleToggle", "insetsAvailable"))
    assert setup["addedSetupAssertionsBefore"] == 3 * (case_id - 18)
    injections = [e for e in entries if e["stage"] == "worker.injection.before"]
    activity = [e for e in entries if e["stage"] == "activity.dispatch.before"]
    child = [e for e in entries if e["stage"] == "toggle.OnTouchListener.before-return-false"]
    intercept = [e for e in entries if e["stage"] == "scroll.intercept.after"]
    # Action fields are read from the actual public MotionEvent observation.
    actions = lambda rows: [e["event"]["masked"] for e in rows]
    assert actions(injections) == actions(activity) == [0] + [2] * 7 + [1]
    assert actions(child) == [0, 3]
    assert sum(e["returned"] is True for e in intercept) == 1
    final = one("scroll.geometry.after")["state"]
    assert final["scrollY"] == 365
    assert all(final[k] for k in ("scrollPositive", "zeroProposals", "notPressed", "inputOpen"))
    cases.append({"case": case_id, "setup": setup, "injectionActions": actions(injections),
                  "activityActions": actions(activity), "childActions": actions(child),
                  "interceptTrueCount": 1, "finalState": final})
assert receipt["cleanup"] == "stopped" and not receipt["ownedEmulatorGroupCleanup"]["after"]
clean = receipt["extractionCleanup"]
assert clean["status"] == "removed" and clean["pathAbsentAfterCleanup"] and not Path(clean["path"]).exists()
assert (clean["files"], clean["bytes"]) == (187, 173027566)
assert clean["openHoldersCheck"]["exitCode"] == 1
assert not (RUN / "extraction-open-holders.log").read_bytes()
assert not receipt["physicalTargetsQueried"] and receipt["target"]["ro.kernel.qemu"] == "1"
assert all(not (RUN / f"port-after-{p}.log").read_bytes() for p in (5586, 5587))
assert not receipt["outputBudget"]["overflow"]
result = {
    "schema": 1,
    "status": "39-component-cases-pass-scroll-cancellation-observed-keyboard-focus-and-result-parser-failures-retained",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevisionContext": "bbed074d3bd2453bbcc0807f05219d042cedd738",
    "completedComponentCases": 39,
    "assertionCounterIncludingFailure": 189,
    "addedSetupAssertions": 6,
    "originalAssertionCounterIncludingFailure": 183,
    "fixtureCountedEvents": 114,
    "full45CaseSuiteAccepted": False,
    "nativeFailure": native["failure"],
    "hostParserFailure": receipt["failure"],
    "scrollCases": cases,
    "observation": "Both original scroll protocols have all nine requests delivered to Activity, one actual parent interception and child CANCEL each, positive scroll, zero proposals and no pressed state. Case40 fails before keyboard input because requestFocus returns false; current touch mode and focusability were not observed there.",
    "parserFinding": "Two intentionally added setup-counter fields are incompatible with the inherited exact-key oracle. This is separate from the native focus failure; correcting parsing cannot pass this run.",
    "cleanup": "Owned emulator group4305 and ports5586/5587 empty;187 extracted files/173027566 bytes removed.",
    "next": "Observe native keyboard focus preconditions and select legitimate fixture setup; repair strict export schema without weakening original cases or production focus policy.",
    "scope": "Actual API37 arm64 private View fixture. Original429-assertion coordinator baseline remains separate. No engine-authoritative commit, complete45-case acceptance, live integration, physical phone, TalkBack, Apple parity or GA acceptance.",
    "bindings": {str(p.relative_to(ROOT)): sha(p) for p in sorted(RUN.rglob("*")) if p.is_file()},
}
result["bindings"][str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
result["bindings"][str((OUT / "selection.json").relative_to(ROOT))] = sha(OUT / "selection.json")
(OUT / "runtime-review.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["status"])
