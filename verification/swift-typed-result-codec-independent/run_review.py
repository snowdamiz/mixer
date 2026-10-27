"""Independent bounded actual-source review; never writes the frozen candidate."""
from pathlib import Path
import datetime, hashlib, json, os, platform, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-typed-result-codec-implementation'
SOURCE=PRODUCER/'source/vm'
BASELINE=ROOT/'verification/swift-initial-profile-construction-implementation'
CONTRACT=ROOT/'verification/swift-retained-profile-real-binding-contract-review'
SELECTION=ROOT/'verification/swift-semantic-adapter-root-review/typed-result-codec-implementation-selection.json'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
PREFIX='experimental_swift_reactor::diagnostic_result_v1::'
EXPECTED_SEAL='4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86'
def sha(data): return hashlib.sha256(data).hexdigest()
def identity(path):
    path=Path(path); b=path.read_bytes(); return {'path':str(path),'bytes':len(b),'sha256':sha(b)}
def write(name,data): (HERE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def manifest(root):
    members=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
    return {'member_count':len(members),'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
def closed_packet(root,expected_sha,count,total):
    seal=root/'seal.json'; assert sha(seal.read_bytes())==expected_sha
    frozen=json.loads(seal.read_text()); members=[]
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file() and p!=seal:
            b=p.read_bytes(); members.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':sha(b)})
    assert members==frozen['members']; assert len(members)==count; assert sum(m['bytes'] for m in members)==total
    return {'path':str(root.relative_to(ROOT)),'seal_sha256':expected_sha,'members':count,'bytes':total,'exact_file_set':True,'all_member_identities_match':True}
def verify_inputs():
    candidate=closed_packet(PRODUCER,EXPECTED_SEAL,235,19708478)
    review=closed_packet(CONTRACT,'2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e',22,48596)
    assert sha(SELECTION.read_bytes())=='243a10a54d2887e83497190df56eeb1a74763c489eedfd0222dd8665cc034d55'
    assert json.loads((PRODUCER/'selection.json').read_text())==json.loads(SELECTION.read_text())
    baseline_seal=BASELINE/'seal.json'; assert sha(baseline_seal.read_bytes())=='50d1c32174ee4cbcade6095039261ea0ff8eed05680322bfb59b5de0dd4cd8b1'
    accepted={m['path']:m for m in json.loads(baseline_seal.read_text())['members']}
    old=json.loads((PRODUCER/'baseline-source-manifest-attempt-12.json').read_text())
    source=manifest(SOURCE); assert source['member_count']==142
    retained=json.loads((PRODUCER/'source-manifest.json').read_text())
    assert source['members']==retained['members']; assert source['tree_sha256']==retained['tree_sha256']=='58a90a1cec00fd3ffbe4d8bee90476f6e136114dbe3d506da8ab4bbd035b8ecd'
    prior={m['path']:m for m in old['members']}; current={m['path']:m for m in source['members']}
    assert len(prior)==140
    for p,m in prior.items():
        seal_m=accepted['source/vm/'+p]; b=(BASELINE/'source/vm'/p).read_bytes()
        assert len(b)==m['bytes']==seal_m['bytes'] and sha(b)==m['sha256']==seal_m['sha256']
    added=sorted(set(current)-set(prior)); changed=sorted(p for p in prior if current[p]!=prior[p])
    assert added==['src/experimental_swift_reactor/diagnostic_result_v1.rs','src/experimental_swift_reactor/diagnostic_result_v1_tests.rs']
    assert changed==['src/experimental_swift_reactor/mod.rs']
    delta=b'\n// Pure unverified typed-result data; no public export or runtime route.\nmod diagnostic_result_v1;\n'
    p='src/experimental_swift_reactor/mod.rs'
    assert (SOURCE/p).read_bytes()==(BASELINE/'source/vm'/p).read_bytes()+delta
    support=json.loads((PRODUCER/'baseline-host-support-manifest.json').read_text())['members']; assert len(support)==11
    assert len([p for p in (PRODUCER/'host').rglob('*') if p.is_file()])==11
    for m in support:
        path=m['retained_path']; b=(PRODUCER/path).read_bytes(); s=accepted[path]
        assert sha(b)==m['sha256']==s['sha256'] and len(b)==m['bytes']==s['bytes']
    commands=json.loads((PRODUCER/'command-receipts.json').read_text()); assert len(commands)==28
    for c in commands:
        assert c['expectation_met'] and c['terminally_waited'] and c['killed_for'] is None
        for stream in ['stdout','stderr']: assert identity(c[stream]['path'])==c[stream]
        if c['expected_diagnostic']: assert c['exit_code']!=0 and c['expected_diagnostic'] in Path(c['stderr']['path']).read_text()
        else: assert c['exit_code']==0
    for mode in ['debug','optimized']:
        assert sum(c['label']==f'compile-contract-{mode}-positive' and c['exit_code']==0 for c in commands)==1
        assert sum(c['label'].startswith(f'compile-contract-{mode}-') and c['expected_diagnostic'] is not None for c in commands)==6
    variants=json.loads((PRODUCER/'compile-variants.json').read_text()); assert len(variants)==14
    for v in variants:
        assert identity(v['fixture']['path'])==v['fixture']; assert v['source_distribution_tree_sha256']==source['tree_sha256']
    return {'candidate':candidate,'prior_contract_review':review,'root_selection':identity(SELECTION),
        'candidate_source_tree_sha256':source['tree_sha256'],'baseline_source_members_verified_against_accepted_seal':140,
        'unchanged_host_support_members_verified_against_accepted_seal':11,'added_distribution_paths':added,
        'changed_existing_paths':changed,'exact_private_module_append':delta.decode(),'producer_commands_reviewed':28,
        'producer_compile_variants_reviewed':14}
def main():
    before=verify_inputs(); write('input-custody-before.json',before)
    logs=HERE/'logs'; logs.mkdir(exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='review-host-',dir=HERE))
    env=os.environ.copy(); env['TMPDIR']=str(scratch)
    commands=[]; artifacts=[]; variants=[]
    def run(label,args,expected=None):
        out=logs/(label+'.stdout'); err=logs/(label+'.stderr'); start=time.monotonic()
        with out.open('wb') as stdout,err.open('wb') as stderr:
            child=subprocess.Popen([str(a) for a in args],cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
            killed=None
            while True:
                try: code=child.wait(timeout=.05); break
                except subprocess.TimeoutExpired:
                    if time.monotonic()-start>60: killed='time'
                    if out.stat().st_size+err.stat().st_size>1024*1024: killed='output'
                    if killed: child.kill(); child.wait(); code=124; break
        stderr=err.read_text(errors='replace'); stdout=out.read_text(errors='replace')
        good=code==0 if expected is None else code!=0 and expected in stderr
        commands.append({'label':label,'argv':[str(a) for a in args],'cwd':str(ROOT),'exit_code':code,'expected_diagnostic':expected,
            'expectation_met':good,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'output_byte_limit':1024*1024,
            'killed_for':killed,'terminally_waited':True,'stdout':identity(out),'stderr':identity(err)})
        write('command-receipts.json',commands); print(label+': '+('pass' if good else 'FAIL'),flush=True)
        assert good,(label,stderr[-4000:]); return stdout
    def flags(opt):
        a=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind']
        for feature in FEATURES:a+=['--cfg','feature="'+feature+'"']
        return a
    try:
        revision=run('revision',['git','rev-parse','HEAD']).strip(); rustc_version=run('rustc-version',[RUSTC,'-vV']); cfg=run('target-cfg',[RUSTC,'--print','cfg','--target','aarch64-apple-darwin'])
        variant=scratch/'source'; shutil.copytree(SOURCE,variant)
        module=variant/'src/experimental_swift_reactor/diagnostic_result_v1.rs'
        delta='\n#[cfg(test)] mod independent_review_controls { include!(env!("MIXER_INDEPENDENT_CODEC_CONTROLS")); }\n'
        module.write_bytes(module.read_bytes()+delta.encode()); env['MIXER_INDEPENDENT_CODEC_CONTROLS']=str(HERE/'independent_controls.rs')
        env['CARGO_MANIFEST_DIR']=str(variant)
        variant_manifest=manifest(variant)
        variants.append({'kind':'independent-behavior-controls','source_tree_sha256':before['candidate_source_tree_sha256'],'variant_tree_sha256':variant_manifest['tree_sha256'],
            'append_path':'src/experimental_swift_reactor/diagnostic_result_v1.rs','append':delta,'included_controls':identity(HERE/'independent_controls.rs')})
        for mode,opt in [('debug','0'),('optimized','3')]:
            binary=scratch/('unit-'+mode); run('compile-'+mode,flags(opt)+['--test',variant/'src/lib.rs','-o',binary]); artifacts.append(identity(binary))
            listing=run('list-'+mode,[binary,PREFIX,'--list'])
            names=[line.split(': test')[0] for line in listing.splitlines() if line.endswith(': test')]
            original=[n for n in names if '::tests::' in n]; independent=[n for n in names if '::independent_review_controls::' in n]
            assert len(original)==27 and len(independent)==7,(len(original),len(independent))
            replay=run('producer-replay-'+mode,[binary,PREFIX+'tests::','--nocapture','--test-threads=1']); assert '27 passed; 0 failed' in replay
            fresh=run('independent-controls-'+mode,[binary,PREFIX+'independent_review_controls::','--nocapture','--test-threads=1']); assert '7 passed; 0 failed' in fresh
            inventory=run('prior-layout-inventory-'+mode,[binary,'--exact','experimental_swift_reactor::cache::initial_profile_v1::tests::selected_layout_and_places','--nocapture','--test-threads=1'])
            rows=[{'id':int(p[1]),'bytes':int(p[3]),'alignment':int(p[4])} for l in inventory.splitlines() if (p:=l.split('\t')) and p[0]=='TYPE']
            accepted={m['path']:m for m in json.loads((BASELINE/'seal.json').read_text())['members']}; expected_path=BASELINE/'actual-layout-comparison-attempt-11.json'
            assert sha(expected_path.read_bytes())==accepted[expected_path.name]['sha256']
            assert rows==json.loads(expected_path.read_text())['unit-'+mode]['rows'] and len(rows)==165
            codec_layouts=[l[l.index('CODEC_DATA\t'):].split('\t')[1:] for l in replay.splitlines() if 'CODEC_DATA\t' in l]
            assert codec_layouts==json.loads((PRODUCER/'data-layouts.json').read_text())[mode]
            write('layouts-'+mode+'.json',{'codec_data_types':codec_layouts,'original_owner_types':165,'original_inventory_matches':True,'original_inventory_covers_codec_storage':False,'operational_storage_accepted':False})
            env['CARGO_MANIFEST_DIR']=str(SOURCE); prod=scratch/('ordinary-'+mode+'.rlib')
            run('ordinary-production-'+mode,flags(opt)+['--crate-type','rlib',SOURCE/'src/lib.rs','-o',prod]); artifacts.append(identity(prod)); env['CARGO_MANIFEST_DIR']=str(variant)
        shutil.rmtree(variant)
        control=scratch/'compile-source';shutil.copytree(SOURCE,control)
        p=control/'src/experimental_swift_reactor/mod.rs'; delta='\n#[cfg(test)] mod typed_result_compile_contract { include!(env!("MIXER_CODEC_COMPILE_CASE")); }\n'
        p.write_bytes(p.read_bytes()+delta.encode());env['CARGO_MANIFEST_DIR']=str(control)
        control_digest=manifest(control)['tree_sha256']
        assert all(v['variant_tree_sha256']==control_digest for v in json.loads((PRODUCER/'compile-variants.json').read_text()))
        for mode,opt in [('debug','0'),('optimized','3')]:
            for name,expected in [('positive',None),('code_escape','lifetime may not live long enough'),('view_escape','lifetime may not live long enough'),('input_mutation','E0502'),('private_view_fields','E0616'),('private_scalar_fields','E0616'),('authoritative_failure','lifetime may not live long enough')]:
                fixture=PRODUCER/'compile_cases'/(name+'.rs');env['MIXER_CODEC_COMPILE_CASE']=str(fixture)
                variants.append({'kind':'frozen-compile-contract','mode':mode,'source_tree_sha256':before['candidate_source_tree_sha256'],'variant_tree_sha256':control_digest,'append_path':'src/experimental_swift_reactor/mod.rs','append':delta,'fixture':identity(fixture),'expected_diagnostic':expected})
                run('compile-contract-'+mode+'-'+name,flags(opt)+['--test','--emit=metadata',control/'src/lib.rs','-o',scratch/'case.rmeta'],expected)
        write('compile-variants.json',variants)
    finally:
        shutil.rmtree(scratch)
        write('cleanup.json',{'scratch_path':str(scratch),'scratch_removed':not scratch.exists(),'all_children_terminally_waited':all(c['terminally_waited'] for c in commands),
            'native_simulator_emulator_UI_capture_or_process_inventory_used':False,'frozen_packet_writes':False})
    after=verify_inputs(); assert before==after; write('input-custody-after.json',after)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'independent-actual-source-host-review-controls-pass',
        'reviewed_candidate':before['candidate'],'source_tree_sha256':before['candidate_source_tree_sha256'],'git_revision_context':revision,
        'rustc':identity(RUSTC),'rustc_version':rustc_version,'target_cfg':cfg,'python':identity(Path(sys.executable).resolve()),'python_version':sys.version,
        'platform':platform.platform(),'target':'aarch64-apple-darwin','host_usize_bits':64,'features':FEATURES,'command_count':len(commands),
        'producer_methods_replayed_each_mode':27,'independent_methods_each_mode':7,'positive_compile_controls_each_mode':1,'negative_compile_controls_each_mode':6,
        'ordinary_production_compiles_each_mode':1,'prior_owner_layouts_each_mode':165,'prior_owner_inventory_covers_codec_storage':False,
        'artifacts_compiled_and_removed':artifacts,'source_and_packets_unchanged_after':True,
        'operational_reservation_provenance_integration_native_FieldLog_OTA_store_customer_GA_accepted':False}
    write('receipt.json',receipt);print(json.dumps({'status':receipt['status'],'command_count':len(commands),'scratch_removed':True}))
if __name__=='__main__':main()
