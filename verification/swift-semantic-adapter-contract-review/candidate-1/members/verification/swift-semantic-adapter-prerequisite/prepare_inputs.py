"""Own-packet source snapshotter. Never imports or executes an input."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
INPUTS = [
    "AGENTS.md", "mixer-product-plan.md", "PLAN.md", "work-graph.json",
    "docs/swift-envelope-ci-acceptance.md",
    "docs/swift-ordered-retention-analyzer.md",
    "docs/swift-ordered-retention-analyzer-review.md",
    "docs/swift-ordered-retention-analyzer-fsm-contract.md",
    "docs/swift-ordered-retention-analyzer-fsm-contract-review.md",
    "docs/swift-envelope-absent-state-correction.md",
    "docs/swift-envelope-absent-state-accounting-review.md",
    "docs/swift-ordered-retention-analyzer-envelope-correction.md",
    "verification/swift-envelope-ci-pack/manifest.json",
    "verification/swift-envelope-ci-pack/source/library/analyzer.rs",
    "verification/swift-envelope-ci-pack/source/library/envelope.rs",
    "verification/swift-envelope-ci-pack/inventories/expected-api.json",
    "verification/swift-envelope-ci-pack/inventories/expected-host-layouts.json",
    "verification/swift-envelope-ci-pack/inventories/proposed-layout.json",
    "verification/swift-envelope-ci-pack/provenance/implementation-selection.json",
    "verification/swift-ordered-retention-analyzer-design/seal.json",
    "verification/swift-ordered-retention-analyzer-design/interface_schema.py",
    "verification/swift-ordered-retention-analyzer-design/commands/run-1/result.json",
    "verification/swift-ordered-retention-analyzer-design/commands/run-5/result.json",
    "verification/swift-ordered-retention-analyzer-design/inputs/candidate__src__experimental__cache__borrowed.rs",
    "verification/swift-ordered-retention-analyzer-design/inputs/candidate__src__experimental_swift_reactor__cache.rs",
    "verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__writer.rs",
    "verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__observer.rs",
    "verification/swift-ordered-retention-analyzer-design/inputs/verification__swift-ordered-retention-diagnostic-rust__source-code-table.json",
]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    manifest = BASE / "input-manifest.json"
    if manifest.exists():
        raise SystemExit("Refuse to overwrite the input freeze")
    rows = []
    for number, relative in enumerate(INPUTS):
        data = (ROOT / relative).read_bytes()
        if len(data) > 1_048_576:
            raise SystemExit("Declared source input exceeds 1 MiB: " + relative)
        snapshot = "inputs/%02d-%s" % (number, Path(relative).name)
        target = BASE / snapshot
        target.parent.mkdir(exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        rows.append({"path": relative, "snapshot": snapshot, "bytes": len(data),
                     "sha256": digest(data), "context_mutable": relative in
                     {"PLAN.md", "work-graph.json"}})
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, check=True, timeout=15)
    result = {
        "schema": 1, "scope": "source-only prerequisite proposal; no input imported/executed",
        "context_revision": revision.stdout.decode().strip(),
        "input_count": len(rows), "members": rows,
        "tree_digest_definition": "SHA256 of sorted path<TAB>bytes<TAB>sha256<LF> rows",
        "consulted_tree_sha256": digest("".join(
            "%s\t%d\t%s\n" % (r["path"], r["bytes"], r["sha256"])
            for r in sorted(rows, key=lambda r:r["path"])).encode()),
        "python": {"executable": sys.executable, "version": sys.version},
        "argv": sys.argv,
        "no_compiler_product_native_or_old_harness_execution": True,
    }
    with manifest.open("x") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({k:result[k] for k in ("input_count", "context_revision", "consulted_tree_sha256")}))

if __name__ == "__main__":
    main()
