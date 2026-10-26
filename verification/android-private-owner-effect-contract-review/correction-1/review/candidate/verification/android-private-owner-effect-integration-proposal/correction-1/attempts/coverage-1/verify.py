#!/usr/bin/env python3
"""Check custody and explicit contract coverage; no product code/test execution."""
import ast
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
ORIGINAL = BASE.parent
ANCHORS = {
    "C1.1": ["void cancelInputFromOwner(long sealSerial)", "It never calls `enter()`"],
    "C1.2": ["first close shared draw/input authority", "On terminal entry set"],
    "C1.3": ["at most 12,288 references", "capture the three roster references and counts", "records cannot own a live gesture"],
    "C1.4": ["consumedSerial", "recursive call while", "SEAL_SERIAL_EXHAUSTED", "Serial exhaustion cannot reset"],
    "C1.5": ["Attempt those", "three independently", "first ordinary and first fatal", "distinct from core `CANCEL_QUEUED`"],
    "C1.6": ["while `active`", "never returns", "opening/adopted may be the same identity", "retained outcomes"],
    "C1.7": ["first/middle/last ordinary/fatal", "serial exhaustion", "actual shared/current/pending gate flags"],
    "C2.1": ["void rendererTerminal", "single report route", "exact bound renderer identity"],
    "C2.2": ["retire", "before dispatch", "primary, firstFatal", "CLOSED` remains `CLOSED"],
    "C2.3": ["INTERACTION_EXHAUSTED", "CAPTURE_FAILED", "ROLLBACK_FAILED", "CURRENT_CHECK_FATAL"],
    "C2.4": ["checks main first", "A retired/stale report returns", "Foreign live reports reject", "It throws the retained first fatal"],
    "C2.5": ["commit/finish path remains callback/capture/allocation/native", "reportDeferredTerminalV2", "after the interval"],
    "C2.6": ["Real C2 interaction exhaustion", "core terminal state", "one pending/idle/tail disposition"],
    "C3.1": ["all fourteen actual production subjects", "actual concrete `Gate`, `Input`, `Record`", "Only the enumerated Android FQCNs"],
    "C3.2": ["Closure A", "Closure B", "never a behavior substitute"],
    "C3.3": ["Prepublication", "before `v2Pending` exists", "inside constructors/defaults/text/title helpers", "renderer attach/restore"],
    "C3.4": ["NativeSwitch.setEnabled", "before the `super` mutation", "Normal valid navigation scrolling", "fence.operation == null"],
    "C3.5": ["Actual Gate draw/touch/key checks", "new IME connection refusal", "retained", "InputConnectionWrapper"],
    "C3.6": ["terminal and dirty reentry", "ordinary/fatal throw", "current-record", "source/bytecode"],
    "P1": ["core.focusChanged(lifetime, actualFocus)", "onResume` -> scalar seal -> `core.resume", "core.pause`/`core.stop"],
    "P2": ["All public/package entries check actual main Looper", "trusted internal bodies"],
    "P3": ["before one-shot `NEW -> REGISTERING -> READY`", "all eight accepted slots", "unregister completion remains deferred", "one-shot"],
    "P4": ["inert binding only", "Candidate retains it", "after finish and the active-operation", "without invented tokens"],
    "P5": ["Move the exact core", "without polling", "Stale deliveries cannot steal", "synchronous and unbuffered"],
    "P6": ["exact retained", "zero engine create/prepare/commit/abort/dispatch/effects", "one later drain"],
    "P7": ["Public V1 stays V1", "Private Activity/instrumentation migrates", "real core for tokens, distinct dedicated roots"],
    "P8": ["Only root selects future fixed source-profile", "22 SDK", "sole compiled policy", "Reject old/edited/recomputed"],
    "P9": ["All computer use, capture and native simulator/emulator runs remain paused", "phones", "Final", "GA"],
}


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    receipt = json.loads((BASE / "receipt.json").read_text())
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})

    original_manifest = json.loads((BASE / "original-manifest.json").read_text())
    check("original manifest exact binding", ident((ORIGINAL / "manifest.json").read_bytes())["sha256"] == receipt["original_manifest"]["sha256"])
    for name, expected in original_manifest["files"].items():
        check("original preserved member: " + name, ident((ROOT / name).read_bytes()) == expected)
    observed_original = {str(p.relative_to(ROOT)) for p in ORIGINAL.rglob("*")
                         if p.is_file() and not p.is_relative_to(BASE)
                         and p not in (ORIGINAL / "manifest.json", ORIGINAL / "handoff.sha256")}
    observed_original.add("docs/android-private-owner-effect-integration-proposal.md")
    check("original member closure excludes only correction-1", observed_original == set(original_manifest["files"]))
    check("original handoff binding preserved", (ORIGINAL / "handoff.sha256").read_text().split()[0] == receipt["original_manifest"]["sha256"])
    review = json.loads((BASE / "review-manifest.json").read_text())
    for name, expected in review["files"].items():
        check("review preserved member: " + name, ident((ROOT / name).read_bytes()) == expected)
    check("review manifest exact binding", ident((ROOT / receipt["independent_review_manifest"]["path"]).read_bytes())["sha256"] == receipt["independent_review_manifest"]["sha256"])
    for name, expected in receipt["inputs"].items():
        check("frozen input: " + name, ident((BASE / "inputs" / name).read_bytes()) == expected)
        if name.startswith("native/android/") or name.startswith("cli/"):
            check("current product/policy binding: " + name, ident((ROOT / name).read_bytes()) == expected)
    check("exact accepted core", receipt["inputs"]["native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java"] ==
          {"bytes": 12473, "sha256": "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6"})
    check("exact accepted observer", receipt["inputs"]["native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java"] ==
          {"bytes": 14318, "sha256": "814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac"})
    check("accepted observer receipt", receipt["inputs"]["verification/android-environment-observer-root-review/implementation-acceptance.json"]["sha256"] ==
          "ca6616f73fb7c342a3a74747c571c29f78ab3b6dacf7c3227375a6807295c022")
    profile_text = (BASE / "inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift").read_text()
    profile = json.loads(profile_text.split('Data(#"""', 1)[1].split('"""#.utf8)', 1)[0])
    check("accepted profile2 counts", profile["id"] == "mixer.android-source-pair.2" and len(profile["sdk_files"]) == 22 and len(profile["adapter_files"]) == 20)
    for name, expected in receipt["inputs"].items():
        if name.startswith("native/android/app/"):
            key = name.removeprefix("native/android/")
            check("current app source matches fixed profile: " + key, profile["adapter_files"].get(key) == expected)
    doc = (ROOT / receipt["correction"]["path"]).read_bytes()
    check("correction exact binding", ident(doc) == {k: receipt["correction"][k] for k in ("bytes", "sha256")})
    text = doc.decode()
    lines = text.splitlines()
    mapping = {}
    plan = json.loads((BASE / "preaccess-plan.json").read_text())
    check("28 admitted obligation IDs", set(ANCHORS) == {o["id"] for o in plan["obligations"]} and len(ANCHORS) == 28)
    for key, fragments in ANCHORS.items():
        mapping[key] = []
        for fragment in fragments:
            found = [i for i, line in enumerate(lines, 1) if fragment in line]
            mapping[key].append({"fragment": fragment, "lines": found})
            check("coverage only: " + key + " " + fragment, bool(found))
    check("correction whitespace", all(line.rstrip() == line for line in lines) and text.endswith("\n"))
    roster = json.loads((BASE / "required-host-roster.json").read_text())
    check("roster exact binding", ident((BASE / "required-host-roster.json").read_bytes()) == receipt["roster"])
    b = roster["closures"]["B-concrete-renderer-views"]
    check("fourteen actual concrete subjects", len(b["actual_production_sources"]) == 14 and len(set(b["actual_production_sources"])) == 14)
    check("no substituted renderer/native views in concrete closure", all(p["fqcn"].startswith("android.") or p["fqcn"] == "dev.mixer.android.NativeBridge" for p in b["substitutes"]))
    for name in ("NativeRenderer.java", "NativeAppearanceViewsV2.java", "NativeOwnerV2.java", "OwnerLifecycleV2.java", "NativeCoordinatorV2.java", "NativeEnvironmentV2.java"):
        check("mandatory actual subject: " + name, any(p.endswith("/" + name) for p in b["actual_production_sources"]))
    for closure in roster["closures"].values():
        paths = [p["source"] for p in closure["substitutes"]]
        check("closed substitute files: " + closure["test_source"], len(paths) == len(set(paths)) and closure["compiled_source_roster_is_exact"])
    for barrier in roster["baseline_callback_barriers"]:
        source = (BASE / "inputs" / barrier["source"]).read_text().splitlines()
        check("baseline source call inventory only: " + barrier["id"], source[barrier["line"] - 1].strip() == barrier["source_line"] and barrier["expression"] in barrier["source_line"])
        check("mandatory dirty/terminal/ordinary/fatal cases: " + barrier["id"], set(barrier["required_cases"]) ==
              {"clean", "terminal-at-entry", "terminal-before-return", "dirty-at-entry", "dirty-before-return", "ordinary-throw-after-callback", "fatal-throw-after-callback"})
    for name in ("capture.py", "verify.py", "seal.py"):
        ast.parse((BASE / name).read_text(), filename=name)
        check("source-only script parses: " + name, True)
    result = {"schema": 1, "scope": "source-custody-and-contract-coverage-only-not-product-tests",
              "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python_version": sys.version,
              "checks": checks, "passed": sum(x["passed"] for x in checks), "failed": sum(not x["passed"] for x in checks),
              "product_tests_run": False, "mandatory_host_closures_executed": False,
              "selection_or_implementation_acceptance": False, "native_or_OTA_acceptance": False}
    (BASE / "obligation-map.json").write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    (BASE / "source-only-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("scope", "passed", "failed", "product_tests_run")}, sort_keys=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
