#!/usr/bin/env python3
"""Bind a design-only source inspection. Never load or execute a Wasm module."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOC = ROOT / "docs/swift-reactor-execution-stage-design.md"
CANONICAL = ROOT / "verification/swift-reactor-validation/2026-10-23-final-v2/receipt.json"
REFERENCE = ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/receipt.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def command(label: str, argv: list[str]) -> dict:
    run = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
    stdout = OUT / f"{label}.stdout"
    stderr = OUT / f"{label}.stderr"
    stdout.write_bytes(run.stdout)
    stderr.write_bytes(run.stderr)
    return {
        "argv": argv,
        "exitCode": run.returncode,
        "stdout": {"path": stdout.name, "sha256": digest(stdout)},
        "stderr": {"path": stderr.name, "sha256": digest(stderr)},
    }


def main() -> None:
    commands = [
        command("revision", ["git", "rev-parse", "HEAD"]),
        command("dirty-tree", ["git", "status", "--short"]),
        command("python-version", [sys.executable, "--version"]),
        command("rustc-version", ["/opt/homebrew/opt/rustup/bin/rustc", "--version"]),
        command("cargo-version", ["/opt/homebrew/opt/rustup/bin/cargo", "--version"]),
    ]
    if any(item["exitCode"] != 0 for item in commands):
        raise SystemExit("A read-only tool/version command failed; inspect retained output")
    inputs = [
        ROOT / "AGENTS.md",
        ROOT / "mixer-product-plan.md",
        ROOT / "PLAN.md",
        ROOT / "docs/swift-reactor-validation-stage-design.md",
        ROOT / "docs/swift-reactor-owned-profile-design.md",
        ROOT / "docs/span-execution-design.md",
        ROOT / "docs/swift-wasi-adapter-design.md",
        ROOT / "docs/swift-guest-execution-next.md",
        ROOT / "verification/swift-profile-design-review/review.md",
        ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json",
        CANONICAL,
        REFERENCE,
        ROOT / "vm/Cargo.toml",
        ROOT / "vm/Cargo.lock",
        DOC,
        OUT / "review.md",
        Path(__file__).resolve(),
    ]
    inputs += list((ROOT / "vm/src").rglob("*.rs"))
    manifest = [
        {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)}
        for path in sorted(set(inputs))
    ]
    save_json(OUT / "source-manifest.json", manifest)
    canonical = json.loads(CANONICAL.read_text())
    reference = json.loads(REFERENCE.read_text())
    target = Path(canonical["artifact"]["path"])
    actual_target = {"path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size, "sha256": digest(target)}
    assert actual_target["bytes"] == 53_777_114
    assert actual_target["sha256"] == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    assert canonical["valid"] is True and canonical["executed"] is False
    validation = canonical["validation"]
    assert validation["defined_functions"] == validation["validated_bodies"] == 79_832
    assert validation["work_used"] == 188_428_924
    assert validation["internal_total_peak_reserved"] == 54_827_522
    assert len(reference["expectedObservation"]) == 11
    old_sources = {item["path"]: item["sha256"] for item in canonical["sources"]}
    comparisons = [
        {"path": item["path"], "matchesCanonicalValidationSource": item["sha256"] == old_sources[item["path"]]}
        for item in manifest
        if item["path"] in old_sources
    ]
    stable = all(digest(ROOT / item["path"]) == item["sha256"] for item in manifest)
    document = DOC.read_text()
    checks = {
        "inputsStableDuringCollection": stable,
        "canonicalValidationOnly": True,
        "exactArtifactHashCheckedWithoutExecution": True,
        "referenceObservationCount": len(reference["expectedObservation"]),
        "markdownFenceCountEven": document.count("```") % 2 == 0,
        "allReadOnlyCommandsSucceeded": True,
    }
    assert checks["inputsStableDuringCollection"]
    assert checks["markdownFenceCountEven"]
    save_json(OUT / "receipt.json", {
        "schema": "mixer.swift-reactor-execution-design.v1",
        "observedUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only source inspection and proposed execution-stage design; no engine implementation or guest execution",
        "collectorCommand": [sys.executable, str(Path(__file__).resolve())],
        "pythonVersion": platform.python_version(),
        "revision": (OUT / "revision.stdout").read_text().strip(),
        "sourceBinding": "Current dirty-tree file hashes; revision alone is not source provenance",
        "sourceManifest": {"path": "source-manifest.json", "sha256": digest(OUT / "source-manifest.json"), "files": len(manifest)},
        "artifact": actual_target,
        "canonicalValidationReceipt": {"path": str(CANONICAL.relative_to(ROOT)), "sha256": digest(CANONICAL)},
        "canonicalSourceComparisons": comparisons,
        "priorValidationObservations": validation,
        "expectedObservationReference": reference["expectedObservation"],
        "commands": commands,
        "checks": checks,
        "implementationApproved": False,
        "targetExecutionApproved": False,
        "targetExecutedByThisCollector": False,
        "testsRunByThisCollector": [],
        "accountingScope": "Design review only; prior validation reservations are quoted with their original scope; no runtime reservation, allocator or RSS measurement",
        "pending": ["root design acceptance", "private seam implementation", "synthetic execution and fault tests", "frozen-route regressions", "root-approved exact-target attempt", "published independent FieldLog consumer", "physical iOS", "physical Android", "GA review"],
    })
    print(json.dumps({"designOnly": True, "targetExecuted": False, "checks": checks, "manifestFiles": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()
