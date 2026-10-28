"""Add the root-supplied sealed, sanitized current CI summary before delivery."""
import json
from owned import OUT, ROOT, now, row, save

source = ROOT / "verification/github-delivery-fixture-format/ci-review"
expected = {"public-summary-candidate.json": "42226a54762ffd0d6a4fe596bc043dd7fa3c022469f7f97c52daa2f9b974f4b0",
            "public-summary-seal.json": "27a65c100da1653b604ad058972738423606dfb4ed9e30b03d864e7559cfa60f"}
assert not (OUT / "current-observations.json").exists()
for name, digest in expected.items():
    assert row(source / name)["sha256"] == digest
    assert not (OUT / name).exists()
    (OUT / name).write_bytes((source / name).read_bytes())
summary = json.loads((OUT / "public-summary-candidate.json").read_bytes())
assert summary["source_revision"] == "5efcb6a2bcf3b076c9a4452926a842209302e56b"
assert summary["engine"]["successful"] == summary["engine"]["total"] == 6
assert summary["network"]["product_tests"]["passed"] == 2 and summary["network"]["product_tests"]["skipped"] == 0
assert summary["phoenix"]["ordinary_suite"]["passed"] == 701 and summary["phoenix"]["ordinary_suite"]["skipped"] == 2
observation = {"schema": 1, "at": now(), "scope": "sealed sanitized current-source host CI review; raw643 files/51.5MB retained locally",
    "summary": row(OUT / "public-summary-candidate.json"), "summarySeal": row(OUT / "public-summary-seal.json"),
    "sourceRevision": summary["source_revision"], "sourceTree": summary["source_tree"],
    "engine": {"run": summary["engine"]["run_id"], "jobsSucceeded": 6, "jobsTotal": 6, "scope": summary["engine"]["metadata_only"]},
    "network": {"run": summary["network"]["run_id"], "passed": 2, "failed": 0, "skipped": 0, "pureCollectorControls": 141,
        "commandsVerified": 137, "metadataFilesVerified": 131, "sourceCount": 178,
        "sourceDigest": summary["source_review"]["formatted_v2_178_digest"], "finalBindingsAndAllThreeExactContainerCleanupVerified": True},
    "phoenix": {"run": summary["phoenix"]["run_id"], "formatAndCompilePassed": True, "total": 703, "passed": 701,
        "skipped": 2, "failed": 0, "fourNewTLSControlsPassed": True, "commandsVerified": 43, "PostgresAndScratchCleanupVerified": True},
    "FieldLog": {"latestRevisionPrefix": "146f2a27", "run": 40771309900, "fetchTimeoutSeconds": 180.084,
        "observedTests": 0, "failuresUnavailable": True, "all10RemoteGroupsCleaned": True,
        "transportCandidatePureMethods": 54, "independentReviewBlocker": "F1 --[no-] help-token parsing", "narrowCorrectionPending": True,
        "candidateDeliveredOrNewHostRun": False, "basis": "root handoff; FieldLog source and raw evidence excluded"},
    "nativeLocalCustodyUnitAAndGAHoldsUnchanged": True, "GA_accepted": False}
save("current-observations.json", observation)
paragraph = """Current baseline `5efcb6a2` CI is independently reviewed: all six Engine jobs
succeeded; ordinary Phoenix formatting/compilation and 701 methods pass, with
two expected network skips (703 total), including all four new TLS controls.
The isolated network lane passes 141 collector controls and both exact methods
without skips, with 137 commands, 131 metadata members, final source bindings
and all three exact container cleanups verified. Phoenix's 43 command hashes,
PostgreSQL stop and scratch removal are verified. Only the
[sanitized summary](verification/github-delivery-frame-pin-128/public-summary-candidate.json)
is delivered; raw CI remains local. FieldLog `146f2a27` still has no observed
host tests after its 180-second dependency fetch timeout; all ten remote groups
closed. The new transport candidate passed 54 pure methods, but independent
review found the `--[no-]` help-token parsing blocker; its narrow correction is
pending and no new host run is selected by this delivery.

"""
for name in ("PLAN.md", "STATUS.md"):
    path = ROOT / name
    text = path.read_text()
    marker = "## Selected bounded frame and pin comparison\n\n"
    assert text.count(marker) == 1
    path.write_text(text.replace(marker, marker + paragraph, 1))
w = json.loads((ROOT / "work-graph.json").read_text())
g = json.loads((ROOT / "gates/ga.json").read_text())
for parent in (w["packages"][13], g["gates"][21]):
    current = parent["identityProductionNetworkCI"]
    current["status"] = "exact formatted-v2 178-source network and Phoenix runtime qualified; existing holds and GA pending"
    current["current_formatted_source_runtime_pending"] = False
    current["latest_formatted_v2_CI"] = observation
for parent in (w["packages"][7], g["gates"][1]):
    parent["empiricalCacheDeadlineCampaign"]["architecture_comparison"]["paired_frame_pin_128"]["baselineCI"] = row(OUT / "current-observations.json")
w["packages"][16]["activePublicSDKFlow"]["latestTransportCandidateObservation"] = observation["FieldLog"]
assert [sum(x["status"] == status for x in g["gates"]) for status in ("running", "planned", "verified")] == [8,30,0]
for name, data in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
checkpoint = json.loads((OUT / "metadata-checkpoint.json").read_bytes())
checkpoint["currentObservation"] = row(OUT / "current-observations.json")
checkpoint["after"] = [row(ROOT / p) for p in ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")]
(OUT / "metadata-checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
print(json.dumps({"baselineCI": "all three workflows succeeded", "Engine": "6/6 jobs", "Phoenix": "701 passed,2 expected skips", "network": "2/2,no skips", "gateCounts": "8/30/0"}))
