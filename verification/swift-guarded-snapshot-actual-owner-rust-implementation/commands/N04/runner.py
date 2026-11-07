"""Owned bounded compiler/host execution. Never native inputs or fixture loader."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
EXPECTED='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
SDK='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def row(p,base=ROOT):
 raw=p.read_bytes();return dict(path=str(p.relative_to(base)) if p.is_relative_to(base) else str(p),bytes=len(raw),sha256=sha(raw))
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def source_manifest(base):return [row(p,base) for p in sorted(base.rglob('*')) if p.is_file()]
def frozen():
 paths=set()
 for packet in ['swift-guarded-snapshot-actual-owner-rust-selection','swift-guarded-snapshot-prepaid-input-owner-affine-refusal','swift-guarded-snapshot-prepaid-affine-refusal-independent']:
  base=ROOT/'verification'/packet;j=json.loads((base/'seal.json').read_bytes())
  assert len(j['members'])==j['member_count'] and sum(r['bytes'] for r in j['members'])==j['member_bytes'] and digest(j['members'])==j['tree_sha256']
  for r in j['members']:
   p=base/r['path'];raw=p.read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256'];paths.add(p)
  paths.add(base/'seal.json')
 c=ROOT/'verification/swift-guarded-snapshot-owned-binding-provider/proposed-source-custody.json';paths.add(c)
 for r in json.loads(c.read_bytes()):
  p=ROOT/r['origin'];raw=p.read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256'];paths.add(p)
 paths.add(ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-actual-owner-Rust-implementation-selection.json')
 return [row(p) for p in sorted(paths)]
def common(source):return [str(TOOL),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','overflow-checks=yes','-C','panic=unwind','--cfg','feature="experimental-swift-reactor"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-function-cache"','--cfg','mixer_bootstrap_one_fixture_v1']
def run(label,argv,source=None,kind='compiler'):
 out=HERE/'commands'/label;out.mkdir(parents=True,exist_ok=False)
 source=source or HERE/'source';source_rows=source_manifest(source);inputs=frozen();toolrow=row(TOOL);assert toolrow['sha256']==EXPECTED
 env={'PATH':'/usr/bin:/bin','RUSTC_BOOTSTRAP':'1','SDKROOT':SDK,'CARGO_MANIFEST_DIR':str(source/'vm'),'TMPDIR':str(HERE/'build'),'LANG':'C','LC_ALL':'C','TZ':'UTC'}
 if kind=='host':toolrow=row(Path(argv[0]));tool_version=json.loads((HERE/'toolchain.json').read_text())
 elif label=='toolchain':tool_version='queried by this exact command'
 else:tool_version=json.loads((HERE/'toolchain.json').read_text())
 write(out/'source-manifest.json',dict(members=source_rows,tree_sha256=digest(source_rows)))
 write(out/'input-before.json',inputs)
 write(out/'plan.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(ROOT),environment=env,
  tool=toolrow,tool_version=tool_version,source_tree_sha256=digest(source_rows),source_revision='9398732c23648a82097d5a72b02b1c77af818e41',
  revision_scope='frozen source baseline; changed two-member overlay is bound by full manifest',timeout_seconds=55,execution_deadline_seconds=51,
  stdout_stderr_each_limit_bytes=4194304,kind=kind,parent_pid=os.getpid(),parent_pgid=os.getpgrp(),native_fixture_UI=False))
 (out/'runner.py').write_bytes(Path(__file__).read_bytes())
 for name in ['vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs']:
  dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source/name).read_bytes())
 start=time.monotonic();reason=None;descendant_cleanup=False
 with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
  p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
  while p.poll() is None:
   if time.monotonic()-start>51:reason='deadline';break
   if any((out/n).stat().st_size>4194304 for n in ['stdout','stderr']):reason='output-limit';break
   time.sleep(.05)
  if reason:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  code=p.wait(timeout=max(.1,54-(time.monotonic()-start)))
  try:
   os.killpg(p.pid,0);os.killpg(p.pid,signal.SIGKILL);descendant_cleanup=True
  except ProcessLookupError:pass
  deadline=start+54
  while time.monotonic()<deadline:
   try:os.killpg(p.pid,0)
   except ProcessLookupError:break
   time.sleep(.05)
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 after=frozen();write(out/'input-after.json',after);src_after=source_manifest(source)
 receipt=dict(exit=code,reason=reason,elapsed_seconds=time.monotonic()-start,owned_pid=p.pid,owned_pgid=p.pid,child_reaped=p.returncode is not None,
  exact_owned_group_absent=absent,descendant_cleanup=descendant_cleanup,stdout=row(out/'stdout'),stderr=row(out/'stderr'),input_unchanged=inputs==after,
  source_unchanged=source_rows==src_after,tool_after=row(Path(argv[0])),output_within_caps=all((out/n).stat().st_size<=4194304 for n in ['stdout','stderr']))
 write(out/'receipt.json',receipt)
 assert absent and inputs==after and source_rows==src_after and receipt['output_within_caps'] and reason is None,receipt
 print(json.dumps(dict(label=label,exit=code,elapsed=receipt['elapsed_seconds'],stderr_bytes=receipt['stderr']['bytes'],group_absent=absent)))
 return code
if __name__=='__main__':
 label=sys.argv[1];build=HERE/'build';build.mkdir(exist_ok=True)
 if label=='toolchain':
  code=run(label,[str(TOOL),'-vV'],kind='version');assert code==0
  write(HERE/'toolchain.json',dict(tool=row(TOOL),version=(HERE/'commands/toolchain/stdout').read_text(),host=SDK))
 elif label in ('production','production-repair1'):
  args=common(HERE/'source')+['-C','opt-level=0','-Zmir-opt-level=0','--crate-type','rlib',str(HERE/'source/vm/src/lib.rs'),'-Zmir-include-spans=yes','--emit=metadata='+str(build/'actual.rmeta')+',mir='+str(build/'actual.mir')]
  sys.exit(run(label,args))
 elif label in ('build-debug','build-opt','build-debug-repair1'):
  mode='debug' if label.startswith('build-debug') else 'opt';args=common(HERE/'source')+['--test','-C','opt-level='+('0' if mode=='debug' else '2'),str(HERE/'source/vm/src/lib.rs'),'-o',str(build/('tests-'+mode))]
  sys.exit(run(label,args))
 elif label in ('run-debug','run-opt','run-debug-repair1'):
  mode=label.split('-')[1];sys.exit(run(label,[str(build/('tests-'+mode)),'prepaid_actual_owner_v1','--test-threads=1','--nocapture'],kind='host'))
 else:raise AssertionError('unknown command')
