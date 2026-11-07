#!/usr/bin/env python3
"""Bounded pure offline review of the exact successful ordinary Phoenix CI."""
import sys
def audit(event,args):
 if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.fork','os.posix_spawn','pty.spawn'}:raise RuntimeError('offline audit denied '+event)
sys.addaudithook(audit)
import datetime,hashlib,io,json,os,platform,re,signal,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent;P=ROOT/'phoenix/_temp/phoenix-foundation'
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('40 second offline bound')));signal.alarm(40)
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def readjson(p):return json.loads(p.read_bytes())
run=readjson(ROOT/'40776622860-meta-metadata.json');job,=readjson(ROOT/'40776622860-jobs-metadata.json')['jobs'];art,=readjson(ROOT/'40776622860-artifacts-metadata.json')['artifacts']
sha='5efcb6a2bcf3b076c9a4452926a842209302e56b';tree='18f204207b0c7dd8f331e0cd947c10b41a663770'
assert run['id']==40776622860 and run['head_sha']==sha and run['head_commit']['tree_id']==tree and run['run_attempt']==1 and run['event']=='push' and run['conclusion']=='success'
assert job['id']==123127479270 and job['run_id']==run['id'] and job['conclusion']=='success'
assert art['id']==12855696376 and art['workflow_run']['head_sha']==sha and art['workflow_run']['id']==run['id']
raw=(ROOT/'phoenix-artifact.zip').read_bytes();assert len(raw)==890670 and art['digest']=='sha256:'+digest(raw)=='sha256:1fa5de4a25e531effda21b3c0bac668c5405c25877ffbf1d182c1bdc12023fc0'
r=readjson(P/'receipt.json');assert r['schema']==2 and r['status']=='passed' and r['source_tree_sha256']==digest(canonical(r['inputs']))
assert len(r['commands'])==43 and r['commands'][0]['label']=='revision' and r['commands'][-1]['label']=='postgres-stop'
for x in r['commands']:
 assert x['exit_code']==(1 if x['label']=='release-missing-config' else 0)
 assert digest((P/x['log']).read_bytes())==x['sha256']
commands={x['label']:x for x in r['commands']};assert len(commands)==43
for label,argv in {'format':['mix','format','--check-formatted'],'compile':['mix','compile','--warnings-as-errors'],'tests':['mix','test','--warnings-as-errors','--seed','0','--trace'],'release-build':['mix','release','--overwrite']}.items():assert commands[label]['argv']==argv
assert (P/'revision.log').read_text().strip()==sha
assert r['cleanup']=={'postgres_stopped':True,'scratch_removed':True}
archive=(P/'source.tar.gz').read_bytes();assert digest(archive)==r['source_archive_sha256']
sources={};folded=set();expanded=0
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
 for m in t.getmembers():
  p=m.name;assert p and not p.startswith('/') and '\\' not in p and ':' not in p and '\x00' not in p and str(PurePosixPath(p))==p and all(x not in ('','.','..') for x in p.split('/'))
  assert m.isfile() and not m.linkname and set(m.pax_headers)<= {'mtime'} and p.casefold() not in folded and 0<=m.size<=256*1024*1024
  expanded+=m.size;assert expanded<=256*1024*1024
  b=t.extractfile(m).read();assert len(b)==m.size;sources[p]=b;folded.add(p.casefold())
assert len(sources)==182 and {p:digest(b) for p,b in sources.items()}==r['inputs']
selected=readjson(ROOT/'network/product-source-manifest.json');assert len(selected)==178
assert digest(canonical(selected))=='8d0139c8c64e02f29f42a96384661f60dd7b724fa5fb4d5f54f6e7c1b7b78cd3'
assert all(sources[p] and {'bytes':len(sources[p]),'sha256':digest(sources[p])}==v for p,v in selected.items())
control='hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs';fixture='hosted/test/support/identity_tls_fixture.ex'
assert len(sources[control])==4401 and digest(sources[control])=='a76b33c4cefac67797fed2909fe7b0c2eb7f7bb99a40b7924adc68901a514fff'
assert digest(sources[fixture])=='d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55'
assert (P/'format.log').read_bytes()==b'' and (P/'compile.log').read_text()=='Compiling 96 files (.ex)\nGenerated mixer_hosted app\n'
testnames=re.findall(r'^  test "([^"]+)"',sources[control].decode(),re.M);assert len(testnames)==4
testlog=(P/'tests.log').read_bytes().decode();assert testlog.endswith('Result: 701 passed, 2 skipped\n')
lines=re.split(r'\r|\n',testlog)
completed=[x for x in lines if re.fullmatch(r'  \* test .*\((?:[\d.]+(?:ms|s)|skipped)\) \[L#\d+\]',x)]
skipped=[x for x in completed if '(skipped)' in x];assert len(completed)==703 and len(skipped)==2
expected_network=['K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched','IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle']
assert all(any(('test '+n+' (skipped)') in x for x in skipped) for n in expected_network)
control_header='MixerHosted.Identity.TLSFixtureLifecycleControlTest [test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs]'
assert testlog.count(control_header)==1
controlblock=testlog.split(control_header)[1].split('\n\n')[0]
for name in testnames:assert len([x for x in completed if re.fullmatch(r'  \* test '+re.escape(name)+r' \([\d.]+ms\) \[L#\d+\]',x)])==1
outcomes=[
{'stage':'peer_close','outcome':'peer_closed','accepted':1,'requests':1,'peer_closed':1,'unexpected_bytes':0},
{'stage':'handshake','outcome':'peer_closed','accepted':1,'requests':0,'peer_closed':1,'unexpected_bytes':0},
{'stage':'peer_close','outcome':'timeout','accepted':1,'requests':1,'peer_closed':0,'unexpected_bytes':0},
{'stage':'peer_close','outcome':'unexpected_data','accepted':1,'requests':1,'peer_closed':0,'unexpected_bytes':25}]
diagnostics=re.findall(r'TLSFixture lifecycle: (.*)',controlblock);assert len(diagnostics)==4
for name,outcome,line in zip(testnames,outcomes,diagnostics):
 expected='%{active: 0, requests: '+str(outcome['requests'])+', accepted: 1, peer_closed: '+str(outcome['peer_closed'])+', terminal_results: [%{stage: :'+outcome['stage']+', outcome: :'+outcome['outcome']+', unexpected_bytes: '+str(outcome['unexpected_bytes'])+'}]}'
 assert line==expected
assert 'invalid or missing hosted setting: MIXER_HOSTED_ROLE' in (P/'release-missing-config.log').read_text()
exclusion=(P/'release-test-exclusion.log').read_text()
assert 'production_test_export_exclusion:' in exclusion and 'production_key_owner_supervisor_fixture_init_exclusion:' in exclusion and 'fixture_init_rejected: true' in exclusion
assert 'production_transport_policy: passed; 4 production modules; test helpers absent; role inactive' in exclusion
elixir=(P/'elixir-version.log').read_text();postgres=(P/'postgres-version.log').read_text()
assert 'Elixir 1.20.4 (compiled with Erlang/OTP 29)' in elixir and 'PostgreSQL) 16.15' in postgres
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ordinary-phoenix-format-compile-four-lifecycle-controls-and-host-suite-qualified','source_revision':sha,'source_tree':tree,'run_id':run['id'],'job_id':job['id'],'run_attempt':1,'artifact_id':art['id'],'zip':{'bytes':len(raw),'sha256':digest(raw)},'source_archive':{'sha256':digest(archive),'files':len(sources),'expanded_bytes':expanded,'all_input_hashes_joined':True,'all_network_selected178_sources_joined':True,'network_selected_digest':digest(canonical(selected))},'commands_verified':len(r['commands']),'format':{'argv':commands['format']['argv'],'exit':0},'compile':{'argv':commands['compile']['argv'],'exit':0,'files':96},'new_TLS_lifecycle_controls':{'source_names':testnames,'source_sha256':digest(sources[control]),'runtime_execution_observed':True,'passed':4,'failed':0,'diagnostics':outcomes,'all_handlers_active_zero':True},'ordinary_suite':{'passed':701,'skipped':2,'total':703,'failed':0,'completed_trace_methods':len(completed),'skip_names':expected_network,'argv':commands['tests']['argv'],'summary':'Result: 701 passed, 2 skipped','seconds':121.8},'release':{'build_passed':True,'missing_config_failed_closed':True,'test_exclusion_passed':True,'scope':'synthetic ordinary CI packaged release; no release publication'},'cleanup':r['cleanup'],'remote_tools':{'elixir':elixir,'postgres':postgres},'local_command':['/usr/bin/python3','-B',str(ROOT/'verify_phoenix.py')],'local_python':platform.python_version(),'script_sha256':digest(Path(__file__).read_bytes()),'own_process':{'pid':os.getpid(),'ppid':os.getppid(),'pgrp':os.getpgrp(),'alarm_seconds':40,'no_children_or_network':True},'offline_audit_denies_network_and_children':True,'local_product_or_runtime_execution':False,'alarm_seconds':40,'scope':r['scope'],'limitations':r['limitations']+['remote Ubuntu synthetic host evidence; no provider, native, customer or GA acceptance','703 trace methods include two intentionally skipped isolated network methods; separate network run executes both','local compiler/Elixir/Swift/runtime/Docker/PostgreSQL/native/UI/capture/held probes remain unrun']}
(ROOT/'phoenix-verification-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['status','commands_verified','new_TLS_lifecycle_controls','ordinary_suite','cleanup']},indent=2))
