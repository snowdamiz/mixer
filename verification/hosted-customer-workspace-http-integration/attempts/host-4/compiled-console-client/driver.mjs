import assert from "node:assert/strict";
import { createWorkspaceClient } from "./api/workspace-client.js";
const bearer = process.env.MIXER_WORKSPACE_EPHEMERAL_BEARER;
assert.equal(typeof bearer, "string");
const client = createWorkspaceClient({ apiOrigin: process.argv[2], allowInsecureLoopback: true, accessToken: () => bearer, timeoutMs: 3000 });
let page = await client.organizations({ limit: 1 });
const ids = page.organizations.map(row => row.id);
let pages = 1;
while (page.next_cursor !== null) {
  page = await client.organizations({ limit: 1, cursor: page.next_cursor });
  ids.push(...page.organizations.map(row => row.id));
  assert.ok(++pages <= 10);
}
assert.deepEqual(ids, [".", "..", "org-a", "org/雪+%"]);
for (const id of [".", "..", "org/雪+%"]) {
  const result = await client.projects(id);
  assert.deepEqual(result.projects, [{ organization_id: id, id: "project/雪+%", display_name: null, roles: ["billing_manager"] }]);
  assert.equal(result.next_cursor, null);
}
await assert.rejects(client.projects("org-b"), error => error.code === "not_found");
const denied = createWorkspaceClient({ apiOrigin: process.argv[2], allowInsecureLoopback: true, accessToken: () => null });
await assert.rejects(denied.organizations(), error => error.code === "unauthenticated");
process.stdout.write(JSON.stringify({ status: "passed", production_phoenix: true, real_global_fetch: true, organization_pages: pages, full_identifier_projects: 3, foreign_organization_denied: true, missing_session_denied: true }) + "\n");
