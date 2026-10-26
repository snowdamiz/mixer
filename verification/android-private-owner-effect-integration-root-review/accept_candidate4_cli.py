"""Accept only the independently reviewed candidate4 CLI host integration scope."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("verification/android-private-owner-profile3-independent-review")


def read(path):
    return json.loads((ROOT / path).read_text())


def bind(path):
    raw = (ROOT / path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def checked(path, expected):
    assert bind(path) == {"bytes": expected["bytes"], "sha256": expected["sha256"]}, path


manifest = BASE / "manifest.json"
assert bind(manifest)["sha256"] == "685a1d1f905540c023d3ffebd5eed392cde08fd8e07ee15e6d9d246dcbd8b7ac"
packet = read(manifest)
assert packet["members"] == len(packet["files"]) == 658
assert sum(r["bytes"] for r in packet["files"].values()) == packet["bytes"] == 5569820
for name, row in packet["files"].items():
    checked(BASE / name, row)
seal_path = BASE / "seal-receipt.json"
assert bind(seal_path)["sha256"] == "075f2f4f89f834e303c3006f2a536b3096fa265b48ebf2e0f3980ba264301607"
seal = read(seal_path)
checked(seal["documentation"]["path"], seal["documentation"])
audit = read(BASE / "final-audit.json")
for name, digest in audit["external_pins"].items():
    assert bind(name)["sha256"] == digest, name
producer = Path("verification/android-private-owner-profile3-integration/candidate4-qualification")
for name, row in read(producer / "source-binding.json")["files"].items():
    checked(name, row)
for name, row in read("verification/android-private-owner-integration-implementation/candidate-4/source-map.json").items():
    checked(name, row)
commands = read(BASE / "commands.json")
assert len(commands) == 63
assert sum(c["expected_exit"] != 0 for c in commands) == 48
for c in commands:
    assert c["exit"] == c["expected_exit"] and c["child_reaped"], c["label"]
    assert not any(c[k] for k in ("timed_out", "output_limit_exceeded", "own_group_signaled")), c["label"]
    assert c["source_binding_sha256"] and c["executable"]["sha256"], c["label"]
receipt = read(BASE / "receipt.json")
for name in receipt["cleanup"]["removed_owned_scratch"]:
    assert not (ROOT / BASE / name).exists(), name
result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": sys.argv, "python": sys.version,
    "script": {"path": str(Path(__file__).relative_to(ROOT)), **bind(Path(__file__).relative_to(ROOT))},
    "status": "bounded-candidate4-profile3-CLI-host-integration-accepted",
    "manifest": {"path": str(manifest), **bind(manifest), "members_verified": 658, "member_bytes_verified": 5569820},
    "seal_receipt": {"path": str(seal_path), **bind(seal_path)},
    "documentation": seal["documentation"],
    "current_producer_sources_verified": 356, "current_native_candidate_sources_verified": 309,
    "independent_host_commands": 63, "independent_Swift_methods": 3,
    "static_expect_sites": 18, "shared_require_sites": 2,
    "independent_refusal_commands": 48, "independent_mutation_fixtures": 8,
    "preaccess_traps": 8, "source_projection_entries": 44,
    "producer_Swift_methods_per_mode": 13, "producer_Swift_invocations_per_mode": 77,
    "producer_Python_methods_per_mode": 30,
    "scope": "Exact selected profile projection, common Swift and direct Python preaccess, copied exports and app-owned host factory/reducer semantics.",
    "limitations": [
        "Independent matrix samples configuration/platform combinations; producer supplies complementary larger matrix.",
        "Direct executable and resolved compiler frontend binding; no descendant compiler/linker launch trace or immutable filesystem sandbox proof.",
        "Producer pre-snapshot tracked-input inventory lacks source binding; actual product commands are bound. Release initial and post-test identities remain distinct.",
        "Local development source admission provides no OTA authorization or protection from arbitrary executable/driver modification.",
        "Native owner full source/callback/legacy review and paused runtime/device checks remain separate."
    ],
    "CLI_scope_accepted": True, "canonical_product_delivery_authorized": False,
    "native_owner_implementation_accepted": False, "native_runtime_or_capture_started": False,
    "public_V2_selected": False, "GA_qualified": False,
}
out = Path("verification/android-private-owner-effect-integration-root-review/candidate-4-CLI-acceptance.json")
assert not (ROOT / out).exists()
(ROOT / out).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"path": str(out), **bind(out)}))
