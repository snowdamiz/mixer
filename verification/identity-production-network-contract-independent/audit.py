#!/usr/bin/env python3
"""Offline byte/source review. Never imports or invokes the proposed collector."""
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/identity-production-network-contract"
COMMANDS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    argv = ["git", *args]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, check=True)
    COMMANDS.append({"argv": argv, "exit_code": result.returncode,
                     "stdout_bytes": len(result.stdout), "stdout_sha256": sha(result.stdout),
                     "stderr": result.stderr.decode()})
    return result.stdout


def canonical_digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def describe(data):
    return {"bytes": len(data), "sha256": sha(data)}


manifest = json.loads((PACKET / "packet-manifest.json").read_bytes())
contract = json.loads((PACKET / "contract.json").read_bytes())
actual_packet = {path: describe((PACKET / path).read_bytes()) for path in manifest["files"]}
errors = []
if actual_packet != manifest["files"]:
    errors.append("packet file bindings differ")
packet_digest = canonical_digest(actual_packet)
if packet_digest != manifest["tree_digest_sha256"]:
    errors.append("packet aggregate digest differs")

product = json.loads((PACKET / "inputs/product-source-manifest.json").read_bytes())
commit = contract["source_identity"]["product_commit"]
head = git("rev-parse", "HEAD").decode().strip()
tree = git("rev-parse", commit + "^{tree}").decode().strip()
tree_rows = git("ls-tree", "-rz", commit, "--", "hosted/").split(b"\0")
ordinary = {}
for row in tree_rows:
    if not row:
        continue
    metadata, path = row.split(b"\t", 1)
    mode, kind, oid = metadata.split()
    if kind != b"blob" or mode not in (b"100644", b"100755"):
        errors.append("nonordinary product member: " + path.decode())
    ordinary[path.decode()] = oid.decode()
if set(ordinary) != set(product["files"]):
    errors.append("177-path manifest is not exact committed hosted set")
actual_product = {path: describe(git("show", commit + ":" + path)) for path in ordinary}
if actual_product != product["files"]:
    errors.append("product blobs differ from manifest")
product_digest = canonical_digest(actual_product)
if product_digest != contract["source_identity"]["product_tree_digest_sha256"]:
    errors.append("product aggregate digest differs")
if tree != contract["source_identity"]["product_tree"] or tree != product["tree"]:
    errors.append("product git tree differs")

local = json.loads((PACKET / "inputs/local-inputs.json").read_bytes())
committed_inputs = 0
for row in local["selected_inputs"]:
    retained = (PACKET / row["snapshot"]).read_bytes()
    if describe(retained) != {k: row[k] for k in ("bytes", "sha256")}:
        errors.append("selected input binding differs: " + row["path"])
    if "commit" in row:
        if retained != git("show", row["commit"] + ":" + row["path"]):
            errors.append("selected snapshot differs from git: " + row["path"])
        committed_inputs += 1

image_results = []
for label, key in (("elixir", "test_image"), ("postgres", "database_image")):
    selected = contract["platform"][key]
    blobs = {name: (PACKET / f"inputs/registry/{label}-{name}.json").read_bytes()
             for name in ("index", "amd64-manifest", "amd64-config")}
    index, child, config = [json.loads(blobs[name]) for name in ("index", "amd64-manifest", "amd64-config")]
    checks = {
        "index_hash": "sha256:" + sha(blobs["index"]) == selected["index_digest"],
        "child_hash": "sha256:" + sha(blobs["amd64-manifest"]) == selected["amd64_manifest_digest"],
        "config_hash": "sha256:" + sha(blobs["amd64-config"]) == selected["config_digest"],
        "child_in_index": any(x["digest"] == selected["amd64_manifest_digest"] and
                              x["size"] == len(blobs["amd64-manifest"]) and
                              x["platform"] == {"architecture": "amd64", "os": "linux"}
                              for x in index["manifests"]),
        "config_in_child": child["config"]["digest"] == selected["config_digest"] and
                           child["config"]["size"] == len(blobs["amd64-config"]),
        "config_platform": config["os"] == "linux" and config["architecture"] == "amd64",
        "layer_count": len(child["layers"]) == selected["layers_count"],
        "layer_compressed_bytes": sum(x["size"] for x in child["layers"]) == selected["compressed_layer_bytes"],
    }
    if not all(checks.values()):
        errors.append("image metadata binding differs: " + label)
    image_results.append({"label": label, "checks": checks,
                          "runtime_ref": selected["runtime_ref"],
                          "config_digest": selected["config_digest"],
                          "runtime_observed": False})

bootstrap_results = []
for item in contract["bootstrap"]["selection"]:
    rows = list(csv.reader(io.StringIO((PACKET / f'inputs/primary/{item["tool"]}.csv').read_text())))
    expected = [item["version"], item["sha512"], item["archive_elixir_build"], item["otp_release"]]
    matched = expected in rows
    if not matched:
        errors.append("bootstrap CSV binding differs: " + item["tool"])
    bootstrap_results.append({"tool": item["tool"], "exact_csv_row_present": matched,
                              "url": item["url"], "sha512": item["sha512"],
                              "artifact_downloaded_or_executed": False})

source_reads = [
    "hosted/test/support/identity_tls_fixture.ex",
    "hosted/lib/mixer_hosted/application.ex",
    "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
    "hosted/lib/mixer_hosted/identity/dns_resolver.ex",
    "hosted/config/config.exs",
    "hosted/scripts/test-local.py",
]
selected_source_bindings = {path: actual_product[path] for path in source_reads}
migrations = sorted(path for path in actual_product if path.startswith("hosted/priv/repo/migrations/"))
if len(migrations) != 10:
    errors.append("expected ten current migration files")

result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "passed-offline-source-byte-audit" if not errors else "failed",
    "scope": "Offline bytes, Git object reads, pinned public metadata consistency; no product runtime qualification",
    "audit_command": [sys.executable, str(Path(__file__).resolve())],
    "audit_tool": {"python": sys.version, "executable": sys.executable,
                   "audit_source": describe(Path(__file__).read_bytes())},
    "source": {"observed_head": head, "selected_product_commit": commit, "selected_product_tree": tree,
               "product_files": len(actual_product), "product_tree_digest_sha256": product_digest,
               "exact_hosted_git_members": set(ordinary) == set(product["files"]),
               "committed_selected_snapshots_checked": committed_inputs,
               "additional_review_source_bindings": selected_source_bindings,
               "migration_paths": migrations},
    "packet": {"manifest_sha256": sha((PACKET / "packet-manifest.json").read_bytes()),
               "frozen_files": len(actual_packet), "tree_digest_sha256": packet_digest,
               "contract_sha256": sha((PACKET / "contract.json").read_bytes())},
    "images": image_results,
    "bootstrap": bootstrap_results,
    "git_commands": COMMANDS,
    "errors": errors,
    "activity": {"Docker_native_compiler_test_version_process_namespace_probes": 0,
                 "network_requests": 0, "image_or_tool_downloads": 0,
                 "CI_dispatches": 0, "canonical_writes": 0,
                 "only_write_root": str(OUT)},
}
(OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "packet_digest": packet_digest,
                  "product_files": len(actual_product), "frozen_files": len(actual_packet), "errors": errors}))
sys.exit(bool(errors))
