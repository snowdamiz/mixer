// EXCLUDED independent review fixture. Imports the frozen compiled component.
import entry, {TestRegistry, TestAudit, FixtureRecovery} from '../hosted-worker-pending-registry-components/candidate/dist/test/worker.js';
import {config, auditName} from '../hosted-worker-pending-registry-components/candidate/dist/src/pending-types.js';
export {TestRegistry, FixtureRecovery};
export class ReviewAudit extends TestAudit {
  async removeSchemaMetaForReview() {
    this.ctx.storage.sql.exec('DROP TABLE pending_audit_meta');
    await this.ctx.storage.sync();
  }
}
export default {
  async fetch(request, env, ctx) {
    const data = await request.clone().json();
    if (data.action === 'reviewRemoveAuditMeta') {
      const c = config(env);
      const audit = env.PENDING_AUDIT.get(env.PENDING_AUDIT.idFromName(auditName(c)));
      await audit.removeSchemaMetaForReview();
      return Response.json({ok: true});
    }
    return entry.fetch(request, env, ctx);
  },
  scheduled: entry.scheduled,
};
