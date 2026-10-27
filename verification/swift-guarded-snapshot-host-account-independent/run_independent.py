#!/usr/bin/env python3
"""Bounded private-account review; no native, product runtime or broad runner."""
import datetime, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
PRODUCER=ROOT/'verification/swift-guarded-snapshot-host-account-entry'
FUNDING=ROOT/'verification/swift-guarded-snapshot-funding-implementation'
BOOT=ROOT/'verification/swift-guarded-snapshot-bootstrap-host-boundary'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
SCRATCH=HERE/'owned-work'
COMMANDS=HERE/'commands'
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def write(name,value):
 p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def members(folder):
 return [dict(path=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(folder.rglob('*')) if p.is_file()]
RECEIPTS=[]
def command(name,argv,expected=0,diagnostic=None,timeout=30,extra_env=None):
 folder=COMMANDS/name;folder.mkdir(parents=True,exist_ok=False)
 env=dict(PATH='/usr/bin:/bin',TMPDIR=str(SCRATCH));env.update(extra_env or {})
 start=time.monotonic();timed_out=False
 with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
  child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=out,stderr=err)
  try:code=child.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True;child.kill();code=child.wait(timeout=10)
 result=dict(argv=argv,cwd=str(ROOT),environment=env,elapsed_seconds=time.monotonic()-start,
  exit_code=code,expected_exit_code=expected,direct_child_pid=child.pid,direct_child_waited=True,
  timed_out=timed_out,diagnostic=diagnostic,compiler_sha256=sha(RUSTC.read_bytes()),
  source_bindings_sha256=sha((HERE/'input-bindings.json').read_bytes()),
  runner_sha256=sha(Path(__file__).read_bytes()),
  output={n:dict(bytes=(folder/n).stat().st_size,sha256=sha((folder/n).read_bytes())) for n in ['stdout','stderr']})
 write('commands/'+name+'/receipt.json',result);RECEIPTS.append(result)
 assert not timed_out and code==expected,(name,code,timed_out)
 if diagnostic:assert diagnostic in (folder/'stderr').read_text(),name
 return folder

def custody():
 release=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-host-account-independent-release.json'
 assert sha(release.read_bytes())=='0ff404a5075827db7e055f16c75a5ec48da09902caa85b594a0cd171d370588f'
 seal=PRODUCER/'seal.json'
 assert sha(seal.read_bytes())=='6e8c8e2d8dde62e2e35fe2e8fb1a851a342d8d95f8c71facd938416ac3e153e3'
 listing=json.loads(seal.read_text())['members']
 assert len(listing)==136 and sum(x['bytes'] for x in listing)==3432402
 for x in listing:
  data=(PRODUCER/x['path']).read_bytes();assert len(data)==x['bytes'] and sha(data)==x['sha256'],x['path']
 inputs=json.loads((PRODUCER/'input-bindings.json').read_text())
 for x in inputs['inputs']:
  data=(ROOT/x['path']).read_bytes();assert len(data)==x['bytes'] and sha(data)==x['sha256'],x['path']
 boot=json.loads((BOOT/'seal.json').read_text())['members']
 for x in boot:
  data=(BOOT/x['path']).read_bytes();assert len(data)==x['bytes'] and sha(data)==x['sha256'],x['path']
 bindings=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  producer_seal=dict(path=str(seal.relative_to(ROOT)),sha256=sha(seal.read_bytes()),member_count=len(listing),member_bytes=sum(x['bytes'] for x in listing)),
  root_release=dict(path=str(release.relative_to(ROOT)),sha256=sha(release.read_bytes())),
  source_tree_sha256='5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b',
  source_members=145,basis='funding144 + released bootstrap leaf + private account/entry, distinct from combined145',
  authored_inputs=[dict(path=n,bytes=(PRODUCER/n).stat().st_size,sha256=sha((PRODUCER/n).read_bytes())) for n in ['host_account.rs','entry.inc.rs']],
  standalone_sources=members(HERE/'sources'),upstream_bindings=inputs['inputs'],bootstrap_members_verified=len(boot))
 write('input-bindings.json',bindings)

def whole_compile():
 vm=SCRATCH/'vm';shutil.copytree(FUNDING/'source/vm',vm)
 base=members(vm);assert len(base)==144 and sha(canonical(base))=='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
 profile=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
 with profile.open('ab') as out:
  out.write(b'\n\n'+(BOOT/'driver.inc.rs').read_bytes())
  out.write(b'\n\n'+(PRODUCER/'entry.inc.rs').read_bytes())
 (vm/'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs').write_bytes((PRODUCER/'host_account.rs').read_bytes())
 actual=members(vm);manifest=json.loads((PRODUCER/'source-manifest.json').read_text())
 assert actual==manifest['members'] and len(actual)==145
 assert sha(canonical(actual))==manifest['source_tree_sha256']=='5cd522af7e126d88496b5aefee722ff481821f0cf5babdbdbd7fbeba646c380b'
 write('reconstructed-source-manifest.json',dict(schema=1,members=actual,source_tree_sha256=sha(canonical(actual)),matches_frozen_manifest=True,not_combined145=True))
 argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
 for flag in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
  argv+=['--cfg','feature="'+flag+'"']
 argv+=['--cfg','mixer_bootstrap_one_fixture_v1','--crate-type','lib',str(vm/'src/lib.rs'),'--emit=metadata='+str(SCRATCH/'entry.rmeta')]
 command('exact145-typed-route-metadata',argv,timeout=180,extra_env={'CARGO_MANIFEST_DIR':str(vm)})
 write('typed-route-compile.json',dict(schema=1,source_members=145,source_tree_sha256=manifest['source_tree_sha256'],metadata_only=True,product_runtime=False,actual_typed_route_compiled=True,complete_quote_or_policy_accepted=False))

def standalone():
 version=command('compiler-version',[str(RUSTC),'--version','--verbose'])
 source=HERE/'sources/test_driver.rs'
 for mode,opt in [('debug','0'),('optimized','3')]:
  binary=SCRATCH/('account-'+mode)
  command(mode+'-compile',[str(RUSTC),'--edition=2021','--test','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind',str(source),'-o',str(binary)])
  result=command(mode+'-run',[str(binary),'--test-threads=1'])
  assert '19 passed; 0 failed' in (result/'stdout').read_text()
 negatives=json.loads((HERE/'sources/negative-controls.json').read_text())
 for x in negatives:
  command('negative-'+x['name'],[str(RUSTC),'--edition=2021',str(HERE/'sources'/x['file']),'--emit=metadata='+str(SCRATCH/(x['name']+'.rmeta'))],1,x['error'])
 command('positive-borrowed-api',[str(RUSTC),'--edition=2021',str(HERE/'sources/positive_borrowed_api.rs'),'--emit=metadata='+str(SCRATCH/'positive.rmeta')])
 write('host-test-results.json',dict(schema=1,compiler_version=(version/'stdout').read_text(),compiler_sha256=sha(RUSTC.read_bytes()),modes=['debug','optimized'],producer_tests_per_mode=11,independently_authored_tests_per_mode=8,total_tests_per_mode=19,negative_compile_controls=len(negatives),positive_controls=1,all_expected=True,genuine_loader_or_product_runtime=False))

def main():
 assert not (HERE/'seal.json').exists()
 SCRATCH.mkdir(exist_ok=False)
 try:
  custody();whole_compile();standalone()
 finally:
  shutil.rmtree(SCRATCH)
  write('cleanup.json',dict(schema=1,owned_scratch_removed=not SCRATCH.exists(),direct_children_waited=True,global_process_inventory=False,native_device_simulator_emulator_UI_capture_started=False,other_projects_inspected_or_changed=False))
if __name__=='__main__':main()
