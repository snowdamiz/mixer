"""Bounded actual-module codec tests. No predecessor runner, native runtime or broad replay."""
from pathlib import Path
import datetime,hashlib,json,os,platform,re,shutil,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SOURCE=HERE/'source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
PREFIX='experimental_swift_reactor::diagnostic_result_v1::tests::'
def sha(b):return hashlib.sha256(b).hexdigest()
def identity(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def manifest(p):
 members=[{'path':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in sorted(p.rglob('*')) if f.is_file()]
 return {'schema':1,'member_count':len(members),'members':members,'tree_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def main():
 source=manifest(SOURCE);assert source['member_count']==142
 baseline=json.loads((HERE/'baseline-source-manifest-attempt-12.json').read_text());old={m['path']:m for m in baseline['members']}
 actual={m['path']:m for m in source['members']}
 assert set(actual)-set(old)=={'src/experimental_swift_reactor/diagnostic_result_v1.rs','src/experimental_swift_reactor/diagnostic_result_v1_tests.rs'}
 assert [k for k in old if old[k]!=actual[k]]==['src/experimental_swift_reactor/mod.rs']
 base_mod=(ROOT/'verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/mod.rs').read_bytes()
 assert (SOURCE/'src/experimental_swift_reactor/mod.rs').read_bytes()==base_mod+b'\n// Pure unverified typed-result data; no public export or runtime route.\nmod diagnostic_result_v1;\n'
 support=json.loads((HERE/'baseline-host-support-manifest.json').read_text())
 for m in support['members']:
  b=(HERE/m['retained_path']).read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256']
 assert len([p for p in (HERE/'host').rglob('*') if p.is_file()])==11
 write(HERE/'source-manifest.json',source)
 scratch=Path(tempfile.mkdtemp(prefix='codec-host-',dir=HERE));logs=HERE/'logs';logs.mkdir(exist_ok=True)
 env=os.environ.copy();env['CARGO_MANIFEST_DIR']=str(SOURCE);env['TMPDIR']=str(scratch)
 receipts=[];binaries=[];layouts={};variants=[]
 def run(label,args,expected=None):
  start=time.monotonic();out=logs/(label+'.stdout');err=logs/(label+'.stderr')
  with out.open('wb') as o,err.open('wb') as e:
   child=subprocess.Popen([str(x) for x in args],cwd=ROOT,env=env,stdout=o,stderr=e);killed=None
   while True:
    try:code=child.wait(timeout=.05);break
    except subprocess.TimeoutExpired:
     if time.monotonic()-start>60:killed='time'
     if out.stat().st_size+err.stat().st_size>1024*1024:killed='output'
     if killed:child.kill();child.wait();code=124;break
  stderr=err.read_text(errors='replace');stdout=out.read_text(errors='replace')
  success=(code==0) if expected is None else code!=0 and expected in stderr
  receipt={'label':label,'argv':[str(x) for x in args],'cwd':str(ROOT),'exit_code':code,'expected_diagnostic':expected,'expectation_met':success,'timeout_seconds':60,'output_byte_limit':1024*1024,'killed_for':killed,'elapsed_seconds':time.monotonic()-start,'terminally_waited':True,'stdout':identity(out),'stderr':identity(err)}
  receipts.append(receipt);write(HERE/'command-receipts.json',receipts)
  print(label+': '+('pass' if success else 'FAIL'),flush=True)
  assert success,(label,stderr[-3000:]);return stdout
 def flags(opt):
  args=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','-C','opt-level='+opt,'-C','overflow-checks=yes','-C','panic=unwind']
  for f in FEATURES:args+=['--cfg','feature="'+f+'"']
  return args
 try:
  revision=run('revision',['git','rev-parse','HEAD']).strip();rust_version=run('rustc-version',[RUSTC,'-vV']);rustfmt_version=run('rustfmt-version',[RUSTC.parent/'rustfmt','-V'])
  target_cfg=run('target-cfg',[RUSTC,'--print','cfg','--target','aarch64-apple-darwin'])
  for mode,opt in [('debug','0'),('optimized','3')]:
   binary=scratch/('unit-'+mode)
   run('compile-'+mode,flags(opt)+['--test',SOURCE/'src/lib.rs','-o',binary]);binaries.append(identity(binary))
   listed=run('list-'+mode,[binary,PREFIX,'--list'])
   names=[line.split(': test')[0] for line in listed.splitlines() if line.endswith(': test')];assert len(names)==27,len(names)
   result=run('codec-'+mode,[binary,PREFIX,'--nocapture','--test-threads=1']);assert '27 passed; 0 failed' in result
   layouts[mode]=[line[line.index('CODEC_DATA\t'):].split('\t')[1:] for line in result.splitlines() if 'CODEC_DATA\t' in line]
   assert len(layouts[mode])==12
   # A single existing host-only layout method confirms old owner layouts separately.
   observed=run('original-layout-'+mode,[binary,'--exact','experimental_swift_reactor::cache::initial_profile_v1::tests::selected_layout_and_places','--nocapture','--test-threads=1'])
   rows=[{'id':int(p[1]),'bytes':int(p[3]),'alignment':int(p[4])} for line in observed.splitlines() if (p:=line.split('\t')) and p[0]=='TYPE']
   frozen=ROOT/'verification/swift-initial-profile-construction-implementation'
   comparison=frozen/'actual-layout-comparison-attempt-11.json';sealed={m['path']:m for m in json.loads((frozen/'seal.json').read_text())['members']}
   assert sha(comparison.read_bytes())==sealed[comparison.name]['sha256']
   expected=json.loads(comparison.read_text())['unit-'+mode]['rows'];assert len(rows)==165 and rows==expected
   layouts[mode+'-original-owner-types']={'rows':rows,'matches_frozen_sealed_expected':True,'covers_codec_storage':False}
   artifact=scratch/('ordinary-'+mode+'.rlib')
   run('ordinary-production-'+mode,flags(opt)+['--crate-type','rlib',SOURCE/'src/lib.rs','-o',artifact]);binaries.append(identity(artifact))
   for name,expected_diagnostic in [('positive',None),('code_escape','lifetime may not live long enough'),('view_escape','lifetime may not live long enough'),('input_mutation','E0502'),('private_view_fields','E0616'),('private_scalar_fields','E0616'),('authoritative_failure','lifetime may not live long enough')]:
    variant=scratch/'variant';shutil.copytree(SOURCE,variant)
    path=variant/'src/experimental_swift_reactor/mod.rs'
    delta=b'\n#[cfg(test)] mod typed_result_compile_contract { include!(env!("MIXER_CODEC_COMPILE_CASE")); }\n'
    path.write_bytes(path.read_bytes()+delta);fixture=HERE/'compile_cases'/(name+'.rs');env['MIXER_CODEC_COMPILE_CASE']=str(fixture)
    env['CARGO_MANIFEST_DIR']=str(variant)
    variant_manifest=manifest(variant);assert variant_manifest['member_count']==142
    variants.append({'mode':mode,'fixture':identity(fixture),'source_distribution_tree_sha256':source['tree_sha256'],'variant_tree_sha256':variant_manifest['tree_sha256'],'test_only_append_path':'src/experimental_swift_reactor/mod.rs','test_only_append_bytes':delta.decode(),'expected_diagnostic':expected_diagnostic})
    run('compile-contract-'+mode+'-'+name,flags(opt)+['--test','--emit=metadata',variant/'src/lib.rs','-o',scratch/'case.rmeta'],expected_diagnostic)
    shutil.rmtree(variant);env['CARGO_MANIFEST_DIR']=str(SOURCE)
 finally:
  shutil.rmtree(scratch)
  write(HERE/'compile-variants.json',variants);write(HERE/'data-layouts.json',layouts)
  write(HERE/'cleanup.json',{'scratch_removed':not scratch.exists(),'terminally_waited_all_children':all(r['terminally_waited'] for r in receipts),'native_UI_capture_process_inventory_used':False,'simulator_emulator_or_native_runtime_started':False})
 assert manifest(SOURCE)==source
 for m in support['members']:assert sha((HERE/m['retained_path']).read_bytes())==m['sha256']
 report={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'actual-private-codec-host-controls-pass','git_revision_context':revision,'source_manifest_sha256':sha((HERE/'source-manifest.json').read_bytes()),'source_tree_sha256':source['tree_sha256'],'distribution_members':142,'unchanged_host_support_members':11,'commands':len(receipts),'methods_each_mode':27,'full_result_roundtrip_combinations':54,'positive_compile_controls_each_mode':1,'negative_compile_controls_each_mode':6,'original_owner_layouts_each_mode':165,'new_codec_layouts_separate':True,'original_layout_inventory_covers_codec_storage':False,'ordinary_production_compile_modes':['debug','optimized'],'compiler':identity(RUSTC),'rustc_version':rust_version,'rustfmt_version':rustfmt_version,'target_cfg':target_cfg,'runner':identity(Path(__file__)),'python':identity(Path(sys.executable).resolve()),'python_version':sys.version,'platform':platform.platform(),'features':FEATURES,'target':'aarch64-apple-darwin','host_usize_bits':64,'binary_identities_executed_or_compiled_then_removed':binaries,'scope':'pure codec data only; no operational reservation or provenance authority','producer_provenance_semantic_replay_FieldLog_native_OTA_GA_accepted':False,'no_canonical_index_commit_push_or_publication':True}
 write(HERE/'receipt.json',report);print(json.dumps({k:report[k] for k in ['status','commands','methods_each_mode','source_tree_sha256']}))
if __name__=='__main__':main()
