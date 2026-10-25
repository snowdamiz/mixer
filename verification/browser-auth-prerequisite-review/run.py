#!/usr/bin/env python3
"""Independent selected-source prerequisite review; no application startup or network."""
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
ELIXIR_SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/identity/manifest.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/browser_auth/config.ex",
    "hosted/lib/mixer_hosted/browser_auth/protocol.ex",
]
TS_SOURCES = [
    "console/src/api/cookie-workspace-client.ts", "console/src/api/workspace-transport.ts",
    "console/src/api/workspace-client.ts", "console/src/domain/workspace-directory.ts",
]
OWNED = [str((HERE / name).relative_to(ROOT)) for name in ["run.py", "transport-review.test.mjs", "protocol_review_test.exs"]]
EXTRA = ["AGENTS.md", "console/package-lock.json", "console/node_modules/typescript/package.json", "hosted/mix.lock"]
PINNED_PROTOCOL = {
    ELIXIR_SOURCES[3]: "0c9b11693d34880ca9e9c05fba95e1f3994a0eadd7189a5fde2f65b036ff4d50",
    ELIXIR_SOURCES[4]: "9904a83c79c5de50ab800d1443fdb6ee1c5ed03eda981ea85852e8c65e9bd8d2",
    ELIXIR_SOURCES[5]: "a569cabebfd905f1f717137b9180ff5ae47fffb747a9b5e45f049f03b3da3428",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    attempt = HERE / "attempts" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    attempt.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-prerequisite-review-"))
    beams = scratch / "beams"
    beams.mkdir()
    compiled_js = scratch / "js"
    dependencies = ROOT / "hosted/_build/test/lib/jason/ebin"
    files = ELIXIR_SOURCES + TS_SOURCES + OWNED + EXTRA
    before = {name: sha(ROOT / name) for name in files}
    dependency_manifest = {str(p.relative_to(ROOT)): sha(p) for p in sorted(dependencies.glob("*.beam"))}
    tree_digest = sha256_json(before)
    (attempt / "sources.json").write_text(json.dumps({"files": before, "tree_sha256": tree_digest, "jason_beams": dependency_manifest}, indent=2) + "\n")
    env = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_")}
    env.update({"ERL_FLAGS": "+S 2:2 +SDcpu 1 +SDio 1", "ERL_CRASH_DUMP": str(scratch / "erl.dump"), "MIXER_REVIEW_COMPILED_JS": str(compiled_js)})
    commands = []
    status = "failed"
    findings = []

    def run(label, argv):
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
        (attempt / (label + ".stdout")).write_bytes(result.stdout)
        (attempt / (label + ".stderr")).write_bytes(result.stderr)
        commands.append({"label": label, "argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                         "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(), "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
        print(label + ": exit " + str(result.returncode), flush=True)
        if result.returncode:
            findings.append(label + " failed; inspect saved stdout/stderr")
        return result.returncode

    try:
        assert dependency_manifest, "pinned Jason BEAMs unavailable"
        assert all(before[name] == digest for name, digest in PINNED_PROTOCOL.items()), "protocol frozen source mismatch"
        failures = 0
        for label, argv in [
            ("python-version", ["python3", "--version"]), ("node-version", ["node", "--version"]),
            ("typescript-version", ["node", "console/node_modules/typescript/bin/tsc", "--version"]),
            ("elixir-version", ["elixir", "--version"]),
            ("crypto-version", ["elixir", "-e", 'Application.load(:crypto); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: Application.spec(:crypto, :vsn), backend: :crypto.info_lib()})']),
        ]:
            failures += bool(run(label, argv))
        compile_ts = run("compile-ts", ["node", "console/node_modules/typescript/bin/tsc", TS_SOURCES[0], TS_SOURCES[2], "--outDir", str(compiled_js), "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes"])
        failures += bool(compile_ts)
        if not compile_ts:
            (compiled_js / "package.json").write_text('{"type":"module"}\n')
            failures += bool(run("transport-review", ["node", "--test", str(HERE / "transport-review.test.mjs")]))
        compile_elixir = run("compile-elixir", ["elixirc", "--warnings-as-errors", "-pa", str(dependencies), "-o", str(beams)] + ELIXIR_SOURCES)
        failures += bool(compile_elixir)
        if not compile_elixir:
            code = 'ExUnit.start(autorun: false, seed: 0); Code.require_file(hd(System.argv())); result = ExUnit.run(); IO.puts("independent_result_json:" <> Jason.encode!(result)); System.halt(if result.failures == 0, do: 0, else: 1)'
            failures += bool(run("protocol-review", ["elixir", "-pa", str(dependencies), "-pa", str(beams), "-e", code, str(HERE / "protocol_review_test.exs")]))
        assert before == {name: sha(ROOT / name) for name in files}, "source changed during review"
        assert dependency_manifest == {str(p.relative_to(ROOT)): sha(p) for p in sorted(dependencies.glob("*.beam"))}, "Jason dependency changed"
        status = "passed" if not failures else "failed"
    except Exception as error:
        findings.append(str(error))
    finally:
        shutil.rmtree(scratch)
        receipt = {
            "status": status, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_tree_sha256": tree_digest, "sources": before, "commands": commands,
            "scope": "Independent adversarial Node and selected-module Elixir host probes; ordinary Config/Protocol plus four explicit identity helpers only. Producer 112 full-console and 39 protocol tests are separate evidence and are not counted here.",
            "findings": findings,
            "exploration_failure": "One read-only command initially used non-existent hosted/lib/mixer_hosted/authentication/startup_config.ex; exited 1, corrected to identity/startup_config.ex. No source mutation or excluded-lane access occurred.",
            "cleanup": {"owned_scratch_path": str(scratch), "owned_scratch_removed": not scratch.exists(), "started_network_browser_native_capture_provider_database": False},
            "pending": ["browser cookie enforcement and page layout", "production browser route/session integration", "provider HTTP and ID-token validation", "durable one-use state/browser epoch claims and replay", "encrypted session vault and lifecycle writer", "ingress and deployment security qualification", "paused native/device checks and all GA acceptance"],
        }
        transport_output = attempt / "transport-review.stdout"
        if transport_output.exists():
            receipt["transport_summary"] = [line for line in transport_output.read_text().splitlines() if line.startswith(("# tests", "# pass", "# fail", "# skipped"))]
        protocol_output = attempt / "protocol-review.stdout"
        if protocol_output.exists():
            for line in protocol_output.read_text().splitlines():
                if line.startswith("independent_result_json:"):
                    receipt["protocol_summary"] = json.loads(line.split(":", 1)[1])
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"status": status, "receipt": str(attempt / "receipt.json"), "findings": findings}))
    return 0 if status == "passed" else 1


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
