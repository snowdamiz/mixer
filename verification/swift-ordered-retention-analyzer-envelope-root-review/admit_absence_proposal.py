"""Read-only root admission of the separate absence proposal and review preparation."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
packets = []
for path, digest, count, size in [
    ("verification/swift-envelope-absent-state-correction/proposal-1/seal.json",
     "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c", 35, 205372),
    ("verification/swift-envelope-absent-state-accounting-review/preparation/seal.json",
     "4bbf4fcd7ffeee393f2e79ffd7d549adda148da74d557cb99db4aa1a7feb3b35", 4, 23245),
]:
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    seal = json.loads(raw)
    assert len(seal["members"]) == count
    total = 0
    seen = set()
    for member in seal["members"]:
        relative = pathlib.PurePosixPath(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) not in seen
        seen.add(str(relative))
        data = (ROOT / relative).read_bytes()
        assert len(data) == member["bytes"] and hashlib.sha256(data).hexdigest() == member["sha256"], str(relative)
        total += len(data)
    assert total == size
    packets.append({"path": path, "sha256": digest, "members": count, "bytes": total})
source = ROOT / "verification/swift-envelope-absent-state-correction/proposal-1/src/envelope.rs"
source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha256 == "2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "checker_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "python_version": sys.version,
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "scope": "Root exact named proposal/preaccess member admission and source diff/funding review; no candidate or collector execution",
    "packets": packets,
    "verified_members": 39,
    "verified_bytes": 228617,
    "source_sha256": source_sha256,
    "status": "frozen-proposal-admitted-independent-accounting-pending",
    "selected": False,
    "G_scope_amendment_selected": False,
    "corrected_candidate_runtime_executed": False,
    "implementation_accepted": False,
    "GA_qualified": False,
    "errors": [],
}
(OUT / "absence-correction-proposal-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("verified_members", "verified_bytes", "source_sha256", "status")}))
