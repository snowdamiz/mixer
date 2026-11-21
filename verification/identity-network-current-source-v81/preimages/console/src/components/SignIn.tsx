import { createContext, createSignal, onCleanup, Show, useContext } from "solid-js";
import type { Accessor, ParentProps } from "solid-js";
import type { ConsoleSession } from "../state/browser-session-controller.js";
import { createSignInAction } from "../state/sign-in-action.js";
import type { SignInState } from "../state/sign-in-action.js";

const Context = createContext<{ readonly state: Accessor<SignInState>; readonly visible: () => boolean; readonly start: () => void }>();

export function SignInBoundary(props: ParentProps<{ readonly session: Accessor<ConsoleSession>; readonly invalidate: () => void }>) {
  const [state, changed] = createSignal<SignInState>({ kind: "idle" });
  let pagehidden = false;
  const foreground = () => typeof document !== "undefined" && document.visibilityState === "visible" && !pagehidden;
  const action = createSignInAction({ allowed: () => props.session().kind === "unauthenticated", foreground,
    invalidate: props.invalidate, changed, navigate: url => window.location.assign(url) });
  const hide = () => { pagehidden = true; action.cancel(); };
  const visibility = () => { if (document.visibilityState !== "visible") action.cancel(); };
  const show = () => { pagehidden = false; };
  document.addEventListener("visibilitychange", visibility);
  window.addEventListener("pagehide", hide); window.addEventListener("pageshow", show);
  onCleanup(() => {
    action.dispose(); document.removeEventListener("visibilitychange", visibility);
    window.removeEventListener("pagehide", hide); window.removeEventListener("pageshow", show);
  });
  return <Context.Provider value={{ state, visible: () => props.session().kind === "unauthenticated" || state().kind !== "idle", start: () => { void action.start(); } }}>{props.children}</Context.Provider>;
}

export function SignIn() {
  const action = useContext(Context);
  return <Show when={action?.visible()}><div class="console-sign-in">
    <button type="button" class="workspace-page-button" disabled={action?.state().kind === "starting"} onClick={() => action?.start()}>
      {action?.state().kind === "starting" ? "Signing in…" : "Sign in"}
    </button>
    <Show when={action?.state().kind === "unavailable"}><p role="alert">Sign in is unavailable. Try again.</p></Show>
  </div></Show>;
}
