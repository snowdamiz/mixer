#!/usr/bin/env python3
"""Independent offline checks of the producer's frozen declaration packet.

No import of producer collectors/verifiers; no product or native execution.
"""
import hashlib, json, pathlib, sys, tarfile

def encoded(obj): return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def digest(data): return hashlib.sha256(data).hexdigest()
def require(ok, text):
    if not ok: raise AssertionError(text)
def archive(path):
    with tarfile.open(path) as tar:
        result={}
        for item in tar.getmembers():
            if not item.isfile(): continue
            require(item.name.startswith('vm/') and '..' not in pathlib.PurePosixPath(item.name).parts,'unsafe archive entry')
            name=item.name[3:]
            require(name not in result,'duplicate archive path')
            result[name]=tar.extractfile(item).read()
        return result

def verify(packet):
    receipt=json.loads((packet/'receipt.json').read_text())
    require(receipt['status']=='contract-compiler-layout-abi-privacy-preflight-only','producer packet incomplete')
    require(not any(receipt[k] for k in ['implementationApplied','guestExecution','frameExecution','nativeRuntime','semanticAcceptance','accountingCompletenessAccepted']),'packet scope overclaim')
    source=archive(packet/'source.tar.gz'); source_manifest={k:digest(v) for k,v in sorted(source.items())}
    require(source_manifest==json.loads((packet/'source-manifest.json').read_text()),'source manifest mismatch')
    require(digest(encoded(source_manifest))==receipt['sourceTreeSHA256'],'source tree mismatch')
    require(digest((packet/'source.tar.gz').read_bytes())==receipt['sourceArchiveSHA256'],'source archive mismatch')
    accepted=json.loads((packet/'accepted-macro-binding.json').read_text())
    require(accepted['candidateTreeSHA256']==receipt['sourceTreeSHA256'],'accepted root binding mismatch')
    retained=json.loads((packet/'qualifying-artifacts.json').read_text())
    require(digest((packet/retained['archive']).read_bytes())==retained['archiveSHA256'],'portable binary archive changed')
    retained_bytes={}
    with tarfile.open(packet/retained['archive']) as tar:
        for member in tar.getmembers():
            if member.isfile():
                require(member.name.startswith('artifacts/') and '..' not in pathlib.PurePosixPath(member.name).parts,'unsafe binary member')
                require(member.name not in retained_bytes,'duplicate binary member')
                retained_bytes[member.name]=tar.extractfile(member).read()
    require(len(retained['artifacts'])==len(retained_bytes)==24,'portable binary matrix missing')
    for artifact in retained['artifacts']:
        data=retained_bytes[artifact['archiveMember']]
        require(len(data)==artifact['bytes'] and digest(data)==artifact['sha256'],'portable binary hash/length changed')
        expected=next(x for x in receipt['layouts'] if x['label']==artifact['id']) if artifact['kind']=='metadata' else next(x for x in receipt['abi'] if x['label']==artifact['id'])
        require(expected['binarySHA256']==artifact['sha256'],'portable binary not qualifying compiler artifact')
    require(sum(x['kind']=='metadata' for x in retained['artifacts'])==16 and sum(x['kind']=='abi-dylib' for x in retained['artifacts'])==8,'portable binary kinds incomplete')
    commands={c['name']:c for c in receipt['commands']}
    require(len(commands)==len(receipt['commands']),'duplicate command identity')
    for c in commands.values():
        for stream in ['stdout','stderr']:
            require(digest((packet/c[stream]).read_bytes())==c[stream+'SHA256'],f'{c["name"]} {stream} changed')
        output=(packet/c['stdout']).read_text()+(packet/c['stderr']).read_text()
        require((c['exitCode']!=0 and c['expectedError'] in output) if c.get('expectedError') else c['exitCode']==0,f'{c["name"]} failed')
    needed={'revision','rustc-version','cargo-version','python-version'}
    for config in ['default','span','swift','all']:
        for profile in ['debug','release']: needed.add(f'candidate-{config}-{profile}-check')
    for config in ['swift','all']:
        for profile in ['debug','release']:
            for label in ['baseline','candidate']:
                for suffix in ['expansion','abi-build','abi-exports']: needed.add(f'{label}-{config}-{profile}-{suffix}')
                for mode in ['production','unit']:
                    for suffix in ['build','run']+(['list'] if mode=='unit' else []): needed.add(f'{label}-{config}-{profile}-{mode}-metadata-{suffix}')
    needed.update(['private-frame-phase','private-control-constructor','no-public-invoke','index-model'])
    require(set(commands)==needed,'exact command matrix mismatch')
    variants={v['label']:v for v in receipt['variants']}
    require(len(variants)==7,'variant matrix mismatch')
    decoded={}
    for label,v in variants.items():
        content=archive(packet/v['archive']); decoded[label]=content
        manifest={k:digest(data) for k,data in sorted(content.items())}
        require(manifest==json.loads((packet/v['manifest']).read_text()),label+' manifest mismatch')
        require(digest(encoded(manifest))==v['treeSHA256'],label+' tree mismatch')
        require(digest((packet/v['archive']).read_bytes())==v['archiveSHA256'],label+' archive mismatch')
    variant_digests={v['treeSHA256'] for v in variants.values()}
    for c in commands.values():
        if c.get('sourceTreeSHA256'):require(c['sourceTreeSHA256'] in variant_digests,'command closure not archived')
        require(not c.get('bootstrap') or c['name'].endswith('-expansion'),'bootstrap used outside expansion')
    require(decoded['baseline']==source,'baseline source differs')
    changed={k for k in source.keys()|decoded['candidate'].keys() if source.get(k)!=decoded['candidate'].get(k)}
    require(changed=={'src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/active_contract.rs','src/experimental/execution/mod.rs','src/experimental_swift_reactor/execution_tests.rs','src/experimental_swift_reactor/value_operations.rs'},'unexpected candidate scope')
    require(decoded['candidate']['src/experimental_swift_reactor/execution_tests.rs']==source['src/experimental_swift_reactor/execution_tests.rs'].replace(b'execution_header: None,',b'execution_header: None,\n            frame_cleanup: Default::default(),',1),'unexpected test-fixture change')
    expected_execution=source['src/experimental_swift_reactor/execution.rs'].decode()
    for old,new in [
        ('pub execution_header: Option<ReservationTicket>,','pub execution_header: Option<ReservationTicket>,\n    pub frame_cleanup: active_contract::FrameCleanupState,'),
        ('execution_header: None,','execution_header: None,\n            frame_cleanup: active_contract::FrameCleanupState::empty(),'),
        ('header.checked_add(value_operations::PERMANENT_BYTES)','match header.checked_add(value_operations::PERMANENT_BYTES) { Some(n) => n.checked_add(active_contract::PERMANENT_BYTES), None => None }'),
    ]:
        require(expected_execution.count(old)==1,'ambiguous expected execution overlay')
        expected_execution=expected_execution.replace(old,new,1)
    expected_execution+='\n#[path="active_contract.rs"] mod active_contract;\n'
    require(decoded['candidate']['src/experimental_swift_reactor/execution.rs']==expected_execution.encode(),'unexpected execution owner/source change')
    require(decoded['candidate']['src/experimental_swift_reactor/value_operations.rs']==source['src/experimental_swift_reactor/value_operations.rs'].replace(b'const VALUE_OPERATION_BYTES: Option<usize>',b'pub(super) const VALUE_OPERATION_BYTES: Option<usize>',1),'nested primitive source changed beyond private const visibility')
    component=json.loads((packet/'nested-value-component.json').read_text())
    require(component['sourceSHA256']==digest(source[component['source']]),'nested primitive source binding mismatch')
    component_path=pathlib.Path(__file__).resolve().parents[2]/component['map']
    require(digest(component_path.read_bytes())==component['mapSHA256'],'nested primitive map changed')
    baseline=source['src/experimental/execution/mod.rs']
    candidate=decoded['candidate']['src/experimental/execution/mod.rs']
    require(candidate.startswith(baseline),'frozen execution source was modified')
    tail=candidate[len(baseline):].decode()
    require(tail.count('fn ')==1 and 'pub(crate) const fn function_entry' in tail and 'kind: Kind::Function' in tail,'unexpected frozen leaf addition')
    schema=json.loads((packet/'inventory-schema.json').read_text())
    require(len({r['field'] for r in schema})==len(schema),'duplicate inventory field')
    expected_labels={f'{l}-{c}-{p}-{m}-metadata' for l in ['baseline','candidate'] for c in ['swift','all'] for p in ['debug','release'] for m in ['production','unit']}
    require({r['label'] for r in receipt['layouts']}==expected_labels,'layout matrix mismatch')
    all_layout={}; measured=[]
    for record in receipt['layouts']:
        label=record['label']; raw=(packet/commands[label+'-run']['stdout']).read_text()
        run=commands[label+'-run']
        binary=pathlib.Path(run['argv'][0])
        if binary.exists():require(digest(binary.read_bytes())==record['binarySHA256'],label+' original binary changed')
        if '-unit-' in label:
            require(run['argv'][1:]==['experimental_swift_reactor::execution::af_layout_only','--exact','--nocapture','--test-threads=1'],'unit metadata command not exact')
            require('experimental_swift_reactor::execution::af_layout_only: test' in (packet/commands[label+'-list']['stdout']).read_text().splitlines(),'unit metadata identity missing')
        parsed=[line[line.index('AF_'):] for line in raw.splitlines() if 'AF_' in line]
        require(parsed==record['records'],label+' parsed output mismatch')
        types={}; fields={}; existing={}; bounds=None; reservations=None; frozen=None; frame_envelope=None
        for line in parsed:
            words=line.split()
            if words[0]=='AF_TYPE':types[words[1]]=(int(words[2]),int(words[3]))
            if words[0]=='AF_FIELD':fields[words[1]]=tuple(map(int,words[2:]))
            if words[0]=='AF_EXISTING':existing[words[1]]=tuple(map(int,words[2:]))
            if words[0]=='AF_BOUNDS':bounds=tuple(map(int,words[1:]))
            if words[0]=='AF_FRAME_ENVELOPE':frame_envelope=tuple(map(int,words[1:]))
            if words[0]=='AF_RESERVATION':reservations=tuple(map(int,words[1:]))
            if words[0]=='AF_FROZEN':frozen=tuple(map(int,words[1:]))
        if label.startswith('candidate-'):
            require(set(fields)=={r['field'] for r in schema},label+' missing field')
            require(bounds==(types['PermanentPositions'][0],types['ActivePositions'][0]),label+' bounds not positive actual struct sizes')
            require(frame_envelope==(bounds[1],reservations[2],bounds[1]+reservations[2]),label+' nested primitive not added in full')
            for envelope,owner in [('permanent','PermanentPositions'),('active','ActivePositions')]:
                slots=[]; size,align=types[owner]
                require(size>0 and size%align==0,'invalid structure layout')
                for row in [r for r in schema if r['envelope']==envelope]:
                    offset,n,a=fields[row['field']]
                    require(n>0 and a>0 and offset%a==0 and offset+n<=size,'field out of bounds')
                    slots.append((offset,offset+n,row['field']))
                slots.sort()
                require(all(a[1]<=b[0] for a,b in zip(slots,slots[1:])),envelope+' fields overlap')
            measured.append({'label':label,'permanentBytes':bounds[0],'activeBytes':bounds[1],'inventoryFields':len(fields),'nestedPrimitiveBytes':frame_envelope[1],'frameOperationBytes':frame_envelope[2]})
        all_layout[label]=(existing,reservations,frozen)
    # Original owner changes are exactly the proposed inline State extension;
    # every other chosen actual owner and the literal frozen reservation match.
    for config in ['swift','all']:
        for profile in ['debug','release']:
            for mode in ['production','unit']:
                a=all_layout[f'baseline-{config}-{profile}-{mode}-metadata']; b=all_layout[f'candidate-{config}-{profile}-{mode}-metadata']
                require(set(a[0])==set(b[0]),'owner type set mismatch')
                require(all(a[0][k]==b[0][k] for k in a[0] if k not in ['SwiftExecutionState','SwiftReactorInstance']),'unexpected original owner layout change')
                require(a[2]==b[2],'frozen layout/reservation changed')
                require(a[1][2]==b[1][2],'accepted value operation bound changed')
                require(b[1][0]>a[1][0],'new header inventory not positively added')
    require(len(receipt['comparisons'])==4 and all(c['CExportsEqual'] for c in receipt['comparisons']),'ABI comparisons missing')
    require(len(receipt['abi'])==8,'ABI matrix missing')
    for config in ['swift','all']:
        for profile in ['debug','release']:
            a=next(r for r in receipt['abi'] if r['label']==f'baseline-{config}-{profile}');b=next(r for r in receipt['abi'] if r['label']==f'candidate-{config}-{profile}')
            require(a['exports']==b['exports'] and bool(a['exports']),'C exports mismatch')
            for r in [a,b]:
                require(r['exports']==sorted(x for x in (packet/commands[r['label']+'-abi-exports']['stdout']).read_text().splitlines() if x.startswith('_mixer_')),'ABI output mismatch')
    require(len(receipt['privacy'])==3,'privacy matrix missing')
    return {'producerReceiptSHA256':digest((packet/'receipt.json').read_bytes()),'sourceTreeSHA256':receipt['sourceTreeSHA256'],'commandsVerified':len(commands),'variantsVerified':len(variants),'layoutsVerified':len(receipt['layouts']),'portableArtifactsVerified':len(retained['artifacts']),'inventoryRows':len(schema),'layoutMeasurements':measured,'scope':'Declaration/compiler/layout/ABI/privacy only. No active-frame semantic or actual binding completeness acceptance.'}

if __name__=='__main__':
    packet=pathlib.Path(sys.argv[1]).resolve()
    print(json.dumps(verify(packet),indent=2))
