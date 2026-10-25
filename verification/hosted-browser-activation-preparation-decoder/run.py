#!/usr/bin/env python3
"""Selected ordinary projection source/tests; no shared hosted harness or startup."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex",
]
TESTS = [
    "hosted/test/mixer_hosted/browser_auth/activation_preparation_test.exs",
    "hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs",
]
OWNED = [
    SOURCES[2], TESTS[0],
    "docs/hosted-browser-activation-preparation-decoder.md",
    "verification/hosted-browser-activation-preparation-decoder/run.py",
]
CONTEXT = [
    SOURCES[0], SOURCES[1], TESTS[1], "AGENTS.md", "hosted/mix.lock",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = HERE / "attempts" / stamp
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-activation-preparation-"))
    env = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_")}
    env.update({
        "ERL_FLAGS": "+S 2:2 +SDcpu 1 +SDio 1",
        "ERL_CRASH_DUMP": str(scratch / "erl.dump"),
    })
    manifest = {name: sha(ROOT / name) for name in OWNED + CONTEXT}
    digest = hashlib.sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    inputs = attempt / "source-inputs.json"
    inputs.write_text(json.dumps({"files": manifest, "tree_sha256": digest}, indent=2) + "\n")
    commands = []

    def run(label: str, argv: list[str]) -> str:
        try:
            result = subprocess.run(
                argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=90,
            )
            output, error, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as expired:
            output = expired.stdout or b""
            error = expired.stderr or b""
            output = output.decode() if isinstance(output, bytes) else output
            error = error.decode() if isinstance(error, bytes) else error
            code = -1
        stdout = attempt / f"{label}.stdout"
        stderr = attempt / f"{label}.stderr"
        stdout.write_text(output)
        stderr.write_text(error)
        commands.append({
            "label": label, "argv": argv, "cwd": str(ROOT), "exit_code": code,
            "timeout_seconds": 90,
            "stdout": str(stdout.relative_to(ROOT)), "stdout_sha256": sha(stdout),
            "stderr": str(stderr.relative_to(ROOT)), "stderr_sha256": sha(stderr),
        })
        print(f"{label}: exit {code}", flush=True)
        if code:
            print(output)
            print(error)
            raise RuntimeError(f"{label} failed")
        return output

    status = "failed"
    try:
        run("tool-versions", ["elixir", "--version"])
        run("elixirc-version", ["elixirc", "--version"])
        run("git-version", ["git", "--version"])
        run("crypto-version", [
            "elixir", "-e",
            'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), '
            'crypto: Application.spec(:crypto, :vsn), crypto_backend: :crypto.info_lib()})',
        ])
        format_code = (
            'Enum.each(System.argv(), fn p -> '
            'true = File.read!(p) == IO.iodata_to_binary(Code.format_string!(File.read!(p))) '
            '<> <<10>> end)'
        )
        run("format", ["elixir", "-e", format_code, SOURCES[2], TESTS[0]])
        run("compile", ["elixirc", "--warnings-as-errors", "-o", str(scratch)] + SOURCES)
        test_code = (
            'ExUnit.start(autorun: false, seed: 0); '
            'Enum.each(System.argv(), &Code.require_file/1); '
            'result = ExUnit.run(); IO.puts("selected_host_result:" <> '
            'Enum.map_join([:total, :failures, :skipped, :excluded], ",", '
            '&Integer.to_string(Map.fetch!(result, &1)))); '
            'System.halt(if result.failures == 0, do: 0, else: 1)'
        )
        run("preparation-tests", ["elixir", "-pa", str(scratch), "-e", test_code, TESTS[0]])
        run("snapshot-regression-tests", ["elixir", "-pa", str(scratch), "-e", test_code, TESTS[1]])
        whitespace_code = (
            'import pathlib,sys; bad=[f"{name}:{n}" for name in sys.argv[1:] '
            'for n,line in enumerate(pathlib.Path(name).read_text().splitlines(),1) '
            'if line != line.rstrip(" \\t")]; '
            'print("owned trailing whitespace:",bad);sys.exit(bool(bad))'
        )
        run("owned-source-whitespace", [sys.executable, "-c", whitespace_code] + OWNED)
        run("source-diff-check", ["git", "diff", "--check", "--"] + OWNED)
        if any(sha(ROOT / name) != value for name, value in manifest.items()):
            raise RuntimeError("selected source or context changed during the run")
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        shutil.rmtree(scratch)
        receipt = {
            "status": status,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": revision,
            "source_tree_sha256": digest,
            "source_inputs": str(inputs.relative_to(ROOT)),
            "python_version": sys.version,
            "commands": commands,
            "dependency_beams": [],
            "scope": (
                "Actual selected ordinary Vault/StoredSnapshot/ActivationPreparation standalone "
                "warnings-as-errors compilation, synthetic preparation-shape tests, and existing "
                "snapshot regressions using existing OTP AES-GCM. No dependency builds, shared "
                "hosted compilation/startup, frozen catalog/authority lane or rejected Worker V2 access."
            ),
            "cleanup": {
                "owned_scratch_removed": not scratch.exists(),
                "owned_scratch_path": str(scratch),
                "started_browser_capture_native_or_phone_processes": False,
                "started_provider_network_or_database": False,
                "process_discovery_performed": False,
            },
            "pending": [
                "additive SQL type/helper, migration, schema and catalog admission",
                "owner-retained claim/current access identity/configuration binding",
                "database provenance, current time and transaction/runtime fencing",
                "provider/OIDC/custody qualification and protected current authorization",
                "HTTP/console/customer/FieldLog/deployment integration",
                "paused native simulator/emulator, capture, UI and physical-phone checks",
                "GA acceptance",
            ],
        }
        for label in ["preparation-tests", "snapshot-regression-tests"]:
            output = attempt / f"{label}.stdout"
            if output.exists():
                for line in output.read_text().splitlines():
                    if line.startswith("selected_host_result:"):
                        receipt[label.replace("-", "_")] = dict(zip(
                            ["total", "failures", "skipped", "excluded"],
                            map(int, line.split(":", 1)[1].split(",")),
                        ))
        encoded = json.dumps(receipt, indent=2) + "\n"
        (attempt / "receipt.json").write_text(encoded)
        (HERE / "receipt.json").write_text(encoded)
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json", flush=True)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
