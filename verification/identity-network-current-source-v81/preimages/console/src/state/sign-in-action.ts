import { createBrowserLoginClient } from "../api/browser-login-client.js";

export type SignInState = Readonly<{ kind: "idle" } | { kind: "starting" } | { kind: "unavailable" }>;

export function createSignInAction(options: {
  readonly allowed: () => boolean;
  readonly foreground: () => boolean;
  readonly invalidate: () => void;
  readonly navigate: (url: string) => void;
  readonly changed: (state: SignInState) => void;
  readonly client?: ReturnType<typeof createBrowserLoginClient>;
}) {
  const client = options.client ?? createBrowserLoginClient();
  let state: SignInState = { kind: "idle" };
  let epoch = 0, disposed = false;
  let active: AbortController | undefined;
  const set = (next: SignInState) => { state = next; options.changed(state); };
  const cancel = () => { epoch++; active?.abort(); active = undefined; if (!disposed && state.kind === "starting") set({ kind: "unavailable" }); };
  return Object.freeze({
    cancel,
    async start(): Promise<void> {
      if (disposed || state.kind === "starting" || !options.foreground() || (!options.allowed() && state.kind !== "unavailable")) return;
      const current = ++epoch;
      const controller = new AbortController(); active = controller;
      set({ kind: "starting" }); options.invalidate();
      try {
        const url = await client.begin(controller.signal);
        if (disposed || current !== epoch || controller.signal.aborted || !options.foreground()) return;
        options.navigate(url);
      } catch {
        if (!disposed && current === epoch && options.foreground()) set({ kind: "unavailable" });
      } finally { if (current === epoch) active = undefined; }
    },
    dispose() { disposed = true; cancel(); },
  });
}
