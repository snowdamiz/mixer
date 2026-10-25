#!/usr/bin/env python3
"""Selected real-module host review; no Mix discovery, DB, native or app startup."""
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
SOURCE_PATHS = [
    "hosted/lib/mixer_hosted/browser_auth/vault.ex",
    "hosted/lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    "hosted/lib/mixer_hosted/browser_auth/activation_preparation.ex",
]
FROZEN_DECODER_SHA256 = "e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt = HERE / "attempts" / attempt_id
    attempt.mkdir(parents=True)
    commands = []
    receipt = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "scope": "independent selected ordinary ActivationPreparation/Vault/StoredSnapshot host shape review",
        "result": "failed",
        "frozen_decoder_sha256": FROZEN_DECODER_SHA256,
        "sources": {},
        "commands": commands,
        "limitations": [
            "shape only; no SQL projection/helper/catalog/owner binding/readiness or route acceptance",
            "no current verifier/OIDC/provider/key custody/deployment/GA qualification",
            "no broad hosted application, Mix discovery or database started",
            "computer use, screen capture, UI automation, native runtime and physical phones remain paused and unrun",
            "no frozen catalog-inspector/authority-driver or rejected Worker V2 read/import/execute",
            "effect tracing covers selected concrete success/error executions; source and compiled imports additionally reviewed",
        ],
    }

    def run(name: str, argv: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env={**os.environ, "ERL_CRASH_DUMP": str(attempt / "erl_crash.dump")})
        (attempt / f"{name}.stdout").write_text(result.stdout)
        (attempt / f"{name}.stderr").write_text(result.stderr)
        commands.append({"name": name, "argv": argv, "cwd": str(ROOT), "started_at": started, "exit_code": result.returncode, "stdout": f"{name}.stdout", "stderr": f"{name}.stderr"})
        return result

    scratch = Path(tempfile.mkdtemp(prefix="mixer-activation-decoder-review-"))
    receipt["cleanup"] = {"owned_scratch": str(scratch), "removed": False, "native_or_capture_processes_started": False, "database_started": False, "process_discovery_performed": False}
    try:
        for path in SOURCE_PATHS:
            source = ROOT / path
            target = attempt / "inputs" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            receipt["sources"][path] = {"sha256": digest(source), "input_copy": str(target.relative_to(HERE))}
        for path in [HERE / "review_tests.exs", Path(__file__).resolve()]:
            target = attempt / "inputs" / path.name
            shutil.copyfile(path, target)
            receipt["sources"][str(path.relative_to(ROOT))] = {"sha256": digest(path), "input_copy": str(target.relative_to(HERE))}
        manifest = "".join(f"{path}\0{meta['sha256']}\n" for path, meta in sorted(receipt["sources"].items()))
        receipt["selected_tree_sha256"] = hashlib.sha256(manifest.encode()).hexdigest()
        (attempt / "source-manifest.txt").write_text(manifest)
        assert receipt["sources"][SOURCE_PATHS[-1]]["sha256"] == FROZEN_DECODER_SHA256, "decoder changed after freeze"
        for name, argv in [
            ("revision", ["git", "rev-parse", "HEAD"]),
            ("tracked-tree", ["git", "rev-parse", "HEAD^{tree}"]),
            ("elixir-version", ["elixir", "--version"]),
            ("python-version", ["python3", "--version"]),
        ]:
            result = run(name, argv)
            assert result.returncode == 0, name
            receipt[name] = result.stdout.strip()
        ebin = scratch / "ebin"
        ebin.mkdir()
        compiler = run("compile", ["elixirc", "--warnings-as-errors", "--output", str(ebin), *[str(ROOT / path) for path in SOURCE_PATHS]])
        assert compiler.returncode == 0, "selected warnings-as-errors compile failed"
        receipt["compiled_beams"] = {path.name: digest(path) for path in sorted(ebin.glob("*.beam"))}
        disassembly = run("compiled-imports", ["elixir", "-pa", str(ebin), "-e", "for module <- [MixerHosted.BrowserAuth.ActivationPreparation, MixerHosted.BrowserAuth.StoredSnapshot, MixerHosted.BrowserAuth.Vault] do {:ok, {^module, chunks}} = :beam_lib.chunks(:code.which(module), [:imports]); IO.inspect({module, chunks}, limit: :infinity) end"])
        assert disassembly.returncode == 0, "compiled import audit failed"
        tests = run("tests", ["elixir", "--warnings-as-errors", "-pa", str(ebin), str(HERE / "review_tests.exs")])
        assert tests.returncode == 0, "independent executable review failed"
        assert "28 tests, 0 failures" in tests.stdout, "unexpected test count"
        receipt["tests"] = {"methods": 28, "failures": 0}
        for path, metadata in receipt["sources"].items():
            assert digest(ROOT / path) == metadata["sha256"], f"source changed during run: {path}"
        receipt["source_stability"] = "all selected live sources and review controls match pre-run copies"
        receipt["result"] = "passed"
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"]["removed"] = not scratch.exists()
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "attempt": attempt_id, "error": receipt.get("error"), "scratch_removed": receipt["cleanup"]["removed"]}))
    return 0 if receipt["result"] == "passed" and receipt["cleanup"]["removed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
