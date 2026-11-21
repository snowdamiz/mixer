import { createBrowserLoginClient } from "../api/browser-login-client.js";
import type { PromotionPublication } from "../domain/release-head.js";
import type { PromotionResumeMarker } from "./promotion-resume.js";

export type SignInState = Readonly<{ kind: "idle" } | { kind: "starting" } | { kind: "unavailable" }>;
type PromotionDeparture = Readonly<{ publication: PromotionPublication; marker: PromotionResumeMarker; expiresAt: number }>;

export function createSignInAction(options: {
  readonly allowed: () => boolean;
  readonly foreground: () => boolean;
  readonly invalidate: () => void;
  readonly navigate: (url: string, promotion?: PromotionDeparture) => void;
  readonly changed: (state: SignInState) => void;
  readonly client?: ReturnType<typeof createBrowserLoginClient>;
}) {
  const client = options.client ?? createBrowserLoginClient();
  let state: SignInState = { kind: "idle" };
  let epoch = 0, disposed = false;
  let active: { readonly controller: AbortController; readonly promotion?: PromotionPublication | undefined } | undefined;
  const set = (next: SignInState) => { state = next; options.changed(state); };
  const cancel = () => { epoch++; active?.controller.abort(); active = undefined; if (!disposed && state.kind === "starting") set({ kind: "unavailable" }); };
  return Object.freeze({
    cancel,
    cancelPromotion() { if (active?.promotion) cancel(); },
    async start(promotion?: PromotionPublication): Promise<void> {
      if (disposed || state.kind === "starting" || !options.foreground() || (!options.allowed() && state.kind !== "unavailable")) return;
      const current = ++epoch;
      const controller = new AbortController(); active = { controller, promotion };
      set({ kind: "starting" }); options.invalidate();
      try {
        const login = await client.begin(controller.signal, promotion ? "promotion-group" : undefined);
        if (disposed || current !== epoch || controller.signal.aborted || !options.foreground()) return;
        options.navigate(login.url, promotion && login.promotionResume
          ? { publication: promotion, marker: login.promotionResume, expiresAt: login.expiresAt }
          : undefined);
      } catch {
        if (!disposed && current === epoch && options.foreground()) set({ kind: "unavailable" });
      } finally { if (current === epoch) active = undefined; }
    },
    dispose() { disposed = true; cancel(); },
  });
}
