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
PRODUCER = REPO / "verification/stripe-webhook-transport-integration"
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
    scratch_identity = scratch.stat().st_dev, scratch.stat().st_ino
    receipt = {"status": "prepared-only", "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
               "commands": [], "scope": "Permanent test and release collector candidate; production module unchanged, no live integration or role activation"}
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
        command("accepted-transport-binding", [sys.executable, "-B", str(PRODUCER / "verify.py"), "--live"], REPO)
        before = json.loads((PRODUCER / "acceptance.json").read_text())["sourceInputs"]
        assert len(before) == 72
        for name, expected in before.items():
            assert sha(REPO / name) == expected
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)
        test = "hosted/test/mixer_hosted/billing/webhook_transport_test.exs"
        collector = "hosted/scripts/test-local.py"
        assert not (source / test).exists() and not (REPO / test).exists()
        shutil.copyfile(HERE / "webhook_transport_test.exs", source / test)
        old_source = (source / collector).read_text()
        needle = '    run("release-test-exclusion",'
        assert old_source.count(needle) == 1
        policy = (HERE / "release-transport-policy.exs").read_text()
        replacement = '    release_code += "; " + ' + repr(policy) + '\n' + needle
        (source / collector).write_text(old_source.replace(needle, replacement, 1))
        command("format-test-addition", ["mix", "format", "test/mixer_hosted/billing/webhook_transport_test.exs"], source / "hosted")
        receipt["productionCodeUnchanged"] = True
        receipt["baselineInputs"] = before
        receipt["additions"] = {name: sha(source / name) for name in [test]}
        receipt["replacements"] = {collector: {"beforeSHA256": before[collector], "afterSHA256": sha(source / collector)}}
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
        assert (scratch.stat().st_dev, scratch.stat().st_ino) == scratch_identity
        receipt["scratchCleanup"]["device"], receipt["scratchCleanup"]["inode"] = scratch_identity
        shutil.rmtree(scratch)
        receipt["scratchCleanup"]["pathAbsent"] = not scratch.exists()
        receipt["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(out / "receipt.json", receipt)
        shutil.copyfile(__file__, out / "prepare-used.py")
        save(out / "seal.json", {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                 for p in sorted(out.rglob("*")) if p.is_file() and p != out / "seal.json"})


if __name__ == "__main__":
    main()
