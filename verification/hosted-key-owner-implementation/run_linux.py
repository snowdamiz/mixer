#!/usr/bin/env python3
"""Disposable network-isolated Linux verification; no provider/deployment."""
import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
scratch = pathlib.Path(tempfile.mkdtemp(prefix="mixer-key-owner-linux-", dir="/private/tmp"))
image = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
name = "mixer-key-owner-linux-tests"

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")

try:
    shutil.copytree(ROOT / "hosted", scratch / "hosted", ignore=shutil.ignore_patterns("_build"))
    shutil.copytree(pathlib.Path.home() / ".mix/archives/hex-2.5.1", scratch / "mix/archives/hex-2.5.1")
    shutil.copy2(pathlib.Path.home() / ".mix/elixir/1-20-otp-29/rebar3", scratch / "rebar3")
    (scratch / "verification/hosted-key-owner-implementation").mkdir(parents=True)
    shutil.copy2(OUT/"linux_netns_setup.exs",scratch/"linux_netns_setup.exs")
    sources = [p for p in (scratch / "hosted").rglob("*") if p.is_file() and "deps" not in p.parts and
               (p.suffix in [".ex", ".exs"] or p.name == "mix.lock")]
    manifest = {str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    save("linux-source-manifest.json", {"files": manifest,
         "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()})
    with tarfile.open(OUT / "linux-source.tar.gz", "w:gz") as archive:
        for source in sorted(sources):
            archive.add(source, arcname=str(source.relative_to(scratch)))
    argv = ["docker", "run", "--rm", "--name", name, "--network", "none", "--cap-add", "NET_ADMIN", "--memory", "1g", "--cpus", "4",
            "-v", str(scratch) + ":/workspace", "-w", "/workspace/hosted", "-e", "MIX_HOME=/workspace/mix",
            "-e", "MIX_REBAR3=/workspace/rebar3", "-e", "MIXER_ISOLATED_NETNS=1", "-e", "MIX_BUILD_PATH=/workspace/build", "-e", "MIX_ENV=test",
            image, "bash", "-c", "mkdir -p /private/tmp; elixir /workspace/linux_netns_setup.exs; elixir --version; openssl version; uname -a; "
            "mix test --seed 0 test/mixer_hosted/identity/key_owner_test.exs test/mixer_hosted/identity/access_token_verifier_test.exs test/mixer_hosted/identity/key_owner_linux_network_test.exs"]
    start = time.monotonic()
    with (OUT / "linux-tests.log").open("w") as log:
        tested = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    prod_code = ('Application.load(:ssl); Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); '
                 'IO.inspect(%{os: :os.type(), fixture_transport_exported: function_exported?(MixerHosted.Identity.JWKSTransport,:fetch_fixture,6),'
                 'fixture_owner_exported: function_exported?(MixerHosted.Identity.KeyOwner,:start_fixture,1), ssl: Application.spec(:ssl,:vsn)}); '
                 'IO.puts(File.read!(Path.join([:code.root_dir(),"releases",System.otp_release(),"OTP_VERSION"])))')
    prod_argv = argv[:-1] + ["MIX_ENV=prod MIX_BUILD_PATH=/workspace/prod-build mix release --path /workspace/release && "
                            "elixir -pa /workspace/release/lib/mixer_hosted-0.1.0/ebin -e " + shlex.quote(prod_code)]
    with (OUT / "linux-prod-compile-exports.log").open("w") as log:
        prod = subprocess.run(prod_argv, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    for result in (scratch / "verification/hosted-key-owner-implementation").glob("*.json"):
        shutil.copy2(result, OUT / ("linux-" + result.name))
    save("linux-execution.json", {"argv": argv, "exitCode": tested.returncode, "elapsedSeconds": time.monotonic() - start,
         "image": image, "network": "none", "scratch": str(scratch), "prodArgv": prod_argv,
         "prodExitCode": prod.returncode, "sourceManifest": "linux-source-manifest.json"})
finally:
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    shutil.rmtree(scratch)
    remains = subprocess.run(["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"], capture_output=True, text=True)
    save("linux-cleanup.json", {"scratchRemoved": not scratch.exists(), "container": name,
         "containerRetained": bool(remains.stdout.strip())})
