public final class ControlProbe {
  enum Outcome { ATTEMPTED, RETURNED, FAILED_UNCERTAIN }
  static final class Fence { boolean rendererReportActive; }
  static final class Ledger {
    Throwable primary, rendererFailure, engineFailure; Error firstFatal;
    Outcome renderer, engine;
  }
  static final class Renderer {
    int calls; boolean editorNativeOnStack, observedOnStack;
    void disposeV2() { calls++; observedOnStack = editorNativeOnStack; }
  }
  static final class NativeBridge { static int destroyed; static void destroy(long v) { destroyed++; } }
  final Fence fence = new Fence(); final Ledger ledger = new Ledger(); final Renderer renderer = new Renderer();
  boolean active, retired, disposed, cancellation;
  Object operation; long session = 1; byte[] committedPacket;
private void leave() {
        active = false; operation = null;
        if (retired && !cancellation && !fence.rendererReportActive) disposeOnce();
        if (ledger.firstFatal != null) throw ledger.firstFatal;
    }
private void disposeOnce() {
        if (disposed) return;
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
private void remember(Throwable failure) {
        if (failure == null) return;
        if (ledger.primary == null) ledger.primary = failure;
        if (failure instanceof Error fatal && ledger.firstFatal == null) ledger.firstFatal = fatal;
    }
  public static void main(String[] args) {
    ControlProbe unprotected = new ControlProbe();
    unprotected.retired = true; unprotected.renderer.editorNativeOnStack = true;
    unprotected.leave();
    if (unprotected.renderer.calls != 1 || !unprotected.renderer.observedOnStack || NativeBridge.destroyed != 1)
      throw new AssertionError("expected direct disposal while authored editor call remains on stack");
    ControlProbe cancellationProtected = new ControlProbe();
    cancellationProtected.retired = true; cancellationProtected.cancellation = true;
    cancellationProtected.leave();
    if (cancellationProtected.renderer.calls != 0) throw new AssertionError("existing cancellation guard");
    ControlProbe reportProtected = new ControlProbe();
    reportProtected.retired = true; reportProtected.fence.rendererReportActive = true;
    reportProtected.leave();
    if (reportProtected.renderer.calls != 0) throw new AssertionError("existing terminal-report guard");
    System.out.println("3 source-control groups passed: direct editor-stack hazard witnessed, existing cancellation/report guards preserved");
  }
}
