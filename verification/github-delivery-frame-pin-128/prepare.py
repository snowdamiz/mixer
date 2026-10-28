"""Pure root-selection binding and metadata update; no compiler or runtime."""
import hashlib
import json
from pathlib import Path
import platform
from owned import OUT, ROOT, now, row, save

BASE = "5efcb6a2bcf3b076c9a4452926a842209302e56b"
TREE = "18f204207b0c7dd8f331e0cd947c10b41a663770"
PACKETS = {
    "swift-frame-pin-admission-candidate": "c5d0e8b29625e09bc5bc6ef73094edc4aebdc03ee5d4e27cafa34b5eda05bd6a",
    "swift-frame-pin-admission-independent": "e14f93bccb9ac5908b7707820456d4c2bab337aef53fc4be105e5285794b8c5f",
}
PROTECTED = {
    ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
    "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
assert not (OUT / "selection.json").exists(), "one preparation only"
verified = []
for lane, expected in PACKETS.items():
    directory = ROOT / "verification" / lane
    seal = row(directory / "seal.json")
    assert seal["sha256"] == expected, lane
    packet = json.loads((directory / "seal.json").read_bytes())
    names = packet["files"]
    assert isinstance(names, dict)
    for name, value in names.items():
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        actual = row(directory / name)
        assert {k: actual[k] for k in ("bytes", "sha256")} == value, name
    verified.append({"lane": lane, "sealSHA256": expected, "files": len(names),
                     "bytes": sum(v["bytes"] for v in names.values())})
for name, digest in PROTECTED.items():
    assert row(ROOT / name)["sha256"] == digest
prior = ROOT / "verification/github-delivery-architecture-comparison/ci-review/seal.json"
assert row(prior)["sha256"] == "6965fd62339bedddc735068068fead314abd79dea56ee466b06cccb565b0cea4"
save("prior-comparison-summary.json", {
    "schema": 1, "at": now(), "scope": "sanitized summary of sealed actual independent review; raw archive and logs remain local",
    "reviewSeal": row(prior), "run": 40768719255, "head": "dfd0e3196543cc1749c9cc924cc7accf28c9dc25",
    "closedFullAttempts": 2, "attemptsRemaining": 0, "bothFailures": {"kind": "FrameLimit", "attempted": 65, "limit": 64,
        "function": 24126, "offset": 4394310, "phase": "corpus_1"},
    "completeOriginalObservations": 0, "corpus2Started": False,
    "all11CommandsClosed": True, "allFinalOwnerLedgersZero": True, "scratchRemoved": True,
    "matchedPrefixDenseElapsedReduction": "approximately 12 percent in one sample; no production winner or full-workload feasibility accepted",
    "failureBaselinePreserved": True, "compiledOrRuntimeAcceptanceForNewProfile": False,
})
source = ROOT / "verification/swift-frame-pin-admission-candidate/workflow.yml"
target = ROOT / ".github/workflows/swift-frame-pin-admission.yml"
assert not target.exists(), "do not overwrite an installed workflow"
target.write_bytes(source.read_bytes())
before = [row(ROOT / p) for p in METADATA]
selection = {
    "schema": 1, "at": now(), "basisRevision": BASE, "basisTree": TREE,
    "rootAuthorization": "Root explicitly selects paired-128-v1 for ONE bounded remote frame/pin comparison; delegated delivery and one manual dispatch",
    "profile": "paired-128-v1", "workflow": row(target), "workflowCopiedByteIdentical": row(source)["sha256"] == row(target)["sha256"],
    "verifiedPackets": verified, "priorActualComparison": row(OUT / "prior-comparison-summary.json"),
    "sourceClosures": {"control": "92e2f54a8b31116d1ba3a0ae77f3b8b7abf901ab0ec07b40feef2ecd49c1dcd1",
                       "dense": "e3a4a90378a90d8cc5d22244c5ae345d30e57670cc396098c4370872a9a2284b"},
    "limits": {"frames": 128, "activePins": 128, "residents": 256, "denseBitmapWordsU64": 2,
        "combinedBytes": 268435456, "instructionFuel": 1000000000, "executionWork": 8000000000,
        "cacheWork": 768000000, "cumulativeRuntimeAndWasiMilliseconds": 600000,
        "maxFullAttempts": 2, "maxCommands": 11, "aggregateSeconds": 2700},
    "admission": {"optimizedRust": "1.99.0", "controlFiniteTests": 9, "denseFiniteTests": 10,
        "bothBuildsFiniteGeometryAndHarnessBeforeAnyFull": True,
        "compiledConservativeBoundsAndActualPeaksMustFitUnchangedCombinedLimit": True,
        "zeroConsumingCleanupRequired": True, "originalTwoCorpus11FieldOracleUnchanged": True},
    "sourceEvidence": {"producerStructuralArithmeticChecks": 152, "producerPureMethods": 39,
        "independentBindingWorkflowChecks": 117, "independentBitmapCases": 11716,
        "independentRunnerCases": 293, "killedMutationWitnesses": 3, "replayedProducerMethods": 39},
    "newActualCompilations": 0, "newActualFiniteRuns": 0, "newActualFullAttempts": 0,
    "dispatchesAuthorized": 1, "retryResumeOrDefaultPromotionSelected": False,
    "feasibilityAccepted": False, "productionDefaultsChanged": False, "GA_accepted": False,
    "protectedDirtyPathsExcluded": PROTECTED, "wranglerUntouched": True,
    "nativeUICaptureAndLocalCompilerRuntimeInventoryHeldProbes": False,
    "holdsUnchanged": [20745,20770,20780,20817,20842,20851,20866,"Unit A","broad hosted","local FieldLog compiler custody","native/UI/capture","disconnected physical phones"],
}
save("selection.json", selection)
paragraph = """## Selected bounded frame and pin comparison

Root selects `paired-128-v1` for one remote comparison after independent Astra
source review: 152 producer structural/arithmetic checks, 39 pure runner methods,
117 independent binding/workflow checks, 11,716 bitmap cases, 293 runner cases,
three mutation witnesses and 39 replayed methods pass. The exact reviewed workflow
is installed unchanged. Both Rust 1.99.0 optimized builds, nine/ten finite tests,
compiled geometry, zero cleanup and original harness controls must pass before
either full attempt. The cap is two full attempts, eleven commands and 2,700
seconds. Both arms use 128 frames/pins, 256 residents, the unchanged 256 MiB
combined envelope, 1B fuel, 8B execution credits, 768M cache credits and 600,000ms
cumulative Runtime/WASI duration; dense uses two u64 bitmap words. Compilation
and all new actual runtime behavior remain pending. No retry, resume, production
default promotion or GA acceptance is selected.

The previous comparison `40768719255` is closed: both arms failed at FrameLimit
65/64 in Corpus 1, with no full original observation or Corpus 2. All eleven
commands closed and final owner ledgers reached zero. Its matched-prefix dense
elapsed reduction is one diagnostic sample, not a production winner. The failed
baseline remains preserved. [Selection](verification/github-delivery-frame-pin-128/selection.json)
binds both reviewed packets, source closures, finite admission and one-dispatch
authority. Gates remain 8 running, 30 planned, 0 verified; all native/UI/capture,
physical-phone, local custody and Unit A holds remain.

"""
plan = (ROOT / "PLAN.md").read_text()
marker = "## Selected fixture format-only source amendment"
assert marker in plan
(ROOT / "PLAN.md").write_text(plan.replace(marker, paragraph + "## Historical selected fixture format-only source amendment", 1))
status = (ROOT / "STATUS.md").read_text()
assert status.startswith("# Implementation status\n\n")
(ROOT / "STATUS.md").write_text(status.replace("# Implementation status\n\n", "# Implementation status\n\n" + paragraph, 1))
w = json.loads((ROOT / "work-graph.json").read_text())
g = json.loads((ROOT / "gates/ga.json").read_text())
checkpoint = {"schema": 1, "at": now(), "status": "selected-reviewed-paired-128-v1-delivery-and-one-dispatch; actual compilation and runtime pending",
              "selection": row(OUT / "selection.json"), "limits": selection["limits"], "admission": selection["admission"],
              "sourceEvidence": selection["sourceEvidence"], "actualCompilations": 0, "actualFiniteRuns": 0,
              "actualFullAttempts": 0, "productionDefaultsChanged": False, "GA_accepted": False, "holdsUnchanged": True}
for parent in (w["packages"][7], g["gates"][1]):
    assert parent["id"] in ("W08", "G02")
    arch = parent["empiricalCacheDeadlineCampaign"]["architecture_comparison"]
    arch["status"] = "closed diagnostic comparison; both FrameLimit65/64 before complete Corpus1; Corpus2 unrun"
    arch["actual_full_attempts"] = 2
    arch["actual_full_attempt_count_observed"] = True
    arch["compiled_or_runtime_acceptance"] = False
    arch["all11_commands_closed_and_final_owner_ledgers_zero"] = True
    arch["actual_review_seal"] = row(prior)
    arch["sanitized_actual_summary"] = row(OUT / "prior-comparison-summary.json")
    arch["retry_or_default_promotion_selected"] = False
    arch["paired_frame_pin_128"] = checkpoint
assert [sum(x["status"] == s for x in g["gates"]) for s in ("running", "planned", "verified")] == [8,30,0]
for name, value in (("work-graph.json", w), ("gates/ga.json", g)):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
save("metadata-checkpoint.json", {"schema": 1, "at": now(), "command": "python3 -B verification/github-delivery-frame-pin-128/prepare.py",
     "python": platform.python_version(), "sourceRevision": BASE, "sourceTree": TREE,
     "before": before, "after": [row(ROOT / p) for p in METADATA], "gateCounts": {"running": 8, "planned": 30, "verified": 0},
     "scope": "Reviewed source selection and original closed diagnostic evidence; no compiler, runtime, process inventory or dispatch"})
print(json.dumps({"selected": selection["profile"], "packets": verified, "workflowSHA256": selection["workflow"]["sha256"], "runtimePending": True}))
