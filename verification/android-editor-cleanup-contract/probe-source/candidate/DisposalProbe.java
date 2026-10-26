
import java.util.ArrayList;
import java.util.List;
public class DisposalProbe {
    static final boolean AMENDED = true;
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
            boolean busyForOwnerDisposal() { requireMain(); return active || cancellation || fence.rendererReportActive || renderer.editorDisposalBusyV2(); }

            boolean inputCancellationInProgress() {
        requireMain(); return cancellation || renderer.cancellationInProgressV2();
    }

            private void enter() {
        requireMain();
        if (retired || fence.terminal) throw new IllegalStateException("V2 coordinator retired");
        if (active || cancellation || fence.rendererReportActive) throw new IllegalStateException("V2 coordinator reentrant call");
        operation = fence.operation;
        if (operation == null) throw new IllegalStateException("V2 owner operation required");
        active = true; sealGatesScalar();
    }

            void closeFromOwner() {
        requireMain();
        if (busyForOwnerDisposal()) throw new IllegalStateException("V2 coordinator disposal deferred");
        retireScalar(); disposeOnce();
        // Disposition reports its own release slots; an earlier operation primary is retained separately.
        if (ledger.rendererFailure instanceof Error || ledger.engineFailure instanceof Error) throw ledger.firstFatal;
        if (ledger.rendererFailure instanceof RuntimeException failure) throw failure;
        if (ledger.engineFailure instanceof RuntimeException failure) throw failure;
    }

            private void leave() {
        active = false; operation = null;
        if (retired && !cancellation && !fence.rendererReportActive) disposeOnce();
        if (ledger.firstFatal != null) throw ledger.firstFatal;
    }

            private void retireScalar() {
        retired = true; fence.terminal = true; fence.drawAllowed = false; fence.inputAllowed = false;
        sealGatesScalar(); committedPacket = null;
    }

            private void disposeOnce() {
        if (disposed || busyForOwnerDisposal()) return;
        disposed = true;
        long owned = session; session = 0; committedPacket = null;
        ledger.renderer = Outcome.ATTEMPTED;
        try { renderer.disposeV2(); ledger.renderer = Outcome.RETURNED; }
        catch (RuntimeException | Error failure) { ledger.rendererFailure = failure; ledger.renderer = Outcome.FAILED_UNCERTAIN; remember(failure); }
        if (owned != 0) {
            ledger.engine = Outcome.ATTEMPTED;
            try { NativeBridge.destroy(owned); ledger.engine = Outcome.RETURNED; }
            catch (RuntimeException | Error failure) { ledger.engineFailure = failure; ledger.engine = Outcome.FAILED_UNCERTAIN; remember(failure); }
        }
    }

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
        private enum WorkKind { DRAIN, TERMINAL_CLOSE }
    private final class Work implements Runnable {
        final WorkKind kind;
        final OwnerLifecycleV2.Token token;
        final NativeCoordinatorV2 resource;
        boolean posting, cancellationPending;
        OwnerLifecycleV2.Token cancellationToken;
        Work(WorkKind kind, OwnerLifecycleV2.Token token, NativeCoordinatorV2 resource) {
            this.kind = kind; this.token = token; this.resource = resource;
        }
        @Override public void run() {
            requireMain();
            if (queued != this) return;
            queued = null; // consume before any callback or concrete probe
            try {
                if (kind == WorkKind.TERMINAL_CLOSE) {
                    if (pendingCloseResource != resource || pendingCloseToken != token) return;
                    closePending();
                } else {
                    if (fence.terminal || token == null || core.snapshot().pendingDrain() != token) return;
                    seal(false);
                    if (!fence.terminal) seedFocus();
                    if (!fence.terminal) process(core.drain(lifetime, token, probeWindow()), null);
                }
            } catch (RuntimeException | Error failure) { fail(failure, Cause.CORE_FAILURE); }
            finally { settle(); }
            throwFatal();
        }
    }

        private void post(Work work) {
        queued = work; work.posting = true;
        try {
            if (!handler.post(work)) throw new IllegalStateException("main Handler rejected V2 work");
        } catch (RuntimeException | Error failure) {
            remember(failure);
            if (work.kind == WorkKind.TERMINAL_CLOSE) {
                if (queued == work) queued = null;
                work.cancellationPending = true;
                ledger.handler = Outcome.DEFERRED;
                ledger.coordinator = Outcome.DEFERRED; return;
            }
            terminate(Cause.SCHEDULING_FAILED, null, failure, failure instanceof Error fatal ? fatal : null, NativeEnvironmentV2.Change.EPOCH_EXHAUSTED);
        } finally {
            work.posting = false;
            // A callback may consume/cancel the slot before Handler.post acquires its native queue entry.
            if (work.cancellationPending || queued != work) {
                OwnerLifecycleV2.Token token = work.cancellationToken;
                work.cancellationToken = null; work.cancellationPending = false;
                removeWork(work, token);
            }
        }
    }

        private void removeWork(Work owned, OwnerLifecycleV2.Token token) {
        ledger.handler = Outcome.ATTEMPTED;
        Throwable failure = null;
        try { if (owned != null) handler.removeCallbacks(owned); ledger.handler = Outcome.RETURNED; }
        catch (RuntimeException | Error caught) { failure = caught; ledger.handlerFailure = caught; ledger.handler = Outcome.FAILED_UNCERTAIN; remember(caught); }
        completeCleanup(token, failure);
    }

        private void closePending() {
        NativeCoordinatorV2 owned = pendingCloseResource;
        if (owned == null) return;
        if (effectDepth != 0 || activeOperation != null || owned.busyForOwnerDisposal()) { ledger.coordinator = Outcome.DEFERRED; return; }
        OwnerLifecycleV2.Token token = pendingCloseToken;
        pendingCloseResource = null; pendingCloseToken = null;
        ledger.coordinator = Outcome.ATTEMPTED;
        Throwable failure = null;
        try { owned.closeFromOwner(); ledger.coordinator = Outcome.RETURNED; }
        catch (RuntimeException | Error caught) { failure = caught; ledger.coordinatorFailure = caught; ledger.coordinator = Outcome.FAILED_UNCERTAIN; }
        finally {
            NativeCoordinatorV2.CleanupLedger retained = owned.cleanupLedger();
            remember(retained.primary());
            remember(retained.firstFatal());
        }
        remember(failure);
        completeCleanup(token, failure);
    }

        private void settle() {
        unregisterPending();
        if (pendingCloseResource == null || effectDepth != 0 || activeOperation != null) return;
        if (pendingCloseResource.busyForOwnerDisposal()) {
            if (queued == null) post(new Work(WorkKind.TERMINAL_CLOSE, pendingCloseToken, pendingCloseResource));
        } else closePending();
    }

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
            check(c.renderer.disposals==1&&p.queued==null,"actual current predicate does NOT defer for renderer depth");
            p=new DisposalProbe();c=new NativeCoordinatorV2(p.fence);c.renderer.editorDepth=1;c.retired=true;c.active=true;c.leave();
            check(c.disposed&&c.renderer.unsafeDisposal,"actual leave bypasses owner busy predicate and disposes native editor stack");
            System.out.println("actual source: witnessed both owner predicate omission and coordinator leave disposal bypass despite editor depth");return;
        }
        check(c.renderer.disposals==0&&p.queued!=null&&p.pendingCloseResource==c,"exact pending retained while depth busy");checks++;
        c.renderer.editorDepth=0;p.handler.next();
        check(c.renderer.disposals==1&&p.pendingCloseResource==null&&p.queued==null&&p.completions==1,"existing owner Work resumes disposal after depth zero");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.cleanupDrain=true;p.settle();
        check(p.queued!=null&&c.renderer.disposals==0,"cleanup drain also disposal busy");checks++;
        c.renderer.cleanupDrain=false;p.handler.next();check(c.renderer.disposals==1,"cleanup completion resumes exact disposal");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.handler.reject=true;p.settle();
        check(p.queued==null&&p.pendingCloseResource==c&&p.pendingCloseToken!=null&&c.renderer.disposals==0&&p.ledger.coordinator==Outcome.DEFERRED,"scheduler rejection retains pending, no fabricated returned");checks++;
        c.renderer.editorDepth=0;check(p.handler.queue.isEmpty()&&c.renderer.disposals==0,"no autonomous wake under scheduler rejection");checks++;
        p.settle();check(c.renderer.disposals==1,"future owner entry may resume retained disposal");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.handler.fail=true;p.settle();
        check(p.queued==null&&p.pendingCloseResource==c&&p.primary!=null&&c.renderer.disposals==0,"throwing scheduler retains pending and primary");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.activeOperation=new OwnerLifecycleV2.Token();p.settle();
        check(c.renderer.disposals==0&&p.queued==null&&p.pendingCloseResource==c,"active owner operation keeps pending");checks++;
        p.activeOperation=null;p.settle();check(p.queued!=null,"subsequent owner settle schedules retained disposal");checks++;
        c.renderer.editorDepth=0;p.handler.next();check(c.renderer.disposals==1,"resumes after operation and native unwind");checks++;
        p=new DisposalProbe();c=p.pending();c.renderer.editorDepth=1;p.settle();NativeCoordinatorV2 old=c;
        NativeCoordinatorV2 newer=p.pending();p.handler.next();
        check(old.renderer.disposals==0&&newer.renderer.disposals==1,"stale task does not dispose old/foreign token; finally settles exact current pending");checks++;
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
