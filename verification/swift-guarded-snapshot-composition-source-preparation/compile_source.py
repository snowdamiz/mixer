"""Compile prepared source only; never executes a guest, wrapper or exporter."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,time,re,difflib,signal
ROOT=Path(__file__).resolve().parent
VM=ROOT/'source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
WORK=ROOT/'owned-work'
WORK.mkdir(exist_ok=True)
def sha(data):return hashlib.sha256(data).hexdigest()
def manifest(directory):
    return [{'path':p.relative_to(directory).as_posix(),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(directory.rglob('*')) if p.is_file()]
def run(label,unit=False,opt=False,emit='llvm-ir',extra=None,expected=0,layout=True):
    command=ROOT/'commands'/label
    command.mkdir(parents=True,exist_ok=False)
    version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True).stdout
    sources=manifest(VM);assert len(sources)==144,len(sources)
    # Frozen upstream support is bound read-only, alongside every authored
    # preparation support member existing at this exact compile preimage.
    upstream=manifest(ROOT.parent/'swift-guarded-snapshot-encoder-implementation/host')
    assert len(upstream)==11,len(upstream)
    own=[{'path':p.relative_to(ROOT).as_posix(),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(ROOT.rglob('*')) if p.is_file() and p.parts[len(ROOT.parts)] not in ('source','commands','owned-work')]
    source_preimage={'schema':1,'source_members':sources,'upstream_encoder_support_members':upstream,'preparation_support_members':own}
    (command/'build-preimage.json').write_text(json.dumps(source_preimage,indent=2)+'\n')
    frozen=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm'
    delta=[]
    for member in sources:
        relative=member['path'];before=(frozen/relative).read_text();after=(VM/relative).read_text()
        if before!=after:delta.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='frozen/'+relative,tofile='prepared/'+relative))
    (command/'source-delta.patch').write_text(''.join(delta))
    artifact=WORK/(label+('.ll' if emit=='llvm-ir' else '.rmeta'))
    argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+('3' if opt else '0'),'-C','overflow-checks=yes','-C','panic=unwind']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        argv+=['--cfg','feature="'+feature+'"']
    if layout:argv+=['--cfg','mixer_snapshot_composition_layout']
    argv+=['--test'] if unit else ['--crate-type','rlib']
    argv+=['--emit='+emit,str(VM/'src/lib.rs'),'-o',str(artifact)]
    if extra:argv+=extra
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(WORK),'CARGO_MANIFEST_DIR':str(VM),
         'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),
         'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
         'MIXER_LOADER_MANIFEST_SHA256':sha(json.dumps(source_preimage,sort_keys=True,separators=(',',':')).encode()),
         'MIXER_LOADER_COMMAND_SHA256':sha(json.dumps(argv,separators=(',',':')).encode())}
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(json.dumps(env,sort_keys=True,separators=(',',':')).encode())
    started=time.monotonic()
    p=subprocess.Popen(argv,env=env,cwd=ROOT.parent.parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False;cleanup_actions=[]
    try:stdout,stderr=p.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        timed_out=True
        try:os.killpg(p.pid,signal.SIGTERM);cleanup_actions.append('SIGTERM owned compiler process group '+str(p.pid))
        except ProcessLookupError:pass
        try:stdout,stderr=p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(p.pid,signal.SIGKILL);cleanup_actions.append('SIGKILL owned compiler process group '+str(p.pid))
            except ProcessLookupError:pass
            stdout,stderr=p.communicate()
    (command/'stdout').write_bytes(stdout);(command/'stderr').write_bytes(stderr)
    layouts={}
    if p.returncode==0 and emit=='llvm-ir' and layout:
        data=artifact.read_text()
        symbols=['MIXER_COMPOSITION_CONTROL_LAYOUTS_V1','MIXER_COMPOSITION_INITIAL_LAYOUTS_V1',
                 'MIXER_COMPOSITION_ENCODER_HELPER_LAYOUTS_V1','MIXER_COMPOSITION_LOADER_HELPER_LAYOUTS_V1',
                 'MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1','MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1']
        for symbol in symbols:
            candidates=[line for line in data.splitlines() if line.startswith('@') and symbol in line and 'constant' in line and 'c"' in line]
            if not candidates:continue
            assert len(candidates)==1,(symbol,candidates)
            line=candidates[0]
            (command/(symbol+'.llvm')).write_text(line+'\n')
            raw=re.search(r'c"(.*?)"',line).group(1)
            decoded=bytearray();i=0
            while i<len(raw):
                if raw[i]=='\\':decoded.append(int(raw[i+1:i+3],16));i+=3
                else:decoded.append(ord(raw[i]));i+=1
            layouts[symbol]=[int.from_bytes(decoded[i:i+8],'little') for i in range(0,len(decoded),8)]
        capture_fragments=[]
        for block in data.split('\n\n'):
            if 'composer_measure_parameter_span_capture_v1' in block and ('define ' in block or block.startswith('@')):
                capture_fragments.append(block)
        (command/'exact-parameter-capture.llvm').write_text('\n\n'.join(capture_fragments)+'\n')
        # Debug emits the exact closure size_of_val/align_of_val specializations;
        # optimized emits the private const measurer's constant tuple directly.
        size=alignment=None
        for block in capture_fragments:
            match=re.search(r'ret i64 (\d+)',block)
            if match and 'size_of_val' in block:size=int(match.group(1))
            if match and 'align_of_val' in block:alignment=int(match.group(1))
            pair=re.search(r'ret \{ i64, i64 \} \{ i64 (\d+), i64 (\d+) \}',block)
            if pair:size,alignment=map(int,pair.groups())
        if size is not None and alignment is not None:
            layouts['EXACT_PARAMETER_CAPTURE_V1']=[size,alignment]
        else:
            raise RuntimeError('Exact parameter capture LLVM extraction unresolved; retained LLVM fragments are required, no guessed size')
        (command/'layouts.json').write_text(json.dumps(layouts,indent=2)+'\n')
    if p.returncode==0 and emit=='llvm-ir' and not layout:
        data=artifact.read_text()
        measurement_names=['MIXER_COMPOSITION_CONTROL_LAYOUTS_V1','MIXER_COMPOSITION_INITIAL_LAYOUTS_V1',
          'MIXER_COMPOSITION_ENCODER_HELPER_LAYOUTS_V1','MIXER_COMPOSITION_LOADER_HELPER_LAYOUTS_V1',
          'MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1','MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1',
          'COMPOSITION_PARAMETER_CAPTURE_MEASURER_V1','composer_measure_span_capture_v1',
          'composer_measure_parameter_span_capture_v1','composer_checked_capture_static_sum_v1']
        found=[name for name in measurement_names if name in data]
        absence={'measurement_cfg_enabled':False,'measurement_names_checked':measurement_names,'found':found,'passed':not found,'LLVM_sha256':sha(data.encode()),'scope':'non-test feature-enabled production LLVM symbol/definition absence only'}
        (command/'measurement-absence.json').write_text(json.dumps(absence,indent=2)+'\n')
        assert not found,found
    receipt={'argv':argv,'cwd':str(ROOT.parent.parent),'environment':env,'rustc_version':version.decode(),'source_member_count':144,
             'upstream_host_support_count':11,'preparation_support_count':len(own),'source_tree_sha256':sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()),'measurement_cfg_enabled':layout,
             'exit_code':p.returncode,'expected':expected,'expectation_met':p.returncode==expected,'elapsed_seconds':time.monotonic()-started,'child_reaped':True,
             'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'owned_process_group':p.pid,'new_session':True,'timeout_seconds':120,'timed_out':timed_out,'cleanup_actions':cleanup_actions,
             'scope':'compiler only; no runtime execution; no upstream acceptance or operational authority'}
    (command/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if artifact.exists():artifact.unlink()
    print(json.dumps({'label':label,'exit_code':p.returncode,'layouts':layouts}))
    return p.returncode
if __name__=='__main__':
    label=sys.argv[1]
    raise SystemExit(run(label,unit='unit' in label,opt='optimized' in label,emit='metadata' if 'typecheck' in label else 'llvm-ir',layout=not label.startswith('default-')))
