#!/usr/bin/env python3
"""Bind an independent static design review; never compile or run a guest."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DESIGN = "docs/swift-reactor-execution-stage-design.md"
DESIGN_EVIDENCE = "verification/swift-reactor-execution-design"
CANONICAL = "verification/swift-reactor-validation/2026-10-23-final-v2/receipt.json"
REFERENCE = "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/receipt.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def file_record(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}


def command(label: str, argv: list[str]) -> dict:
    completed = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
    stdout, stderr = OUT / f"{label}.stdout", OUT / f"{label}.stderr"
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    binary = Path(shutil.which(argv[0]) or argv[0]).resolve()
    return {
        "argv": argv,
        "executable": {"resolvedPath": str(binary), "bytes": binary.stat().st_size, "sha256": sha(binary)},
        "exitCode": completed.returncode,
        "stdout": {"path": stdout.name, "bytes": stdout.stat().st_size, "sha256": sha(stdout)},
        "stderr": {"path": stderr.name, "bytes": stderr.stat().st_size, "sha256": sha(stderr)},
    }


def main() -> None:
    commands = [
        command("revision-before", ["git", "rev-parse", "HEAD"]),
        command("dirty-tree", ["git", "status", "--short"]),
        command("git-version", ["git", "--version"]),
        command("python-version", [sys.executable, "--version"]),
        command("rg-version", ["rg", "--version"]),
        command("rustc-version", ["/opt/homebrew/opt/rustup/bin/rustc", "--version", "--verbose"]),
        command("cargo-version", ["/opt/homebrew/opt/rustup/bin/cargo", "--version"]),
    ]
    assert all(item["exitCode"] == 0 for item in commands)
    inputs = [
        "AGENTS.md", "mixer-product-plan.md", "PLAN.md", DESIGN,
        "docs/swift-reactor-validation-stage-design.md",
        "docs/span-execution-design.md", "docs/swift-wasi-adapter-design.md",
        "vm/Cargo.toml", "vm/Cargo.lock", "vm/src/lib.rs", "vm/src/execute.rs",
        "vm/src/experimental/mod.rs", "vm/src/experimental/account.rs",
        "vm/src/experimental/metadata.rs", "vm/src/experimental/policy.rs",
        "vm/src/experimental/reader.rs", "vm/src/experimental/validate.rs",
        "vm/src/experimental/descriptors.rs", "vm/src/experimental/swift.rs",
        "vm/src/experimental_swift_reactor/mod.rs",
        "vm/src/experimental/cache/mod.rs", "vm/src/experimental/cache/decode.rs",
        "vm/src/experimental/execution/mod.rs", "vm/src/experimental_wasi/mod.rs",
        "vm/src/experimental_wasi/descriptor.rs", "vm/src/experimental_wasi/platform.rs",
        f"{DESIGN_EVIDENCE}/review.md", f"{DESIGN_EVIDENCE}/receipt.json",
        f"{DESIGN_EVIDENCE}/source-manifest.json",
        f"{DESIGN_EVIDENCE}/proposal-before-root-refinements.md", CANONICAL, REFERENCE,
        "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json",
        str((OUT / "review.md").relative_to(ROOT)),
        str(Path(__file__).resolve().relative_to(ROOT)),
    ]
    manifest = [file_record(ROOT / item) for item in sorted(set(inputs))]
    save(OUT / "source-manifest.json", manifest)
    current = {item["path"]: item for item in manifest}
    canonical = json.loads((ROOT / CANONICAL).read_text())
    reference = json.loads((ROOT / REFERENCE).read_text())
    prior = json.loads((ROOT / DESIGN_EVIDENCE / "receipt.json").read_text())
    prior_manifest_path = ROOT / DESIGN_EVIDENCE / prior["sourceManifest"]["path"]
    assert sha(prior_manifest_path) == prior["sourceManifest"]["sha256"]
    prior_manifest = {item["path"]: item for item in json.loads(prior_manifest_path.read_text())}
    historical_proposal = current[f"{DESIGN_EVIDENCE}/proposal-before-root-refinements.md"]
    assert historical_proposal["sha256"] == prior_manifest[DESIGN]["sha256"]
    prior_comparisons = [
        {"path": path, "matchesDesignEvidenceSource": item["sha256"] == prior_manifest[path]["sha256"]}
        for path, item in current.items() if path in prior_manifest
    ]
    canonical_sources = {item["path"]: item["sha256"] for item in canonical["sources"]}
    canonical_comparisons = [
        {"path": path, "matchesCanonicalValidationSource": item["sha256"] == canonical_sources[path]}
        for path, item in current.items() if path in canonical_sources
    ]
    artifact = Path(canonical["artifact"]["path"])
    artifact_record = file_record(artifact)
    assert artifact_record["bytes"] == 53_777_114
    assert artifact_record["sha256"] == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    assert canonical["valid"] is True and canonical["executed"] is False
    expected = reference["expectedObservation"]
    assert len(expected) == 11
    text = (ROOT / DESIGN).read_text()
    refinement_anchors = {
        "oneOwnerPerMeter": "`WasiContext` counters remain the sole authoritative WASI call/work/transfer/log",
        "privateCheckedDispatch": "Swift runtime's private dispatch wrapper checks the shared control before and",
        "finiteTicketInventory": "inventory is at most 86 authoritative tickets",
        "noGrowingRegistry": "there is no allocated or growing ticket registry",
        "aggregateEntryOwnership": "Each decoded-entry ticket covers its three vectors",
    }
    # These are document binding checks only, not proof of executable enforcement.
    normalized_text = " ".join(text.split())
    anchors = {key: anchor in normalized_text for key, anchor in refinement_anchors.items()}
    assert all(anchors.values())
    assert 2 + 3 + 64 + 6 + 1 + 4 + 1 + 4 + 1 == 86
    commands.append(command("revision-after", ["git", "rev-parse", "HEAD"]))
    stable = all(sha(ROOT / item["path"]) == item["sha256"] for item in manifest)
    revision_before = (OUT / "revision-before.stdout").read_text().strip()
    revision_after = (OUT / "revision-after.stdout").read_text().strip()
    assert stable and revision_before == revision_after
    receipt = {
        "schema": "mixer.swift-reactor-execution-design-review.v1",
        "observedUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "Independent static design/source review only; no build, engine test, validation or guest execution",
        "collectorCommand": [sys.executable, str(Path(__file__).resolve())],
        "pythonVersion": platform.python_version(),
        "priorCollectorAttempts": [{
            "exitCode": 1,
            "reason": "Document-only anchor check initially treated a Markdown line wrap as a mismatch; collector now normalizes whitespace. No engine or source failure.",
            "stdout": file_record(OUT / "collection-attempt1.stdout"),
            "stderr": file_record(OUT / "collection-attempt1.stderr"),
        }],
        "revision": revision_before,
        "sourceBinding": "Explicit dirty-tree file manifest; revision alone does not bind uncommitted source",
        "sourceManifest": {"path": "source-manifest.json", "files": len(manifest), "sha256": sha(OUT / "source-manifest.json")},
        "review": file_record(OUT / "review.md"),
        "reviewedDesign": current[DESIGN],
        "designEvidenceReceipt": current[f"{DESIGN_EVIDENCE}/receipt.json"],
        "historicalProposal": historical_proposal,
        "historicalProposalMatchesOriginalDesignManifest": True,
        "designEvidenceSourceComparisons": prior_comparisons,
        "canonicalValidationSourceComparisons": canonical_comparisons,
        "canonicalValidationReceipt": current[CANONICAL],
        "quotedPriorValidation": {
            "valid": canonical["valid"], "executed": canonical["executed"],
            "scope": "Historical complete-validation observations; this review did not rerun validation",
            "observations": canonical["validation"],
        },
        "artifact": artifact_record,
        "artifactReadScope": "SHA-256/length only; not parsed, instantiated, initialized or invoked",
        "expectedNativeObservations": expected,
        "resolvedFindings": [
            {"id": "R1", "topic": "Sole WASI meters with private checked dispatch and carried deadline", "status": "resolved in revised design"},
            {"id": "R2", "topic": "Finite inline aggregate ticket inventory", "status": "resolved in revised design", "maxAuthoritativeTickets": 86},
        ],
        "outstandingActionableDesignFindings": [],
        "recommendation": "accept design for root-coordinated bounded implementation",
        "implementationAcceptance": False,
        "targetExecutionApproved": False,
        "targetExecuted": False,
        "testsRun": [],
        "runtimeAllocationOrLayoutMeasurements": [],
        "deviceOperations": [],
        "commitsOrPushes": [],
        "commands": commands,
        "bindingChecks": {
            "inputsStableDuringCollection": stable,
            "revisionStableDuringCollection": revision_before == revision_after,
            "designEvidenceManifestHashValid": True,
            "canonicalValidationOnly": True,
            "exactArtifactHashOnly": True,
            "observationCount": len(expected),
            "reviewRefinementDocumentAnchors": anchors,
            "allReadOnlyCommandsSucceeded": all(item["exitCode"] == 0 for item in commands),
        },
        "pending": [
            "root design acceptance and private seam freeze", "bounded independent implementation",
            "original synthetic execution and fault tests", "frozen-route and all-feature regressions",
            "allocator/layout/cancellation-backing evidence", "root approval for one exact-target attempt",
            "published independent FieldLog consumer", "artifact size and performance qualification",
            "physical iOS", "physical Android", "store/customer/operational/GA review",
        ],
    }
    save(OUT / "receipt.json", receipt)
    print(json.dumps({
        "staticDesignReviewOnly": True, "recommendation": receipt["recommendation"],
        "sourceFiles": len(manifest), "resolvedFindings": ["R1", "R2"],
        "outstandingFindings": [], "targetExecuted": False,
        "priorDesignEvidenceDrift": [item["path"] for item in prior_comparisons if not item["matchesDesignEvidenceSource"]],
        "canonicalValidationSourceDrift": [item["path"] for item in canonical_comparisons if not item["matchesCanonicalValidationSource"]],
    }, indent=2))


if __name__ == "__main__":
    main()
