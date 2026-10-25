#!/usr/bin/env python3
"""Selected ordinary Vault/Snapshot compilation and tests; no application startup."""
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
SOURCES = ["hosted/lib/mixer_hosted/browser_auth/vault.ex",
           "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex"]
TEST = "hosted/test/mixer_hosted/browser_auth/stored_snapshot_test.exs"
OWNED = [SOURCES[1], TEST, "docs/hosted-browser-stored-snapshot.md",
         "verification/hosted-browser-stored-snapshot/run.py"]
CONTEXT = [SOURCES[0], "AGENTS.md", "hosted/mix.exs", "hosted/mix.lock",
           "THIRD_PARTY.yml", "docs/hosted-browser-session-vault.md"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = HERE / "attempts" / stamp
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-snapshot-"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env.update({"ERL_FLAGS": "+S 2:2 +SDcpu 1 +SDio 1", "ERL_CRASH_DUMP": str(scratch / "erl.dump")})
    manifest = {name: sha(ROOT / name) for name in OWNED + CONTEXT}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (attempt / "source-inputs.json").write_text(json.dumps({"files": manifest, "tree_sha256": digest}, indent=2) + "\n")
    commands = []

    def run(label: str, argv: list[str]) -> str:
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=90)
            output, error, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as expired:
            output = expired.stdout or b""
            error = expired.stderr or b""
            output = output.decode() if isinstance(output, bytes) else output
            error = error.decode() if isinstance(error, bytes) else error
            code = -1
        (attempt / f"{label}.stdout").write_text(output)
        (attempt / f"{label}.stderr").write_text(error)
        commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exit_code": code,
                         "timeout_seconds": 90,
                         "stdout": str((attempt / f"{label}.stdout").relative_to(ROOT)),
                         "stdout_sha256": sha(attempt / f"{label}.stdout"),
                         "stderr": str((attempt / f"{label}.stderr").relative_to(ROOT)),
                         "stderr_sha256": sha(attempt / f"{label}.stderr")})
        print(f"{label}: exit {code}", flush=True)
        if code:
            print(output)
            print(error)
            raise RuntimeError(f"{label} failed")
        return output

    status = "failed"
    try:
        run("tool-versions", ["elixir", "--version"])
        run("crypto-version", ["elixir", "-e", 'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), crypto_backend: :crypto.info_lib()})'])
        run("format", ["elixir", "-e", 'Enum.each(System.argv(), fn p -> true = File.read!(p) == IO.iodata_to_binary(Code.format_string!(File.read!(p))) <> "\\n" end)', SOURCES[1], TEST])
        run("compile", ["elixirc", "--warnings-as-errors", "-o", str(scratch)] + SOURCES)
        test_code = 'ExUnit.start(autorun: false, seed: 0); Code.require_file(hd(System.argv())); result = ExUnit.run(); IO.puts("selected_host_result:" <> Enum.map_join([:total, :failures, :skipped, :excluded], ",", &Integer.to_string(Map.fetch!(result, &1)))); System.halt(if result.failures == 0, do: 0, else: 1)'
        run("tests", ["elixir", "-pa", str(scratch), "-e", test_code, TEST])
        whitespace_code = 'import pathlib,sys; bad=[f"{name}:{n}" for name in sys.argv[1:] for n,line in enumerate(pathlib.Path(name).read_text().splitlines(),1) if line != line.rstrip(" \\t")]; print("owned trailing whitespace:",bad);sys.exit(bool(bad))'
        run("owned-source-whitespace", [sys.executable, "-c", whitespace_code] + OWNED)
        run("source-diff-check", ["git", "diff", "--check", "--"] + OWNED)
        if any(sha(ROOT / name) != value for name, value in manifest.items()):
            raise RuntimeError("source changed during selected run")
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        shutil.rmtree(scratch)
        receipt = {
            "status": status, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": revision, "source_tree_sha256": digest,
            "source_inputs": str((attempt / "source-inputs.json").relative_to(ROOT)),
            "python_version": sys.version, "commands": commands,
            "scope": "Selected Vault/StoredSnapshot compilation and synthetic row decoding with real OTP authenticated encryption. No shared hosted app compilation/startup, dependency builds or frozen lane access.",
            "cleanup": {"owned_scratch_removed": not scratch.exists(), "owned_scratch_path": str(scratch),
                        "started_browser_capture_native_or_phone_processes": False,
                        "started_provider_network_or_database": False},
            "pending": ["actual SQL result composition", "runtime provenance and trusted lifecycle owner",
                        "key custody and provider integration", "current verifier and OIDC/API subject binding",
                        "HTTP/console/browser/deployment integration", "native/physical and GA acceptance"]}
        output = attempt / "tests.stdout"
        if output.exists():
            for line in output.read_text().splitlines():
                if line.startswith("selected_host_result:"):
                    receipt["selected_host_tests"] = dict(zip(["total", "failures", "skipped", "excluded"],
                        map(int, line.split(":", 1)[1].split(","))))
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json", flush=True)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
