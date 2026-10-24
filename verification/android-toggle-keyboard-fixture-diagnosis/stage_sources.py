#!/usr/bin/env python3
"""Finite fixture-only adaptation from a sealed reset packet; no native commands."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];UPSTREAM=ROOT/'verification/android-toggle-scroll-reset-fix'
PACKAGE='dev.mixer.android.authoredtogglekeyboardfixture'
def digest(data):return hashlib.sha256(data).hexdigest()
def changes(name):
    if name=='fixture/AndroidManifest.xml':return [('private-package','dev.mixer.android.authoredtogglescrollresetfix',PACKAGE,2),('private-label','Mixer private scroll reset fix','Mixer private keyboard setup fixture',1)]
    if name=='fixture/AuthoredToggleSupplementActivity.java':return [('keyboard-observer-and-public-focus-snapshots','    Map<String,Object> exportTrace()',(HERE/'keyboard-activity.fragment').read_text()+'    Map<String,Object> exportTrace()',1)]
    if name=='fixture/AuthoredToggleSupplementInstrumentation.java':return [
        ('keyboard-counter-fields','    private int setupChecks;','    private int setupChecks,keyboardSetupChecks,keyboardSetupEvents;\n    private final List<Object> keyboardSetupObservations=new ArrayList<>(),keyboardSetupRequests=new ArrayList<>();',1),
        ('keyboard-mode-setup-single-original-focus-predicate','    private void focus(){main(()->require(toggle.requestFocus(),"native focus admitted"));idle();}',(HERE/'keyboard-instrumentation.fragment').read_text().rstrip(),1),
        ('finite-keyboard-export','"addedSetupAssertions",setupChecks,"originalAssertionCounter",checks-setupChecks,','"addedSetupAssertions",setupChecks,"originalAssertionCounter",checks-setupChecks,"addedScrollSetupAssertions",setupChecks-keyboardSetupChecks,"addedKeyboardSetupAssertions",keyboardSetupChecks,"keyboardSetupEvents",keyboardSetupEvents,"keyboardSetup",Json.map("schema",1,"requests",keyboardSetupRequests,"observations",keyboardSetupObservations,"nativeKeyTrace",window==null?List.of():window.keyboardTrace.snapshot(),"nativeModeTrace",window==null?List.of():window.keyboardModeTrace.snapshot(),"modeDropped",window==null?0:window.keyboardModeTrace.dropped(),"dropped",window==null?0:window.keyboardTrace.dropped(),"observerFailures",window==null?0:window.keyboardObserverFailures),',1)]
    if name=='build.py':return [('build-description','fresh scroll container reset correction','public keyboard-mode setup correction',1)]
    if name=='verify.py':return [('replay-description','scroll reset correction','keyboard setup correction',1),('host-result-status','scroll-reset-correction','keyboard-setup-correction',1),('host-source-snapshots',"'source-adaptation.json')","'source-adaptation.json','oracle_adapter.py','keyboard_oracle.py','reset_counter_oracle.py','oracle-adaptation.json')",1)]
    return []
def transformed(name,source=None):
    data=(UPSTREAM/name).read_text() if source is None else source;record=[]
    for label,before,after,count in changes(name):
        if data.count(before)!=count:raise ValueError('finite source site '+name+':'+label)
        data=data.replace(before,after,count);record.append({'name':label,'occurrences':count,'beforeSHA256':digest(before.encode()),'afterSHA256':digest(after.encode())})
    return data,record
def main():
    (HERE/'fixture').mkdir(exist_ok=True);(HERE/'host-tests').mkdir(exist_ok=True);record={}
    names=['build.py','verify.py',*[str(p.relative_to(UPSTREAM)) for p in sorted((UPSTREAM/'fixture').iterdir()) if p.is_file() and p.name!='supplement-contract.json'],*[str(p.relative_to(UPSTREAM)) for p in sorted((UPSTREAM/'host-tests').iterdir()) if p.is_file()]]
    diffs=[]
    for name in names:
        original=(UPSTREAM/name).read_text();after,changeset=transformed(name);(HERE/name).write_text(after)
        record[name]={'upstreamSHA256':digest(original.encode()),'candidateSHA256':digest(after.encode()),'changes':changeset}
        diffs+=list(difflib.unified_diff(original.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='sealed-reset/'+name,tofile='keyboard-fixture/'+name))
    contract=json.loads((UPSTREAM/'fixture/supplement-contract.json').read_text());contract['fixtureKeyboardSetup']={'rootSelection':'public DPAD_DOWN DOWN/UP via sendKeySync, observed non-touch mode, ordinary platform Button focus control, original single-call toggle focus predicate','focusHelperCases':[40,41,42,43],'perHelperSetupAssertions':5,'fullOriginal45AdditionalKeyboardAssertions':20,'fullOriginal45ScrollSetupAssertions':6,'fullSetupAssertions':26,'fullKeyboardSetupEvents':8,'nativeKeyTraceRows':[8,16],'nativeModeTraceRows':[0,4],'focusObservationRows':32,'productFocusPolicyChanged':False,'controlRemovedInFinally':True,'original45CaseBodiesAndScrollInjection':'exact unchanged'}
    (HERE/'fixture/supplement-contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
    (HERE/'source-adaptation.json').write_text(json.dumps({'schema':1,'upstreamSealSHA256':digest((UPSTREAM/'packet-seal.json').read_bytes()),'files':record,'fixtureContract':'finite root-selected keyboard setup appended to original contract'},indent=2,sort_keys=True)+'\n')
    (HERE/'fixture-source.diff').write_text(''.join(diffs))
if __name__=='__main__':main()
