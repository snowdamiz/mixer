"""Select the reviewed fixture-only active-flight contract; no runtime release."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).with_name("inflight-lifecycle-selection.json")

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def verify(path, digest, count):
    assert row(path)["sha256"] == digest
    value = json.loads(path.read_bytes())
    members = value.get("members", value.get("files"))
    assert len(members) == count
    for expected in members:
        actual = row(path.parent / expected["path"])
        assert actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"]

assert not DEST.exists(), "One-shot; do not replay"
contract = ROOT / "verification/console-key-owner-inflight-lifecycle-contract/freeze.json"
review = ROOT / "verification/console-key-owner-inflight-lifecycle-independent/review-1/review-seal.json"
verify(contract, "dcf68267fbfe7d495f0cf92de97e2a46f140d1c9bd8f5a353bebacadf66ce276", 39)
verify(review, "1929c914b2da1454739ee24da1956e2a6e6829110911b5a8f71d6076ad2268f4", 3)
selection = {
    "status": "reviewed-source-contract-selected-implementation-pending",
    "contract": row(contract), "independent_review": row(review),
    "prior_socket_free_acceptance": row(DEST.with_name("key-owner-lifecycle-acceptance.json")),
    "canonical_supervisor_before": row(ROOT / "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex"),
    "implementation_lane": "verification/console-key-owner-inflight-lifecycle-implementation",
    "selected": ["Test-build-only supervisor fixture constructor and guarded init dispatch sharing ordinary topology",
                 "KOL08-GRACEFUL with completed TLS negotiation and pending JWKS response",
                 "KOL09-KILL with the same pending flight and mandatory adverse-ordering observation"],
    "amendments": ["Execute the unchanged seven ordinary regressions plus two new cases: nine methods, two new",
                   "Fixture constructor and init dispatch must both be unavailable in production builds",
                   "Zero compiler warnings; retain and narrowly classify intentional kill OTP reports; callback exceptions fail the resource gate",
                   "Existing TLSFixture OpenSSL subprocesses require exact tool identity, invocation accounting and owned-group cleanup in the future plan"],
    "production_DNS_TLS_policy_unchanged": True, "new_runtime_released": False,
    "hypothesized_noproc_or_early_replacement_verified": False,
    "pending": ["Implementation and exact frozen host-plan review/release", "Original KOL08 owner-crash adaptation",
                "Production destination/provider/application integration, native/device, operations and GA"]}
w = json.loads((ROOT / "work-graph.json").read_bytes())
g = json.loads((ROOT / "gates/ga.json").read_bytes())
assert w["packages"][13]["fixedWorkspaceDispatcher"] == g["gates"][21]["fixedWorkspaceDispatcher"]
for target in [w["packages"][13], g["gates"][21]]:
    target["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]["next_inflight_contract"] = copy.deepcopy(selection)
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "selection": selection,
               "metadata": [row(ROOT / "work-graph.json"), row(ROOT / "gates/ga.json")], "GA_verified": 0}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"source_contract_selected": True, "runtime_released": False, "GA_verified": 0}))
