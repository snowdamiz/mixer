#!/usr/bin/env python3
"""Selected pure constructor compilation/tests; no Mix or application startup."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/runtime_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/configuration_digest.ex",
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/custody.ex",
    "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex",
]
TESTS = [
    "hosted/test/mixer_hosted/browser_auth/custody_test.exs",
    "hosted/test/mixer_hosted/browser_auth/runtime_config_test.exs",
]
OWNED = SOURCES[-2:] + TESTS + [
    "docs/hosted-browser-runtime-constructors.md",
    "verification/hosted-browser-runtime-constructors/run.py",
]
EXTRA = [
    "AGENTS.md", "hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml",
    "docs/hosted-browser-lifecycle-runtime-contract.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest() -> dict[str, str]:
    return {name: sha(ROOT / name) for name in SOURCES + TESTS + OWNED[-2:] + EXTRA}


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = HERE / "attempts" / stamp
    attempt.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-runtime-constructors-"))
    dependency = ROOT / "hosted/_build/test/lib/jason/ebin"
    commands: list[dict] = []
    # Do not inherit configured application/secret/BEAM-loading variables.
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR"}}
    env.update({"ERL_FLAGS": "+S 2:2 +SDcpu 1 +SDio 1",
                "ERL_CRASH_DUMP": str(scratch / "erl.dump")})
    before = source_manifest()
    digest = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dependencies = {str(path.relative_to(ROOT)): sha(path)
                    for path in sorted(dependency.glob("*.beam"))}
    (attempt / "source-inputs.json").write_text(json.dumps({
        "files": before, "tree_sha256": digest, "jason_beams": dependencies,
    }, indent=2) + "\n")

    def run(label: str, argv: list[str], timeout: int = 120) -> str:
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        (attempt / f"{label}.stdout").write_text(result.stdout)
        (attempt / f"{label}.stderr").write_text(result.stderr)
        commands.append({
            "label": label, "argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
            "stdout": str((attempt / f"{label}.stdout").relative_to(ROOT)),
            "stderr": str((attempt / f"{label}.stderr").relative_to(ROOT)),
        })
        print(f"{label}: exit {result.returncode}")
        if result.returncode:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"{label} failed")
        return result.stdout

    status = "failed"
    revision = None
    result_json = None
    try:
        if not dependencies:
            raise RuntimeError("existing pinned Jason dependency BEAMs unavailable")
        revision = run("revision", ["git", "rev-parse", "HEAD"]).strip()
        run("git-version", ["git", "--version"])
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        run("crypto-version", ["elixir", "-e", "Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), crypto_backend: :crypto.info_lib()})"])
        code = 'Enum.each(System.argv(), fn p -> true = File.read!(p) == IO.iodata_to_binary(Code.format_string!(File.read!(p))) <> "\\n" end)'
        run("format", ["elixir", "-e", code] + SOURCES[-2:] + TESTS)
        run("compile", ["elixirc", "--warnings-as-errors", "-pa", str(dependency), "-o", str(scratch)] + SOURCES)
        code = 'ExUnit.start(autorun: false, seed: 0); Enum.each(System.argv(), &Code.require_file/1); result = ExUnit.run(); IO.puts("selected_host_result_json:" <> Jason.encode!(result)); System.halt(if result.failures == 0, do: 0, else: 1)'
        output = run("tests", ["elixir", "-pa", str(dependency), "-pa", str(scratch), "-e", code] + TESTS)
        for line in output.splitlines():
            if line.startswith("selected_host_result_json:"):
                result_json = json.loads(line.split(":", 1)[1])
        if result_json is None:
            raise RuntimeError("missing selected test result")
        code = 'import pathlib,sys; bad=[f"{name}:{n}" for name in sys.argv[1:] for n,line in enumerate(pathlib.Path(name).read_text().splitlines(),1) if line != line.rstrip(" \\t")]; print("owned source trailing whitespace:", bad); sys.exit(bool(bad))'
        run("owned-whitespace", ["python3", "-c", code] + OWNED)
        run("diff-check", ["git", "diff", "--check", "--"] + OWNED)
        status = "passed"
    except Exception as error:
        (attempt / "failure.txt").write_text(str(error) + "\n")
    finally:
        after = source_manifest()
        dependencies_after = {str(path.relative_to(ROOT)): sha(path)
                              for path in sorted(dependency.glob("*.beam"))}
        (attempt / "source-inputs-after.json").write_text(json.dumps({
            "files": after, "jason_beams": dependencies_after,
        }, indent=2) + "\n")
        unchanged = before == after and dependencies == dependencies_after
        if not unchanged:
            status = "failed"
        shutil.rmtree(scratch)
        receipt = {
            "status": status,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": revision,
            "source_tree_sha256": digest,
            "source_inputs": str((attempt / "source-inputs.json").relative_to(ROOT)),
            "source_inputs_after": str((attempt / "source-inputs-after.json").relative_to(ROOT)),
            "source_and_dependency_hashes_unchanged": unchanged,
            "commands": commands,
            "selected_host_tests": result_json,
            "scope": "Pure Custody.new/2 and RuntimeConfig.new/4; selected ordinary existing source closure and Jason BEAMs. Actual ordinary startup loader/Config/Manifest/Digest/Vault interactions; no shared hosted compile or application startup.",
            "host_trust_store": "The actual existing ordinary startup loader reads OTP's host CA roots in tests. Constructors only validate/preserve supplied roots, never fetch roots, resolve names, connect, or read environment/application state.",
            "cleanup": {
                "owned_scratch_path": str(scratch), "owned_scratch_removed": not scratch.exists(),
                "started_browser_capture_native_or_phone_processes": False,
                "started_provider_network_or_database": False,
                "other_projects_processes_or_data_changed": False,
            },
            "pending": [
                "independent constructor review and root acceptance",
                "Application/shared startup provenance and RuntimeSupervisor/RuntimeOwner wiring",
                "dedicated LifecycleRepo, current catalog admission and operation-owned Store transactions",
                "external secret source qualification, deployed Neon/TLS and pool behavior",
                "provider/OIDC/default verifier/process-owner/HTTP/console session composition",
                "native runtime checks paused; physical-device/customer/FieldLog/GA acceptance",
            ],
        }
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"receipt: {attempt.relative_to(ROOT)}/receipt.json")
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
