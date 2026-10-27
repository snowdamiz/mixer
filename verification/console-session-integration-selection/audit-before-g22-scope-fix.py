"""Bounded read-only source/receipt selection audit; never authentication evidence."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
START = time.monotonic()
COMMANDS = []


def git(*args: str) -> bytes:
    if time.monotonic() - START > 45:
        raise RuntimeError("source selection audit exceeded its bounded work window")
    command = ["git", *args]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=5)
    COMMANDS.append({"argv": command, "exit_code": result.returncode,
                     "stdout": result.stdout.decode("utf-8"),
                     "stderr": result.stderr.decode("utf-8")})
    result.check_returncode()
    return result.stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


revision = git("rev-parse", "HEAD").decode().strip()
tree = git("rev-parse", "HEAD^{tree}").decode().strip()
tool_version = git("--version").decode().strip()
canonical_paths = [
    "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/lib/mixer_hosted_web/endpoint.ex",
    "hosted/lib/mixer_hosted/application.ex",
    "hosted/lib/mixer_hosted/browser_auth/store.ex",
    "hosted/lib/mixer_hosted/browser_auth/runtime_owner.ex",
]
worktree_paths = [
    "AGENTS.md", "PLAN.md", "mixer-product-plan.md", "gates/ga.json",
    "console/src/main.tsx", "console/src/App.tsx",
    "console/src/state/workspace-context.tsx",
    "console/src/state/workspace-controller.ts",
    "console/src/state/workspace-binding.ts",
    "console/src/api/cookie-workspace-client.ts",
    "console/src/api/workspace-client.ts",
    "docs/console-identity-flow-contract.md",
    "docs/console-cookie-workspace-transport.md",
    "docs/hosted-browser-auth-protocol.md",
    "docs/hosted-browser-session-integration.md",
    "docs/hosted-browser-session-storage-contract.md",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
    "docs/hosted-browser-callback-storage.md",
    "docs/hosted-browser-callback-storage-review.md",
    "docs/hosted-browser-callback-ci.md",
    "verification/hosted-browser-callback-storage-review/interrupted-cleanup.json",
    "verification/console-workspace-composition/root-acceptance/receipt.json",
]
data = {}
inputs = []
for path in canonical_paths:
    raw = git("show", f"{revision}:{path}")
    data[path] = raw.decode()
    inputs.append({"path": path, "authority": "canonical-git-revision",
                   "sha256": sha(raw), "bytes": len(raw)})
for path in worktree_paths:
    raw = (ROOT / path).read_bytes()
    data[path] = raw.decode()
    inputs.append({"path": path, "authority": "observed-worktree-source-or-status",
                   "sha256": sha(raw), "bytes": len(raw)})

gates = json.loads(data["gates/ga.json"])


def named(obj: object, key: str) -> list:
    found = []
    if isinstance(obj, dict):
        for name, value in obj.items():
            if name == key:
                found.append(value)
            else:
                found.extend(named(value, key))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(named(value, key))
    return found


candidates = named(gates, "callbackStorageCandidate")
assert len(candidates) == 1, "expected one recorded callback candidate status"
candidate = candidates[0]
cleanup = json.loads(data["verification/hosted-browser-callback-storage-review/interrupted-cleanup.json"])
router = data[canonical_paths[0]]
owner = data[canonical_paths[4]]
store = data[canonical_paths[3]]
client = data["console/src/api/cookie-workspace-client.ts"]
checks = {
    "main_has_no_workspace_session": "render(() => <App />, container);" in data["console/src/main.tsx"],
    "app_has_existing_session_seam": "session={props.workspaceSession}" in data["console/src/App.tsx"],
    "provider_uses_live_session_accessor": "createWorkspaceBinding(() => props.session)" in data["console/src/state/workspace-context.tsx"],
    "cookie_client_has_two_fixed_routes": all(path in client for path in ["/console-api/v1/orgs", "/console-api/v1/projects"]),
    "canonical_router_has_no_auth_or_console_api": "/auth/" not in router and "/console-api/" not in router,
    "canonical_router_uses_bearer_workspace_pipeline": all(term in router for term in ["BearerIdentity", 'scope "/v3"', 'get("/orgs"', 'get("/projects"']),
    "canonical_application_does_not_wire_browser_owner": "BrowserAuth" not in data[canonical_paths[2]],
    "canonical_owner_preauthed_load_only": ":preauth <- envelope.context.purpose" in owner and "%Vault.Preauth{csrf: csrf}" in owner,
    "canonical_store_has_no_callback_candidate_operations": all(f"def {name}(" not in store for name in ["discover_callback", "claim", "provider_reject", "activate", "logout"]),
    "callback_independent_review_interrupted_zero_pg16": candidate["independent_review"]["status"] == "incomplete-interrupted-no-acceptance" and candidate["independent_review"]["pg16_methods_run"] == 0,
    "callback_ci_is_not_independent_acceptance": candidate["ci_validation"]["independent_acceptance"] is False,
    "recorded_callback_cleanup_without_controls": cleanup["all_owned_resources_absent"] is True and cleanup["review_controls_executed"] is False,
    "canonical_revision_unchanged_during_audit": git("rev-parse", "HEAD").decode().strip() == revision,
}
write("inputs.json", inputs)
write("source-checks.json", checks)
write("recorded-callback-status.json", candidate)
summary = (f"Source selection audit: {sum(checks.values())}/{len(checks)} checks pass.\n"
           f"Canonical revision: {revision}\n"
           "No authentication, callback acceptance, runtime, provider, deployment or GA result is established.\n"
           "Only source/receipt reads and bounded Python hashing/JSON/source assertions ran.\n")
(OUT / "audit.stdout.txt").write_text(summary)
write("receipt.json", {
    "schema": 1,
    "scope": "W14 source-only production session integration selection; no product source edits",
    "revision": revision, "git_tree": tree,
    "selected_input_tree_sha256": sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()),
    "command": [sys.executable, "-B", "verification/console-session-integration-selection/audit.py"],
    "tools": {"python": platform.python_version(), "git": tool_version},
    "commands": COMMANDS,
    "owner_pid": os.getpid(), "elapsed_seconds": time.monotonic() - START,
    "hard_child_command_timeout_seconds": 5,
    "source_check_count": len(checks), "source_check_passed": sum(checks.values()),
    "source_checks_are_runtime_or_authentication_acceptance": False,
    "cleanup": {"all_git_read_children_waited": True, "servers_started": 0,
                "native_ui_capture_browser_phone_processes_started": 0,
                "compiler_or_test_binaries_started": 0, "scratch_created": False,
                "process_inventory_performed": False, "network_or_git_mutation_performed": False},
    "limitations": ["No live HTTP endpoint/session/provider operation",
                    "No stopped callback review/harness rerun or delegation",
                    "Protected dirty Store/workflow/callback sources never executed",
                    "No product compiler/test binary run",
                    "Native/UI/capture/browser/phones remain paused",
                    "Independent callback acceptance, main integration, UnitB, provider, session lifecycle and startup remain pending"],
})
print(summary, end="")
if not all(checks.values()):
    raise SystemExit(1)
