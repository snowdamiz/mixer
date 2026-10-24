#!/usr/bin/env python3
"""Source-bound host-only checks for the explicit identity component."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
owned = sorted((ROOT / 'hosted/lib/mixer_hosted/identity').glob('*.ex'))
owned += sorted((ROOT / 'hosted/test/support').glob('identity_*.ex'))
owned += sorted((ROOT / 'hosted/test/mixer_hosted/identity').glob('*.exs'))
manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in owned}
(OUT / 'source-manifest.json').write_text(json.dumps({'sourceRevision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'files':manifest},indent=2)+'\n')
environment = dict(os.environ, MIX_ENV='test', MIX_BUILD_PATH='/private/tmp/mixer-key-owner-build')
commands=[]
def run(argv, output, env=environment, cwd=ROOT/'hosted'):
    start=time.monotonic()
    with (OUT/output).open('w') as log:
        result=subprocess.run(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append({'argv':argv,'cwd':str(cwd),'environment':{'MIX_ENV':env.get('MIX_ENV'),'MIX_BUILD_PATH':env.get('MIX_BUILD_PATH')},'exitCode':result.returncode,'elapsedSeconds':time.monotonic()-start,'output':output,'outputSHA256':hashlib.sha256((OUT/output).read_bytes()).hexdigest()})
    return result.returncode
before=set(Path('/private/tmp').glob('mixer-key-owner-tls-*'))
run(['elixir','--version'],'elixir-version.log')
run(['mix','--version'],'mix-version.log')
run(['openssl','version'],'openssl-version.log')
run(['mix','format','--check-formatted']+[str(p.relative_to(ROOT/'hosted')) for p in owned],'format-final.log')
run(['mix','test','--seed','0','test/mixer_hosted/identity/key_owner_test.exs','test/mixer_hosted/identity/access_token_verifier_test.exs'],'macos-tests-final.log')
prod_env=dict(environment,MIX_ENV='prod',MIX_BUILD_PATH='/private/tmp/mixer-key-owner-prod-build')
run(['mix','compile'],'prod-compile-final.log',prod_env)
code='Application.load(:ssl); Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); IO.inspect(%{os: :os.type(), ssl: Application.spec(:ssl,:vsn),fixture_transport_exported: function_exported?(MixerHosted.Identity.JWKSTransport,:fetch_fixture,6),fixture_owner_exported: function_exported?(MixerHosted.Identity.KeyOwner,:start_fixture,1)}); IO.puts(File.read!(Path.join([:code.root_dir(),"releases",System.otp_release(),"OTP_VERSION"])))'
run(['elixir','-pa','/private/tmp/mixer-key-owner-prod-build/lib/mixer_hosted/ebin','-e',code],'prod-exports-final.log',prod_env)
after=set(Path('/private/tmp').glob('mixer-key-owner-tls-*'))
unchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in manifest.items())
(OUT/'macos-execution.json').write_text(json.dumps({'commands':commands,'sourceManifest':'source-manifest.json','inputsUnchanged':unchanged,'newTLSKeyDirectoriesRetained':[str(p) for p in sorted(after-before)],'scope':'45 explicit host identity tests; no DB/provider/application or native-device startup'},indent=2)+'\n')
