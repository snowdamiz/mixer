#!/usr/bin/env python3
"""Compile bounded ACTUAL owner methods and actual/candidate coordinator predicates.

Leaves model Handler acceptance/queueing and renderer depth, not Android effects.
All extracted production fragments are retained byte-for-byte in source-fragments.json.
"""
from pathlib import Path
import hashlib, json, subprocess, tempfile

PACK = Path(__file__).resolve().parents[1]
SRC = PACK / 'inputs/native/android/app/src/dev/mixer/android'
JDK = Path('/opt/homebrew/opt/openjdk/bin')

def span(source, begin, end):
    a = source.index(begin); b = source.index(end, a + len(begin))
    return source[a:b]

def main():
    owner = (SRC / 'NativeOwnerV2.java').read_text()
    coordinator = (SRC / 'NativeCoordinatorV2.java').read_text()
    fragments = {
        'Work': span(owner, '    private enum WorkKind', '    private final Activity'),
        'post': span(owner, '    private void post(Work work)', '    private void cancelQueued('),
        'removeWork': span(owner, '    private void removeWork(', '    private void unregisterPending()'),
        'closePending': span(owner, '    private void closePending()', '    private void settle()'),
        'settle': span(owner, '    private void settle()', '    private void completeCleanup('),
        'busy': span(coordinator, '    boolean busyForOwnerDisposal()', '    boolean isRetired()'),
        'inputBusy': span(coordinator, '    boolean inputCancellationInProgress()', '    boolean busyForOwnerDisposal()'),
        'enter': span(coordinator, '    private void enter()', '    private void checkOperation()'),
        'closeFromOwner': span(coordinator, '    void closeFromOwner()', '    private void enter()'),
        'leave': span(coordinator, '    private void leave()', '    private void retireScalar()'),
        'retireScalar': span(coordinator, '    private void retireScalar()', '    private void disposeOnce()'),
        'disposeOnce': span(coordinator, '    private void disposeOnce()', '    private void remember('),
    }
    (PACK / 'source-fragments.json').write_text(json.dumps({k: {'source': v, 'sha256': hashlib.sha256(v.encode()).hexdigest()} for k,v in fragments.items()}, indent=2)+'\n')
    results = []
    for amended in (False, True):
        predicate = fragments['busy']
        if amended:
            old = 'return active || cancellation || fence.rendererReportActive;'
            assert predicate.count(old) == 1
            predicate = predicate.replace(old, 'return active || cancellation || fence.rendererReportActive || renderer.editorDisposalBusyV2();')
        dispose = fragments['disposeOnce']
        if amended:
            dispose = dispose.replace('if (disposed) return;', 'if (disposed || busyForOwnerDisposal()) return;')
        java = r'''
import java.util.ArrayList;
import java.util.List;
public class DisposalProbe {
    static final boolean AMENDED = __AMENDED__;
    enum Outcome { NOT_REQUESTED, DEFERRED, ATTEMPTED, RETURNED, FAILED_UNCERTAIN }
    enum Cause { CORE_FAILURE, SCHEDULING_FAILED }
    static class OwnerLifecycleV2 { static class Token {} }
    static class NativeEnvironmentV2 { enum Change { EPOCH_EXHAUSTED } }
    static class Fence { boolean terminal, rendererReportActive,drawAllowed,inputAllowed; OwnerLifecycleV2.Token operation; }
    static class Renderer {
        int editorDepth;
        boolean cleanupDrain, cancellation;
        int disposals;
        boolean unsafeDisposal;
        boolean editorDisposalBusyV2() { return editorDepth != 0 || cleanupDrain; }
        boolean cancellationInProgressV2() { return cancellation; }
        void disposeV2() {disposals++;unsafeDisposal=editorDisposalBusyV2();}
    }
    static class NativeBridge {static void destroy(long session) {}}
    static class NativeCoordinatorV2 {
        final Fence fence;
        final Renderer renderer = new Renderer();
        boolean active, cancellation, retired,disposed;
        long session=1;
        byte[] committedPacket;
        final CleanupLedger ledger=new CleanupLedger();
        OwnerLifecycleV2.Token operation;
        NativeCoordinatorV2(Fence fence) { this.fence=fence; }
        static void requireMain() {}
        void sealGatesScalar() {}
        __PREDICATE__
        __INPUTBUSY__
        __ENTER__
        __CLOSEFROMOWNER__
        __LEAVE__
        __RETIRESCALAR__
        __DISPOSE__
        void remember(Throwable failure) {if(ledger.primary==null)ledger.primary=failure;if(failure instanceof Error fatal&&ledger.firstFatal==null)ledger.firstFatal=fatal;}
        static class CleanupLedger { Throwable primary,rendererFailure,engineFailure; Error firstFatal;Outcome renderer,engine;Throwable primary() {return primary;} Error firstFatal() {return firstFatal;} }
        CleanupLedger cleanupLedger() {return ledger;}
    }
    static class HandlerLeaf {
        final List<Runnable> queue = new ArrayList<>();
        boolean reject, fail;
        boolean post(Runnable work) { if(fail)throw new IllegalStateException("post"); if(reject)return false; queue.add(work); return true; }
        void removeCallbacks(Runnable work) {queue.remove(work);}
        void next() {queue.remove(0).run();}
    }
    static class Snapshot { OwnerLifecycleV2.Token pendingDrain() {return null;} }
    static class CoreLeaf {
        Snapshot snapshot() {return new Snapshot();}
        Object drain(Object lifetime, OwnerLifecycleV2.Token token, Object window) {return null;}
    }
    static class Ledger { Outcome coordinator,handler; Throwable handlerFailure,coordinatorFailure; }
    final HandlerLeaf handler = new HandlerLeaf();
    final Fence fence = new Fence();
    final CoreLeaf core = new CoreLeaf();
    final Object lifetime = new Object();
    final Ledger ledger = new Ledger();
    NativeCoordinatorV2 pendingCloseResource;
    OwnerLifecycleV2.Token pendingCloseToken, activeOperation;
    Work queued;
    int effectDepth;
    Throwable primary;
    Error fatal;
    int completions;
    static void requireMain() {}
    void remember(Throwable failure) {if(failure==null)return;if(primary==null)primary=failure;if(failure instanceof Error value&&fatal==null)fatal=value;}
    void unregisterPending() {}
    void completeCleanup(OwnerLifecycleV2.Token token,Throwable failure) {completions++;remember(failure);}
    void seal(boolean terminal) {}
    void seedFocus() {}
    Object probeWindow() {return null;}
    void process(Object decisions,byte[] input) {}
    void fail(Throwable failure,Cause cause) {remember(failure);}
    void throwFatal() {if(fatal!=null)throw fatal;}
    void terminate(Cause cause,Object rendererCause,Throwable primary,Error fatal,NativeEnvironmentV2.Change change) {remember(primary);remember(fatal);}
    __WORK__
    __POST__
    __REMOVE__
    __CLOSE__
    __SETTLE__
    static void check(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
    NativeCoordinatorV2 pending() {
        NativeCoordinatorV2 c=new NativeCoordinatorV2(fence);
        pendingCloseResource=c;pendingCloseToken=new OwnerLifecycleV2.Token();return c;
    }
    public static void main(String[] args) {
        int checks=0;
        DisposalProbe p=new DisposalProbe();NativeCoordinatorV2 c=p.pending();c.renderer.editorDepth=1;p.fence.terminal=true;
        p.settle();
        if(!AMENDED) {
            check(c.closes==1&&p.queued==null,"actual current predicate does NOT defer for renderer depth");
            p=new DisposalProbe();c=new NativeCoordinatorV2(p.fence);c.renderer.editorDepth=1;c.retired=true;c.active=true;c.leave();
            check(c.disposed&&c.renderer.unsafeDisposal,"actual leave bypasses owner busy predicate and disposes native editor stack");
            System.out.println("actual source: witnessed both owner predicate omission and coordinator leave disposal bypass despite editor depth");return;
        }
        check(c.closes==0&&p.queued!=null&&p.pendingCloseResource==c,"exact pending retained while depth busy");checks++;
        c.renderer.editorDepth=0;p.handler.next();
        check(c.closes==1&&p.pendingCloseResource==null&&p.queued==null&&p.completions==1,"existing owner Work resumes disposal after depth zero");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.cleanupDrain=true;p.settle();
        check(p.queued!=null&&c.closes==0,"cleanup drain also disposal busy");checks++;
        c.renderer.cleanupDrain=false;p.handler.next();check(c.closes==1,"cleanup completion resumes exact disposal");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.handler.reject=true;p.settle();
        check(p.queued==null&&p.pendingCloseResource==c&&p.pendingCloseToken!=null&&c.closes==0&&p.ledger.coordinator==Outcome.DEFERRED,"scheduler rejection retains pending, no fabricated returned");checks++;
        c.renderer.editorDepth=0;check(p.handler.queue.isEmpty()&&c.closes==0,"no autonomous wake under scheduler rejection");checks++;
        p.settle();check(c.closes==1,"future owner entry may resume retained disposal");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.handler.fail=true;p.settle();
        check(p.queued==null&&p.pendingCloseResource==c&&p.primary!=null&&c.closes==0,"throwing scheduler retains pending and primary");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.activeOperation=new OwnerLifecycleV2.Token();p.settle();
        check(c.closes==0&&p.queued==null&&p.pendingCloseResource==c,"active owner operation keeps pending");checks++;
        p.activeOperation=null;p.settle();check(p.queued!=null,"subsequent owner settle schedules retained disposal");checks++;
        c.renderer.editorDepth=0;p.handler.next();check(c.closes==1,"resumes after operation and native unwind");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.settle();NativeCoordinatorV2 old=c;
        NativeCoordinatorV2 newer=p.pending();p.handler.next();
        check(old.closes==0&&newer.closes==1,"stale task does not dispose old/foreign token; finally settles exact current pending");checks++;
        p=new DisposalProbe();c=new NativeCoordinatorV2(p.fence);c.renderer.editorDepth=1;p.fence.operation=new OwnerLifecycleV2.Token();
        check(c.busyForOwnerDisposal(),"candidate disposal busy during healthy native call");checks++;
        c.enter();check(c.active&&c.operation==p.fence.operation&&!p.fence.rendererReportActive,"unchanged coordinator enter still admits compatible synchronous feature operation");checks++;
        c.active=false;c.renderer.editorDepth=0;c.renderer.cancellation=true;
        check(c.inputCancellationInProgress()&&!c.busyForOwnerDisposal(),"input cancellation reporting is a distinct predicate");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;c.retired=true;c.active=true;c.leave();
        check(!c.disposed&&c.session==1&&c.renderer.disposals==0,"central candidate disposal guard protects actual leave before disposed/session consumption");checks++;
        p.settle();check(p.queued!=null,"owner schedules retained retired coordinator");checks++;
        c.renderer.editorDepth=0;p.handler.next();
        check(c.disposed&&c.session==0&&c.renderer.disposals==1&&!c.renderer.unsafeDisposal,"exact retained coordinator disposes after native unwind");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;
        boolean refused=false;try{c.closeFromOwner();}catch(IllegalStateException expected){refused=true;}
        check(refused&&!c.disposed&&c.session==1&&p.pendingCloseResource==c,"actual closeFromOwner refuses busy before successful-return claim");checks++;
        c.renderer.editorDepth=0;p.settle();
        check(c.disposed&&p.pendingCloseResource==null&&p.ledger.coordinator==Outcome.RETURNED&&c.renderer.disposals==1,"owner RETURNED after scalar busy recheck means actual disposal consumed, not central guard no-op");checks++;
        System.out.println("candidate predicate: "+checks+" disposal/ordinary-admission checks passed; host leaves only");
    }
}
'''
        replacements = {'__AMENDED__':str(amended).lower(), '__PREDICATE__':predicate,
                        '__INPUTBUSY__':fragments['inputBusy'], '__ENTER__':fragments['enter'],
                        '__LEAVE__':fragments['leave'], '__DISPOSE__':dispose,
                        '__CLOSEFROMOWNER__':fragments['closeFromOwner'], '__RETIRESCALAR__':fragments['retireScalar'],
                        '__WORK__':fragments['Work'], '__POST__':fragments['post'],
                        '__REMOVE__':fragments['removeWork'], '__CLOSE__':fragments['closePending'], '__SETTLE__':fragments['settle']}
        for marker, text in replacements.items(): java = java.replace(marker, text)
        java = java.replace('.closes', '.renderer.disposals')
        variant = 'candidate' if amended else 'actual'
        out = PACK / 'probe-source' / variant / 'DisposalProbe.java'
        out.parent.mkdir(parents=True,exist_ok=True);out.write_text(java)
        with tempfile.TemporaryDirectory(prefix='mixer-editor-disposal-') as temp:
            for i, command in enumerate([[str(JDK/'javac'), '--release','17','-Xlint:all','-Werror','-d',temp,str(out)],
                                         [str(JDK/'java'),'-cp',temp,'DisposalProbe']]):
                run=subprocess.run(command,capture_output=True,text=True)
                stdout=f'logs/disposal-{variant}-{i}.stdout.txt';stderr=f'logs/disposal-{variant}-{i}.stderr.txt'
                (PACK/stdout).write_text(run.stdout);(PACK/stderr).write_text(run.stderr)
                results.append({'argv':command,'exit':run.returncode,'stdout':stdout,'stderr':stderr})
                if run.returncode:
                    (PACK/'disposal-probe.json').write_text(json.dumps(results,indent=2)+'\n')
                    raise SystemExit(run.stderr)
    for tool in ['java','javac']:
        run=subprocess.run([str(JDK/tool),'-version'],capture_output=True,text=True)
        results.append({'argv':[str(JDK/tool),'-version'],'exit':run.returncode,'output':run.stdout+run.stderr})
    (PACK/'disposal-probe.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Two actual-source failure witnesses and 20 candidate disposal/admission checks passed; unchanged extracted owner methods, bounded coordinator amendments, finite host leaves only.')

if __name__=='__main__':main()
