#!/usr/bin/env python3
"""Seal this lane's data-only investigation; writes only its owned packet."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = HERE.relative_to(ROOT).as_posix()
START = datetime.now(timezone.utc).isoformat()
audit = runpy.run_path(str(HERE / "audit.py"))

def emit(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

data = audit["derive"]()
emit("input-bindings.json", audit["inputs"]())
emit("analysis.json", data)
emit("official-reference-notes.json", {
    "schema": 1,
    "accessedUTC": datetime.now(timezone.utc).isoformat(),
    "scope": "Primary Apple documentation read through web tool; summaries below are authored notes, not downloaded SDK content. Pinned local headers are bound separately.",
    "references": [
        {"url": "https://developer.apple.com/documentation/UIKit/UIWindow", "supports": "Window key status can be observed through public become/resign-key notifications; makeKeyAndVisible establishes key visibility at the call."},
        {"url": "https://developer.apple.com/documentation/uikit/uiwindow/iskeywindow", "supports": "Key-window status is scoped to the scene on current iOS; the key window is the destination for keyboard and other non-touch events."},
        {"url": "https://developer.apple.com/documentation/uikit/uiwindow/windowscene", "supports": "windowScene names the associated scene; a nil assignment removes that association. Selected runtime samples already show a scene."},
        {"url": "https://developer.apple.com/documentation/uikit/uifocusenvironment/preferredfocusenvironments", "supports": "The ordered list supplies the search for the default focused item; it does not define a Tab successor."},
        {"url": "https://developer.apple.com/documentation/uikit/uifocusheading/uifocusheadingnone", "supports": "Heading none conveys no movement heading; it does not identify the cause of an update."},
        {"url": "https://developer.apple.com/documentation/uikit/uiwindowscene/focussystem", "supports": "The nullable property can be unavailable when the scene does not support focus."},
        {"url": "https://developer.apple.com/documentation/uikit/uiscene", "supports": "Scene lifecycle has public connect/disconnect, foreground/background and activate/deactivate notifications."},
        {"url": "https://developer.apple.com/documentation/uikit/uiscene/activationstate-swift.enum/foregroundinactive", "supports": "An onscreen foreground scene may be inactive and not receiving user events."},
        {"url": "https://developer.apple.com/documentation/xcuiautomation/xcuielement/typekey(_:modifierflags:)-9ubn", "supports": "The public API types one physical-key representation with specified modifiers; return alone does not promise focus traversal."},
        {"url": "https://developer.apple.com/documentation/uikit/transitioning-to-the-uikit-scene-based-life-cycle", "supports": "Programmatic scene lifecycle setup creates a UIWindow associated with a UIWindowScene. This general direction does not prove the cause of the selected iOS26.5 failure."},
    ],
    "limits": "Online docs were read as requirements/reference material. They are not evidence of actual lifecycle state during the original run. No source implementation was obtained from competitors or imported from documentation."
})
emit("experiment.json", {
    "schema": 1,
    "status": "proposed-only-awaiting-root-selection",
    "experimentCount": 1,
    "name": "passive-app-scene-key-window-observation-during-original-first-tab",
    "sourcePatchProvided": False,
    "nativeExecutionAuthorizedByThisPacket": False,
    "actions": "The original public Settings setup and one public Tab from the same reference-focus precondition; preserve the original oracle/actions/budgets.",
    "observer": {
        "registration": "In diagnostic app launch before makeKeyAndVisible; record registration time and initial scope.",
        "captureSites": ["registration", "existing focus sample", "owned app lifecycle notification", "owned window lifecycle notification", "owned scene lifecycle notification"],
        "fields": ["sequence", "systemUptime", "processIdentifier", "notificationNameOrCaptureSite", "notificationObjectIdentity", "applicationState", "ownedWindowIdentity", "ownedWindowIsKey", "ownedWindowSceneIdentity", "ownedSceneActivationState"],
        "notifications": {
            "UIApplication": ["didBecomeActiveNotification", "willResignActiveNotification", "willEnterForegroundNotification", "didEnterBackgroundNotification"],
            "UIScene": ["willConnectNotification", "didDisconnectNotification", "didActivateNotification", "willDeactivateNotification", "willEnterForegroundNotification", "didEnterBackgroundNotification"],
            "UIWindow": ["didBecomeKeyNotification", "didResignKeyNotification", "didBecomeVisibleNotification", "didBecomeHiddenNotification"],
        },
        "scope": "Diagnostic app only; window/scene notifications filtered to the retained owned objects. Do not enumerate other apps or change delegates/lifecycle.",
        "mainActor": True, "atomic": False, "authoritative": False,
        "maximumRows": 64, "maximumEncodedBytes": 16384,
        "captureStatusAndDroppedRequired": True,
        "timing": "Use original witness interval and ordered existing focus-context references. Retain non-atomic timing limits; never supply an oracle identity/anchor from diagnostic data."
    },
    "outcomes": [
        {"condition": "Ordered lifecycle/key transition and confirming samples accompany focus loss", "meaning": "Supports transient event-ownership loss; transition initiator still unknown."},
        {"condition": "Complete trace; same window key, app active, scene foreground-active at observed focus-system changes; no transition notification", "meaning": "Narrows to focus-system/input support within observed active lifecycle; cannot exclude all unobserved transients or prove Apple defect."},
        {"condition": "Incomplete scope/timing/size coverage or changed native traversal", "meaning": "Record the exact new outcome; no causal assertion or automatic repeat; retain original V8 failure."}
    ],
    "invariants": {"settingsSessionSeconds": 29, "requestAllowanceSeconds": 2, "anchoredSwitchObservationSeconds": 3, "transportLimits": "unchanged", "oracle": "unchanged", "inputAction": "one original public Tab", "phones": "disconnected-deferred", "simulators": "one owned instance maximum; preserve baseline; cleanup including failure"},
    "forbiddenAdditions": ["focus request", "extra key", "tap fallback", "app activation", "scene migration", "sleep", "polling", "custom key handler", "budget increase", "frozen V7 join import/execute", "automatic retry"],
    "gaAccepted": False
})
summary = {"passed": True, "checks": data["checkCount"], "inputFiles": len(audit["inputs"]()), "sourceMembersCompared": 40, "nativeExecution": False, "causeProven": False, "gaAccepted": False}
emit("command-receipt.json", {
    "schema": 1,
    "command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", PREFIX + "/prepare.py"],
    "cwd": str(ROOT), "startedUTC": START, "finishedUTC": datetime.now(timezone.utc).isoformat(),
    "python": sys.version, "executable": sys.executable,
    "rootReportedNativeContext": "6403eea98031207f6e40a72b55dfd3bd4e7e6ec2",
    "reviewSourceSHA256": "d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda",
    "output": summary,
    "scope": "Host-only source/evidence data derivation and owned packet sealing; no imported upstream code, child process, native/device/UI/Git query, frozen join execution, or service mutation.",
    "references": "Apple primary web documentation read separately; read-only audit itself uses no network.",
})
names = ["audit.py", "prepare.py", "input-bindings.json", "analysis.json", "official-reference-notes.json", "experiment.json", "command-receipt.json"]
members = [PREFIX + "/" + n for n in names] + [audit["REPORT"]]
bindings = {}
for path in sorted(members):
    raw = (ROOT / path).read_bytes()
    bindings[path] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
emit("handoff.json", {
    "schema": 1, "status": "host-source-evidence-diagnosis-complete-cause-unproven",
    "agentModelRequested": "gpt-6.1-sol", "agentReasoningRequested": "xhigh",
    "members": bindings, "inputFiles": summary["inputFiles"], "checks": summary["checks"],
    "runID": "d9a1ae2b-ef02-4db2-b2ff-4979213c8236",
    "nativeExecution": False, "causeProven": False, "productionPatchSelected": False,
    "nextExperimentCount": 1, "nativePassed": False, "gaAccepted": False,
})
(HERE / "handoff.sha256").write_text(hashlib.sha256((HERE / "handoff.json").read_bytes()).hexdigest() + "  handoff.json\n")
print(json.dumps(summary, sort_keys=True))
