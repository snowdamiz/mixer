#!/usr/bin/env python3
"""Independent, bounded raw-decoder/semantic review, never device discovery.
Each JVM variant compiles a new copy of the pinned production source closure.
The producer's large cross-language corpus is audited without executing it again.
"""
from pathlib import Path
import argparse, base64, datetime, gzip, hashlib, json, subprocess, sys, time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/android-appearance-v2-resolution/candidate-5'
EXPECTED_RECEIPT='4fe1e9500ed24e2e145b58a8c8e11bfc58811f282c86bd857313cb50bf51756f'
EXPECTED_INPUT='7ab9c87aabdd15fe4c660674012234aefc183ce04ae7c7a43d112abc53613d26'
JAVA=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home/bin/java')
sha=lambda b:hashlib.sha256(b).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('candidate');args=parser.parse_args()
assert args.candidate and '/' not in args.candidate and args.candidate not in ('.','..')
OUT=HERE/args.candidate;OUT.mkdir(exist_ok=False)
source_files=[f'native/android/app/src/dev/mixer/android/{name}.java' for name in
              ['AppearanceDescriptorV2','AppearanceGeometryV2','AppearanceResolverV2','Json','UiPacket']]
review_files=['verification/android-v2-resolver-independent-review/ReviewProbe.java',
              'verification/android-v2-resolver-independent-review/run_review.py']
paths=source_files+review_files+['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md',
    'docs/android-appearance-v2-resolution.md','docs/ui-appearance-resolution-v2.md',
    'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json',
    'verification/android-appearance-v2-resolution/candidate-5/receipt.json',
    'verification/android-appearance-v2-resolution/verify_seal.py']
manifest={}
for relative in paths:
    data=(ROOT/relative).read_bytes();p=OUT/'inputs'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    manifest[relative]=sha(data)
receipt=dict(format='mixer.android-v2-resolver-independent-review.1',status='running',
    startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    sourceGitTree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
    inputManifest=manifest,inputTreeSHA256=sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()),
    commands=[],artifacts={},variantSourceManifests={},findings=[],
    scope='Reviewer-authored JVM default/-Xint raw-decoder semantic oracle plus independent audit of frozen actual Swift/JVM output streams.',
    limitations=['No new Swift corpus execution; frozen actual producer streams are audited.',
        'No Java-to-DEX or Android framework/native runtime evidence in this review; root owns separate compile work.',
        'No installed resources/fonts/preference capture/shaping/layout/drawing/transactions, native support, display/input/health, signed or OTA authority.',
        'Phones disconnected: no device discovery/run/reconnection request. Physical parity, immutable published separate-repository FieldLog, store/customer/operational and all GA evidence pending.'],
    physicalDevices=dict(discovered=False,used=False,reconnectionRequested=False))
def save(): (OUT/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
def artifact(p): receipt['artifacts'][str(p.relative_to(ROOT))]=dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
def run(name,argv,cwd,expected_marker=None):
    start=time.monotonic();argv=list(map(str,argv));r=subprocess.run(argv,cwd=cwd,capture_output=True,timeout=180)
    c=dict(name=name,argv=argv,cwd=str(cwd),exitCode=r.returncode,seconds=time.monotonic()-start,
           expectedNonzero=expected_marker is not None,expectedFailureMarker=expected_marker)
    for stream,data in [('stdout',r.stdout),('stderr',r.stderr)]:
        p=OUT/(name+'.'+stream+'.log');p.write_bytes(data)
        c[stream]=dict(path=str(p.relative_to(ROOT)),bytes=len(data),sha256=sha(data))
    receipt['commands'].append(c);save();print(name,r.returncode,flush=True)
    if expected_marker is not None:
        assert r.returncode!=0 and expected_marker in (r.stdout+r.stderr).decode(errors='replace'),('undetected or unrelated mutation',name)
    elif r.returncode:raise RuntimeError(name+' failed: '+(r.stdout+r.stderr).decode(errors='replace')[-7000:])
    return r.stdout
def audit_producer():
    raw=(PRODUCER/'receipt.json').read_bytes();assert sha(raw)==EXPECTED_RECEIPT
    producer=json.loads(raw);assert producer['inputTreeSHA256']==EXPECTED_INPUT
    for p in source_files:assert manifest[p]==producer['inputManifest'][p],('changed product',p)
    parsed={};streams={}
    for name in ['swift-debug-probe','swift-release-probe','java-default','java-interpreted']:
        command=next(c for c in producer['commands'] if c['name']==name)
        stream=command['stdout'];path=ROOT/stream['path'];stored=path.read_bytes()
        assert sha(stored)==stream['storedSHA256'];data=gzip.decompress(stored) if path.suffix=='.gz' else stored
        assert len(data)==stream['bytes'] and sha(data)==stream['sha256']
        records={}
        for line in data.decode().splitlines():
            fields=line.split('\t');assert len(fields)==(6 if name.startswith('swift') else 2)
            assert fields[0] not in records,('duplicate case name',fields[0])
            payload=base64.b64decode(fields[-1],validate=True)
            records[fields[0]]=payload.decode() if payload.startswith(b'error:') else json.loads(payload)
        assert len(records)==185
        assert sum(isinstance(v,dict) for v in records.values())==170
        assert sum(isinstance(v,str) for v in records.values())==15
        parsed[name]=records;streams[name]=dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=sha(data),storedSHA256=sha(stored))
    baseline=parsed['swift-debug-probe']
    for name,values in parsed.items():assert values==baseline,('differential mismatch',name)
    # Independent structural/semantic audit of the retained output, no reliance on
    # the producer's mismatch list or its stated assertion counts.
    total_nodes=0;styles=0;unique_kinds=set();metric_checks=0;seen_metrics=set()
    profiles=['xs','s','m','l','xl','xxl','xxxl','a1','a2','a3','a4','a5']
    family=[[14,25,11,31],[15,26,11,32],[16,27,11,33],[17,28,12,34],[19,30,14,36],[21,32,16,38],
            [23,34,18,40],[28,38,22,44],[33,43,26,48],[40,48,32,52],[47,53,37,56],[53,58,43,60]]
    role_columns=dict(body=0,headline=0,sectionHeader=0,title=1,caption=2,navigationExpanded=3)
    def check_text(t,profile):
        nonlocal metric_checks
        if t is None:return
        role=t['role'];size=family[profiles.index(profile)][role_columns[role]]*64
        weight=600 if role in ('headline','sectionHeader') else 700 if role=='navigationExpanded' else 400
        assert t['metrics']==dict(size64=size,weight=weight),('six role metrics',profile,role,t)
        metric_checks+=1;seen_metrics.add((profile,role))
    for name,plan in baseline.items():
        if not isinstance(plan,dict):continue
        nodes=plan['nodes'];ids={n['identity']['id']:n for n in nodes};assert len(ids)==len(nodes)<=4096
        total_nodes+=len(nodes)
        for n in nodes:
            unique_kinds.add(n['kind']);ident=n['identity'];assert ident['generation'].isdigit() and 0<int(ident['generation'])<2**64
            assert all(c in ids for c in n['childIDs'])
            for field in ['text','header','expandedTitle','compactTitle']:
                if field in n['recipe']:check_text(n['recipe'][field],plan['environment']['profile'])
            for index,s in enumerate(n['styles']):
                styles+=1;press=index in (1,3);focus=index in (2,3)
                assert s['disabled']==n['disabled']
                assert s['pressed']==(press and not n['disabled'] and n['kind'] in ('button','toggle'))
                assert s['focused']==(focus and not n['disabled'] and n['kind'] in ('button','toggle','textField'))
            if n['kind']=='list':
                for g,group in enumerate(n['recipe']['groups']):
                    check_text(group['header'],plan['environment']['profile'])
                    for row,identity in enumerate(group['rowIdentities']):
                        target=ids[identity['id']];assert target['identity']==identity
                        assert target['rowPlacement']==dict(listIdentity=ident,groupIndex=g,rowIndex=row,separatorAfter=row+1<len(group['rowIdentities']))
        assert int(plan['revision'])<2**64
    assert len(unique_kinds)==10 and len(seen_metrics)==72
    result=dict(producerReceiptSHA256=EXPECTED_RECEIPT,producerInputTreeSHA256=EXPECTED_INPUT,
        streams=streams,variants=4,casesPerVariant=185,acceptedPerVariant=170,rejectedPerVariant=15,
        acceptedNodeRecordsAudited=total_nodes,stateRecordsAudited=styles,distinctNodeKinds=sorted(unique_kinds),
        metricRecordsAudited=metric_checks,distinctProfileRolePairs=len(seen_metrics),
        result='Exact 4-stream full JSON/error equality and independent output structural/state assertions passed.')
    p=OUT/'producer-output-audit.json';p.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');artifact(p)
    receipt['producerAudit']=result
def mutation_checks():
    resolver=source_files[2];codec=source_files[0]
    mutations=[
        ('disabled-press',resolver,'boolean press = !node.disabled() && pressed &&','boolean press = pressed &&',1,'button press'),
        ('invisible-padding',resolver,'previous = false;','previous = true;',1,'group gap 1'),
        ('nested-section-context',resolver,'listAncestor == null ? new OutsideList() : new WithinListRow(listAncestor)','new OutsideList()',1,'deep ancestor context'),
        ('uint64-double-rounding',resolver,'new Identity(node.id, node.generation)','new Identity(node.id, Long.toUnsignedString((long)Double.parseDouble(node.generation)))',1,'exact UInt64 above double precision'),
        ('unselected-theme-admission',codec,'semantics(ios, resources);','if (mode == Mode.shared) semantics(ios, resources);',1,'accepted unselected iOS full profile validation'),
        ('raw-utf16-admission',resolver,'admit(i + 1 < locale.length() && Character.isLowSurrogate(locale.charAt(i + 1)), Error.shape);','admit(true, Error.shape);',1,'accepted malformed/forbidden/overlong locale'),
        ('role-paint-collapse',resolver,'rolePaint(paints.text(), text.text().role())','paints.text().body()',1,'role paint adj-b'),
        ('explicit-zero-spacing',resolver,'node.properties.containsKey("spacing") ? AppearanceGeometryV2.spacing64','node.number("spacing", 0) != 0 ? AppearanceGeometryV2.spacing64',2,'explicit zero beats pair'),
    ]
    receipt['mutations']=[]
    for name,path,old,new,count,marker in mutations:
        work=OUT/'.build'/'mutations'/name;classes=work/'classes';classes.mkdir(parents=True)
        javafiles=[];copied={}
        for relative in source_files+[review_files[0]]:
            data=(OUT/'inputs'/relative).read_bytes()
            if relative==path:
                source=data.decode();assert source.count(old)==count,(name,source.count(old));data=source.replace(old,new).encode()
            target=work/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            copied[relative]=sha(data);javafiles.append(target)
        run('mutant-'+name+'-compile',[JAVA.with_name('javac'),'--release','17','-Xlint:all','-Werror','-d',classes,*javafiles],work)
        run('mutant-'+name+'-detect',[JAVA,'-cp',classes,'dev.mixer.android.ReviewProbe',OUT/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'],work,marker)
        for p in classes.rglob('*.class'):artifact(p)
        receipt['mutations'].append(dict(name=name,target=path,original=old,replacement=new,occurrences=count,
            expectedAssertionMarker=marker,sourceManifest=copied,result='detected-by-reviewer-oracle'))
        save()
try:
    save();run('java-version',[JAVA,'-version'],ROOT);run('javac-version',[JAVA.with_name('javac'),'-version'],ROOT)
    run('python-version',[sys.executable,'--version'],ROOT)
    run('producer-seal',[sys.executable,ROOT/'verification/android-appearance-v2-resolution/verify_seal.py','candidate-5','--with-binaries','--check-live'],ROOT)
    audit_producer();save()
    results=[]
    for variant,flags in [('default',[]),('interpreted',['-Xint'])]:
        work=OUT/'.build'/variant;classes=work/'classes';classes.mkdir(parents=True)
        copied={};javafiles=[]
        for relative in source_files+[review_files[0]]:
            target=work/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);data=(OUT/'inputs'/relative).read_bytes();target.write_bytes(data)
            copied[relative]=sha(data);javafiles.append(target)
        receipt['variantSourceManifests'][variant]=copied
        run('javac-'+variant,[JAVA.with_name('javac'),'--release','17','-Xlint:all','-Werror','-d',classes,*javafiles],work)
        output=run('java-'+variant,[JAVA,*flags,'-cp',classes,'dev.mixer.android.ReviewProbe',OUT/'inputs/verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'],work)
        results.append(output.decode().strip())
        for p in classes.rglob('*.class'):artifact(p)
    assert results[0]==results[1],results
    receipt['results']=results;mutation_checks();receipt['status']='passed-host-data-independent-review'
except Exception as error:
    receipt['status']='failed';receipt['error']=str(error);raise
finally:
    receipt['completedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt['liveInputChangesSinceSnapshot']=[p for p,d in manifest.items() if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=d]
    save()
print('PASS independent review '+str(OUT),flush=True)
