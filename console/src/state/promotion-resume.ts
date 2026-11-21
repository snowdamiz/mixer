import { parseReleaseHeadSearch, promotionGroupQuery } from "../domain/release-head.js";
import type { PromotionPublication } from "../domain/release-head.js";

const releases = "/releases";
const landing = "/workspace";
const markerPrefix = "#promotion-resume=";
const storageKey = "mixer.promotion-resume.v1";
const lifetimeSeconds = 300;
// Five catalog IDs of at most 128 ASCII characters, two hashes, and fixed fields.
const maxSearchLength = 1024;

type Route = Pick<Location, "pathname" | "search" | "hash">;
type ResumeStorage = Pick<Storage, "getItem" | "removeItem" | "setItem">;

export type PromotionResumeMarker = string & { readonly __brand: "PromotionResumeMarker" };

export function isPromotionResumeMarker(value: unknown): value is PromotionResumeMarker {
  // Canonical unpadded base64url encoding of 32 bytes.
  return typeof value === "string" && value.length === 43 && /^[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]$/u.test(value);
}

function canonicalPromotion(search: string): PromotionPublication | undefined {
  if (search.length > maxSearchLength) return;
  const selection = parseReleaseHeadSearch(search);
  if (selection.kind === "promotion" && search === "?" + promotionGroupQuery(selection.publication)) {
    return selection.publication;
  }
}

export function promotionToResume(route: Route): PromotionPublication | undefined {
  if (route.pathname === releases && route.hash === "") return canonicalPromotion(route.search);
}

function validExpiry(expiresAt: number, now: number): boolean {
  return Number.isSafeInteger(expiresAt) && expiresAt > now && expiresAt - now <= lifetimeSeconds;
}

export function savePromotionResume(
  storage: ResumeStorage,
  promotion: PromotionPublication,
  marker: PromotionResumeMarker,
  expiresAt: number,
  now = Math.floor(Date.now() / 1000),
): void {
  if (validExpiry(expiresAt, now)) {
    storage.setItem(storageKey, expiresAt + "|" + marker + "|?" + promotionGroupQuery(promotion));
  }
}

export function clearPromotionResume(storage: Pick<ResumeStorage, "removeItem">): void {
  storage.removeItem(storageKey);
}

// Consumes the slot before interpreting it, on all startup routes. Only the fixed
// callback landing can restore a selector. A failed match still strips its marker.
export function consumePromotionResume(
  route: Route,
  getStorage: () => ResumeStorage,
  now = Math.floor(Date.now() / 1000),
): string | undefined {
  const returning = route.pathname === landing && route.search === "" && route.hash.startsWith(markerPrefix);
  try {
    const storage = getStorage();
    const record = storage.getItem(storageKey);
    clearPromotionResume(storage);
    if (returning && record && record.length <= maxSearchLength + 64) {
      const [expiry, marker, search, extra] = record.split("|", 4);
      if (expiry && /^[1-9][0-9]{0,15}$/u.test(expiry) && validExpiry(Number(expiry), now) &&
          isPromotionResumeMarker(marker) && route.hash === markerPrefix + marker && search && extra === undefined) {
        const publication = canonicalPromotion(search);
        if (publication) return releases + "?" + promotionGroupQuery(publication);
      }
    }
  } catch { /* Ordinary sign-in remains available when session storage is blocked. */ }
  if (returning) return landing;
}

export function applyPromotionResume(browser: Window): void {
  const path = consumePromotionResume(browser.location, () => browser.sessionStorage);
  if (path !== undefined) {
    try { browser.history.replaceState(browser.history.state, "", path); } catch { /* Keep the ordinary landing. */ }
  }
}
