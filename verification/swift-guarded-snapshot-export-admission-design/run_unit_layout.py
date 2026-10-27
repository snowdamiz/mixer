"""Bounded compiler-only unit-configuration layout probe. No unit test runs."""
import json,os,pathlib,re,shutil,tempfile
from run_controls import HERE,ACCEPTED,command,dump,digest

scratch=pathlib.Path(tempfile.mkdtemp(prefix='unit-layout-',dir=HERE))
try:
    tree=scratch/'source'; shutil.copytree(ACCEPTED,tree)
    for added,member in [('control_append.rs','src/experimental_swift_reactor/control.rs'),
        ('initial_append.rs','src/experimental_swift_reactor/cache/initial_profile_v1.rs'),
        ('wasi_append.rs','src/experimental_wasi/accounted.rs')]:
        p=tree/member; p.write_bytes(p.read_bytes()+b'\n'+(HERE/'prototype'/added).read_bytes())
    ll=scratch/'unit.ll'
    argv=['/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc',
        '--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--test',
        '--emit',f'llvm-ir={ll}','-C','opt-level=0','-C','overflow-checks=yes']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        argv+=['--cfg',f'feature="{feature}"']
    argv+=[str(tree/'src/lib.rs')]
    previous_manifest=os.environ.get('CARGO_MANIFEST_DIR')
    os.environ['CARGO_MANIFEST_DIR']=str(tree)
    try: receipt,out,err=command('compile-unit-layout',argv,HERE)
    finally:
        if previous_manifest is None: os.environ.pop('CARGO_MANIFEST_DIR',None)
        else: os.environ['CARGO_MANIFEST_DIR']=previous_manifest
    assert receipt['exit_code']==0,err
    definition=next(line for line in ll.read_text().splitlines() if line.startswith('@MIXER_ADMISSION_DESIGN_LAYOUT_PROBE'))
    (HERE/'commands/compile-unit-layout/layout-llvm.txt').write_text(definition+'\n')
    value=re.search(r'c"(.*?)"',definition).group(1); raw=bytearray(); i=0
    while i<len(value):
        if value[i]=='\\': raw.append(int(value[i+1:i+3],16)); i+=3
        else: raw.append(ord(value[i])); i+=1
    assert len(raw)==18*8
    words=[int.from_bytes(raw[i:i+8],'little') for i in range(0,len(raw),8)]
    result=dict(layout_words=words,unit_configuration=True,no_tests_executed=True,
        runner_sha256=digest(pathlib.Path(__file__)),source_manifest='compile-source-manifest.json',
        cargo_manifest_dir=str(tree),earlier_compile_refusal='commands/compile-unit-layout-attempt-1/stderr',
        scope='Compiler constants for proposal types, not final implementation source-place admission')
    dump(HERE/'unit-layout-result.json',result)
    print(json.dumps(result,indent=2))
finally:
    shutil.rmtree(scratch)
    dump(HERE/'unit-layout-cleanup.json',dict(scratch_removed=not scratch.exists(),compiler_child_reaped=True,no_tests_executed=True))
