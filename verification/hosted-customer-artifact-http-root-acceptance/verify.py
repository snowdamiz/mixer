#!/usr/bin/env python3
"""Join only the selected ordinary HTTP evidence to current product sources."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


parser = argparse.ArgumentParser()
parser.add_argument("--integration", required=True)
parser.add_argument("--review", required=True)
parser.add_argument("--review-count", required=True, type=int)
parser.add_argument("--output", required=True)
args = parser.parse_args()
output = HERE / args.output
assert output.parent == HERE and not output.exists()
output.mkdir()
(output / "verifier.py").write_bytes(Path(__file__).read_bytes())
packets = [
    ("hosted-customer-artifact-route-binding/run-1", 18),
    ("hosted-customer-artifact-route-binding-review/run-1", 25),
    ("hosted-customer-artifact-http-transport/run-5", 32),
    (args.review, args.review_count),
    (args.integration, 8),
]
bindings, current, accepted = {}, {}, []
for relative, count in packets:
    directory = ROOT / "verification" / relative
    assert directory.is_relative_to(ROOT / "verification")
    receipt = load(directory / "receipt.json")
    assert (receipt.get("success") is True or receipt.get("status") == "passed"
            or receipt.get("exit_code") == 0), relative
    assert not receipt.get("live_source_changes_during_run", []), relative
    assert not receipt.get("dependency_changes_during_run", []), relative
    cleanup = receipt.get("cleanup", {"scratch_removed": receipt.get("scratch_removed")})
    assert cleanup.get("scratch_removed") is True, relative
    for key in ["postgres_stopped", "bandit_stopped", "key_owner_stopped",
                "jwks_workers_stopped", "tls_fixture_stopped",
                "ephemeral_tls_key_directory_removed", "bandit_socket_closed",
                "tls_socket_closed"]:
        if key in cleanup:
            assert cleanup[key] is True, (relative, key)

    manifest = receipt.get("input_sha256", receipt.get("inputs"))
    if manifest is None:
        manifest = load(directory / "source-manifest.json")
    for name, expected in manifest.items():
        saved = directory / "inputs" / name
        assert saved.is_relative_to(directory / "inputs") and digest(saved) == expected, name
        bindings[str(saved.relative_to(ROOT))] = expected
        if name.startswith(("hosted/lib/", "hosted/test/", "hosted/priv/")) or name in [
            "hosted/mix.exs", "hosted/mix.lock", "services/protocol/testdata/signed-release-v3.json"
        ]:
            assert digest(ROOT / name) == expected, (relative, name)
            assert name not in current or current[name] == expected, name
            current[name] = expected

    for name, expected in receipt.get("output_sha256", receipt.get("outputs", {})).items():
        assert digest(directory / name) == expected, (relative, name)
    for command in receipt.get("commands", []):
        assert command["exit_code"] == 0, (relative, command)
        if "output_sha256" in command:
            assert digest(directory / command["output"]) == command["output_sha256"]
    if "dependency_manifest_sha256" in receipt:
        assert digest(directory / "dependency-beams.json") == receipt["dependency_manifest_sha256"]

    log = next(directory / name for name in ["tests.log", "output.txt"] if (directory / name).exists())
    assert re.search(rf"Result: {count} passed(?:\s|$)", log.read_text()), relative
    if relative == args.integration:
        assert receipt["exunit_result"] == {"excluded": 0, "failures": 0, "skipped": 0, "total": 8}
        helper = receipt["provision_helper"]
        assert digest(ROOT / helper["path"]) == helper["whole_source_sha256"]
        assert digest(directory / "executed-provision-helper.py") == helper["executed_sha256"]
        current[helper["path"]] = helper["whole_source_sha256"]
        assert receipt["public_request_count"] > 30
    for path in directory.rglob("*"):
        if path.is_file() and "inputs" not in path.relative_to(directory).parts:
            bindings[str(path.relative_to(ROOT))] = digest(path)
    accepted.append({"receipt": str((directory / "receipt.json").relative_to(ROOT)),
                     "receipt_sha256": digest(directory / "receipt.json"),
                     "passed_methods": count, "source_copies": len(manifest),
                     "source_tree_sha256": receipt["source_tree_sha256"], "cleanup": cleanup})

brand = load(ROOT / "verification/console-brand-contrast/receipt.json")["sourceFiles"]
assert all(digest(ROOT / name) == expected for name, expected in brand.items())
vm = load(ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
assert all(digest(ROOT / "vm" / name) == expected for name, expected in vm.items())
(output / "bindings.json").write_text(json.dumps(bindings, sort_keys=True, indent=2) + "\n")
(output / "current-product-inputs.json").write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")
result = {
    "schema": 1, "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "python": sys.version, "verifier_sha256": digest(Path(__file__)),
    "status": "accepted-local-customer-artifact-http", "packets": accepted,
    "retained_bindings": len(bindings), "current_product_inputs": len(current),
    "current_product_inputs_sha256": digest(output / "current-product-inputs.json"),
    "bindings_sha256": digest(output / "bindings.json"),
    "console_brand_bindings_unchanged": len(brand), "vm_bindings_unchanged": len(vm),
    "scope": "Authenticated canonical artifact PUT/GET/HEAD and audit GET/HEAD through the actual Phoenix Endpoint, default token verifier with synthetic TLS JWKS, and restricted local PostgreSQL transactions. Unit and independent adversarial reviews overlap; counts are not additive distinct coverage.",
    "limitations": [
        "No production identity provider/public DNS, Neon TLS, Cloudflare deployment, R2/CDN or live console connection.",
        "Single configured host/trust snapshot; tenant trust/lifecycle writers, distributed rate/admission limits and legacy Go audit migration remain pending.",
        "Wire compatibility is scoped; stronger authorization and documented normalization/error/audit differences are not full Go parity.",
        "Native runtime/capture paused under latest supplied AGENTS override; phones deferred. No FieldLog, store, full product or GA acceptance.",
        "Automatically triggered standard CI requires a separate exact-commit observation. No shared local main or frozen lane was run for this acceptance."
    ],
}
(output / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ["status", "retained_bindings", "current_product_inputs", "console_brand_bindings_unchanged", "vm_bindings_unchanged"]}))
