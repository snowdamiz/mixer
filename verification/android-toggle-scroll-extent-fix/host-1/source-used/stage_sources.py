#!/usr/bin/env python3
"""One-time finite fixture/build adaptation, writes only this fresh packet."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OLD=ROOT/'verification/android-toggle-scroll-failure-analysis'
PACKAGE='dev.mixer.android.authoredtogglescrollextentfix'
PRECONDITION='''            int viewport=window.scroll.getHeight()-window.scroll.getPaddingTop()-window.scroll.getPaddingBottom();
            require(viewport>0&&window.content.getMeasuredHeight()>viewport&&window.content.getHeight()>viewport&&window.scroll.canScrollVertically(1),"fixture positive measured content extent and canScrollDown before injection");
'''
def replacements(name):
    if name=='fixture/AuthoredToggleSupplementActivity.java':return [('minimum-content-extent','content=new Parent();scroll.addView','content=new Parent();content.setMinimumHeight(6000);scroll.addView')]
    if name=='fixture/AuthoredToggleSupplementInstrumentation.java':return [('positive-measured-extent-precondition','"state",scrollState()));});\n        int[] xy=', '"state",scrollState()));\n'+PRECONDITION+'        });\n        int[] xy=')]
    if name=='fixture/AndroidManifest.xml':return [('new-private-package','dev.mixer.android.authoredtogglescrolldiagnostic',PACKAGE),('new-private-label','Mixer private scroll diagnostic','Mixer private scroll extent fix')]
    if name=='build.py':return [('host-build-description','Build original-protocol scroll diagnostic','Build fixture-only minimum scroll extent correction'),('compare-original-private-apk',"common.PRODUCER/'supplement-3/apk-entries.json'","common.SCROLL/'supplement-1/apk-entries.json'")]
    if name=='verify.py':return [('fresh-host-description','original-protocol scroll observation','fixture-only scroll extent correction'),('snapshot-files',"('support.py','run.py','diagnostics.py','test_host.py','verify.py','runner-contract.json','derived-runner.py','capture_analysis.py')","('support.py','run.py','diagnostics.py','test_host.py','verify.py','runner-contract.json','derived-runner.py','stage_sources.py','source-adaptation.json')"),('host-result-status','passed-fresh-host-original-protocol-scroll-observation','passed-fresh-host-fixture-only-scroll-extent-correction')]
    return []
def transformed(name):
    source=(OLD/name).read_text();changes=[]
    for label,before,after in replacements(name):
        count=source.count(before)
        expected=2 if label=='new-private-package' else 1
        if count!=expected:raise ValueError('finite source site '+label+' '+str(count))
        source=source.replace(before,after);changes.append({'name':label,'occurrences':count,'before':before,'after':after})
    return source,changes
def main():
    inputs=['fixture/AuthoredToggleSupplementActivity.java','fixture/AuthoredToggleSupplementInstrumentation.java','fixture/FixtureFailures.java','fixture/ScrollTraceBuffer.java','fixture/AndroidManifest.xml','build.py','verify.py','host-tests/FixtureFailuresTest.java','host-tests/ScrollTraceBufferTest.java']
    record={};diff=[]
    for name in inputs:
        source,changes=transformed(name);target=HERE/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x') as stream:stream.write(source)
        original=(OLD/name).read_text();record[name]={'upstreamSHA256':hashlib.sha256(original.encode()).hexdigest(),'candidateSHA256':hashlib.sha256(source.encode()).hexdigest(),'changes':changes}
        diff.extend(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='frozen-scroll-diagnostic/'+name,tofile='fixture-extent-fix/'+name))
    contract=json.loads((OLD/'fixture/supplement-contract.json').read_text());contract['package']=PACKAGE;contract['status']='prepared-fixture-only-minimum-extent-correction-native-NOT-RUN';contract['fixtureExtentCorrection']={'minimumContentHeight':6000,'precondition':'measured and laid-out content height exceed positive viewport and canScrollVertically(1) before injection','original45CaseBodiesAssertions':'unchanged','originalNineEventsCoordinatesTimestampsSchedule':'unchanged'}
    (HERE/'fixture/supplement-contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
    (HERE/'source-adaptation.json').write_text(json.dumps({'schema':1,'upstreamSeal':'165707429ecda4f075b995508be9a16f0e87c3f013b8820138480128b6d000ef','files':record},indent=2,sort_keys=True)+'\n')
    (HERE/'fixture-source.diff').write_text(''.join(diff))
if __name__=='__main__':main()
