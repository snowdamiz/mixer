#!/usr/bin/env python3
"""Data-only independent composition and prospective-application check. Never applies patch."""
from pathlib import Path
import collections,difflib,hashlib,json,os,subprocess,sys,time
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;P=D/'input';REPO=D.parents[1]
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def read(p):
 assert p.is_file() and not p.is_symlink(),p
 return p.read_bytes()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
commands=[]
def run(name,args,input=None):
 start=time.monotonic();result=subprocess.run(args,cwd=REPO,input=input,capture_output=True,timeout=60)
 (D/(name+'.stdout')).write_bytes(result.stdout);(D/(name+'.stderr')).write_bytes(result.stderr)
 commands.append({'name':name,'argv':args,'input':None if input is None else identity(input),'exit':result.returncode,'stdout':identity(result.stdout),'stderr':identity(result.stderr),'elapsed':time.monotonic()-start,'reaped':True});save(D/'commands.json',commands);assert result.returncode==0,(name,result.stderr)
 return result.stdout
receipt=json.loads(read(P/'receipt.json'));composition=json.loads(read(P/'composition.json'));rows=composition['targets'];assert len(rows)==346 and len({r['path'] for r in rows})==346
indices={}
for folder,pinned in receipt['inputs'].items():
 root=REPO/folder;raw=read(root/'seal.json');assert identity(raw)['sha256']==pinned
 seal=json.loads(raw)
 if 'members' in seal:members=seal['members']
 else:
  manifest=read(root/'manifest.json');assert identity(manifest)==seal['manifest'];members=json.loads(manifest)['members']
 indices[folder]={r['path']:{k:r[k] for k in ('bytes','sha256')} for r in members};assert len(indices[folder])==len(members)
def selected(folder,path):
 data=read(REPO/folder/path);assert identity(data)==indices[folder][path];return data
cli='verification/android-editor-source-pair5-cli-integration';host='verification/android-editor-source-pair5-host-integration';probe='verification/android-editor-membership-compiled-boundary-qualification/passive-return-probe-v3';pair='verification/android-editor-source-pair5-rebinding'
expected={}
for r in json.loads(selected(cli,'source-manifest.json'))['members']:
 target=r['path'].removeprefix('source/');assert target not in expected;expected[target]=(cli,r['path'],selected(cli,r['path']))
assert len(expected)==162
host_targets=json.loads(selected(host,'test-targets.json'))['targets'];assert len(host_targets)==183
for r in host_targets:
 assert r['canonical_path'] not in expected;expected[r['canonical_path']]=(host,r['candidate_path'],selected(host,r['candidate_path']))
before_probes=dict(expected);B='native/android/tests/NativeOwnerV2ConcreteHostLeaves/';A='native/android/tests/NativeOwnerV2HostLeaves/'
for r in json.loads(selected(probe,'derivative-source-roster.json'))['records']:
 target=B+r['path'];expected[target]=(probe,'inputs/host-leaves/'+r['path'],selected(probe,'inputs/host-leaves/'+r['path']))
assert len(expected)==346
actual_files={f.relative_to(P/'source').as_posix() for f in (P/'source').rglob('*') if f.is_file()};assert actual_files==set(expected)
for row in rows:
 name=row['path'];folder,origin,data=expected[name];assert read(P/'source'/name)==data
 assert row['candidate']==identity(data) and row['origin']==folder+'/'+origin and row['packet_seal_sha256']==receipt['inputs'][folder]
 assert bool((P/'source'/name).stat().st_mode&0o111)==(row['mode']=='100755')
profile=json.loads(selected(pair,'profile5.json'));assert read(P/'selected-profile5.json')==selected(pair,'profile5.json');counts={}
for group in ('sdk','adapter'):
 mapping=profile[group+'_files'];assert len(mapping)==(22 if group=='sdk' else 24);counts[group]=len(mapping)
 for name,wanted in mapping.items():
  target=('sdk/' if group=='sdk' else 'native/android/engine/' if name.startswith('Sources/') else 'native/android/')+name
  assert identity(read(P/'source'/target))==wanted and read(P/'source'/target)==selected(pair,'sources/'+group+'/'+name)
extras=composition['canonical_only_extras'];assert len(extras)==3
for name in extras:assert read(P/'source/native/android'/name.removeprefix('canonical-only-inputs/'))==selected(pair,name)
bleaves={r.removeprefix('inputs/host-leaves/'):v for r,v in indices[probe].items() if r.startswith('inputs/host-leaves/') and r.endswith('.java')};assert len(bleaves)==87
for name,wanted in bleaves.items():assert identity(read(P/'source'/B/name))==wanted
aleaves=[r for r in rows if r['path'].startswith(A)];assert len(aleaves)==86
for row in aleaves:
 assert expected[row['path']]==before_probes[row['path']] and expected[row['path']][0]==host
Achanging=[r['path'] for r in aleaves if r['state']!='unchanged'];assert Achanging==[A+'dev/mixer/android/NativeRenderer.java']
assert receipt['mechanical_A_host_leaves_changed_from_canonical']==Achanging and receipt['mechanical_A_host_leaves_changed_by_probe_overlay'] is False
base=composition['base_revision'];tree=run('base-tree',['git','ls-tree','-z',base,'--',*sorted(expected)]);tracked={}
for entry in tree.split(b'\0'):
 if entry:
  meta,name=entry.split(b'\t');mode,kind,oid=meta.decode().split();assert kind=='blob';tracked[name.decode()]=(mode,oid)
oids=sorted({v[1] for v in tracked.values()});data=run('base-blobs',['git','cat-file','--batch'],('\n'.join(oids)+'\n').encode());blobs={};pos=0
for oid in oids:
 end=data.index(b'\n',pos);got,kind,size=data[pos:end].decode().split();assert got==oid and kind=='blob';start=end+1;blobs[oid]=data[start:start+int(size)];pos=start+int(size);assert data[pos:pos+1]==b'\n';pos+=1
assert pos==len(data);patch=[];states=collections.Counter();source_before={}
for row in rows:
 name=row['path'];candidate=read(P/'source'/name);old=None if name not in tracked else blobs[tracked[name][1]];state='new' if old is None else 'unchanged' if old==candidate else 'changed';states[state]+=1;assert row['state']==state and row['base']==(None if old is None else identity(old));assert row['mode']==('100644' if old is None else tracked[name][0])
 live=REPO/name
 if old is None:assert not live.exists() and not live.is_symlink()
 else:assert read(live)==old
 source_before[name]=None if old is None else identity(read(live))
 if state=='unchanged':continue
 patch.append('diff --git a/'+name+' b/'+name+'\n')
 if state=='new':patch.append('new file mode '+row['mode']+'\n')
 for line in difflib.unified_diff((old or b'').decode().splitlines(True),candidate.decode().splitlines(True),fromfile='/dev/null' if old is None else 'a/'+name,tofile='b/'+name):patch.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
assert dict(states)==receipt['target_states']=={'new':27,'changed':23,'unchanged':296}
reconstructed=''.join(patch).encode();assert reconstructed==read(P/'prospective.patch') and identity(reconstructed)==receipt['prospective_patch']
run('prospective-application-check',['git','apply','--check',str(P/'prospective.patch')])
for name,old in source_before.items():
 live=REPO/name
 if old is None:assert not live.exists() and not live.is_symlink()
 else:assert identity(read(live))==old
result={'scope':'Independent byte composition/base custody/prospective patch check only; no product or test execution and no patch application',
 'selected_source_targets':len(rows),'states':dict(states),'source_pair':counts,'canonical_only_extras':extras,'exact_B_v3_leaves':len(bleaves),'exact_A_accepted_leaves':len(aleaves),'A_changes_from_canonical':Achanging,'A_probe_edits':False,
 'all_selected_origins_and_seals_recomputed':True,'all_current_source_targets_match_recorded_base':True,'reconstructed_patch_matches':True,'prospective_apply_check':'passed','canonical_source_or_index_writes':False,
 'accepted_original_host_runner_copied_exactly':read(P/'source/native/android/tests/run-private-owner-host.py')==selected(host,'candidate/native/android/tests/run-private-owner-host.py'),
 'full_matrix_execution_closure_integration_native_OTA_GA_accepted':False,'native_UI_capture_or_process_inventory':False,'python':sys.version,'reviewer_script':identity(read(Path(__file__)))}
save(D/'review.json',result);print(json.dumps({'targets':len(rows),'states':dict(states),'source_pair':counts,'B_leaves':len(bleaves),'A_leaves':len(aleaves),'patch_check':'passed','integration_accepted':False}))
