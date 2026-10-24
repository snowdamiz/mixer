#!/usr/bin/env python3
"""Verify self-contained saved review evidence, or replay native tests afresh."""
from pathlib import Path
import datetime, hashlib, json, os, re, shutil, subprocess, sys, tarfile, tempfile

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else max((HERE/'results').iterdir())
EXECUTE='--execute' in sys.argv[2:]
encode=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(encode(x)).hexdigest()
def manifest(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
receipt=json.loads((OUT/'receipt.json').read_text())
assert receipt['status']=='passed-selected-native-outcomes-accounting-review-separate'
source=json.loads((OUT/'source-manifest.json').read_text())
assert len(source)==receipt['sourceCount'] and digest(source)==receipt['sourceTreeSHA256']
commands={x['name']:x for x in receipt['commands']}
assert len(commands)==len(receipt['commands'])
for row in commands.values():
    assert row['exit']==0 and sha(OUT/row['log'])==row['logSHA256']
    if row['target']: assert row['sourceBeforeAfterVerified']
producer=json.loads((OUT/'inputs/producer-receipt.json').read_text())
producer_commands={x['name']:x for x in producer['commands']}
for row in producer_commands.values():
    assert sha(OUT/'producer-logs'/row['log'])==row['logSHA256']
assert sha(OUT/'candidate-source.tar.gz')==producer['candidateSourceArchiveSHA256']
assert sha(OUT/'baseline-source.tar')==producer['baselineSourceArchiveSHA256']
assert receipt['sourceTreeSHA256']==producer['candidateSourceTreeSHA256']
counts=[]
for binary in receipt['binaries']:
    listed=(OUT/commands[binary['listCommand']]['log']).read_text()
    identities=[s[:-6] for s in listed.splitlines() if s.endswith(': test')]
    assert identities==binary['listedTests']
    runtime=(OUT/commands[binary['runCommand']]['log']).read_text()
    actual=re.findall(r'^test ([^ ]+) \.\.\. ok$',runtime,re.M)
    assert sorted(actual)==sorted(binary['selectedTests'])
    assert re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',runtime)==[(str(binary['passed']),'0')]
    path=Path(binary['path'])
    if path.exists(): assert sha(path)==binary['sha256']
    counts.append(dict(label=binary['label'],passed=len(actual),ignored=0,sourceTreeSHA256=binary['sourceTreeSHA256']))
assert len(counts)==8 and sum(x['passed'] for x in counts)==92
# Reconstruct source closures in a temporary directory; no producer paths are modified.
with tempfile.TemporaryDirectory(prefix='mixer-value-review-verify-') as temp:
    temp=Path(temp)
    for label,archive in [('baseline','baseline-source.tar'),('product','candidate-source.tar.gz'),('derived','derived-test-source.tar.gz')]:
        with tarfile.open(OUT/archive) as tf:tf.extractall(temp/label,filter='data')
    base=manifest(temp/'baseline/vm')
    assert base==json.loads((OUT/'inputs/producer-baseline-product-closure.json').read_text())
    assert manifest(temp/'product/vm')==source
    derived=manifest(temp/'derived/vm')
    assert derived==json.loads((OUT/'derived-source-manifest.json').read_text())
    glue='\n#[cfg(test)] #[path = "independent_value_review_tests.rs"] mod independent_value_review_tests;\n'
    operation='src/experimental_swift_reactor/value_operations.rs'
    assert (temp/'derived/vm'/operation).read_bytes()==(temp/'product/vm'/operation).read_bytes()+glue.encode()
    assert (temp/'derived/vm/src/experimental_swift_reactor/independent_value_review_tests.rs').read_bytes()==(OUT/'inputs/independent_tests.rs').read_bytes()
    assert all(derived[p]==expected for p,expected in source.items() if p!=operation)
    assert source['src/experimental/execution/mod.rs']==base['src/experimental/execution/mod.rs']
    # Rebuild the exact metadata-only input closures without compiling or sharing targets.
    for label,original_label in [('baseline','baseline'),('candidate','product')]:
        destination=temp/(label+'-metadata')/'vm'
        shutil.copytree(temp/original_label/'vm',destination)
        execution=destination/'src/experimental_swift_reactor/execution.rs'
        execution.write_text(execution.read_text()+'\n'+(OUT/'inputs/producer-owner-layout-probe.rs').read_text())
        calls='execution::operations_owner_layout_probe();'
        if label=='candidate':
            metadata_operation=destination/'src/experimental_swift_reactor/value_operations.rs'
            metadata_operation.write_text(metadata_operation.read_text()+'\n'+(OUT/'inputs/producer-operation-layout-probe.rs').read_text())
            calls+=' execution::value_operations::operations_layout_probe();'
        module=destination/'src/experimental_swift_reactor/mod.rs'
        module.write_text(module.read_text()+'\npub(crate) fn value_layout_probe(){'+calls+'}\n')
        lib=destination/'src/lib.rs'
        lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn value_layout_probe(){experimental_swift_reactor::value_layout_probe();}\n')
        (destination/'examples').mkdir(exist_ok=True)
        (destination/'examples/value-layout.rs').write_text('fn main(){mixer_vm::value_layout_probe();}\n')
        execution.write_text(execution.read_text()+'\n#[cfg(test)] #[test] fn value_layout_only(){super::value_layout_probe();}\n')
        assert manifest(destination)==json.loads((OUT/'inputs'/('producer-'+label+'-layout-closure.json')).read_text())
    shared=[]
    for label in ['baseline','product']:
        body=(temp/label/'vm/src/experimental/execution/borrowed.rs').read_text()
        shared.append(body[body.index('    if saturating {',body.index(' fn numeric<')):])
    assert shared[0]==shared[1]
    original=(temp/'product/vm'/operation).read_text()
    assert 'const VALUE_OPERATION_BYTES:' in original
    assert original.split('pub(crate) fn value_operation_bytes()',1)[1].split('\n}',1)[0].strip()=='-> Option<usize> {\n    VALUE_OPERATION_BYTES'
    # The declared-field parser only checks evidence correspondence; review is not OTA authorization.
    field_map={}
    for inventory in ['PermanentPositions','ActivePositions']:
        body=original.split('struct '+inventory+' {',1)[1].split('\n}',1)[0]
        body='\n'.join(line for line in body.splitlines() if not line.lstrip().startswith('//'))
        depth=0;start=0;fields={}
        for i,c in enumerate(body):
            if c in '([{<':depth+=1
            elif c in ')]}>':depth-=1
            elif c==',' and depth==0:
                declaration=body[start:i].strip();start=i+1
                if declaration:
                    name,shape=declaration.split(':',1);fields[name.strip()]=' '.join(shape.split())
        assert depth==0 and not body[start:].strip()
        field_map[inventory]=fields
    binding=json.loads((OUT/'inputs/producer-binding-map.json').read_text())
    assert binding['sourceTreeSHA256']==receipt['sourceTreeSHA256']
    for inventory,fields in field_map.items():
        actual={x['name']:x['declaredShape'] for x in binding['positions'] if x['inventory']==inventory}
        assert actual==fields
    for row in producer['layouts']:
        log=(OUT/'producer-logs'/producer_commands[row['command']]['log']).read_text()
        markers=['value_owner|','value_owner_field|','value_bounds|','value_inventory|','value_position|']
        records=[]
        for line in log.splitlines():
            indices=[line.index(marker) for marker in markers if marker in line]
            if indices:records.append(line[min(indices):])
        assert records==row['records']
        assert any(x.startswith('value_owner|SwiftExecutionState|') for x in records)
        if row['label']!='candidate':continue
        for inventory,fields in field_map.items():
            positions=[x.split('|') for x in row['records'] if x.startswith('value_position|'+inventory+'|')]
            assert {x[2] for x in positions}==set(fields)
            intervals=sorted((int(x[3]),int(x[3])+int(x[4])) for x in positions if int(x[4]))
            assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
            total=int(next(x.split('|')[2] for x in row['records'] if x.startswith('value_inventory|'+inventory+'|')))
            assert max(x[1] for x in intervals)<=total
    # All saved raw Frozen traces must agree, not only the producer's Boolean claim.
    traces=[]
    for profile in ['debug','release']:
        sides=[]
        for label in ['baseline','candidate']:
            result=[]
            for row in producer['binaries']:
                if row['configuration']!=label+'-all-'+profile:continue
                log=(OUT/'producer-logs'/producer_commands[row['runCommand']]['log']).read_text()
                result.extend(x[x.index('numeric_trace '):] for x in log.splitlines() if 'numeric_trace ' in x)
            sides.append(result)
        assert sides[0]==sides[1] and len(sides[0])==454
        traces.append(dict(profile=profile,records=454,sha256=digest(sides[0])))
    lint=[]
    for label in ['baseline','candidate']:
        text=(OUT/'producer-logs'/producer_commands[label+'-clippy-broad']['log']).read_text()
        identities=[]
        for block in re.split(r'(?=^error:)',text,flags=re.M):
            if not block.startswith('error:') or block.startswith('error: could not compile'):continue
            location=re.search(r'-->\s+([^\n]+?):(\d+):(\d+)',block)
            assert location
            identities.append((block.splitlines()[0],*location.groups()))
        lint.append(identities)
    assert sorted(lint[0])==sorted(lint[1]) and len(lint[0])==26
    replay=[]
    if EXECUTE:
        env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
        # New targets for every source/config/profile. No metadata source is involved.
        for binary in receipt['binaries']:
            label=binary['label'];kind='derived' if label.startswith('independent-') else 'product'
            dest=temp/kind/'vm'
            target=temp/(label+'-target')
            env['CARGO_TARGET_DIR']=str(target)
            argv=['cargo','test','--locked','--offline','--lib']
            argv+=['--all-features'] if '-all-' in label else ['--features','experimental-swift-reactor']
            if label.endswith('-release'):argv+=['--release']
            argv+=['independent_values_' if kind=='derived' else 'swift_values_','--','--test-threads=1']
            start=manifest(dest)
            p=subprocess.run(argv,cwd=dest,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
            assert p.returncode==0 and manifest(dest)==start,p.stdout.decode(errors='replace')
            summary=re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',p.stdout.decode())
            assert summary==[(str(binary['passed']),'0')]
            replay.append(dict(label=label,argv=argv,passed=binary['passed'],logSHA256=hashlib.sha256(p.stdout).hexdigest()))
summary=dict(status='verified-saved-independent-review-evidence',sourceTreeSHA256=receipt['sourceTreeSHA256'],
    counts=counts,producerBinaries=len(receipt['producerBinaryChecks']),producerLayoutConfigurations=len(receipt['producerRawLayoutsVerified']),
    fields=binding['fields'],typedPositions=binding['typedPositions'],frozenTraces=traces,broadClippySameExistingIdentities=26,
    runtimeBodyInstrumented=False,derivedTestOnlyGlue=True,replayed=replay,
    interpretation='Completeness is a separate source review recorded in accounting-audit.json and the review document; typed layouts alone do not prove it.')
(OUT/'verified-summary.json').write_bytes(encode(summary))
print(json.dumps({k:summary[k] for k in ['status','sourceTreeSHA256','fields','typedPositions','producerBinaries']},indent=2))
