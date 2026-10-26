#!/usr/bin/env python3
"""Only build/run the finite data-only host layout executable in two modes."""
from pathlib import Path
import datetime, hashlib, json, os, platform, shutil, subprocess, sys, tempfile, time

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def run(argv,folder,env=None,timeout=60,cwd=ROOT):
    folder.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    r=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,capture_output=True,timeout=timeout)
    (folder/'stdout').write_bytes(r.stdout);(folder/'stderr').write_bytes(r.stderr)
    receipt={'argv':[str(x) for x in argv],'cwd':str(cwd),'exit_code':r.returncode,
             'elapsed_seconds':time.monotonic()-start,'stdout_sha256':sha(folder/'stdout'),
             'stderr_sha256':sha(folder/'stderr')}
    write(folder/'receipt.json',receipt)
    return r
def main():
    at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    commands=OUT/'commands';manifest=json.loads((OUT/'probe-source-manifest.json').read_text())
    for m in manifest['members']:
        p=OUT/'source/vm'/m['path'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256']
    environment={'at':at,'python':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable)),
      'platform':platform.platform(),'rustc_executable':str(TOOL/'rustc'),'rustc_sha256':sha(TOOL/'rustc'),
      'cargo_executable':str(TOOL/'cargo'),'cargo_sha256':sha(TOOL/'cargo'),
      'runner_sha256':sha(OUT/'run_layout.py'),'preparer_sha256':sha(OUT/'prepare_packet.py'),
      'protocol_model_sha256':sha(OUT/'protocol-types.rs'),
      'probe_source_tree_sha256':manifest['tree_sha256'],'native_UI_capture_or_process_inventory':False}
    for name,argv in [('rustc-vV',[TOOL/'rustc','-vV']),('cargo-version',[TOOL/'cargo','--version']),
      ('target-cfg',[TOOL/'rustc','--print','cfg','--target','aarch64-apple-darwin']),
      ('target-features',[TOOL/'rustc','--print','target-features','--target','aarch64-apple-darwin']),
      ('head-context',['git','rev-parse','HEAD'])]:
        r=run(argv,commands/name);environment[name]={'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace')}
    scratch=Path(tempfile.mkdtemp(prefix='initial-profile-layout-',dir=OUT))
    environment['owned_scratch']=str(scratch);results={};okay=True
    try:
        env=os.environ.copy();env['RUSTC']=str(TOOL/'rustc');env['PATH']=str(TOOL)+':'+env.get('PATH','')
        env['CARGO_TARGET_DIR']=str(scratch/'target');env['TMPDIR']=str(scratch/'tmp');Path(env['TMPDIR']).mkdir()
        env['CARGO_HOME']=str(scratch/'cargo-home')
        target_source=OUT/'layout-target.rs'
        r=run([TOOL/'rustc','--crate-type','lib','--crate-name','initial_profile_target',
          '--target','aarch64-apple-darwin','--emit=llvm-ir','-o','-',target_source],commands/'target-data-layout',env=env)
        assert r.returncode==0
        environment['target_data_layout']=[s for s in r.stdout.decode().splitlines() if s.startswith('target datalayout') or s.startswith('target triple')]
        environment['target_data_layout_source_sha256']=sha(target_source)
        flags='--cfg mixer_initial_profile_layout_probe --check-cfg cfg(mixer_initial_profile_layout_probe)'
        env['RUSTFLAGS']=flags
        config_keys={'RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_ENCODED_RUSTFLAGS',
          'CARGO_BUILD_RUSTFLAGS','CARGO_TARGET_AARCH64_APPLE_DARWIN_RUSTFLAGS','MACOSX_DEPLOYMENT_TARGET',
          'SDKROOT','CARGO_INCREMENTAL','CARGO_BUILD_TARGET','CARGO_TARGET_DIR','CARGO_HOME','TMPDIR'}
        environment['compiler_environment']={k:v for k,v in env.items() if k in config_keys or k.startswith('CARGO_PROFILE_')}
        for mode in ['debug','release']:
            argv=[TOOL/'cargo','build','--verbose','--offline','--locked','--manifest-path',OUT/'source/vm/Cargo.toml',
                  '--target','aarch64-apple-darwin','--features','experimental-swift-reactor,experimental-function-cache',
                  '--bin','initial-profile-layout-probe']
            if mode=='release':argv+=['--release']
            r=run(argv,commands/f'{mode}-build',env=env,timeout=60)
            results[mode]={'build_exit':r.returncode,'RUSTFLAGS':flags,'features':'experimental-swift-reactor,experimental-function-cache'}
            if r.returncode:
                okay=False;continue
            binary=scratch/'target/aarch64-apple-darwin'/mode/'initial-profile-layout-probe'
            results[mode]['binary_sha256']=sha(binary);results[mode]['binary_bytes']=binary.stat().st_size
            r=run([binary],commands/f'{mode}-probe',env=env,timeout=10)
            results[mode]['probe_exit']=r.returncode
            rows=[];values={}
            for line in r.stdout.decode().splitlines():
                parts=line.split('\t')
                if parts[0]=='TYPE':rows.append({'id':int(parts[1]),'type':parts[2],'bytes':int(parts[3]),'alignment':int(parts[4])})
                elif parts[0]=='VALUE':values[parts[1]]=int(parts[2])
            index=json.loads((OUT/'local-layout-type-index.json').read_text());assert len(rows)==index['entry_count']
            assert [{'id':m['id'],'type':m['type']} for m in rows]==index['types']
            results[mode]['types']=rows;results[mode]['derived_layout_values']=values
            okay=okay and r.returncode==0
    finally:
        shutil.rmtree(scratch)
        environment['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':True,
          'compiler_products_retained':False,'retained_inputs_sources_logs_are_review_evidence':True,
          'no_native_instance_started':True}
        write(OUT/'environment.json',environment)
        write(OUT/'layout-measurements.json',{'schema':1,'scope':'Local data-only exact-source host layout proposal; no product implementation or combined budget proof',
          'modes':results,'probe_source_tree_sha256':manifest['tree_sha256'],'all_selected_builds_and_layout_probes_passed':okay})
    if not okay:raise SystemExit(1)
    assert results['debug']['types']==results['release']['types']
    assert results['debug']['derived_layout_values']==results['release']['derived_layout_values']
    write(OUT/'local-structure-proposal.json',{'schema':1,'selected_by_root':False,
      'producer_to_implement':'cache::initial_profile_v1::selected::selected_initial_profile_v1 -> &\'static SelectedInitialProfileV1; sole literal static SELECTED_INITIAL_PROFILE_V1',
      'budget_input':'inputs/root/selected-host-budget.json',
      'layout_source':'layout-measurements.json; literal constants for later selection, never freshly derived expected values',
      'fixed_fields':{'schema':1,'entries':len(results['debug']['types']),'word_bytes':8,'little_endian':1,
       'header_bytes':512,'row_bytes':32,'rows':80000,'header_words':16,'digest_slots':8,'digest_bytes':32,
       'trailing_zero_bytes':128,'outcome_variant_schema':1,'header_error_schema':1,'selected_slots_max':64,'selected_pins':64},
      'derived_fields':results['debug']['derived_layout_values'],'type_layout':results['debug']['types'],
      'compiler_target_cfg_and_source_binding':'External environment.json, probe-source-manifest.json and command receipts; not inferred in product helper',
      'pending':'Actual implementation must remeasure complete new types, source places and call paths; any changed layout requires new reviewed constants and receipt'})
    print(f'PASS: debug/release finite data-only host probes; {len(results["debug"]["types"])} types each; scratch removed')
if __name__=='__main__':main()
