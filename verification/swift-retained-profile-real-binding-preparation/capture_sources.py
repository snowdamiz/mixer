"""Capture only released/canonical sources; do not discover or execute lanes."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ACCEPTED = "verification/swift-initial-profile-construction-implementation/source/vm/src/"
HEADER = "verification/swift-profile-header-preparation/inputs/"
STDIO = "verification/swift-retained-profile-stdio-read-boundary-correction/new/replay/corrected/replay/"
FILES = [
    "AGENTS.md", "mixer-product-plan.md", "PLAN.md", "STATUS.md",
    "verification/swift-semantic-adapter-root-review/retained-composition-stdio-host-acceptance.json",
    "verification/swift-semantic-adapter-root-review/initial-profile-component-acceptance.json",
    "verification/swift-semantic-adapter-root-review/initial-profile-implementation-selection.json",
    "verification/swift-semantic-adapter-root-review/initial-profile-foundation-configuration-correction.json",
    "verification/swift-semantic-adapter-root-review/initial-profile-source-action-scope-selection.json",
    "verification/swift-initial-profile-construction-implementation/host-support-manifest.json",
    ACCEPTED + "experimental/swift.rs",
    ACCEPTED + "experimental_swift_reactor/control.rs",
    ACCEPTED + "experimental_wasi/mod.rs",
    ACCEPTED + "experimental_swift_reactor/diagnostic_profile.rs",
    ACCEPTED + "experimental_swift_reactor/cache/initial_profile_v1.rs",
    ACCEPTED + "experimental_swift_reactor/cache/initial_profile_v1/header.rs",
    HEADER + "verification/swift-cache-state-ci/pack/source/library/analyzer.rs",
    STDIO + "prototype.py", STDIO + "consumer.py",
    "verification/swift-retained-profile-composition-preparation/contract.md",
    "verification/swift-retained-profile-composition-preparation/protocol-types.rs",
    "verification/swift-retained-profile-composition-preparation/dependencies.json",
    "verification/swift-retained-profile-composition-preparation/schema.py",
    "vm/src/main.rs", "vm/src/experimental/swift.rs",
    "vm/src/experimental_swift_reactor/control.rs",
    "vm/src/experimental_swift_reactor/mod.rs",
]
EXCERPTS = {
    ACCEPTED + "experimental_swift_reactor/cache.rs": [(280, 320), (1470, 1526), (1625, 1810), (1889, 1910)],
    HEADER + "completion-source/src/experimental_swift_reactor/cache_tests.rs": [(3855, 4008), (4100, 4173), (4371, 4453)],
    HEADER + "verification/swift-cache-state-ci/pack/source/library/cache_state.rs": [(1, 105), (15657, 15689)],
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    records = []
    for path in FILES:
        data = (ROOT / path).read_bytes()
        destination = HERE / "inputs" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        records.append({"path": path, "bytes": len(data), "sha256": sha(data), "copy": str(destination.relative_to(HERE))})
    for path, spans in EXCERPTS.items():
        data = (ROOT / path).read_bytes()
        lines = data.splitlines(keepends=True)
        for first, last in spans:
            excerpt = b"".join(lines[first-1:last])
            destination = HERE / "excerpts" / (path.replace("/", "__") + f".{first}-{last}.txt")
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(excerpt)
            records.append({"path": path, "source_bytes": len(data), "source_sha256": sha(data), "first_line": first, "last_line": last, "bytes": len(excerpt), "sha256": sha(excerpt), "copy": str(destination.relative_to(HERE))})
    # These exact source declarations compile as data only. No validator, VM,
    # cache, loader or diagnostic control behavior is linked or executed.
    fragments = [
        (ACCEPTED + "experimental/swift.rs", 58, 70),
        (ACCEPTED + "experimental_wasi/mod.rs", 83, 101),
        (ACCEPTED + "experimental_wasi/mod.rs", 109, 131),
        (ACCEPTED + "experimental_swift_reactor/control.rs", 64, 230),
    ]
    declarations = b"#![allow(dead_code)]\n"
    for path, first, last in fragments:
        lines = (ROOT / path).read_bytes().splitlines(keepends=True)
        declarations += f"// Exact {path}:{first}-{last}\n".encode() + b"".join(lines[first-1:last])
    (HERE / "actual_data_records.rs").write_bytes(declarations)
    record = {"scope": "finite source declarations and explicitly consulted released/canonical inputs only", "files": records, "actual_data_declarations": {"fragments": [{"path": p, "first_line": a, "last_line": b} for p,a,b in fragments], "bytes": len(declarations), "sha256": sha(declarations)}}
    (HERE / "source-evidence.json").write_text(json.dumps(record, indent=2) + "\n")
    comparisons=[]
    for relative in ("experimental/swift.rs","experimental_swift_reactor/control.rs","experimental_swift_reactor/mod.rs","experimental_swift_reactor/diagnostic_profile.rs","experimental_swift_reactor/cache/initial_profile_v1.rs"):
        canonical=ROOT/"vm/src"/relative
        accepted=ROOT/ACCEPTED/relative
        comparisons.append({"relative":relative,"accepted_sha256":sha(accepted.read_bytes()),"canonical_exists":canonical.is_file(),"canonical_sha256":sha(canonical.read_bytes()) if canonical.is_file() else None,"same_bytes":canonical.is_file() and canonical.read_bytes()==accepted.read_bytes()})
    (HERE/"canonical-comparison.json").write_text(json.dumps({"scope":"five named source comparisons only; no canonical promotion","files":comparisons},indent=2)+"\n")
    print(json.dumps({"captured_files_or_excerpts": len(records), "data_declaration_bytes": len(declarations)}))

if __name__ == "__main__":
    main()
