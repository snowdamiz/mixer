#!/usr/bin/env python3
"""Check frozen compiler/metadata/ABI/privacy evidence; never executes VM/native code."""
from pathlib import Path
import hashlib, json, sys, tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def encoded(x): return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def archive_manifest(p):
    with tarfile.open(p) as t:
        return {m.name.removeprefix('vm/'):hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
def main():
    folder=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/json.loads((HERE/'seal.json').read_text())['results']
    seal_path=HERE/'seal.json'
    if seal_path.exists():
        seal=json.loads(seal_path.read_text())
        if folder.resolve()==(HERE/seal['results']).resolve():
            for name,digest in seal['bindings'].items():
                assert sha(ROOT/name)==digest,'frozen proposal changed: '+name
    r=json.loads((folder/'receipt.json').read_text())
    assert r['status']=='contract-compiler-layout-abi-privacy-preflight-only'
    assert r['productImplementationUnchanged']
    assert r['coordinatedLiveChangedPaths'] in [[],['tests/span_control_extraction.rs']]
    for name in ['implementationApplied','guestExecution','frameExecution','nativeRuntime','semanticAcceptance','accountingCompletenessAccepted']:
        assert r[name] is False, name
    source=json.loads((folder/'source-manifest.json').read_text())
    assert archive_manifest(folder/'source.tar.gz')==source
    assert sha(folder/'source.tar.gz')==r['sourceArchiveSHA256']
    assert len(source)==r['sourceFiles']==117
    assert hashlib.sha256(encoded(source)).hexdigest()==r['sourceTreeSHA256']=='5d1da3fedb28804ed8ddc271ce78461b58b06b8475b5cc8eb411226626bc199f'
    # The sole amended control.rs change is a read-only private-field leaf;
    # original owner/check/refund/meter source remains literal archived bytes.
    baseline=next(v for v in r['variants'] if v['label']=='baseline')
    candidate=next(v for v in r['variants'] if v['label']=='candidate')
    with tarfile.open(folder/baseline['archive']) as archive:
        original_control=archive.extractfile('vm/src/experimental_swift_reactor/control.rs').read()
    with tarfile.open(folder/candidate['archive']) as archive:
        candidate_control=archive.extractfile('vm/src/experimental_swift_reactor/control.rs').read()
    leaf=b'\nimpl ReservationTicket {\n    pub(crate) fn matches_layout(&self, category: SwiftReservationCategory, bytes: usize) -> bool {\n        self.category == category && self.bytes == bytes\n    }\n}\n'
    assert candidate_control==original_control+leaf
    closures=set()
    for v in r['variants']:
        m=json.loads((folder/v['manifest']).read_text())
        assert archive_manifest(folder/v['archive'])==m,v['label']
        assert sha(folder/v['archive'])==v['archiveSHA256']
        h=hashlib.sha256(encoded(m)).hexdigest()
        assert h==v['treeSHA256']; closures.add(h)
    commands={x['name']:x for x in r['commands']}
    retained=json.loads((folder/'qualifying-artifacts.json').read_text())
    assert sha(folder/retained['archive'])==retained['archiveSHA256']
    artifacts={x['id']:x for x in retained['artifacts']}
    assert len(artifacts)==24
    with tarfile.open(folder/retained['archive']) as archive:
        members={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    assert set(members)=={x['archiveMember'] for x in retained['artifacts']}
    for item in retained['artifacts']:
        data=members[item['archiveMember']]
        assert len(data)==item['bytes']
        assert hashlib.sha256(data).hexdigest()==item['sha256']
    for c in r['commands']:
        for stream in ['stdout','stderr']:
            assert sha(folder/c[stream])==c[stream+'SHA256'], c['name']
        if c['expectedError']:
            assert c['exitCode']!=0
            output=(folder/c['stdout']).read_text()+(folder/c['stderr']).read_text()
            assert c['expectedError'] in output
        else: assert c['exitCode']==0,c['name']
        if c.get('sourceTreeSHA256'): assert c['sourceTreeSHA256'] in closures,c['name']
        if c['bootstrap']: assert c['name'].endswith('-expansion')
    assert len(r['privacy'])==4
    assert {(c['config'],c['profile']) for c in r['comparisons']}=={(f,p) for f in ['swift','all'] for p in ['debug','release']}
    assert all(c['CExportsEqual'] for c in r['comparisons'])
    assert all(c['frozenMethodsEqual'] for c in r['comparisons'] if c['config']=='all')
    for config in ['swift','all']:
        for profile in ['debug','release']:
            entries=[x for x in r['abi'] if x['label'].endswith(config+'-'+profile)]
            assert len(entries)==2 and entries[0]['exports']==entries[1]['exports']
            for entry in entries:
                assert artifacts[entry['label']]['sha256']==entry['binarySHA256']
            if config=='all':
                names=[folder/(variant+'-'+config+'-'+profile+'-frozen-methods.json') for variant in ['baseline','candidate']]
                assert names[0].read_bytes()==names[1].read_bytes()
    schema=json.loads((folder/'inventory-schema.json').read_text())
    assert len({x['field'] for x in schema})==len(schema)
    measured={}
    for entry in r['layouts']:
        label=entry['label']; records=entry['records']
        run=commands[label+'-run']
        output=(folder/run['stdout']).read_text()
        parsed=[]
        for line in output.splitlines():
            at=line.find('AF_')
            if at>=0: parsed.append(line[at:])
        assert records==parsed,label
        binary=Path(run['argv'][0])
        artifact=artifacts[label]
        assert artifact['sha256']==entry['binarySHA256']
        assert artifact['originalPath']==str(binary)
        assert artifact['sourceTreeSHA256']==run['sourceTreeSHA256']
        if binary.exists(): assert sha(binary)==entry['binarySHA256']
        if 'unit' in label:
            listed=(folder/commands[label+'-list']['stdout']).read_text()
            assert 'experimental_swift_reactor::execution::af_layout_only: test' in listed.splitlines()
            assert run['argv'][1:]==['experimental_swift_reactor::execution::af_layout_only','--exact','--nocapture','--test-threads=1']
        types={}
        fields={}
        for line in records:
            if line.startswith(('AF_TYPE ','AF_EXISTING ')):
                marker,name_size=line.split(' ',1)
                name,size,align=name_size.rsplit(' ',2)
                types[name]=(int(size),int(align))
            if line.startswith('AF_FIELD '):
                _,name,offset,size,align=line.split()
                fields[name]=(int(offset),int(size),int(align))
        reservation=[x for x in records if x.startswith('AF_RESERVATION ')]
        assert len(reservation)==1
        if label.startswith('candidate'):
            assert set(fields)=={x['field'] for x in schema}
            for envelope,owner in [('permanent','PermanentPositions'),('active','ActivePositions')]:
                bounds=sorted(fields[x['field']] for x in schema if x['envelope']==envelope)
                size=types[owner][0]
                end=0
                for offset,width,align in bounds:
                    assert offset>=end and offset%align==0
                    end=offset+width
                assert end<=size
                measured[label+':'+envelope]=dict(fields=len(bounds),bytes=size,fieldBytes=sum(x[1] for x in bounds),padding=size-sum(x[1] for x in bounds))
            line=next(x for x in records if x.startswith('AF_FRAME_ENVELOPE '))
            _,active,nested,total=line.split()
            assert int(active)==types['ActivePositions'][0]
            assert int(nested)==119576
            assert int(total)==int(active)+int(nested)
        measured[label+':reservation']=reservation[0]
    assert len(r['layouts'])==16
    for config in ['swift','all']:
        for profile in ['debug','release']:
            for mode in ['production','unit']:
                candidates=[x for x in r['layouts'] if x['label'].endswith(config+'-'+profile+'-'+mode+'-metadata')]
                assert len(candidates)==2
                get=lambda x,prefix:[v for v in x['records'] if v.startswith(prefix)]
                baseline=next(x for x in candidates if x['label'].startswith('baseline'))
                candidate=next(x for x in candidates if x['label'].startswith('candidate'))
                if config=='all': assert get(baseline,'AF_FROZEN ')==get(candidate,'AF_FROZEN ')
                old=get(baseline,'AF_RESERVATION ')[0].split(); new=get(candidate,'AF_RESERVATION ')[0].split()
                assert int(new[1])>int(old[1]) and int(new[2])>int(old[2]) and new[3]==old[3]=='119576'
    nested=json.loads((folder/'nested-value-component.json').read_text())
    assert sha(ROOT/nested['map'])==nested['mapSHA256']
    assert source[nested['source']]==nested['sourceSHA256']
    model=json.loads((folder/commands['index-model']['stdout']).read_text())
    assert model['status']=='pass-index-model-only' and model['realFrames'] is False and model['realPins'] is False
    summary=dict(status='verified-saved-contract-preflight-only',commands=len(r['commands']),positions=len(schema),metadataExecutions=16,retainedPortableArtifacts=24,measured=measured,frameRuntimeAcceptance=False)
    (folder/'verified-summary.json').write_bytes(encoded(summary))
    print(json.dumps({k:v for k,v in summary.items() if k!='measured'},sort_keys=True))
if __name__=='__main__': main()
