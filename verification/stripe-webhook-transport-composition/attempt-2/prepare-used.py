"""Exact and separately normalized isolated full-hosted composition collector.

No live app is edited. Root approval is required before running --normalize.
Every attempt retains the exact source, output and cleanup, including failures.
"""
import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/stripe-webhook-transport"
REVIEW = ROOT / "verification/stripe-webhook-transport-review"
MODULE = "hosted/lib/mixer_hosted/billing/webhook_transport.ex"
BASELINE_DIGEST = "ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc"
RAW_HASH = "62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0"
SEALS = {
    "verification/stripe-webhook-transport/seal.json": "a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d",
    "verification/stripe-webhook-transport-review/seal.json": "a3d8b7677ce58b23246c61e76e0db13806c5cc53a41c44fd06aa3a75376a4f81",
}
HELPER = ROOT / "verification/android-coordinator-runner-cleanup/owned_process.py"
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == "209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216"
spec = importlib.util.spec_from_file_location("composition_owned", HELPER)
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def tree_digest(inputs):
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def archive(path, base, inputs):
    with tarfile.open(path, "w:gz") as stream:
        for name in sorted(inputs):
            stream.add(base / name, arcname=name, recursive=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    parser.add_argument("--normalize", action="store_true")
    args = parser.parse_args()
    out = HERE / args.attempt
    assert out.parent == HERE and out.name.startswith("attempt-")
    out.mkdir()
    scratch = out / ".scratch"
    source = scratch / "source"
    source.mkdir(parents=True)
    identity = (scratch.stat().st_dev, scratch.stat().st_ino)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["ERL_CRASH_DUMP_SECONDS"] = "0"
    env["ERL_CRASH_DUMP"] = str(scratch / "erl_crash.dump")
    receipt = {
        "schema": 1,
        "status": "preparing",
        "startedUTC": now(),
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "runnerArgv": sys.argv,
        "normalizationSelectedByRoot": args.normalize,
        "producerSealSHA256": SEALS["verification/stripe-webhook-transport/seal.json"],
        "reviewSealSHA256": SEALS["verification/stripe-webhook-transport-review/seal.json"],
        "commands": [],
        "environmentOverrides": {k: env[k] for k in ["PYTHONDONTWRITEBYTECODE", "ERL_CRASH_DUMP_SECONDS", "ERL_CRASH_DUMP"]},
        "scope": "Private additive isolated hosted composition. No live integration, transport activation, public admission, provider, catalog/authority retry, native execution or GA acceptance.",
        "publicAdmissionAccepted": False,
        "gaAccepted": False,
        "liveIntegrated": False,
    }

    def command(label, argv, cwd=ROOT, timeout=60, accepted=(0,), extra_env=None):
        effective = dict(env, **(extra_env or {}))
        result = owned.execute(list(map(str, argv)), cwd=cwd, env=effective, timeout=timeout)
        log = out / (label + ".log")
        log.write_bytes(result.stdout)
        row = {
            "label": label, "argv": list(map(str, argv)), "cwd": str(cwd), "timeoutSeconds": timeout,
            "exitCode": result.returncode, "output": log.name, "sha256": sha(log),
            "timedOut": result.timedOut, "groupCleanup": result.groupCleanup,
            "environmentOverrides": extra_env or {},
        }
        receipt["commands"].append(row)
        save(out / "receipt.json", receipt)
        assert result.returncode in accepted and not result.timedOut, label
        return result.stdout

    try:
        for name, digest in SEALS.items():
            assert sha(ROOT / name) == digest, name
        command("producer-binding", [sys.executable, "-B", PRODUCER / "verify.py"])
        command("review-binding", [sys.executable, "-B", REVIEW / "verify.py"])
        command("accepted-capture-binding", [sys.executable, "-B", ROOT / "verification/stripe-raw-body-integration/verify.py", "--live"])
        accepted = json.loads((ROOT / "verification/stripe-raw-body-integration/acceptance.json").read_text())["sourceInputs"]
        assert len(accepted) == 71 and tree_digest(accepted) == BASELINE_DIGEST
        for name, digest in accepted.items():
            assert sha(ROOT / name) == digest, name
            dest = source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        save(out / "baseline-inputs.json", accepted)
        assert not (source / MODULE).exists() and not (ROOT / MODULE).exists()
        raw = PRODUCER / "candidate/lib/mixer_hosted/billing/webhook_transport.ex"
        assert sha(raw) == RAW_HASH
        shutil.copyfile(raw, out / "reviewed-webhook-transport.ex")
        shutil.copyfile(raw, source / MODULE)
        command("elixir-version", ["elixir", "--version"])
        command("python-version", [sys.executable, "--version"])
        command("os-version", ["uname", "-a"])
        command("postgres-version", ["/opt/homebrew/opt/postgresql@17/bin/postgres", "--version"])
        tools = [sys.executable, "elixir", "mix", "erl", "/opt/homebrew/opt/postgresql@17/bin/postgres", "/opt/homebrew/opt/postgresql@17/bin/pg_ctl", "/opt/homebrew/opt/postgresql@17/bin/initdb"]
        save(out / "toolchain-executables.json", {
            tool: {"resolved": str(Path(shutil.which(tool) or tool).resolve()), "sha256": sha(Path(shutil.which(tool) or tool).resolve())}
            for tool in tools
        })
        if args.normalize:
            command("format-normalize-candidate", ["mix", "format", "lib/mixer_hosted/billing/webhook_transport.ex"], source / "hosted")
            diff = "".join(difflib.unified_diff(raw.read_text().splitlines(keepends=True), (source / MODULE).read_text().splitlines(keepends=True), fromfile="reviewed/webhook_transport.ex", tofile="normalized/webhook_transport.ex"))
            (out / "formatter-only.patch").write_text(diff)
            command("formatter-equivalence", ["elixir", HERE / "equivalence.exs", raw, source / MODULE, out / "formatter-equivalence.json"])
            assert diff and raw.read_text().split() == (source / MODULE).read_text().split(), "non-whitespace normalization"
        receipt["normalization"] = {"reviewedSHA256": RAW_HASH, "composedSHA256": sha(source / MODULE), "difference": "formatter whitespace only" if args.normalize else "none"}
        inputs = dict(accepted, **{MODULE: sha(source / MODULE)})
        assert len(inputs) == 72
        receipt["sourceDigest"] = tree_digest(inputs)
        receipt["sourceInputs"] = 72
        save(out / "source-inputs.json", inputs)
        shutil.copytree(source, out / "source")
        archive(out / "source-closure.tar.gz", source, inputs)
        # Check before resolving/building dependencies, so the original byte-exact
        # candidate's format failure remains its own failed attempt.
        command("format-check", ["mix", "format", "--check-formatted"], source / "hosted")
        command("dependencies", ["mix", "deps.get", "--check-locked"], source / "hosted", timeout=120)
        depbase = source / "hosted/deps"
        depinputs = {str(p.relative_to(depbase)): sha(p) for p in sorted(depbase.rglob("*")) if p.is_file() and not p.is_symlink() and "_build" not in p.relative_to(depbase).parts and ".git" not in p.relative_to(depbase).parts}
        save(out / "dependency-source-inputs.json", depinputs)
        archive(out / "dependency-source-closure.tar.gz", depbase, depinputs)
        command("hosted-suite", [sys.executable, "scripts/test-local.py", "--output", out / "hosted"], source / "hosted", timeout=1200)
        nested = json.loads((out / "hosted/receipt.json").read_text())
        assert nested["status"] == "passed" and nested["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
        assert nested["inputs"] == inputs and nested["source_tree_sha256"] == receipt["sourceDigest"]
        assert "Result: 142 passed, 2 skipped" in (out / "hosted/tests.log").read_text()
        release = source / "hosted/_build/prod/rel/mixer_hosted"
        paths = sorted((release / "lib").glob("*/ebin"))
        command("production-transport-policy", ["elixir", *[item for p in paths for item in ["-pa", p]], HERE / "production-policy.exs"], source / "hosted", extra_env={"MIX_ENV": "prod", "COMPOSITION_POLICY_OUTPUT": str(out / "production-policy.json")})
        app = release / "lib/mixer_hosted-0.1.0/ebin"
        shutil.copytree(app, out / "production-app-ebin")
        test = source / "hosted/_build/test/lib/mixer_hosted/ebin"
        shutil.copytree(test, out / "test-app-ebin")
        compiled = {str(p.relative_to(release)): sha(p) for p in sorted(release.rglob("*")) if p.is_file() and not p.is_symlink()}
        save(out / "production-release-inputs.json", compiled)
        archive(out / "production-release.tar.gz", release, compiled)
        for name, digest in inputs.items():
            assert sha(source / name) == digest, name
        for name, digest in accepted.items():
            assert sha(ROOT / name) == digest, "live source changed: " + name
        assert not (ROOT / MODULE).exists()
        receipt["status"] = "passed-normalized-isolated-hosted-composition-root-integration-pending"
        receipt["nestedReceiptSHA256"] = sha(out / "hosted/receipt.json")
        receipt["fullHostedSuite"] = {"passed": 142, "skipped": 2, "skips": "Existing Linux network-namespace fixtures unavailable on macOS; not passes"}
    except BaseException as failure:
        receipt["status"] = "failed-isolated-hosted-composition"
        receipt["failure"] = repr(failure)
        raise
    finally:
        holders = command("scratch-holders", ["/usr/sbin/lsof", "-nP", "+D", scratch], accepted=(1,))
        assert not holders
        files = [p for p in scratch.rglob("*") if p.is_file() and not p.is_symlink()]
        cleanup = {"path": str(scratch), "files": len(files), "bytes": sum(p.stat().st_size for p in files), "openHolders": 0, "device": identity[0], "inode": identity[1]}
        assert (scratch.stat().st_dev, scratch.stat().st_ino) == identity
        shutil.rmtree(scratch)
        cleanup["identityMatched"] = True
        cleanup["pathAbsent"] = not scratch.exists()
        cleanup["ownedProcessGroupsEmpty"] = all(not c["groupCleanup"]["after"] for c in receipt["commands"])
        receipt["scratchCleanup"] = cleanup
        receipt["finishedUTC"] = now()
        save(out / "receipt.json", receipt)
        shutil.copyfile(__file__, out / "prepare-used.py")
        shutil.copyfile(HELPER, out / "owned-process-used.py")
        for name in ["equivalence.exs", "production-policy.exs"]:
            shutil.copyfile(HERE / name, out / name)
        save(out / "seal.json", {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(out.rglob("*")) if p.is_file() and p != out / "seal.json"})
        print(json.dumps({"status": receipt["status"], "receipt": str(out / "receipt.json"), "cleanup": cleanup}))


if __name__ == "__main__":
    main()
