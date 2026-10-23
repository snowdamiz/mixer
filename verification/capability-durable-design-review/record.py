#!/usr/bin/env python3
"""Record bounded design-inspection evidence; performs no product mutation or execution."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEFORE = "9d4bcd887c67a115f774220e52dd250ac41a9a3ece1e6a52f7e9c9be7722e205"
AFTER = "f5a8c7bf2ae7f597da56061870a926181ae3a8ecfe877d70033bb0787d37f08b"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)


def main():
    material_receipt = ROOT / "verification/capability-installed-material/2026-10-23-candidate-2/receipt.json"
    raw = material_receipt.read_bytes()
    require(sha(raw) == "0c3b8df6a04fabda6ad0f8301832d7679dc216c1a5a4bf23983ebb332f29db31", "frozen material/dependency receipt")
    material = json.loads(raw); export = Path(material["immutable_source_export"])
    selected = [
        "contracts/activation-v2.json", "contracts/capability-execution-v1.json", "contracts/release-v3.json", "contracts/runtime-identity-v2.json",
        "capability-activation/Sources/MixerCapabilityActivation/InstalledCapabilityExecution.swift",
        "updates/Sources/MixerUpdates/VerifierV3.swift", "updates/Sources/MixerUpdates/Verifier.swift",
        "updates/Sources/MixerUpdates/ColdStartUpdater.swift", "updates/Sources/MixerUpdates/ColdStartModels.swift",
        "updates/Sources/MixerUpdates/DurableDirectory.swift", "updates/Sources/MixerDurableIO/lock.c",
        "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Session.swift",
        "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Ownership.swift",
        "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Validation.swift",
        "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Types.swift",
        "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Failure.swift",
        "sdk/Sources/MixerCapabilities/Host.swift", "sdk/Sources/MixerCapabilities/InstalledCapabilityAdapters.swift",
        "sdk/Sources/MixerCapabilities/AppPrivateKeyValueStore.swift", "sdk/Sources/MixerCapabilities/URLSessionHTTPTransport.swift",
        "sdk/Sources/MixerCapabilities/CapabilityExitLease.swift",
    ]
    sources = {}
    for relative in selected:
        path = export / relative; digest = sha(path.read_bytes())
        require(digest == material["source_files"][relative], "frozen source " + relative)
        sources[relative] = dict(sha256=digest, inspected_bytes=str(path))
    # The old coordinator was read from the live tree, with an exact unchanged
    # baseline check; the actively edited V3 SPI source is deliberately excluded.
    old_coordinator = "activation/Sources/MixerActivation/ColdStartRuntime.swift"
    baseline = subprocess.check_output(["git", "show", "1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636:" + old_coordinator], cwd=ROOT)
    require((ROOT / old_coordinator).read_bytes() == baseline, "old coordinator baseline")
    sources[old_coordinator] = dict(sha256=sha(baseline), inspected_bytes=str(ROOT / old_coordinator))
    require(sha((HERE / "design-before.md").read_bytes()) == BEFORE, "before design pin")
    require(sha((HERE / "design-after.md").read_bytes()) == AFTER, "after design pin")
    require(sha((ROOT / "docs/capability-durable-updater-api-design.md").read_bytes()) == AFTER, "owner design pin")
    corrected = (HERE / "design-after.md").read_bytes()
    start = corrected.index(b"Terminal failure observation is separate from retirement.")
    end = corrected.index(b"`CapabilityRecoveryConfiguration`", start)
    require(sha(corrected[:start] + corrected[end:]) == BEFORE, "only approved correction")
    metadata = dict(schema=1, result="architecture approved after one root-authorized design correction; no executable qualification",
        observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), model="gpt-6.1-sol", reasoning_effort="xhigh",
        command=[sys.executable, str(Path(__file__).resolve())], python=platform.python_version(),
        head_at_record=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        scope="Read-only independent architecture review, plus only the root-authorized terminal-observer draft addition; no product implementation, device, commit or push",
        design_before_sha256=BEFORE, design_after_sha256=AFTER,
        frozen_material_dependency_receipt=dict(path=str(material_receipt.relative_to(ROOT)), sha256=sha(raw), source_manifest_sha256=material["source_manifest_sha256"]),
        inspected_sources=sources, source_count=len(sources),
        findings=[dict(id="D1", status="corrected in proposal only", severity="required before coordinator implementation",
            trigger="Asynchronous post-enable/after-health wake or bridge failure with hung/quarantined actual exits",
            issue="Final drain cannot notify terminal failure when drain may never occur; current bridge failure is diagnostic status only",
            correction="Attempt-bound synchronous checked first-failure latch before any worker, coalesced counted actor notification, enable/health/post-await gates, truthful in-flight commit outcomes, no reservation release before exact retirement")],
        metadata_spi_assessment="Approved distinct offer/retained opaque types with same private verifier context and no external coordinator ingress; no stop/change issue for isolated SPI implementation",
        limitations=["Design review only; no build, test or native execution performed", "Current source exports do not yet supply proposed terminal observer, exclusive adapter-close ownership or durable V3 coordinator", "Future qualification must test original race/fault/authority cases, not treat prose or source analysis as OTA authorization", "No physical mobile, complete graph/final binary attestation, actual health, publication or GA evidence"])
    inputs = dict(sources)
    for path in [HERE / "README.md", HERE / "design-before.md", HERE / "design-after.md", Path(__file__).resolve()]:
        inputs[path.relative_to(ROOT).as_posix()] = dict(sha256=sha(path.read_bytes()), inspected_bytes=str(path))
    encoded = "".join(record["sha256"] + "  " + path + "\n" for path, record in sorted(inputs.items())).encode()
    (HERE / "source-manifest.sha256").write_bytes(encoded)
    metadata["source_manifest_sha256"] = sha(encoded)
    target = HERE / "receipt.json"; target.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(dict(result=metadata["result"], sources=len(sources), design_after_sha256=AFTER, manifest_sha256=sha(encoded), receipt_sha256=sha(target.read_bytes()))))


if __name__ == "__main__": main()
