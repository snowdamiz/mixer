#!/usr/bin/env python3
"""Independent, standalone pure-module probes; no Mix/application startup."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
FILES = [
    "AGENTS.md", "mixer-product-plan.md", "docs/hosted-identity-contract.md",
    "docs/hosted-customer-authorization.md", "hosted/.tool-versions",
    "verification/customer-authorization-policy-root-selection/selection.json",
    "verification/hosted-customer-authorization/seal.json",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/access_token_verifier.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex",
    "hosted/lib/mixer_hosted/audit/upload_event.ex",
    "services/protocol/protocol.go",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/repository.ex",
    "hosted/test/mixer_hosted/authorization/policy_test.exs",
    "verification/hosted-customer-authorization-review/probes.exs",
]
MODULES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/repository.ex",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    n = 1
    while (PACKET / f"run-{n}").exists():
        n += 1
    out = PACKET / f"run-{n}"
    out.mkdir()
    shutil.copyfile(__file__, out / "driver.py")
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-auth-review-"))
    env = dict(os.environ, ERL_FLAGS="+S 2:2")
    receipt = {
        "schema": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": "b375e55ded9e3e10c327891ab681beff2a471e26",
        "source_revision_provenance": "parent/root supplied context; no Git executed",
        "host": {"system": platform.system(), "machine": platform.machine(), "release": platform.release()},
        "python": sys.version, "environment_overrides": {"ERL_FLAGS": env["ERL_FLAGS"]},
        "scope": "independent standalone pure authorization negative and compatibility probes",
        "not_executed": ["Mix startup", "database", "migration", "server", "provider", "network", "UI", "native", "device", "frozen lanes"],
        "scratch": str(scratch), "inputs": [], "commands": [],
    }
    def command(label, args):
        start = time.monotonic()
        result = subprocess.run(args, cwd=scratch, env=env, capture_output=True, timeout=45)
        (out / f"{label}.stdout").write_bytes(result.stdout)
        (out / f"{label}.stderr").write_bytes(result.stderr)
        receipt["commands"].append({"label": label, "argv": args, "cwd": str(scratch),
            "timeout_seconds": 45, "exit_code": result.returncode,
            "elapsed_seconds": round(time.monotonic() - start, 6)})
        return result.returncode
    try:
        for rel in FILES:
            data = (ROOT / rel).read_bytes()
            for prefix in [out / "inputs", scratch]:
                dst = prefix / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
            receipt["inputs"].append({"path": rel, "bytes": len(data), "sha256": sha(data)})
        receipt["input_tree_sha256"] = sha(json.dumps(receipt["inputs"], sort_keys=True, separators=(",", ":")).encode())
        receipt["driver_sha256"] = sha(Path(__file__).read_bytes())
        elixir = "/opt/homebrew/bin/elixir"
        elixirc = "/opt/homebrew/bin/elixirc"
        receipt["tools"] = {"elixir": elixir, "elixirc": elixirc}
        command("tool-version", [elixir, "--version"])
        command("otp-version", [elixir, "-e", 'IO.puts(File.read!(Path.join([:code.root_dir(), "releases", :erlang.system_info(:otp_release), "OTP_VERSION"])))'])
        ebin = scratch / "ebin"
        ebin.mkdir()
        compiled = command("compile", [elixirc, "--warnings-as-errors", "-o", str(ebin)] + [str(scratch / p) for p in MODULES]) == 0
        receipt["compiled"] = compiled
        if compiled:
            receipt["producer_tests_passed"] = command("producer-tests", [elixir, "-pa", str(ebin), "-e", "ExUnit.start(seed: 0); Code.require_file(hd(System.argv()))", "--", str(scratch / "hosted/test/mixer_hosted/authorization/policy_test.exs")]) == 0
            receipt["independent_probes_passed"] = command("independent-probes", [elixir, "-pa", str(ebin), "-e", "ExUnit.start(seed: 0); Code.require_file(hd(System.argv()))", "--", str(scratch / "verification/hosted-customer-authorization-review/probes.exs")]) == 0
        receipt["live_inputs_match_executed"] = all(sha((ROOT / p["path"]).read_bytes()) == p["sha256"] for p in receipt["inputs"])
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"owned_scratch_removed": not scratch.exists(), "native_instances_created": 0, "other_project_processes_changed": False}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"run": str(out.relative_to(ROOT)), "compiled": receipt.get("compiled"),
        "producer_tests_passed": receipt.get("producer_tests_passed"),
        "independent_probes_passed": receipt.get("independent_probes_passed"),
        "cleanup": receipt["cleanup"]}, indent=2))
    return 0 if (receipt.get("compiled") and receipt.get("producer_tests_passed")
        and receipt.get("independent_probes_passed") and receipt.get("live_inputs_match_executed")) else 1


if __name__ == "__main__":
    sys.exit(main())
