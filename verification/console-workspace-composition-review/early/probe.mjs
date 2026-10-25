import { createRoot, createSignal, createComputed, createMemo } from '../../../console/node_modules/solid-js/dist/solid.js';
import { createWorkspaceBinding } from './build/state/workspace-binding.js';

const orgs = { organizations: [{ id: 'old-org', display_name: 'Old private org', organization_roles: ['owner'] }], next_cursor: null };
const client = { organizations: async () => orgs, projects: async () => ({ projects: [], next_cursor: null }) };
const nextClient = { organizations: () => new Promise(() => {}), projects: async () => ({ projects: [], next_cursor: null }) };
let binding, session, setSession, dispose;
const observations = [];
createRoot(stop => {
  dispose = stop;
  [session, setSession] = createSignal(undefined);
  const oldConsumer = createMemo(() => {
    const current = session();
    const state = binding?.state();
    return { who: 'memo-created-before-binding', session: current?.kind ?? 'none', state: state?.organizations.kind ?? 'none', rows: state?.organizations.input };
  });
  createComputed(() => observations.push(oldConsumer()));
  binding = createWorkspaceBinding(session);
  createComputed(() => observations.push({ who: 'computed-after-binding', session: session()?.kind ?? 'none', state: binding.state().organizations.kind, rows: binding.state().organizations.input }));
});
setSession({ kind: 'ready', client });
await Promise.resolve(); await Promise.resolve();
observations.length = 0;
setSession({ kind: 'unauthenticated' });
const logout = observations.slice();
setSession({ kind: 'ready', client });
await Promise.resolve(); await Promise.resolve();
observations.length = 0;
setSession({ kind: 'ready', client: nextClient });
const replacement = observations.slice();
console.log(JSON.stringify({ logout, replacement }, null, 2));
dispose();
