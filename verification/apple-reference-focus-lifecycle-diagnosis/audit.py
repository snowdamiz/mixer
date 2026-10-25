#!/usr/bin/env python3
"""Read-only source/evidence verifier. No selected source is imported or executed."""
import hashlib
import json
import plistlib
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LANE = HERE.relative_to(ROOT).as_posix()
REPORT = "docs/apple-reference-focus-lifecycle-diagnosis.md"
SELECTION = "verification/apple-focus-system-native-root-selection/original-selection.json"
RESULT = "verification/apple-focus-system-native-result/result.json"
HANDOFF = "verification/apple-focus-system-native-result/handoff.json"
REVIEW = "verification/apple-focus-system-observation/review-source-package.tar.gz"
SOURCE = "verification/apple-focus-system-native-build/attempt-1/sources.tar.gz"
PRODUCTS = "verification/apple-focus-system-native-build/attempt-1/products.tar.gz"
NATIVE_ROOT = "verification/apple-focus-system-runtime-preparation/native-run-v8-d9a1ae2b-ef02-4db2-b2ff-4979213c8236"
LOG = NATIVE_ROOT + "/runtime/session/command-observer/stdout.log"
HEADERS = [
    "verification/apple-settings-fixed-chunk-native-result-review/inputs/platform-api/UIFocusSystem.h",
    "verification/apple-settings-fixed-chunk-native-result-review/inputs/platform-api/XCUIElement.h",
    "verification/apple-settings-fixed-chunk-native-result-review/inputs/platform-api/XCUIElementAttributes.h",
    "verification/apple-toggle-keyboard-focus-v6-preparation/official/XCUIAutomation-XCUIApplication.h",
]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return (ROOT / path).read_bytes()

def load(path):
    return json.loads(read(path))

def archive(path):
    # Data only, no extraction, imports, compilation, or runtime execution.
    with tarfile.open(ROOT / path) as tar:
        result = {}
        for member in tar.getmembers():
            if member.isfile():
                assert member.name not in result, "duplicate archive member"
                result[member.name] = tar.extractfile(member).read()
        return result

def inputs():
    selection = load(SELECTION)
    paths = [SELECTION, RESULT, HANDOFF, REVIEW, SOURCE, PRODUCTS, LOG,
             "docs/apple-focus-system-native-result.md",
             "verification/apple-focus-system-native-result/source-slices.json",
             "verification/apple-focus-system-native-build/attempt-1/tools.json",
             "verification/apple-focus-system-native-build/attempt-1/packaging-derivation.json"]
    paths += HEADERS
    paths += [row["path"] for row in selection["originals"].values()]
    return {path: {"bytes": len(read(path)), "sha256": digest(read(path))}
            for path in sorted(set(paths))}

def derive():
    checks = {}
    def check(name, condition):
        assert condition, name
        checks[name] = True
    sel, res, hand = load(SELECTION), load(RESULT), load(HANDOFF)
    check("root-selected-original-identity", digest(read(SELECTION)) == "1cee9899bcbd1739787a6ba991a82e6e1fb924f3225420640a82f2d4040ae8f3")
    check("audited-v8-handoff-identity", digest(read(HANDOFF)) == "0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de" and len(hand["members"]) == 10)
    check("authoritative-source-archive-identity", digest(read(REVIEW)) == "d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda")
    accepted, compiled = archive(REVIEW), archive(SOURCE)
    normalized = {name.removeprefix("accepted/"): data for name, data in accepted.items()}
    check("all-forty-reviewed-compile-members-byte-identical", len(normalized) == len(compiled) == 40 and normalized == compiled)
    originals = {}
    for role, binding in sel["originals"].items():
        check(role + "-original-identity", digest(read(binding["path"])) == binding["sha256"])
        check(role + "-original-current-mode", (ROOT / binding["path"]).stat().st_mode & 0o777 == 0o444)
        originals[role] = load(binding["path"])
    before, after = (originals[k]["observation"] for k in ("before", "after"))
    witness = originals["witness"]["witness"]
    b, a = (v["focusSystemDiagnostic"] for v in (before, after))
    check("supplemental-not-authoritative-or-atomic", all(v["authoritative"] is False and v["atomic"] is False for v in (b, a)))
    check("supplemental-complete-no-drops", all(v["captureStatus"] == "complete" and v["dropped"] == 0 for v in (b, a)))
    check("before-prefix-preserved", len(b["entries"]) == 27 and len(a["entries"]) == 32 and a["entries"][:27] == b["entries"])
    rows = a["entries"][26:]
    windows = {r["environment"]["windowIdentity"] for r in rows}
    scenes = {r["scene"]["identity"] for r in rows}
    check("same-non-null-window-and-scene-in-six-samples", len(windows) == len(scenes) == 1 and None not in windows | scenes)
    check("fixed-controls-attached-and-focusable-in-six-samples", all(c["attachedToWindow"] and c["canBecomeFocused"] and c["windowIdentity"] in windows for r in rows for c in r["controls"]))
    control_ids = [[c["identity"] for c in r["controls"]] for r in rows]
    check("fixed-control-identities-stable-in-six-samples", all(ids == control_ids[0] for ids in control_ids))
    check("focus-system-loss-reacquisition-loss", [r["system"]["state"] for r in rows] == ["present", "present", "unavailable", "present", "present", "unavailable"])
    systems = [r["system"]["identity"] for r in rows]
    check("focus-system-identity-turnover", systems[0] == systems[1] and systems[3] == systems[4] and systems[0] != systems[3])
    contexts = after["focusContexts"][1:]
    check("three-new-controller-callbacks-with-no-heading", len(contexts) == 3 and all(c["source"] == "controller" and c["heading"] == 0 for c in contexts))
    ref = control_ids[0][1]
    check("reference-null-reference-null-contexts", [(c["previous"]["identity"], c["next"]["identity"]) for c in contexts] == [(ref, None), (None, ref), (ref, None)])
    check("callbacks-inside-returned-key-interval", all(witness["startedUptime"] <= c["uptime"] <= witness["finishedUptime"] for c in contexts))
    check("foreground-only-before-and-after", witness["before"]["appForeground"] and witness["after"]["appForeground"])
    check("only-original-traversal-predicate-failed", res["failedOriginalPredicates"] == ["actualNativeFocusTraversal"] and res["otherOriginalPredicatesPassed"] == 19)
    check("native-failure-retained", not res["nativePassed"] and res["xcodebuildExitCode"] == 65 and res["officialTotals"]["skippedTests"] == 0)
    check("all-five-recorded-cleanups-pass", len(res["cleanupResults"]) == 5 and all(r["passed"] for r in res["cleanupResults"]))
    check("no-key-window-or-activation-field-in-supplement", all(not ({"isKeyWindow", "activationState", "applicationState"} & set(r)) for r in rows))
    main = compiled["source/Prototype/main.swift"].decode()
    harness = compiled["harness/UITests/ToggleUITests.swift"].decode()
    check("legacy-window-source-and-fixed-preference-retained", "UIWindow(frame: UIScreen.main.bounds)" in main and "window.makeKeyAndVisible(); self.window = window" in main and "override var preferredFocusEnvironments: [UIFocusEnvironment] { [referenceButton] }" in main)
    check("launchcase-commands-resume-reset-only-for-selected-case", 'for command in ["resume", "reset"] + (initial ? ["set-on"] : [])' in harness)
    check("selected-tab-method-and-public-action-retained", 'try key("acquire", "tab", requiredFocusBefore: "plain-uibutton-reference")' in harness and "app.typeKey(value == \"space\" ? XCUIKeyboardKey.space : XCUIKeyboardKey.tab, modifierFlags: [])" in harness)
    products = archive(PRODUCTS)
    app_plist = plistlib.loads(products["MixerToggleDiagnostics.app/Info.plist"])
    runner_plist = plistlib.loads(products["runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/Info.plist"])
    check("built-app-minimum26-no-scene-manifest", app_plist["MinimumOSVersion"] == "26.0" and "UIApplicationSceneManifest" not in app_plist)
    check("separate-apple-runner-has-own-scene-manifest", runner_plist["CFBundleIdentifier"] != app_plist["CFBundleIdentifier"] and runner_plist["UIApplicationSceneManifest"]["UISceneConfigurations"]["UIWindowSceneSessionRoleApplication"][0]["UISceneDelegateClassName"] == "_XCTRunnerAppDelegate")
    log = read(LOG).decode().splitlines()
    start = next(i for i, line in enumerate(log) if line.startswith("Test Case '-[MixerToggleUITests.ToggleUITests test010ReferenceFirstTab]' started"))
    end = next(i for i in range(start + 1, len(log)) if log[i].startswith("Test Case '-[MixerToggleUITests.ToggleUITests test010ReferenceFirstTab]' failed"))
    selected_log = log[start:end + 1]
    check("one-tab-synthesis-in-official-log", sum("Type '⇥' key (XCUIKeyboardKeyTab) with no modifiers" in line for line in selected_log) == 1 and sum("Synthesize event" in line for line in selected_log) == 1)
    check("no-explicit-relaunch-around-key-in-official-log", sum("    Launch dev.mixer.verification.authoredtoggle.diagnostics" in line for line in selected_log) == 1 and not any("Activate dev.mixer.verification.authoredtoggle.diagnostics" in line for line in selected_log))
    slices = []
    for member, spans in {
        "source/Prototype/main.swift": [(46, 52), (97, 103), (256, 299)],
        "source/Prototype/DiagnosticTrace.swift": [(34, 41), (121, 161)],
        "source/Prototype/Info.plist": [(1, 30)],
        "harness/UITests/ToggleUITests.swift": [(262, 274), (333, 341), (394, 423), (471, 474)],
        "harness/MixerToggleUITests.xcodeproj/project.pbxproj": [(10, 18)],
    }.items():
        lines = compiled[member].decode().splitlines()
        for first, last in spans:
            slices.append({"member": member, "memberSHA256": digest(compiled[member]), "lineStart": first, "lineEnd": last, "lines": lines[first - 1:last]})
    timeline = [{"originalPointer": "/observation/focusSystemDiagnostic/entries/" + str(index), **row}
                for index, row in enumerate(a["entries"]) if index >= 26]
    return {
        "schema": 1, "checks": checks, "checkCount": len(checks),
        "sourceMembers": {name: {"bytes": len(data), "sha256": digest(data)} for name, data in sorted(compiled.items())},
        "sourceSlices": slices, "timeline": timeline, "appInfo": app_plist,
        "runnerLifecycleInfo": {k: runner_plist[k] for k in ["CFBundleIdentifier", "MinimumOSVersion", "UIApplicationSceneManifest"]},
        "keyInterval": {k: witness[k] for k in ["startedUptime", "finishedUptime", "publicAPI", "key", "returned"]},
        "focusContexts": contexts,
        "officialLogSlice": {"path": LOG, "lineStart": start + 1, "lineEnd": min(start + 52, end + 1), "lines": log[start:min(start + 52, end + 1)]},
        "finding": "Cause unproven. Stable observed window/scene association excludes a missing-association assertion for these samples. Active/key ownership during the returned key is unobserved.",
        "nextExperiment": "One unchanged public Settings plus first-Tab attempt with bounded passive app/scene/key-window lifecycle observation; no corrective lifecycle rewrite selected.",
        "nativeExecution": False, "gaAccepted": False,
    }

def verify():
    manifest = load(LANE + "/handoff.json")
    for path, expected in manifest["members"].items():
        data = read(path)
        assert {"bytes": len(data), "sha256": digest(data)} == expected, "packet identity " + path
    assert inputs() == load(LANE + "/input-bindings.json"), "upstream identity mismatch"
    result = derive()
    assert result == load(LANE + "/analysis.json"), "derived analysis mismatch"
    print(json.dumps({"passed": True, "checks": result["checkCount"], "members": len(manifest["members"]), "inputFiles": len(inputs()), "sourceMembersCompared": 40, "nativeExecution": False, "networkAccess": False, "writes": 0, "causeProven": False, "gaAccepted": False}, sort_keys=True))

if __name__ == "__main__":
    assert sys.argv[1:] == ["verify"], "usage: audit.py verify"
    verify()
