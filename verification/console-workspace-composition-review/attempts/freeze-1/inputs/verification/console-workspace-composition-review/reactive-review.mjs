// Independent host-only probes. No DOM, browser, native instance, or capture.
import assert from 'node:assert/strict';
import test from 'node:test';
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';

const runtime = process.env.MIXER_REVIEW_RUNTIME;
const { createWorkspaceController } = await import(pathToFileURL(join(runtime, 'state/workspace-controller.js')));
const { createWorkspaceBinding } = await import(pathToFileURL(join(runtime, 'state/workspace-binding.js')));
const { WorkspaceClientError } = await import(pathToFileURL(join(runtime, 'api/workspace-client.js')));
const { createRoot, createSignal, createMemo, createComputed, batch, untrack } =
  await import(pathToFileURL(join(process.env.MIXER_REVIEW_DEPENDENCIES, 'solid-js/dist/solid.js')));

const organizations = (id = 'old-org') => ({ organizations: [{ id, display_name: `private:${id}`, organization_roles: ['owner'] }], next_cursor: null });
const projects = id => ({ projects: [{ organization_id: id, id: 'project', display_name: 'private:project', roles: ['viewer'] }], next_cursor: null });
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const flush = () => new Promise(resolve => setImmediate(resolve));
const controlled = () => {
  const calls = [];
  const start = (list, id, page, signal) => {
    const promise = deferred(); calls.push({ list, id, page, signal, ...promise }); return promise.promise;
  };
  return { calls, client: { organizations: (page, signal) => start('organizations', undefined, page, signal),
    projects: (id, page, signal) => start('projects', id, page, signal) } };
};
const empty = (state, kind) => assert.deepEqual(state, { organizations: { kind }, projects: { kind: 'unselected' } });
async function loadOld(binding, api, setSession) {
  setSession({ kind: 'ready', client: api.client });
  api.calls.at(-1).resolve(organizations()); await flush();
  binding.controller.selectOrganization('old-org');
  api.calls.at(-1).resolve(projects('old-org')); await flush();
  binding.controller.selectProject({ organizationId: 'old-org', projectId: 'project' });
  assert.equal(binding.state().selectedProjectId, 'project');
}
function owner(observeBefore = () => {}) {
  let binding, setSession, dispose, session;
  createRoot(stop => {
    dispose = stop;
    [session, setSession] = createSignal(undefined);
    observeBefore(session, () => binding);
    binding = createWorkspaceBinding(session);
  });
  return { binding, setSession, dispose, session };
}

test('earlier memo and later computed never pair a replacement session with old rows', async () => {
  const old = controlled(); const next = controlled(); const observations = [];
  const app = owner((session, binding) => {
    const value = createMemo(() => ({ session: session(), state: binding()?.state() }));
    createComputed(() => observations.push({ location: 'before', ...value() }));
  });
  createRoot(stop => { app.stopObserver = stop; createComputed(() => observations.push({ location: 'after', session: app.session(), state: app.binding.state() })); });
  try {
    await loadOld(app.binding, old, app.setSession);
    for (const replacement of [{ kind: 'unauthenticated' }, undefined, { kind: 'ready', client: next.client }]) {
      observations.length = 0;
      app.setSession(replacement);
      assert.ok(observations.length >= 2);
      for (const observation of observations) {
        assert.equal(observation.session, replacement);
        assert.doesNotMatch(JSON.stringify(observation.state), /private:|old-org|project"/);
      }
      if (replacement?.kind === 'ready') empty(app.binding.state(), 'loading');
      else await loadOld(app.binding, old, app.setSession);
    }
    assert.deepEqual(Object.keys(app.binding.controller).sort(), [
      'nextOrganizations', 'nextProjects', 'retryOrganizations', 'retryProjects', 'selectOrganization', 'selectProject']);
  } finally { app.stopObserver(); app.dispose(); }
});

test('batched session changes hide rows and reject all stale commands before effect admission', async () => {
  for (const replacementKind of ['unauthenticated', 'unavailable', 'ready']) {
    const old = controlled(); const next = controlled(); const app = owner();
    try {
      await loadOld(app.binding, old, app.setSession);
      const count = old.calls.length;
      batch(() => {
        app.setSession(replacementKind === 'ready' ? { kind: 'ready', client: next.client } : { kind: replacementKind });
        empty(app.binding.state(), replacementKind === 'ready' ? 'loading' : replacementKind);
        const actions = app.binding.controller;
        actions.selectOrganization('old-org'); actions.selectProject({ organizationId: 'old-org', projectId: 'project' });
        actions.nextOrganizations('CURSOR'); actions.nextProjects({ organizationId: 'old-org', cursor: 'CURSOR' });
        actions.retryOrganizations(); actions.retryProjects('old-org');
        assert.equal(old.calls.length, count);
        assert.equal(next.calls.length, 0);
      });
      assert.equal(next.calls.length, replacementKind === 'ready' ? 1 : 0);
    } finally { app.dispose(); }
  }
});

test('an earlier pure consumer cannot issue an old-session request during logout', async () => {
  const old = controlled(); let armed = false; let commandAttempts = 0;
  const app = owner((session, binding) => createComputed(() => {
    if (session()?.kind === 'unauthenticated' && armed) untrack(() => {
      commandAttempts++; binding().controller.selectOrganization('old-org');
      binding().controller.retryOrganizations();
    });
  }));
  try {
    await loadOld(app.binding, old, app.setSession);
    const count = old.calls.length; armed = true;
    app.setSession({ kind: 'unauthenticated' });
    assert.equal(commandAttempts, 1); assert.equal(old.calls.length, count);
    empty(app.binding.state(), 'unauthenticated');
  } finally { app.dispose(); }
});

test('same client in a fresh immutable session epoch clears ready selection', async () => {
  const old = controlled(); const app = owner();
  try {
    await loadOld(app.binding, old, app.setSession);
    batch(() => { app.setSession({ kind: 'ready', client: old.client }); empty(app.binding.state(), 'loading'); });
    assert.equal(old.calls.length, 3); assert.deepEqual(old.calls.at(-1).page, {});
    old.calls.at(-1).resolve(organizations('new-org')); await flush();
    assert.equal(app.binding.state().organizations.input.organizations[0].id, 'new-org');
    assert.equal(app.binding.state().selectedOrganizationId, undefined);
    assert.equal(app.binding.state().selectedProjectId, undefined);
  } finally { app.dispose(); }
});

test('all completion orders across three same-client epochs commit only the last request', async () => {
  const orders = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]];
  for (const order of orders) for (const staleFailure of [false, true]) {
    const controller = createWorkspaceController(); const api = controlled();
    try {
      for (let i = 0; i < 3; i++) controller.setSession({ kind: 'ready', client: api.client });
      for (const index of order) {
        const call = api.calls[index];
        if (index < 2 && staleFailure) call.reject(new WorkspaceClientError('unauthenticated'));
        else call.resolve(organizations(`epoch-${index}`));
        await flush();
        if (controller.getState().organizations.kind === 'ready') {
          assert.equal(controller.getState().organizations.input.organizations[0].id, 'epoch-2');
        } else empty(controller.getState(), 'loading');
      }
      assert.equal(api.calls[0].signal.aborted, true); assert.equal(api.calls[1].signal.aborted, true);
      assert.equal(controller.getState().organizations.input.organizations[0].id, 'epoch-2');
    } finally { controller.dispose(); }
  }
});

test('project validation reentrancy cannot publish rows into a replacement session', async () => {
  const controller = createWorkspaceController(); const api = controlled();
  try {
    controller.setSession({ kind: 'ready', client: api.client }); api.calls[0].resolve(organizations()); await flush();
    controller.selectOrganization('old-org');
    const page = projects('old-org');
    Object.defineProperty(page.projects[0], 'roles', { enumerable: true, get() {
      controller.setSession({ kind: 'ready', client: api.client }); return ['viewer'];
    } });
    api.calls[1].resolve(page); await flush();
    empty(controller.getState(), 'loading');
    assert.equal(api.calls.length, 3);
    api.calls[2].resolve(organizations('replacement')); await flush();
    assert.equal(controller.getState().organizations.input.organizations[0].id, 'replacement');
    assert.equal(controller.getState().selectedProjectId, undefined);
  } finally { controller.dispose(); }
});

test('subscriber churn and nested session replacement never deliver superseded revision', async () => {
  const controller = createWorkspaceController(); const seen = []; let stopLate, added = false;
  const api = controlled();
  try {
    controller.subscribe(state => {
      if (state.organizations.kind !== 'loading') return;
      stopLate(); controller.setSession({ kind: 'unauthenticated' });
      if (!added) { added = true; controller.subscribe(next => seen.push(`new:${next.organizations.kind}`)); }
    });
    stopLate = controller.subscribe(state => seen.push(`late:${state.organizations.kind}`));
    controller.subscribe(state => seen.push(`last:${state.organizations.kind}`));
    controller.setSession({ kind: 'ready', client: api.client });
    assert.deepEqual(seen, ['late:unavailable', 'last:unavailable', 'last:unauthenticated', 'new:unauthenticated']);
    assert.equal(api.calls.length, 0);
  } finally { controller.dispose(); }
});

test('binding disposal is visible inside abort handlers and cannot revive via retained actions', async () => {
  const api = controlled(); const app = owner(); let observed = 0;
  app.setSession({ kind: 'ready', client: api.client });
  const call = api.calls[0];
  call.signal.addEventListener('abort', () => {
    observed++; empty(app.binding.state(), 'unavailable');
    app.binding.controller.selectOrganization('old-org'); app.binding.controller.retryOrganizations();
    app.setSession({ kind: 'ready', client: api.client });
  }, { once: true });
  app.dispose(); assert.equal(observed, 1); assert.equal(api.calls.length, 1);
  call.resolve(organizations()); await flush();
  empty(app.binding.state(), 'unavailable'); assert.equal(api.calls.length, 1);
});

test('rejected asynchronous observers are isolated without unhandled rejection', async () => {
  const controller = createWorkspaceController(); const unhandled = []; const listener = error => unhandled.push(error);
  process.on('unhandledRejection', listener);
  try {
    controller.subscribe(async () => { throw Error('private:observer'); });
    const seen = []; controller.subscribe(state => seen.push(state.organizations.kind));
    controller.setSession({ kind: 'unauthenticated' }); await flush();
    assert.deepEqual(unhandled, []); assert.deepEqual(seen, ['unavailable', 'unauthenticated']);
  } finally { controller.dispose(); process.off('unhandledRejection', listener); }
});
