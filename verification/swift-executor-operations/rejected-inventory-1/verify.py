#!/usr/bin/env python3
"""Check saved source/command/binary/layout evidence without executing guest work."""
from pathlib import Path
import hashlib, json, re, subprocess, sys, tarfile, tempfile

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else sorted((HERE/'results').iterdir())[-1]
sha=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
encoded=lambda obj:(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
digest=lambda obj:hashlib.sha256(encoded(obj)).hexdigest()
receipt=json.loads((OUT/'receipt.json').read_text())
assert receipt['status'].startswith('passed-private-zero-frame-')
assert sha(OUT/'candidate-source.tar.gz')==receipt['candidateSourceArchiveSHA256']
assert sha(OUT/'baseline-source.tar')==receipt['baselineSourceArchiveSHA256']
commands={row['name']:row for row in receipt['commands']}
for row in commands.values():
    assert sha(OUT/row['log'])==row['logSHA256']
    if row['name'].endswith('clippy-broad'): assert row['exit']!=0
    else: assert row['exit']==0
    if row['target']: assert row['sourceBeforeAfterVerified']

def manifest(path):return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
def declared_fields(body):
    body='\n'.join(line for line in body.splitlines() if not line.lstrip().startswith('//'))
    fields={};depth=0;start=0
    for index,character in enumerate(body):
        if character in '([{<':depth+=1
        elif character in ')]}>':depth-=1
        elif character==',' and depth==0:
            declaration=body[start:index].strip();start=index+1
            if declaration:
                name,shape=declaration.split(':',1)
                fields[name.strip()]=' '.join(shape.split())
    assert depth==0 and not body[start:].strip()
    return fields
source=json.loads((OUT/'candidate-manifest.json').read_text())
assert digest(source)==receipt['candidateSourceTreeSHA256'] and len(source)==receipt['sourceCount']
with tempfile.TemporaryDirectory(prefix='mixer-values-evidence-') as tmp:
    tmp=Path(tmp)
    closures={}
    for label,archive in [('baseline','baseline-source.tar'),('candidate','candidate-source.tar.gz')]:
        with tarfile.open(OUT/archive) as tf:tf.extractall(tmp/label,filter='data')
        dest=tmp/label/'vm'
        closure=manifest(dest)
        assert closure==json.loads((OUT/(label+'-product-closure.json')).read_text())
        closures[label]=closure
        if label=='candidate': assert closure==source
        execution=dest/'src/experimental_swift_reactor/execution.rs'
        execution.write_text(execution.read_text()+'\n'+(OUT/'inputs/owner-layout-probe.rs').read_text())
        calls='execution::operations_owner_layout_probe();'
        if label=='candidate':
            operations=dest/'src/experimental_swift_reactor/value_operations.rs'
            original=operations.read_text()
            operations.write_text(original+'\n'+(OUT/'inputs/operation-layout-probe.rs').read_text())
            calls+=' execution::value_operations::operations_layout_probe();'
            field_map={}
            for name in ['PermanentPositions','ActivePositions']:
                body=original.split('struct '+name+' {',1)[1].split('\n}',1)[0]
                fields=declared_fields(body)
                field_map[name]=fields
        module=dest/'src/experimental_swift_reactor/mod.rs'
        module.write_text(module.read_text()+'\npub(crate) fn value_layout_probe(){'+calls+'}\n')
        lib=dest/'src/lib.rs'
        lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn value_layout_probe(){experimental_swift_reactor::value_layout_probe();}\n')
        (dest/'examples').mkdir(exist_ok=True)
        (dest/'examples/value-layout.rs').write_text('fn main(){mixer_vm::value_layout_probe();}\n')
        execution.write_text(execution.read_text()+'\n#[cfg(test)] #[test] fn value_layout_only(){super::value_layout_probe();}\n')
        assert manifest(dest)==json.loads((OUT/(label+'-layout-closure.json')).read_text())
    compile_input=lambda name:name in ['Cargo.toml','Cargo.lock'] or name.startswith(('src/','tests/','include/'))
    changed=sorted(name for name in set(closures['baseline'])|set(closures['candidate']) if compile_input(name)
        if closures['baseline'].get(name)!=closures['candidate'].get(name))
    assert changed==sorted(['src/experimental/execution/borrowed.rs',
        'src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/execution_tests.rs',
        'src/experimental_swift_reactor/value_operations.rs','src/experimental_swift_reactor/value_operation_tests.rs'])
    # The shared dispatch body and full Frozen owner source remain literal.
    shared=[]
    for label in ['baseline','candidate']:
        text=(tmp/label/'vm/src/experimental/execution/borrowed.rs').read_text()
        shared.append(text[text.index('    if saturating {',text.index(' fn numeric<')):])
    assert shared[0]==shared[1]
    assert closures['baseline']['src/experimental/execution/mod.rs']==closures['candidate']['src/experimental/execution/mod.rs']

layout_summary=[]
for after in [row for row in receipt['layouts'] if row['label']=='candidate']:
    before=next(row for row in receipt['layouts'] if row['label']=='baseline' and all(row[k]==after[k] for k in ['configuration','profile','cfg']))
    assert [v for v in before['records'] if v.startswith('value_owner')]==[v for v in after['records'] if v.startswith('value_owner')]
    def bounds(row):return {v.split('|')[1]:int(v.split('|')[2]) for v in row['records'] if v.startswith('value_bounds|')}
    b,a=bounds(before),bounds(after)
    assert a['header']==b['header']+a['permanent'] and a['construction']==b['construction']
    assert a['phase']==a['declared_operation']+a['active']
    for inventory,fields in field_map.items():
        actual=[v.split('|') for v in after['records'] if v.startswith('value_position|'+inventory+'|')]
        assert {v[2] for v in actual}==set(fields)
        offsets=[(int(v[3]),int(v[4]),int(v[5])) for v in actual]
        assert all(offset%alignment==0 for offset,size,alignment in offsets)
        intervals=sorted((offset,offset+size) for offset,size,_ in offsets if size)
        assert all(left[1]<=right[0] for left,right in zip(intervals,intervals[1:]))
        recorded=next(v.split('|') for v in after['records'] if v.startswith('value_inventory|'+inventory+'|'))
        total=int(recorded[2]);assert max(end for _,end in intervals)<=total
        assert total==a['permanent' if inventory=='PermanentPositions' else 'active']
    layout_summary.append(dict(configuration=after['configuration'],profile=after['profile'],cfg=after['cfg'],before=b,after=a,fields=sum(map(len,field_map.values()))))

runtime_lists=[]
for row in receipt['binaries']:
    path=Path(row['path']); assert sha(path)==row['sha256']
    listed=subprocess.check_output([str(path),'--list'],cwd=commands[row['listCommand']]['cwd'],text=True)
    tests=[line for line in listed.splitlines() if line.endswith(': test')]
    assert tests==row['runtimeTests']
    runtime=(OUT/commands[row['runCommand']]['log']).read_text()
    summary=re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',runtime)
    assert len(summary)==1 and sum(map(int,summary[0]))==len(tests)
    runtime_lists.append(dict(configuration=row['configuration'],target=row['target'],sha256=row['sha256'],listed=len(tests),passed=int(summary[0][0]),ignored=int(summary[0][1])))

lint=[]
for label in ['baseline','candidate']:
    text=(OUT/commands[label+'-clippy-broad']['log']).read_text()
    identities=[]
    for block in re.split(r'(?=^error:)',text,flags=re.M):
        if not block.startswith('error:') or block.startswith('error: could not compile'):continue
        location=re.search(r'-->\s+([^\n]+?):(\d+):(\d+)',block)
        assert location
        identities.append((block.splitlines()[0],*location.groups()))
    lint.append(identities)
assert sorted(lint[0])==sorted(lint[1])
positions=[]
chosen=next(row for row in receipt['layouts'] if row['label']=='candidate' and row['cfg']=='production')
for inventory,fields in field_map.items():
    for record in [v.split('|') for v in chosen['records'] if v.startswith('value_position|'+inventory+'|')]:
        name=record[2];offset,size,alignment=map(int,record[3:]);shape=fields[name]
        count=1;element_shape=shape
        if shape.startswith('['):
            element_shape,number=shape[1:-1].rsplit(';',1);count=int(number)
        assert size%count==0
        struct_at=original.index('struct '+inventory+' {')
        declaration=original.index('    '+name+':',struct_at)
        positions.append(dict(inventory=inventory,name=name,declaredShape=shape,
            declarationFile='vm/src/experimental_swift_reactor/value_operations.rs',
            declarationLine=original[:declaration].count('\n')+1,
            bytes=size,alignment=alignment,offset=offset,
            typedPositions=[dict(name=name+('['+str(n)+']' if count>1 else ''),shape=element_shape.strip(),
                offset=offset+n*(size//count),bytes=size//count) for n in range(count)]))
binding_map=dict(status='CANDIDATE_TYPED_INVENTORY_REQUIRES_INDEPENDENT_BINDING_COVERAGE_REVIEW',
    sourceTreeSHA256=receipt['candidateSourceTreeSHA256'],positions=positions,
    fields=len(positions),typedPositions=sum(len(v['typedPositions']) for v in positions),
    interpretation='All positions add positive full field sizes. Compiled offsets prove disjoint typed layout, not completeness of correspondence to actual simultaneous implementation bindings. Permanent rows cover pre-enlargement/after-restore/final retained diagnostics; active rows supplement the original declaration rows only while the operation construction envelope is enlarged.')
(OUT/'binding-map.json').write_bytes(encoded(binding_map))
result=dict(status='verified-host-value-operation-evidence-pending-independent-accounting-and-root-acceptance',
    receiptSHA256=sha(OUT/'receipt.json'),changedSourceFiles=changed,sourceClosureReconstruction=True,
    frozenOwnerSourceLiteral=True,sharedNumericBodyLiteral=True,layouts=layout_summary,
    fieldMap=field_map,binaries=runtime_lists,broadClippyExistingDiagnosticCount=len(lint[0]),
    broadClippyDiagnosticIdentitiesEqual=True,broadClippyIdentityFields=['title','primaryPath','line','column'],
    bindingMapSHA256=sha(OUT/'binding-map.json'),comparisons=receipt['comparisons'],
    limits=receipt['scope'])
(OUT/'verified-summary.json').write_bytes(encoded(result))
print(json.dumps(dict(status=result['status'],layouts=len(layout_summary),fields=sum(map(len,field_map.values())),binaries=len(runtime_lists),broadClippyDiagnostics=len(lint[0])),indent=2))
