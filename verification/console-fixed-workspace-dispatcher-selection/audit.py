#!/usr/bin/env python3
"""Freeze this source selection only; never import/execute product or harness code."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PIN = "114a2632fd58076574bd5b2444c511861c3b30d4"
CANONICAL = [
    "hosted/lib/mixer_hosted_web/customer_workspace_controller.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
    "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/identity/admission.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/customer_workspace.ex",
    "hosted/lib/mixer_hosted/customer_workspace/input.ex",
    "hosted/lib/mixer_hosted/customer_workspace/storage.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/context.ex",
    "hosted/lib/mixer_hosted/repo.ex",
    "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/lib/mixer_hosted_web/endpoint.ex",
    "hosted/lib/mixer_hosted/application.ex",
    "hosted/mix.exs",
    "hosted/test/test_helper.exs",
    "hosted/test/mixer_hosted_web/customer_workspace_transport_test.exs",
    "hosted/test/mixer_hosted_web/bearer_identity_test.exs",
]
DOCUMENTS = [
    "AGENTS.md",
    "mixer-product-plan.md",
    "verification/console-session-integration-selection/selection.md",
    "verification/console-session-integration-selection/frontend-contract.json",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    "docs/console-cookie-workspace-transport.md",
]
DEPENDENCY_SOURCES = [
    "hosted/deps/plug/lib/plug/conn.ex",
    "hosted/deps/plug/lib/plug/conn/adapter.ex",
    "hosted/deps/plug/lib/plug/adapters/test/conn.ex",
    "hosted/deps/plug/mix.exs",
    "hosted/deps/ecto/lib/ecto/repo.ex",
    "hosted/deps/ecto_sql/lib/ecto/adapters/sql.ex",
]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check(condition, label):
    if not condition:
        raise RuntimeError("source-selection audit failed: " + label)
    checks.append({"name": label, "result": "pass", "scope": "source/proposal only"})


checks = []
manifest = []
current = git("rev-parse", "HEAD").decode().strip()
tree = git("rev-parse", PIN + "^{tree}").decode().strip()
for path in CANONICAL + DOCUMENTS + DEPENDENCY_SOURCES:
    check("callback" not in path and not path.endswith("browser_auth/store.ex")
          and path != ".github/workflows/hosted.yml", "allowed input: " + path)
    data = git("show", PIN + ":" + path) if path in CANONICAL else (ROOT / path).read_bytes()
    observed = (ROOT / path).read_bytes()
    if path in CANONICAL:
        check(data == observed, "canonical pin equals observed worktree: " + path)
        check(data == git("show", current + ":" + path),
              "canonical pin equals current HEAD: " + path)
    target = OUT / "inputs" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    manifest.append({
        "path": path,
        "authority": "canonical git pin" if path in CANONICAL else "observed source/document",
        "revision": PIN if path in CANONICAL else None,
        "bytes": len(data),
        "sha256": sha(data),
        "snapshot": str(target.relative_to(OUT)),
    })

contract = json.loads((OUT / "dispatcher-contract.json").read_text())
frontend = json.loads((OUT / "inputs" / DOCUMENTS[3]).read_text())
check(contract["arity"] == 3 and contract["configuration_options"] == [], "closed dispatcher arity/options")
check(len(contract["operations"]) == 2, "two read-only typed operations")
check(contract["execution"]["worker"] is False, "same-process composition selected")
check(contract["capture"]["network"] is False and contract["capture"]["socket"] is False,
      "local adapter only")
check(contract["capture"]["mailbox_notifications"] is False
      and contract["capture"]["mailbox_drain"] is False, "caller mailbox preserved")
check(contract["capture"]["max_body_bytes"] == 262144, "bounded captured body")
check(contract["response"]["statuses"] == [200, 400, 401, 403, 404, 415, 503],
      "closed ordinary status roster")
check(len(contract["new_product_files"]) == 3 and len(contract["new_test_files"]) == 3,
      "bounded new source/test roster")
check(frontend["server_and_stopped_review_boundary"]["missing_server_facade"].startswith("Sessions.workspace/3"),
      "upstream frontend contract still distinguishes missing Sessions facade")

def frozen(path):
    return (OUT / "inputs" / path).read_text()

check("do: %{operation: operation, facade: CustomerWorkspace, request: Request.init(operation)}"
      in frozen(CANONICAL[0]), "atom controller init fixes canonical facade")
check("ConfiguredVerifier)" in frozen(CANONICAL[2]), "bearer verifier default is ConfiguredVerifier")
check("repo \\\\ MixerHosted.Repo" in frozen("hosted/lib/mixer_hosted/customer_workspace.ex"),
      "workspace facade defaults ordinary Repo")
check("Context.active?() or repo.in_transaction?()" in frozen("hosted/lib/mixer_hosted/customer_workspace/storage.ex"),
      "ordinary nested-transaction/context refusal remains canonical")
check("owner && send(owner, @already_sent)" in frozen("hosted/deps/plug/lib/plug/conn.ex"),
      "Plug caller notification is conditional on owner")
check("Process.get({__MODULE__, :dynamic_repo}, @default_dynamic_repo)"
      in frozen("hosted/deps/ecto/lib/ecto/repo.ex"), "Ecto dynamic Repo is caller-local")
check("is_list(values) and length(values) <= 64" in frozen("hosted/lib/mixer_hosted/identity/bounded_json.ex"),
      "identity decoder cannot admit 100-row page arrays")

write_json("inputs.json", manifest)
write_json("source-checks.json", {"status": "passed-source-selection-only", "checks": checks,
                                "not_runtime_tests": True})
selected_digest = sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())
receipt = {
    "schema": 1,
    "status": "frozen-source-proposal-no-product-execution",
    "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": PIN,
    "source_tree": tree,
    "observed_head_at_freeze": current,
    "head_advanced_from_pin": current != PIN,
    "known_head_advance": "Root reported unrelated accepted console-session + verify.yml delivery. All selected canonical inputs were separately compared with current HEAD and observed worktree.",
    "selected_input_manifest_sha256": selected_digest,
    "tools": {"python": platform.python_version(), "python_executable": sys.executable,
              "git": git("--version").decode().strip(), "plug_source_version": "1.20.3"},
    "commands": [
        {"command": "targeted cat/sed/rg reads of listed canonical/default/source/proposal inputs", "scope": "read-only source selection", "exit": "selected reads succeeded except missing configured_verifier_test.exs (not an existing test path); not treated as a pass"},
        {"command": "initial rg --files search including verification and git status --short", "scope": "source/path discovery only", "output": "oversized/truncated; narrowed subsequent reads; no listed callback/review path content imported or executed"},
        {"command": "python3 verification/console-fixed-workspace-dispatcher-selection/audit.py", "scope": "stdlib hashing/JSON and literal source observations only", "exit": 0},
        {"command": "git rev-parse HEAD; git rev-parse <pin>^{tree}; git show <pin>:<allowlisted-path>; git show HEAD:<allowlisted-path>; git --version", "scope": "read-only exact source custody"},
        {"command": "git status --short --untracked-files=no; python3 --version", "scope": "read-only version/tracked-state inventory"}
    ],
    "execution": {"compiler": False, "mix": False, "beam_or_product_tests": False,
                  "postgresql": False, "network": False, "callback_review_or_harness": False,
                  "browser_ui_capture": False, "native_runtime": False, "git_mutation": False,
                  "canonical_product_edits": False},
    "resources": {"owned_service_or_native_processes_started": 0, "cleanup": "not applicable; only foreground source/shell/Python inspection processes", "other_projects_processes": "untouched"},
    "pending": contract["pending"],
    "checks_passed": len(checks),
    "claim_limit": "source selection and immutable custody only; no runtime/authentication/independent callback/production/customer/W14/GA acceptance"
}
write_json("receipt.json", receipt)
summary = "Passed " + str(len(checks)) + " bounded source/proposal checks. No product, compiler, BEAM, database, network or callback harness execution.\n"
summary += "Pinned revision " + PIN + "; observed HEAD " + current + ".\n"
(OUT / "audit.stdout.txt").write_text(summary)
seal = []
for path in sorted(OUT.rglob("*")):
    if path.is_file() and path.name != "freeze.json":
        data = path.read_bytes()
        seal.append({"path": str(path.relative_to(OUT)), "bytes": len(data), "sha256": sha(data)})
write_json("freeze.json", {"schema": 1, "files": seal,
                          "manifest_sha256": sha(json.dumps(seal, sort_keys=True, separators=(",", ":")).encode())})
print(summary, end="")
