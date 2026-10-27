"""Collect bounded independent preaccess inputs; never import/run candidate code."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OWN = ROOT / "verification/console-browser-session-consumer-independent"
COMMANDS: list[dict[str, object]] = []


def command(arguments: list[str]) -> bytes:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True, check=False)
    COMMANDS.append({
        "argv": arguments,
        "returncode": result.returncode,
        "stdout_bytes": len(result.stdout),
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr": result.stderr.decode("utf-8", errors="replace"),
    })
    if result.returncode:
        raise RuntimeError(f"Read-only custody command failed: {arguments[0]}")
    return result.stdout


def digest(data: bytes) -> dict[str, object]:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


revision = "b231f3d405c06bfb348f193d46a348af0529bd84"
tree = command(["git", "rev-parse", f"{revision}^{{tree}}"]).decode().strip()
observed_head = command(["git", "rev-parse", "HEAD"]).decode().strip()
git_version = command(["git", "--version"]).decode().strip()

released_paths = [
    "AGENTS.md",
    "verification/console-session-integration-selection/frontend-contract.json",
    "verification/console-session-integration-selection/selection.md",
    "verification/console-session-and-checkout-root-review/acceptance.json",
]
released = []
for path in released_paths:
    data = (ROOT / path).read_bytes()
    released.append({"path": path, "source": "released-working-tree-input", **digest(data)})

acceptance = json.loads((ROOT / released_paths[-1]).read_bytes())
contract_digest = released[1]["sha256"]
assert acceptance["session_selection"]["contract"]["sha256"] == contract_digest
assert acceptance["session_selection"]["status"] == "closed-frontend-contract-selected-implementation-active"
assert acceptance["revision"] == revision

canonical_paths = [
    "console/src/App.tsx",
    "console/src/state/workspace-context.tsx",
    "console/src/state/workspace-controller.ts",
    "console/src/state/workspace-binding.ts",
    "console/src/api/cookie-workspace-client.ts",
    "console/src/api/workspace-transport.ts",
    "console/src/api/workspace-client.ts",
    "console/src/domain/workspace-directory.ts",
    "console/package.json",
]
canonical = []
for path in canonical_paths:
    data = command(["git", "show", f"{revision}:{path}"])
    canonical.append({"path": path, "source": f"git-show:{revision}:{path}", **digest(data)})

oracle = OWN / "preaccess-oracles.md"
manifest = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "preaccess-preparation-complete-candidate-sealed-execution-not-authorized",
    "scope": "Independent contract oracles and bounded canonical source custody only",
    "revision": revision,
    "tree": tree,
    "observed_head_at_collection": observed_head,
    "baseline_policy": "Initial HEAD source reads were at revision; subsequent custody pinned to that revision after concurrent root delivery advanced HEAD.",
    "collector_command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))],
    "python": sys.version,
    "git": git_version,
    "released_inputs": released,
    "canonical_inputs": canonical,
    "frozen_oracles": {"path": str(oracle.relative_to(ROOT)), **digest(oracle.read_bytes())},
    "candidate_access": {
        "product": False,
        "producer_tests": False,
        "producer_evidence": False,
        "working_tree_main_tsx": False,
    },
    "root_selection": {
        "status": acceptance["session_selection"]["status"],
        "backend_session_and_cookie_routes_exist": acceptance["session_selection"]["backend_session_and_cookie_routes_exist"],
        "authenticated_workspace_accepted": acceptance["session_selection"]["authenticated_workspace_accepted"],
        "stopped_callback_review_replayed": acceptance["session_selection"]["stopped_callback_review_replayed"],
    },
    "activity": {
        "compiler_or_test_runtime": False,
        "browser_ui_capture_native": False,
        "global_inventory": False,
        "stopped_callback_or_android_retry": False,
        "git_mutation": False,
        "hosted_edit_or_new_dependency": False,
    },
    "cleanup": {"owned_native_browser_capture_processes_started": 0, "owned_compiler_test_processes_started": 0, "disposable_instances_started": 0},
    "pending": ["root candidate release", "root targeted execution allocation", "candidate source review", "independent host probes", "implementation acceptance"],
    "GA_gates_verified": 0,
    "commands": COMMANDS,
}
(OWN / "preaccess-custody.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"status": manifest["status"], "revision": revision, "released_inputs": len(released), "canonical_inputs": len(canonical), "oracle_sha256": manifest["frozen_oracles"]["sha256"], "candidate_access": manifest["candidate_access"], "compiler_or_test_runtime": False, "GA_gates_verified": 0}))
