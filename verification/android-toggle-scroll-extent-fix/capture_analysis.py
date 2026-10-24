#!/usr/bin/env python3
"""Bind prior failure and finite fixture changes; no Android or Git commands."""
import difflib,json,platform,sys
from pathlib import Path
import support,stage_sources

def main():
    out=support.HERE/'analysis-1';out.mkdir();before=support.upstream();review=support.ROOT/'verification/android-toggle-scroll-runtime-root-review'
    paths=[support.ROOT/'AGENTS.md',support.ROOT/'THIRD_PARTY.yml',review/'runtime-review.json',review/'trace-summary.json',support.SCROLL/'runtime/runtime-1/receipt.json',support.SCROLL/'runtime/runtime-1/scroll-private-trace.log',support.SCROLL/'runtime/runtime-1/toggle-supplement-results.json']
    changes=[]
    for name,row in support.read(support.HERE/'source-adaptation.json')['files'].items():
        expected,_=stage_sources.transformed(name)
        if expected!=(support.HERE/name).read_text():raise ValueError('finite source mismatch '+name)
        old=(support.SCROLL/name).read_text();paths.extend((support.SCROLL/name,support.HERE/name))
        changes.extend(difflib.unified_diff(old.splitlines(keepends=True),expected.splitlines(keepends=True),fromfile='frozen-scroll-diagnostic/'+name,tofile='fixture-extent-fix/'+name))
    (support.HERE/'fixture-source.diff').write_text(''.join(changes))
    receipt={'schema':1,'status':'bound-original-failure-and-fixture-only-minimum-extent-correction-native-NOT-RUN','observedUTC':support.now(),'invocation':[sys.executable,'-B',str(Path(__file__).resolve())],'python':sys.version,'host':platform.platform(),'bindings':{str(p.relative_to(support.ROOT)):support.bind(p) for p in paths},'upstreamBefore':before,'upstreamAfter':support.upstream(),'sourceRevisionContext':'bbed074d3bd2453bbcc0807f05219d042cedd738','sourceRevisionAuthority':'root-supplied context only; no Git commands; exact source bytes bound independently','originalRuntime':{'completedCases':17,'failingCase':18,'assertionsIncludingFailure':85,'reportedEvents':64,'contentRequestedHeight':6000,'contentMeasuredHeight':532,'viewportHeight':2622,'canScrollUp':False,'canScrollDown':False,'activityDeliveries':9,'childDeliveries':9,'childCancelCount':0,'interceptTrueCount':0},'change':{'fixtureOnly':True,'minimumContentHeight':6000,'measuredExtentAndCanScrollDownRequiredBeforeInjection':True,'original45CaseBodiesAndAssertionsUnchanged':True,'originalNineEventActionsCoordinatesTimestampsScheduleUnchanged':True,'failureAndTraceInstrumentationRetained':True,'productCodeChanged':False},'nativeCommandsExecuted':0,'GitCommandsExecuted':0,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'full45CaseSuiteAccepted':False,'cleanup':'No source-extraction or runtime scratch created by analysis.','scope':'Fixture correction candidate only; original failed APK and packets immutable. Actual positive extent, native interception/CANCEL and full45case acceptance require root runtime. Phones disconnected; TalkBack, live engine, FieldLog and GA remain pending.'}
    if before!=receipt['upstreamAfter']:raise ValueError('upstream drift')
    support.save(out/'receipt.json',receipt);support.save(out/'artifact-seal.json',support.seal(out));print(json.dumps({'status':receipt['status'],'bindings':len(paths)},sort_keys=True))
if __name__=='__main__':main()
