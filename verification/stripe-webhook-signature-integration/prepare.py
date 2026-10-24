"""Prepare an additive hosted candidate and test it without editing the live app."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCER = REPO / "verification/stripe-webhook-signature"
HELPER = REPO / "verification/android-coordinator-runner-cleanup/owned_process.py"
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == "209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216"
spec = importlib.util.spec_from_file_location("owned", HELPER)
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    out = HERE / sys.argv[1]
    assert out.name.startswith("attempt-") and out.parent == HERE
    out.mkdir()
    scratch = out / ".scratch"
    source = scratch / "source"
    source.mkdir(parents=True)
    receipt = {"status": "prepared-only", "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "commands": [], "scope": "Additive isolated hosted composition; no live integration, HTTP route, provider or G23 acceptance"}
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def command(label, argv, cwd, timeout=60, accepted=(0,)):
        r = owned.execute(argv, cwd=cwd, env=env, timeout=timeout)
        log = out / (label + ".log")
        log.write_bytes(r.stdout)
        receipt["commands"].append({"label": label, "argv": argv, "cwd": str(cwd), "timeoutSeconds": timeout,
                                    "exitCode": r.returncode, "output": log.name, "outputSHA256": sha(log),
                                    "timedOut": r.timedOut, "groupCleanup": r.groupCleanup})
        save(out / "receipt.json", receipt)
        assert r.returncode in accepted and not r.timedOut, label
        return r.stdout

    try:
        command("producer-binding", [sys.executable, "-B", str(PRODUCER / "verify.py")], REPO)
        tracked = subprocess.check_output(["git", "ls-files", "-z", "hosted"], cwd=REPO).split(b"\0")
        names = [p.decode() for p in tracked if p]
        names += ["services/protocol/testdata/" + p for p in ["signed-release-v3.json", "release-v3-cases.json"]]
        before = {name: sha(REPO / name) for name in names}
        for name in names:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)
        module = "hosted/lib/mixer_hosted/billing/webhook_signature.ex"
        test = "hosted/test/mixer_hosted/billing/webhook_signature_test.exs"
        fixture = "hosted/test/fixtures/billing/webhook-signature.json"
        assert not any((source / p).exists() or (REPO / p).exists() for p in [module, test, fixture])
        for name in [module, test, fixture]:
            (source / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PRODUCER / "candidate/webhook_signature.ex", source / module)
        shutil.copyfile(PRODUCER / "vectors.json", source / fixture)
        test_source = (PRODUCER / "webhook_signature_test.exs").read_text()
        prefix = 'Code.require_file("candidate/webhook_signature.ex", __DIR__)\nExUnit.start(seed: 1)\n\n'
        assert test_source.startswith(prefix)
        test_source = test_source.removeprefix(prefix)
        old = '@vectors __DIR__ |> Path.join("vectors.json") |> File.read!() |> :json.decode()'
        assert test_source.count(old) == 1
        test_source = test_source.replace(old, '@vectors __DIR__ |> Path.join("../../fixtures/billing/webhook-signature.json") |> File.read!() |> :json.decode()', 1)
        (source / test).write_text(test_source)
        command("format-added-test", ["mix", "format", "test/mixer_hosted/billing/webhook_signature_test.exs"], source / "hosted")
        receipt["baselineInputs"] = before
        receipt["additions"] = {name: sha(source / name) for name in [module, test, fixture]}
        inputs = {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()}
        receipt["sourceDigest"] = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        save(out / "source-inputs.json", inputs)
        frozen = out / "source"
        shutil.copytree(source, frozen)
        command("elixir-version", ["elixir", "--version"], source / "hosted")
        command("python-version", [sys.executable, "--version"], source / "hosted")
        command("dependencies", ["mix", "deps.get", "--check-locked"], source / "hosted", timeout=120)
        # The existing collector owns a private PostgreSQL instance and its own
        # cleanup. Retain its full nested receipt even on a failed command.
        command("hosted-suite", [sys.executable, "scripts/test-local.py", "--output", str(out / "hosted")], source / "hosted", timeout=1200)
        nested = json.loads((out / "hosted/receipt.json").read_text())
        assert nested["status"] == "passed" and nested["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
        for name, expected in inputs.items():
            assert sha(source / name) == expected, "candidate source changed"
        for name, expected in before.items():
            assert sha(REPO / name) == expected, "live hosted source changed"
        receipt["status"] = "passed-isolated-hosted-composition-review-pending"
        receipt["nestedReceiptSHA256"] = sha(out / "hosted/receipt.json")
    except BaseException as failure:
        receipt["status"] = "failed-isolated-composition"
        receipt["failure"] = repr(failure)
        raise
    finally:
        # Never remove another lane's data or a live process's open files.
        holders = command("scratch-holders", ["/usr/sbin/lsof", "-nP", "+D", str(scratch)], REPO, accepted=(1,))
        assert not holders
        files = [p for p in scratch.rglob("*") if p.is_file()]
        receipt["scratchCleanup"] = {"path": str(scratch), "files": len(files), "bytes": sum(p.stat().st_size for p in files), "openHolders": 0}
        shutil.rmtree(scratch)
        receipt["scratchCleanup"]["pathAbsent"] = not scratch.exists()
        receipt["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / "receipt.json", receipt)
        shutil.copyfile(__file__, out / "prepare-used.py")
        save(out / "seal.json", {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                 for p in sorted(out.rglob("*")) if p.is_file() and p != out / "seal.json"})


if __name__ == "__main__":
    main()
