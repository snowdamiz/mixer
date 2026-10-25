import { DurableObject } from 'cloudflare:workers';
import { OperationState } from './operation-state.js';
import { Engine } from './engine.js';
import { UnavailableClock } from './clock.js';
import { UnavailableObjectVerifier, UnavailableProvider } from './provider.js';
export class MixerWorkerOperation extends DurableObject {
    #state;
    constructor(ctx, env) { super(ctx, env); this.#state = new OperationState(ctx, env, (ledger, context) => new Engine(ledger, new UnavailableClock(), new UnavailableProvider(), new UnavailableObjectVerifier(), undefined, context)); }
    async fetch(request) { return this.#state.fetch(request); }
    async recoverKnown(i, p, t) { return this.#state.recoverKnown(i, p, t); }
    async enrollExisting(i) { return this.#state.enrollExisting(i); }
    async alarm() { await this.#state.alarm(); }
}
