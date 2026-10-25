import { ingress } from './principal.js';
import { errorResponse } from './wire.js';
import { budget, config, pendingIdentity, registration } from './entry-context.js';
import { auditName, wait } from './pending-types.js';
export { MixerWorkerOperation } from './operation.js';
export { MixerPendingRegistryShard } from './pending-registry.js';
export { MixerPendingAuditCoordinator } from './pending-audit.js';
export default {
    async fetch(request, env) {
        let timer;
        const controller = new AbortController(), b = budget(request.signal);
        const check = () => { b.check(); if (controller.signal.aborted)
            throw new Error('entry_deadline'); };
        const timeout = new Promise(resolve => { timer = setTimeout(() => { controller.abort(); resolve(errorResponse(503)); }, 4000); });
        const work = async () => {
            try {
                const checked = await ingress(request, env);
                check();
                if (checked instanceof Response)
                    return checked;
                const c = config(env), i = await pendingIdentity(checked.r, c, b);
                check();
                await registration(env, c, i.value, b);
                check();
                // Registration and every post-await deadline check precede operation allocation.
                const id = env.OPERATIONS.idFromName(i.value.operationKey);
                check();
                const operation = env.OPERATIONS.get(id);
                check();
                const response = await operation.fetch(new Request(request.url, { method: 'POST', headers: request.headers, body: checked.bytes, signal: controller.signal }));
                check();
                return response;
            }
            catch {
                return errorResponse(503);
            }
        };
        try {
            return await Promise.race([work(), timeout]);
        }
        finally {
            if (timer !== undefined)
                clearTimeout(timer);
        }
    },
    async scheduled(_event, env) { try {
        const c = config(env), port = env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c)));
        await wait(port.runScheduled(), 24000);
    }
    catch { /* Fixed audit remains unavailable; no alternate trigger or identity. */ } }
};
