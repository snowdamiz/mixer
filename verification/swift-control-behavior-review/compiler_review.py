#!/usr/bin/env python3
"""Fresh compiler observations on exact frozen source, with separate metadata copy."""
from pathlib import Path
import ast, collections, gzip, importlib.util, json, re, shutil, sys, tarfile
from review import HERE, ROOT, PRODUCER, SCRATCH, VM, BASE, META, enc, sha, digest, manifest, run

CAND=ROOT/'verification/swift-control-accounting-candidate-2'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def definitions(path,names,namespace):
    parsed=ast.parse(path.read_text());nodes=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)

def metadata():
    assert not META.exists()
    shutil.copytree(VM,META)
    ns=dict(ROOT=ROOT,HERE=CAND,json=json,Path=Path)
    definitions(CAND/'collect.py',['metadata_source','parse_layout'],ns)
    existing=ns['metadata_source'](META,'candidate')
    hooks=json.loads((PRODUCER/'unit-hook-inventory.json').read_text())
    code=['pub(super) fn review_control_hook_metadata(){']
    for envelope,cls in [('permanent','ControlHookPermanentPositions'),('active','ControlHookActivePositions')]:
        code.append(f'println!("CPI_CLASS {cls} {{}} {{}}",size_of::<{cls}>(),std::mem::align_of::<{cls}>());')
        for row in hooks:
            if row['envelope']==envelope:code.append(f'println!("CPI_FIELD {row["field"]} {{}} {{}} {{}}",std::mem::offset_of!({cls},{row["field"]}),size_of::<{row["rustType"]}>(),std::mem::align_of::<{row["rustType"]}>());')
    code+=['println!("CPI_TYPE Hooks {} {}",size_of::<Hooks>(),std::mem::align_of::<Hooks>());','}']
    p=META/'src/experimental_swift_reactor/frame_operations_tests.rs';p.write_text(p.read_text()+'\n'+'\n'.join(code))
    p=META/'src/experimental_swift_reactor/frame_operations.rs';p.write_text(p.read_text().replace('pub(crate) fn accounting_preflight_metadata(){','pub(crate) fn accounting_preflight_metadata(){\n#[cfg(test)] tests::review_control_hook_metadata();',1))
    metadata_manifest=manifest(META);(HERE/'metadata-manifest.json').write_bytes(enc(metadata_manifest))
    with tarfile.open(HERE/'metadata-source.tar.gz','w:gz') as archive:
        for path in metadata_manifest:archive.add(META/path,arcname='vm/'+path,recursive=False)
    schema=json.loads((CAND/'inventory-schema.json').read_text());layouts=[]
    producer=json.loads((PRODUCER/json.loads((PRODUCER/'receipt.json').read_text())['metadataDirectory']/'layouts.json').read_text())
    for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for release in [False,True]:
            for unit in [False,True]:
                args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'control_accounting_preflight_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--locked','--offline','--bin','control_accounting_layout',*flags,*(['--release'] if release else [])]
                p,out=run('layout-'+config+('-release' if release else '-debug')+('-unit' if unit else '-production'),args,META,target='metadata-target');assert p.returncode==0
                layout=ns['parse_layout'](p.stdout.decode());layout.update(config=config,profile='release' if release else 'debug',unit=unit)
                expected=next(x for x in producer if (x['config'],x['profile'],x['unit'])==(layout['config'],layout['profile'],unit));assert layout==expected
                rows=[r for r in schema if unit or r.get('config')!='unit']+ (hooks if unit else [])
                assert set(layout['fields'])=={r['field'] for r in rows}
                seen={}
                for row in sorted(rows,key=lambda r:((r.get('ownerClass') or ('ControlHookPermanentPositions' if r['envelope']=='permanent' else 'ControlHookActivePositions')),layout['fields'][r['field']]['offset'])):
                    cls=row.get('ownerClass') or ('ControlHookPermanentPositions' if row['envelope']=='permanent' else 'ControlHookActivePositions');field=layout['fields'][row['field']]
                    assert field['offset']%field['alignment']==0
                    assert field['offset']>=seen.get(cls,0);seen[cls]=field['offset']+field['bytes'];assert seen[cls]<=layout['classes'][cls]['bytes']
                assert layout['types']['FrameOperationStorage']['bytes']==6232
                assert layout['totals']['frame_bound']==layout['totals']['frame_active']+119576+layout['totals']['new_active']
                assert layout['totals']['new_active']==(2325256 if unit else 1162520)
                assert layout['totals']['header']==(2409184 if unit else 1514504)
                assert layout['totals']['frame_bound']==(3950128 if unit else 2211968)
                if config=='all':assert layout['totals']['frozen_header']==2912
                layouts.append(layout);(HERE/'layouts.json').write_bytes(enc(layouts))
    (HERE/'containing-rows.json').write_bytes(enc(existing))
    print('fresh exact 8 configurations match every producer field, containing layout and total',flush=True)

def sources():
    tools=[('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('revision',['git','rev-parse','HEAD'])]
    for name,args in tools:run('tool-'+name,args,ROOT)
    builder=module('builder',CAND/'build_overlay.py');frozen={}
    for label,source in [('baseline',BASE),('candidate',VM)]:
        p,out=run(label+'-expanded',['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],source,{'RUSTC_BOOTSTRAP':'1'},target='source-'+label+'-target');assert p.returncode==0
        span=p.stdout.decode().split('impl SpanInstance {',1)[1]
        frozen[label]={name:builder.method(span,name) for name in ['pop32','close_control','branch','run']}
    assert frozen['baseline']==frozen['candidate'];(HERE/'frozen-identity.json').write_bytes(enc({name:dict(identical=True,sha256=__import__('hashlib').sha256(body.encode()).hexdigest(),reservationBytes=2912) for name,body in frozen['baseline'].items()}))
    (HERE/'expanded-bodies.json').write_bytes(enc(frozen))
    # Fresh actual-source unoptimized MIR, never the metadata/probe source tree.
    mir={}
    for unit in [False,True]:
        name='unit' if unit else 'production';target='canonical-'+name+'-target'
        args=['cargo','test','--lib','--no-run','--locked','--offline','--all-features'] if unit else ['cargo','rustc','--lib','--locked','--offline','--all-features','--','--emit=mir','-Zmir-include-spans=yes']
        extra={'RUSTC_BOOTSTRAP':'1'}
        if unit:extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
        p,out=run(name+'-fresh-mir',args,VM,extra,target=target);assert p.returncode==0
        selected=[p for p in (SCRATCH/target/'debug/deps').glob('*.mir') if '::control_operation(' in p.read_text() and (('fn experimental_swift_reactor::execution::frame_operations::tests::control_after_value_pop(' in p.read_text())==unit)]
        assert len(selected)==1;mir[name]=selected[0]
        with gzip.open(HERE/(name+'.mir.gz'),'wb') as f:f.write(selected[0].read_bytes())
    inv=module('accepted_inventory',CAND/'inventory.py')
    ns=dict(re=re)
    definitions(PRODUCER/'canonical_audit.py',['functions','canonical_name','canonical_functions'],ns)
    inv.prior.functions=ns['canonical_functions'];schema=json.loads((CAND/'inventory-schema.json').read_text());canonical=[]
    for name,path in mir.items():
        rows,defs=inv.inventory(path,name);old=[r for r in schema if r['config']==name and 'mirFunction' in r and r['window']!='complete_controlled_empty']
        identity=lambda r:{k:r[k] for k in ['envelope','window','binding','position','rustType','sourceNames','mirType','field']}
        assert list(map(identity,rows))==list(map(identity,old));assert len(defs)==38
        canonical.append(dict(config=name,functions=defs,fields=len(rows),mirSHA256=sha(path)))
    (HERE/'canonical-roles.json').write_bytes(enc(canonical))
    # Replay the finite compiler role recipe, then independently compare its exact
    # positive rows and every field against the frozen declarations/layouts.
    prior=module('accepted_prior',ROOT/'verification/swift-active-frames-implementation/inventory.py')
    ns=dict(re=re,collections=collections,prior=prior)
    definitions(PRODUCER/'hook_inventory.py',['readfunctions','norm','items'],ns)
    original=ns['readfunctions'](gzip.decompress((CAND/'unit.mir.gz').read_bytes()).decode());current=ns['readfunctions'](mir['unit'].read_text());rows=[]
    hook_functions=json.loads((PRODUCER/'unit-hook-functions.json').read_text())
    for ordinal,fn in enumerate(hook_functions):
        key=fn['key'];data=ns['items'](current[key]);mode=fn['mode']
        if mode!='new':
            old=collections.Counter((x[0],x[1],x[2] if x[1]!='mir' else '') for x in ns['items'](original[key]));selected=[]
            for item in data:
                identity=(item[0],item[1],item[2] if item[1]!='mir' else '')
                if old[identity]:old[identity]-=1
                else:selected.append(item)
            data=selected
        assert len(data)*4==fn['positions']
        envelope='active' if key in ['primitive_pop','primitive_push','experimental_swift_reactor::execution::frame_operations::work'] else 'permanent'
        for n,(ty,kind,binding,mirtype) in enumerate(data):
            for position in ['source','argument','returned','caller']:rows.append(dict(envelope=envelope,field=f'hook_{ordinal}_{n}_{position}',rustType=ty,mirType=mirtype,sourceName=binding,kind=kind,position=position,mode=mode,config='unit'))
    original_rows=json.loads((PRODUCER/'unit-hook-inventory.json').read_text());identity=lambda r:{k:v for k,v in r.items() if k not in ['mirLine','mirFunction']}
    assert rows==list(map(identity,original_rows));assert len(rows)==400
    (HERE/'hook-role-replay.json').write_bytes(enc(dict(positiveFields=len(rows),functions=hook_functions,rows=rows,scope='authored canonical logical ownership, not machine stack or RSS')))
    p,_=run('library-clippy',['cargo','clippy','--lib','--all-features','--locked','--offline','--','-D','warnings'],VM,target='source-candidate-target');assert p.returncode==0
    diagnostics={}
    for label,source in [('baseline',BASE),('candidate',VM)]:
        p,_=run(label+'-broad-clippy',['cargo','clippy','--all-targets','--all-features','--keep-going','--message-format=json','--locked','--offline','--','-D','warnings'],source,target='source-'+label+'-target');assert p.returncode!=0
        messages=[]
        for line in p.stdout.decode().splitlines():
            try:msg=json.loads(line)
            except ValueError:continue
            if msg.get('reason')!='compiler-message':continue
            m=msg['message']
            if m['level']!='error' or not m.get('code'):continue
            spans=[s for s in m['spans'] if s.get('is_primary')]
            for s in spans:messages.append(dict(code=m['code']['code'],message=m['message'],path=s['file_name'],column=s['column_start'],source=[t['text'] for t in s['text']]))
        diagnostics[label]=messages
    normalize=lambda rows:collections.Counter(json.dumps(r,sort_keys=True) for r in rows)
    assert len(diagnostics['baseline'])==len(diagnostics['candidate'])==26
    assert normalize(diagnostics['baseline'])==normalize(diagnostics['candidate'])
    (HERE/'clippy-comparison.json').write_bytes(enc(diagnostics))
    print('fresh exact Frozen source identity, 38 canonical functions/config, 400 hook positions; same 26 broad Clippy identities',flush=True)

if __name__=='__main__':{'metadata':metadata,'sources':sources}[sys.argv[1]]()
