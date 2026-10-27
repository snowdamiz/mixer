#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Source-only pin preparation. Does not launch a compiler or product code."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ORDINARY = [
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/verifier.ex",
    "hosted/lib/mixer_hosted/identity/admission.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/trust_snapshot.ex",
    "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
    "hosted/lib/mixer_hosted/identity/global_address.ex",
    "hosted/lib/mixer_hosted/identity/dns_resolver.ex",
    "hosted/lib/mixer_hosted/identity/bounded_tcp.ex",
    "hosted/lib/mixer_hosted/identity/http_wire_guard.ex",
    "hosted/lib/mixer_hosted/identity/http_freshness.ex",
    "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
    "hosted/lib/mixer_hosted/identity/fetch_flight.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/context.ex",
    "hosted/lib/mixer_hosted/customer_workspace/input.ex",
    "hosted/lib/mixer_hosted/customer_workspace/storage.ex",
    "hosted/lib/mixer_hosted/customer_workspace.ex",
    "hosted/lib/mixer_hosted/repo.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex",
    "hosted/lib/mixer_hosted_web/customer_workspace_controller.ex",
]
PRODUCT = [
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/request.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher/capture_adapter.ex",
    "hosted/lib/mixer_hosted_web/browser_workspace_dispatcher.ex",
]
TESTS = [
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_request_test.exs",
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_capture_adapter_test.exs",
    "hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs",
]
DEPENDENCIES = ["decimal", "jason", "telemetry", "mime", "plug_crypto", "plug", "db_connection", "ecto", "postgrex", "ecto_sql", "jose", "hpax", "mint"]

def pin(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

lock = (ROOT / "hosted/mix.lock").read_text()
dependencies = []
for name in DEPENDENCIES:
    ebin = ROOT / f"hosted/_build/test/lib/{name}/ebin"
    app = (ebin / f"{name}.app").read_text()
    version = re.search(r'\{vsn,\s*"([^"]+)"\}', app).group(1)
    lock_line = next(line.strip() for line in lock.splitlines() if line.lstrip().startswith(f'"{name}":'))
    if f'"{version}"' not in lock_line:
        raise SystemExit("dependency version mismatch")
    files = sorted(p for p in ebin.iterdir() if p.suffix in (".beam", ".app"))
    dependencies.append({"name": name, "version": version, "lock_entry": lock_line, "files": [pin(p) for p in files]})

elixir = Path("/opt/homebrew/Cellar/elixir/1.20.4")
erlang = Path("/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang")
tool_files = [
    Path("/opt/homebrew/opt/python@3.14/bin/python3.14").resolve(),
    elixir / "bin/elixir", erlang / "bin/erl", erlang / "erts-17.1/bin/erlexec", erlang / "erts-17.1/bin/beam.smp",
    erlang / "releases/29/OTP_VERSION",
]
for app in ["elixir", "eex", "logger", "mix", "ex_unit"]:
    tool_files.extend(sorted((elixir / f"lib/elixir/lib/{app}/ebin").glob("*.beam")))
    tool_files.extend(sorted((elixir / f"lib/elixir/lib/{app}/ebin").glob("*.app")))

plan = {
    "schema": 1,
    "status": "prepared-awaiting-root-compiler-and-host-release",
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
    "runner_argv": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "verification/console-fixed-workspace-dispatcher/run_host_tests_attempt_2.py"],
    "runner_sha256": hashlib.sha256((OUT / "run_host_tests_attempt_2.py").read_bytes()).hexdigest(),
    "inner_argv_template": [str(elixir / "bin/elixir"), "--no-color", "--erl", "+S 2:2 +A 2", "{scratch}/run.exs"],
    "ordinary_source_closure": [pin(ROOT / p) for p in ORDINARY],
    "new_product_sources": [pin(ROOT / p) for p in PRODUCT],
    "selected_test_sources": [pin(ROOT / p) for p in TESTS],
    "dependencies": dependencies,
    "tool_files": [pin(p) for p in tool_files],
    "tools": {"elixir": "1.20.4", "erlang_package": "29.1.1_2", "otp": (erlang / "releases/29/OTP_VERSION").read_text().strip(), "python": "3.14"},
    "limits": {"work_wall_seconds": 50, "owned_cleanup_seconds": 5, "total_child_seconds": 55, "combined_output_bytes": 196608, "per_test_ms": 5000, "schedulers": "2:2", "async_threads": 2, "exunit_max_cases": 1},
    "execution_policy": {"code_paths": "Only individually verified dependency beams are copied into owned scratch; no shared _build path or mixer_hosted app beams", "application_boot": "No product/dependency application start or ensure_all_started, no Mix project/task/loadconfig. ExUnit.start starts the test framework only. Mix.State.start_link([]) supports canonical compile-time Mix.env()==:prod guards without starting the Mix application; loaded dependency app metadata is not started", "sources": "Frozen ordinary closure and selected six files only; compile into fresh owned scratch", "environment": "Sanitized; no inherited ERL_LIBS/ERL_FLAGS/ERL_AFLAGS/ELIXIR_ERL_OPTIONS; MIX_ENV=prod", "resources": "No database, container, network, provider, browser-auth/callback, UI/capture or native runtime; delete scratch and observe absence in outer finally; record PID/PGID, reap direct child and prove exact killpg(pid,0) absence, including remaining group after leader exit", "evidence": "Refuse existing output/bootstrap/receipt before run; create retained evidence exclusively; verify copied source/dependency bytes and postrun original input hashes"},
    "host_test_roster": {"request": "Six tests: limits 1/65/100, canonical cursor and exact ID encoding roundtrip via labelled synthetic identity, closed shapes/IDs/cross-scope cursor refusal", "capture": "Seven tests: empty read/one send, binary/nested iodata bounds, invalid/double/unsupported mode failures, mailbox unchanged, labelled synthetic trusted-facade canonical controller positive 65/100/project pages and ordinary denials/invalid rows", "dispatcher": "Six tests: only arity3/no injection, early invalid shapes, wrong dynamic Repo no reset, actual ConfiguredVerifier absent default owner redacted503/no Repo start, canonical malformed-token400, request ID/process dictionary/mailbox continuity"},
    "pending": ["actual default verifier/default Repo 200", "ordinary database/RLS/commit/revocation/context integration", "callback Unit A/lifecycle and active token provenance", "provider/startup/custody", "cookie route and HTTP/log/ingress qualification", "customer workflows/W14/G22/GA"]
}
(OUT / "execution-plan-attempt-2.json").write_text(json.dumps(plan, indent=2) + "\n")
print(json.dumps({"ordinary_sources": len(ORDINARY), "new_sources": len(PRODUCT), "tests": len(TESTS), "dependency_files": sum(len(d["files"]) for d in dependencies), "tool_files": len(tool_files), "plan_sha256": hashlib.sha256((OUT / "execution-plan-attempt-2.json").read_bytes()).hexdigest()}, indent=2))
