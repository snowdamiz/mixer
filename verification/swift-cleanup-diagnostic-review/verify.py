#!/usr/bin/env python3
"""Offline sealed independent-review replay. Never launches retained binaries."""
import difflib,gzip,hashlib,json,pathlib,re,sys,tarfile
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda n:json.loads((H/n).read_text())
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()

def archive(manifest_name):
    manifest=read(manifest_name);result={}
    with tarfile.open(H/manifest_name.replace('-source-manifest.json','-source.tar.gz'))as t:
        for e in t:
            assert e.isfile()and not pathlib.PurePosixPath(e.name).is_absolute()and'..'not in pathlib.PurePosixPath(e.name).parts
            assert e.name in manifest and e.name not in result
            b=t.extractfile(e).read();assert sha(b)==manifest[e.name];result[e.name]=b
    assert set(result)==set(manifest);return result

def main():
    seal=read('seal.json');actual={str(p.relative_to(H))for p in H.rglob('*')if p.is_file()and p!=H/'seal.json'}
    assert actual==set(seal['files'])
    for n,h in seal['files'].items():assert sha((H/n).read_bytes())==h,n
    for n,h in seal['externalBindings'].items():assert sha((ROOT/n).read_bytes())==h,n
    from bootstrap import checked_packet
    initial=read('input-validation.json')
    for n,summary in initial['packets'].items():assert checked_packet(ROOT/'verification'/n)==summary
    for n,h in json.loads((ROOT/'verification/swift-cleanup-diagnostic/input-bindings.json').read_text()).items():assert sha((ROOT/n).read_bytes())==h,n
    r=read('receipt.json');assert r['status']=='independent-review-recommends-private-host-slice-acceptance'
    assert r['recommendation']=='accept-exact-candidate-for-root-integration'
    assert not any(r[k]for k in ['liveIntegrated','g08Accepted','nativeAccepted','physicalAccepted','publicInvocation','fullSwiftAccepted','gaAccepted'])
    assert not r['findings']
    b=archive('baseline-source-manifest.json');a=archive('candidate-source-manifest.json');assert len(b)==len(a)==128
    assert sha(enc(read('baseline-source-manifest.json')))==r['acceptedBaselineSourceSHA256']=='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329'
    assert sha(enc(read('candidate-source-manifest.json')))==r['candidateSourceSHA256']=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
    patch=''.join(''.join(difflib.unified_diff(b[n].decode().splitlines(True),a[n].decode().splitlines(True),fromfile='a/vm/'+n,tofile='b/vm/'+n))for n in sorted(b)if b[n]!=a[n])
    assert patch==(H/'candidate.patch').read_text()
    overlays=archive('adversarial-source-manifest.json')
    changed={n for n in a if a[n]!=overlays[n]}
    assert changed=={'src/experimental_swift_reactor/control_tests.rs','src/experimental_swift_reactor/memory_operations_tests.rs'}
    for n,fragment in [('src/experimental_swift_reactor/control_tests.rs','adversarial-control-tests.rs'),('src/experimental_swift_reactor/memory_operations_tests.rs','adversarial-memory-tests.rs')]:assert overlays[n]==a[n]+(H/fragment).read_bytes()
    manifests={}
    for p in H.glob('*-source-manifest.json'):
        archive(p.name);manifests[sha(p.read_bytes())]=p.name
    rows=read('commands.json');assert len(rows)==len(list((H/'commands').glob('*/receipt.json')))
    for row in rows:
        assert row==read(row['receipt'])|{'receipt':row['receipt']}
        assert row['exitCode']==row['expectedExitCode'] and not row['timedOut']and not row['groupCleanup']['after']
        assert row['sourceUnchanged']and row['sourceTreeBeforeSHA256']==row['sourceTreeAfterSHA256']
        if row['sourceTreeBeforeSHA256']is not None:
            assert row['sourceTreeBeforeSHA256']in manifests
            assert sha((H/pathlib.Path(row['receipt']).parent/'source-manifest.json').read_bytes())==row['sourceTreeBeforeSHA256']
        for stream in ['stdout','stderr']:assert sha(gzip.decompress((H/pathlib.Path(row['receipt']).parent/(stream+'.gz')).read_bytes()))==row[stream+'SHA256']
    for p in(H/'artifacts').glob('*/identity.json'):
        x=json.loads(p.read_text());body=gzip.decompress((p.parent/'executable.gz').read_bytes());assert sha(body)==x['executableSHA256']and len(body)==x['executableBytes']
        assert x['cargoArtifactFresh']is False and x['targetCreatedEmpty']
        for key in ['executableAfterListSHA256','executableAfterRunSHA256']:
            if x.get(key)is not None:assert x[key]==x['executableSHA256']
    runtime=read('runtime-results.json');assert [x['passed']for x in runtime]==[252,252,282,282]
    for x in runtime:
        n='independent-runtime-'+x['features']+'-'+x['profile'];assert x['sourceTreeSHA256']==r['candidateSourceSHA256']
        tests=read('artifacts/'+n+'/test-list.json');assert len(tests)==x['passed']and len(x['selectedTests'])==17
        text=gzip.decompress((H/'commands'/('execute-'+n)/'stdout.gz').read_bytes()).decode();assert f"test result: ok. {x['passed']} passed; 0 failed;"in text
    assert sum(x['passed']for x in read('frozen-runtime-results.json'))==64
    adversarial=read('adversarial-results.json');assert len(adversarial)==2 and all(x['passed']==3 and len(x['selectedTests'])==3 for x in adversarial)
    for profile in ['debug','release']:
        text=gzip.decompress((H/'commands'/('execute-adversarial-all-'+profile)/'stdout.gz').read_bytes()).decode();assert 'actualFunction=36 actualOffset=1729'in text and 'REVIEW_R02'in text and 'REVIEW_R03'in text
    import inventory
    schema=read('inventory-schema.json');observed=[];fn=[]
    for config in ['production','unit']:
        rows,f,captures=inventory.canonical(config,'final-qualified-mir');observed+=rows;fn+=f
    stable=lambda x:{k:v for k,v in x.items()if k not in ['ownerClass','mirLine']}
    assert list(map(stable,observed))==list(map(stable,[x for x in schema if x['config']!='source']))
    assert len(schema)==5516 and len(fn)==32
    from rebuild import completeness
    # Independent header selection is replayed without changing its retained output.
    import collect as c
    orig_save=c.save;c.save=lambda n,x:None
    old_manifest=c.manifest;c.manifest=lambda _:read('candidate-source-manifest.json')
    try:completeness()
    finally:c.save=orig_save;c.manifest=old_manifest
    from validate import mir_bodies
    q=read('accounting-qualification.json');assert q['preexistingTypeDeclarations']==329 and len(q['legacyMIR'])==24
    for config in ['production','unit']:
        old=mir_bodies(gzip.decompress((H/('baseline-mir-'+config+'.mir.gz')).read_bytes()).decode());new=mir_bodies(gzip.decompress((H/('final-qualified-mir-'+config+'.mir.gz')).read_bytes()).decode())
        for key,h in q['legacyMIR'].items():
            if not key.startswith(config+':'):continue
            suffix=key[len(config)+1:];names=[k for k in old if k==suffix or('control::'in k and k.endswith('::'+suffix))];assert len(names)==1
            assert old[names[0]]==new[names[0]]and sha(new[names[0]].encode())==h
    from source_audit import declarations
    declaration_count=0
    for n in b:
        if n.endswith('.rs'):
            before=declarations(b[n].decode());after=declarations(a[n].decode())
            for name,spans in before.items():assert after[name]==spans;declaration_count+=len(spans)
    assert declaration_count==363
    assert read('frozen-identity.json')['methodCount']==39 and read('frozen-identity.json')['frozenReservationBytes']==2912
    from layouts import verify_fields
    layouts=read('qualified-layouts.json');assert len(layouts)==16
    for x in layouts:
        if x['label']=='candidate':
            old=next(v for v in layouts if v['label']=='baseline'and all(v[k]==x[k]for k in ['features','profile','unit']))
            assert old['layout']['types']==x['layout']['types']and old['layout']['owners']==x['layout']['owners'];verify_fields(x['layout'],schema,x['unit'])
    from type_layouts import parse
    full=read('complete-owned-type-layout-replay.json');assert full['pairedContexts']==8
    for x in full['records']:
        measured={}
        for label in ['baseline','candidate']:
            name='build-qualified-'+label+'-'+x['features']+'-'+x['profile']+'-'+x['config'];text=''.join(gzip.decompress((H/'commands'/name/(s+'.gz')).read_bytes()).decode()for s in ['stdout','stderr']);measured[label]=parse(text)
        for name,layout in x['layouts'].items():assert measured['baseline'][name]==measured['candidate'][name]and all(layout[k]==measured['baseline'][name][k]for k in ['bytes','alignment','detail'])
    assert read('cleanup.json')['ownedScratchRemoved']and read('cleanup.json')['holderCheckEmpty']and not read('cleanup.json')['survivingOwnedGroups']
    print('PASS sealed independent cleanup diagnostic review:',len(seal['files']),'files;1068 library/68 diagnostic/64 Frozen/6 adversarial executions;5516 positions;16 metadata contexts;24 legacy MIR;Frozen39;recommend exact private host slice only')

if __name__=='__main__':main()
