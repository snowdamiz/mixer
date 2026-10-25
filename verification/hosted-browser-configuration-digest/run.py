#!/usr/bin/env python3
"""Compile only this slice plus four existing identity helpers; start no application."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
]
TESTS = [
    "hosted/test/mixer_hosted/browser_auth/config_test.exs",
    "hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs",
]
EXTRA = [
    "hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml", "AGENTS.md",
    "docs/hosted-browser-configuration-digest.md",
    "verification/hosted-browser-configuration-digest/run.py",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = HERE / "attempts" / stamp
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-config-digest-"))
    dependency = ROOT / "hosted/_build/test/lib/jason/ebin"
    commands = []
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env.update({"ERL_FLAGS": "+S 2:2 +SDcpu 1 +SDio 1", "ERL_CRASH_DUMP": str(scratch / "erl.dump")})
    files = SOURCES + TESTS + EXTRA
    manifest = {name: sha(ROOT / name) for name in files}
    dependencies = {str(path.relative_to(ROOT)): sha(path) for path in sorted(dependency.glob("*.beam"))}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (attempt / "source-inputs.json").write_text(json.dumps({"files": manifest, "tree_sha256": digest, "jason_beams": dependencies}, indent=2) + "\n")

    def run(label: str, argv: list[str]) -> None:
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        (attempt / f"{label}.stdout").write_text(result.stdout)
        (attempt / f"{label}.stderr").write_text(result.stderr)
        commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                         "stdout": str((attempt / f"{label}.stdout").relative_to(ROOT)),
                         "stderr": str((attempt / f"{label}.stderr").relative_to(ROOT))})
        print(f"{label}: exit {result.returncode}")
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"{label} failed")

    status = "failed"
    try:
        if not dependencies:
            raise RuntimeError("existing pinned Jason BEAM dependency unavailable")
        run("tool-versions", ["elixir", "--version"])
        run("crypto-version", ["elixir", "-e", 'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), crypto_backend: :crypto.info_lib(), hash_equals: function_exported?(:crypto, :hash_equals, 2)})'])
        run("format", ["elixir", "-e", 'Enum.each(System.argv(), fn p -> true = File.read!(p) == IO.iodata_to_binary(Code.format_string!(File.read!(p))) <> "\\n" end)'] + SOURCES[-2:] + TESTS)
        run("compile", ["elixirc", "--warnings-as-errors", "-pa", str(dependency), "-o", str(scratch)] + SOURCES)
        test_code = 'ExUnit.start(autorun: false, seed: 0); Enum.each(System.argv(), &Code.require_file/1); result = ExUnit.run(); IO.puts("selected_host_result_json:" <> Jason.encode!(result)); System.halt(if result.failures == 0, do: 0, else: 1)'
        run("tests", ["elixir", "-pa", str(dependency), "-pa", str(scratch), "-e", test_code] + TESTS)
        whitespace_code = 'import pathlib,sys; bad=[f"{name}:{n}" for name in sys.argv[1:] for n,line in enumerate(pathlib.Path(name).read_text().splitlines(),1) if line != line.rstrip(" \\t")]; print("owned source trailing whitespace:", bad); sys.exit(bool(bad))'
        run("owned-source-whitespace", ["python3", "-c", whitespace_code] + SOURCES[-2:] + TESTS + ["docs/hosted-browser-configuration-digest.md", "verification/hosted-browser-configuration-digest/run.py"])
        run("source-whitespace", ["git", "diff", "--check", "--"] + SOURCES[-2:] + TESTS + ["docs/hosted-browser-configuration-digest.md", "verification/hosted-browser-configuration-digest/run.py"])
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        shutil.rmtree(scratch)
        receipt = {
            "status": status, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": revision, "source_tree_sha256": digest,
            "source_inputs": str((attempt / "source-inputs.json").relative_to(ROOT)),
            "commands": commands,
            "scope": "Selected BrowserAuth.Config/ConfigurationDigest host tests with existing Encoding, BoundedJSON, Manifest and StartupConfig; pinned Jason BEAMs. No shared hosted compilation or application startup.",
            "cleanup": {"owned_scratch_removed": not scratch.exists(), "owned_scratch_path": str(scratch),
                        "started_browser_capture_native_or_phone_processes": False, "started_provider_network_or_database": False},
            "pending": ["application/runtime configuration/startup wiring", "provider I/O/TLS/transport qualification", "ID-token cryptographic validation and OIDC/API subject binding", "durable state claim and browser epoch lifecycle", "controlled identity/family/credential lifecycle writer and encrypted session vault", "HTTP endpoint/ingress/Host allowlist/cookie/cache integration", "provider/deployment/browser/security qualification", "native/physical-device and GA acceptance"],
        }
        tests_output = attempt / "tests.stdout"
        if tests_output.exists():
            for line in tests_output.read_text().splitlines():
                if line.startswith("selected_host_result_json:"):
                    receipt["selected_host_tests"] = json.loads(line.split(":", 1)[1])
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
