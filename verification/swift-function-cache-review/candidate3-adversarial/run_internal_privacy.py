#!/usr/bin/env python3
"""Negative compile probes use actual private Swift types in their own module."""
from pathlib import Path
import hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent;TREE=HERE/'tree'
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'CARGO_TARGET_DIR':str(HERE/'build'),'TMPDIR':str(HERE/'tmp')}
target=TREE/'vm/src/experimental_swift_reactor/cache_tests.rs';original=target.read_bytes()
cases=[
('positive','fn review_compile_positive(cache: &SwiftFunctionCache,p:&SwiftFunctionPin,c:&mut RuntimeControl){let _=cache.view(p,c,None).unwrap().function;}',None),
('swift_view_mutation','fn review_compile_negative(cache:&mut SwiftFunctionCache,p:SwiftFunctionPin,c:&mut RuntimeControl){let v=cache.view(&p,c,None).unwrap();let mut phase=cache.prepare_operation(c,None,cache_cursor()).unwrap();let _=phase.pin(cache,34);let _=v.instructions.len();}','E0502'),
('swift_view_release','fn review_compile_negative(cache:&mut SwiftFunctionCache,p:SwiftFunctionPin,c:&mut RuntimeControl){let v=cache.view(&p,c,None).unwrap();let _=cache.release(p,c,None);let _=v.instructions.len();}','E0502'),
('swift_pin_clone','fn review_compile_negative(p:SwiftFunctionPin){let _=p.clone();}','E0599'),
('actual_adopted_reuse','fn review_compile_negative(c:&mut RuntimeControl,a:AdoptedProof){let mut phase=SwiftFunctionCache::prepare(c,None,&a,cache_cursor()).unwrap();let _=phase.construct(a);let _=phase.construct(a);}','E0382'),
('tail_control_alias','fn review_compile_negative(owner:&mut Option<SwiftFunctionCache>,c:&mut RuntimeControl){let tail=SwiftFunctionCache::cleanup(owner,c,None).unwrap();let _=c.usage(None);let mut outcome=None;tail.complete((),&mut outcome);}','E0502')]
commands=[]
try:
    for mode in ['debug','release']:
        for name,source,expected in cases:
            addition=('\n'+source+'\n').encode();target.write_bytes(original+addition)
            argv=['cargo','check','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib','--tests']
            if mode=='release':argv+=['--release']
            start=time.monotonic();p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);output=p.stdout+p.stderr
            passed=(p.returncode==0) if expected is None else (p.returncode!=0 and expected in output)
            log=f'privacy-{mode}-{name}.log';(HERE/log).write_text(output)
            commands.append({'argv':argv,'cwd':str(TREE),'case':name,'source':source,'expected_error':expected,'exit_code':p.returncode,'expected_outcome':passed,'seconds':time.monotonic()-start,'output':log,'output_sha256':hashlib.sha256(output.encode()).hexdigest(),'derived_test_source_sha256':hashlib.sha256(original+addition).hexdigest()})
            print(f'{mode} {name}: exit={p.returncode} expected={passed}',flush=True)
            (HERE/'internal-privacy.json').write_text(json.dumps({'commands':commands,'scope':'no executed code; private Swift borrow/move rules in isolated test-only copies'},indent=2)+'\n')
            if not passed:raise SystemExit(1)
finally:
    target.write_bytes(original)
