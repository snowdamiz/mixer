#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[1]);ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('b',HERE/'build_overlay.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
BUILD=Path('/tmp')/('mixer-control-nested-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));BUILD.mkdir();vm=BUILD/'vm'
with tarfile.open(OUT/'candidate-source.tar.gz') as t:t.extractall(BUILD,filter='data')
child=vm/'src/experimental_swift_reactor/control_operations.rs';child.write_text(child.read_text()+'''
pub(super) fn nested_layout_metadata() {
 println!("NESTED {} {} {} {}",std::mem::offset_of!(ActivePositions,private_scalar_transfers),std::mem::size_of::<crate::experimental::execution::SwiftControlPrivatePositions>(),std::mem::align_of::<crate::experimental::execution::SwiftControlPrivatePositions>(),std::mem::size_of::<ActivePositions>());
}
#[cfg(test)] #[test] fn nested_control_layout_only(){nested_layout_metadata();}
''')
f=vm/'src/experimental_swift_reactor/frame_operations.rs';f.write_text(f.read_text()+'\npub(crate) fn nested_control_layout_route(){control_operations::nested_layout_metadata();}\n')
f=vm/'src/experimental_swift_reactor/mod.rs';f.write_text(f.read_text()+'\npub(crate) fn nested_control_layout_route(){execution::frame_operations::nested_control_layout_route();}\n')
f=vm/'src/lib.rs';f.write_text(f.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn nested_control_layout_route(){experimental_swift_reactor::nested_control_layout_route();}\n')
(vm/'src/bin').mkdir(exist_ok=True);(vm/'src/bin/nested_control_layout.rs').write_text('fn main(){mixer_vm::nested_control_layout_route();}\n')
manifest=b.files(vm);(OUT/'nested-layout-manifest.json').write_bytes(b.enc(manifest));commands=[];layouts=[];status='failed';env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(BUILD/'target'))
try:
 for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   for unit in [False,True]:
    name='nested-'+config+('-release' if release else '-debug')+('-unit' if unit else '-production')
    argv=['cargo','test','--lib',*flags,*(['--release'] if release else []),'nested_control_layout_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--bin','nested_control_layout',*flags,*(['--release'] if release else [])]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(argv,cwd=vm,env=env,capture_output=True,timeout=180)
    for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
    commands.append(dict(name=name,argv=argv,cwd=str(vm),sourceTreeSHA256=hashlib.sha256(b.enc(manifest)).hexdigest(),exitCode=p.returncode,startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout=name+'.stdout',stdoutSHA256=b.sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=b.sha(OUT/(name+'.stderr'))))
    assert p.returncode==0,p.stderr.decode()[-3000:]
    line=next(x[x.index('NESTED '):] for x in p.stdout.decode().splitlines() if 'NESTED ' in x);values=list(map(int,line.split()[1:]));layouts.append(dict(config=config,profile='release' if release else 'debug',unit=unit,offset=values[0],bytes=values[1],alignment=values[2],activeBytes=values[3]));print(name,values,flush=True)
 status='passed-nested-component-offset-layout-only'
finally:
 (OUT/'nested-layout-receipt.json').write_bytes(b.enc(dict(status=status,commands=commands,layouts=layouts,controlMethodsExecuted=False)))
 shutil.rmtree(BUILD);(OUT/'nested-layout-cleanup.json').write_bytes(b.enc(dict(removed=str(BUILD),buildRemoved=not BUILD.exists(),nativeInstancesStarted=False)))
