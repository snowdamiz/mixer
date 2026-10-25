#!/usr/bin/env python3
"""Independent file-only verification. No subprocesses, extraction or writes."""
import collections
import difflib
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import stat
import struct
import sys
import tarfile

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PRODUCER=ROOT/'verification/apple-passive-lifecycle-sendable-correction'
FAILED=ROOT/'verification/apple-passive-lifecycle-generic-build'
OBSERVER=ROOT/'verification/apple-passive-lifecycle-observer'
REPORT=ROOT/'docs/apple-passive-sendable-review.md'
PINS={
 'verification/apple-passive-lifecycle-observer/handoff.json':('9e30a9aeef107094d70b17fc83fc632f0278af9d0384a58564cd7b0456efbd75',73),
 'verification/apple-passive-lifecycle-review/handoff.json':('376642724000ecd82914f322337ee498b5b083f3bd927dcfab03d8259d425a27',53),
 'verification/apple-passive-lifecycle-generic-build/handoff.json':('5b23f406d3781bccc59f1e181c2588c6df7af16435b375c4cc0bd197d559a8c1',51),
 'verification/apple-passive-lifecycle-sendable-correction/handoff.json':('207821bc258c351b1767932ad7b2e85dd7f621f3ad7e56054bcb3cfdcf87ed88',81),
}
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def load(p): return json.loads(p.read_bytes())
def safe(n):
    p=PurePosixPath(n)
    assert n and not p.is_absolute() and '..' not in p.parts and str(p)==n,n
def binding(p):
    s=p.lstat(); assert stat.S_ISREG(s.st_mode) and not p.is_symlink(),p
    b=p.read_bytes(); return {'kind':'file','mode':stat.S_IMODE(s.st_mode),'bytes':len(b),'sha256':sha(b)}
def row(b,m): return {'kind':'file','mode':m,'bytes':len(b),'sha256':sha(b)}
def archive(p):
    out={}; seen=set()
    with tarfile.open(fileobj=io.BytesIO(p.read_bytes()),mode='r:gz') as t:
        for m in t:
            safe(m.name); assert m.name not in seen; seen.add(m.name)
            assert m.isfile() or m.isdir(),m.name
            if m.isfile(): out[m.name]=(t.extractfile(m).read(),m.mode)
    assert not any(str(p) in out for n in out for p in PurePosixPath(n).parents)
    return out
def rows(d): return {n:row(*v) for n,v in sorted(d.items())}
def command_receipts(p):
    commands=load(p/'commands.json')
    assert len({c['name'] for c in commands})==len(commands)
    for c in commands:
        assert c['exitCode']==0 and c['processGroupAbsent'] and c['stdoutEOF'] and c['stderrEOF']
        assert not c['timedOut'] and not c['signalsSent']
        for s in ['stdout','stderr']: assert c[s]==binding(p/(c['name']+'.'+s))
    return commands
def macho_target(raw):
    assert raw[:4]==b'\xcf\xfa\xed\xfe'
    _,cpu,sub,kind,n,size,flags,reserved=struct.unpack_from('<8I',raw)
    offset=32; builds=[]
    for _ in range(n):
        cmd,length=struct.unpack_from('<2I',raw,offset)
        assert length>=8 and offset+length<=32+size
        if cmd==0x32: builds.append(struct.unpack_from('<4I',raw,offset+8))
        offset+=length
    assert offset==32+size and builds==[(7,26<<16,(26<<16)+(5<<8),1)]
    assert cpu==0x100000c
    return kind
def warnings(b): return [l.split('warning:',1)[1].strip() for l in b.decode().splitlines() if 'warning:' in l]

def audit():
    counts={}
    for n,(digest,count) in PINS.items():
        path=ROOT/n; assert binding(path)['sha256']==digest,n
        members=load(path)['members']; assert len(members)==count
        for member,expected in members.items():
            safe(member); actual=binding(ROOT/member)
            assert all(actual[k]==v for k,v in expected.items()),member
        assert load(path)['memberTreeSHA256']==sha(canonical(members))
        counts[n]=count
    source=archive(PRODUCER/'review-source-package.tar.gz')
    old=archive(OBSERVER/'review-source-package.tar.gz')
    baseline=archive(ROOT/'verification/apple-focus-system-observation/review-source-package.tar.gz')
    observer='accepted/source/Prototype/PassiveLifecycleObserver.swift'
    assert binding(PRODUCER/'review-source-package.tar.gz')['sha256']=='bf31888a14490e83e2424f458eac0cf8f56258d581ff2fc4034840b0d1783663'
    assert set(source)==set(old) and len(source)==42
    assert [n for n in sorted(source) if source[n]!=old[n]]==[observer]
    assert sum(source[n]==baseline[n] for n in baseline)==39
    assert all(m==0o444 for b,m in source.values())
    assert sum(n.endswith('.swift') for n in source)==37
    assert sum(n.startswith('accepted/source/Prototype/') and n.endswith('.swift') for n in source)==12
    assert sum(n.startswith('accepted/harness/') and n.endswith('.swift') for n in source)==4
    diff=''.join(difflib.unified_diff(old[observer][0].decode().splitlines(keepends=True),source[observer][0].decode().splitlines(keepends=True),fromfile=observer,tofile='PROPOSAL-ONLY/PassiveLifecycleObserver.swift')).encode()
    assert diff==(FAILED/'correction-proposal.patch').read_bytes()==(PRODUCER/'source.patch').read_bytes()
    assert sha(source[observer][0])=='487aca9a7578d638868ed1d5f155cc1b5edb84ca0e141e7a4fd7677be3690df9'
    assert source[observer][0]==(PRODUCER/'PassiveLifecycleObserver.swift').read_bytes()
    selected=load(PRODUCER/'selection.json')
    assert selected['maximumGenericAttempts']==1 and selected['genericSimulatorBuildOnly']
    assert not selected['runtimeSelected'] and not selected['nativeDiscoverySelected'] and not selected['reuseOldProducts']
    context=load(PRODUCER/'delivery-context.json')
    assert context['correctionContextRevisionReportedByRoot']=='7b6048642b42e4900cccff4e14aa0fe8949ab35e'
    assert context['inheritedHistoricalAcceptedInputRevision']=='6b8aba350224ed19f678669bdbea6b359d8de68b'
    review_context=load(BASE/'delivery-context.json')
    assert review_context['correctionContextRevisionReportedByRootViaProducerFinalHandoff']==context['correctionContextRevisionReportedByRoot']
    assert review_context['inheritedHistoricalAcceptedInputRevision']==context['inheritedHistoricalAcceptedInputRevision']

    build=PRODUCER/'build-attempt-1'; bc=command_receipts(build)
    prior=load(FAILED/'attempt-1/commands.json')
    keys=['name','argv','explicitEnvironment','cwd','timeoutSeconds']
    current=[{k:c[k] for k in keys} for c in bc]
    normalized=json.loads(json.dumps(current).replace(str(build/'owned-build'),str(FAILED/'attempt-1/owned-build')))
    assert normalized==[{k:c[k] for k in keys} for c in prior]
    assert [c['name'] for c in bc]==['xcode-version','swift-version','sdk-version','python-version','mixer-core','mixer-ui','app','runner']
    assert all(c['overallBuildDeadlineSeconds']==780 and 0<c['actualTimeoutSeconds']<=c['timeoutSeconds'] for c in bc)
    assert all('simctl' not in c['argv'] and 'devicectl' not in c['argv'] for c in bc)
    built=archive(build/'sources.tar.gz')
    assert built=={n.removeprefix('accepted/'):v for n,v in source.items()}
    br=load(build/'receipt.json'); sm=load(build/'source-manifest.json')
    assert sm['sources']==rows(built) and sm['selectedArchiveMembers']==rows(source)
    assert br['sourceTreeSHA256']==sm['sourceTreeSHA256']==sha(canonical(rows(built)))
    assert br['selectedSourceTreeSHA256']==sm['selectedSourceTreeSHA256']==sha(canonical(rows(source)))
    assert br['passed'] and br['oldAppProductFilesCopied']==0
    products=archive(build/'products.tar.gz'); pm=load(build/'product-manifest.json')
    assert binding(build/'products.tar.gz')['sha256']=='495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
    assert len(products)==55 and rows(products)==pm['products']
    assert pm['productTreeSHA256']==br['productTreeSHA256']==sha(canonical(rows(products)))
    assert pm['appProductsFresh'] and pm['runnerProductsFresh'] and pm['oldAppProductFilesCopied']==0
    assert pm['appProductFiles']==13 and pm['runnerProductFiles']==42
    targets=[('MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib',6),('MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib',6),('MixerToggleDiagnostics.app/MixerToggleDiagnostics',2),('runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests',8)]
    for n,kind in targets: assert macho_target(products[n][0])==kind
    info=plistlib.loads(source['accepted/source/Prototype/Info.plist'][0]); assert info['MinimumOSVersion']=='17.0'
    info['MinimumOSVersion']='26.0'; assert plistlib.dumps(info)==products['MixerToggleDiagnostics.app/Info.plist'][0]
    wcount=0
    for name in ['mixer-core','mixer-ui','app','runner']:
        for stream in ['stdout','stderr']:
            now=warnings((build/(name+'.'+stream)).read_bytes())
            historical=warnings((ROOT/'verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/commands'/(name+'.'+stream)).read_bytes())
            assert collections.Counter(now)==collections.Counter(historical)
            wcount+=len(now)
    assert wcount==21
    assert (build/'xcode-version.stdout').read_bytes()==b'Xcode 26.6\nBuild version 17F113\n'
    assert b'Apple Swift version 6.3.3' in (build/'swift-version.stdout').read_bytes()
    assert (build/'sdk-version.stdout').read_bytes()==b'26.5\n'
    for p in [build,PRODUCER/'finite',BASE/'controls']:
        cleanup=load(p/'cleanup.json')
        for k in ['inodeStable','processGroupsAbsent','stdoutStderrEOF','regularFilesSingleLink','holdersAbsent','ownedScratchRemoved']: assert cleanup[k]
        assert not Path(cleanup['ownedScratchPath']).exists()
        assert cleanup['nativeInstancesTouched']==0 and not cleanup['otherProjectsTouched']
        assert not (p/'holders.stdout').read_bytes() and not (p/'holders.stderr').read_bytes()
    finite=PRODUCER/'finite'; command_receipts(finite)
    results=load(finite/'semantic-results.json')
    assert results['corrected']==results['producer-baseline'] and results['corrected']['checks']==88
    assert results['producer-Foundation']['checks']==116 and results['independent-Foundation']['checks']==371
    for name,key in [('execute-corrected','corrected'),('execute-producer-baseline','producer-baseline'),('execute-producer-Foundation','producer-Foundation'),('execute-independent-Foundation','independent-Foundation')]:
        assert results[key]['passed'] and json.loads((finite/(name+'.stdout')).read_text().splitlines()[-1])==results[key]
    controls=BASE/'controls'; cc=command_receipts(controls)
    cr=load(controls/'receipt.json'); before=load(controls/'bindings-before.json')
    assert cr['passed'] and cr['normalizedResultsEqual'] and cr['ownedScratchRemoved']
    assert before==load(controls/'bindings-after.json')==cr['sourcesAndTools']
    assert before['sourceRevisionReportedByRoot']==review_context['inheritedHistoricalAcceptedInputRevision']
    assert load(controls/'driver-command.json')['driver']==binding(BASE/'run_controls.py')
    assert before['candidateArchive']==binding(PRODUCER/'review-source-package.tar.gz')
    assert before['sources']['corrected.swift']['sha256']==sha(source[observer][0])
    assert before['sources']['original.swift']['sha256']==sha(old[observer][0])
    assert before['sources']['Data.swift']['sha256']==sha(source['accepted/source/Prototype/PassiveLifecycleData.swift'][0])
    assert before['sources']['BoundaryControls.swift']['sha256']==binding(BASE/'BoundaryControls.swift')['sha256']
    assert before['sources']['UIKitDouble.swift']['sha256']==binding(PRODUCER/'UIKitDouble.swift')['sha256']
    assert before['swift']==binding(Path(before['swiftResolved'])) and before['sdkSettings']==binding(Path(before['sdkResolved'])/'SDKSettings.json')
    for label in ['corrected','original']:
        result=json.loads((controls/('execute-'+label+'.stdout')).read_text().splitlines()[-1])
        assert result==cr['results'][label] and result['checks']==19 and result['passed']
    assert cr['results']['corrected']==cr['results']['original']
    return {'passed':True,'blockingFindings':[],'producerHandoffSHA256':PINS['verification/apple-passive-lifecycle-sendable-correction/handoff.json'][0],
            'verifiedSealedInputMembers':counts,'candidateArchiveSHA256':binding(PRODUCER/'review-source-package.tar.gz')['sha256'],
            'productArchiveSHA256':binding(build/'products.tar.gz')['sha256'],'exactSelectedProposalRegenerated':True,
            'producerChangedMembers':1,'producerByteIdenticalMembers':41,'baselineByteIdenticalMembers':39,
            'independentBoundaryChecksPerAdapter':19,'producerSemanticChecksPerAdapter':88,'FoundationChecks':[116,371],
            'genericBuildAttemptsByProducer':1,'genericCommands':8,'freshProductFiles':55,'warningLineOccurrences':21,
            'status':'accepted-minimal-copied-observer-correction-and-generic-build-evidence',
            'nativeExecuted':False,'runtimeSelected':False,'futureRuntimeIngestionAccepted':False,'originalOraclePassed':False,'gaAccepted':False,
            'reviewOwnedScratchRemoved':True,'physicalPhones':'disconnected-deferred'}

def inventory():
    paths=[p for p in BASE.rglob('*') if p.is_file() and p.name not in ['handoff.json','handoff.sha256']]
    paths.append(REPORT)
    return dict(sorted((str(p.relative_to(ROOT)),binding(p)) for p in paths))
def main():
    assert len(sys.argv)==2,'Pass exact reviewed handoff SHA256'
    digest=binding(BASE/'handoff.json')['sha256']; assert digest==sys.argv[1]
    h=load(BASE/'handoff.json'); members=inventory()
    assert h['members']==members and h['memberTreeSHA256']==sha(canonical(members))
    assert (BASE/'handoff.sha256').read_text()==digest+'  handoff.json\n'
    assert h['audit']==audit()
    print(json.dumps({'reviewHandoffSHA256':digest,'reviewMembers':len(members),**h['audit']},indent=2,sort_keys=True))
if __name__=='__main__': main()
