"""Independent frozen-custody, exact-overlay, identity-preimage and pure parser review.
Only this packet and its owned scratch are written. No real loader/VM/writer runs.
"""
from pathlib import Path
import datetime, difflib, hashlib, json, os, platform, shutil, signal, struct, subprocess, sys, time
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-guarded-snapshot-descriptor-rebinding'
FUNDING=ROOT/'verification/swift-guarded-snapshot-funding-implementation'
EMISSION=ROOT/'verification/swift-guarded-snapshot-emission-bound-implementation'
LOADER=ROOT/'verification/swift-real-profile-loader-binding'
RELEASE=ROOT/'verification/swift-semantic-adapter-root-review/guarded-snapshot-descriptor-rebinding-independent-release.json'
SCRATCH=HERE/'owned-work'
LP='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
PP='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
HP='src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs'
KEYS=['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256']
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
checks={}; commands=[]; artifacts=[]
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def read(p): return json.loads(p.read_bytes())
def save(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def identity(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def require(name,v):
    assert v,name
    checks[name]=True
def roster(files):
    members=[{'path':p,'bytes':len(b),'sha256':sha(b)} for p,b in sorted(files.items(),key=lambda e:Path(e[0]))]
    return {'schema':1,'member_count':len(members),'members':members,'tree_sha256':sha(canonical(members))}
def seal(packet,expected,selected=None):
    raw=(packet/'seal.json').read_bytes();require('seal_hash_'+packet.name,sha(raw)==expected)
    v=json.loads(raw);by={m['path']:m for m in v['members']}
    require('seal_roster_'+packet.name,len(by)==v['member_count'] and ('tree_sha256' not in v or sha(canonical(v['members']))==v['tree_sha256']))
    names=list(by) if selected is None else selected
    for n in names:
        p=Path(n); assert not p.is_absolute() and '..' not in p.parts
        b=(packet/n).read_bytes();assert len(b)==by[n]['bytes'] and sha(b)==by[n]['sha256'],n
    extras=[]
    if selected is None:
        actual={str(p.relative_to(packet)) for p in packet.rglob('*') if p.is_file()}
        assert set(by)|{'seal.json'} <= actual
        extras=sorted(actual-(set(by)|{'seal.json'}))
        if packet==PRODUCER:assert not extras
        assert sum(m['bytes'] for m in v['members'])==v['member_bytes']
    return {'packet':str(packet.relative_to(ROOT)),'seal_sha256':expected,'verified_members':len(names),'whole_sealed_roster_verified':selected is None,'unsealed_nonmembers':extras,'member_bytes':sum(by[n]['bytes'] for n in names)}
def packed(items):
    bs=[os.fsencode(i) for i in items];return struct.pack('<Q',len(bs))+b''.join(struct.pack('<Q',len(b))+b for b in bs)
def envpacked(env): return packed([k+'='+v for k,v in sorted(env.items(),key=lambda e:os.fsencode(e[0]))])
def unpack(b):
    n=struct.unpack_from('<Q',b)[0];at=8;items=[]
    for _ in range(n):
        size=struct.unpack_from('<Q',b,at)[0];at+=8;assert at+size<=len(b);items.append(b[at:at+size]);at+=size
    assert at==len(b);return items
def absent(pgid):
    try: os.killpg(pgid,0);return False
    except ProcessLookupError:return True
def run(label,argv,env,timeout=45):
    dest=HERE/'commands'/label;dest.mkdir(parents=True,exist_ok=False);start=time.monotonic();actions=[]
    with (dest/'stdout').open('wb') as out,(dest/'stderr').open('wb') as err:
        p=subprocess.Popen(list(map(str,argv)),cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
        try:code=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM);actions.append('TERM owned timed-out group')
            try:code=p.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);actions.append('KILL owned group');code=p.wait(timeout=3)
    if not absent(p.pid):
        os.killpg(p.pid,signal.SIGKILL);actions.append('KILL owned surviving descendants')
    receipt={'argv':list(map(str,argv)),'environment':env,'cwd':str(ROOT),'exit_code':code,'timeout_seconds':timeout,'elapsed_seconds':time.monotonic()-start,'owned_process_group':p.pid,'owned_group_absent':absent(p.pid),'child_reaped':True,'cleanup_actions':actions,'stdout':identity(dest/'stdout'),'stderr':identity(dest/'stderr')}
    save(dest/'receipt.json',receipt);commands.append({'label':label,'receipt':identity(dest/'receipt.json')});save(HERE/'command-index.json',commands)
    assert receipt['owned_group_absent'] and code==0 and (dest/'stdout').stat().st_size+(dest/'stderr').stat().st_size<262144,(label,(dest/'stderr').read_text()[-4000:])
    print(label+': pass',flush=True);return (dest/'stdout').read_bytes()
def descriptor(parts,compiler,output):
    h=bytearray(512);h[:8]=b'MIXLBD01'
    for at,v in [(8,1),(16,512),(24,512+sum(map(len,parts))),(32,145),(40,11),(80,len(output))]:struct.pack_into('<Q',h,at,v)
    target=b'aarch64-apple-darwin';h[88:88+len(target)]=target
    for i,b in enumerate(parts):struct.pack_into('<Q',h,48+8*i,len(b));h[152+32*i:184+32*i]=bytes.fromhex(sha(b))
    h[280:312]=bytes.fromhex(compiler['sha256']);h[312:344]=bytes.fromhex(sha(output));return bytes(h)+b''.join(parts)
def main():
    assert not (HERE/'seal.json').exists() and not SCRATCH.exists()
    require('root_release_sha256',sha(RELEASE.read_bytes())=='1b438498f50bad81ee701d7e7d7c3c65c80686468c1789c4109da446db33a1e9')
    custody=[seal(PRODUCER,'5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea'),seal(FUNDING,'e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7'),seal(EMISSION,'e92026187ef181ddbcc178e53611ce5e4aa0111c613e9c8ad3a4aca58ff8ffcc')]
    support=read(LOADER/'baseline-host-support-manifest.json');selected=[m['retained_path'] for m in support['members']]+['baseline-host-support-manifest.json','CONTRACT.md','run_checks.py']
    custody.append(seal(LOADER,'e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2',selected))
    base={str(p.relative_to(FUNDING/'source/vm')):p.read_bytes() for p in (FUNDING/'source/vm').rglob('*') if p.is_file()}
    require('funding144_digest',len(base)==144 and roster(base)['tree_sha256']=='7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b')
    source=base.copy();source[LP]=base[LP].replace(b'if word(b, 32) != 144\n',b'if word(b, 32) != 145\n')
    declaration=b'// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\n'
    source[PP]=base[PP].replace(b'fn proposed_emission_work_v1(',declaration+b'fn proposed_emission_work_v1(')
    source[HP]=(EMISSION/'overlay/vm'/HP).read_bytes()
    require('three_path_overlay_closure',{str(p.relative_to(PRODUCER/'overlay/vm')) for p in (PRODUCER/'overlay/vm').rglob('*') if p.is_file()}=={LP,PP,HP})
    for name in [LP,PP,HP]: require('overlay_'+name,(PRODUCER/'overlay/vm'/name).read_bytes()==source[name])
    require('loader_whole_file_only_count_changed',source[LP].replace(b'if word(b, 32) != 145\n',b'if word(b, 32) != 144\n')==base[LP] and base[LP].count(b'if word(b, 32) != 144\n')==1)
    require('phase_whole_file_only_private_declaration',source[PP].replace(declaration,b'')==base[PP] and source[PP].count(declaration)==1)
    require('helper_exact_and_unused',sha(source[HP])=='ef14f2fe335eb822141ae802f822ddf41a3ba81729d2e5b436d3940cf1946c8a' and sum(b.count(b'checked_snapshot_emission_bound_v1') for b in source.values())==1)
    require('WorkAuditPending_preserved',b'Err(AError::WorkAuditPending)' in source[PP])
    require('source145_digest_and_manifest',len(source)==145 and roster(source)==read(PRODUCER/'source-manifest.json') and roster(source)['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a')
    hosts={m['retained_path'].removeprefix('host/'):(LOADER/m['retained_path']).read_bytes() for m in support['members']}
    require('unchanged_host11_digest_and_manifest',len(hosts)==11 and roster(hosts)==read(PRODUCER/'host-support-manifest.json') and roster(hosts)['tree_sha256']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2')
    delta=''.join(''.join(difflib.unified_diff(base.get(n,b'').decode().splitlines(True),source[n].decode().splitlines(True),fromfile='funding-source144/'+n,tofile='descriptor-source145/'+n)) for n in [LP,PP,HP])
    require('patch_exactness',delta.encode()==(PRODUCER/'source-delta.patch').read_bytes())
    closure=read(PRODUCER/'build-input-manifest.json');prod=read(PRODUCER/'results.json');compiler=identity(RUSTC)
    require('compiler_live_bytes',compiler==prod['compiler']==closure['tools']['rustc'])
    for item in closure['orchestration']+[closure['tools']['python']]+closure['tools']['SDK_headers']:
        require('live_identity_'+item['path'],identity(Path(item['path']))==item)
    require('host11_separate_from_orchestration_tools',closure['host_support']==roster(hosts) and len(closure['orchestration'])==4 and len(closure['tools']['SDK_headers'])==4 and not any(m['path'].endswith(('prepare.py','run.py','controls.rs','descriptor.rs')) for m in roster(hosts)['members']))
    receipts={}
    for entry in read(PRODUCER/'command-index.json'):
        p=PRODUCER/'commands'/entry['label']/'receipt.json';require('producer_receipt_'+entry['label'],identity(p)==entry['receipt']);r=read(p);receipts[entry['label']]=r
        assert r['exit_code']==0 and r['expectation_met'] and r['owned_group_absent'] and r['child_reaped']
        for kind in ['stdout','stderr']:assert identity(p.parent/kind)==r[kind]
    require('producer_22_commands',len(receipts)==22)
    preimage_review=[]
    for artifact in prod['artifacts_measured_then_removed']:
        label=artifact['label'];p=PRODUCER/'preimages'/label;r=receipts[label];binding=read(p/'binding.json')
        parts=[(p/f).read_bytes() for f in ['manifest.json','argv.bin','environment.bin','compiler-version.txt']]
        manifest=json.loads(parts[0]);assert canonical(manifest)==parts[0] and manifest['distribution']==roster(source) and manifest['host_support']==roster(hosts)
        assert unpack(parts[1])==list(map(os.fsencode,r['argv'])) and parts[1]==packed(r['argv'])
        clean={k:v for k,v in r['environment'].items() if k not in KEYS};assert parts[2]==envpacked(clean) and set(clean)=={'PATH','TMPDIR','CARGO_MANIFEST_DIR'}
        assert parts[3]==(PRODUCER/'rustc-version.txt').read_bytes()
        values=[sha(parts[0]),sha(parts[1]),sha(parts[2]),compiler['sha256'],sha(parts[3])];expected=dict(zip(KEYS,values));assert binding['compile_keys']==expected
        variant=binding['negative_identity_variant']
        if variant=='missing':del expected[KEYS[0]]
        elif variant=='malformed':expected[KEYS[0]]='G'*64
        elif variant=='stale':expected[KEYS[0]]='0'*64
        actual={k:r['environment'][k] for k in KEYS if k in r['environment']};assert expected==actual==binding['actual_compile_identity_keys']
        record=(p/'build-preimage.bin').read_bytes();assert record[:8]==b'MIXLBD01'
        for at,value in [(8,1),(16,512),(24,len(record)),(32,145),(40,11),(80,artifact['bytes'])]:assert struct.unpack_from('<Q',record,at)[0]==value
        assert record[88:152]==b'aarch64-apple-darwin'+bytes(45) and record[344:512]==bytes(168)
        at=512
        for i,part in enumerate(parts):
            assert struct.unpack_from('<Q',record,48+8*i)[0]==len(part) and record[at:at+len(part)]==part and record[152+32*i:184+32*i].hex()==sha(part);at+=len(part)
        assert at==len(record) and record[280:312].hex()==compiler['sha256'] and record[312:344].hex()==artifact['sha256'] and not Path(artifact['path']).exists()
        preimage_review.append({'label':label,'keys_reconstructed':5,'record_sha256':sha(record),'negative_variant':variant,'artifact_bytes':artifact['bytes'],'artifact_executed':artifact['executed']})
    require('twelve_complete_preimages_reconstructed',len(preimage_review)==12)
    for mode in ['debug','optimized']:
        assert b'descriptor_controls=41' in (PRODUCER/'commands'/('pure-'+mode+'-bound-controls')/'stdout').read_bytes()
        for variant in ['missing','malformed','stale']:assert ('identity_negative='+variant).encode() in (PRODUCER/'commands'/('pure-'+mode+'-'+variant+'-controls')/'stdout').read_bytes()
    require('producer_82_pure_and_six_identity_negative_pairs',True)
    history=PRODUCER/'attempt-history';failure=read(history/'pure-scaffold-v1/commands/pure-debug-bound/receipt.json')
    require('failed_history_preserved',failure['exit_code']!=0 and not failure['expectation_met'] and b'too many leading `super`' in (history/'pure-scaffold-v1/commands/pure-debug-bound/stderr').read_bytes() and not read(history/'preparation-ordering-v1/receipt.json')['expectation_met'])
    require('failed_and_final_cleanup_recorded',read(history/'pure-scaffold-v1/postfailure-cleanup.json')['scratch_removed_after_recording'] and read(PRODUCER/'cleanup.json')['owned_scratch_removed'] and not (PRODUCER/'owned-work').exists())
    save(HERE/'custody-and-preimages.json',{'custody':custody,'preimages':preimage_review,'checks':checks,'root_release':identity(RELEASE),'preserved_history':'Path ordering assertion; first pure scaffold pub(super) compile refusal; corrected private module wrapper.'})
    # Fresh independently assembled scaffold, with verbatim real parser/identity body.
    text=source[LP].decode();spec=[('constants','const HEADER:','#[derive(Clone, Copy, Debug, PartialEq, Eq)]'),('errors','#[derive(Clone, Copy, Debug, PartialEq, Eq)]\n#[repr(u8)]','/// All actual File owners'),('views','#[derive(Clone, Copy)]\nstruct Section','struct SessionView'),('parser','fn word(b:','fn parse_session('),('hash','    pub(super) fn hash(','    pub(super) unsafe fn c_string'),('identity','    let embedded = COMPILED.map(','    let build_digest =')]
    fragments={};extraction=[]
    for name,start,end in spec:
        a=text.index(start);b=text.index(end,a);fragments[name]=text[a:b];extraction.append({'name':name,'source_start':a,'bytes':b-a,'sha256':sha(text[a:b].encode())})
    harness='#![allow(dead_code)]\nmod independent {\nuse std::io;\n#[derive(Debug)] struct SwiftValidationFailure;\n'+''.join(fragments[n] for n in ['constants','errors','views','parser'])
    harness+='\nmod platform {use super::*;use std::ffi::c_void;#[link(name="System")] unsafe extern "C" {fn CC_SHA256(data:*const c_void,len:u32,md:*mut u8)->*mut u8;}\n'+fragments['hash']+'}\n'
    harness+='fn checked(build:&[u8])->Result<(),LoaderFailureV1>{let b=parse_build(build)?;let usage=&mut LoaderUsageV1::default();\n'+fragments['identity']+'Ok(())}\n'+(HERE/'cases.rs').read_text()+'\n}\nfn main(){independent::main();}\n'
    (HERE/'derived-harness.rs').write_text(harness);save(HERE/'extraction.json',{'fragments':extraction,'source_sha256':sha(source[LP]),'harness':identity(HERE/'derived-harness.rs'),'type_layout_claim':False,'stub':'Only unrelated SwiftValidationFailure name; no validator/proof/loader/VM/writer linked or executed.'})
    SCRATCH.mkdir();env={'PATH':'/usr/bin:/bin','TMPDIR':str(SCRATCH),'CARGO_MANIFEST_DIR':str(SCRATCH/'vm')};completed=False
    try:
        version=run('rustc-version',[RUSTC,'-vV'],env,10);require('fresh_version_matches_producer',version==(PRODUCER/'rustc-version.txt').read_bytes())
        revision=run('git-revision',['git','rev-parse','HEAD'],env,10).decode().strip()
        ownmanifest={'schema':1,'distribution':roster(source),'host_support':roster(hosts),'orchestration':[identity(HERE/n) for n in ['review.py','cases.rs','derived-harness.rs']],'tools':closure['tools'],'scope':'Independent pure descriptor/identity controls and one real source metadata compile; no real ingress'}
        variants=[('positive',None,None)]+[('stale-'+str(i),i,'0'*64) for i in range(5)]+[('missing',0,None),('malformed',4,'G'*64)]
        def compile_one(label,argv,output,manifest,index=None,value=None):
            parts=[canonical(manifest),packed(argv),envpacked(env),version];values=[sha(parts[0]),sha(parts[1]),sha(parts[2]),compiler['sha256'],sha(parts[3])];keys=dict(zip(KEYS,values));actual=keys.copy()
            if index is not None:
                if value is None:del actual[KEYS[index]]
                else:actual[KEYS[index]]=value
            p=HERE/'preimages'/label;p.mkdir(parents=True)
            for name,data in zip(['manifest.json','argv.bin','environment.bin','compiler-version.txt'],parts):(p/name).write_bytes(data)
            save(p/'keys.json',{'derived_keys':keys,'actual_keys':actual})
            run(label,argv,env|actual);out=output.read_bytes();artifacts.append(identity(output)|{'label':label,'executed':label.startswith('pure-')});record=descriptor(parts,compiler,out);(p/'build-preimage.bin').write_bytes(record);return p/'build-preimage.bin'
        for label,index,value in variants:
            output=SCRATCH/('pure-'+label);argv=[str(RUSTC),'--edition=2021','--target','aarch64-apple-darwin','-C','opt-level=3','-C','overflow-checks=yes','-C','panic=unwind',str(HERE/'derived-harness.rs'),'-o',str(output)]
            record=compile_one('pure-'+label,argv,output,ownmanifest,index,value);mode='positive' if label=='positive' else ('unsupported' if label in ['missing','malformed'] else 'stale')
            result=run('run-'+label,[output,record,mode],env,10);assert (b'independent_pure_controls=' if mode=='positive' else b'independent_identity_refusal=') in result;output.unlink()
        vm=SCRATCH/'vm'
        for name,data in source.items():p=vm/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        require('materialized_source145_exact',roster({str(p.relative_to(vm)):p.read_bytes() for p in vm.rglob('*') if p.is_file()})==roster(source))
        output=SCRATCH/'candidate.rmeta';argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','overflow-checks=yes','-C','panic=unwind','-C','opt-level=0']
        for f in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+f+'"']
        argv+=['--crate-type','rlib',str(vm/'src/lib.rs'),'--emit=metadata='+str(output)]
        compile_one('candidate-metadata',argv,output,ownmanifest);output.unlink();completed=True
        require('compiler_after_all_builds',identity(RUSTC)==compiler)
        require('frozen_producer_unchanged_after_checks',seal(PRODUCER,'5e11885ef1a1189dc10ef8de5b82f4cd969573a8a1130e0a25f146725c23d7ea')['verified_members']==208)
        save(HERE/'results.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'accepted for exact private descriptor preparation only','git_revision_context':revision,'source_tree_sha256':roster(source)['tree_sha256'],'source_members':145,'host_support_tree_sha256':roster(hosts)['tree_sha256'],'host_support_members':11,'checks':checks,'independent_pure_builds':8,'independent_pure_executions':8,'independent_stale_key_positions':[0,1,2,3,4],'independent_missing_and_malformed':True,'independent_metadata_builds':1,'artifacts_measured_then_removed':artifacts,'compiler':compiler,'python_version':sys.version,'python':identity(Path(sys.executable).resolve()),'platform':platform.platform(),'limitations':['Extracted pure identity body does not qualify real loader ingress, actual output digest/extent, real typelayout or writer.','One independent production metadata compile; producer four debug/optimized production/unit compiles reviewed as custody evidence.','H/bootstrap, phase-retention/work-admission/final composition, source/storage/work/host pre-ingress admission and real caller qualification pending.','WorkAuditPending remains; emission helper unused.','Native/UI/capture/simulator/emulator/device runtime checks paused and unrun; no global process inventories.','No canonical integration, immutable FieldLog package, publication, OTA/store/customer/operations or GA qualification.'],'actual_loader_ingress_executed':False,'engine_VM_guest_writer_executed':False,'GA_verified':False})
    finally:
        groups_absent=all(read(Path(e['receipt']['path']))['owned_group_absent'] for e in commands)
        if completed and groups_absent:shutil.rmtree(SCRATCH)
        save(HERE/'cleanup.json',{'completed':completed,'recorded_owned_groups_absent':groups_absent,'owned_scratch_removed':not SCRATCH.exists(),'native_capture_started':False,'global_process_inventory':False,'scope':'Only direct owned subprocess groups and this packet owned-work directory.'})
    assert completed
if __name__=='__main__':main()
