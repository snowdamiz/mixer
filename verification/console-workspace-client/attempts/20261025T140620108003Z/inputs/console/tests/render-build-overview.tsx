import { renderToString } from "solid-js/web";
import { BuildOverview } from "../src/components/BuildOverview.js";
import type { BuildOverviewState } from "../src/components/BuildOverview.js";
export { buildExample } from "../src/preview/BuildOverviewPreview.js";

export function renderBuildOverview(state: BuildOverviewState): string {
  return renderToString(() => <BuildOverview state={state} />);
}
