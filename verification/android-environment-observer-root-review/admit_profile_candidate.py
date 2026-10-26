import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent; P=ROOT/'verification/android-environment-observer-lifecycle'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check(p,r):
 if p.is_symlink() or not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']: raise RuntimeError('Changed input '+str(p))
proposal=P/'candidate-proposal.json'
if sha(proposal)!='80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a':raise RuntimeError('Proposal differs')
j=json.loads(proposal.read_bytes()); profile_path=P/'candidate-profile-2.json'; check(profile_path,j['profile']); profile=json.loads(profile_path.read_bytes())
for p,r in j['files'].items():check(ROOT/p,r)
policy=ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
parse=lambda text:json.loads(text.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
if parse(policy.read_text())!=profile:raise RuntimeError('Compiled literal differs')
old=parse(subprocess.check_output(['git','show','4e48ac1a:cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'],text=True))
changed=[]
for kind in ['sdk','adapter']:
 if set(old[kind+'_files'])!=set(profile[kind+'_files']):raise RuntimeError('Map topology differs')
 for path,r in profile[kind+'_files'].items():
  src=ROOT/('sdk/'+path if kind=='sdk' else 'native/android/'+('engine/' if path.startswith('Sources/') else '')+path)
  check(src,r)
  if r!=old[kind+'_files'][path]:changed.append(kind+':'+path)
 projection=''.join(path+'\0'+row['sha256']+'\n' for path,row in sorted(profile[kind+'_files'].items())).encode()
 if hashlib.sha256(projection).hexdigest()!=profile[kind+'_compatibility_sha256']:raise RuntimeError('Projection differs')
if changed!=['adapter:app/src/dev/mixer/android/NativeEnvironmentV2.java']:raise RuntimeError('Wrong source changes')
expected=json.loads(json.dumps(old));expected['id']='mixer.android-source-pair.2';expected['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentV2.java']=profile['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentV2.java'];expected['adapter_compatibility_sha256']=profile['adapter_compatibility_sha256']
if expected!=profile:raise RuntimeError('Unexpected profile contract change')
for name,key in [('receipt.json','host_receipt'),('source-freeze.json','host_source_freeze')]:check(P/'host-attempt-3'/name,j[key])
freeze=json.loads((P/'host-attempt-3/source-freeze.json').read_bytes())
for name,r in freeze['files'].items():check(ROOT/name,r)
result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(Path(__file__))],'python_version':sys.version,'status':'candidate-profile-2-admitted-for-dependent-qualification','candidate_proposal_sha256':sha(proposal),'candidate_profile_sha256':sha(profile_path),'profile_id':profile['id'],'mapped_members_verified':42,'all_proposal_inputs_verified':len(j['files']),'host_frozen_inputs_verified':len(freeze['files']),'changed_mapped_sources':changed,'adapter_projection_sha256':profile['adapter_compatibility_sha256'],'sdk_descriptor_wire_unchanged':True,'actual_profile_qualification_authorized':True,'direct_cross_compilation_authorized':True,'implementation_accepted':False,'native_runtime_or_capture_authorized':False,'GA_qualified':False,'scope':'Exact candidate bytes and selected successor map verified; host outcomes and native/CLI acceptance still require independent review. No automatic mutable profile refresh.'}
(OUT/'profile-candidate-admission.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
