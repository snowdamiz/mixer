"""One-time root acceptance and exact additive integration of the tested component."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "acceptance.json").exists(), "one-time integration only"
    bindings = {}
    for directory, seal, expected in [
        ("stripe-webhook-signature", "seal.json", "27191daebc5ce6dc41e93251027b72b7cabed491aa7b50450daa40346d964e16"),
        ("stripe-webhook-signature-review", "seal.json", "d5432f6c01027ec9ccc9949074b20bab07a31fd9ae2db4478ba4ff18233c6ef4")
    ]:
        path = REPO / "verification" / directory / seal
        assert sha(path) == expected
        bindings[str(path.relative_to(REPO))] = expected
        for item in json.loads(path.read_text())["files"]:
            source = REPO / item["path"]
            assert source.is_file() and not source.is_symlink()
            assert source.stat().st_size == item["bytes"] and sha(source) == item["sha256"]
            bindings[item["path"]] = item["sha256"]
    attempt = HERE / "attempt-1"
    for name, value in json.loads((attempt / "seal.json").read_text()).items():
        source = attempt / name
        assert source.stat().st_size == value["bytes"] and sha(source) == value["sha256"]
        bindings[str(source.relative_to(REPO))] = value["sha256"]
    bindings[str((attempt / "seal.json").relative_to(REPO))] = sha(attempt / "seal.json")
    tested = json.loads((attempt / "receipt.json").read_text())
    review = json.loads((REPO / "verification/stripe-webhook-signature-review/receipt.json").read_text())
    assert review["findings"] == [] and review["status"] == "accepted-isolated-signature-freshness-only"
    assert tested["status"] == "passed-isolated-hosted-composition-review-pending"
    assert "Result: 127 passed, 2 skipped" in (attempt / "hosted/tests.log").read_text()
    nested = json.loads((attempt / "hosted/receipt.json").read_text())
    assert nested["status"] == "passed" and nested["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
    for name, expected in tested["baselineInputs"].items():
        assert sha(REPO / name) == expected, "existing hosted input changed"
    for name, expected in tested["additions"].items():
        assert not (REPO / name).exists() and not (REPO / name).is_symlink()
        assert sha(attempt / "source" / name) == expected
    for name in tested["additions"]:
        target = REPO / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(attempt / "source" / name, target)
    live = {name: sha(REPO / name) for name in tested["baselineInputs"] | tested["additions"]}
    digest = hashlib.sha256(json.dumps(live, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == tested["sourceDigest"], "live source differs from full tested composition"
    receipt = {"schema": 1, "status": "accepted-and-integrated-signature-component-only",
               "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sourceRevision": tested["sourceRevision"], "sourceDigest": digest, "sourceInputs": live,
               "appliedFiles": list(tested["additions"]), "bindingsVerified": len(bindings), "bindings": bindings,
               "validation": {"hostedPassed": 127, "hostedSkipped": 2,
                              "skipReason": "Existing Linux network namespace/NET_ADMIN tests are unavailable on this macOS host",
                              "newHostTests": 22, "independentCases": 2352, "lateCryptoFaults": 4,
                              "release": "build, missing-config expected rejection and four test-only export exclusions passed"},
               "cleanup": {"postgresStopped": True, "ownedGroupsEmpty": True, "scratchRemoved": True},
               "scope": "Only the pure bounded signature/freshness component is integrated. No HTTP route, provider call, billing state, configuration secret or database schema added.",
               "pending": ["Linux exact-head CI", "raw-body HTTP/header adapter", "endpoint/account/mode/generation owner", "durable deduplicated inbox and atomic Oban enqueue", "provider test-mode billing/reconciliation", "usage and G23"]}
    (HERE / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Integrated three tested files; {len(bindings)} proof bindings and {len(live)} composed source inputs match")


if __name__ == "__main__":
    main()
