#!/usr/bin/env python3
"""Exact signed workspace scope recognition and complete pure token verifier regressions."""
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
SOURCES = ['hosted/lib/mixer_hosted/identity/verified_identity.ex', 'hosted/lib/mixer_hosted/identity/encoding.ex', 'hosted/lib/mixer_hosted/identity/bounded_json.ex', 'hosted/lib/mixer_hosted/identity/manifest.ex', 'hosted/lib/mixer_hosted/identity/trust_snapshot.ex', 'hosted/lib/mixer_hosted/identity/access_token_verifier.ex']
TESTS = ['hosted/test/mixer_hosted/identity/access_token_verifier_test.exs']
DEPENDENCIES = {'jason': '1.4.5', 'jose': '1.11.12'}

def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    existing = [int(p.name[4:]) for p in EVIDENCE.glob("run-*") if p.name[4:].isdigit()]
    run = EVIDENCE / f"run-{max(existing, default=0) + 1}"
    run.mkdir()
    manifest = {}
    for name in SOURCES + TESTS + ["hosted/mix.lock", str(Path(__file__).relative_to(ROOT))]:
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
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="mixer-customer-artifact-http-") as scratch_name:
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
Application.put_env(:jose, :json_module, :jose_json_jason)
Application.put_env(:jose, :unsecured_signing, false)
Application.put_env(:jose, :crypto_fallback, false)
{{:ok, _}} = Application.ensure_all_started(:jose)
{{:ok, _, %{{compile_warnings: [], runtime_warnings: []}}}} = Kernel.ParallelCompiler.compile({elixir_sources}, return_diagnostics: true)
ExUnit.start(seed: 0)
for path <- {json.dumps([str(run / "inputs" / test) for test in TESTS])}, do: Code.require_file(path)
''')
        (run / "runner.exs").write_text(runner.read_text())
        command = ["elixir"]
        for path in dep_paths:
            command.extend(["-pa", str(path)])
        command.append(str(runner))
        versions = subprocess.run(["elixir", "--version"], text=True, capture_output=True, check=True)
        (run / "tool-versions.txt").write_text(versions.stdout + versions.stderr + sys.version + "\n")
        (run / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        environment = dict(os.environ, ERL_FLAGS="+S 4:4")
        result = subprocess.run(command, cwd=scratch, env=environment, text=True, capture_output=True, timeout=120)
        (run / "output.txt").write_text(result.stdout + result.stderr)
        receipt = {
            "scope": "Real RS256 signed workspace scope, exact allowlist filtering and complete pure verifier host regressions. Explicit ordinary sources only; no socket/DB/fullapp/provider/native/GA acceptance.",
            "source_tree_sha256": digest(json.dumps(manifest, sort_keys=True).encode()),
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "exit_code": result.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "source_allowlist": SOURCES,
            "test_sources": TESTS,
            "dependency_versions": DEPENDENCIES,
            "application_ebin_loaded": False,
            "forbidden_lane_sources_read_compiled_or_executed": False,
            "scratch_cleanup": "TemporaryDirectory removed after subprocess completion",
        }
    receipt["scratch_removed"] = not scratch.exists()
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout + result.stderr)
    print(json.dumps({"run": str(run.relative_to(ROOT)), "exit_code": result.returncode, "scratch_removed": receipt["scratch_removed"]}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
