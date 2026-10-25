const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const rows = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, 'cross-runtime-vectors.json'), 'utf8')).vectors;
const hash = text => crypto.createHash('sha256').update(text, 'utf8').digest('hex');
const decimal = text => {
  assert.match(text, /^(0|[1-9][0-9]*)$/);
  assert(BigInt(text) <= 9223372036854775807n);
  return text;
};
for (const v of rows) {
  const r = v.ref, s = v.spec;
  const original = ['mixer-build-operation-v1', v.guard.record_id, r.organization_id,
    r.project_id, r.application_id, r.build_id, r.platform, r.attempt];
  // Preserve the original algorithm's integer token without JS Number rounding.
  const legacy = '[' + original.map(x => JSON.stringify(x)).join(',') + ',' + decimal(r.fence) + ']';
  assert.equal(hash(legacy), v.operation_id);
  const binding = ['mixer-worker-binding-v1', v.operation_id, v.guard.record_id,
    [r.organization_id, r.project_id, r.application_id, r.build_id, r.platform, r.attempt, decimal(r.fence)],
    [s.organization_id, s.project_id, s.application_id, s.build_id, s.platform, s.source.kind,
      s.source.sha256, s.source.reference, s.toolchain_lock_sha256, s.build_definition_sha256], decimal(v.deadline_ms)];
  assert.equal(hash(JSON.stringify(binding)), v.immutable_sha256);
}
assert.equal(new Set(rows.map(x => x.operation_id)).size, rows.length);
console.log(JSON.stringify({scope: 'actual-Elixir-wire-vs-JavaScript-bytes-only', vectors: rows.length,
  node: process.version, operation_id_algorithm_preserved: true, immutable_binding_matches: true}));
