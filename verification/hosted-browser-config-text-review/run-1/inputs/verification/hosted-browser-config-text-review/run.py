#!/usr/bin/env python3
"""Independent selected Config review; no app startup, network, database or harness."""
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
BASE = Path("verification/hosted-browser-config-text-review")
MODULES = ["identity/encoding.ex", "identity/bounded_json.ex", "identity/manifest.ex", "identity/startup_config.ex", "browser_auth/config.ex", "browser_auth/configuration_digest.ex"]
MODULES = ["hosted/lib/mixer_hosted/" + name for name in MODULES]
TESTS = ["hosted/test/mixer_hosted/browser_auth/config_test.exs", "hosted/test/mixer_hosted/browser_auth/configuration_digest_test.exs", str(BASE / "probes.exs")]
FIELDS = "mode public_origin profile_id profile_version issuer client_id api_audience authorization_endpoint token_endpoint id_token_jwks_endpoint redirect_uri client_auth_method client_credential_ref session_vault_ref scope response_mode response_iss_required transaction_seconds session_idle_seconds return_path failure_path".split()
PRODUCER_INPUTS = ROOT / "verification/hosted-browser-config-text-admission/attempts/20261025T160312880595Z/source-inputs.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    out = ROOT / BASE / args.attempt
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-config-text-review-"))
    receipt = {"status": "failed", "commands": [], "source_revision": "1257cbf83f973d3ad05a3a279f94007476f7ce2b", "scope": "independent exact Config/producer-test source review plus six adversarial groups and six Python canonical-JSON/SHA256 comparisons; no whole hosted harness or application/provider/DB/native/capture activation", "cleanup": {}}
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test", MIXER_CONFIG_TEXT_REVIEW_VECTORS=str(out / "vectors.jsonl"))

    def run(name, argv):
        argv = [str(arg) for arg in argv]
        result = subprocess.run(argv, cwd=out / "inputs", env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(out / "inputs"), "exit_code": result.returncode, "stdout": name + ".stdout", "stderr": name + ".stderr"})
        if result.returncode:
            raise RuntimeError(name + " failed")
        return result

    try:
        paths = MODULES + TESTS + [str(BASE / "run.py"), "hosted/mix.exs", "hosted/mix.lock"]
        expected = json.loads(PRODUCER_INPUTS.read_text())["files"]
        receipt["producer_hashes_match"] = all(sha(ROOT / name) == expected[name] for name in MODULES + TESTS[:2])
        if not receipt["producer_hashes_match"]:
            raise RuntimeError("live review sources differ from producer accepted snapshot")
        manifest = {}
        for name in paths:
            target = out / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest[name] = sha(target)
        receipt["input_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        dep = ROOT / "hosted/_build/test/lib/jason/ebin"
        receipt["dependency_sha256"] = {str(path.relative_to(ROOT)): sha(path) for path in sorted(dep.iterdir()) if path.is_file()}
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("compile", ["elixirc", "--warnings-as-errors", "-pa", dep, "-o", scratch, *[out / "inputs" / name for name in MODULES]])
        command = 'ExUnit.start(autorun: false, seed: 0); Enum.each(System.argv(), &Code.require_file/1); result = ExUnit.run(); File.write!(' + json.dumps(str(out / "test-result.json")) + ', Jason.encode!(result)); System.halt(if result.total == 32 and result.failures == 0 and result.skipped == 0 and result.excluded == 0, do: 0, else: 1)'
        run("tests", ["elixir", "-pa", dep, "-pa", scratch, "-e", command, *[out / "inputs" / name for name in TESTS]])
        vectors = [json.loads(line) for line in (out / "vectors.jsonl").read_text().splitlines()]
        if len(vectors) != 6:
            raise RuntimeError("expected five Unicode vectors and one baseline")
        comparisons = []
        for vector in vectors:
            value = vector["config"]
            canonical = b"mixer.browser.configuration.v1\x00" + json.dumps([1, [[name, value[name]] for name in FIELDS]], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if canonical.hex() != vector["canonical_hex"] or hashlib.sha256(canonical).hexdigest() != vector["digest_hex"]:
                raise RuntimeError("independent Python bytes/digest mismatch")
            comparisons.append({"client_id": value["client_id"], "canonical_bytes": len(canonical), "digest_hex": vector["digest_hex"], "matches": True})
        (out / "python-reference.json").write_text(json.dumps(comparisons, indent=2, ensure_ascii=False) + "\n")
        receipt["selected_result"] = json.loads((out / "test-result.json").read_text())
        receipt["independent_review_groups"] = 6
        receipt["python_comparisons"] = len(comparisons)
        receipt["status"] = "passed"
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"owned_scratch_removed": not scratch.exists(), "started_postgres_native_capture_provider": False}
        receipt["live_source_changes_during_run"] = [name for name, expected in receipt.get("input_sha256", {}).items() if sha(ROOT / name) != expected]
        if receipt["live_source_changes_during_run"]:
            receipt["status"] = "failed"
        receipt["output_sha256"] = {str(path.relative_to(out)): sha(path) for path in sorted(out.iterdir()) if path.is_file() and path.name != "receipt.json"}
        receipt["recorded_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt.get(key) for key in ["status", "failure", "selected_result", "python_comparisons", "source_tree_sha256", "cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
