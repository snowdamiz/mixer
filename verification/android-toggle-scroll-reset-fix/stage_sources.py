#!/usr/bin/env python3
"""Finite fresh-container fixture adaptation; writes only this new packet."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OLD=ROOT/'verification/android-toggle-scroll-extent-fix'
PACKAGE='dev.mixer.android.authoredtogglescrollresetfix'
ORIGINAL_SCROLL_CONSTRUCTION='        scroll=new ObservedScroll();content=new Parent();content.setMinimumHeight(6000);scroll.addView(content,new ScrollView.LayoutParams(-1,6000));root.addView(scroll,new FrameLayout.LayoutParams(-1,-1));\n'
RESET_CONSTRUCTION='''        recreateScroll();
    }
    void recreateScroll(){
        if(scroll!=null)root.removeView(scroll);
'''+ORIGINAL_SCROLL_CONSTRUCTION
OLD_RESET='if(record!=null)record.cancelToggleInput();window.content.removeAllViews();window.scroll.scrollTo(0,0);'
NEW_RESET='if(record!=null){record.cancelToggleInput();if(record.view.getParent() instanceof android.view.ViewGroup parent)parent.removeView(record.view);}window.content.removeAllViews();window.recreateScroll();'
OLD_EXTENT='''            int viewport=window.scroll.getHeight()-window.scroll.getPaddingTop()-window.scroll.getPaddingBottom();
            require(viewport>0&&window.content.getMeasuredHeight()>viewport&&window.content.getHeight()>viewport&&window.scroll.canScrollVertically(1),"fixture positive measured content extent and canScrollDown before injection");
'''
OLD_PREFIX='''            window.trace.add(Json.map("stage","scroll.geometry.before","case",cases,"uptime",SystemClock.uptimeMillis(),"diagonal",diagonal,"geometry",window.geometry(toggle),"state",scrollState()));
'''+OLD_EXTENT+'''        });
        int[] xy=new int[2];main(()->toggle.getLocationOnScreen(xy));double x=xy[0]+geometry().offCenter(),y=xy[1]+66;
'''
NEW_PREFIX='''            window.trace.add(Json.map("stage","scroll.geometry.before","case",cases,"uptime",SystemClock.uptimeMillis(),"diagonal",diagonal,"geometry",window.geometry(toggle),"state",scrollState()));
        });
        int[] xy=new int[2];main(()->toggle.getLocationOnScreen(xy));double x=xy[0]+geometry().offCenter(),y=xy[1]+66;
        main(()->{
            Map<String,Object> ownedInput=window.ownedInputGeometry(toggle,x,y,diagonal);
            window.trace.add(Json.map("stage","scroll.input.preconditions","case",cases,"uptime",SystemClock.uptimeMillis(),"geometry",window.geometry(toggle),"state",scrollState(),"ownedInput",ownedInput,"addedSetupAssertionsBefore",setupChecks));
            int viewport=window.scroll.getHeight()-window.scroll.getPaddingTop()-window.scroll.getPaddingBottom();
            setupRequire(viewport>0&&window.content.getMeasuredHeight()>viewport&&window.content.getHeight()>viewport&&window.scroll.canScrollVertically(1),"fixture positive measured content extent and canScrollDown before injection");
            setupRequire(window.scroll.getScrollX()==0&&window.scroll.getScrollY()==0,"fixture fresh scroll zero offset before injection");
            setupRequire(Boolean.TRUE.equals(ownedInput.get("admitted")),"fixture original first and last points within owned visible app input area");
        });
'''
OWNED_GEOMETRY='''    Map<String,Object> ownedInputGeometry(View toggle,double x,double y,boolean diagonal){
        View decor=getWindow().getDecorView();Rect frame=new Rect();decor.getWindowVisibleDisplayFrame(frame);
        Rect rootVisible=new Rect(),toggleVisible=new Rect();boolean rootHasVisible=root.getLocalVisibleRect(rootVisible),toggleHasVisible=toggle.getLocalVisibleRect(toggleVisible);
        int[] rootScreen=new int[2],toggleScreen=new int[2],decorScreen=new int[2];root.getLocationOnScreen(rootScreen);toggle.getLocationOnScreen(toggleScreen);decor.getLocationOnScreen(decorScreen);
        rootVisible.offset(rootScreen[0],rootScreen[1]);toggleVisible.offset(toggleScreen[0],toggleScreen[1]);
        WindowInsets insets=decor.getRootWindowInsets();android.graphics.Insets bars=insets==null?null:insets.getInsets(WindowInsets.Type.systemBars());
        int[] visibleFrame={frame.left,frame.top,frame.right,frame.bottom},rootRect={rootVisible.left,rootVisible.top,rootVisible.right,rootVisible.bottom};
        int[] decorRect={decorScreen[0],decorScreen[1],decorScreen[0]+decor.getWidth(),decorScreen[1]+decor.getHeight()};
        int[] system=bars==null?new int[]{0,0,0,0}:new int[]{bars.left,bars.top,bars.right,bars.bottom};
        int[] owned=FixtureInputBounds.intersect(visibleFrame,rootRect,decorRect,system);double lastX=x+(diagonal?8*10:0),lastY=y-8*35;
        boolean firstOnToggle=toggleHasVisible&&FixtureInputBounds.contains(new int[]{toggleVisible.left,toggleVisible.top,toggleVisible.right,toggleVisible.bottom},x,y);
        boolean windowOwned=bars!=null&&rootHasVisible&&root.isAttachedToWindow()&&root.isShown()&&root.hasWindowFocus()&&decor.hasWindowFocus()&&toggle.isAttachedToWindow()&&toggle.isShown()&&toggle.hasWindowFocus();
        boolean admitted=windowOwned&&firstOnToggle&&FixtureInputBounds.contains(owned,x,y)&&FixtureInputBounds.contains(owned,lastX,lastY);
        return Json.map("admitted",admitted,"windowOwned",windowOwned,"firstOnVisibleToggle",firstOnToggle,"insetsAvailable",bars!=null,
            "windowVisibleFrame",List.of(frame.left,frame.top,frame.right,frame.bottom),"rootVisibleScreen",List.of(rootVisible.left,rootVisible.top,rootVisible.right,rootVisible.bottom),
            "toggleVisibleScreen",List.of(toggleVisible.left,toggleVisible.top,toggleVisible.right,toggleVisible.bottom),"decorScreen",List.of(decorRect[0],decorRect[1],decorRect[2],decorRect[3]),
            "systemBarInsets",List.of(system[0],system[1],system[2],system[3]),"ownedVisibleScreen",List.of(owned[0],owned[1],owned[2],owned[3]),"firstPoint",List.of(x,y),"lastPoint",List.of(lastX,lastY));
    }
'''
BOUNDS_TEST_RUN='''        output=command('run-host-input-bounds-test',[support.JDK/'bin/java','-ea','-cp',os.pathsep.join(map(str,[fresh,host])),'dev.mixer.android.FixtureInputBoundsTest']);result=re.findall(rb'^RESULT (.+)$',output,re.M)
        if len(result)!=1:raise ValueError('one input bounds result required')
        support.save(out/'input-bounds-tests.json',json.loads(result[0]))
'''
def replacements(name):
    if name=='fixture/AuthoredToggleSupplementActivity.java':return [('fresh-scroll-construction',ORIGINAL_SCROLL_CONSTRUCTION,RESET_CONSTRUCTION,1),('owned-input-geometry','    Map<String,Object> exportTrace()',OWNED_GEOMETRY+'    Map<String,Object> exportTrace()',1)]
    if name=='fixture/AuthoredToggleSupplementInstrumentation.java':return [('replace-reset-container',OLD_RESET,NEW_RESET,1),('classify-added-setup-assertions','    private int mode,overflowAt=-1;','    private int setupChecks;\n    private int mode,overflowAt=-1;',1),('setup-assertion-counter','    private void main(Runnable action)', '    private void setupRequire(boolean value,String label){setupChecks++;require(value,label);}\n    private void main(Runnable action)',1),('record-and-admit-original-input',OLD_PREFIX,NEW_PREFIX,1),('export-original-and-added-counters','"assertions",checks,"events",events','"assertions",checks,"addedSetupAssertions",setupChecks,"originalAssertionCounter",checks-setupChecks,"events",events',1)]
    if name=='fixture/AndroidManifest.xml':return [('new-private-package','dev.mixer.android.authoredtogglescrollextentfix',PACKAGE,2),('new-private-label','Mixer private scroll extent fix','Mixer private scroll reset fix',1)]
    if name=='build.py':return [('host-build-description','minimum scroll extent correction','fresh scroll container reset correction',1)]
    if name=='verify.py':return [('fresh-host-description','fixture-only scroll extent correction','fixture-only scroll reset correction',1),('input-bounds-host-test',"        support.save(out/'trace-buffer-tests.json',json.loads(result[0]))\n","        support.save(out/'trace-buffer-tests.json',json.loads(result[0]))\n"+BOUNDS_TEST_RUN,1),('host-test-snapshot',"('FixtureFailuresTest.java','ScrollTraceBufferTest.java')","('FixtureFailuresTest.java','ScrollTraceBufferTest.java','FixtureInputBoundsTest.java')",1),('host-result-status','passed-fresh-host-fixture-only-scroll-extent-correction','passed-fresh-host-fixture-only-scroll-reset-correction',1)]
    return []
def transformed(name):
    source=(OLD/name).read_text();changes=[]
    for label,before,after,expected in replacements(name):
        count=source.count(before)
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
        diff.extend(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='frozen-extent-fix/'+name,tofile='fixture-reset-fix/'+name))
    contract=json.loads((OLD/'fixture/supplement-contract.json').read_text());contract['package']=PACKAGE;contract['status']='prepared-fixture-only-fresh-scroll-container-reset-native-NOT-RUN';contract['sources'].append('FixtureInputBounds.java');contract['fixtureResetCorrection']={'newScrollAndContentPerReset':True,'oldRecordCancelledAndRemovedBeforeReset':True,'minimumContentHeight':6000,'preconditions':['positive measured extent and canScrollDown','zero horizontal and vertical offset','original first and last points inside visible owned app area and first on visible toggle'],'geometryRecordedBeforeSetupAssertions':True,'setupAssertionsPerScrollCase':3,'setupAssertionsAtFull45Cases':6,'original45CaseBodiesAssertions':'unchanged','originalNineEventsCoordinatesTimestampsSchedule':'unchanged'}
    (HERE/'fixture/supplement-contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
    (HERE/'source-adaptation.json').write_text(json.dumps({'schema':1,'upstreamSeal':'233f2a713571621e48e07cab2e6e2678545bb1fb64830ca77b32ebeb95bc9ace','files':record},indent=2,sort_keys=True)+'\n')
    (HERE/'fixture-source.diff').write_text(''.join(diff))
    a=(OLD/'fixture/supplement-contract.json').read_text();b=(HERE/'fixture/supplement-contract.json').read_text();(HERE/'contract-source.diff').write_text(''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='frozen-extent-fix/fixture/supplement-contract.json',tofile='fixture-reset-fix/fixture/supplement-contract.json')))
if __name__=='__main__':main()
