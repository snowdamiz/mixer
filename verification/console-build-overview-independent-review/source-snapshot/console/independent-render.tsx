import { renderToString } from "solid-js/web";
import { BuildOverview } from "./src/components/BuildOverview.js";
export const render = (state: any) => renderToString(() => <BuildOverview state={state} />);
