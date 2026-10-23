#!/usr/bin/env python3
"""Read-only fact binding for a proposal; never validates or executes Wasm."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent / "proposal-inputs.json"
TARGET=ROOT / "compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm"
DIAGNOSTICS=ROOT / "verification/swift-reactor-function-diagnostics/2026-10-23-reactor-final-v2"


def sha(path):
    value=hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    assert TARGET.stat().st_size==53_777_114
    assert sha(TARGET)=="24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    receipt=json.loads((DIAGNOSTICS / "receipt.json").read_text())
    stats=json.loads((DIAGNOSTICS / "statistics.json").read_text())
    assert receipt["artifact"]["sha256"]==sha(TARGET)
    assert receipt["valid"] is False and stats["valid"] is False
    descriptors=json.loads((ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json").read_text())
    assert len(descriptors["imports"])==34 and descriptors["functionCount"]==79_866
    assert receipt["observed"]["functions"]+len(descriptors["imports"])==descriptors["functionCount"]
    assert stats["raw_maximum_block_nesting"]+1==379
    paths=[ROOT / "docs/swift-reactor-owned-profile-design.md",ROOT / "docs/span-execution-design.md",
           ROOT / "docs/swift-wasi-adapter-design.md",ROOT / "docs/swift-guest-execution-next.md",
           DIAGNOSTICS / "receipt.json",DIAGNOSTICS / "statistics.json",DIAGNOSTICS / "functions.csv.gz",
           ROOT / "verification/swift-reactor-function-diagnostics/audit.json",
           ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json",
           ROOT / "verification/swift-wasi/evidence/2026-10-23/receipt.json",
           ROOT / "verification/next-slice-review/wasi-receipt.json",Path(__file__).resolve()]
    paths+=sorted((ROOT / "vm/src/experimental").rglob("*.rs"))
    paths+=sorted((ROOT / "vm/src/experimental_wasi").rglob("*.rs"))
    manifest=[{"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths]
    result={"status":"proposal-input-binding-only","authorization":False,"valid":False,
            "scope":"Existing target/diagnostic/source facts plus proposed arithmetic; no new complete validation, profile implementation, owned execution, device run, publication or GA approval",
            "observedUtc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "command":[sys.executable,"-B",str(Path(__file__).resolve())],"python":sys.version,
            "revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "dirtyTree":subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True),
            "artifact":{"path":str(TARGET.relative_to(ROOT)),"bytes":TARGET.stat().st_size,"sha256":sha(TARGET)},
            "facts":{"definedFunctions":stats["function_count"],"totalFunctions":descriptors["functionCount"],
                     "imports":len(descriptors["imports"]),"instructions":stats["raw_instruction_count"],
                     "nestedBlocks":stats["raw_maximum_block_nesting"],"functionInclusiveControlsFloor":379,
                     "abstractOperandHeight":stats["static_maximum_operand_height"],
                     "maximumParametersPlusLocals":stats["static_maximum_parameters_plus_locals"],
                     "rejectedAbsoluteFunctions":[r["function"] for r in stats["rejections"]],
                     "observedResources":receipt["resources"]},
            "arithmetic":{"initialMemoryBytes":584*65536,"referenceSecondCallMemoryBytes":626*65536,
                          "proposedHostMemoryBytes":768*65536,"proposedMemoryGrowthOldNewUpperBytes":2*768*65536,
                          "currentValidationSourceAndSectionWorkLowerBound":107_554_182,
                          "proposedAggregateVMBytes":256*1024*1024},
            "sourceManifest":manifest,
            "sourceManifestDigest":hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"authorization":False,"valid":False,
                      "sourceManifestDigest":result["sourceManifestDigest"],"facts":result["facts"]},indent=2))


if __name__=="__main__":
    main()
