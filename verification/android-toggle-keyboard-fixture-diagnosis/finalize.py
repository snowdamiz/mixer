#!/usr/bin/env python3
"""Seal complete host candidate, preserved failed/superseded attempts and scope; no native dispatch."""
import json,os,sys
from pathlib import Path
import support
def main():
    here=support.HERE;out=here/'final-host-1';out.mkdir()
    receipt={'schema':1,'status':'host-finalization-running','startedUTC':support.now(),'commands':[],'invocation':[sys.executable,'-B',str(Path(__file__).resolve())],
        'nativeRuntime':'NOT RUN','nativeCommandsExecuted':0,'nativeInstancesStarted':0,'GitCommandsExecuted':0,'physicalTargetsQueried':False,'dependenciesAdded':[],
        'full45CaseSuiteAccepted':False,'originalRuntimeStatus':'failed at native case40 focus request after39completed cases; separate strict-schema mismatch retained',
        'counterContract':{'originalCaseBodies':45,'scrollSetupAssertions':6,'keyboardSetupAssertionsPerHelper':5,'keyboardHelperCases':[40,41,42,43],'keyboardSetupAssertions':20,'addedSetupAssertions':26,'keyboardSetupEvents':8,'focusObservationRows':32,'nativeActivityKeyRows':[8,16],'nativeModeChangeRows':[0,4]},
        'originalAssertionsRemovedOrWeakened':0,'originalMotionEventsAndScrollScheduleChanged':False,'productionFocusPolicyChanged':False,
        'scope':'private actual-View component fixture candidate only; new public keyboard navigation setup and native Button control; original failed runtime remains failed; actual full45 native acceptance pending root; physical/TalkBack/live engine/Apple/FieldLog/GA pending'}
    def command(name,argv,allowed=0):
        argv=list(map(str,argv));started=support.now();result=support.owned.execute(argv,cwd=here,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=180)
        path=out/(name+'.log');path.write_bytes(result.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(here),'startedUTC':started,'finishedUTC':support.now(),'exitCode':result.returncode,'output':str(path.relative_to(here)),**support.bind(path),'ownedCommandGroupCleanup':result.groupCleanup});support.save(here/'receipt.json',receipt)
        if result.returncode!=allowed:raise ValueError('final host check failed '+name)
        return result.stdout
    receipt['upstreamBefore']=support.upstream()
    command('python-version',[sys.executable,'--version'])
    receipt['controls']=json.loads(command('finite-keyboard-source-export-negative-controls',[sys.executable,'-B',here/'test_host.py']))
    before=(here/'runtime').exists()
    refusal=command('root-native-flag-required-refusal',[sys.executable,'-B',here/'run.py','--build','candidate-3','--attempt','runtime-1'],2)
    if b'explicit root dispatch required' not in refusal or (here/'runtime').exists()!=before:raise ValueError('native refusal before runtime creation absent')
    build=support.read(here/'supplement-3/receipt.json');host=support.read(here/'host-2/receipt.json')
    if not build['cleanup']['absent'] or not host['cleanup']['absent'] or not host['exactDexReplay']:raise ValueError('exact class/DEX replay and cleanup required')
    attempts=[]
    for name in ('supplement-1','supplement-2','supplement-3','host-1','host-2'):
        value=support.read(here/name/'receipt.json')
        if not value['cleanup']['absent']:raise ValueError('owned scratch remains '+name)
        attempts.append({'attempt':name,'status':value['status'],'receipt':support.bind(here/name/'receipt.json'),'cleanup':value['cleanup']})
    receipt.update(status='prepared-frozen-keyboard-mode-fixture-host-passed-native-NOT-RUN',privatePackage=support.PACKAGE,candidate='supplement-3',
        apk=build['apk'],sourceClosureSHA256=build['sourceClosureSHA256'],sourceRevisionContext=support.read(here/'analysis-1/receipt.json')['sourceRevisionContext'],sourceRevisionAuthority='sealed original runtime context only; exact source bytes independently bound; no Git commands',
        unchangedProductionClasses=build['unchangedProductionClasses'],unchangedNativeLibraries=build['unchangedLibraries'],fixtureClasses=build['supplementClasses'],
        hostChecks={'failureForwarding':support.read(here/'host-2/fixture-failure-tests.json')['checks'],'traceStorage':support.read(here/'host-2/trace-buffer-tests.json')['checks'],'ownedInputBounds':support.read(here/'host-2/input-bounds-tests.json')['checks'],'finiteSourceAndExportControls':receipt['controls']['checks'],'exactFixtureClassAndDexReplay':True,'signatureAlignmentAndPackaging':True},
        retainedAttempts=attempts,selection=support.bind(here/'selection-and-refinement.json'),officialSources=support.bind(here/'official-sources.json'),
        cleanup={'ownedScratchAbsent':True,'filesRemoved':sum(a['cleanup']['filesRemoved'] for a in attempts),'bytesRemoved':sum(a['cleanup']['bytesRemoved'] for a in attempts),'scope':'only unique owned host build/replay extractions; all command groups empty; no native instance created'})
    receipt['upstreamAfter']=support.upstream()
    if receipt['upstreamBefore']!=receipt['upstreamAfter']:raise ValueError('immutable original packet or source dependencies drift')
    receipt['finishedUTC']=support.now();support.save(here/'receipt.json',receipt);support.save(here/'packet-seal.json',{'schema':1,'files':support.packet_files()})
    receipt['readOnlyPacketCheck']=json.loads(command('frozen-read-only-packet-check',[sys.executable,'-B',here/'check.py']))
    receipt['finishedUTC']=support.now();support.save(here/'receipt.json',receipt);support.save(here/'packet-seal.json',{'schema':1,'files':support.packet_files()});support.check_packet()
    print(json.dumps({'status':receipt['status'],'apk':receipt['apk'],'sourceClosureSHA256':receipt['sourceClosureSHA256'],'packetSeal':support.bind(here/'packet-seal.json'),'packetFiles':len(support.packet_files()),'cleanup':receipt['cleanup']},sort_keys=True))
if __name__=='__main__':main()
