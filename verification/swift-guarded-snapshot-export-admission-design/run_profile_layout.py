"""Compiler-only exact sizes of the selected-scope proposal's explicit source roles."""
import json,os,pathlib,re,shutil,tempfile
from run_controls import HERE,ACCEPTED,command,dump,digest
scratch=pathlib.Path(tempfile.mkdtemp(prefix='profile-layout-',dir=HERE)); results=[]
try:
    tree=scratch/'source'; shutil.copytree(ACCEPTED,tree)
    p=tree/'src/experimental_swift_reactor/control.rs'
    p.write_bytes(p.read_bytes()+b'\n'+(HERE/'prototype/profile_append.rs').read_bytes())
    manifest=[dict(path=str(p.relative_to(tree)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(tree.rglob('*')) if p.is_file()]
    dump(HERE/'profile-compile-source-manifest.json',dict(members=manifest,prototype_only=True))
    for name,opt,unit in [('debug','0',False),('optimized','3',False),('unit','0',True)]:
        ll=scratch/(name+'.ll')
        argv=['/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc',
            '--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
            '--emit',f'llvm-ir={ll}','-C',f'opt-level={opt}','-C','overflow-checks=yes']
        argv+=['--test'] if unit else ['--crate-type','lib']
        for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
            argv+=['--cfg',f'feature="{feature}"']
        argv+=[str(tree/'src/lib.rs')]
        previous=os.environ.get('CARGO_MANIFEST_DIR'); os.environ['CARGO_MANIFEST_DIR']=str(tree)
        try: receipt,out,err=command('profile-layout-'+name,argv,HERE)
        finally:
            if previous is None: os.environ.pop('CARGO_MANIFEST_DIR',None)
            else: os.environ['CARGO_MANIFEST_DIR']=previous
        assert receipt['exit_code']==0,err
        definition=next(line for line in ll.read_text().splitlines() if line.startswith('@MIXER_ADMISSION_PROFILE_LAYOUT_PROBE'))
        (HERE/'commands'/('profile-layout-'+name)/'layout-llvm.txt').write_text(definition+'\n')
        value=re.search(r'c"(.*?)"',definition).group(1); raw=bytearray(); i=0
        while i<len(value):
            if value[i]=='\\': raw.append(int(value[i+1:i+3],16)); i+=3
            else: raw.append(ord(value[i])); i+=1
        assert len(raw)==128
        results.append(dict(mode=name,unit=unit,no_tests_executed=True,cargo_manifest_dir=str(tree),
            layout_words=[int.from_bytes(raw[i:i+8],'little') for i in range(0,len(raw),8)]))
    assert results[0]['layout_words']==results[1]['layout_words']
    dump(HERE/'profile-layout-result.json',dict(results=results,runner_sha256=digest(pathlib.Path(__file__)),
        scope='Exact compiler sizes of conservative proposed common-core delta and opaque owning scope; not implemented admission/source-closure completeness or selected floor'))
    print(json.dumps(results,indent=2))
finally:
    shutil.rmtree(scratch)
    dump(HERE/'profile-layout-cleanup.json',dict(scratch_removed=not scratch.exists(),all_compiler_children_reaped=True,no_tests_executed=True))
