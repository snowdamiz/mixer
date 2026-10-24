#!/usr/bin/env python3
"""Offline root-auditable replay verification; writes nothing and runs no binary."""
from pathlib import Path
import gzip, hashlib, json, re, sys, tarfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
enc=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
sha=lambda value:hashlib.sha256(value).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def output(name,stream='stdout'):
    return gzip.decompress((HERE/'commands'/name/(stream+'.gz')).read_bytes())
def parse(data):
    result={k:{} for k in ['types','classes','fields','totals','owners']}
    for line in data.decode().splitlines():
        if 'HC_' not in line:continue
        kind,name,*values=line[line.index('HC_'):].split();values=list(map(int,values))
        category={'HC_TYPE':'types','HC_CLASS':'classes','HC_FIELD':'fields','HC_TOTAL':'totals','HC_OWNER':'owners'}[kind]
        assert name not in result[category]
        result[category][name]=(dict(bytes=values[0],alignment=values[1]) if category in ['types','classes']
            else dict(offset=values[0],bytes=values[1],alignment=values[2]) if category=='fields' else values[0])
    return result
def verify_fields(layout,schema,unit):
    wanted={r['field'] for r in schema if unit or r['config']!='unit'}
    assert set(layout['fields'])==wanted
    end={}
    for row in sorted((r for r in schema if r['field'] in wanted),key=lambda r:(r['ownerClass'],layout['fields'][r['field']]['offset'])):
        value=layout['fields'][row['field']];cls=row['ownerClass']
        assert value['offset']>=end.get(cls,0)
        assert value['offset']%value['alignment']==0
        end[cls]=value['offset']+value['bytes']
        assert end[cls]<=layout['classes'][cls]['bytes']
def verify(sealed=True):
    if sealed:
        seal=read('receipt.json')
        for name,expected in seal['bindings'].items():assert sha((ROOT/name).read_bytes())==expected,name
        # Exclude only this exact seal, never other files named receipt.json.
        expected_paths={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'receipt.json'}
        expected_paths.add('docs/swift-host-dispatch-layout-replay.md')
        assert set(seal['bindings'])==expected_paths
    records=read('layouts.json');assert len(records)==16
    assert len({x['cargoTarget'] for x in records})==16
    closures=read('source-closures.json');source_manifests={}
    for label,expected in closures.items():
        m=read('inputs/metadata-'+label+'-source-manifest.json')
        assert len(m)==126 and sha(enc(m))==expected
        with tarfile.open(HERE/('inputs/metadata-'+label+'-source.tar.gz')) as tar:
            actual={entry.name:sha(tar.extractfile(entry).read()) for entry in tar.getmembers() if entry.isfile()}
        assert actual==m
        source_manifests[expected]=m
    commands={}
    for p in sorted((HERE/'commands').glob('*/receipt.json')):
        row=json.loads(p.read_text());name=p.parent.name
        expected=row['expectedSourceTreeSHA256']
        assert expected in source_manifests and row['sourceFiles']==126
        assert row['sourceTreeBeforeSHA256']==row['sourceTreeAfterSHA256']==expected
        assert row['sourceUnchanged'] and row['exitCode']==0
        m=json.loads((p.parent/'source-manifest.json').read_text())
        assert m==source_manifests[expected] and sha(enc(m))==row['sourceManifestSHA256']
        for stream in ['stdout','stderr']:assert sha(output(name,stream))==row[stream+'SHA256']
        commands[name]=row
    assert len(commands)==44,len(commands)
    schema=read('inputs/inventory-schema.json');proposed=read('inputs/historical-proposed-layouts.json')
    lists={}
    for record in records:
        name=record['context'];unit=record['unit'];label=record['label'];expected=closures[label]
        assert record['sourceTreeSHA256']==expected and record['sourceFiles']==126
        assert record['targetCreatedEmpty'] and record['cargoArtifactFresh'] is False
        expected_target='target-'+expected+'-'+record['features']+'-'+record['profile']+'-'+('unit' if unit else 'production')
        assert Path(record['cargoTarget']).name==expected_target
        artifact=read(record['cargoArtifact'])
        assert artifact['executable']==record['exactExecutablePath'] and artifact['fresh'] is False
        messages=[json.loads(line) for line in output('build-'+name).decode().splitlines() if line]
        assert artifact in messages
        build=commands['build-'+name]
        assert build['environment']['CARGO_TARGET_DIR']==record['cargoTarget']
        assert '--message-format=json-render-diagnostics' in build['argv']
        assert build['sourceTreeBeforeSHA256']==expected
        binary=gzip.decompress((HERE/record['retainedExecutable']).read_bytes())
        assert len(binary)==record['executableBytes'] and sha(binary)==record['executableSHA256']
        assert record['executableBeforeRunSHA256']==record['executableAfterRunSHA256']==sha(binary)
        exact_path=record['exactExecutablePath'];run=commands['execute-'+name]
        assert run['argv'][0]==exact_path and run['sourceTreeBeforeSHA256']==expected
        assert run['environment']['CARGO_TARGET_DIR']==record['cargoTarget']
        if unit:
            assert artifact['profile']['test'] and artifact['target']['name']=='mixer_vm'
            assert artifact['target']['src_path'].endswith('/src/lib.rs')
            list_command=commands['testlist-'+name]
            assert list_command['argv']==[exact_path,'--list']
            assert record['executableBeforeListSHA256']==record['executableAfterListSHA256']==sha(binary)
            tests=read(record['fullUnitTestList'])
            assert tests==[line.removesuffix(': test') for line in output('testlist-'+name).decode().splitlines() if line.endswith(': test')]
            wanted='experimental_swift_reactor::execution::frame_operations::host_contract_layout_only'
            assert tests.count(wanted)==1 and len(tests)==record['fullUnitTestCount']==(201 if record['features']=='swift' else 230)
            assert run['argv']==[exact_path,'--exact',wanted,'--nocapture','--test-threads=1']
            assert 'test result: ok. 1 passed; 0 failed;' in output('execute-'+name).decode()
            lists[(label,record['features'],record['profile'])]=tests
        else:
            assert artifact['target']['name']=='host_contract_layout' and 'bin' in artifact['target']['kind']
            assert run['argv']==[exact_path] and record['fullUnitTestList'] is None
        measured=parse(output('execute-'+name));assert measured==record['layout']
        old=next(v for v in proposed if (v['label'],v['features'],v['profile'],v['unit'])==(label,record['features'],record['profile'],unit))
        assert measured=={k:old[k] for k in measured}
        if label=='candidate':verify_fields(measured,schema,unit)
        assert measured['totals']['ticket_max']==86
        assert measured['totals']['state_limit']==134217728 and measured['totals']['combined_limit']==268435456
    for record in records:
        if record['label']!='candidate':continue
        base=next(v for v in records if (v['label'],v['features'],v['profile'],v['unit'])==('baseline',record['features'],record['profile'],record['unit']))
        for key in ['types','owners']:assert base['layout'][key]==record['layout'][key]
        for key,value in base['layout']['totals'].items():assert record['layout']['totals'][key]==value
        if record['unit']:assert lists[('baseline',record['features'],record['profile'])]==lists[('candidate',record['features'],record['profile'])]
    frozen=read('frozen-original-file-bindings.json')
    for name,expected in frozen.items():assert sha((ROOT/name).read_bytes())==expected,name
    if sealed:
        for cleanup in seal['cleanup']['directories']:assert cleanup['removed'] and not Path(cleanup['scratch']).exists()
    return dict(status='verified',freshContexts=16,exactRetainedExecutables=16,fullUnitLists=8,
        boundCommandReceipts=len(commands),sourceClosures=closures,allLayoutFieldsMatch=True,
        allOriginalOwnerLayoutsMatch=True,positiveFields=len(schema),originalFrozenFilesUnchanged=len(frozen),
        noHostImportExecuted=True,noRuntimeAcceptance=True,sealed=sealed)
if __name__=='__main__':print(json.dumps(verify(sealed='--preseal' not in sys.argv),sort_keys=True,indent=2))
