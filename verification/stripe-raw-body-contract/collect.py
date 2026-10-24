"""Freeze read-only inputs and run dependency API probes; no HTTP/app startup."""
import hashlib
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DOC = REPO / "docs/stripe-raw-body-contract.md"
EXPECTED = "eb6f50bde86c742e269a605f15e3170d8dd18646f71289c2b8e5c470f5f4808d"
SIGNATURE = "3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6"
INPUTS = [
    "AGENTS.md", "mixer-product-plan.md", "PLAN.md", "THIRD_PARTY.yml",
    "hosted/.tool-versions", "hosted/mix.exs", "hosted/mix.lock",
    "hosted/lib/mixer_hosted_web/endpoint.ex", "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/lib/mixer_hosted/billing/webhook_signature.ex",
    "docs/stripe-webhook-signature-contract.md", "docs/stripe-webhook-signature-integration.md",
    "verification/stripe-webhook-signature-integration/acceptance.json",
    "hosted/deps/plug/lib/plug/conn.ex", "hosted/deps/plug/lib/plug/conn/adapter.ex",
    "hosted/deps/bandit/lib/bandit.ex", "hosted/deps/bandit/lib/bandit/adapter.ex",
    "hosted/deps/bandit/lib/bandit/pipeline.ex", "hosted/deps/bandit/lib/bandit/headers.ex",
    "hosted/deps/bandit/lib/bandit/http1/socket.ex", "hosted/deps/bandit/lib/bandit/http2/stream.ex",
    "hosted/deps/thousand_island/lib/thousand_island/socket.ex",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run(name, command):
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, timeout=30)
    (HERE / f"{name}.log").write_text(result.stdout + result.stderr)
    return {"command": command, "cwd": str(REPO), "exitCode": result.returncode,
            "output": f"{name}.log", "outputSHA256": sha(HERE / f"{name}.log")}


def main():
    commands = []
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    acceptance = json.loads((REPO / INPUTS[12]).read_text())
    current = {name: sha(REPO / name) for name in acceptance["sourceInputs"]}
    digest = hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert len(current) == 69 and current == acceptance["sourceInputs"] and digest == EXPECTED
    assert sha(REPO / INPUTS[9]) == SIGNATURE
    frozen = {}
    for name in INPUTS:
        destination = HERE / "inputs" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, destination)
        frozen[name] = sha(destination)
    write("source-inputs.json", frozen)
    write("accepted-hosted-inputs.json", {"sourceDigest": digest, "sourceInputs": current})
    commands.append(run("elixir-version", ["elixir", "--version"]))
    commands.append(run("python-version", ["python3", "--version"]))
    paths = sorted((REPO / "hosted/_build/test/lib").glob("*/ebin"))
    command = ["elixir"]
    for path in paths:
        command.extend(["-pa", str(path)])
    command.append(str(HERE / "api_probe.exs"))
    commands.append(run("api-probe", command))
    beam_inputs = {}
    for module, app in [("Plug.Conn", "plug"), ("Bandit.Adapter", "bandit"),
                        ("Bandit.Headers", "bandit"), ("Bandit.HTTPTransport", "bandit"),
                        ("Bandit.HTTPTransport.Bandit.HTTP1.Socket", "bandit")]:
        path = REPO / f"hosted/_build/test/lib/{app}/ebin/Elixir.{module}.beam"
        beam_inputs[str(path.relative_to(REPO))] = sha(path)
    write("beam-inputs.json", beam_inputs)
    write("receipt.json", {
        "schema": 1, "status": "contract-proposal-root-selection-pending",
        "observedUTC": datetime.now(timezone.utc).isoformat(), "sourceRevision": revision,
        "sourceDigest": digest, "sourceInputCount": 69, "signatureModuleSHA256": SIGNATURE,
        "frozenSourceInputCount": len(frozen), "host": platform.platform(), "commands": commands,
        "validation": {"dependencyAPIProbeTests": 9, "componentImplementationTests": 0,
                       "realHTTPTests": 0, "upstreamHostPasses": 127, "upstreamHostSkips": 2,
                       "upstreamIndependentSignatureCases": 2352},
        "scope": "Read-only installed dependency API probes and source review; no capture implementation or live HTTP",
        "cleanup": {"listenerStarted": False, "databaseStarted": False, "nativeRuntimeStarted": False,
                    "backgroundProcessStarted": False, "scratchCreated": False,
                    "probeProcessesCompleted": all(c["exitCode"] == 0 for c in commands)},
        "pending": ["root transport/profile selection", "raw capture implementation",
                    "real localhost HTTP matrix", "hard endpoint cancellation and ingress qualification",
                    "logging/telemetry qualification", "endpoint/account/mode/generation ownership",
                    "durable deduplicated inbox and atomic Oban enqueue", "Stripe test-mode reconciliation", "G23"],
    })
    for result in commands:
        assert result["exitCode"] == 0, result
    seal = {}
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and path.name != "seal.json":
            seal[str(path.relative_to(REPO))] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    seal[str(DOC.relative_to(REPO))] = {"bytes": DOC.stat().st_size, "sha256": sha(DOC)}
    write("seal.json", seal)
    print(f"PASS: {len(frozen)} frozen inputs; accepted 69-input digest matches; 9 dependency API probes; no service started")


if __name__ == "__main__":
    main()
