import { renderToString } from "solid-js/web";
import { ReleaseChecks } from "./src/components/ReleaseChecks.js";
export const render = (state: any) => renderToString(() => <ReleaseChecks state={state} />);
