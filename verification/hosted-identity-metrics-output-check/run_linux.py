#!/usr/bin/env python3
"""Run final identity sources with explicit owned evidence output and no legacy writes."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = OUT / "linux-final"
RUN.mkdir(exist_ok=False)
SCRATCH = Path(tempfile.mkdtemp(prefix="mixer-identity-metrics-output-check-")).resolve()
CONTAINER = "mixer-identity-metrics-output-check-" + uuid.uuid4().hex[:12]
IMAGE = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
EXPECTED_METRICS = {
    "transport-metrics.json", "chunked-TLS-resources.json",
    "owner-four-full-candidate-publication.json", "hostile-fast-TLS-resources.json",
    "suspended-consumer-TLS-resources.json", "handshake-cleanup.json",
    "crash-restart-cleanup.json", "history-metadata-size.json",
    "production-DNS-rebinding.json",
}
EXPECTED_SOURCE_CHANGES = {
    "hosted/scripts/test-local.py",
    "hosted/test/mixer_hosted/identity/key_owner_test.exs",
    "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs",
}
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    (RUN / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def tree(base, prefix=""):
    return {prefix + str(p.relative_to(base)): sha(p) for p in sorted(base.rglob("*"))
            if p.is_file() and "_build" not in p.relative_to(base).parts}


def digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(argv, name, timeout=300):
    start = time.monotonic()
    with (RUN / name).open("x") as log:
        result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    commands.append({"argv": argv, "cwd": str(ROOT), "exitCode": result.returncode,
                     "elapsedSeconds": time.monotonic() - start,
                     "output": name, "outputSHA256": sha(RUN / name)})
    save("execution.json", {"commands": commands})
    if result.returncode:
        raise RuntimeError(f"{name}: exit {result.returncode}")


frozen = {name: tree(ROOT / "verification" / name) for name in
          ("hosted-key-owner-implementation", "hosted-tls-fixture-ci-repair")}
save("frozen-evidence-before.json", {name: {"files": files, "treeDigest": digest(files)}
                                   for name, files in frozen.items()})
before_containers = subprocess.check_output(["docker", "ps", "-aq", "--no-trunc"], text=True).splitlines()
ci_log = ROOT / "verification/github-ci-dd604eca-phoenix/artifact/tests.log"
ci_sha = sha(ci_log)
outcome = {"status": "failed", "runnerSHA256": sha(Path(__file__).resolve()),
           "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
           "scratch": str(SCRATCH), "image": IMAGE,
           "environment": {"MIXER_TEST_IDENTITY_EVIDENCE": "/workspace/identity-metrics",
                           "MIXER_ISOLATED_NETNS": "1", "MIX_ENV": "test"},
           "scope": "46-case Linux identity component matrix and explicit metrics routing; no hosted service or provider startup"}
try:
    shutil.copytree(ROOT / "hosted", SCRATCH / "hosted", ignore=shutil.ignore_patterns("_build"))
    metrics = SCRATCH / "identity-metrics"
    metrics.mkdir()
    shutil.copytree(Path.home() / ".mix/archives/hex-2.5.1", SCRATCH / "mix/archives/hex-2.5.1")
    shutil.copy2(Path.home() / ".mix/elixir/1-20-otp-29/rebar3", SCRATCH / "rebar3")
    setup = ROOT / "verification/hosted-key-owner-implementation/linux_netns_setup.exs"
    shutil.copy2(setup, SCRATCH / "linux_netns_setup.exs")
    source = {p: h for p, h in tree(SCRATCH / "hosted", "hosted/").items()
              if not p.startswith("hosted/deps/")}
    deps = tree(SCRATCH / "hosted/deps", "hosted/deps/")
    save("source-manifest.json", {"files": source, "treeDigest": digest(source)})
    save("dependency-manifest.json", {"files": deps, "treeDigest": digest(deps)})
    prior_path = ROOT / "verification/hosted-tls-fixture-ci-repair/linux-final/source-manifest.json"
    prior = json.loads(prior_path.read_text())
    differences = {p: {"beforeSHA256": prior["files"].get(p), "afterSHA256": source.get(p)}
                   for p in sorted(prior["files"].keys() | source.keys())
                   if prior["files"].get(p) != source.get(p)}
    save("source-differences-from-repair.json", {
        "priorManifest": str(prior_path.relative_to(ROOT)), "priorManifestSHA256": sha(prior_path),
        "priorSourceTreeDigest": prior["treeDigest"], "currentSourceTreeDigest": digest(source),
        "differences": differences})
    assert set(differences) == EXPECTED_SOURCE_CHANGES, differences
    prior_deps = json.loads((prior_path.parent / "dependency-manifest.json").read_text())
    assert deps == prior_deps["files"], "dependencies changed from repaired accepted matrix"
    outcome.update({"sourceTreeDigest": digest(source), "dependencyTreeDigest": digest(deps),
                    "fixtureSHA256": source["hosted/test/support/identity_tls_fixture.ex"],
                    "exactSourceChangesFromAcceptedRepair": sorted(differences)})
    save("tool-inputs.json", {"hexArchiveTree": tree(SCRATCH / "mix", "mix/"),
         "rebar3SHA256": sha(SCRATCH / "rebar3"), "namespaceSetupSource": str(setup.relative_to(ROOT)),
         "namespaceSetupSHA256": sha(setup)})
    run(["git", "diff", "--", *sorted(EXPECTED_SOURCE_CHANGES)], "root-source-diff.patch")
    probe = ('IO.inspect(%{system_tmp_dir: System.tmp_dir!(), '
             'private_tmp_exists: File.exists?("/private/tmp"), '
             'fixture_directories: Path.wildcard(Path.join(System.tmp_dir!(), "mixer-key-owner-tls-*"))}); '
             'if File.exists?("/private/tmp") or '
             'Path.wildcard(Path.join(System.tmp_dir!(), "mixer-key-owner-tls-*")) != [], do: System.halt(9)')
    versions = ('Application.load(:ssl); IO.inspect(%{ssl: Application.spec(:ssl,:vsn)}); '
                'IO.puts(File.read!(Path.join([:code.root_dir(),"releases",System.otp_release(),"OTP_VERSION"])))')
    shell = ("test ! -e /private/tmp\n"
             "elixir /workspace/linux_netns_setup.exs\n"
             "elixir --version\nmix --version\nopenssl version\nuname -a\n"
             "elixir -e " + shlex.quote(versions) + "\n"
             "elixir -e " + shlex.quote(probe) + "\n"
             "mix test --seed 0 test/mixer_hosted/identity/key_owner_test.exs "
             "test/mixer_hosted/identity/access_token_verifier_test.exs "
             "test/mixer_hosted/identity/key_owner_linux_network_test.exs\n"
             "test ! -e /private/tmp\n"
             "test ! -e /workspace/verification\n"
             "elixir -e " + shlex.quote(probe))
    argv = ["docker", "run", "--rm", "--name", CONTAINER, "--network", "none", "--cap-add", "NET_ADMIN",
            "--memory", "1g", "--cpus", "4", "-v", str(SCRATCH) + ":/workspace", "-w", "/workspace/hosted",
            "-e", "MIX_HOME=/workspace/mix", "-e", "MIX_REBAR3=/workspace/rebar3",
            "-e", "MIXER_ISOLATED_NETNS=1", "-e", "MIX_BUILD_PATH=/workspace/hosted/_build/test",
            "-e", "MIX_ENV=test", "-e", "MIXER_TEST_IDENTITY_EVIDENCE=/workspace/identity-metrics",
            IMAGE, "bash", "-euc", shell]
    run(["docker", "version"], "docker-version.log")
    run(["docker", "image", "inspect", IMAGE], "image-inspect.json")
    run(argv, "tests.log")
    produced = {p.name for p in metrics.iterdir() if p.is_file()}
    assert produced == EXPECTED_METRICS, produced
    for metric in metrics.iterdir():
        json.loads(metric.read_text())
    shutil.copytree(metrics, RUN / "identity-metrics")
    assert not (SCRATCH / "verification").exists(), "legacy source-relative evidence path created"
    tested_source = tree(SCRATCH / "hosted", "hosted/")
    assert all(tested_source.get(p) == h for p, h in source.items()), "tested source inputs changed"
    assert all(sha(ROOT / p) == h for p, h in source.items()), "live source changed during matrix"
    assert tree(SCRATCH / "hosted/deps", "hosted/deps/") == deps, "dependency source inputs changed"
    log = (RUN / "tests.log").read_text()
    assert "Result: 46 passed\n" in log
    assert log.count('%{system_tmp_dir: "/tmp", private_tmp_exists: false, fixture_directories: []}') == 2
    outcome.update({"status": "passed", "passed": 46, "invalid": 0, "skipped": 0,
                    "inputsUnchanged": True, "legacyEvidencePathCreated": False,
                    "allNineMetricsInExplicitDirectory": True,
                    "identityMetrics": tree(RUN / "identity-metrics")})
except Exception as exc:
    outcome["error"] = repr(exc)
    raise
finally:
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    remaining = subprocess.check_output(["docker", "ps", "-aq", "--filter", "name=^/" + CONTAINER + "$"], text=True).strip()
    shutil.rmtree(SCRATCH)
    after_containers = subprocess.check_output(["docker", "ps", "-aq", "--no-trunc"], text=True).splitlines()
    unchanged = {name: files == tree(ROOT / "verification" / name) for name, files in frozen.items()}
    save("cleanup.json", {"scratchRemoved": not SCRATCH.exists(), "ownedContainer": CONTAINER,
         "ownedContainerRetained": bool(remaining), "frozenPacketsUnchanged": unchanged,
         "originalCIFailureUnchanged": ci_sha == sha(ci_log),
         "preexistingContainerIDs": before_containers,
         "preexistingContainerIDsStillPresent": [p for p in before_containers if p in after_containers]})
    save("receipt.json", outcome)
