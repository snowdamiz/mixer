#!/usr/bin/env python3
"""Record only explicitly listed ordinary inputs and this protocol model."""

import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
INPUTS = [
    "AGENTS.md", "mixer-product-plan.md",
    "docs/hosted-identity-contract.md", "docs/hosted-identity-startup-contract.md",
    "docs/hosted-workspace-identity-session.md", "docs/hosted-customer-workspace-contract.md",
    "docs/hosted-customer-workspace-http.md", "docs/console-workspace-client.md",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "console/src/api/workspace-client.ts", "docs/console-identity-flow-contract.md",
    "verification/console-identity-flow-contract/model_test.py",
    "verification/console-identity-flow-contract/sources.json",
    "verification/console-identity-flow-contract/run.py",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    return [{"path": path, "sha256": sha((ROOT / path).read_bytes())} for path in INPUTS]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


before = manifest()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
command = [sys.executable, "-B", str(HERE / "model_test.py")]
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
(HERE / "model-output.txt").write_text(result.stdout + result.stderr)
after = manifest()
receipt = {
    "status": "model_pass" if result.returncode == 0 and before == after else "failed",
    "scope": "Proposed contract and standard-library transaction/PKCE design model only; not product identity admission.",
    "started_at_utc": started,
    "finished_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "agent": {"model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "fresh_context": True},
    "source_revision": git("rev-parse", "HEAD"),
    "source_binding": "Explicit selected working-tree files, including uncommitted document/model; unrelated active lanes excluded.",
    "inputs": before,
    "input_tree_sha256": sha(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()),
    "inputs_unchanged_during_run": before == after,
    "command": command,
    "reproduce": "python3 verification/console-identity-flow-contract/run.py",
    "python_version": sys.version,
    "platform": platform.platform(),
    "git_version": subprocess.check_output(["git", "--version"], text=True).strip(),
    "exit_code": result.returncode,
    "output": "verification/console-identity-flow-contract/model-output.txt",
    "output_sha256": sha((HERE / "model-output.txt").read_bytes()),
    "network": "None for executable model; official standards reviewed separately with web tool.",
    "cleanup": "Model creates no files, sockets, database, native/capture process or scratch; collector writes only owned evidence files.",
    "pending": [
        "Root review and contract freeze", "Product OIDC, token/ID-token verifier composition and lifecycle writers",
        "Real Phoenix/PostgreSQL/provider adapter and replicated session tests",
        "Browser interaction, cookie/CORS/CSRF/CSP and deployment qualification",
        "Refresh, provider logout/revocation, tenant onboarding/linking/SSO/SCIM",
        "Computer use, capture, native simulator/emulator and physical phone checks paused",
        "FieldLog immutable published packages, customer acceptance and all GA gates",
    ],
    "prohibited_lanes": "No frozen catalog-inspector, authority-driver or rejected outbound Worker V2 source imported/compiled/executed; no hosted/scripts/test-local.py main run.",
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "exit_code": result.returncode,
                  "inputs_unchanged": before == after, "input_tree_sha256": receipt["input_tree_sha256"]}))
sys.exit(0 if receipt["status"] == "model_pass" else 1)
