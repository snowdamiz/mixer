#!/usr/bin/env python3
"""Two fresh exact-type metadata builds; never constructs a runtime owner."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile

HERE=Path(__file__).resolve().parent
PROD=HERE.parent/'swift-active-frames-implementation'
FREEZE=PROD/'source-freeze/20261024T045840237261Z'
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT=HERE/'layout-results'/STAMP
BUILD=HERE/'build'/('layouts-'+STAMP)
OUT.mkdir(parents=True);BUILD.mkdir(parents=True);(OUT/'inputs').mkdir()
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(path):return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
for p in [HERE/'collect_layouts.py',PROD/'implementation-inventory-schema.json',PROD/'frozen-inventory-schema.json',FREEZE/'candidate-source.tar.gz',FREEZE/'candidate-manifest.json',FREEZE/'freeze.json']:
    shutil.copyfile(p,OUT/'inputs'/p.name)
rows=[]
for name,classes in [('frozen-inventory-schema.json',{'permanent':'PermanentPositions','active':'ActivePositions'}),('implementation-inventory-schema.json',{'permanent':'ImplementationPermanentPositions','active':'ImplementationActivePositions'})]:
    for row in json.loads((OUT/'inputs'/name).read_text()):rows.append(dict(row,ownerClass=classes[row['envelope']]))
code=['pub(crate) fn independent_layout_probe(){']
for cls in ['PermanentPositions','ActivePositions','ImplementationPermanentPositions','ImplementationActivePositions']:
    code.append(f'println!("AFI_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
for row in rows:
    line=f'println!("AFI_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({row["ownerClass"]},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());'
    code.append('#[cfg(test)] {'+line+'}' if row.get('config')=='unit' else line)
code+=['println!("AFI_TOTAL {} {} {} {} {} {}",PERMANENT_BYTES,ACTIVE_BYTES,FRAME_OPERATION_BYTES.unwrap(),value_operations::VALUE_OPERATION_BYTES.unwrap(),size_of::<SwiftExecutionState>(),std::mem::align_of::<SwiftExecutionState>());','}', '#[cfg(test)] #[test] fn independent_accounting_layout_unit(){independent_layout_probe();}']
(OUT/'inputs/layout-probe.rs').write_text('\n'.join(code)+'\n')
commands=[];binaries=[];layouts=[];status='failed-layout-collection'
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTC_BOOTSTRAP',None);env.pop('RUSTFLAGS',None)
def run(name,argv,cwd,target=None,closure=None):
    if closure is not None:assert manifest(cwd)==closure
    used=dict(env)
    if target:used['CARGO_TARGET_DIR']=str(target)
    result=subprocess.run(argv,cwd=cwd,env=used,capture_output=True,timeout=1200)
    for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(result,stream))
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,exitCode=result.returncode,sourceTreeSHA256=hashlib.sha256(enc(closure)).hexdigest() if closure else None,stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))))
    if closure is not None:assert manifest(cwd)==closure
    print(name,result.returncode,flush=True)
    assert result.returncode==0,result.stderr.decode(errors='replace')[-5000:]
    return result.stdout.decode(errors='replace')
try:
    run('rustc-version',['rustc','-vV'],HERE);run('cargo-version',['cargo','-V'],HERE)
    for label,unit,flags in [('swift-debug-unit',True,['--features','experimental-swift-reactor']),('all-release-production',False,['--all-features','--release'])]:
        dest=BUILD/label
        with tarfile.open(OUT/'inputs/candidate-source.tar.gz') as a:a.extractall(dest,filter='data')
        vm=dest/'vm';assert manifest(vm)==json.loads((OUT/'inputs/candidate-manifest.json').read_text())
        frame=vm/'src/experimental_swift_reactor/frame_operations.rs';frame.write_text(frame.read_text()+'\n'+(OUT/'inputs/layout-probe.rs').read_text())
        if not unit:
            module=vm/'src/experimental_swift_reactor/mod.rs';module.write_text(module.read_text()+'\npub(crate) fn independent_frame_layout_route(){execution::frame_operations::independent_layout_probe();}\n')
            lib=vm/'src/lib.rs';lib.write_text(lib.read_text()+'\npub fn independent_frame_accounting_layout(){experimental_swift_reactor::independent_frame_layout_route();}\n')
            (vm/'src/bin').mkdir(exist_ok=True);(vm/'src/bin/independent_frame_layout.rs').write_text('fn main(){mixer_vm::independent_frame_accounting_layout();}\n')
        closure=manifest(vm);(OUT/(label+'-manifest.json')).write_bytes(enc(closure))
        with tarfile.open(OUT/(label+'-source.tar.gz'),'w:gz') as a:
            for name in closure:a.add(vm/name,arcname='vm/'+name,recursive=False)
        target=BUILD/(label+'-target')
        argv=['cargo','test','--lib','--no-run'] if unit else ['cargo','build','--bin','independent_frame_layout']
        output=run(label+'-build',[*argv,'--locked','--offline','--message-format=json',*flags],vm,target,closure)
        artifacts=[json.loads(line) for line in output.splitlines() if line.startswith('{')]
        executables=[Path(o['executable']) for o in artifacts if o.get('reason')=='compiler-artifact' and o.get('executable') and (o.get('profile',{}).get('test') if unit else o['target']['name']=='independent_frame_layout')]
        assert len(executables)==1
        binary=executables[0]
        output=run(label+'-metadata',[str(binary),*(['independent_accounting_layout_unit','--nocapture','--test-threads=1'] if unit else [])],vm,target,closure)
        fields={};classes={};total=None
        for line in output.splitlines():
            if line.startswith('AFI_CLASS '):
                _,name,size,align=line.split();classes[name]={'bytes':int(size),'alignment':int(align)}
            if line.startswith('AFI_FIELD '):
                _,name,offset,size,align=line.split();assert name not in fields;fields[name]={'offset':int(offset),'bytes':int(size),'alignment':int(align)}
            if line.startswith('AFI_TOTAL '):total=list(map(int,line.split()[1:]))
        selected=[row for row in rows if unit or row.get('config')!='unit'];assert set(fields)=={r['field'] for r in selected}
        previous={}
        for row in sorted(selected,key=lambda r:(r['ownerClass'],fields[r['field']]['offset'])):
            item=fields[row['field']];cls=row['ownerClass'];assert item['offset']%item['alignment']==0
            assert item['offset']+item['bytes']<=classes[cls]['bytes']
            if item['bytes']:
                assert item['offset']>=previous.get(cls,0),(cls,row['field']);previous[cls]=item['offset']+item['bytes']
        assert total and total[2]==total[1]+119576 and total[3]==119576 and total[4]==424
        assert total[0]==classes['PermanentPositions']['bytes']+classes['ImplementationPermanentPositions']['bytes']
        assert total[1]==classes['ActivePositions']['bytes']+classes['ImplementationActivePositions']['bytes']
        layouts.append(dict(label=label,unit=unit,sourceTreeSHA256=hashlib.sha256(enc(closure)).hexdigest(),classes=classes,fields=fields,total=total))
        shutil.copyfile(binary,OUT/(label+'-metadata-executable'));binaries.append(dict(label=label,path=label+'-metadata-executable',sha256=sha(binary)))
    status='passed-two-fresh-exact-field-layout-checks'
finally:
    (OUT/'receipt.json').write_bytes(enc(dict(schema=1,status=status,sourceFreeze=json.loads((OUT/'inputs/freeze.json').read_text()),commands=commands,binaries=binaries,layouts=layouts,scope='Host compiler metadata only. No runtime owner, entry, return, drain, instruction, native app or GA execution.',ownedBuildScratch=str(BUILD))))
    print(OUT/'receipt.json',flush=True)
