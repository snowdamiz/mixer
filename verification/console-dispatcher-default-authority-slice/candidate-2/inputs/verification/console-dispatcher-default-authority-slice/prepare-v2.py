#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Freeze source/dependency/tool bytes only. Never launch a compiler or service."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
BASELINE = ROOT / "verification/console-fixed-workspace-dispatcher/execution-plan-attempt-3.json"
PRODUCT = [
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex",
]
ADDITIONAL = [
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
    "hosted/test/support/identity_tls_fixture.ex",
]
OWNED = ["default_authority_test-v2.exs", "provision.sql", "bootstrap-v2.exs", "prepare-v2.py", "run-v2.py", "README-v2.md"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": path.stat().st_size, "sha256": sha(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, choices=["candidate-2", "candidate-3"])
    args = parser.parse_args()
    destination = PACKET / args.candidate
    destination.mkdir(exist_ok=False)
    baseline = json.loads(BASELINE.read_text())
    sources = [entry["path"] for entry in baseline["ordinary_source_closure"]] + PRODUCT + ADDITIONAL
    assert len(sources) == 36 and len(set(sources)) == 36
    assert not any(part in name for name in sources for part in ("browser_auth", "callback", "endpoint.ex", "router.ex", "application.ex"))
    dependencies = []
    for dependency in baseline["dependencies"]:
        files = [pin(ROOT / entry["path"]) for entry in dependency["files"]]
        dependencies.append({**dependency, "files": files})
    tools = [pin(Path(entry["path"])) for entry in baseline["tool_files"]]
    pg = Path("/opt/homebrew/opt/postgresql@17/bin").resolve()
    for executable in ["initdb", "postgres", "psql", "pg_ctl"]:
        tools.append(pin(pg / executable))
    tools.append(pin(Path("/usr/bin/openssl")))
    selected = sources + [str((PACKET / name).relative_to(ROOT)) for name in OWNED]
    selected += ["hosted/mix.lock", str(BASELINE.relative_to(ROOT)),
                 "verification/console-fixed-dispatcher-format-correction/source-after.json",
                 "verification/console-fixed-dispatcher-format-correction/receipt.json"]
    inputs = [pin(ROOT / name) for name in selected]
    for entry in inputs:
        target = destination / "inputs" / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / entry["path"], target)
        assert sha(target) == entry["sha256"]
    plan = {
        "schema": 1,
        "status": "source-frozen-runtime-not-released-v2",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "source_roster": sources,
        "selected_inputs": inputs,
        "dependencies": dependencies,
        "tool_files": tools,
        "runner_sha256": sha(PACKET / "run-v2.py"),
        "tools": {**baseline["tools"], "postgresql": "17 expected; exact version unobserved until released version command",
                  "openssl": "pinned /usr/bin/openssl; exact version unobserved until released version command"},
        "postgres_bin": str(pg),
        "argv": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", str((PACKET / "run-v2.py").relative_to(ROOT)), "--candidate", args.candidate],
        "environment": {
            "inherited": [],
            "PATH": "/opt/homebrew/Cellar/erlang/29.1.1_2/bin:/opt/homebrew/Cellar/elixir/1.20.4/bin:/usr/bin:/bin",
            "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "MIX_ENV": "test",
            "HOME": "{scratch}/home", "TMPDIR": "{scratch}/tmp", "ERL_CRASH_DUMP": "/dev/null",
            "MIXER_DISPATCHER_DEFAULT_TEST_PORT": "{owned_loopback_postgres_port}",
            "MIXER_DISPATCHER_DEFAULT_EVIDENCE": "{candidate}/execution"
        },
        "limits": {"total_work_seconds": 50, "owned_cleanup_seconds": 5, "combined_output_bytes": 262144,
                   "per_test_ms": 10000, "max_cases": 1, "schedulers": "2:2", "async_threads": 2},
        "test_roster": [
            "DA01 actual default ConfiguredVerifier and restricted default Repo organization/project success; foreign/missing tenant denials",
            "DA02 real database pagination, canonical cursor, exact special-character organization bytes and cross-organization cursor refusal",
            "DA03 actual default verifier wrong-signature/audience/expired-token 401 and missing-workspace-scope 403",
            "DA04 committed role revision then membership revocation with the same still-cryptographically-valid bearer",
            "DA05 six current database identity controls: profile/binding/principal/family/credential active flags and credential expiry",
            "DA06 forced-RLS default runtime role, no outside-context rows or UPDATE privilege, repeated clean successful reads",
            "DA07 inherited default transaction and wrong dynamic Repo refusal; no repair and recovery to successful default reads"
        ],
        "proposed_commands": [
            ["/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir", "--erl", "+S 2:2 +A 2", "--version"],
            [str(pg / "postgres"), "--version"],
            ["/usr/bin/openssl", "version"],
            [str(pg / "initdb"), "-D", "{scratch}/pg", "-U", "mixer_dispatcher_fixture", "-A", "trust", "--no-locale", "-E", "UTF8"],
            [str(pg / "postgres"), "-D", "{scratch}/pg", "-h", "127.0.0.1", "-p", "{owned_port}", "-k", "", "-c", "timezone=UTC", "-c", "max_connections=15"],
            [str(pg / "psql"), "-X", "-A", "-t", "-h", "127.0.0.1", "-p", "{owned_port}", "-U", "mixer_dispatcher_fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "SHOW data_directory"],
            [str(pg / "psql"), "-X", "-h", "127.0.0.1", "-p", "{owned_port}", "-U", "mixer_dispatcher_fixture", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-f", "{scratch}/inputs/verification/console-dispatcher-default-authority-slice/provision.sql"],
            ["/opt/homebrew/Cellar/elixir/1.20.4/bin/elixir", "--no-color", "--erl", "+S 2:2 +A 2", "{-pa each copied dependency ebin}", "{scratch}/inputs/verification/console-dispatcher-default-authority-slice/bootstrap-v2.exs", "{scratch}/sources.json", "{scratch}/inputs/verification/console-dispatcher-default-authority-slice/default_authority_test-v2.exs", "{scratch}/app-ebin", "{scratch}/dependency-metadata.json"]
        ],
        "prerequisites": [
            "Root exact plan release and exclusive compiler/runtime reservation",
            "Existing pinned ordinary dependencies and platform tools; no deps.get/shared build",
            "Dedicated loopback PostgreSQL cluster and loopback JWKS TLS fixture are permitted after release",
            "Readonly SHOW data_directory must equal exact scratch/pg with the owned postgres alive before any role/database/schema mutation",
            "Existing test-only KeyOwner.start_fixture and normal FetchFlight refresh; no canonical source prerequisite"
        ],
        "cleanup_policy": [
            "Record every directly launched PID and its newly owned process group; bounded output and one total work deadline",
            "Stop/reap test child and exact remaining owned group; no process-name/global inventory or signaling",
            "Send SIGINT only to owned postgres child, reap then remove exact leftover owned group within cleanup deadline",
            "Observe dedicated loopback PostgreSQL/TLS port closure and exact owned PGID absence; preserve scratch on incomplete server cleanup",
            "Verify ExUnit component cleanup, named default Repo/owner/Admission absence, TLS ephemeral key directory removal",
            "Delete only scratch created by this invocation; retain all outputs/failure receipts and frozen inputs; rehash original selected inputs"
        ],
        "pending": [
            "Candidate compilation, seven tests, database/fixture startup and all cleanup are unrun",
            "No race/lock/commit-fault matrix beyond stated sequential committed state changes and inherited transaction control",
            "No production identity provider/public DNS/startup/custody, browser_auth/callback/session/cookie authority, Endpoint/Router/HTTP integration",
            "No Neon/Cloudflare deployment, customer workflow, publication, G22 or any GA acceptance",
            "Computer use, capture and native simulator/emulator runtime paused; physical phones disconnected"
        ]
    }
    (destination / "execution-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    freeze = {"execution_plan_sha256": sha(destination / "execution-plan.json"),
              "source_tree_sha256": hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
              "runtime_started": False, "source_files": len(sources), "test_methods": 7,
              "dependency_files": sum(len(item["files"]) for item in dependencies)}
    (destination / "preexecution-freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps(freeze, sort_keys=True))


if __name__ == "__main__":
    main()
