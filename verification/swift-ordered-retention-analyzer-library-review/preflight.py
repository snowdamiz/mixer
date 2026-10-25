"""Read-only input audit; never imports a producer or historical harness."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OWN = pathlib.Path(__file__).resolve().parent
SEALS = [
    "verification/swift-ordered-retention-analyzer-design/seal.json",
    "verification/swift-ordered-retention-analyzer-review/seal.json",
    "verification/swift-ordered-retention-diagnostic-rust/seal.json",
    "verification/swift-ordered-retention-diagnostic-completion/seal.json",
    "verification/swift-ordered-retention-diagnostic-completion-review/seal.json",
]

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def file_row(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": digest(path)}

def audit():
    seals = []
    for name in SEALS:
        path = ROOT / name
        expected = path.with_suffix(".sha256").read_text().strip()
        assert digest(path) == expected, name
        packet = json.loads(path.read_bytes())
        for row in packet["members"]:
            member = ROOT / row["path"]
            assert member.stat().st_size == row["bytes"], row["path"]
            assert digest(member) == row["sha256"], row["path"]
        seals.append({"path": name, "sha256": expected,
                      "members": len(packet["members"]),
                      "bytes": sum(row["bytes"] for row in packet["members"])})
    copies = ROOT / "verification/swift-ordered-retention-analyzer-review/inputs/historical-sidecars"
    sidecars = []
    for copy in sorted(copies.glob("*.sidecar.json")):
        directory, name = copy.name.split("__", 1)
        original = ROOT / "verification/swift-ordered-retention-diagnostic-completion/streams" / directory / name
        assert original.is_file(), str(original)
        assert original.read_bytes() == copy.read_bytes(), str(copy)
        content = json.loads(copy.read_bytes())
        assert content.get("status") == "invalid", (copy.name, content)
        assert content.get("failure") == 15, (copy.name, content)
        sidecars.append(file_row(original))
    assert len(sidecars) == 17
    inputs = ["AGENTS.md", "PLAN.md", "mixer-product-plan.md",
              "docs/swift-ordered-retention-analyzer.md",
              "docs/swift-ordered-retention-analyzer-review.md",
              "verification/swift-ordered-retention-analyzer-root-review/acceptance.json",
              "verification/swift-ordered-retention-diagnostic-completion/candidate-source.tar.gz"]
    return {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "seals": seals, "historical_sidecars": sidecars,
            "inputs": [file_row(ROOT / name) for name in inputs],
            "python": sys.version, "python_executable": str(pathlib.Path(sys.executable).resolve()),
            "python_sha256": digest(pathlib.Path(sys.executable).resolve()),
            "producer_imported_or_executed": False,
            "upstream_sources_restored": False,
            "native_capture_target_or_process_discovery": False}

if __name__ == "__main__":
    result = audit()
    destination = OWN / (sys.argv[1] if len(sys.argv) > 1 else "preflight.json")
    assert destination.parent == OWN
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": True, "seals": len(result["seals"]),
                      "members": sum(row["members"] for row in result["seals"]),
                      "historical_sidecars": len(result["historical_sidecars"]),
                      "receipt": str(destination.relative_to(ROOT))}))
