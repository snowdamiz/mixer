#!/usr/bin/env python3
"""Read-only hash and evidence verifier. No extraction, writes or subprocesses."""
import collections
import json
import plistlib
import sys
from common import *

REPORT = ROOT / 'docs/apple-passive-lifecycle-sendable-correction.md'

def load(path): return json.loads(path.read_bytes())

def inventory():
    result = {}
    for p in sorted(BASE.rglob('*')):
        if p.is_dir(): continue
        if p in [BASE/'handoff.json',BASE/'handoff.sha256']: continue
        result[str(p.relative_to(ROOT))] = binding(p,True)
    result[str(REPORT.relative_to(ROOT))] = binding(REPORT,True)
    return dict(sorted(result.items()))

def commands(path, directory):
    values=load(path)
    for c in values:
        assert c['exitCode']==0 and c['stdoutEOF'] and c['stderrEOF'] and c['processGroupAbsent']
        assert not c['timedOut'] and not c['signalsSent']
        assert c['elapsedSeconds']>0 and c['timeoutSeconds']>0
        for s in ['stdout','stderr']: assert c[s]==binding(directory/(c['name']+'.'+s))
    return values

def audit():
    inputs=verify_inputs()
    context=load(BASE/'delivery-context.json')
    assert context['correctionContextRevisionReportedByRoot']=='7b6048642b42e4900cccff4e14aa0fe8949ab35e'
    assert context['inheritedHistoricalAcceptedInputRevision']==REVISION
    assert context['gitQueried'] is False
    source=payload((ROOT/SOURCE).read_bytes())
    producer=payload((ROOT/PRODUCER_SOURCE).read_bytes())
    baseline=payload((ROOT/OLD_SOURCE).read_bytes())
    observer='accepted/source/Prototype/PassiveLifecycleObserver.swift'
    helper='accepted/source/Prototype/PassiveLifecycleData.swift'
    assert source[helper]==producer[helper]
    assert sum(source[n]==producer[n] for n in source)==41
    assert sum(source[n]==baseline[n] for n in baseline)==39

    finite=BASE/'finite'
    fr=load(finite/'receipt.json')
    assert fr['passed'] and fr['differentialSemanticOutputsEqual'] and fr['ownedHostScratchRemoved']
    assert fr['correctedSourceArchive']==binding(ROOT/SOURCE)
    assert fr['nativeExecutions']==fr['nativeQueries']==fr['genericBuildsDuringFiniteControls']==0
    assert fr['realUIKitCompiled'] is False and fr['realUIKitExecuted'] is False
    assert load(finite/'input-bindings-before.json')==load(finite/'input-bindings-after.json')==inputs
    fc=commands(finite/'commands.json',finite)
    assert len(fc)==10
    results=load(finite/'semantic-results.json')
    assert results==fr['results']
    assert results['corrected']==results['producer-baseline']
    assert results['corrected']['passed'] and results['corrected']['checks']==88
    assert results['corrected']['notificationKinds']==14 and len(results['corrected']['transcript'])==14
    assert results['producer-Foundation']['checks']==116 and results['producer-Foundation']['passed']
    assert results['independent-Foundation']['checks']==371 and results['independent-Foundation']['passed']
    for name,label in [('execute-corrected','corrected'),('execute-producer-baseline','producer-baseline'),('execute-producer-Foundation','producer-Foundation'),('execute-independent-Foundation','independent-Foundation')]:
        assert json.loads((finite/(name+'.stdout')).read_text().splitlines()[-1])==results[label]
    ft=load(finite/'source-tool-bindings.json')
    assert fr['testedSources']==ft and ft['swift']==binding(SWIFT.resolve())
    assert ft['sdkSettings']==binding(Path(ft['sdkResolved'])/'SDKSettings.json')
    kept=payload((finite/'host-scratch.tar.gz').read_bytes())
    for n,expected in ft['inputs'].items(): assert row(*kept[n])==expected,n
    assert kept['corrected-observer.swift'][0]==source[observer][0]
    assert kept['producer-observer.swift'][0]==producer[observer][0]
    assert kept['PassiveLifecycleData.swift'][0]==source[helper][0]
    assert kept['UIKitDouble.swift'][0]==(BASE/'UIKitDouble.swift').read_bytes()
    assert kept['SemanticTests.swift'][0]==(BASE/'SemanticTests.swift').read_bytes()
    cleanup=load(finite/'cleanup.json')
    assert cleanup['preservedScratchArchive']==binding(finite/'host-scratch.tar.gz')
    assert cleanup['preservedMembers']==len(kept)
    assert cleanup['preservedTreeSHA256']==sha(canonical(rows(kept)))
    assert not Path(cleanup['ownedScratchPath']).exists()
    for k in ['inodeStable','regularFilesSingleLink','processGroupsAbsent','stdoutStderrEOF','holdersAbsent','ownedScratchRemoved']: assert cleanup[k]
    assert cleanup['holderExitCode']==1 and cleanup['nativeInstancesTouched']==0 and not cleanup['otherProjectsTouched']
    assert not (finite/'holders.stdout').read_bytes() and not (finite/'holders.stderr').read_bytes()

    br=load(OUT/'receipt.json')
    assert br['passed'] and br['status']=='compiled-linked-fresh-app-and-runner-build-only'
    assert br['sourceRevisionReportedByRoot']==REVISION
    for k in ['gitQueried','liveSourceEdits','runtimeSelected','nativeExecuted','nativeAccepted','futureRuntimeIngestionAccepted','originalOraclePassed','gaAccepted','uiOrCapture','listenersOrExplicitNetwork']: assert br[k] is False,k
    assert br['copiedObserverCorrection'] and br['simulatorOrDeviceCommands']==0
    assert br['sourceFiles']==42 and br['overallSwiftFiles']==37 and br['prototypeSwiftFiles']==12 and br['harnessSwiftFiles']==4
    assert br['oldAppProductFilesCopied']==0 and br['recipeOnlyChangesScratchPrefixFromVerifiedGenericBuild']
    assert br['inputsAndToolsUnchangedAfterBuild'] and br['ownedScratchRemoved']
    assert load(OUT/'input-bindings-before.json')==load(OUT/'input-bindings-after.json')==inputs
    bc=commands(OUT/'commands.json',OUT)
    expected=recipe_commands()
    assert len(bc)==8 and br['exitCodes']=={c['name']:c['exitCode'] for c in bc}
    for c,r in zip(bc,expected):
        for k,v in r.items(): assert c[k]==v,(c['name'],k)
        assert c['overallBuildDeadlineSeconds']==780 and 0<c['actualTimeoutSeconds']<=c['timeoutSeconds']
    recipe=load(OUT/'recipe-comparison.json')
    assert recipe['commands']==expected and recipe['scratchSubstitutionOnlyFromVerifiedGenericRecipe']
    assert recipe['source']==binding(ROOT/GENERIC/'attempt-1/commands.json')
    assert (OUT/'xcode-version.stdout').read_bytes()==b'Xcode 26.6\nBuild version 17F113\n'
    assert b'Apple Swift version 6.3.3' in (OUT/'swift-version.stdout').read_bytes()
    assert (OUT/'sdk-version.stdout').read_bytes()==b'26.5\n'
    tools=load(OUT/'tools.json')
    original_tools=load(ROOT/ORIGINAL/'tool-bindings.json')['tools']
    assert tools['bindings']==original_tools=={p:binding(Path(p).resolve()) for p in original_tools}
    assert tools['sdkRequested']==str(SDK) and tools['sdkResolved']==str(SDK.resolve())
    build_sources=payload((OUT/'sources.tar.gz').read_bytes())
    assert build_sources=={n.removeprefix('accepted/'):v for n,v in source.items()}
    manifest=load(OUT/'source-manifest.json')
    assert manifest['sources']==rows(build_sources) and manifest['selectedArchiveMembers']==rows(source)
    assert manifest['sourceTreeSHA256']==br['sourceTreeSHA256']==sha(canonical(rows(build_sources)))
    assert manifest['selectedSourceTreeSHA256']==br['selectedSourceTreeSHA256']==sha(canonical(rows(source)))
    assert manifest['archive']==br['sourceArchive']==binding(OUT/'sources.tar.gz')
    assert manifest['selectedArchive']==binding(ROOT/SOURCE)
    assert manifest['unchangedCompileClosureFiles']==39 and manifest['producerByteIdenticalMembers']==41
    assert manifest['producerOnlyChangedMembers']==[observer]
    products=payload((OUT/'products.tar.gz').read_bytes())
    pm=load(OUT/'product-manifest.json')
    assert pm['products']==rows(products) and len(products)==br['productFiles']==55
    assert pm['archive']==br['productArchive']==binding(OUT/'products.tar.gz')
    assert pm['productTreeSHA256']==br['productTreeSHA256']==sha(canonical(rows(products)))
    assert pm['sourceTreeSHA256']==br['sourceTreeSHA256']
    assert pm['appProductsFresh'] and pm['runnerProductsFresh'] and pm['oldAppProductFilesCopied']==0 and not pm['nativeExecuted']
    assert pm['appProductFiles']==br['appProductFilesFresh']==13
    assert pm['runnerProductFiles']==br['runnerProductFilesFresh']==42
    actual_inspection=product_inspection(products)
    inspection=load(OUT/'product-inspection.json')
    assert inspection['machO']==actual_inspection['machO'] and inspection['plists']==actual_inspection['plists']
    targets=['MixerToggleDiagnostics.app/Frameworks/libMixerCore.dylib','MixerToggleDiagnostics.app/Frameworks/libMixerUI.dylib','MixerToggleDiagnostics.app/MixerToggleDiagnostics','runner-products/Debug-iphonesimulator/MixerToggleUITests-Runner.app/PlugIns/MixerToggleUITests.xctest/MixerToggleUITests']
    assert inspection['freshCompiledLinkedTargets']==targets
    for name,kind in zip(targets,[6,6,2,8]):
        m=inspection['machO'][name]
        assert m['cpuType']==0x100000c and m['fileType']==kind
        assert m['buildVersions']==[{'platform':7,'minimumOS':'26.0.0','sdk':'26.5.0','toolCount':1}]
    info=plistlib.loads(source['accepted/source/Prototype/Info.plist'][0])
    assert info['MinimumOSVersion']=='17.0'; info['MinimumOSVersion']='26.0'
    assert products['MixerToggleDiagnostics.app/Info.plist'][0]==plistlib.dumps(info)
    packaging=load(OUT/'packaging-derivation.json')
    assert packaging['source']==rows(source)['accepted/source/Prototype/Info.plist']
    assert packaging['product']==row(*products['MixerToggleDiagnostics.app/Info.plist'])
    assert packaging['sourceUnchanged'] and packaging['sameDerivationAsOriginal'] and packaging['signing']=='unsigned'
    warnings=load(OUT/'warning-comparison.json')
    for name in ['mixer-core','mixer-ui','app','runner']:
        for s in ['stdout','stderr']:
            current=warning_messages((OUT/(name+'.'+s)).read_bytes())
            old=warning_messages((ROOT/ORIGINAL/'commands'/(name+'.'+s)).read_bytes())
            assert warnings['commandWarnings'][name]['current'][s]==current
            assert warnings['commandWarnings'][name]['originalQualification'][s]==old
            assert collections.Counter(current)==collections.Counter(old)
    assert warnings['warningLineOccurrences']==br['warningLineOccurrences']==21
    assert br['allWarningMessageMultisetsMatchFullOriginalQualification']
    cleanup=load(OUT/'cleanup.json')
    assert not SCRATCH.exists() and cleanup['ownedScratchPath']==str(SCRATCH)
    for k in ['inodeStable','regularFilesSingleLink','processGroupsAbsent','stdoutStderrEOF','holdersAbsent','ownedScratchRemoved']: assert cleanup[k]
    for name in ['sources.tar.gz','products.tar.gz']:
        assert cleanup['archivesVerifiedBeforeRemoval'][name]=={'binding':binding(OUT/name),'regularMembers':len(payload((OUT/name).read_bytes()))}
    assert cleanup['nativeInstancesTouched']==0 and not cleanup['otherProjectsTouched']
    driver=load(BASE/'driver-receipt.json')
    assert driver['exitCode']==0 and driver['stdoutEOF'] and driver['stderrEOF'] and driver['processGroupAbsent']
    assert not driver['timedOut'] and not driver['signalsSent']
    assert driver['script']==binding(BASE/'build.py') and driver['common']==binding(BASE/'common.py')
    for s in ['stdout','stderr']: assert driver[s]==binding(BASE/('driver.'+s))
    assert driver['stderr']['bytes']==0
    return {'passed':True,'status':'corrected-source-finite-controls-and-one-generic-build-ready-for-independent-review',
            'correctionContextRevisionReportedByRoot':context['correctionContextRevisionReportedByRoot'],
            'sourceMembers':42,'overallSwiftFiles':37,'prototypeSwiftFiles':12,'harnessSwiftFiles':4,
            'producerChangedMembers':1,'producerByteIdenticalMembers':41,'baselineByteIdenticalMembers':39,
            'semanticChecksPerAdapter':88,'differentialSemanticOutputsEqual':True,'FoundationChecks':[116,371],
            'genericBuildAttempts':1,'genericCommands':8,'freshProductFiles':55,'oldProductFilesCopied':0,
            'warningLineOccurrences':21,'baselineWarningMessageMultisetsEqual':True,
            'candidateArchiveSHA256':binding(ROOT/SOURCE)['sha256'],'productArchiveSHA256':br['productArchive']['sha256'],
            'ownedScratchAbsent':True,'nativeExecuted':False,'runtimeSelected':False,'originalOraclePassed':False,'gaAccepted':False}

def main():
    handoff=load(BASE/'handoff.json')
    members=inventory()
    assert handoff['members']==members
    assert handoff['memberTreeSHA256']==sha(canonical(members))
    digest=sha((BASE/'handoff.json').read_bytes())
    assert (BASE/'handoff.sha256').read_text()==digest+'  handoff.json\n'
    result=audit()
    assert handoff['audit']==result
    print(json.dumps({'handoffSHA256':digest,'sealedMembers':len(members),**result},indent=2,sort_keys=True))

if __name__=='__main__': main()
