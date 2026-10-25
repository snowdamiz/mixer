import { createEffect, createSignal, on, onCleanup } from "solid-js";
import { createWorkspaceController } from "./workspace-controller.js";
/** One owner per console: route changes retain selection, session changes erase it. */
export function createWorkspaceBinding(session) {
    const controller = createWorkspaceController();
    const [state, setState] = createSignal(controller.getState());
    const unsubscribe = controller.subscribe(value => setState(value));
    // Effects do not fetch while server rendering. The static shell stays unavailable
    // until its client-side session adapter supplies ordinary customer authorization.
    createEffect(on(session, value => controller.setSession(value ?? { kind: "unavailable" })));
    onCleanup(() => {
        unsubscribe();
        controller.dispose();
        setState(controller.getState());
    });
    return Object.freeze({ state, controller });
}
