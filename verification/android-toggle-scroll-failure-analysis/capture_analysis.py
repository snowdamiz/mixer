#!/usr/bin/env python3
"""Fresh read-only analysis of frozen source and already-collected runtime evidence."""
import difflib,hashlib,json,platform,sys
from pathlib import Path
import support
def main():
    out=support.HERE/'analysis-1';out.mkdir();repair=support.REPAIR
    before=support.upstream();result_path=repair/'runtime/runtime-1/toggle-supplement-results.json';result=support.read(result_path)
    native=support.PRODUCER/'candidate-3/inputs/native'
    inspected=[*sorted(native.rglob('*.java')),*sorted((repair/'fixture').glob('*.java'))]
    bindings={str(p.relative_to(support.ROOT)):support.bind(p) for p in [support.ROOT/'AGENTS.md',support.ROOT/'THIRD_PARTY.yml',result_path,repair/'runtime/runtime-1/actual-native-component.log',repair/'runtime/runtime-1/diagnostic-private-fixture.log',support.ROOT/'verification/android-authored-toggle-supplement-root-review/runtime-review.json',*inspected]}
    if any('setOnTouchListener' in p.read_text() or 'OnTouchListener' in p.read_text() for p in inspected):raise ValueError('prior public listener found; observation contract refused')
    changes=[]
    for path in sorted((support.HERE/'fixture').glob('*')):
        previous=repair/'fixture'/path.name;old=previous.read_text() if previous.exists() else ''
        changes.extend(difflib.unified_diff(old.splitlines(keepends=True),path.read_text().splitlines(keepends=True),fromfile='frozen-repair/'+path.name,tofile='original-protocol-diagnostic/'+path.name))
    (support.HERE/'fixture-source.diff').write_text(''.join(changes))
    receipt={'schema':1,'status':'fresh-frozen-source-analysis-only-native-NOT-RUN','observedUTC':support.now(),'invocation':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'host':platform.platform(),'bindings':bindings,'upstreamBefore':before,'upstreamAfter':support.upstream(),'sourceRevisionContext':support.read(support.ROOT/'verification/android-authored-toggle-supplement-root-review/runtime-review.json')['sourceRevisionContext'],'sourceRevisionAuthority':'root contextual revision only; exact bytes bound independently; no Git command',
      'knownRuntime':{'status':result['status'],'completedCases':len(result['cases']),'assertionsIncludingFailure':result['assertions'],'reportedEvents':result['events'],'failure':result['failure'],'durationMilliseconds':result['durationMilliseconds'],'finalCleanupState':result['observations'][-1]},
      'missingEvidence':['scrollY at failing assertion','individual proposals and pressed conjuncts at failure','actual hierarchy delivery/CANCEL','native intercept return','actual content extent/window geometry','injection and delivery uptime versus eventTime'],
      'sourceObservation':{'contentLayoutHeight':6000,'toggleFrame':[60,400,1000,132],'eventsPerScroll':9,'eventOffsetsMs':[i*25 for i in range(9)],'verticalOffsetsPx':[-i*35 for i in range(9)],'diagonalOffsetsPx':[i*10 for i in range(9)],'sleepAdded':False,'existingListenerFound':False,'inspectedSourceFiles':len(inspected)},
      'hypothesesNotConclusions':['input scheduled/delivered differently from synthetic timestamps','window/hit geometry or scroll extent differs from assumptions','native interception/child cancellation path differs','product state or proposal behavior differs'],
      'nativeCommandsExecuted':0,'GitCommandsExecuted':0,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'dependenciesChanged':False,'cleanup':'No source-extraction or runtime temporary directory created by this analysis command.','scope':'Original45case suite still failed; no cause inferred for earlier runtime3 process crash; independent original20action429assertion baseline remains separate.'}
    support.save(out/'receipt.json',receipt);support.save(out/'artifact-seal.json',support.seal(out));print(json.dumps({'status':receipt['status'],'bindings':len(bindings),'listenerInspectionFiles':len(inspected)},sort_keys=True))
if __name__=='__main__':main()
