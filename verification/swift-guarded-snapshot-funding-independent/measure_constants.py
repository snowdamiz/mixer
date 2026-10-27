#!/usr/bin/env python3
"""Compile-only diagnostic seam reveals actual const sizes; never links/runs Mixer."""
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CANDIDATE=ROOT/'verification/swift-guarded-snapshot-funding-implementation'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SCRATCH=OUT/'owned-work'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def summarize(receipts):
 result={'schema':1,'scope':'Actual const compiler-evaluated values on aarch64-apple-darwin Rust1.99; no runtime qualification','contexts':{}}
 for mode,r in zip(['production','unit'],receipts):
  v=r['actual_constants']
  result['contexts'][mode]={'F0':v['F0'],'common':v['COMMON'],'selected_without_H':v['F0']+78240+941467,'selected':v['SELECTED'],'admitted':v['SELECTED']+430175}
 result['cfg_context_F0_equality_required']=False
 result['physical_stack_or_RSS_or_operational_acceptance']=False
 dump(OUT/'actual-constants.json',result)
 print(json.dumps(result['contexts']))
if '--summarize-existing' in sys.argv:
 summarize([json.loads((OUT/f'compiler-{mode}/receipt.json').read_text()) for mode in ['production','unit']])
 sys.exit(0)
assert not SCRATCH.exists(), 'Never replace an unowned scratch directory'
SCRATCH.mkdir()
source=SCRATCH/'vm'
shutil.copytree(CANDIDATE/'source/vm',source)
manifest=json.loads((CANDIDATE/'source-manifest.json').read_text())
assert manifest['source_tree_sha256']=='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
for m in manifest['members']:
 p=source/m['path'];assert sha(p)==m['sha256'] and p.stat().st_size==m['bytes']
control=source/'src/experimental_swift_reactor/control.rs'
original_sha=sha(control)
seam='''
// Independent compile-only diagnostic seam; intentionally mismatched arrays.
const INDEPENDENT_REVEAL_F0: [(); 0] = [(); FOUNDATION_CONSTRUCTION_BYTES.unwrap()];
const INDEPENDENT_REVEAL_COMMON: [(); 0] = [(); COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap()];
const INDEPENDENT_REVEAL_SELECTED: [(); 0] = [(); SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1.unwrap()];
'''
control.write_text(control.read_text()+seam)
dump(OUT/'compiler-seam.json',{'schema':1,'source_tree_sha256':manifest['source_tree_sha256'],'members_verified':len(manifest['members']),'path':'src/experimental_swift_reactor/control.rs','original_sha256':original_sha,'seam':seam,'seamed_sha256':sha(control),'purpose':'force E0308 actual constant values without metadata success/codegen/runtime'})
env=dict(os.environ,RUSTC_BOOTSTRAP='1')
version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,text=True,timeout=10,env=env)
assert version.returncode==0
(OUT/'compiler-version.stdout').write_text(version.stdout)
(OUT/'compiler-version.stderr').write_text(version.stderr)
def run(mode):
 target=OUT/('compiler-'+mode);target.mkdir(exist_ok=False)
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind','-Zmir-opt-level=0']
 for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
  argv+=['--cfg',f'feature="{feature}"']
 argv+=['--test'] if mode=='unit' else ['--crate-type','rlib']
 argv += [str(source/'src/lib.rs'),'--emit=metadata='+str(SCRATCH/(mode+'.rmeta'))]
 started=time.monotonic();p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True)
 try:
  stdout,stderr=p.communicate(timeout=55);timed_out=False
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate();timed_out=True
 (target/'stdout').write_text(stdout);(target/'stderr').write_text(stderr)
 # Each deliberate E0308 diagnostic carries its originating const line then
 # the actual compiler-evaluated array size. Preserve raw stderr as authority.
 values={}
 errors=stderr.split('error[E0308]')[1:]
 for error in errors:
  name=re.search(r'INDEPENDENT_REVEAL_(F0|COMMON|SELECTED)',error)
  size=re.search(r'found one with a size of (\d+)',error)
  if name and size:values[name.group(1)]=int(size.group(1))
 assert p.returncode!=0 and not timed_out
 assert stderr.count('error[E0308]')==3 and set(values)=={'F0','COMMON','SELECTED'},stderr
 assert values['COMMON']==values['F0']+78240
 assert values['SELECTED']==values['COMMON']+941467+(81327 if mode=='unit' else 0)
 absent=False
 try:os.killpg(p.pid,0)
 except ProcessLookupError:absent=True
 assert absent
 receipt={'schema':1,'argv':argv,'source_tree_sha256':manifest['source_tree_sha256'],'seamed_control_sha256':sha(control),'compiler_sha256':sha(RUSTC),'compiler_version':version.stdout,'python_version':platform.python_version(),'elapsed_seconds':time.monotonic()-started,'exit_code':p.returncode,'expected_E0308_count':3,'actual_constants':values,'child_reaped':True,'owned_group_absent':absent,'timed_out':timed_out,'scope':'Compile-only diagnostic seam; no Mixer executable or VM/writer/native runtime'}
 dump(target/'receipt.json',receipt)
 return receipt
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  receipts=list(pool.map(run,['production','unit']))
finally:
 shutil.rmtree(SCRATCH)
 dump(OUT/'compiler-cleanup.json',{'schema':1,'removed_owned_scratch':str(SCRATCH),'scratch_absent':not SCRATCH.exists(),'no_global_process_inventory':True,'native_or_capture_or_VM_or_writer_started':False})
summarize(receipts)
