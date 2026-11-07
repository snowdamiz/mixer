"""Closed real-pan observations. Host fixtures never qualify native delivery."""
import importlib.util
import json
import math
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("original_geometry", BASE.parent / "apple-toggle-pan-origin-correction/oracle.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
geometry_valid = original.geometry_valid
SPECS = {x["name"]: x for x in json.loads((BASE / "cases.json").read_bytes())}
CASES = set(SPECS)
ACTIONS = {"native-pan-interruption"}
CASE_ACTION = {name: "native-pan-interruption" for name in CASES}
CASE_COMMAND_SEQUENCE = {
    name: ["resume", "reset"] + (["rtl"] if x["rtl"] else []) +
    (["set-on"] if x["initial"] else []) +
    (["arm-pan-" + x["mode"]] if x["mode"] != "nochange" else [])
    for name, x in SPECS.items()
}
COMMANDS = set(sum(CASE_COMMAND_SEQUENCE.values(), []))


def verdict(candidate, case, action, before, after, file_changed=True):
    spec = SPECS[case]
    b, a = before["state"], after["state"]
    initial, mode = spec["initial"], spec["mode"]
    trace = after["diagnosticTrace"]
    prior_sequence = max((x["sequence"] for x in before["diagnosticTrace"]), default=0)
    delta = [x for x in trace if x["sequence"] > prior_sequence]
    callbacks = [x for x in delta if x["kind"] == "authoredPanCallback"]
    decisions = [x for x in delta if x["kind"] == "shouldBeginDecision"]
    previews = [x["state"] for x in after["events"][len(before["events"]):] if x["reason"] == "panPreview"]
    hooks = after["nativeInterruptions"]
    accepted = mode == "accessibility"
    expected_value = not initial if mode in {"accessibility", "binding"} else initial
    p = {
        "closedCandidateAndAction": candidate == "diagnostic" and action == CASE_ACTION[case],
        "freshObservation": file_changed is True,
        "initialValueDirectionAndGates": b["isOn"] is initial and b["retainedOn"] is initial and b["rtl"] is spec["rtl"] and b["enabled"] is True and b["allowed"] is True,
        "initialPanIdle": b["panActive"] is False and b["previewThumbX"] is None,
        "initialHooksEmpty": before["nativeInterruptions"] == [],
        "nativeIdentityPreserved": type(a["identity"]) is str and bool(a["identity"]) and a["identity"] == b["identity"],
        "untruncatedMonotonicTrace": after["diagnosticTraceDropped"] == 0 and [x["sequence"] for x in trace] == list(range(1, len(trace) + 1)),
        "actualNativeTouchBegin": any(x["kind"] == "recognizerShouldReceiveTouch" and x["phase"] == 0 for x in delta),
        "actualNativePanBegan": bool(callbacks) and callbacks[0]["state"] == 1 and callbacks[0]["touchCount"] == 1,
        "oneNativeRecognizer": bool(callbacks) and len({x["identity"] for x in callbacks}) == 1,
        "actualAdmissionAccepted": bool(decisions) and all(x["result"] is True and x["admissionReason"] == "accepted" for x in decisions),
        "previewBeforeSemanticChange": bool(previews) and all(x["isOn"] is initial and x["retainedOn"] is initial and x["eventCount"] == b["eventCount"] and x["panActive"] is True and type(x["previewThumbX"]) in (int, float) and math.isfinite(x["previewThumbX"]) for x in previews),
        "expectedFinalSelection": a["isOn"] is expected_value and a["retainedOn"] is expected_value and a["selectedTrait"] is expected_value,
        "expectedFinalGates": a["enabled"] is (mode != "disable") and a["allowed"] is (mode != "stale") and a["notEnabledTrait"] is (mode == "disable"),
        "previewCleared": a["panActive"] is False and a["previewThumbX"] is None,
        "noPanCommit": a["panAcceptedCount"] == b["panAcceptedCount"],
        "exactPrimaryAndValueCounts": a["primaryCount"] - b["primaryCount"] == int(accepted) and a["acceptedCount"] - b["acceptedCount"] == int(accepted) and a["eventCount"] - b["eventCount"] == int(accepted),
        "exactValueHistory": a["eventValues"] == b["eventValues"] + ([expected_value] if accepted else []),
        "scrollStationary": abs(a["scrollOffsetY"] - b["scrollOffsetY"]) <= 1,
        "semanticCarrierMetadata": a["buttonTrait"] is True and a["toggleTrait"] is True and a["nativeToggleSelection"] is False and a["label"] == "Sync entries" and a["hint"] == "Updates the sync preference",
    }
    if mode == "nochange":
        states = [x["state"] for x in callbacks]
        compressed = [s for i, s in enumerate(states) if i == 0 or states[i-1] != s]
        p.update(noInterruptionHooks=hooks == [], nativeBeganChangedEnded=compressed == [1, 2, 3],
                 oneNoChangeRelease=a["panNoChangeCount"] == b["panNoChangeCount"] + 1,
                 noPanCancellation=a["panCancellationCount"] == b["panCancellationCount"])
    else:
        p["oneInterruptionHook"] = len(hooks) == 1
        if len(hooks) == 1:
            h = hooks[0]; hb, ha = h["before"], h["after"]; g = h["nativeGestureBefore"]
            p.update(
                exactHookMode=h["mode"] == "arm-pan-" + mode,
                actualHeldNativePan=h["nativeHeld"] is True and hb["panActive"] is True and g["state"] in [1, 2] and g["touchCount"] == 1 and bool(callbacks) and g["identity"] == callbacks[0]["identity"],
                hookAfterNativeBegin=bool(callbacks) and callbacks[0]["uptime"] <= h["startedUptime"] <= h["finishedUptime"],
                hookBeforeAnyCommit=hb["isOn"] is initial and hb["eventCount"] == b["eventCount"] and hb["panAcceptedCount"] == b["panAcceptedCount"] and hb["primaryCount"] == b["primaryCount"],
                hookIdentity=hb["identity"] == ha["identity"] == a["identity"],
                exactAccessibilityReturn=h["returned"] is (True if accepted else None),
                hookClearsPreviewImmediately=ha["panActive"] is False and ha["previewThumbX"] is None,
                cancellationObserved=ha["panCancellationCount"] > hb["panCancellationCount"] and any(x["state"] == 4 for x in callbacks),
                nativeReleaseCannotReplay=all(a[k] == ha[k] for k in ["isOn", "retainedOn", "eventCount", "eventValues", "primaryCount", "acceptedCount", "panAcceptedCount", "panNoChangeCount", "enabled", "allowed"]),
                hookExpectedValue=ha["isOn"] is expected_value and ha["retainedOn"] is expected_value,
                noNoChangeCommit=a["panNoChangeCount"] == b["panNoChangeCount"],
            )
    return {"schema": "mixer.apple-toggle.native-interruption-verdict.1", "candidate": candidate,
            "case": case, "action": action, "predicates": p,
            "passed": all(v is True for v in p.values()),
            "scope": "Real XCTest pan with fixture-controlled application operations; direct accessibility callback does not qualify physical VoiceOver. No full carrier or GA acceptance."}
