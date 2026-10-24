#!/usr/bin/env python3
"""Independent host-only source/accounting review; never executes control bodies."""
from pathlib import Path
import collections, datetime, gzip, hashlib, json, os, re, shutil, subprocess, sys, tarfile, tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-control-accounting-candidate-2'
QUALIFYING = PACKET / 'results/20261024T065629251176Z'
BASELINE = '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
CANDIDATE = 'e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d'
ENV = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'])
ENV.pop('RUSTFLAGS', None)
ENV.pop('RUSTC_BOOTSTRAP', None)
commands = []

def encode(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def save(name, value): (HERE / name).write_bytes(encode(value))
def sha(data): return hashlib.sha256(data).hexdigest()
def raw(path): return path.read_bytes() if path.exists() else gzip.decompress(Path(str(path) + '.gz').read_bytes())
def read(path): return json.loads(raw(path))
def closure(path):
    files = [path/'Cargo.toml', path/'Cargo.lock'] + [p for name in ['src','tests','include'] for p in sorted((path/name).rglob('*')) if p.is_file()]
    return {str(p.relative_to(path)):sha(p.read_bytes()) for p in files if p.exists()}
def digest(value): return sha(encode(value))
def run(name, argv, cwd=ROOT, extra=None):
    assert digest(closure(ROOT/'vm')) == BASELINE, 'live VM drift before '+name
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    env = dict(ENV)
    if extra: env.update(extra)
    proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=600)
    for stream in ['stdout','stderr']: (HERE/(name+'.'+stream)).write_bytes(getattr(proc,stream))
    commands.append(dict(name=name, argv=argv, cwd=str(cwd), extraEnvironment=extra or {}, sourceTreeSHA256=digest(closure(cwd)) if (cwd/'Cargo.toml').exists() else None, startedUTC=started, completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), exitCode=proc.returncode, stdout=name+'.stdout', stdoutSHA256=sha(proc.stdout), stderr=name+'.stderr', stderrSHA256=sha(proc.stderr)))
    save('commands.json',commands)
    assert digest(closure(ROOT/'vm')) == BASELINE, 'live VM drift after '+name
    assert proc.returncode == 0, (name,proc.stderr.decode()[-4000:])
    print(name,proc.returncode,flush=True)
    return proc.stdout.decode()

def struct_fields(source, name):
    body = source.split('struct '+name+' {',1)[1].split('\n}',1)[0]
    starts = list(re.finditer(r'^    (\w+): ',body,re.M))
    result=[]
    for i,m in enumerate(starts):
        end = starts[i+1].start() if i+1 < len(starts) else len(body)
        chunk=body[m.end():end]
        ty=chunk.split('\n    #[',1)[0].strip().rstrip(',')
        before=body[(starts[i-1].start() if i else 0):m.start()]
        unit=before.rstrip().endswith('#[cfg(test)]')
        result.append(dict(field=m.group(1),rustType=ty,unitOnly=unit))
    return result

def brace_end(source, opening):
    depth=0; string=False; escape=False
    for i in range(opening,len(source)):
        ch=source[i]
        if string:
            if escape: escape=False
            elif ch=='\\': escape=True
            elif ch=='"': string=False
            continue
        if ch=='"': string=True
        elif ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:return i+1
    raise AssertionError('unclosed body')

def frozen_bodies(text):
    owner=text.index('impl SpanInstance {')
    answer={}
    for name in ['pop32','close_control','branch','run']:
        start=text.index('fn '+name+'(',owner)
        end=brace_end(text,text.index('{',start))
        answer[name]=text[start:end]
    return answer

def offline_audit():
    seal=read(PACKET/'seal.json')
    for name,expected in seal['files'].items(): assert sha(raw(PACKET/name))==expected,name
    for name,expected in seal['externalBindings'].items(): assert sha(raw(ROOT/name))==expected,name
    inputs={str(p.relative_to(ROOT)):sha(raw(p)) for p in [PACKET/'seal.json',PACKET/'source.patch',PACKET/'verify.py',QUALIFYING/'bound-inventory-schema.json',QUALIFYING/'canonical-function-manifest.json',QUALIFYING/'corrected-boundary-comparisons.json',ROOT/'docs/swift-control-invocation-contract.md',ROOT/'verification/swift-control-invocation-root-review/accounting-scope-interpretation.json']}
    save('inputs.json',dict(files=inputs,baseline=digest(closure(ROOT/'vm')),producerSealedFiles=len(seal['files'])))
    assert digest(closure(ROOT/'vm'))==BASELINE
    archives={}
    for label in ['baseline','candidate','baseline-metadata','candidate-metadata']:
        expected=read(QUALIFYING/(label+'-manifest.json'))
        with tarfile.open(QUALIFYING/(label+'-source.tar.gz')) as tar:
            actual={str(Path(m.name).relative_to('vm')):sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
        assert actual==expected,label
        archives[label]=dict(files=len(actual),closure=digest(actual))
    assert archives['baseline']['closure']==BASELINE and archives['candidate']['closure']==CANDIDATE
    rows=read(QUALIFYING/'bound-inventory-schema.json')
    assert len(rows)==7640 and len({r['field'] for r in rows})==7640
    control=(PACKET/'overlay/src/experimental_swift_reactor/control_operations.rs').read_text()
    owner=(PACKET/'overlay/src/experimental/execution/mod.rs').read_text()
    frame=(PACKET/'overlay/src/experimental_swift_reactor/frame_operations.rs').read_text()
    classes={'PermanentPositions':struct_fields(control,'PermanentPositions'),'ActivePositions':struct_fields(control,'ActivePositions'),'crate::experimental::execution::SwiftControlPrivatePositions':struct_fields(owner,'SwiftControlPrivatePositions')}
    declared=[x['field'] for c,fields in classes.items() for x in fields if x['field']!='private_scalar_transfers']
    assert set(declared)=={r['field'] for r in rows} and len(declared)==7640
    assert sum(x['field']=='private_scalar_transfers' for x in classes['ActivePositions'])==1
    containing={cls:[x for x in struct_fields(frame,cls) if 'FrameOperationStorage' in x['rustType']] for cls in ['PermanentPositions','ActivePositions','ImplementationPermanentPositions','ImplementationActivePositions']}
    flat=[x for items in containing.values() for x in items]
    assert len(flat)==44 and sum(not x['unitOnly'] for x in flat)==28
    assert containing==read(QUALIFYING/'all-enlarged-containing-positions.json')
    save('independent-containing-positions.json',containing)
    # Independent MIR partition and exhaustive declaration/alias ownership check.
    census={}
    leaves={'result','height','start','end','is_loop','is_function','is_if','clear_result','decoded'}
    for config in ['production','unit']:
        mir=raw(QUALIFYING/('swift-debug-'+config+'.mir')).decode()
        functions=[]
        for m in re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{\n(.*?)^\}',mir,re.M|re.S):
            name,params,ret,body=m.groups()
            if not (name.startswith('control_operations::') or (name.startswith('experimental::execution::') and name.rsplit('::',1)[-1] in leaves)):continue
            selected=[r for r in rows if r['config']==config and r.get('mirFunction')==name]
            assert selected,('omitted function',name)
            locals_=set(re.findall(r'^    let (?:mut )?(_\d+): ',body,re.M))
            arguments=set(re.findall(r'(_\d+): ',params))
            bindings=locals_|arguments
            for binding in bindings:
                matches=[r for r in selected if r['binding']==binding]
                assert {r['position'] for r in matches}=={'source','argument','returned','caller'},(config,name,binding)
            aliases=re.findall(r'\bdebug (\w+) => (_\d+);',body)
            for alias,binding in aliases:
                assert {r['position'] for r in selected if r['binding']==alias}=={'source','argument','returned','caller'},(config,name,alias)
            functions.append(dict(function=name,bindings=len(bindings),aliases=len(aliases),rows=len(selected)))
        assert len(functions)==38,(config,len(functions))
        census[config]=functions
    save('independent-canonical-census.json',census)
    layouts=read(QUALIFYING/'layouts.json')
    comparisons=read(QUALIFYING/'corrected-boundary-comparisons.json')
    for layout in layouts:
        if layout['label']!='candidate':continue
        unit=layout['unit'];previous=next(x for x in layouts if x['label']=='baseline' and (x['config'],x['profile'],x['unit'])==(layout['config'],layout['profile'],unit))
        selected=[r for r in rows if unit or r['config']!='unit']
        assert set(layout['fields'])=={r['field'] for r in selected}
        intervals=collections.defaultdict(list)
        for row in selected:
            f=layout['fields'][row['field']];cls=row['ownerClass']
            assert f['offset']%f['alignment']==0 and f['offset']+f['bytes']<=layout['classes'][cls]['bytes']
            if f['bytes']:intervals[cls].append((f['offset'],f['offset']+f['bytes']))
        nested=next(x for x in read(QUALIFYING/'nested-layout-receipt.json')['layouts'] if (x['config'],x['profile'],x['unit'])==(layout['config'],layout['profile'],unit))
        intervals['ActivePositions'].append((nested['offset'],nested['offset']+nested['bytes']))
        for cls,values in intervals.items():
            last=0
            for start,end in sorted(values):assert start>=last,(cls,start,last);last=end
        totals=layout['totals'];base=previous['totals']
        assert totals['header']-base['header']==totals['new_permanent']+sum(not x['unitOnly'] or unit for x in flat)*1096
        assert totals['frame_bound']==totals['frame_active']+119576+totals['new_active']
        comparison=next(x for x in comparisons if (x['config'],x['profile'],x['unit'])==(layout['config'],layout['profile'],unit))
        assert comparison['phasePreviousBound']==0 and comparison['phaseBoundaryAt']==totals['frame_bound']
        assert comparison['headerPlusFrameBound']==totals['header']+totals['frame_bound']
    save('offline-audit.json',dict(status='passed',archives=archives,positiveFields=len(rows),canonicalFunctionCount=38,containingFields=len(flat),productionContainingFields=28,liveVMUnchanged=True))
    return classes,containing

def metadata_instrument(vm,classes,containing):
    frame=vm/'src/experimental_swift_reactor/frame_operations.rs'
    lines=['\npub(crate) fn independent_review_metadata(){']
    types={'storage':"FrameOperationStorage<'static>",'drop_tuple':"(ExecutionParts<'static, SwiftMode>,FrameOperationStorage<'static>)",'failure':'SwiftRunFailure'}
    for name,ty in types.items():lines.append(f'println!("REVIEW type {name} {{}}",size_of::<{ty}>());')
    for name,expr in [('header','execution_header_bytes().unwrap()'),('frame_bound','FRAME_OPERATION_BYTES.unwrap()'),('frame_permanent','PERMANENT_BYTES'),('frame_active','ACTIVE_BYTES'),('value_bound','value_operations::VALUE_OPERATION_BYTES.unwrap()'),('bootstrap','construction_bytes().unwrap()')]:lines.append(f'println!("REVIEW total {name} {{}}",{expr});')
    for cls,items in containing.items():
        for field in items:
            prefix='#[cfg(test)] ' if field['unitOnly'] else ''
            lines.append(prefix+f'println!("REVIEW containing {cls}.{field["field"]} {{}} {{}}",std::mem::offset_of!({cls},{field["field"]}),size_of::<{field["rustType"]}>());')
    lines+=['control_operations::independent_review_control_metadata();','#[cfg(feature="experimental-span-execution")] crate::experimental::execution::independent_review_frozen_metadata();','}','#[cfg(test)] #[test] fn independent_preflight_metadata_only(){independent_review_metadata();}']
    frame.write_text(frame.read_text()+'\n'.join(lines)+'\n')
    owner=vm/'src/experimental/execution/mod.rs'
    ownerlines=['\n#[cfg(feature="experimental-span-execution")] pub(crate) fn independent_review_frozen_metadata(){println!("REVIEW total frozen {}",std::mem::size_of::<SpanInstance>()-std::mem::size_of::<FunctionCache>()+3*std::mem::size_of::<ExecutionFailure>()+2*std::mem::size_of::<CacheFailure>()+std::mem::size_of::<super::cache::DecodedInstruction>()+std::mem::size_of::<Control>()+std::mem::size_of::<ScalarReader<\'_>>()+512);}', '#[cfg(feature="experimental-swift-reactor")] pub(crate) fn independent_review_private_metadata(){']
    child=vm/'src/experimental_swift_reactor/control_operations.rs'
    childlines=['\npub(super) fn independent_review_control_metadata(){']
    for cls,items in classes.items():
        private='SwiftControlPrivatePositions' in cls
        lines=ownerlines if private else childlines
        localcls='SwiftControlPrivatePositions' if private else cls
        lines.append(f'println!("REVIEW class {cls} {{}} {{}}",std::mem::size_of::<{localcls}>(),std::mem::align_of::<{localcls}>());')
        for field in items:
            prefix='#[cfg(test)] ' if field['unitOnly'] else ''
            name=field['field']
            lines.append(prefix+f'println!("REVIEW field {name} {{}} {{}} {{}}",std::mem::offset_of!({localcls},{name}),std::mem::size_of::<{field["rustType"]}>(),std::mem::align_of::<{field["rustType"]}>());')
    ownerlines+=['}'];childlines+=['crate::experimental::execution::independent_review_private_metadata();','}']
    owner.write_text(owner.read_text()+'\n'.join(ownerlines)+'\n');child.write_text(child.read_text()+'\n'.join(childlines)+'\n')
    reactor=vm/'src/experimental_swift_reactor/mod.rs';reactor.write_text(reactor.read_text()+'\npub(crate) fn independent_review_metadata_route(){execution::frame_operations::independent_review_metadata();}\n')
    lib=vm/'src/lib.rs';lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn independent_review_metadata_route(){experimental_swift_reactor::independent_review_metadata_route();}\n')
    (vm/'src/bin').mkdir(exist_ok=True)
    (vm/'src/bin/independent_review_metadata.rs').write_text('fn main(){mixer_vm::independent_review_metadata_route();}\n')

def main():
    assert not (HERE/'seal.json').exists(), 'sealed historical review; copy harness into a fresh sibling packet to reproduce'
    for name,argv in [('rustc-version',['rustc','-vV']),('cargo-version',['cargo','-V']),('python-version',['python3','--version']),('revision',['git','rev-parse','HEAD']),('host',['uname','-a'])]:run(name,argv)
    classes,containing=offline_audit()
    independent_type_and_delta_audit(classes)
    run('producer-offline-verifier',['python3','-B',str(PACKET/'verify.py')])
    scratch=Path(tempfile.mkdtemp(prefix='mixer-independent-control-preflight-'))
    save('scratch.json',dict(path=str(scratch)))
    try:
        sources={}
        for label in ['baseline','candidate']:
            dest=scratch/label;dest.mkdir()
            with tarfile.open(QUALIFYING/(label+'-source.tar.gz')) as tar:
                for member in tar.getmembers():
                    assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                    output=dest/member.name;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(tar.extractfile(member).read())
            vm=dest/'vm';sources[label]=vm
            expanded=run(label+'-expanded',['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],vm,{'CARGO_TARGET_DIR':str(scratch/(label+'-target')),'RUSTC_BOOTSTRAP':'1'})
            bodies=frozen_bodies(expanded);save(label+'-frozen-bodies.json',bodies)
        assert read(HERE/'baseline-frozen-bodies.json')==read(HERE/'candidate-frozen-bodies.json')
        save('independent-frozen-identity.json',{k:dict(identical=True,sha256=sha(v.encode())) for k,v in bodies.items()})
        # Apply the supplied patch in a third isolated copy and compare every file.
        patched=scratch/'patched-vm';shutil.copytree(sources['baseline'],patched)
        run('patch-apply',['patch','--batch','--forward','-p1','-i',str(PACKET/'source.patch')],patched)
        assert closure(patched)==closure(sources['candidate'])
        fresh_mir_audit(sources['candidate'],scratch)
        vm=sources['candidate'];metadata_instrument(vm,classes,containing)
        save('independent-metadata-manifest.json',closure(vm))
        with tarfile.open(HERE/'independent-metadata-source.tar.gz','w:gz') as tar:
            for name in closure(vm):tar.add(vm/name,arcname='vm/'+name,recursive=False)
        layouts=[]
        for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            for release in [False,True]:
                for unit in [False,True]:
                    label=config+('-release' if release else '-debug')+('-unit' if unit else '-production')
                    args=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'independent_preflight_metadata_only','--','--nocapture','--test-threads=1'] if unit else ['cargo','run','--bin','independent_review_metadata','--locked','--offline',*flags,*(['--release'] if release else [])]
                    output=run(label,args,vm,{'CARGO_TARGET_DIR':str(scratch/'metadata-target')})
                    parsed={'class':{},'field':{},'containing':{},'total':{},'type':{}}
                    for line in output.splitlines():
                        at=line.find('REVIEW ')
                        if at>=0:
                            _,kind,name,*numbers=line[at:].split();parsed[kind][name]=list(map(int,numbers))
                    expected=next(x for x in read(QUALIFYING/'layouts.json') if x['label']=='candidate' and (x['config'],x['profile'],x['unit'])==(config,'release' if release else 'debug',unit))
                    for name,value in parsed['total'].items():
                        mapped={'frozen':'frozen_header','bootstrap':'construction','frame_bound':'frame_bound','header':'header','value_bound':'value_bound','frame_active':'frame_active','frame_permanent':'frame_permanent'}[name]
                        assert value==[expected['totals'][mapped]],(label,name,value,expected['totals'][mapped])
                    for name,value in parsed['class'].items():assert value==[expected['classes'][name]['bytes'],expected['classes'][name]['alignment']],(label,name)
                    for name,value in parsed['field'].items():
                        if name=='private_scalar_transfers':continue
                        assert value==[expected['fields'][name][key] for key in ['offset','bytes','alignment']],(label,name)
                    for name,value in parsed['containing'].items():
                        if name in expected['containing']:
                            assert value==[expected['containing'][name]['offset'],expected['containing'][name]['bytes']],(label,name)
                        else:
                            assert name.startswith('PermanentPositions.completion_storage_') and value[1]==6232,(label,name,value)
                    assert len(parsed['containing'])==(44 if unit else 28)
                    assert parsed['type']['storage']==[6232] and parsed['type']['failure']==[1096]
                    assert len(parsed['field'])==(7641 if unit else 3881)
                    layouts.append(dict(config=config,profile='release' if release else 'debug',unit=unit,**parsed))
                    save('independent-layouts.json',layouts)
        save('receipt.json',dict(status='recommend-accept-source-accounting-preflight-only',sourceRevision=(HERE/'revision.stdout').read_text().strip(),baselineVMClosure=BASELINE,candidateVMClosure=CANDIDATE,commands=len(commands),metadataConfigurations=len(layouts),controlOperationsExecuted=False,sc01Through12Passed=False,sourceAccountingPreflightAccepted=False,sourceAccountingPreflightRecommendation=True,implementationAccepted=False,nativeRuntime=False,physicalRuntime=False,gaAcceptance=False,liveVMUnchanged=digest(closure(ROOT/'vm'))==BASELINE))
    finally:
        shutil.rmtree(scratch)
        save('cleanup.json',dict(ownedScratch=str(scratch),removed=not scratch.exists(),nativeInstancesStarted=False,otherProjectProcessesTouched=False,liveVMUnchanged=digest(closure(ROOT/'vm'))==BASELINE))

def parts(value):
    result=[];start=0;depth=0
    for i,c in enumerate(value):
        if c in '<([{':depth+=1
        elif c in '>)]}':depth-=1
        elif c==',' and depth==0:result.append(value[start:i].strip());start=i+1
    if value[start:].strip():result.append(value[start:].strip())
    return result

def actual_functions(text):
    leaves={'result','height','start','end','is_loop','is_function','is_if','clear_result','decoded'}
    answer=[]
    for match in re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{\n(.*?)^\}',text,re.M|re.S):
        name,params,ret,body=match.groups()
        if not(name.startswith('control_operations::') or (name.startswith('experimental::execution::') and name.rsplit('::',1)[-1] in leaves)):continue
        declarations=dict(re.findall(r'^\s+let (?:mut )?(_\d+): ([^\n]+);',body,re.M))
        for arg in parts(params):
            ident,ty=arg.split(': ',1);declarations[ident]=ty
        assert '_0' in declarations,name
        answer.append(dict(name=name,params=params,returnType=ret,body=body,declarations=declarations,line=text.count('\n',0,match.start())+1))
    assert len(answer)==38,len(answer)
    return answer

def normalize_actual(ty,capture_types):
    # Only authored references/path spelling and actual closure capture tuples.
    # No replacement of any compiler-private core type is permitted.
    ty=re.sub(r'\{closure@[^}]+\}',lambda m:capture_types[m.group()],ty)
    ty=ty.replace("'_","'static")
    ty=re.sub(r'(?<![:\w])(experimental_swift_reactor|experimental_wasi|experimental)::',r'crate::\1::',ty)
    ty=re.sub(r'(?<![:\w])control::','crate::experimental_swift_reactor::control::',ty)
    ty=re.sub(r'(?<![:\w])accounted::','crate::experimental_wasi::accounted::',ty)
    ty=re.sub(r'&(?!(?:\'|\s*\'))',"&'static ",ty)
    return 'Infallible' if ty=='!' else ty

def canonical_types(mir,rows,config):
    functions=actual_functions(mir);capture_types={};summary=[]
    for fn in functions:
        for site in re.findall(r'\{closure@[^}]+\}',fn['params']):
            captures={int(i):ty for i,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',fn['body'])}
            assert list(sorted(captures))==list(range(len(captures))),fn['name']
            if not captures:assert not re.search(r'_1\.\d+',fn['body'])
            capture_types[site]='('+', '.join(captures[i] for i in range(len(captures)))+(',' if len(captures)==1 else '')+')'
    for fn in functions:
        selected=[r for r in rows if r['config']==config and r.get('mirFunction')==fn['name']]
        expected=[(ident,ty) for ident,ty in fn['declarations'].items()]
        aliases=re.findall(r'\bdebug (\w+) => (_\d+);',fn['body'])
        for alias,ident in aliases:expected.append((alias,fn['declarations'][ident]))
        literals=re.findall(r'const ("(?:[^"\\]|\\.)*"|(?:true|false)|\d+_(?:u|i)(?:size|8|16|32|64|128))',fn['body'])
        for i,literal in enumerate(literals):expected.append(('literal_'+str(i),"&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]))
        required=collections.Counter((binding,ty,normalize_actual(ty,capture_types),position) for binding,ty in expected for position in ['source','argument','returned','caller'])
        observed=collections.Counter((r['binding'],r['mirType'],r['rustType'],r['position']) for r in selected)
        assert required==observed,(fn['name'],required-observed,observed-required)
        assert all(r['sourceTreeSHA256']==CANDIDATE for r in selected)
        summary.append(dict(function=fn['name'],declarations=len(fn['declarations']),aliases=len(aliases),literals=len(literals),fields=len(selected)))
    return summary

def independent_type_and_delta_audit(classes):
    rows=read(QUALIFYING/'bound-inventory-schema.json')
    declared={f['field']:f['rustType'] for cls,fields in classes.items() for f in fields if f['field']!='private_scalar_transfers'}
    for row in rows:
        actual=declared[row['field']]
        if 'SwiftControlPrivatePositions' in row['ownerClass']:actual=actual.replace('Kind','crate::experimental::execution::Kind')
        assert re.sub(r',(?=>)', '', re.sub(r'\s+','',actual))==re.sub(r',(?=>)', '', re.sub(r'\s+','',row['rustType'])),row['field']
    type_summary={c:canonical_types(raw(QUALIFYING/('swift-debug-'+c+'.mir')).decode(),rows,c) for c in ['production','unit']}
    save('independent-typed-census.json',type_summary)
    prior=ROOT/'verification/swift-control-accounting-preflight'
    prior_result=prior/'results/20261024T062441792011Z'
    old=read(prior_result/'bound-inventory-schema.json')
    def key(row):
        role='alias:'+row['binding'] if row['field'].startswith('alias_') else 'literal' if row['field'].startswith('literal_') else 'canonical' if row['field'].startswith('mir_') else row['field']
        return (row['config'],row['window'],re.sub(r'\{closure@[^}]+\}','{actual-closure}',row['mirType']) if 'mirType' in row else row['rustType'],row['position'],role)
    before=collections.Counter(key(r) for r in old);after=collections.Counter(key(r) for r in rows)
    added=after-before;removed=before-after
    assert sum(added.values())==136 and sum(removed.values())==16,(sum(added.values()),sum(removed.values()))
    assert all(k[1]=='control_pop_value' for k in added)
    assert all(k[1] in ['pop32','close_control'] and 'ExecutionOperationPhase' in k[2] for k in removed),removed
    files1=read(prior_result/'candidate-manifest.json');files2=read(QUALIFYING/'candidate-manifest.json')
    changed=[p for p in sorted(files1) if files1[p]!=files2[p]]
    assert changed==['src/experimental_swift_reactor/control_operations.rs'],changed
    path='overlay/src/experimental_swift_reactor/control_operations.rs'
    source1=(prior/path).read_text().split('// ACCOUNTING_START')[0]
    source2=(PACKET/path).read_text().split('// ACCOUNTING_START')[0]
    import difflib
    delta=''.join(difflib.unified_diff(source1.splitlines(True),source2.splitlines(True),fromfile='candidate1/control_operations.rs',tofile='candidate2/control_operations.rs'))
    assert delta==(PACKET/'behavior-delta.patch').read_text()
    assert source2.count('self.phase.pop_value()')==1
    save('independent-delta.json',dict(changedFiles=changed,behaviorPatchSHA256=sha(delta.encode()),oldFields=len(old),newFields=len(rows),addedFields=sum(added.values()),removedFields=sum(removed.values()),added=[dict(key=k,count=v) for k,v in added.items()],removed=[dict(key=k,count=v) for k,v in removed.items()],wrapperFieldsPerConfiguration=68,sourceLifecycleFields=sum(r['config']=='source' for r in rows)))

def fresh_mir_audit(vm,scratch):
    rows=read(QUALIFYING/'bound-inventory-schema.json');summary={}
    for config in ['production','unit']:
        target=scratch/('fresh-mir-'+config)
        args=['cargo','rustc','--lib','--locked','--offline','--features','experimental-swift-reactor','--','--emit=mir','-Zmir-include-spans=yes'] if config=='production' else ['cargo','test','--lib','--no-run','--locked','--offline','--features','experimental-swift-reactor']
        extra={'CARGO_TARGET_DIR':str(target),'RUSTC_BOOTSTRAP':'1'}
        if config=='unit':extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
        run('fresh-'+config+'-canonical-mir',args,vm,extra)
        files=[p for p in target.rglob('*.mir') if '::control_pop_value(' in p.read_text()];assert len(files)==1,[str(p) for p in target.rglob('*.mir')]
        data=files[0].read_bytes();(HERE/('fresh-'+config+'.mir.gz')).write_bytes(gzip.compress(data,mtime=0))
        summary[config]=dict(mirSHA256=sha(data),functions=canonical_types(data.decode(),rows,config))
    save('fresh-canonical-mir-census.json',summary)

if __name__=='__main__':main()


