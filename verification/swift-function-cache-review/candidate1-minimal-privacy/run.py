#!/usr/bin/env python3
"""Feature-specific downstream privacy check against immutable candidate1."""
from pathlib import Path
import hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent;TREE=HERE.parent/'tree'
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'CARGO_TARGET_DIR':str(HERE/'build'),'TMPDIR':str(HERE.parent/'tmp')}
def sha(b):return hashlib.sha256(b).hexdigest()
source={str(p.relative_to(TREE)):sha(p.read_bytes()) for p in (TREE/'vm/src').rglob('*.rs')}
folder=HERE/'snippets';folder.mkdir(exist_ok=True)
cases=[('positive','use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;fn f(p:&ValidatedSwiftReactor){let _=p.source();}',None),
('minimal_legacy_cache_private','use mixer_vm::experimental::cache::FunctionCache;', 'E0603'),
('swift_cache_private','use mixer_vm::experimental_swift_reactor::cache::SwiftFunctionCache;','E0603'),
('control_private','use mixer_vm::experimental_swift_reactor::control::RuntimeControl;','E0603'),
('descriptor_private','use mixer_vm::experimental::descriptors::FunctionSpanView;','E0603'),
('adapters_private','use mixer_vm::experimental::cache::borrowed::{SnapshotView,CacheParts,FrozenMode};','E0603')]
commands=[]
for mode in ['debug','release']:
    argv=['cargo','build','--locked','--manifest-path','vm/Cargo.toml','--lib','--features','experimental-swift-reactor']
    if mode=='release':argv+=['--release']
    p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);out=p.stdout+p.stderr
    log=f'build-{mode}.log';(HERE/log).write_text(out);assert p.returncode==0,out
    commands.append({'argv':argv,'cwd':str(TREE),'exit_code':p.returncode,'output':log,'output_sha256':sha(out.encode())})
    lib=HERE/'build'/mode/'libmixer_vm.rlib'
    for name,text,expected in cases:
        file=folder/(mode+'-'+name+'.rs');file.write_text(text)
        argv=['rustc','--edition=2021','--crate-type=lib','--emit=metadata','--crate-name','review_minimal_'+name,'--extern',f'mixer_vm={lib}','-L',f'dependency={lib.parent}/deps','--out-dir',str(folder),str(file)]
        p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);out=p.stdout+p.stderr
        passed=p.returncode==0 if expected is None else p.returncode!=0 and expected in out
        log=f'{mode}-{name}.log';(HERE/log).write_text(out)
        commands.append({'argv':argv,'cwd':str(TREE),'case':name,'source':text,'expected_error':expected,'exit_code':p.returncode,'expected_outcome':passed,'output':log,'output_sha256':sha(out.encode())})
        print(f'{mode} {name}: {passed}',flush=True)
        assert passed,out
        (HERE/'receipt.json').write_text(json.dumps({'scope':'minimal experimental-swift-reactor downstream visibility only; candidate1; no guest execution','source_manifest':source,'source_digest':sha(json.dumps(source,sort_keys=True).encode()),'commands':commands},indent=2)+'\n')
assert source=={p:sha((TREE/p).read_bytes()) for p in source}
