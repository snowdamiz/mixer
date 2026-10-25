#!/usr/bin/env python3
"""Explicit workspace/artifact transport snapshot with pinned deps; no full app build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
# Explicit source ownership allowlist. No recursive application source collector.
SOURCES = [
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/verifier.ex",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/trust_snapshot.ex",
    "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
    "hosted/lib/mixer_hosted/identity/global_address.ex",
    "hosted/lib/mixer_hosted/identity/dns_resolver.ex",
    "hosted/lib/mixer_hosted/identity/http_freshness.ex",
    "hosted/lib/mixer_hosted/identity/http_wire_guard.ex",
    "hosted/lib/mixer_hosted/identity/bounded_tcp.ex",
    "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
    "hosted/lib/mixer_hosted/identity/fetch_flight.ex",
    "hosted/lib/mixer_hosted/identity/admission.ex",
    "hosted/lib/mixer_hosted/identity/key_owner.ex",
    "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/identity/configured_verifier.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_json.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex",
    "hosted/lib/mixer_hosted_web/customer_artifact_controller.ex",
    "hosted/lib/mixer_hosted_web/customer_workspace_controller.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex",
    "hosted/lib/mixer_hosted_web/health_controller.ex",
    "hosted/lib/mixer_hosted_web/router.ex",
    "verification/hosted-customer-workspace-http/transport_defaults.ex",
]
TEST = "hosted/test/mixer_hosted_web/customer_workspace_transport_test.exs"
REGRESSION = "hosted/test/mixer_hosted_web/customer_artifact_transport_test.exs"
DEPENDENCIES = {
    "telemetry": "1.4.2", "mime": "2.0.7", "plug_crypto": "2.2.1",
    "plug": "1.20.3", "jason": "1.4.5", "jose": "1.11.12",
    "phoenix_pubsub": "2.4.1", "phoenix_template": "1.1.0",
    "websock": "0.5.3", "hpax": "1.1.0", "thousand_island": "1.6.0",
    "bandit": "1.13.1", "websock_adapter": "0.6.0", "phoenix": "1.8.16",
    "mint": "1.11.0",
}

def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    existing = [int(p.name[4:]) for p in EVIDENCE.glob("run-*") if p.name[4:].isdigit()]
    run = EVIDENCE / f"run-{max(existing, default=0) + 1}"
    run.mkdir()
    manifest = {}
    for name in SOURCES + [TEST, REGRESSION, "hosted/mix.lock", str(Path(__file__).relative_to(ROOT))]:
        data = (ROOT / name).read_bytes()
        destination = run / "inputs" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        manifest[name] = digest(data)
    (run / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    lock = (run / "inputs/hosted/mix.lock").read_text()
    dep_paths = []
    for name, version in DEPENDENCIES.items():
        match = re.search(rf'"{re.escape(name)}": \{{:hex, :{re.escape(name)}, "([^"]+)"', lock)
        if not match or match.group(1) != version:
            raise RuntimeError(f"dependency lock mismatch for {name}: expected {version}")
        path = ROOT / "hosted/_build/test/lib" / name / "ebin"
        if not path.is_dir():
            raise RuntimeError(f"missing pinned dependency ebin: {name}")
        dep_paths.append(path)
    dependency_beams = {
        str(beam.relative_to(ROOT)): digest(beam.read_bytes())
        for path in dep_paths
        for beam in sorted(path.iterdir())
        if beam.is_file()
    }
    (run / "dependency-beams.json").write_text(json.dumps(dependency_beams, indent=2) + "\n")
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="mixer-customer-workspace-http-") as scratch_name:
        scratch = Path(scratch_name)
        runner = scratch / "runner.exs"
        sources = [str(run / "inputs" / name) for name in SOURCES]
        elixir_sources = json.dumps(sources)
        expected_deps = "%{" + ", ".join(f":{name} => {json.dumps(version)}" for name, version in DEPENDENCIES.items()) + "}"
        runner.write_text(f'''Mix.start()
Mix.env(:test)
for {{app, expected}} <- {expected_deps} do
  :ok = Application.load(app)
  actual = Application.spec(app, :vsn) |> to_string()
  if actual != expected, do: raise("dependency runtime version mismatch: #{{app}}")
end
Application.put_env(:phoenix, :json_library, Jason)
{{:ok, _}} = Application.ensure_all_started(:phoenix)
{{:ok, _, []}} = Kernel.ParallelCompiler.compile({elixir_sources}, return_diagnostics: true)
ExUnit.start(seed: 0)
Code.require_file({json.dumps(str(run / 'inputs' / TEST))})
Code.require_file({json.dumps(str(run / 'inputs' / REGRESSION))})
''')
        (run / "runner.exs").write_text(runner.read_text())
        command = ["elixir"]
        for path in dep_paths:
            command.extend(["-pa", str(path)])
        command.append(str(runner))
        versions = subprocess.run(["elixir", "--version"], text=True, capture_output=True, check=True)
        (run / "tool-versions.txt").write_text(versions.stdout + versions.stderr + sys.version + "\n")
        (run / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        environment = dict(os.environ, ERL_FLAGS="+S 2:2")
        owned = ["hosted/lib/mixer_hosted_web/customer_workspace_controller.ex", "hosted/lib/mixer_hosted_web/plugs/customer_workspace_request.ex", "hosted/lib/mixer_hosted_web/router.ex", TEST, "verification/hosted-customer-workspace-http/transport_defaults.ex"]
        formatting = ["mix", "format", "--check-formatted", *[str(run / "inputs" / name) for name in owned]]
        formatted = subprocess.run(formatting, cwd=scratch, env=environment, text=True, capture_output=True, timeout=30)
        (run / "format-output.txt").write_text(formatted.stdout + formatted.stderr)
        (run / "format-command.json").write_text(json.dumps(formatting, indent=2) + "\n")
        result = subprocess.run(command, cwd=scratch, env=environment, text=True, capture_output=True, timeout=120)
        (run / "output.txt").write_text(result.stdout + result.stderr)
        receipt = {
            "scope": "Standalone workspace and existing artifact Plug transport; trusted fixture facades/verifier, production router missing-auth checks. Default domain facades are explicit standalone declarations that must not be called. No real socket/database/default verifier acceptance/workspace policy/signing/deployment/device/GA qualification.",
            "source_tree_sha256": digest(json.dumps(manifest, sort_keys=True).encode()),
            "source_revision": args.source_revision,
            "revision_provenance": "root-supplied repair HEAD context; copied per-file hashes bind working additions",
            "format_exit_code": formatted.returncode,
            "exit_code": result.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "source_allowlist": SOURCES,
            "test_source": TEST,
            "artifact_regression_test": REGRESSION,
            "dependency_versions": DEPENDENCIES,
            "dependency_manifest_sha256": digest((run / "dependency-beams.json").read_bytes()),
            "application_ebin_loaded": False,
            "forbidden_lane_sources_read_compiled_or_executed": False,
            "native_or_capture_processes_started": False,
            "services_started": [],
            "live_source_changes_during_run": [name for name, expected in manifest.items() if digest((ROOT / name).read_bytes()) != expected],
            "scratch_cleanup": "TemporaryDirectory removed after subprocess completion",
        }
    receipt["scratch_removed"] = not scratch.exists()
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout + result.stderr)
    print(json.dumps({"run": str(run.relative_to(ROOT)), "exit_code": result.returncode, "scratch_removed": receipt["scratch_removed"]}))
    return result.returncode or formatted.returncode


if __name__ == "__main__":
    raise SystemExit(main())
