#!/usr/bin/env python3
"""Compile the exact signal producer and its six tests against retained dependencies."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);a=parser.parse_args()
assert re.fullmatch('[a-z0-9-]{1,64}',a.name)
OUT=HERE/a.name;OUT.mkdir(exist_ok=False)
WORK=ROOT/'capability-activation/.build'/('signals-'+a.name);WORK.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=['capability-activation/Sources/MixerCapabilityActivation/CapabilityAttemptSignals.swift','capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptSignalsTests.swift']
rows={}
for name in inputs:
 p=ROOT/name;q=WORK/p.name;q.write_bytes(p.read_bytes());q.chmod(0o444);rows[name]=sha(q)
bridge_path=ROOT/'experimental-capability-runtime/verification/2026-10-23-enable-deadline-candidate-1/receipt.json'
store_path=ROOT/'verification/capability-durable-store/2026-10-23-candidate-2/receipt.json'
bridge=json.loads(bridge_path.read_text());store=json.loads(store_path.read_text())
for mode in ['debug','release','tsan']:
 assert any(c['name']=='bridge-'+mode and c['exitCode']==0 and c['passedTests']==[35] for c in bridge['commands'])
native=Path(bridge['stageRoot'])/'host'
for name,digest in bridge['nativeArtifacts']['host'].items():assert sha(Path(bridge['stageRoot'])/name)==digest
r={'status':'running','inputs':rows,'source_export':str(WORK),'driver_sha256':sha(Path(__file__)),
   'bridge_receipt_sha256':sha(bridge_path),'store_receipt_sha256':sha(store_path),'commands':[],'products':{},'binaries':{},
   'scope':'Six exact producer test functions in standalone mode, without a package rebuild or consumer/coordinator claim.',
   'limitations':['Test-only typed failure values exercise the latch, not native failure classification.','TSan covers these Swift tests and available instrumented dependencies; not Rust/system internals.','The AsyncStream consumer and signed transition composition remain unimplemented/unqualified.','Base bridge full runtime35 tests passed; its unrelated standalone fixture failure and repaired cross consumer are recorded separately.']}
def save():(OUT/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
def run(name,args):
 began=time.monotonic();p=subprocess.run(args,cwd=ROOT,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
 path=OUT/(name+'.log');path.write_bytes(p.stdout)
 r['commands'].append({'name':name,'command':args,'exit_code':p.returncode,'seconds':time.monotonic()-began,'log':path.name,'log_sha256':sha(path)})
 save();print(name,p.returncode,flush=True);return p.returncode
save();run('swift-version',['swiftc','--version'])
for mode in ['debug','release','tsan']:
 label='Release' if mode=='release' else 'Debug'
 bp=Path(bridge['frozenSourceExport']).parent/mode/'out/Products'/label
 if mode=='tsan':
  sp=Path(store['export']).parent/'host/out/Products/Debug'
  maps=Path(store['export']).parent/'host/out/Intermediates.noindex/GeneratedModuleMaps'
 else:
  retained=store['retained_products'][mode];base=Path(retained['directory'])
  for name,digest in retained['files'].items():assert sha(base/name)==digest
  sp=base/'products';maps=base/'modulemaps'
 paths={str(p):sha(p) for folder in [bp,sp,maps] for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink()}
 r['products'][mode]=paths
 flags=['-swift-version','6','-warnings-as-errors','-parse-as-library','-module-name','MixerCapabilityActivation','-D','SIGNALS_STANDALONE','-I'+str(bp),'-I'+str(sp),'-L'+str(bp),'-lMixerExperimentalCapabilityRuntime','-L'+str(sp),'-lMixerCapabilityActivation','-L'+str(native/'lib'),'-lmixer_vm_capability_experimental','-Xcc','-I'+str(native/'include')]
 for module in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:flags+=['-Xcc','-fmodule-map-file='+str(maps/(module+'.modulemap'))]
 if mode=='release':flags+=['-O']
 if mode=='tsan':flags+=['-sanitize=thread']
 binary=WORK/(mode+'-signals')
 if run(mode+'-compile',['swiftc']+flags+[str(WORK/Path(n).name) for n in inputs]+['-o',str(binary)])==0:
  r['binaries'][mode]={'path':str(binary),'sha256':sha(binary)}
  run(mode+'-execute',[str(binary)])
 assert all(sha(Path(n))==d for n,d in paths.items())
assert all(sha(ROOT/n)==d and sha(WORK/Path(n).name)==d for n,d in rows.items())
r['status']='six cases passed in debug release and Swift TSan' if len(r['commands'])==7 and all(c['exit_code']==0 for c in r['commands']) and all(b'PASS 6 signal cases' in (OUT/(m+'-execute.log')).read_bytes() for m in ['debug','release','tsan']) else 'failed check preserved'
save();raise SystemExit(0 if r['status'].startswith('six cases') else 1)
