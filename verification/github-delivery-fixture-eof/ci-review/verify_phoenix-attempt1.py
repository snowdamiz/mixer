#!/usr/bin/env python3
"""Pure offline evidence validation of the failed ordinary Phoenix run."""
import sys
def audit(event,args):
 if event.startswith(('socket.','subprocess.')) or event in {'os.system','os.fork','os.posix_spawn','pty.spawn'}:raise RuntimeError('offline audit denied '+event)
sys.addaudithook(audit)
import datetime,hashlib,io,json,platform,re,signal,tarfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent;P=ROOT/'phoenix/_temp/phoenix-foundation'
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('40 second offline bound')));signal.alarm(40)
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def readjson(p):return json.loads(p.read_bytes())
run=readjson(ROOT/'40775131269-meta-metadata.json');job,=readjson(ROOT/'40775131269-jobs-metadata.json')['jobs'];art,=readjson(ROOT/'40775131269-artifacts-metadata.json')['artifacts']
sha='86a96a4ba6c14e45be41999873f00d5788bbc649';tree='0e4df024715e23aefe3aa7635c6829df5d4e85fa'
assert run['id']==40775131269 and run['head_sha']==sha and run['head_commit']['tree_id']==tree and run['run_attempt']==1 and run['event']=='push' and run['conclusion']=='failure'
assert job['id']==123122340168 and job['run_id']==run['id'] and job['conclusion']=='failure'
assert art['id']==12854846000 and art['workflow_run']['head_sha']==sha and art['workflow_run']['id']==run['id']
raw=(ROOT/'phoenix-artifact.zip').read_bytes();assert len(raw)==825352 and art['digest']=='sha256:'+digest(raw)=='sha256:e837cc5fdd331d18a518b58325f1d6f0f933ee8d3d11490aad033f02fb21781c'
r=readjson(P/'receipt.json');assert r['status']=='failed' and r['source_tree_sha256']==digest(canonical(r['inputs']))
assert [x['label'] for x in r['commands']]==['revision','elixir-version','postgres-version','format']
assert [x['exit_code'] for x in r['commands']]==[0,0,0,1]
for x in r['commands']:assert digest((P/x['log']).read_bytes())==x['sha256']
assert r['commands'][-1]['argv']==['mix','format','--check-formatted']
assert (P/'revision.log').read_text().strip()==sha
assert r['cleanup']=={'postgres_stopped':True,'scratch_removed':True}
archive=(P/'source.tar.gz').read_bytes();assert digest(archive)==r['source_archive_sha256']
sources={};folded=set();expanded=0
with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
 for m in t.getmembers():
  p=m.name;assert p and not p.startswith('/') and '\\' not in p and ':' not in p and '\x00' not in p and str(PurePosixPath(p))==p and all(x not in ('','.','..') for x in p.split('/'))
  assert m.isfile() and not m.linkname and not m.pax_headers and p.casefold() not in folded and 0<=m.size<=256*1024*1024
  expanded+=m.size;assert expanded<=256*1024*1024
  b=t.extractfile(m).read();assert len(b)==m.size;sources[p]=b;folded.add(p.casefold())
assert {p:digest(b) for p,b in sources.items()}==r['inputs']
control='hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs';fixture='hosted/test/support/identity_tls_fixture.ex'
assert digest(sources[control])=='417704f8e805196f9546a508a770d23a55d40ce9d6214be5225f131c4bd2c7c6'
assert digest(sources[fixture])=='d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55'
formatlog=(P/'format.log').read_text();assert 'mix format failed due to --check-formatted.' in formatlog
assert '/home/runner/work/mixer/mixer/'+control in formatlog and ' 83     -|    assert {:ok, socket} = :gen_tcp.connect' in formatlog
assert '     84 +|    assert {:ok, socket} =' in formatlog and '     85 +|             :gen_tcp.connect' in formatlog
testnames=re.findall(r'^  test "([^"]+)"',sources[control].decode(),re.M);assert len(testnames)==4
assert not (P/'compile.log').exists() and not (P/'tests.log').exists()
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'failed-at-format-before-compile-and-four-control-tests','source_revision':sha,'source_tree':tree,'run_id':run['id'],'job_id':job['id'],'run_attempt':1,'artifact_id':art['id'],'zip':{'bytes':len(raw),'sha256':digest(raw)},'source_archive':{'sha256':digest(archive),'files':len(sources),'expanded_bytes':expanded,'all_input_hashes_joined':True},'commands_verified':r['commands'],'causal_error':{'command':['mix','format','--check-formatted'],'exit':1,'file':control,'source_line':83,'message':'long assert and gen_tcp.connect require formatter line wrapping; one blank line precedes assertion','raw_diff':'phoenix/_temp/phoenix-foundation/format.log'},'new_TLS_lifecycle_controls':{'source_names':testnames,'source_sha256':digest(sources[control]),'runtime_execution_observed':False,'passed':None},'ordinary_suite':{'expected_total_from_prior_plus_four':701,'expected_network_skips':2,'actual_total':None,'actual_skips':None,'compile_executed':False,'tests_executed':False},'cleanup':r['cleanup'],'local_command':['/usr/bin/python3','-B',str(ROOT/'verify_phoenix.py')],'local_python':platform.python_version(),'script_sha256':digest(Path(__file__).read_bytes()),'offline_audit_denies_network_and_children':True,'local_product_or_runtime_execution':False,'alarm_seconds':40,'limits':['failed Phoenix run is not development-slice acceptance','no source edits, retry, native, provider, customer or GA acceptance']}
(ROOT/'phoenix-verification-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':result['status'],'causal_error':result['causal_error'],'four_controls_unrun':testnames,'cleanup':r['cleanup']},indent=2))
