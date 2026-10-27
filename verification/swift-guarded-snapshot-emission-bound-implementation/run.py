#!/usr/bin/env python3
"""Bounded arithmetic-only host tests plus full-source metadata compilation.

Only owned compiler/math-test children are spawned; no product entry executes.
No predecessor harness, process inventory, UI or runtime service is used.
"""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BASE=ROOT/'verification/swift-guarded-snapshot-scope-authority-correction'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
I='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
HELPER='src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def emit(path,x):path.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(argv,cwd,env,timeout=55):
 started=time.monotonic();timed_out=False;cleanup=[]
 child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 try:stdout,stderr=child.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(child.pid,signal.SIGKILL);cleanup.append('killed_only_owned_child_group_after_timeout')
  stdout,stderr=child.communicate(timeout=5)
 return {'argv':[str(x) for x in argv],'cwd':str(cwd),'environment':env,
   'exit_code':child.returncode,'timed_out':timed_out,'timeout_seconds':timeout,
   'elapsed_seconds':time.monotonic()-started,'owned_child_reaped':True,'cleanup_actions':cleanup},stdout,stderr
def stage(case,argv,env,expected=0,expected_codes=None):
 receipt,stdout,stderr=command([str(x) for x in argv],ROOT,env)
 folder=HERE/'commands'/case;folder.mkdir(parents=True,exist_ok=True)
 (folder/'stdout').write_bytes(stdout);(folder/'stderr').write_bytes(stderr)
 codes=[]
 for line in stderr.decode(errors='replace').splitlines():
  try:msg=json.loads(line)
  except json.JSONDecodeError:continue
  code=msg.get('code')
  if isinstance(code,dict) and code.get('code'):codes.append(code['code'])
 receipt.update(expected_exit_code=expected,observed_error_codes=sorted(set(codes)),
   expectation_met=receipt['exit_code']==expected and not receipt['timed_out'],
   stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),
   scope='Pure arithmetic test harness OR metadata compiler only; no VM/encoder/writer execution')
 if expected_codes is not None:
  receipt['expected_error_codes']=expected_codes
  receipt['expectation_met']=receipt['expectation_met'] and sorted(set(codes))==expected_codes
 emit(folder/'receipt.json',receipt)
 print(json.dumps({'case':case,'exit_code':receipt['exit_code'],'expectation_met':receipt['expectation_met']},sort_keys=True),flush=True)
 return receipt,stdout,stderr
def manifest_for(vm):
 rows=[]
 for row in json.loads((HERE/'source-manifest.json').read_text())['members']:
  raw=(vm/row['path']).read_bytes();rows.append({'path':row['path'],'bytes':len(raw),'sha256':sha(raw)})
 return rows
def full_vm(work,negative=False):
 vm=work/'vm'
 for row in json.loads((BASE/'source-manifest.json').read_text())['members']:
  target=vm/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(BASE/'source/vm'/row['path'],target)
 for relative in (I,HELPER):
  target=vm/relative;target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(HERE/'overlay/vm'/relative,target)
 expected=json.loads((HERE/'source-manifest.json').read_text())['members']
 assert manifest_for(vm)==expected
 if negative:
  p=vm/HELPER;s=p.read_text();assert s.count('blocks.checked_add(fixed_and_transfers).ok_or(AError::Arithmetic)')==1
  p.write_text(s.replace('blocks.checked_add(fixed_and_transfers).ok_or(AError::Arithmetic)','Ok("metadata-helper-type-sentinel")'))
 return vm
def pure_host(work,mutant=False):
 host=work/'host';host.mkdir(parents=True)
 for name in ('arithmetic.rs','source-types.rs'):shutil.copyfile(HERE/'host'/name,host/name)
 target=work/'overlay/vm'/HELPER;target.parent.mkdir(parents=True,exist_ok=True)
 raw=(HERE/'overlay/vm'/HELPER).read_text()
 if mutant:
  assert raw.count('299_377u64')==1;raw=raw.replace('299_377u64','299_376u64')
 target.write_text(raw)
 return host/'arithmetic.rs'
def main():
 (HERE/'commands').mkdir(exist_ok=True);owned=HERE/'owned-work';owned.mkdir(exist_ok=True)
 version=subprocess.run([str(RUSTC),'-vV'],capture_output=True,check=True).stdout
 (HERE/'rustc-version.txt').write_bytes(version)
 compiler_sha=sha(RUSTC.read_bytes());version_sha=sha(version)
 all_results=[];layouts={}
 cases=[('host-debug','host',0,False),('host-optimized','host',3,False),
        ('host-negative-coefficient','host',0,True),('metadata-debug','metadata',0,False),
        ('metadata-optimized','metadata',3,False),('metadata-negative-type','metadata',0,True)]
 for name,kind,opt,negative in cases:
  work=owned/name
  assert not work.exists(),('retain prior attempt; choose a new case name',name)
  work.mkdir()
  try:
   env={'PATH':'/usr/bin:/bin','TMPDIR':str(work)}
   if kind=='host':
    source=pure_host(work,negative);artifact=work/'arithmetic-tests'
    argv=[RUSTC,'--crate-name','mixer_emission_arithmetic','--edition=2021','--target','aarch64-apple-darwin',
      '--error-format=json','-C','opt-level='+str(opt),'-C','overflow-checks=yes','--test',source,'-o',artifact]
    receipt,_,_=stage(name+'-compile',argv,env)
    all_results.append({'case':name+'-compile','passed':receipt['expectation_met']})
    if receipt['expectation_met']:
     argv=[artifact,'--test-threads=1','--nocapture']
     if negative:argv += ['--exact','tests::exact_floor_and_valid_minimum']
     receipt,stdout,_=stage(name+'-run',argv,env,101 if negative else 0)
     all_results.append({'case':name+'-run','passed':receipt['expectation_met']})
     if not negative and receipt['expectation_met']:
      marker='MIXER_EMISSION_HELPER_TYPE_LAYOUTS_V1='
      text=stdout.decode();assert marker in text
      layouts[name]=json.loads(text.split(marker,1)[1].splitlines()[0])
   else:
    vm=full_vm(work,negative);artifact=work/'candidate.rmeta'
    env['CARGO_MANIFEST_DIR']=str(vm)
    env.update(MIXER_LOADER_COMPILER_SHA256=compiler_sha,MIXER_LOADER_COMPILER_VERSION_SHA256=version_sha,
      MIXER_LOADER_MANIFEST_SHA256=sha((HERE/'source-manifest.json').read_bytes()))
    argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
      '--error-format=json','-C','opt-level='+str(opt),'-C','overflow-checks=yes','-C','panic=unwind',
      '--crate-type=rlib','--emit=metadata']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
     argv += ['--cfg','feature="'+feature+'"']
    argv += [vm/'src/lib.rs','-o',artifact]
    env['MIXER_LOADER_COMMAND_SHA256']=sha(canonical([str(x) for x in argv]))
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
    emit((HERE/'commands'/name).with_suffix('.preimage.json'),{
      'source_tree_format':'sha256 canonical source roster','source_members':145,
      'source_tree_sha256':sha(canonical(manifest_for(vm))),
      'candidate_source_manifest_sha256':sha((HERE/'source-manifest.json').read_bytes()),
      'negative_mutation':'actual helper return replaced with wrong string type' if negative else None,
      'compiler_sha256':compiler_sha,'compiler_version_sha256':version_sha,
      'no_product_execution':True})
    receipt,_,_=stage(name,argv,env,1 if negative else 0,['E0308'] if negative else [])
    all_results.append({'case':name,'passed':receipt['expectation_met']})
    if artifact.exists():
     emit(HERE/'commands'/name/'artifact.json',{'bytes':artifact.stat().st_size,'sha256':sha(artifact.read_bytes()),'executed':False})
  finally:
   shutil.rmtree(work)
   folder=HERE/'commands'/name;folder.mkdir(parents=True,exist_ok=True)
   emit(folder/'cleanup.json',{'owned_work_path':str(work.relative_to(HERE)),
     'scratch_removed':not work.exists(),'owned_children_waited_before_cleanup':True,
     'global_process_inventory_used':False,'preserved_other_projects':True})
 if layouts:
  assert layouts.get('host-debug')==layouts.get('host-optimized')
 emit(HERE/'helper-type-layouts.json',{'schema':1,'target':'aarch64-apple-darwin','observed':layouts,
    'scope':'Real extracted helper/error/shape type host layouts; not simultaneous source-place closure or target-device qualification'})
 if not any(owned.iterdir()):owned.rmdir()
 summary={'schema':1,'cases':all_results,'all_expectations_met':all(x['passed'] for x in all_results),
   'arithmetic_test_groups_per_positive_mode':9,'product_runtime_entrypoints_executed':False,
   'pure_functions_executed':['checked_snapshot_emission_bound_v1','snapshot_shape_v1','checked_add_v1','checked_mul_v1'],
   'metadata_compilation_only_for_full145_source':True,'WorkAuditPending_preserved':True,
   'original_execution_work_limit':1000000000,'operational_emission_selected':False,
   'all_owned_scratch_removed':not owned.exists(),'forbidden_runtime_UI_process_inventory_used':False}
 emit(HERE/'run-results.json',summary)
 assert summary['all_expectations_met'],summary
 print(json.dumps(summary,sort_keys=True),flush=True)
if __name__=='__main__':main()
