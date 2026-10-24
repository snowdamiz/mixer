#!/usr/bin/env python3
"""Independent replay in one disposable network-none Linux namespace."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
state = json.loads((OUT / "state.json").read_text())
scratch = Path(state["scratch"])
image = "hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"
container = "mixer-key-owner-independent-ji2mbagy"
def save(name,obj): (OUT / name).write_text(json.dumps(obj,indent=2)+"\n")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(scratch / "verification/hosted-key-owner-implementation", OUT / "macos-replayed-producer-artifacts", dirs_exist_ok=True)
shutil.copytree(Path.home()/".mix/archives/hex-2.5.1",scratch/"mix/archives/hex-2.5.1")
shutil.copy2(Path.home()/".mix/elixir/1-20-otp-29/rebar3",scratch/"rebar3")
shutil.copy2(ROOT/"verification/hosted-key-owner-implementation/linux_netns_setup.exs",scratch/"linux_netns_setup.exs")
script = """set -eu
mkdir -p /private/tmp
elixir /workspace/linux_netns_setup.exs
elixir --version
mix --version
openssl version
uname -a
mix test --seed 0 test/mixer_hosted/identity/key_owner_test.exs test/mixer_hosted/identity/access_token_verifier_test.exs test/mixer_hosted/identity/key_owner_linux_network_test.exs test/mixer_hosted/identity/independent_adversarial_test.exs
elixir -e 'IO.inspect(Enum.filter(File.ls!("/private/tmp"), &String.starts_with?(&1,"mixer-key-owner-tls-")), label: "retained_fixture_key_directories")'
MIX_ENV=prod MIX_BUILD_PATH=/workspace/linux-prod-build mix release --path /workspace/linux-release
elixir -pa /workspace/linux-release/lib/mixer_hosted-0.1.0/ebin -e 'Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); values = %{fixture_transport_exported: function_exported?(MixerHosted.Identity.JWKSTransport,:fetch_fixture,6), fixture_owner_exported: function_exported?(MixerHosted.Identity.KeyOwner,:start_fixture,1), fixture_module_present: Code.ensure_loaded?(MixerHosted.Identity.TLSFixture), independent_fixture_present: Code.ensure_loaded?(MixerHosted.Identity.IndependentAdapterOwner)}; IO.inspect(values,label: "production_fixture_exclusion"); true = Enum.all?(Map.values(values), &(&1 == false))'
"""
(scratch/"review_linux.sh").write_text(script)
prior = subprocess.run(["docker","ps","-aq","--filter","name=^/"+container+"$"],capture_output=True,text=True,check=True)
assert not prior.stdout.strip(), "Unique owned container name unexpectedly occupied"
argv = ["docker","run","--rm","--name",container,"--network","none","--cap-add","NET_ADMIN","--memory","1g","--cpus","4",
        "-v",str(scratch)+":/workspace","-w","/workspace/hosted","-e","MIX_HOME=/workspace/mix","-e","MIX_REBAR3=/workspace/rebar3",
        "-e","MIXER_ISOLATED_NETNS=1","-e","MIX_BUILD_PATH=/workspace/linux-build","-e","MIX_ENV=test",image,"bash","/workspace/review_linux.sh"]
started = time.monotonic()
result = None
try:
    with (OUT/"linux-independent.log").open("w") as log:
        result = subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    shutil.copytree(scratch/"verification/hosted-key-owner-implementation",OUT/"linux-replayed-producer-artifacts",dirs_exist_ok=True)
    save("linux-execution.json",{"argv":argv,"script":"review_linux.sh","scriptSHA256":sha(scratch/"review_linux.sh"),
        "exitCode":result.returncode,"elapsedSeconds":time.monotonic()-started,"observedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "image":image,"network":"none","capabilitiesAdded":["NET_ADMIN"],"testScope":"46 frozen component/pure/DNS tests plus 12 independent adversarial tests; production release build/export exclusion; no application start",
        "output":"linux-independent.log","outputSHA256":sha(OUT/"linux-independent.log")})
finally:
    removal = subprocess.run(["docker","rm","-f",container],capture_output=True,text=True)
    remain = subprocess.run(["docker","ps","-aq","--filter","name=^/"+container+"$"],capture_output=True,text=True)
    save("linux-cleanup.json",{"container":container,"containerRetained":bool(remain.stdout.strip()),"removalExitCode":removal.returncode,
        "removalOutput":removal.stdout+removal.stderr,"scope":"Only the unique owned container; host processes/network unchanged"})
shutil.copy2(scratch/"review_linux.sh",OUT/"review_linux.sh")
print(json.dumps({"exitCode":result.returncode,"elapsedSeconds":time.monotonic()-started}))
