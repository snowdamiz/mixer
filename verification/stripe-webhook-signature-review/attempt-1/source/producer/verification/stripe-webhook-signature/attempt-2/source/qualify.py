"""Freeze exact standalone inputs and retain each bounded command and its output."""
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
HELPER = REPO / "verification/android-coordinator-runner-cleanup/owned_process.py"
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == "209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216"
spec = importlib.util.spec_from_file_location("owned", HELPER)
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    attempt = ROOT / sys.argv[1]
    assert attempt.name.startswith("attempt-") and attempt.parent == ROOT
    attempt.mkdir()
    source = attempt / "source"
    source.mkdir()
    commands = []
    receipt = {"status": "running", "scope": "isolated macOS host signature boundary only",
               "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "commands": commands, "ownedProcessHelper": {"path": str(HELPER.relative_to(REPO)), "sha256": sha(HELPER)},
               "notQualified": ["HTTP raw-body adapter", "durable inbox/Oban", "tenant/account/mode binding", "Stripe provider test mode", "billing reconciliation", "G23"]}

    def save():
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(argv, cwd=source, timeout=45):
        entry = {"argv": argv, "cwd": str(cwd), "timeoutSeconds": timeout}
        commands.append(entry)
        save()
        result = owned.execute(argv, cwd=cwd, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=timeout)
        log = attempt / f"command-{len(commands):02}.log"
        log.write_bytes(result.stdout)
        entry.update(exitCode=result.returncode, timedOut=result.timedOut, cleanup=result.groupCleanup,
                     output={"path": str(log.relative_to(ROOT)), "sha256": sha(log), "bytes": log.stat().st_size})
        save()
        assert result.returncode == 0, f"command failed: {argv}; see {log}"

    try:
        files = ["candidate/webhook_signature.ex", "webhook_signature_test.exs", "generate_vectors.py", "crypto_failure.exs", "qualify.py"]
        for relative in files:
            dest = source / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, dest)
        shutil.copyfile(REPO / "docs/stripe-webhook-signature-contract.md", source / "contract.md")
        run([sys.executable, "generate_vectors.py"])
        if (ROOT / "vectors.json").exists():
            assert (ROOT / "vectors.json").read_bytes() == (source / "vectors.json").read_bytes()
        else:
            shutil.copyfile(source / "vectors.json", ROOT / "vectors.json")
        manifest = [{"path": str(p.relative_to(source)), "sha256": sha(p), "bytes": p.stat().st_size}
                    for p in sorted(source.rglob("*")) if p.is_file()]
        (attempt / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
        receipt["sourceDigest"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        run([sys.executable, "--version"])
        run(["elixir", "--version"])
        run([sys.executable, "generate_vectors.py", "--check"])
        run(["mix", "format", "--check-formatted", "candidate/webhook_signature.ex", "webhook_signature_test.exs", "crypto_failure.exs"])
        compiled = attempt / "compiled"
        compiled.mkdir()
        run(["elixirc", "--warnings-as-errors", "-o", str(compiled), "candidate/webhook_signature.ex"])
        run(["elixir", "webhook_signature_test.exs"])
        for mode in ["error", "throw", "exit", "comparison"]:
            run(["elixir", "crypto_failure.exs", mode])
        for item in manifest:
            assert sha(source / item["path"]) == item["sha256"], "source changed during verification"
        receipt["status"] = "passed-host-only"
    except BaseException as error:
        receipt["status"] = "failed"
        receipt["failure"] = repr(error)
        raise
    finally:
        receipt["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
        artifacts = [{"path": str(p.relative_to(attempt)), "sha256": sha(p), "bytes": p.stat().st_size}
                     for p in sorted(attempt.rglob("*")) if p.is_file() and p.name != "seal.json"]
        (attempt / "seal.json").write_text(json.dumps({"files": artifacts}, indent=2) + "\n")


if __name__ == "__main__":
    main()
