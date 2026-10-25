import { renderToString } from "solid-js/web";
import { ReleaseChecks } from "../src/components/ReleaseChecks.js";
import type { ReleaseCheckState } from "../src/components/ReleaseChecks.js";
export { example } from "../src/preview/ReleaseChecksPreview.js";

export function renderChecks(state: ReleaseCheckState): string {
  return renderToString(() => <ReleaseChecks state={state} />);
}
