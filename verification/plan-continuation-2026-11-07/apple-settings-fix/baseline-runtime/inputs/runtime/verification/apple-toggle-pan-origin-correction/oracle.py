"""Independent closed evidence verdicts. Host unit tests do not qualify UIKit."""
import math

EXPECTED_CHECK_NAMES = {
    "diagnostic": ["binding writes emit no events", "disabled native trait", "public native toggle and button traits", "authored metadata survives native state", "binding environment and theme preserve native identity", "native visual carrier is custom unconfigured UIButton", "pan reference is attached directly to root view outside scroll", "carrier-primary-off-to-on strict settled transition", "carrier-primary-on-to-off strict settled transition", "carrier-stale-primary strict settled transition", "carrier-disabled-primary strict settled transition", "carrier-disabled-accessibility strict settled transition", "carrier-accessibility-off-to-on strict settled transition", "carrier-accessibility-on-to-off strict settled transition", "reference-primary-off-to-on strict settled transition", "reference-primary-on-to-off strict settled transition", "reference-accessibility-off-to-on strict settled transition", "reference-accessibility-on-to-off strict settled transition", "diagnostic trace has not overflowed"],
    "comparator": ["binding writes emit no events", "UIKit primary activation selects and emits once", "UIKit second activation deselects and emits once", "stale native primary action restores value without event", "disabled primary action has no value event", "disabled native trait", "disabled accessibility activation rejected", "UIButton accessibility activation selects and emits once", "public native toggle and button traits", "authored metadata survives native state", "binding environment and theme preserve native identity", "native visual carrier is custom unconfigured UIButton"]
}

ACTIONS = {"reference-pan", "blank-scroll", "authored-pan", "carrier-scroll", "plain-tap", "authored-tap", "direct-suite"}
CASES = {"standalone-pan", "blank-scroll", "ltr-on", "ltr-off", "rtl-on", "rtl-off", "carrier-scroll", "diagnostic-taps", "plain-taps", "comparator-taps", "diagnostic-direct", "comparator-direct"}
COMMANDS = {"resume", "reset", "rtl", "set-on", "self-tests"}
CASE_ACTION = {"standalone-pan": "reference-pan", "blank-scroll": "blank-scroll", "carrier-scroll": "carrier-scroll", "plain-taps": "plain-tap", "diagnostic-taps": "authored-tap", "comparator-taps": "authored-tap", "diagnostic-direct": "direct-suite", "comparator-direct": "direct-suite", **{name: "authored-pan" for name in ("ltr-on", "ltr-off", "rtl-on", "rtl-off")}}
CASE_COMMAND_SEQUENCE = {case: ["resume", "reset"] + (["rtl"] if case.startswith("rtl-") else []) + (["set-on"] if case in {"ltr-off", "rtl-off"} else []) + (["self-tests"] if case.endswith("-direct") else []) for case in CASES}

def geometry_valid(value):
    if not isinstance(value, dict) or set(value) not in ({"app", "target"}, {"app", "target", "start", "end", "initialHoldSeconds", "velocity", "finalHoldSeconds"}): return False
    def rectangle(rect):
        return isinstance(rect, dict) and set(rect) == {"x", "y", "width", "height"} and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 4096 for v in rect.values()) and rect["width"] > 0 and rect["height"] > 0
    if not all(rectangle(value[key]) for key in ("app", "target")): return False
    if "start" in value:
        for key in ("start", "end"):
            if not isinstance(value[key], dict) or set(value[key]) != {"x", "y"} or not all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 4096 for v in value[key].values()): return False
        if value["initialHoldSeconds"] != 0.15 or value["finalHoldSeconds"] != 0.15 or value["velocity"] != 120: return False
    return True

def verdict(candidate, case, action, before, after, file_changed=True):
    b, a = before["state"], after["state"]
    tests = {"freshObservationAfterBaseline": file_changed, "sameNativeCarrierIdentity": a["identity"] == b["identity"], "enabledAndAllowed": b["enabled"] is True and b["allowed"] is True, "caseMatchesClosedAction": CASE_ACTION.get(case) == action}
    trace = after.get("diagnosticTrace", [])
    previous = max((entry["sequence"] for entry in before.get("diagnosticTrace", [])), default=0)
    delta = [entry for entry in trace if entry["sequence"] > previous]
    if candidate == "diagnostic":
        tests["completeTraceNoOverflow"] = after.get("diagnosticTraceDropped") == 0 and [entry["sequence"] for entry in trace] == list(range(1, len(trace) + 1))
    def count(key): return a[key] - b[key]
    def callbacks(kind):
        return [entry for entry in delta if entry["kind"] == kind]
    def recognized(kind, nested=False):
        entries = callbacks(kind)
        gestures = [entry.get("gesture", {}) if nested else entry for entry in entries]
        states = [entry.get("state") for entry in gestures]
        compressed = [state for index, state in enumerate(states) if index == 0 or state != states[index-1]]
        tests["nativePanOrderedBeganChangedEnded"] = compressed == [1, 2, 3]
        tests["nativePanDurationAtLeast150ms"] = bool(entries) and max(entry["uptime"] for entry in entries) - min(entry["uptime"] for entry in entries) >= 0.15
        tests["sameNativeRecognizerIdentity"] = bool(gestures) and None not in [entry.get("identity") for entry in gestures] and len({entry.get("identity") for entry in gestures}) == 1
        times = [entry["uptime"] for entry in entries]
        tests["nativeCallbackTimeProgressed"] = bool(times) and times == sorted(times) and len(set(times)) >= 3
        translations = [entry.get("translationInWindow", {}) for entry in gestures]
        valid = bool(translations) and all(set(point) == {"x", "y"} and all(type(v) in (int, float) and math.isfinite(v) for v in point.values()) for point in translations)
        axis = "y" if action in {"blank-scroll", "carrier-scroll"} else "x"
        positive = action == "reference-pan" or (action == "authored-pan" and case in {"ltr-on", "rtl-off"})
        span = max(point[axis] for point in translations)-min(point[axis] for point in translations) if valid else 0
        tests["nativeTranslationProgressedAtLeast12pt"] = valid and span >= 12
        final = translations[-1][axis] if valid else 0
        tests["nativeTranslationHasIntendedDirection"] = valid and (final >= 12 if positive else final <= -12)
    if action == "reference-pan":
        recognized("referencePan")
        tests["authoredStateUnchanged"] = a["isOn"] == b["isOn"] and count("eventCount") == 0
    elif action in {"blank-scroll", "carrier-scroll"}:
        recognized("scrollPanCallback", nested=True)
        tests["positiveScrollOffset"] = a["scrollOffsetY"] - b["scrollOffsetY"] >= 20
        tests["authoredStateUnchanged"] = a["isOn"] == b["isOn"] and count("eventCount") == 0
        tests["noAuthoredPanAcceptance"] = count("panAcceptedCount") == 0
        if action == "carrier-scroll":
            decisions = [entry for entry in callbacks("shouldBeginDecision") if entry.get("isAuthoredPan")]
            tests["authoredHorizontalAdmissionRejected"] = bool(decisions) and all(entry["result"] is False for entry in decisions)
    elif action == "authored-pan":
        recognized("authoredPanCallback")
        tests["correctInitialDirectionalPremise"] = b["isOn"] == case.endswith("off") and b["rtl"] == case.startswith("rtl")
        tests["selectedTransition"] = a["isOn"] is (not b["isOn"]) and a["retainedOn"] == a["isOn"]
        tests["onePanAndOneValueNoPrimary"] = count("panAcceptedCount") == 1 and count("eventCount") == 1 and count("primaryCount") == 0 and a["eventValues"][-1:] == [a["isOn"]]
        decisions = [entry for entry in callbacks("shouldBeginDecision") if entry.get("isAuthoredPan")]
        tests["nativeAdmissionAccepted"] = bool(decisions) and any(entry["result"] is True for entry in decisions)
        events = after["events"][len(before["events"]):]
        previews = [entry["state"] for entry in events if entry["reason"] == "panPreview"]
        tests["intermediatePreviewWithoutCommit"] = bool(previews) and all(value["isOn"] == b["isOn"] and value["eventCount"] == b["eventCount"] and value["panActive"] is True and value["previewThumbX"] is not None for value in previews)
        tests["previewClearedOnRelease"] = a["panActive"] is False and a["previewThumbX"] is None
        tests["scrollRemainedStationary"] = abs(a["scrollOffsetY"] - b["scrollOffsetY"]) <= 1
    elif action == "authored-tap":
        tests["selectedTransition"] = a["isOn"] is (not b["isOn"]) and a["retainedOn"] == a["isOn"]
        tests["onePrimaryOneCorrectValue"] = count("primaryCount") == 1 and count("eventCount") == 1 and a["eventValues"][-1:] == [a["isOn"]]
        tests["noPanAcceptance"] = count("panAcceptedCount") == 0
        if candidate == "diagnostic": tests["actualNativeTouchBegin"] = bool(callbacks("carrierTouchesBegan"))
    elif action == "plain-tap":
        rb, ra = before["reference"], after["reference"]
        tests["samePlainUIButtonIdentity"] = rb["identity"] == ra["identity"]
        tests["plainSelectedTransition"] = ra["selected"] is (not rb["selected"])
        tests["onePlainPrimary"] = ra["primaryCount"] - rb["primaryCount"] == 1
        tests["plainPrimaryObservedCorrectSelection"] = ra["primaryValues"][-1:] == [ra["selected"]]
        tests["plainAttachedToWindow"] = rb["attachedToWindow"] is True and ra["attachedToWindow"] is True
        tests["authoredStateUnchanged"] = a["isOn"] == b["isOn"] and count("eventCount") == 0
    elif action == "direct-suite":
        expected = 19 if candidate == "diagnostic" else 12
        checks = after.get("checks", [])
        tests["originalStrictCheckCount"] = len(checks) == expected and len({entry["name"] for entry in checks}) == expected
        tests["originalStrictCheckNamesAndOrder"] = [entry["name"] for entry in checks] == EXPECTED_CHECK_NAMES[candidate]
        tests["allOriginalStrictChecksTrue"] = len(checks) == expected and all(entry["pass"] is True for entry in checks)
        if candidate == "diagnostic": tests["diagnosticSuiteExplicitlyComplete"] = after.get("diagnosticSuiteState") == "complete"
    else: tests["supportedAction"] = False
    view_touches = [entry for entry in delta if "Touches" in entry["kind"]]
    return {"schema": "mixer.apple-toggle.xctest-verdict.1", "candidate": candidate, "case": case, "action": action, "predicates": tests, "passed": all(value is True for value in tests.values()), "newNativeTraceKinds": [entry["kind"] for entry in delta], "viewTouchObservations": {"kinds": [entry["kind"] for entry in view_touches], "movedCount": sum(entry.get("phase") == 1 for entry in view_touches), "qualification": "Observed separately because public cancelsTouchesInView may suppress view delivery; strict native recognizer translation/time required"}, "referenceValueCountDelta": after.get("reference", {}).get("valueCount", 0)-before.get("reference", {}).get("valueCount", 0) if action == "plain-tap" else None, "originalChecks": after.get("checks", []) if action == "direct-suite" else None, "scope": "Simulator diagnostics only; no product, screenshot parity, physical VoiceOver, external release or GA acceptance"}
