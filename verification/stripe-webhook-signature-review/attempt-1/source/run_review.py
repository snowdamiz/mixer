"""Freeze independent inputs and producer packet, then retain bounded host runs."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
EXPECTED_HELPER = "209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(base):
    return [{"path": p.relative_to(base).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(base.rglob("*")) if p.is_file()]


def main():
    attempt = ROOT / sys.argv[1]
    assert attempt.parent == ROOT and attempt.name.startswith("attempt-")
    attempt.mkdir()
    source = attempt / "source"
    source.mkdir()
    for name in ["run_review.py", "audit_packet.py", "generate_cases.py", "review_cases.exs", "late_fault.exs", "crypto_probe.exs"]:
        shutil.copyfile(ROOT / name, source / name)
    helper = REPO / "verification/android-coordinator-runner-cleanup/owned_process.py"
    assert sha(helper) == EXPECTED_HELPER
    shutil.copyfile(helper, source / "owned_process.py")
    snapshot = source / "producer"
    producer = REPO / "verification/stripe-webhook-signature"
    shutil.copytree(producer, snapshot / "verification/stripe-webhook-signature")
    (snapshot / "docs").mkdir()
    for name in ["stripe-webhook-signature-contract.md", "stripe-webhook-signature-evidence.md"]:
        shutil.copyfile(REPO / "docs" / name, snapshot / "docs" / name)
    # All future executable inputs are frozen under this attempt before execution.
    spec = importlib.util.spec_from_file_location("review_owned", source / "owned_process.py")
    owned = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owned)
    receipt = {"schema": 1, "status": "running", "reviewer": {"model": "gpt-6.1-sol", "reasoningEffort": "xhigh"},
               "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "scope": "Independent host review of frozen signature/freshness function; no hosted, provider, native or G23 qualification",
               "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "commands": []}
    def save():
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def run(argv, cwd=source):
        result = owned.execute(argv, cwd=cwd, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=45)
        output = attempt / f"command-{len(receipt['commands'])+1:02}.log"
        output.write_bytes(result.stdout)
        receipt["commands"].append({"argv": argv, "cwd": str(cwd), "timeoutSeconds": 45,
                                    "exitCode": result.returncode, "timedOut": result.timedOut, "cleanup": result.groupCleanup,
                                    "output": {"path": output.relative_to(attempt).as_posix(), "bytes": output.stat().st_size, "sha256": sha(output)}})
        save()
        assert result.returncode == 0 and result.groupCleanup["after"] == [], str(output)
    try:
        run([sys.executable, "generate_cases.py", "cases.json"])
        inputs = manifest(source)
        (attempt / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
        receipt["sourceDigest"] = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        run([sys.executable, "--version"])
        run(["elixir", "--version"])
        run(["uname", "-a"])
        run([sys.executable, "audit_packet.py", str(snapshot)])
        frozen_producer = snapshot / "verification/stripe-webhook-signature"
        run([sys.executable, "-B", str(frozen_producer / "verify.py")])
        run(["elixir", "crypto_probe.exs"])
        compiled = attempt / "compiled"
        compiled.mkdir()
        candidate = frozen_producer / "candidate/webhook_signature.ex"
        run(["elixirc", "--warnings-as-errors", "-o", str(compiled), str(candidate)])
        run(["elixir", "review_cases.exs", str(candidate), "cases.json"])
        for mode in ["late_mac", "late_compare", "late_throw", "late_exit", "schedule"]:
            run(["elixir", "late_fault.exs", str(candidate), mode])
        # Reproduce original tests and fault processes from their exact final snapshot.
        final_source = frozen_producer / "attempt-4/source"
        run([sys.executable, "generate_vectors.py", "--check"], final_source)
        run(["elixir", "webhook_signature_test.exs"], final_source)
        for mode in ["error", "throw", "exit", "comparison", "schedule"]:
            run(["elixir", "crypto_failure.exs", mode], final_source)
        run([sys.executable, "audit_packet.py", str(snapshot)])
        assert manifest(source) == inputs, "frozen source changed during review"
        receipt["independentCaseCount"] = len(json.loads((source / "cases.json").read_text())["cases"])
        receipt["status"] = "passed-bounded-host-review"
    except BaseException as error:
        receipt["status"] = "failed"
        receipt["failure"] = repr(error)
        raise
    finally:
        receipt["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        artifacts = [{"path": p.relative_to(attempt).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
                     for p in sorted(attempt.rglob("*")) if p.is_file() and p != attempt / "seal.json"]
        (attempt / "seal.json").write_text(json.dumps({"schema": 1, "files": artifacts}, indent=2) + "\n")


if __name__ == "__main__":
    main()
