#!/usr/bin/env python3
"""Seal dependency-only API probes; never start or compile MixerHosted."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCES = [
    "AGENTS.md", "mixer-product-plan.md", "THIRD_PARTY.yml",
    "docs/hosted-build-coordinator.md", "docs/hosted-worker-transport-contract.md",
    "docs/stripe-webhook-resource-ingress-contract.md",
    "docs/stripe-webhook-linux-resource-harness.md",
    "hosted/mix.exs", "hosted/mix.lock", "hosted/config/config.exs",
    "hosted/config/runtime.exs", "hosted/lib/mixer_hosted/application.ex",
    "hosted/lib/mixer_hosted/runtime_config.ex",
    "hosted/lib/mixer_hosted/builds/dispatch.ex",
    "hosted/lib/mixer_hosted/builds/coordinator.ex",
    "hosted/lib/mixer_hosted/builds/lifecycle.ex",
    "hosted/lib/mixer_hosted/builds/admission.ex",
    "hosted/lib/mixer_hosted/identity/startup_config.ex",
    "hosted/lib/mixer_hosted/identity/jwks_transport.ex",
    "hosted/lib/mixer_hosted/identity/bounded_tcp.ex",
    "hosted/lib/mixer_hosted/identity/dns_resolver.ex",
    "hosted/lib/mixer_hosted/identity/http_wire_guard.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/billing/webhook_transport.ex",
    "hosted/deps/jason/lib/jason.ex", "hosted/deps/jason/lib/decoder.ex",
    "hosted/deps/mint/lib/mint/http.ex",
    "hosted/deps/mint/lib/mint/core/transport/ssl.ex",
    "verification/hosted-worker-transport-contract/api_probe.exs",
    "verification/hosted-worker-transport-contract/integer_probe.js",
    "verification/hosted-worker-transport-contract/run.py",
]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name: str, value: object) -> None:
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def run(name: str, arguments: list[str]) -> dict:
    started = time.monotonic()
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8",
                   "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}
    process = subprocess.Popen(arguments, cwd=ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        output, errors = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, errors = process.communicate()
        raise RuntimeError("probe exceeded 20-second outer timeout")
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if len(output) > 65_536 or len(errors) > 65_536:
        raise RuntimeError("probe output overflow")
    (HERE / (name + ".stdout")).write_bytes(output)
    (HERE / (name + ".stderr")).write_bytes(errors)
    record = {"name": name, "arguments": arguments, "cwd": str(ROOT),
        "exit_code": process.returncode, "duration_ms": round((time.monotonic()-started)*1000),
        "stdout_sha256": digest(HERE / (name + ".stdout")),
        "stderr_sha256": digest(HERE / (name + ".stderr")),
        "cleanup": "owned process group disposed after command completion"}
    if process.returncode:
        raise RuntimeError("probe failed: " + name)
    return record

def main() -> None:
    sources = []
    for name in SOURCES:
        path = ROOT / name
        sources.append({"path": name, "sha256": digest(path), "size": path.stat().st_size})
    for dependency in ["jason", "mint", "hpax"]:
        for path in sorted((ROOT / "hosted/_build/test/lib" / dependency / "ebin").glob("*")):
            if path.is_file():
                sources.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path), "size": path.stat().st_size})
    sources.sort(key=lambda row: row["path"])
    source_digest = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write("source-map.json", {"schema": 1, "sources": sources, "source_digest": source_digest})
    tools = {name: shutil.which(name) for name in ["elixir", "node", "python3", "git"]}
    assert all(tools.values())
    commands = []
    commands.append(run("elixir-version", [tools["elixir"], "--version"]))
    commands.append(run("node-version", [tools["node"], "--version"]))
    commands.append(run("python-version", [tools["python3"], "--version"]))
    commands.append(run("source-revision", [tools["git"], "rev-parse", "HEAD"]))
    arguments = [tools["elixir"], "--erl", "+S 2:2 +SDcpu 1 +SDio 1"]
    for dependency in ["mint", "jason", "hpax"]:
        arguments += ["-pa", str(ROOT / "hosted/_build/test/lib" / dependency / "ebin")]
    arguments += [str(HERE / "api_probe.exs")]
    commands.append(run("dependency-api-probe", arguments))
    commands.append(run("integer-probe", [tools["node"], str(HERE / "integer_probe.js")]))
    observed = json.loads((HERE / "dependency-api-probe.stdout").read_text())
    assert observed["loaded_mixer_modules"] == 0
    assert observed["duplicate_keys_preserved"] is True
    assert observed["signed_int64_preserved"] is True
    assert observed["mint_passive_post_response_and_close"] is True
    interoperability = json.loads((HERE / "integer-probe.stdout").read_text())
    assert interoperability["number_loses_int64_precision"] is True
    assert interoperability["decimal_string_preserves_int64"] is True
    unchanged = all(digest(ROOT / row["path"]) == row["sha256"] for row in sources)
    assert unchanged, "source/dependency drift during probe"
    write("commands.json", {"schema": 1, "commands": commands})
    write("receipt.json", {
        "schema": 1, "status": "contract-and-dependency-api-probes-passed",
        "scope": "contract-authoring-and-two-dependency-api-probes-only",
        "source_revision": (HERE / "source-revision.stdout").read_text().strip(),
        "source_digest": source_digest, "input_count": len(sources),
        "source_unchanged_during_probes": unchanged,
        "platform": platform.platform(), "tools": tools,
        "probes": [observed, interoperability],
        "production_changes": [], "mixer_modules_loaded": 0,
        "cleanup": {"owned_probe_process_groups_disposed": True,
          "owned_plaintext_listener_closed": True, "temporary_files_created": False,
          "hosted_application_started": False, "native_instances_started": False,
          "database_or_cloud_provider_started": False},
        "limitations": ["not production implementation acceptance", "no HTTPS/authentication replay",
          "no controller/persistence/provider execution", "no hard Linux resource qualification",
          "local compiled dependency BEAM provenance not independently rebuilt",
          "no tenant/source/artifact/signing/publication/native/GA acceptance"],
        "commands_sha256": digest(HERE / "commands.json"),
        "source_map_sha256": digest(HERE / "source-map.json")})
    print(json.dumps({"status": "passed", "probes": 2, "inputs": len(sources),
        "source_digest": source_digest, "loaded_mixer_modules": 0}))

if __name__ == "__main__":
    main()
