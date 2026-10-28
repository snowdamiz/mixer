"""Offline source bookkeeping only. Never loads or executes Elixir/test code."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REVISION = "d87ce0a1b05a9ad42cd2118bbf2ccc5491499663"
SELECTION = "verification/console-session-and-checkout-root-review/hosted-http2-source-selection.json"
REVIEW = "verification/hosted-dependency-advisory-correction-independent/http2-plan-review"
DESIGN = "verification/hosted-dependency-advisory-correction/http2-qualification-plan"
SOURCES = [
    "hosted/test/support/http2_wire_fixture.ex",
    "hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bound(relative, expected=None):
    data = (ROOT / relative).read_bytes()
    if expected is not None and sha(data) != expected:
        raise ValueError("input pin mismatch: " + relative)
    return data


def pin(relative):
    data = read_bound(relative)
    return {"path": relative, "bytes": len(data), "sha256": sha(data)}


def write_json(relative, value):
    (OUT / relative).write_text(json.dumps(value, indent=2) + "\n")


selection_bytes = read_bound(SELECTION, "40354b3c83abd5a58a3419c82153f932e7d7937d70d090520afdcb3836d02d06")
selection = json.loads(selection_bytes)
review_bytes = read_bound(REVIEW + "/review-seal.json", "293ebfe217ed68f2e547146cbadf30a533315dc5c2cf3747b2447759649651be")
review = json.loads(review_bytes)
assert selection["methods"] == 5 and selection["finite_subcases"] == 7
assert selection["upstream_Bandit_commit"] == "220b9dfd27f9a21305be2afc75cbe585ddc24e7a"
for member in review["files"]:
    read_bound(REVIEW + "/" + member["path"], member["sha256"])
design_seal = read_bound(DESIGN + "/seal.sha256", "73abbc2d2a9198c2c5df0c2824672bae5cf1f3d3bdd9d8457bf4580687b8f2bd")
for line in design_seal.decode().splitlines():
    digest, name = line.split("  ", 1)
    read_bound(DESIGN + "/" + name, digest)
old_inputs = json.loads(read_bound(DESIGN + "/source-evidence.json"))["inputs"]
assert len(old_inputs) == 24
current_inputs = {path: pin(path) for path in old_inputs}
drift = [path for path, old in old_inputs.items() if current_inputs[path]["sha256"] != old["sha256"]]
application = json.loads(read_bound("verification/hosted-dependency-advisory-correction/integration-v1/application-map.json"))
canonical = []
for item in application["canonical_files"]:
    read_bound(item["canonical_path"], item["proposed_sha256"])
    canonical.append(pin(item["canonical_path"]))
audit = json.loads(read_bound(REVIEW + "/audit.json"))
official = []
for item in audit["official_sources"]:
    path = REVIEW + "/upstream/" + item["path"]
    data = read_bound(path, item["sha256"])
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert blob == item["git_blob_sha"]
    official.append({**item, "local_evidence_path": path, "verified_git_blob_sha": blob})
assert len(official) == 8

source_pins = []
patch = []
for relative in SOURCES:
    data = read_bound(relative)
    assert len(data) <= 40_000 and data.endswith(b"\n")
    assert all(line.rstrip() == line for line in data.splitlines())
    destination = OUT / "source" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    source_pins.append(pin(relative))
    patch += [f"diff --git a/{relative} b/{relative}\n", "new file mode 100644\n"]
    patch += list(difflib.unified_diff([], data.decode().splitlines(keepends=True), fromfile="/dev/null", tofile="b/" + relative))
(OUT / "two-file.patch").write_text("".join(patch))
test_text = read_bound(SOURCES[1]).decode()
methods = re.findall(r'^  test "([^"]+)", context do$', test_text, re.M)
assert len(methods) == 5
protected = [
    ".github/workflows/hosted.yml",
    "hosted/lib/mixer_hosted/browser_auth/store.ex",
    "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
    "hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex",
    "hosted/lib/mixer_hosted/billing/webhook_transport.ex",
]
write_json("source-evidence.json", {
    "source_revision_observed_by_git_rev_parse": REVISION,
    "root_selection": pin(SELECTION),
    "independent_review_seal": pin(REVIEW + "/review-seal.json"),
    "original_design_input_count_actual": len(old_inputs),
    "original_receipt_declared_input_count_historical": 23,
    "current_original_input_pins": current_inputs,
    "original_input_drift_observed": drift,
    "official_commit_source_blobs": official,
    "canonical_dependency_bytes_match_accepted_application": canonical,
    "local_shared_bandit_source_version": "1.13.1",
    "local_shared_bandit_is_not_target_runtime_proof": True,
    "new_test_source": source_pins,
    "protected_observed_current_bytes_not_edited_by_this_lane": [pin(path) for path in protected],
})
write_json("preparation-receipt.json", {
    "schema": 1,
    "status": "source-frozen-awaiting-independent-review-and-authorized-remote-CI",
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "python": sys.version,
    "python_executable": sys.executable,
    "revision_observation_command": ["git", "rev-parse", "HEAD"],
    "source_revision_observed": REVISION,
    "owned_canonical_source_files": SOURCES,
    "methods_source_inventory_only": methods,
    "methods": 5,
    "finite_subcases": 7,
    "module_admission_deadline_ms": 25000,
    "case_work_deadline_ms": 3000,
    "case_cleanup_reserve_ms": 500,
    "original_design_inputs_actual_count": 24,
    "official_exact_commit_blobs_verified": len(official),
    "runtime_tests_run": 0,
    "Mix_Elixir_compiler_formatter_listener_network_native_capture_process_inventory_invocations": 0,
    "source_bookkeeping_checks": [
        "Root-selected control bytes hashed before JSON parsing",
        "Sealed original design/review members and eight Git/SHA256 blob identities",
        "Three canonical dependency byte hashes equal accepted proposals",
        "Two frozen source copies equal current authored files; bounded sizes/newlines/whitespace",
        "Five method names inventoried textually; this is not a syntax or executable pass",
    ],
    "pending": ["independent source review", "remote formatting", "remote compilation", "remote five-method/seven-case execution", "case-specific wire receipt review"],
    "qualifications": {
        "HTTP2_BATCHING_APPLICATION_BYTE_CAPS": "pending",
        "HTTP2_NONPROGRESS_PUBLIC_READ_DEADLINE": "pending",
    },
    "limitation": "No blanket advisory, exploit, memory/backpressure, provider, production, native/device or GA proof.",
})
members = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "seal.sha256")
seal = "".join(sha(p.read_bytes()) + "  " + p.relative_to(OUT).as_posix() + "\n" for p in members)
(OUT / "seal.sha256").write_text(seal)
print(json.dumps({"status": "source-freeze-prepared", "members": len(members), "methods": 5, "subcases": 7, "original_inputs_actual": 24, "original_input_drift": drift, "seal_sha256": sha(seal.encode()), "runtime_tests": 0}))
