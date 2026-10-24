#!/usr/bin/env python3
"""Collect exact host-only verifier evidence; no network, database or UI runtime."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BUILD = Path("/private/tmp/mixer-hosted-token-verifier-build")
ENV = {**os.environ, "MIX_ENV": "test", "MIX_BUILD_PATH": str(BUILD)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, argv, cwd=ROOT, env=None):
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    stdout, stderr = OUT / f"{name}.stdout", OUT / f"{name}.stderr"
    stdout.write_text(result.stdout)
    stderr.write_text(result.stderr)
    return {
        "argv": argv, "cwd": str(cwd), "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": result.returncode,
        "environment_overrides": {"MIX_ENV": "test", "MIX_BUILD_PATH": str(BUILD)} if env else {},
        "stdout": {"path": str(stdout.relative_to(ROOT)), "sha256": sha(stdout)},
        "stderr": {"path": str(stderr.relative_to(ROOT)), "sha256": sha(stderr)},
    }


manifest = json.loads((OUT / "source-manifest.json").read_text())
assert all(sha(ROOT / row["path"]) == row["sha256"] for row in manifest["files"])
inputs = [
    "AGENTS.md", "mixer-product-plan.md", "docs/hosted-identity-contract.md",
    "docs/hosted-verifier-dependency.md", "hosted/mix.exs", "hosted/mix.lock",
    "hosted/config/config.exs", "hosted/test/test_helper.exs",
]
input_rows = [{"path": name, "sha256": sha(ROOT / name)} for name in inputs]
checks = [
    run("mix-version", ["mix", "--version"]),
    run("elixir-version", ["elixir", "--version"]),
    run("macos-version", ["sw_vers"]),
    run("git-revision", ["git", "rev-parse", "HEAD"]),
    run("format", ["mix", "format", "--check-formatted", *[str(Path(row["path"]).relative_to("hosted")) for row in manifest["files"]]], ROOT / "hosted", ENV),
    run("tests", ["mix", "test", "--no-start", "test/mixer_hosted/identity", "--seed", "0"], ROOT / "hosted", ENV),
    run("crypto-runtime", ["mix", "run", "--no-start", "-e", """
{:ok, _} = Application.ensure_all_started(:jose)
IO.inspect(%{
  otp: System.otp_release(), erts: :erlang.system_info(:version),
  elixir: System.version(), jose: Application.spec(:jose, :vsn),
  jason: Application.spec(:jason, :vsn), crypto: Application.spec(:crypto, :vsn),
  public_key: Application.spec(:public_key, :vsn), native_crypto: :crypto.info_lib(),
  jose_json: JOSE.json_module(), jose_crypto_fallback: JOSE.crypto_fallback(),
  jose_unsecured_signing: JOSE.unsecured_signing(),
  mixer_application_started: Enum.any?(Application.started_applications(), fn {app, _, _} -> app == :mixer_hosted end)
}, limit: :infinity)
"""], ROOT / "hosted", ENV),
]
assert all(sha(ROOT / row["path"]) == row["sha256"] for row in manifest["files"])
assert all(sha(ROOT / row["path"]) == row["sha256"] for row in input_rows)
receipt = {
    "schema": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Pure hosted RS256 token verification using product modules; host-only scoped ExUnit, no app start/DB/HTTP/provider/native runtime",
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source_manifest": "verification/hosted-token-verifier/source-manifest.json",
    "source_aggregate_sha256": manifest["aggregate_sha256"],
    "source_unchanged_during_run": True, "inputs": input_rows, "inputs_unchanged_during_run": True,
    "collector": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha(Path(__file__).resolve())},
    "python_version": platform.python_version(), "platform": platform.platform(),
    "checks": checks,
    "success": all(check["exit_code"] == 0 for check in checks),
    "private_key_fixtures": "Generated only in memory by executable tests; no serialized fixture/key output",
    "pending": [
        "Configured adapter, current profile ownership and atomic activation/invalidation",
        "JWKS authenticated transport/cache/concurrency and provider issuance",
        "HTTP/PostgreSQL/principal/revocation/membership/RLS and full hosted integration",
        "Linux/Cloudflare/Neon deployment, production/operational/security gate acceptance",
        "Native runtimes/computer use/screenshots/devices paused; no attempts",
        "Immutable external FieldLog packages and customer qualification",
    ],
    "cleanup": "See cleanup.json for owned scratch removal after evidence collection",
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"success": receipt["success"], "checks": [{"argv": c["argv"][:5], "exit_code": c["exit_code"]} for c in checks], "source_aggregate_sha256": manifest["aggregate_sha256"]}, indent=2))
raise SystemExit(0 if receipt["success"] else 1)
