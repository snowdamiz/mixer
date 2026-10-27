import { createSignal, getOwner, onCleanup } from "solid-js";
import type { Accessor } from "solid-js";
import { createBrowserSessionController } from "./browser-session-controller.js";
import type { WorkspaceSession } from "./workspace-controller.js";

export interface BrowserSessionBinding {
  readonly workspaceSession: Accessor<WorkspaceSession>;
  revalidate(): void;
  invalidate(): void;
}

function invalidation(value: unknown): boolean {
  try {
    if (!value || typeof value !== "object" || Object.getPrototypeOf(value) !== Object.prototype) return false;
    const keys = Reflect.ownKeys(value);
    const field = Object.getOwnPropertyDescriptor(value, "type");
    return keys.length === 1 && keys[0] === "type" && field !== undefined && "value" in field && field.value === "invalidate";
  } catch { return false; }
}

/** Own inside a Solid owner. Browser events can only invalidate or request a fresh check. */
export function createBrowserSessionBinding(): BrowserSessionBinding {
  if (!getOwner()) throw new Error("Missing browser session owner");
  const controller = createBrowserSessionController();
  const [snapshot, setSnapshot] = createSignal(controller.getSession());
  let disposed = false, pagehidden = false, queued = false;
  let channel: BroadcastChannel | undefined;
  const hasBrowser = typeof document !== "undefined" && typeof window !== "undefined";
  const visible = () => hasBrowser && document.visibilityState === "visible" && !pagehidden;
  const unsubscribe = controller.subscribe(value => {
    if (disposed) return;
    if (!visible() && value.kind !== "unavailable") { controller.invalidate(); return; }
    setSnapshot(value);
  });
  const schedule = () => {
    if (disposed || queued || !visible()) return;
    queued = true;
    queueMicrotask(() => {
      if (!queued || disposed) return;
      queued = false;
      if (visible()) controller.revalidate();
    });
  };
  const foreground = () => {
    if (disposed) return;
    if (document.visibilityState !== "visible") { queued = false; controller.invalidate(); return; }
    pagehidden = false;
    schedule();
  };
  const hide = () => { pagehidden = true; queued = false; controller.invalidate(); };
  const message = (event: MessageEvent<unknown>) => {
    if (!disposed && invalidation(event.data)) { controller.invalidate(); schedule(); }
  };
  if (hasBrowser) {
    document.addEventListener("visibilitychange", foreground);
    window.addEventListener("focus", foreground);
    window.addEventListener("pageshow", foreground);
    window.addEventListener("pagehide", hide);
    if (typeof BroadcastChannel === "function") {
      try {
        channel = new BroadcastChannel("mixer.browser-session.v1");
        channel.addEventListener("message", message);
      } catch { /* Startup/foreground checks remain available without a channel. */ }
    }
    schedule();
  }
  onCleanup(() => {
    disposed = true; queued = false;
    if (hasBrowser) {
      document.removeEventListener("visibilitychange", foreground);
      window.removeEventListener("focus", foreground);
      window.removeEventListener("pageshow", foreground);
      window.removeEventListener("pagehide", hide);
    }
    if (channel) { channel.removeEventListener("message", message); channel.close(); channel = undefined; }
    unsubscribe(); controller.dispose();
    setSnapshot(controller.getSession());
  });
  return Object.freeze({
    workspaceSession(): WorkspaceSession {
      snapshot(); // Track notifications, but always enforce the live synchronous fence.
      if (!visible()) { queued = false; controller.invalidate(); }
      return controller.getSession();
    },
    revalidate(): void {
      if (disposed) return;
      queued = false;
      if (visible()) controller.revalidate(); else controller.invalidate();
    },
    invalidate(): void {
      if (disposed) return;
      queued = false;
      controller.invalidate();
      try { channel?.postMessage({ type: "invalidate" }); } catch { /* No credential or persistent fallback. */ }
    },
  });
}
