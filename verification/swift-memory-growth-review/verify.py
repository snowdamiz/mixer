#!/usr/bin/env python3
"""Read-only sealed review replay. No writes, extraction, compilation or subprocesses."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,importlib.util,json,re,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda o:(json.dumps(o,sort_keys=True,indent=2)+'\n').encode()
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def archive(path):
    with tarfile.open(path,'r:gz')as t:
        members=t.getmembers();assert all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in members)
        data={m.name:t.extractfile(m).read()for m in members};assert len(data)==len(members);return data
def output(name):return gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode()
seal=read(HERE/'seal.json')
files={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.relative_to(HERE)!=Path('seal.json')}
assert files==set(seal['files']),(files-set(seal['files']),set(seal['files'])-files)
for path,digest in seal['files'].items():assert sha((HERE/path).read_bytes())==digest,path
for path,digest in seal['documentation'].items():assert sha((ROOT/path).read_bytes())==digest,path
ids=read(HERE/'input-identities.json');assert ids['baselineFiles']==125 and ids['candidateFiles']==127
assert ids['baselineSHA256']=='96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d'
assert ids['candidateSHA256']=='56e47ffa2c74ea243c9ead371a5ebfdeb59e85c0f05555419d51c84483afabe3'
assert ids['producerReceiptSHA256']==sha((HERE/'inputs/producer-receipt.json').read_bytes())
assert ids['producerSealSHA256']==sha((HERE/'inputs/producer-seal.json').read_bytes())
assert ids['candidateArchiveSHA256']==sha((HERE/'inputs/candidate-source.tar.gz').read_bytes())
sources={}
for p in (HERE/'sources').glob('*.tar.gz'):
    data=archive(p);assert sha(enc({k:sha(v)for k,v in data.items()}))==p.name[:-7];sources[p.name[:-7]]=data
base=sources[ids['baselineSHA256']];candidate=sources[ids['candidateSHA256']]
assert archive(HERE/'inputs/baseline-source.tar.gz')==base and archive(HERE/'inputs/candidate-source.tar.gz')==candidate
assert len(base)==125 and len(candidate)==127
assert {p for p in base.keys()|candidate.keys()if base.get(p)!=candidate.get(p)}==set(ids['changedPaths'])
commands=read(HERE/'command-index.json');assert set(commands)=={p.parent.name for p in (HERE/'commands').glob('*/receipt.json')}
for name,row in commands.items():
    d=HERE/'commands'/name;assert read(d/'receipt.json')==row
    for stream in ['stdout','stderr']:assert sha(gzip.decompress((d/(stream+'.gz')).read_bytes()))==row[stream+'SHA256']
    assert row['sourceUnchanged']is True
    assert row['sourceBeforeSHA256']==row['sourceAfterSHA256']==row['sourceTreeSHA256']
    digest=row['sourceTreeSHA256']
    if digest:
        m=read(d/'source-manifest.json');assert sha(enc(m))==digest
        assert m=={p:sha(v)for p,v in sources[digest].items()}
        target=row['environment']['CARGO_TARGET_DIR'];assert '/target-source-'+digest+'/'in target,(name,target)
        assert re.search(r'/(all|swift)-(debug|release)-(production|unit)-(mir|runtime|layout|expansion)$',target)
        for binary in row['executables']:
            assert binary['path'].startswith(target+'/')and binary['bytes']>0 and re.fullmatch('[a-f0-9]{64}',binary['sha256'])
receipt=read(HERE/'receipt.json');assert receipt['disposition']=='no-reproducible-correctness-or-accounting-defect-found'
assert receipt['expectedNonzeroCommands']=={'scratch-holder-check':1}
for name,code in receipt['expectedNonzeroCommands'].items():assert commands[name]['exitCode']==code
failed={name for name,row in commands.items()if row['exitCode']!=0 and name not in receipt['expectedNonzeroCommands']}
assert failed==set(receipt['excludedFailedCommands'])
assert failed==set(read(HERE/'harness-limitations.json')['excludedFailures'])
for name in receipt['qualifyingCommands']:assert name in commands and commands[name]['exitCode']==0
for name,row in commands.items():
    if row['executables']:
        for binary in row['executables']:
            # Execution must match a Cargo-emitted artifact captured at compile.
            artifacts=[x for d in (HERE/'commands').glob('*/artifacts.json')for x in read(d)]
            assert binary in artifacts,(name,binary)
expected=re.findall(r'fn (mg\d+_\w+)\(',candidate['src/experimental_swift_reactor/memory_growth_operations_tests.rs'].decode())
tests=re.findall(r'test ([\w:]+) \.\.\.',output('exact-runtime-all-debug-growth'))
assert len(tests)==20 and sorted(x.rsplit('::',1)[-1]for x in tests)==sorted(expected)
assert 'test result: ok. 20 passed; 0 failed; 0 ignored;'in output('exact-runtime-all-debug-growth')
assert commands['exact-runtime-all-debug-growth']['sourceTreeSHA256']==ids['candidateSHA256']
review_names=re.findall(r'fn (review\d+_\w+)\(', (HERE/'review-tests.rs').read_text());assert len(review_names)==7
for profile in ['debug','release']:
    name='adversarial-final-all-'+profile+'-execute';text=output(name)
    tests=re.findall(r'test ([\w:]+) \.\.\.',text);assert sorted(x.rsplit('::',1)[-1]for x in tests)==sorted(review_names)
    assert 'test result: ok. 7 passed; 0 failed; 0 ignored;'in text
    digest=commands[name]['sourceTreeSHA256'];overlay=sources[digest]
    for p,data in candidate.items():
        extra={'src/experimental_swift_reactor/memory_growth_operations_tests.rs':'review-tests.rs','src/experimental_swift_reactor/control.rs':'review-control-hooks.rs'}.get(p)
        assert overlay[p]==data+(b'\n'+(HERE/extra).read_bytes()if extra else b'')
    assert set(overlay)==set(candidate)
    assert len(re.findall(r'MG_BOUND fixtures=\d+ steps=\d+ maxFixtures=24 maxSteps=128 maxFrames=3',text))==7
# Recompute fresh MIR inventories rather than accepting stored audit conclusions.
growth=load('review_sealed_growth_inventory',HERE/'inputs/producer-inventory.py')
schema=read(HERE/'inputs/producer-inventory-schema.json');assert len(schema)==10356
parser=load('review_raw_inventory_parser',HERE/'audit_inventory.py')
for features in ['all','swift']:
    for config in ['production','unit']:
        label='fresh-'+features+'-'+config;path=HERE/(label+'.mir.gz');text=gzip.decompress(path.read_bytes()).decode()
        assert sha(text.encode())==read(HERE/'commands'/(label+'-compile')/'mir.json')['sha256']
        assert commands[label+'-compile']['sourceTreeSHA256']==ids['candidateSHA256']
        rows,methods,_=growth.canonical(path,config);wanted=[x for x in schema if x['config']==config]
        assert parser.projection(rows)==parser.projection(wanted)
        raw=parser.raw_functions(text);assert {x[0]for x in raw}=={x['function']for x in methods}
        for name,decl,debug in raw:
            actual=[x for x in wanted if x['mirFunction']==name and x['kind']=='canonical']
            assert {(x['binding'],x['mirType'],x['position'])for x in actual}=={(binding,ty,role)for binding,ty in decl.items()for role in ['source','argument','returned','caller']}
            aliases=[x for x in wanted if x['mirFunction']==name and x['kind']=='authored-alias']
            assert Counter((x['binding'],x['mirType'],x['position'])for x in aliases)==Counter((alias,decl[binding],role)for binding,names in debug.items()for alias in names for role in ['source','argument','returned','caller'])
        for family,total in [('memory',4800),('bulk',4324)]:
            collector=load('review_sealed_old_'+family,HERE/'inputs'/('accepted-'+family+'-inventory.py'));collector.promoted_constants=growth.promoted_constants
            prior=read(HERE/'inputs'/('accepted-'+family+'-schema.json'));old,_,_=collector.canonical(path,config)
            assert len(prior)==total and parser.projection(old,family=='memory')==parser.projection([x for x in prior if x['config']==config],family=='memory')
fields=re.findall(r'^    (\w+): ([^\n]+),$',candidate['src/experimental_swift_reactor/memory_growth_operations.rs'].decode().split('// ACCOUNTING_START')[1],re.M)
assert len(fields)==10356 and dict(fields)=={x['field']:x['rustType']for x in schema}
inventory=read(HERE/'inventory-audit.json');assert (inventory['canonicalProductionFields'],inventory['canonicalUnitFields'],inventory['authoredFields'])==(4724,4824,808)
# Independently parse all16 raw metadata outputs, then reproduce fresh4 pairings.
layout_module=load('review_sealed_layout_parser',HERE/'layouts.py');layouts=read(HERE/'inputs/producer-layouts.json');assert len(layouts)==16
for layout in layouts:
    name='layout-qualified-'+layout['label']+'-'+layout['features']+'-'+layout['profile']+('-unit'if layout['unit']else'-production')
    d=HERE/'inputs/producer-layouts'/name;row=read(d/'receipt.json');text=gzip.decompress((d/'stdout.gz').read_bytes()).decode();assert sha(text.encode())==row['stdoutSHA256']
    value=layout_module.parse(text);layout_module.audit(value,layout,schema)
    prior=next(x for x in layouts if x['label']=='baseline'and all(x[k]==layout[k]for k in ['features','profile','unit']))
    assert layout['types']==prior['types']and layout['owners']==prior['owners']
    assert value['totals']['state_limit']==128*1024*1024 and value['totals']['combined_limit']==256*1024*1024
    if layout['features']=='all':assert value['totals']['frozen_header']==2912
    if layout['label']=='candidate':
        t=value['totals'];assert t['header']==prior['totals']['header']+t['growth_permanent']and t['frame']==prior['totals']['frame']+t['growth_active']
        assert t['growth_permanent']==(559472 if layout['unit']else 316376)and t['growth_active']==(1815568 if layout['unit']else 973920)
for row in read(HERE/'fresh-layout-audit.json'):
    name=row['command'];text=output(name);bits=name.split('-');label,features,profile,unit=bits[2],bits[3],bits[4],bits[5]=='unit'
    expected=next(x for x in layouts if(x['label'],x['features'],x['profile'],x['unit'])==(label,features,profile,unit));layout_module.audit(layout_module.parse(text),expected,schema)
    derived=sources[commands[name]['sourceTreeSHA256']];original=base if label=='baseline'else candidate
    assert all(derived[p].startswith(data)for p,data in original.items())and set(derived)-set(original)=={'src/bin/growth_contract_layout.rs'}
frozen=load('review_sealed_frozen_parser',HERE/'audit_frozen.py');impls=[];maps=[]
for label in ['baseline','candidate']:
    impl=frozen.item(output('fresh-expanded-'+label),'impl SpanInstance {');impls.append(impl)
    names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',impl,re.M);assert len(names)==39
    maps.append({name:sha(frozen.item(impl,'fn '+name+'(').encode())for name in names})
assert impls[0]==impls[1]and maps[0]==maps[1]==read(HERE/'inputs/producer-frozen-identity.json')['methods']
owner_audit=read(HERE/'frozen-audit.json')['owners'];assert len(owner_audit)==16
for keyword,row in owner_audit.items():
    before=frozen.item(base[row['path']].decode(),keyword);after=frozen.item(candidate[row['path']].decode(),keyword)
    assert before==after and sha(after.encode())==row['sha256']
for keyword,digest in read(HERE/'inputs/producer-frozen-identity.json')['containingOwners'].items():assert owner_audit[keyword]['sha256']==digest
cleanup=read(HERE/'cleanup.json');assert cleanup['removed']is True and cleanup['openFilesBeforeRemoval']==0 and cleanup['nativeOrPhysicalToolsUsed']is False
print('PASS: sealed independent private growth review;20 exact growth+14 adversarial selections;4 fresh MIR inventories;10356+4800+4324 fields;16 raw/4 fresh layouts;39 Frozen methods;all nested receipts sealed;read-only')
