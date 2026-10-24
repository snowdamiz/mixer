#!/usr/bin/env python3
"""Isolated OTP29/Mint TLS transport cap probe. Does not modify product files."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
OTP=pathlib.Path('/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang/lib/ssl-11.7.7/src')
files=['hosted/lib/mixer_hosted/identity/jwks_transport.ex','hosted/lib/mixer_hosted/identity/http_freshness.ex','hosted/lib/mixer_hosted/identity/http_wire_guard.ex','hosted/lib/mixer_hosted/identity/fetch_flight.ex','hosted/test/support/identity_tls_fixture.ex','hosted/deps/mint/lib/mint/core/transport/ssl.ex','hosted/mix.lock']
manifest={}
for rel in files:
    if os.environ.get('PREFLIGHT_REUSE_INPUTS') == '1':
        continue
    p=ROOT/rel
    manifest[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    if rel.endswith('.ex'):
        shutil.copy2(p,OUT/'inputs'/p.name)
for filename in ['ssl.erl','ssl_config.erl','ssl_gen_statem.erl','tls_socket.erl','tls_gen_connection.erl','tls_record.erl','tls_record_1_3.erl','ssl_internal.hrl','ssl_api.hrl']:
    p=OTP/filename
    manifest[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
if os.environ.get('PREFLIGHT_REUSE_INPUTS') != '1':
    (OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'revision.log').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True))
scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-tls-buffer-preflight-',dir='/private/tmp'))
start=time.monotonic()
try:
    for dep in ['mint','hpax','jason']:
        shutil.copytree(ROOT/'hosted/deps'/dep,scratch/'deps'/dep)
    (scratch/'mix.exs').write_text('''defmodule MixerTLSPreflight.MixProject do
  use Mix.Project
  def project, do: [app: :mixer_tls_preflight, version: "0.0.0", deps: [
    {:mint, path: "deps/mint"}, {:hpax, path: "deps/hpax", override: true}, {:jason, path: "deps/jason"}]]
  def application, do: [extra_applications: [:ssl, :inets]]
end
''')
    lib=scratch/'lib'; lib.mkdir()
    for filename in ['http_freshness.ex','http_wire_guard.ex','identity_tls_fixture.ex']:
        shutil.copy2(OUT/'inputs'/filename,lib/filename)
    source=(OUT/'inputs/jwks_transport.ex').read_text()
    for mod,cap in [('Baseline',False),('Capped',True)]:
        candidate=source.replace('defmodule MixerHosted.Identity.JWKSTransport do',f'defmodule Preflight.{mod} do')
        if cap:
            candidate=candidate.replace('verify: :verify_peer,','cb_info: {Preflight.BoundedTCP, :tcp, :tcp_closed, :tcp_error, :tcp_passive},\n        verify: :verify_peer,')
        candidate=candidate.replace('{:ok, body, wire, metrics} <-\n               receive_loop','_ = Preflight.ClientPause.after_request(),\n             {:ok, body, wire, metrics} <-\n               receive_loop')
        (lib/(mod.lower()+'.ex')).write_text(candidate)
    shutil.copy2(OUT/'probe.exs',scratch/'probe.exs')
    env=dict(os.environ,MIX_ENV='test',MIX_BUILD_PATH=str(scratch/'build'),PREFLIGHT_OUTPUT=str(OUT))
    argv=['mix','run','--no-start','probe.exs']
    with (OUT/'probe.log').open('w') as log:
        p=subprocess.run(argv,cwd=scratch,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    (OUT/'execution.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(scratch),'exitCode':p.returncode,'elapsedSeconds':time.monotonic()-start,'scope':'macOS local loopback real verified TLS; isolated source copies; no external service, device, publication, or production mutations'},indent=2)+'\n')
finally:
    shutil.rmtree(scratch)
    (OUT/'cleanup.json').write_text(json.dumps({'scratch':str(scratch),'scratchRemoved':not scratch.exists(),'ownedProcessesRetained':False,'simulatorsUsed':False},indent=2)+'\n')
