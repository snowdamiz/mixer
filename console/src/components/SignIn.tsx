import { useLocation } from "@solidjs/router";
import { createContext, createEffect, createSignal, on, onCleanup, Show, useContext } from "solid-js";
import type { Accessor, ParentProps } from "solid-js";
import type { ConsoleSession } from "../state/browser-session-controller.js";
import { createSignInAction } from "../state/sign-in-action.js";
import type { SignInState } from "../state/sign-in-action.js";
import { clearPromotionResume, promotionToResume, savePromotionResume } from "../state/promotion-resume.js";
import { promotionGroupQuery } from "../domain/release-head.js";

const Context = createContext<{
  readonly state: Accessor<SignInState>;
  readonly visible: () => boolean;
  readonly start: () => void;
  readonly cancelPromotion: () => void;
}>();

export function SignInBoundary(props: ParentProps<{ readonly session: Accessor<ConsoleSession>; readonly invalidate: () => void }>) {
  const [state, changed] = createSignal<SignInState>({ kind: "idle" });
  let pagehidden = false;
  const foreground = () => typeof document !== "undefined" && document.visibilityState === "visible" && !pagehidden;
  const clear = () => {
    try { clearPromotionResume(window.sessionStorage); } catch { /* Session storage can be blocked. */ }
  };
  const action = createSignInAction({ allowed: () => props.session().kind === "unauthenticated", foreground,
    invalidate: props.invalidate, changed, navigate: (url, promotion) => {
      clear();
      if (promotion) {
        const current = promotionToResume(window.location);
        if (current && promotionGroupQuery(current) === promotionGroupQuery(promotion.publication)) {
          try {
            savePromotionResume(window.sessionStorage, promotion.publication, promotion.marker, promotion.expiresAt);
          } catch { /* Sign-in can proceed without a continuation. */ }
        }
      }
      try { window.location.assign(url); } catch (error) { clear(); throw error; }
    } });
  const hide = () => { pagehidden = true; action.cancel(); };
  const visibility = () => { if (document.visibilityState !== "visible") action.cancel(); };
  const show = (event: PageTransitionEvent) => { pagehidden = false; if (event.persisted) clear(); };
  document.addEventListener("visibilitychange", visibility);
  window.addEventListener("pagehide", hide); window.addEventListener("pageshow", show);
  onCleanup(() => {
    action.dispose(); document.removeEventListener("visibilitychange", visibility);
    window.removeEventListener("pagehide", hide); window.removeEventListener("pageshow", show);
  });
  return <Context.Provider value={{
    state, visible: () => props.session().kind === "unauthenticated" || state().kind !== "idle",
    start: () => { void action.start(promotionToResume(window.location)); },
    cancelPromotion: action.cancelPromotion,
  }}>{props.children}</Context.Provider>;
}

export function SignIn() {
  const action = useContext(Context);
  const location = useLocation();
  createEffect(on(() => [location.pathname, location.search, location.hash], () => action?.cancelPromotion(), { defer: true }));
  return <Show when={action?.visible()}><div class="console-sign-in">
    <button type="button" class="workspace-page-button" disabled={action?.state().kind === "starting"} onClick={() => action?.start()}>
      {action?.state().kind === "starting" ? "Signing in…" : "Sign in"}
    </button>
    <Show when={action?.state().kind === "unavailable"}><p role="alert">Sign in is unavailable. Try again.</p></Show>
  </div></Show>;
}
