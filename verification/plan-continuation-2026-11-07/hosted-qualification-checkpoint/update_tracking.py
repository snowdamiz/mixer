"""Refresh current checkpoints; leave earlier checkpoint sections unchanged."""
import datetime
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = BASE.parent.parent
PREFIX = str(BASE.relative_to(ROOT)) + "/"
OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((BASE / name).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


for capture in ["ci-corrections-integration/ci-discovery/final-jobs.json",
                "pair9-r2-delivery/ci-discovery/final-jobs.json"]:
    jobs = read(capture)["jobs"]
    require(len(jobs) == 7 and all(j["status"] == "completed" and j["conclusion"] == "success" for j in jobs), capture)
require(read("generated-java-hosted-acceptance.json")["decision"] == "ACCEPT_FROZEN_PAIR8_HOSTED_JAVA_BOOTSTRAP", "hosted review")
require(read("cache-deadline-ci-acceptance.json")["decision"] == "ACCEPT_EXACT_RUST_1_99_1_HOST_FIXTURE_NEW_DEADLINE_ADOPTION", "cache review")

replacements = [
    ("attempt 1, is queued.", "attempt 1, has passed all seven jobs. Its uploaded host and generated-Java artifacts are under independent review."),
    ("attempt 1, has passed VM, Android host, cache fixture and services; Swift, capability-native and generated-Java remain active.", "attempt 1, has passed all seven jobs."),
    ("[Fresh cache artifact acquisition](verification/plan-continuation-2026-11-07/ci25-cache-actual/acquisition.json) is complete and independent qualification is running.",
     "[Fresh cache qualification](verification/plan-continuation-2026-11-07/cache-deadline-ci-acceptance.json) accepts the exact Rust1.99.1 fixture and new deadline-control adoption: 103 commands, 768 method executions, 124 captures and 135 Python controls. [Hosted pair8 Java acceptance](verification/plan-continuation-2026-11-07/generated-java-hosted-acceptance.json) covers the official bootstrap and six consumers, 92 command records and 24 tamper invocations; it does not qualify pair9 or runtime behavior."),
    ("Pair `.9` fixes that delivery path in source and host tests; fresh native callback/restoration/silence evidence remains pending.",
     "Pair `.9` fixes that delivery path in source and host tests. The selected runtime preparation stopped before any emulator or APK build because the old controller lacked required custody, output-bound and failure-restoration handling. Zero native attempts were consumed. A bounded controller repair is active; callback/restoration/silence evidence remains pending."),
    ("W13 now has an isolated implementation lane for the [selected read-only existing App Store Connect build-status command](verification/plan-continuation-2026-11-07/store-next-integration/REPORT.md): the real CLI/HTTP reader, identity-bound local observations and host tests.",
     "W13's isolated implementation of the [read-only existing App Store Connect build-status command](verification/plan-continuation-2026-11-07/store-next-integration/REPORT.md) passes eight original host test groups. [Independent review](verification/plan-continuation-2026-11-07/store-status-review/REPORT.md) reproduced one credential-persistence defect: a prior observation recognized as a newly supplied token was hidden only in the current response, then re-emitted by a later credential-free invocation. The correction is active; parent integration, the 103-input rebind and fresh consumers remain pending."),
    ("Another frontend-dependent attempt requires Accessibility preflight and cleanup that preserves unrelated devices.",
     "A safe controller successor and read-only Accessibility preflight are in progress before any new frontend/device creation. Another original Tab attempt remains dependent on verified Accessibility and cleanup that preserves unrelated devices."),
]
changed = []
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    original = path.read_text()
    current, marker, historical = original.partition("\n## Previous")
    (OUT / (name + ".before")).write_text(current)
    for old, new in replacements:
        require(current.count(old) == 1, name + " missing current phrase: " + old)
        current = current.replace(old, new)
    path.write_text(current + marker + historical)
    require(path.read_text().partition("\n## Previous")[2] == historical, "historical text changed")
    changed.append(name)

checkpoint = "Pair9 R2 delivered at96f03ab6; ordinary CI42430741909 attempt1 passes all7jobs. Exact local six-consumer Java17/D8 artifacts are independently accepted; hosted pair9 host/Java artifacts are under review. Preceding25ac seven-job CI, exact Rust1.99.1 deadline-adoption fixture and hosted pair8 bootstrap/sixconsumers are independently accepted. Native testing is resumed; Android runtime preparation stopped before emulator/compilation for controller custody repair. API-floor, FieldLog and GA remain pending."
snapshots = {}
for name, key, ids in [("work-graph.json", "packages", {"W02", "W05"}), ("gates/ga.json", "gates", {"G02", "G06"})]:
    path = ROOT / name
    data = json.loads(path.read_text())
    snapshots[name] = {}
    for item in data[key]:
        if item["id"] in ids:
            snapshots[name][item["id"]] = {"currentCheckpoint": item.get("currentCheckpoint"), "continuation20261107": item["continuation20261107"]}
    # Deep copy the retained snapshot before changing nested dictionaries.
    snapshots[name] = json.loads(json.dumps(snapshots[name]))
    for item in data[key]:
        if item["id"] not in ids:
            continue
        item["currentCheckpoint"] = checkpoint
        c = item["continuation20261107"]
        c["state"] = "pair9 R2 delivered; seven-job CI passed; native controller repair active"
        c["ciCorrectionsDelivery"].update(status="all seven jobs passed", cacheArtifactQualification="accepted exact Rust1.99.1 host fixture", cacheAcceptance=PREFIX + "cache-deadline-ci-acceptance.json", hostedJavaAcceptance=PREFIX + "generated-java-hosted-acceptance.json")
        c["signatureCorrection"].update(state="accepted and executed in successful hosted bootstrap at25ac", hostedExecution=True, actualAcceptance=PREFIX + "generated-java-hosted-acceptance.json")
        c["cacheDeadlineCorrection"].update(state="accepted exact new hosted fixture at25ac; local EPERM hold remains", fixtureExecuted=True, actualAcceptance=PREFIX + "cache-deadline-ci-acceptance.json", localCustodyHoldCleared=False)
        c["pair9CandidateR2"].update(state="delivered; independent source/local artifacts accepted; all seven ordinary CI jobs passed", deliveryAndOrdinaryCI="delivered; all seven jobs passed", finalJobs=PREFIX + "pair9-r2-delivery/ci-discovery/final-jobs.json", hostedArtifactReview="active; no hosted artifact verdict yet")
        c["nativeControllerPreparation"] = {"status": "stopped before runtime; four controller admission defects; repair active", "nativeAttempts": 0, "receipt": PREFIX + "android-motion-r2-controller-admission/result.json", "productChanged": False, "nativeAccepted": False}
    if name == "work-graph.json":
        for item in data[key]:
            if item["id"] == "W04":
                item["currentCheckpoint"] = "Accepted retained Settings transport passes on iOS26.5; original firstTab fails actualNativeFocusTraversal with19otherpredicatespassing. Keyboard experiment stopped on AX-25211 before XCTest; cleanup mistakenly stopped two protected devices, subsequently restored Booted by root with user authorization. Incident remains failed; one attempt remains. Safe controller/Accessibility preflight active; native testing explicitly resumed."
            if item["id"] == "W13":
                item["currentCheckpoint"] = "Existing ASC build-status CLI implemented in isolation;8hostgroups passed. Independent review reproduced one P2 durable credential reflection; correction active. Not integrated;103inputclosure rebind andfreshconsumers pending. LiveASC/fullstore/D6 unqualified."
                item.setdefault("evidence", []).append(PREFIX + "store-status-review/REPORT.md")
    path.write_text(json.dumps(data, indent=2) + "\n")
    changed.append(name)
(OUT / "tracking-before.json").write_text(json.dumps(snapshots, indent=2) + "\n")
(OUT / "tracking-receipt.json").write_text(json.dumps({"schema": 1, "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), "historicalSectionsUnchanged": True, "changed": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in changed}, "gatesPromoted": []}, indent=2) + "\n")
print(json.dumps({"updated": changed, "gaPromoted": False}))
