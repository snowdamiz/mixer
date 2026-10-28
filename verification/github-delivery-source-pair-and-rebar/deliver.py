"""One-shot root-authorized source-pair/Rebar delivery; do not replay historical helpers."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import signal
import subprocess
import time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
BASE='56ff14c925168284761c5aca4f0bd4129cf3c995'
BASE_TREE='75989099938ed5256c4144cbc9e62979ee323183'
DEADLINE=time.monotonic()+300
PROTECTED={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
METADATA=['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']
CANONICAL={
 'hosted/scripts/test-identity-network.py':'8f499146601a63fada79026e4dd3eabed867edb4430360e4866918dcdd46f011',
 'hosted/scripts/test_identity_network_collector.py':'8a43d2410a299ce59edba11d06d4e94966d27150485b3baf063ef194ce5f41b7',
 'docs/hosted-identity-production-network-ci-contract.md':'1ba2d65716838e03f937bd07f77ff5f8a5f46dbfa229e0ab328866f4702ae90a',
 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift':'f6a0cf11ecc8ea2773d8dbf90de44500eb4c2f28aca841df433e700994bfb152',
 'cli/Sources/MixerBuild/Resources/android-build.py':'0f13545e610e527fe491314194fde1aa91698e9b458b638df6094f0e789fe4f2',
 'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift':'b864c3e3186e62aa23c6cd87e74678b8c2a3283f5ca8d9d90a04e1c2a508b726',
 'cli/build-tests/test_android_sdk_compatibility.py':'d2407422f0901b3e1670c79fbff33f57a7b330d03a1a9eba0856009372e07d75'}
LANES=['github-delivery-binary-export-and-ui','identity-network-rebar-output-correction','identity-network-rebar-output-independent','android-sdk-axis-pair-correction','public-ui-theme-contract']
OBSERVATIONS=['identity-network-rebar-selection.json','fieldlog-public-baseline-result.json','fieldlog-public-fields-delivery-observation.json']
PREEXECUTION=['prepare-checkpoint.py','checkpoint.json','update-current-observations.py','current-observations-addendum.json','deliver.py']
COMMANDS=[]

def read(p):return json.loads(p.read_bytes())
def row(p):
 assert p.is_file() and not p.is_symlink(),p
 b=p.read_bytes();return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,v):
 with (OUT/name).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def command(name,argv,cap=30):
 remaining=DEADLINE-time.monotonic();assert remaining>8,'Delivery budget exhausted before '+name
 start=time.monotonic();timed=False
 with (OUT/(name+'.stdout')).open('xb') as stdout,(OUT/(name+'.stderr')).open('xb') as stderr:
  child=subprocess.Popen(argv,cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
  try:child.wait(timeout=min(cap,remaining-7))
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 record={'argv':argv,'exit':child.returncode,'timed_out':timed,'elapsed_seconds':time.monotonic()-start,'owned_pid':child.pid,'owned_pgid':child.pid,'direct_child_reaped':True,'owned_group_absent':absent,'stdout':row(OUT/(name+'.stdout')),'stderr':row(OUT/(name+'.stderr'))}
 save(name+'.command.json',record);COMMANDS.append({'name':name,'exit':child.returncode,'direct_child_reaped':True,'owned_group_absent':absent})
 assert not timed and absent and child.returncode==0,name
 return (OUT/(name+'.stdout')).read_bytes()

assert not (OUT/'manifest.json').exists(),'One-shot; do not replay'
assert command('branch',['git','branch','--show-current']).decode().strip()=='main'
assert command('head',['git','rev-parse','HEAD']).decode().strip()==BASE
assert command('base-tree',['git','rev-parse','HEAD^{tree}']).decode().strip()==BASE_TREE
assert command('remote-before',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==BASE
assert not command('index-before',['git','diff','--cached','--name-only','-z'])
command('git-version',['git','--version'])
for p,digest in {**CANONICAL,**PROTECTED}.items():assert row(ROOT/p)['sha256']==digest,p
checkpoint=read(OUT/'checkpoint.json')
assert checkpoint['proof_member_files_rehashed']==625
assert row(OUT/'prepare-checkpoint.py')['sha256']=='e97548f5312ce127cbceb31ec7747e090907152d78e1310c5489b21fc2f2692b'
network=read(ROOT/'verification/console-session-and-checkout-root-review/identity-network-rebar-selection.json')
assert network['canonical_controls_passed']==126 and network['independent_pure_methods_passed']==6
assert network['remote_execution_selected'] and not network['corrected_actual_CI_product_or_GA_accepted']
for expected in network['canonical_sources']+[network['independent_decision']]:assert row(ROOT/expected['path'])==expected
cli=read(ROOT/'verification/android-sdk-axis-pair-correction/source-review.json')
assert cli['profile_id']=='mixer.android-source-pair.5' and cli['in_process_controls_passed']==8
assert cli['Swift_CLI_and_complete_Python_execution_pending'] and not cli['held_Android_candidate_v5_changed_or_retried']
for p,e in cli['canonical_sources'].items():assert row(ROOT/p)=={'path':p,**e}
addendum=read(OUT/'current-observations-addendum.json')
for expected in addendum['observations'].values():assert row(ROOT/expected['path'])==expected
for expected in addendum['metadata']:assert row(ROOT/expected['path'])==expected
w=read(ROOT/'work-graph.json');g=read(ROOT/'gates/ga.json')
assert len(w['packages'])==18 and len(g['gates'])==38
assert [sum(x['status']==s for x in g['gates']) for s in ['running','planned','verified']]==[8,30,0]
for wi,gi,key in [(13,21,'identityProductionNetworkCI'),(7,1,'empiricalCacheDeadlineCampaign')]:assert w['packages'][wi][key]==g['gates'][gi][key]
selected={ROOT/p for p in list(CANONICAL)+METADATA}
for name in LANES:
 lane=ROOT/'verification'/name;assert lane.is_dir()
 selected.update(p for p in lane.rglob('*') if p.is_file() and not p.name.startswith(('ci-runs-3.','github-rate-limit.')))
selected.update(ROOT/'verification/console-session-and-checkout-root-review'/n for n in OBSERVATIONS)
selected.update(OUT/n for n in PREEXECUTION)
assert not set(PROTECTED)&{str(p.relative_to(ROOT)) for p in selected}
assert all('swift-execution-architecture' not in str(p) and 'fieldlog-public-sdk-next-flow' not in str(p) and '/.codex' not in str(p) and '/.wrangler' not in str(p) for p in selected)
assert len(selected)<=2500 and sum(p.stat().st_size for p in selected)<=96*1024*1024
assert max(p.stat().st_size for p in selected)<100*1024*1024
members=[row(p) for p in sorted(selected)]
save('manifest.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':['python3','-B',str(Path(__file__).relative_to(ROOT))],'python':platform.python_version(),'base':BASE,'base_tree':BASE_TREE,'members':members,'canonical_paths':list(CANONICAL),'scope':'Exact Rebar generated-output correction, source-pair5 row refresh and reviewed prior CI outcomes; fresh remote validation pending; sanitized FieldLog status only','prior_checkpoint_not_replayed':True,'native_compiler_runtime_custody_inventory_or_capture_actions':False,'architecture_directories_and_FieldLog_source_raw_evidence_excluded':True,'protected_dirty_paths_excluded':list(PROTECTED),'GA_accepted':False})
paths=[r['path'] for r in members]+[str((OUT/'manifest.json').relative_to(ROOT))]
with (OUT/'paths.nul').open('xb') as f:f.write(b''.join(p.encode()+b'\0' for p in paths))
command('stage',['git','add','--force','--pathspec-from-file='+str(OUT/'paths.nul'),'--pathspec-file-nul'])
for expected in members:assert row(ROOT/expected['path'])==expected
index=set(filter(None,command('index-selected',['git','diff','--cached','--name-only','-z']).decode().split('\0')))
assert index<=set(paths) and set(CANONICAL)<=index
command('authored-check',['git','diff','--cached','--check','--',*list(CANONICAL),*METADATA,*[str((OUT/n).relative_to(ROOT)) for n in PREEXECUTION],*[str((ROOT/'verification/console-session-and-checkout-root-review'/n).relative_to(ROOT)) for n in OBSERVATIONS]])
raw=command('staged-objects',['git','diff','--cached','--raw','--no-abbrev','-z']).split(b'\0')
for offset in range(0,len(raw)-1,2):
 header=raw[offset].decode().split();p=raw[offset+1].decode()
 assert len(header)==5 and header[-1] in ('A','M') and header[1] in ('100644','100755')
 b=(ROOT/p).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==header[3]
command('commit',['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-m','Classify generated Rebar output and refresh Android SDK source pair'])
head=command('committed-head',['git','rev-parse','HEAD']).decode().strip()
tree=command('committed-tree',['git','rev-parse','HEAD^{tree}']).decode().strip()
assert command('committed-parent',['git','rev-parse','HEAD^']).decode().strip()==BASE
committed=set(filter(None,command('committed-paths',['git','diff-tree','--no-commit-id','--name-only','-z','-r','HEAD']).decode().split('\0')))
assert committed==index
assert not command('index-after',['git','diff','--cached','--name-only','-z'])
for p,digest in PROTECTED.items():assert row(ROOT/p)['sha256']==digest,p
command('push',['git','-c','core.hooksPath=/dev/null','-c','pack.window=0','push','origin','HEAD:refs/heads/main'],cap=120)
assert command('remote-after',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==head
for p,digest in PROTECTED.items():assert row(ROOT/p)['sha256']==digest,p
save('receipt.json',{'schema':1,'at':datetime.now(timezone.utc).isoformat(),'commit':head,'tree':tree,'parent':BASE,'committed_paths':len(index),'manifest':row(OUT/'manifest.json'),'canonical_paths':list(CANONICAL),'pushed':True,'force':False,'CI_pending':True,'selected_files':len(members),'selected_bytes':sum(r['bytes'] for r in members),'all_new_commands':COMMANDS,'all_new_commands_reaped_and_groups_absent':all(c['direct_child_reaped'] and c['owned_group_absent'] for c in COMMANDS),'architecture_and_FieldLog_source_raw_excluded':True,'protected_work_unchanged':PROTECTED,'wrangler_untouched':True,'GA_accepted':False})
print(json.dumps({'commit':head,'tree':tree,'committed_paths':len(index),'selected_files':len(members),'pushed':True,'new_commands':len(COMMANDS),'all_cleanup_verified':True}))
