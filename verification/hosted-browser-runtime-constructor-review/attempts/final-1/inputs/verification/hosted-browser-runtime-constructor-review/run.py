#!/usr/bin/env python3
"""Exact-source isolated constructor review. Starts no app, DB or native runtime."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("verification/hosted-browser-runtime-constructor-review")
MODULES = ["runtime_config.ex", "identity/encoding.ex", "identity/bounded_json.ex",
           "identity/manifest.ex", "identity/startup_config.ex", "browser_auth/config.ex",
           "browser_auth/configuration_digest.ex", "browser_auth/vault.ex",
           "browser_auth/custody.ex", "browser_auth/runtime_config.ex"]
MODULES = ["hosted/lib/mixer_hosted/" + name for name in MODULES]
TEST = str(BASE / "probes.exs")
FROZEN = {
    "hosted/lib/mixer_hosted/browser_auth/custody.ex": "675429fa3daf5c84cf8ee8223aeeea6842889af859a6468c763ffc0ea6033803",
    "hosted/lib/mixer_hosted/browser_auth/runtime_config.ex": "0ce7e28450b7f5652313fc22cb909ea6e65cc8b4a8edcc960669d5a950da0962",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    if not args.attempt.replace("-", "").replace("_", "").isalnum():
        parser.error("attempt must be one simple directory name")
    out = ROOT / BASE / "attempts" / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-constructor-review-"))
    receipt = {
        "status": "failed", "commands": [], "source_revision": None,
        "scope": "Independent Custody.new/2 and BrowserAuth.RuntimeConfig.new/4 boundary review using actual ordinary Config/Manifest/StartupConfig/ConfigurationDigest/Vault and ordinary loader sources. No product tests imported; no broad hosted compile/harness/startup, DB, network, provider, browser, capture, simulator, emulator or device discovery.",
        "fixture_scope": "Actual ordinary startup loader reads local OTP CA roots during test setup only; constructor effect trace excludes setup and checks environment/global-store/I/O/network/randomness/process operations. One separate control changes/restores only the disposable BEAM node's HTTPS default-port registry and proves failure closed.",
        "permitted_infrastructure_reads": "Exactly 12 URI.uri_from_map/1 -> elixir_config.get({:uri, https}, nil) -> ets.lookup(:elixir_config, {:uri, https}) reads across two configured calls; trace match specifications bind the exact table and key. No broad ETS allowance.",
        "limitations": ["No startup provenance, live secret-custody security, owner composition, pool checkout, SQL/catalog privilege, provider, native, customer, FieldLog, operator or GA acceptance."],
        "frozen_product_sha256": FROZEN,
    }
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")

    def run(name, argv, cwd=None):
        argv = [str(arg) for arg in argv]
        where = cwd or out / "inputs"
        result = subprocess.run(argv, cwd=where, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(where),
                                    "exit_code": result.returncode, "stdout": name + ".stdout",
                                    "stderr": name + ".stderr"})
        if result.returncode:
            raise RuntimeError(name + " failed")
        return result

    try:
        paths = MODULES + [TEST, str(BASE / "run.py"), "AGENTS.md", "PLAN.md",
                           "docs/hosted-browser-lifecycle-runtime-contract.md", "hosted/mix.exs", "hosted/mix.lock"]
        manifest = {}
        for name in paths:
            target = out / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest[name] = sha(target)
        receipt["input_sha256"] = manifest
        receipt["input_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipt["product_hashes_match_frozen_handoff"] = all(manifest[name] == value for name, value in FROZEN.items())
        if not receipt["product_hashes_match_frozen_handoff"]:
            raise RuntimeError("product source differs from producer frozen handoff")
        receipt["source_revision"] = run("git-revision", ["git", "rev-parse", "HEAD"], ROOT).stdout.decode().strip()
        dep = ROOT / "hosted/_build/test/lib/jason/ebin"
        receipt["dependency_sha256"] = {str(path.relative_to(ROOT)): sha(path) for path in sorted(dep.iterdir()) if path.is_file()}
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("otp-crypto-versions", ["elixir", "-e", 'Application.load(:public_key); IO.inspect(%{otp: :erlang.system_info(:otp_release), crypto: :crypto.info_lib(), public_key: Application.spec(:public_key, :vsn)})'])
        run("compile", ["elixirc", "--warnings-as-errors", "-pa", dep, "-o", scratch,
                        *[out / "inputs" / name for name in MODULES]])
        command = 'ExUnit.start(autorun: false, seed: 0); Code.require_file(hd(System.argv())); result = ExUnit.run(); File.write!(' + json.dumps(str(out / "test-result.json")) + ', Jason.encode!(result)); System.halt(if result.total == 25 and result.failures == 0 and result.skipped == 0 and result.excluded == 0, do: 0, else: 1)'
        run("tests", ["elixir", "-pa", dep, "-pa", scratch, "-e", command, out / "inputs" / TEST])
        receipt["selected_result"] = json.loads((out / "test-result.json").read_text())
        receipt["status"] = "passed"
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"owned_scratch_removed": not scratch.exists(), "owned_scratch_path": str(scratch),
                              "started_application_database_network_native_capture": False}
        changed = [name for name, value in receipt.get("input_sha256", {}).items() if sha(ROOT / name) != value]
        receipt["live_source_changes_during_run"] = [name for name in changed if name in MODULES + [TEST, str(BASE / "run.py"), "hosted/mix.exs", "hosted/mix.lock"]]
        receipt["as_of_document_changes_during_run"] = [name for name in changed if name not in receipt["live_source_changes_during_run"]]
        if receipt["live_source_changes_during_run"]:
            receipt["status"] = "failed"
        receipt["output_sha256"] = {str(path.relative_to(out)): sha(path) for path in sorted(out.iterdir()) if path.is_file() and path.name != "receipt.json"}
        receipt["recorded_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt.get(key) for key in ["status", "failure", "selected_result", "input_tree_sha256", "cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
