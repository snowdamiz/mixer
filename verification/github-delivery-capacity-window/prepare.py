"""Bind the root-selected frozen packets and reconcile current metadata only."""
import hashlib
import json
import platform
from owned import OUT, ROOT, now, row, save

selection = json.loads((OUT / "selection.json").read_bytes())
METADATA = ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
assert not (OUT / "metadata-checkpoint.json").exists()
before = [row(ROOT / p) for p in METADATA]
for path, expected in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == expected, path
packets = []
for name, expected in (("swift-cachework-128-experiment", selection["producerSealSHA256"]),
                       ("swift-capacity-window-independent", selection["independentSealSHA256"])):
    directory = ROOT / "verification" / name
    seal = directory / "seal.json"
    assert row(seal)["sha256"] == expected
    packet = json.loads(seal.read_bytes())
    for member, binding in packet["files"].items():
        actual = row(directory / member)
        assert {k: actual[k] for k in ("bytes", "sha256")} == binding, member
    packets.append({"directory": str(directory.relative_to(ROOT)), "seal": row(seal),
                    "members": len(packet["files"]), "bytes": sum(x["bytes"] for x in packet["files"].values())})
review = json.loads((ROOT / "verification/swift-capacity-window-independent/receipt.json").read_bytes())
assert review["sourceAcceptanceOnly"] and review["allPureChecksPassed"] and review["totalPureMethods"] == 56
assert review["actualCompilerFiniteHarnessFullRuns"] == 0
source = ROOT / selection["workflow"]["source"]
assert row(source)["sha256"] == selection["workflow"]["sha256"]
destination = ROOT / selection["workflow"]["destination"]
with destination.open("xb") as stream:
    stream.write(source.read_bytes())
assert destination.read_bytes() == source.read_bytes()
fieldlog = json.loads((OUT / "fieldlog-promisor-v2-result.json").read_bytes())
assert row(OUT / "fieldlog-promisor-v2-result.json")["sha256"] == selection["smallFieldlogSummary"]["sha256"]
assert fieldlog["publicHydrationPassed"] and fieldlog["packetWants"] == 73
assert fieldlog["failureRequest"] == ["describe", "--exact-match", "--tags"]
new_text = """## Selected capacity and observation window

Root selects the independently reviewed `capacity-window-v1` for one manual
remote campaign. Dense 256 and 512 residents share 4B cache work, 2B instruction
fuel and 16B execution work. Frames/pins remain 128, Runtime/WASI remain 600
seconds, and all category ceilings and the 256 MiB combined envelope remain.
Both compiled geometries, twelve finite methods and one original harness per
arm must pass before either full attempt. The campaign permits two full
attempts, eleven owned commands and 2,700 seconds; no retry or single-arm
fallback is selected. Source evidence passes 26 producer checks, 43 producer
pure methods and 13 additional independent methods. Actual compilation,
geometry and execution remain pending. [Exact root selection and source
seals](verification/github-delivery-capacity-window/selection.json) bind this
delivery; runtime, production defaults and GA remain unaccepted.

FieldLog's subsequent public `44190fef` run hydrated the exact 73 selected SDK
blobs with matching body hashes. SwiftPM then requested app
`describe --exact-match --tags`, which the app-role allowlist rejected before
compilation and all 38 authored tests. All twelve remote outer groups, 29 inner
children and 40 local commands closed. A source-backed app-read correction is
under preparation; no further FieldLog run is selected here. The
[small latest result](verification/github-delivery-capacity-window/fieldlog-promisor-v2-result.json)
supersedes the older hydration frontier while preserving that failed evidence.
Mixer `295f3f18` remains the six-job green ordinary Engine baseline. Gates stay
**8 running, 30 planned, 0 verified**; all native/UI/capture, phone, local
compiler/custody, Unit A and broad hosted holds remain.

"""
for name in ("PLAN.md", "STATUS.md"):
    path = ROOT / name
    text = path.read_text()
    marker = "## Closed public host campaigns\n"
    assert text.count(marker) == 1 and "## Selected capacity and observation window" not in text
    path.write_text(text.replace(marker, new_text + marker, 1))
w = json.loads((ROOT / "work-graph.json").read_bytes())
g = json.loads((ROOT / "gates/ga.json").read_bytes())
assert [sum(x["status"] == s for x in g["gates"]) for s in ("running", "planned", "verified")] == [8, 30, 0]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"] == g["gates"][1]["empiricalCacheDeadlineCampaign"]
capacity = {"schema": 1, "at": now(), "status": "root-selected-reviewed-source; one manual dispatch selected; actual runtime pending",
    "selection": row(OUT / "selection.json"), "producerSeal": packets[0]["seal"], "independentSeal": packets[1]["seal"],
    "workflow": row(destination), "dispatchProfile": "capacity-window-v1", "dispatchLimit": 1,
    "profiles": selection["profiles"], "runtimePolicy": selection["runtimePolicy"],
    "pureEvidence": selection["pureEvidence"], "actualCompilations": 0, "actualFiniteOrHarnessRuns": 0,
    "actualFullAttempts": 0, "runtimeAccepted": False, "productionDefaultsChanged": False,
    "GA_accepted": False, "holdsUnchanged": True}
campaign = w["packages"][7]["empiricalCacheDeadlineCampaign"]
paired = campaign["architecture_comparison"]["paired_frame_pin_128"]
paired.update({"status": "closed diagnostic; both CacheWork768M exhaustion after peak67frames/pins; Corpus1 incomplete and Corpus2 unrun",
    "actualCompilations": 2, "actualFiniteRuns": 2, "actualFiniteMethods": [9, 10],
    "actualHarnessRuns": 2, "actualFullAttempts": 2, "fullAttemptsRemaining": 0,
    "actualResult": w["packages"][7]["framePin128ActualResult"]["summary"],
    "all11CommandsClosed": True, "allFinalOwnerLedgersAndTicketsZero": True,
    "retryOrDefaultPromotionSelected": False})
campaign["architecture_comparison"]["capacity_window_v1"] = capacity
g["gates"][1]["empiricalCacheDeadlineCampaign"] = json.loads(json.dumps(campaign))
w["packages"][7]["framePin128ActualResult"]["next"] = "Exact reviewed capacity-window-v1 selected for one independent bounded campaign; prior two attempts remain spent"
for obj in (w["packages"][7], g["gates"][1]):
    for path in (str((OUT / "selection.json").relative_to(ROOT)), "verification/swift-capacity-window-independent/receipt.json"):
        if path not in obj["evidence"]:
            obj["evidence"].append(path)
latest = {"summary": row(OUT / "fieldlog-promisor-v2-result.json"), "commit": fieldlog["commit"],
    "tree": fieldlog["tree"], "run": fieldlog["runID"], "status": fieldlog["status"],
    "public73BlobHydrationPassed": True, "failureRequest": fieldlog["failureRequest"],
    "testsStartedObserved": 0, "authoredTests": 38, "allRemoteAndLocalCommandsClosed": True,
    "next": "Source-backed exact app Git reads correction under preparation; no further host dispatch selected",
    "nativeDogfoodOrGA": False}
flow = w["packages"][16]["activePublicSDKFlow"]
flow["latestPromisorV2Result"] = latest
flow["latestFilteredTransportResult"]["historical_observation"] = True
flow["public_SDK_adoption_current_state"].update({"commit": fieldlog["commit"], "run_id": fieldlog["runID"],
    "host_result": "exact73blob hydration passed; app describe read guard rejected before resolve/build/tests"})
for obj in (w["packages"][16], g["gates"][25], g["gates"][26]):
    obj["fieldlogPromisorV2Result"] = latest
    if latest["summary"]["path"] not in obj["evidence"]:
        obj["evidence"].append(latest["summary"]["path"])
for obj in (w, g):
    obj["executionPolicy"]["currentCapacityWindowSelection"] = {"at": now(),
        "selection": row(OUT / "selection.json"), "sourceOnlyAccepted": True,
        "fieldlogLatest": latest["summary"], "runtimeProductionOrGAAccepted": False}
for name, obj in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(obj, indent=2) + "\n")
for path, expected in PROTECTED.items():
    assert row(ROOT / path)["sha256"] == expected
save("metadata-checkpoint.json", {"schema": 1, "at": now(), "command": "python3 -B verification/github-delivery-capacity-window/prepare.py",
    "python": platform.python_version(), "base": selection["base"], "baseTree": selection["baseTree"],
    "before": before, "after": [row(ROOT / p) for p in METADATA], "packets": packets,
    "protectedFilesUnchanged": PROTECTED, "rootClosedCheckpointPreserved": True,
    "scope": "Frozen source/receipt hash verification, exact workflow installation and four current metadata updates; no compiler/runtime/native/process inventory",
    "GA_accepted": False})
print(json.dumps({"prepared": True, "sealedMembers": sum(p["members"] for p in packets),
    "sealedBytes": sum(p["bytes"] for p in packets), "workflowSHA256": row(destination)["sha256"], "gates": [8,30,0]}))
