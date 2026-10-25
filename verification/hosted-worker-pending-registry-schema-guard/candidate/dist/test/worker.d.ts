import { TestAudit, TestRegistry, FixtureRecovery } from './base-fixture.js';
import { PendingEnv } from '../src/pending-types.js';
export { TestRegistry, FixtureRecovery };
export declare class GuardAudit extends TestAudit {
    schemaFault(mode: string): Promise<unknown>;
    inspectSchema(): Promise<unknown>;
}
declare const _default: {
    fetch(request: Request, env: PendingEnv): Promise<Response>;
    scheduled: (_event: ScheduledController, env: PendingEnv, _ctx: ExecutionContext) => Promise<void>;
};
export default _default;
