"""Apply the independently reviewed checkout-only patch and record its scope."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / "swift-capability-checkout-acceptance.json"
PRODUCER = ROOT / "verification/ci-swift-capability-sparse-checkout-contract"
REVIEW = ROOT / "verification/ci-swift-capability-sparse-checkout-independent"


def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


assert not DEST.exists(), "One-shot; do not replay"
packets = []
for directory, manifest_name, digest in [
    (PRODUCER, "packet-manifest.sha256", "99b65cf71f7a07bb2fb8f129b673b82759cbb8c6796dd69a4dce6250a3d73ddc"),
    (REVIEW, "seal.sha256", "9c3a363575b39a1040b2b7b5f3dde89940c75d5cbe8f018d7afb0d68199d05ec"),
]:
    manifest = directory / manifest_name
    assert row(manifest)["sha256"] == digest
    members = []
    for line in manifest.read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        actual = row(directory / name)
        assert actual["sha256"] == expected, name
        members.append(actual)
    assert len(list(p for p in directory.rglob("*") if p.is_file())) == len(members) + 1
    packets.append({"directory": str(directory.relative_to(ROOT)),
                    "manifest": row(manifest), "members": members})
r = read(REVIEW / "receipt.json")
assert r["result"] == "bounded-source-coverage-accepted"
assert r["current_closure"]["files"] == 370
assert r["current_closure"]["bytes"] == 22995155
assert r["counts"]["Git_matcher_controls"] == 393
workflow_path = ROOT / ".github/workflows/verify.yml"
before = row(workflow_path)
assert before["sha256"] == r["workflow_base_sha256"] == "fa8fd8887391ffc00f55bc70b370e725cf99ee330c744387f498bea7a2626a88"
assert row(PRODUCER / "proposed-workflow.diff")["sha256"] == r["proposal_members"]["proposed-workflow.diff"]
assert row(PRODUCER / "source-manifest.sha256")["sha256"] == r["current_closure"]["source_manifest_sha256"]
for line in (PRODUCER / "source-manifest.sha256").read_text().splitlines():
    expected, name = line.split("  ", 1)
    assert row(ROOT / name)["sha256"] == expected, name
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
assert len(w["packages"]) == 18 and len(g["gates"]) == 38
assert w["packages"][7]["fixtureCacheStateContractCandidate"] == g["gates"][1]["fixtureCacheStateContractCandidate"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"] == g["gates"][4]["privateOwnerEffectContractCandidate"]
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
paragraph = "The Swift capability CI checkout has bounded offline acceptance after independent review of all 370 canonical inputs / 22,995,155 bytes and 393 Git rule controls. The checkout-only change preserves complete declared resources, nine historical input blobs and full history; every build/test command and pin remains unchanged. The reviewed patch is applied locally. Delivery, remote checkout duration, dependency resolution and complete job outcomes remain pending."
texts = {}
for name in ["PLAN.md", "STATUS.md"]:
    text = (ROOT / name).read_text()
    marker = "The isolated actual Rust input-owner candidate is returned for correction"
    assert text.count(marker) == 1
    texts[name] = text.replace(marker, paragraph + "\n\n" + marker)
commands = []
for apply_args in [["--check"], []]:
    argv = ["git", "apply", *apply_args, str(PRODUCER / "proposed-workflow.diff")]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=10)
    commands.append({"argv": argv, "exit": result.returncode,
                     "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
    assert result.returncode == 0
after = row(workflow_path)
assert after["sha256"] == r["proposed_workflow_sha256"] == "f83defbefd14e710103f4a948f02c15eea8cfd789841d3a5e3593efdb0572eeb"
value = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
         "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
         "python": sys.version, "status": "accepted-and-applied-offline-checkout-closure-for-remote-validation",
         "source": r["source"], "workflow_before": before, "workflow_after": after,
         "packets": packets, "commands": commands, "selected_files": 370,
         "selected_bytes": 22995155, "independent_rule_controls": 393,
         "independent_receipt": row(REVIEW / "receipt.json"), "root_runtime_replay": False,
         "root_review": "Reviewed exact checkout-only insertion and finite transitive source/resource/history closure. Rehashed every selected live input and both frozen packets. Original commands, pins, limits, full-history setting and other jobs are unchanged.",
         "remote_CI_passed": False, "pending": r["pending"], "GA_verified": 0}
save(DEST, value)
entry = {"status": value["status"], "root_acceptance": row(DEST), "accepted": True,
         "selected_files": 370, "selected_bytes": 22995155, "independent_rule_controls": 393,
         "commands_pins_limits_full_history_unchanged": True,
         "delivery_pending": True, "remote_CI_passed": False, "GA_accepted": False}
w["packages"][7]["capabilityHostSparseCheckout"] = entry
g["gates"][1]["capabilityHostSparseCheckout"] = copy.deepcopy(entry)
for name, data in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n")
for name, text in texts.items():
    (ROOT / name).write_text(text)
subprocess.run(["git", "diff", "--check", "--", ".github/workflows/verify.yml", "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"], check=True, cwd=ROOT, timeout=10)
save(OUT / "swift-capability-checkout-metadata-validation.json", {
    "passed": True, "metadata_files": [row(ROOT / name) for name in ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]],
    "packages": 18, "gates": 38, "W08_G02_equal": True, "W05_G05_equal": True, "GA_verified": 0})
print(json.dumps({"accepted_and_applied": True, "selected_files": 370,
                  "packet_files": sum(len(p["members"]) + 1 for p in packets), "remote_pending": True}))
