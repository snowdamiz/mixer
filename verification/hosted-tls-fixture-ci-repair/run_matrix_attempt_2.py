#!/usr/bin/env python3
"""Run the existing identity matrix from owned snapshots without changing old receipts."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
TESTS = ["test/mixer_hosted/identity/key_owner_test.exs",
         "test/mixer_hosted/identity/access_token_verifier_test.exs"]
PLATFORM = sys.argv[1]
assert PLATFORM in ("macos", "linux")
RUN = OUT / (sys.argv[2] if len(sys.argv) > 2 else PLATFORM)
RUN.mkdir(exist_ok=False)
SCRATCH = Path(tempfile.mkdtemp(prefix="mixer-tls-fixture-ci-repair-"))
CONTAINER = "mixer-tls-fixture-ci-repair-" + uuid.uuid4().hex[:12]
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (RUN / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def tree(base, prefix):
    return {prefix + str(p.relative_to(base)): sha(p)
            for p in sorted(base.rglob("*")) if p.is_file() and
            "_build" not in p.relative_to(base).parts}


def run(argv, name, cwd=None, env=None, timeout=300):
    start = time.monotonic()
    with (RUN / name).open("x") as log:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=timeout)
    commands.append({"argv": argv, "cwd": str(cwd) if cwd else None,
                     "environmentOverrides": {k: env[k] for k in
                         ("MIX_ENV", "MIX_BUILD_PATH", "MIX_HOME", "MIX_REBAR3")
                         if env and k in env},
                     "exitCode": result.returncode,
                     "elapsedSeconds": time.monotonic() - start,
                     "output": name, "outputSHA256": sha(RUN / name)})
    save("execution.json", {"commands": commands})
    if result.returncode:
        raise RuntimeError(f"{name}: exit {result.returncode}")


before_containers = subprocess.check_output(
    ["docker", "ps", "-aq", "--no-trunc"], text=True).splitlines()
original_packet = tree(ROOT / "verification/hosted-key-owner-implementation", "")
ci_log = ROOT / "verification/github-ci-dd604eca-phoenix/artifact/tests.log"
ci_sha = sha(ci_log)
tls_dirs_before = set()
tmp_root = None
outcome = {"status": "failed", "platform": PLATFORM,
           "runnerSHA256": sha(Path(__file__).resolve()),
           "sourceRevision": subprocess.check_output(
               ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
           "scratch": str(SCRATCH), "image": IMAGE if PLATFORM == "linux" else None,
           "originalFailure": {"path": str(ci_log.relative_to(ROOT)), "sha256": ci_sha}}
try:
    shutil.copytree(ROOT / "hosted", SCRATCH / "hosted",
                    ignore=shutil.ignore_patterns("_build"))
    prior_receipts = SCRATCH / "verification/hosted-key-owner-implementation"
    prior_receipts.mkdir(parents=True)
    source_files = tree(SCRATCH / "hosted", "hosted/")
    source_files = {p: h for p, h in source_files.items() if not p.startswith("hosted/deps/")}
    dep_files = tree(SCRATCH / "hosted/deps", "hosted/deps/")
    for name, files in (("source-manifest.json", source_files),
                        ("dependency-manifest.json", dep_files)):
        save(name, {"files": files,
                    "treeDigest": hashlib.sha256(json.dumps(
                        files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
    outcome["sourceTreeDigest"] = json.loads((RUN / "source-manifest.json").read_text())["treeDigest"]
    outcome["dependencyTreeDigest"] = json.loads((RUN / "dependency-manifest.json").read_text())["treeDigest"]
    outcome["fixtureSHA256"] = source_files["hosted/test/support/identity_tls_fixture.ex"]
    if PLATFORM == "macos":
        env = dict(os.environ, MIX_ENV="test", MIX_BUILD_PATH=str(SCRATCH / "hosted/_build/test"))
        tmp_root = Path(subprocess.check_output(
            ["elixir", "-e", "IO.puts(System.tmp_dir!())"], text=True, env=env).strip())
        tls_dirs_before = set(tmp_root.glob("mixer-key-owner-tls-*"))
        save("tmp-before.json", {"systemTmpDir": str(tmp_root),
                                  "fixtureDirectories": sorted(map(str, tls_dirs_before))})
        for argv, name in ((["sw_vers"], "os-version.log"),
                           (["uname", "-a"], "uname.log"),
                           (["elixir", "--version"], "elixir-version.log"),
                           (["mix", "--version"], "mix-version.log"),
                           (["openssl", "version"], "openssl-version.log")):
            run(argv, name, SCRATCH / "hosted", env)
        run(["mix", "format", "--check-formatted", "test/support/identity_tls_fixture.ex"],
            "format.log", SCRATCH / "hosted", env)
        run(["mix", "test", "--seed", "0"] + TESTS,
            "tests.log", SCRATCH / "hosted", env)
        after = set(tmp_root.glob("mixer-key-owner-tls-*"))
        save("tmp-after.json", {"systemTmpDir": str(tmp_root),
             "newFixtureDirectoriesRetained": sorted(map(str, after - tls_dirs_before))})
        assert not (after - tls_dirs_before), "new TLS key directories retained"
    else:
        shutil.copytree(Path.home() / ".mix/archives/hex-2.5.1",
                        SCRATCH / "mix/archives/hex-2.5.1")
        shutil.copy2(Path.home() / ".mix/elixir/1-20-otp-29/rebar3", SCRATCH / "rebar3")
        setup = ROOT / "verification/hosted-key-owner-implementation/linux_netns_setup.exs"
        shutil.copy2(setup, SCRATCH / "linux_netns_setup.exs")
        save("tool-inputs.json", {"hexArchiveTree": tree(SCRATCH / "mix", "mix/"),
             "rebar3SHA256": sha(SCRATCH / "rebar3"),
             "namespaceSetupSource": str(setup.relative_to(ROOT)),
             "namespaceSetupSHA256": sha(setup)})
        probe = ('IO.inspect(%{system_tmp_dir: System.tmp_dir!(), '
                 'private_tmp_exists: File.exists?("/private/tmp"), '
                 'fixture_directories: Path.wildcard(Path.join(System.tmp_dir!(), '
                 '"mixer-key-owner-tls-*"))}); '
                 'if File.exists?("/private/tmp") or '
                 'Path.wildcard(Path.join(System.tmp_dir!(), "mixer-key-owner-tls-*")) != [], '
                 'do: System.halt(9)')
        # This namespace starts without /private/tmp and never creates that path.
        shell = ("test ! -e /private/tmp\n"
                 "elixir /workspace/linux_netns_setup.exs\n"
                 "elixir --version\nmix --version\nopenssl version\nuname -a\n"
                 "elixir -e " + shlex.quote(probe) + "\n"
                 "mix test --seed 0 " + " ".join(TESTS + [
                     "test/mixer_hosted/identity/key_owner_linux_network_test.exs"]) + "\n"
                 "test ! -e /private/tmp\n"
                 "elixir -e " + shlex.quote(probe))
        argv = ["docker", "run", "--rm", "--name", CONTAINER,
                "--network", "none", "--cap-add", "NET_ADMIN", "--memory", "1g", "--cpus", "4",
                "-v", str(SCRATCH) + ":/workspace", "-w", "/workspace/hosted",
                "-e", "MIX_HOME=/workspace/mix", "-e", "MIX_REBAR3=/workspace/rebar3",
                "-e", "MIXER_ISOLATED_NETNS=1", "-e", "MIX_BUILD_PATH=/workspace/hosted/_build/test",
                "-e", "MIX_ENV=test", IMAGE, "bash", "-euc", shell]
        run(["docker", "version"], "docker-version.log")
        run(["docker", "image", "inspect", IMAGE], "image-inspect.json")
        run(argv, "tests.log")
    shutil.copytree(prior_receipts, RUN / "resource-observations")
    tested_source = tree(SCRATCH / "hosted", "hosted/")
    assert all(tested_source.get(p) == h for p, h in source_files.items()), "tested inputs changed"
    outcome["inputsUnchanged"] = True
    outcome["status"] = "passed"
except Exception as exc:
    outcome["error"] = repr(exc)
    raise
finally:
    if PLATFORM == "linux":
        removal = subprocess.run(["docker", "rm", "-f", CONTAINER],
                                 capture_output=True, text=True)
        remaining = subprocess.check_output(["docker", "ps", "-aq", "--filter",
                     "name=^/" + CONTAINER + "$"], text=True).strip()
    else:
        removal = None
        remaining = ""
    shutil.rmtree(SCRATCH)
    after_containers = subprocess.check_output(
        ["docker", "ps", "-aq", "--no-trunc"], text=True).splitlines()
    cleanup = {"scratchRemoved": not SCRATCH.exists(),
               "ownedContainer": CONTAINER if PLATFORM == "linux" else None,
               "ownedContainerRetained": bool(remaining),
               "preexistingContainerIDs": before_containers,
               "preexistingContainerIDsStillPresent": [p for p in before_containers if p in after_containers],
               "historicalIdentityPacketUnchanged": original_packet == tree(
                   ROOT / "verification/hosted-key-owner-implementation", ""),
               "originalCIFailureUnchanged": ci_sha == sha(ci_log)}
    save("cleanup.json", cleanup)
    save("receipt.json", outcome)
