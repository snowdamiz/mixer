"""Verify immutable reviewer tooling without opening or executing producer code."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    require(path.is_file() and not path.is_symlink(), "Nonregular file: " + str(path))
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def verify_seal(name, digest, count, total):
    path = ROOT / name
    require(identity(path)["sha256"] == digest, "Seal differs: " + name)
    data = json.loads(path.read_bytes())
    seen = set()
    observed_bytes = 0
    for row in data["members"]:
        relative = Path(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe member")
        require(row["path"] not in seen, "Duplicate member")
        require(identity(ROOT / relative) == {key: row[key] for key in ("bytes", "sha256")}, "Member differs: " + row["path"])
        seen.add(row["path"])
        observed_bytes += row["bytes"]
    require(len(seen) == data["member_count"] == count, "Count differs")
    require(observed_bytes == data["member_bytes"] == total, "Bytes differ")
    prefix = path.parent.relative_to(ROOT).as_posix() + "/"
    actual = {p.relative_to(ROOT).as_posix() for p in path.parent.rglob("*") if p.is_file()}
    expected = {p for p in seen | set(data["excluded"]) if p.startswith(prefix)}
    require(actual == expected, "Sealed directory closure differs")
    return data


preaccess = "verification/swift-cache-state-independent-review/preaccess/seal.json"
preaccess_sha = "1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c"
verify_seal(preaccess, preaccess_sha, 173, 27268876)
preparation = "verification/swift-cache-state-independent-review/execution-preparation/seal.json"
preparation_sha = "07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6"
verify_seal(preparation, preparation_sha, 1479, 8158127)
base = (ROOT / preparation).parent
ready = json.loads((base / "ready.json").read_bytes())
receipt = json.loads((base / "final-receipt.json").read_bytes())
require(ready["seal_sha256"] == preparation_sha, "Readiness identity differs")
require(not receipt["candidate_source_accessed"], "Candidate access in preparation")
for key in ("actual_candidate_API_probe_compilations", "actual_private_candidate_controls", "actual_public_candidate_File_cases", "candidate_Rust_semantic_executions", "product_tests", "private_paid_domain_exclusions_runtime_passes"):
    require(receipt[key] == 0, "Unexpected candidate evidence: " + key)
for mode in ("normal_controls", "optimized_controls"):
    controls = receipt[mode]
    require((controls["methods"], controls["checks"], controls["stub_executions"]) == (9, 372, 35), "Tooling totals differ")
    require(controls["failures"] == controls["errors"] == controls["skips"] == 0, "Tooling failure")
require(receipt["self_owned_stub_API_positive_controls"] == 1 and receipt["self_owned_stub_API_negative_controls"] == 14, "API totals differ")
require(not receipt["native_capture_UI_simulator_emulator_phone_started_or_queried"] and not receipt["process_discovery"], "Environment scope differs")
require(identity(ROOT / "docs/swift-cache-state-execution-review-preparation.md")["sha256"] == "3d2099fb5338e9ebea7e3fce15bc2fc42e8b70962bae94663c110389e038bfb2", "Plan differs")
for name, digest in (("implementation-selection.json", "012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3"), ("public-getter-selection.json", "80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1")):
    require(identity(OUT / name)["sha256"] == digest, "Root selection differs")

result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python": sys.version,
    "script_sha256": identity(Path(__file__))["sha256"],
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "reviewer-execution-preparation-custody-verified-candidate-admission-pending",
    "preaccess_seal_sha256": preaccess_sha,
    "preaccess_members": 173,
    "preaccess_bytes": 27268876,
    "preparation_seal_sha256": preparation_sha,
    "preparation_members": 1479,
    "preparation_bytes": 8158127,
    "tooling_methods_per_mode": 9,
    "tooling_checks_per_mode": 372,
    "stub_executions_per_mode": 35,
    "stub_API_positive": 1,
    "stub_API_negative": 14,
    "candidate_access_or_execution_authorized_by_this_receipt": False,
    "scope": "Custody verification and bounded reviewer-tooling reuse only; no producer source execution or implementation acceptance.",
    "future_public_execution": "Requires a separate exact frozen candidate admission; prepared runner batches at most 64 serial public cases.",
    "private_execution": "Unimplemented separate-admission plan; actual private seams and source proof remain pending.",
    "implementation_accepted": False,
    "native_runtime_or_capture_started": False,
    "GA_qualified": False,
}
destination = OUT / "execution-preparation-acceptance.json"
destination.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"path": destination.relative_to(ROOT).as_posix(), **identity(destination)}))
