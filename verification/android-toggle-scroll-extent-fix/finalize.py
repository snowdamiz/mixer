#!/usr/bin/env python3
"""Finalize fixture extent candidate and seal after host controls; no native dispatch."""
import json,os,sys
from pathlib import Path
import support
def main():
    here=support.HERE;out=here/'final-host-1';out.mkdir()
    receipt={'schema':1,'status':'host-finalization-running','startedUTC':support.now(),'commands':[],
        'invocation':[sys.executable,'-B',str(Path(__file__).resolve())],'nativeRuntime':'NOT RUN','nativeCommandsExecuted':0,
        'GitCommandsExecuted':0,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'dependenciesAdded':[],
        'full45CaseSuiteAccepted':False,'originalSuiteStatus':'failed at native parent vertical scroll after17completedcases85counterincludingfailure64events',
        'addedPreconditionChecks':{'perScrollCase':1,'originalScrollCaseNumbers':[18,19],'complete45CaseRunAdditionalChecks':2,'originalAssertionsRemovedOrWeakened':0},
        'originalProtocolPreserved':True,'pacedModePresent':False,'observerTimingPerturbation':True,
        'scope':'private fixture extent correction candidate only; full45case native acceptance pending root; product unchanged; phones disconnected/TalkBack/fullrenderer/GA pending'}
    def command(name,argv,allowed=0):
        start=support.now();result=support.owned.execute(list(map(str,argv)),cwd=here,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=180)
        log=out/(name+'.log');log.write_bytes(result.stdout)
        receipt['commands'].append({'name':name,'argv':list(map(str,argv)),'cwd':str(here),'startedUTC':start,'finishedUTC':support.now(),'exitCode':result.returncode,'output':str(log.relative_to(here)),**support.bind(log),'ownedCommandGroupCleanup':result.groupCleanup})
        support.save(here/'receipt.json',receipt)
        if result.returncode!=allowed:raise ValueError('final host control failed '+name)
        return result.stdout
    receipt['upstreamBefore']=support.upstream()
    command('python-version',[sys.executable,'--version'])
    output=command('finite-source-negative-controls',[sys.executable,'-B','-c','import test_host,json; print(json.dumps(test_host.source_checks(),sort_keys=True))']);receipt['sourceControls']=json.loads(output)
    before=here/'runtime';existing=before.exists()
    output=command('root-flag-required-host-refusal',[sys.executable,'-B',here/'run.py','--build','candidate-3','--attempt','runtime-1'],allowed=2)
    if b'explicit root dispatch required' not in output or before.exists()!=existing:raise ValueError('host-only native refusal control failed')
    build=support.read(here/'supplement-1/receipt.json');host=support.read(here/'host-1/receipt.json')
    if not build['cleanup']['absent'] or not host['cleanup']['absent'] or not host['exactDexReplay']:raise ValueError('required cleanup/host replay absent')
    receipt.update(status='prepared-frozen-fixture-only-scroll-extent-fix-host-passed-native-NOT-RUN',
        sourceClosureSHA256=build['sourceClosureSHA256'],apk=build['apk'],privatePackage=support.PACKAGE,
        unchangedProductionClasses=build['unchangedProductionClasses'],unchangedNativeLibraries=build['unchangedLibraries'],fixtureClasses=build['supplementClasses'],
        hostChecks={'failureForwarding':support.read(here/'host-1/fixture-failure-tests.json')['checks'],'traceStorage':support.read(here/'host-1/trace-buffer-tests.json')['checks'],'sourceRunnerCapture':support.read(here/'host-1/host-controls.json')['checks'],'finiteSourceNegative':receipt['sourceControls']['checks']},
        buildReceipt=support.bind(here/'supplement-1/receipt.json'),hostReceipt=support.bind(here/'host-1/receipt.json'),analysisReceipt=support.bind(here/'analysis-1/receipt.json'),
        sourceRevisionContext=support.read(here/'analysis-1/receipt.json')['sourceRevisionContext'],sourceRevisionAuthority='root contextual revision only; byte closures independently verified; no Git command',
        cleanup={'ownedScratchAbsent':True,'filesRemoved':build['cleanup']['filesRemoved']+host['cleanup']['filesRemoved'],'bytesRemoved':build['cleanup']['bytesRemoved']+host['cleanup']['bytesRemoved'],'scope':'only unique build/replay scratch; all owned child command groups empty; no runtime instance created'})
    receipt['upstreamAfter']=support.upstream()
    if receipt['upstreamBefore']!=receipt['upstreamAfter']:raise ValueError('upstream or dependency identity changed')
    receipt['finishedUTC']=support.now();support.save(here/'receipt.json',receipt);support.save(here/'packet-seal.json',{'schema':1,'files':support.packet_files()})
    checked=command('frozen-read-only-packet-check',[sys.executable,'-B',here/'check.py']);receipt['packetCheck']=json.loads(checked)
    receipt['finishedUTC']=support.now();support.save(here/'receipt.json',receipt);support.save(here/'packet-seal.json',{'schema':1,'files':support.packet_files()})
    support.check_packet()
    print(json.dumps({'status':receipt['status'],'packetSealSHA256':support.sha(here/'packet-seal.json'),'packetFiles':len(support.packet_files()),'cleanup':receipt['cleanup']},sort_keys=True))
if __name__=='__main__':main()
