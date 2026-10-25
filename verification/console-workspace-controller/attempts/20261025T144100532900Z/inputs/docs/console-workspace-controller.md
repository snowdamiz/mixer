# Console workspace controller

`console/src/state/workspace-controller.ts` connects the read-only workspace client
to the controlled directory state. It keeps one current page per list and one
active request slot per list, with no response cache, pagination history, stored
token, browser API, framework dependency or automatic selection. The client owns
transport and session-token resolution.

## Public contract

`createWorkspaceController()` performs no request and begins with organizations
`unavailable` and projects `unselected`. It returns a frozen `WorkspaceController`:

```ts
type WorkspaceSession =
  | { readonly kind: "unauthenticated" }
  | { readonly kind: "unavailable" }
  | { readonly kind: "ready"; readonly client: WorkspaceClient };

interface WorkspaceController {
  getState(): WorkspaceDirectoryState;
  subscribe(listener: (state: WorkspaceDirectoryState) => void): () => void;
  setSession(session: WorkspaceSession): void;
  selectOrganization(id: string): void;
  selectProject(selection: { organizationId: string; projectId: string }): void;
  nextOrganizations(cursor: string): void;
  nextProjects(page: { organizationId: string; cursor: string }): void;
  retryOrganizations(): void;
  retryProjects(organizationId: string): void;
  dispose(): void;
}
```

Every `setSession` call invalidates previous requests, even when the same client
object is reused. It synchronously clears both pages and both selections, aborts
old requests, and starts the first organization page only for `ready`. The
controller passes an empty page object for a first page, preserving the API's
default page size. It captures the client reference rather than retaining the
caller's session wrapper.

Organization selection must exactly match a row in the currently visible
organization page. It clears the previous project page/selection and requests
that organization's first project page. Selecting the current organization again
is inert; failures are retried through the explicit retry action. A project
selection must carry the current organization's exact ID and a project ID in its
current page. Whitespace, punctuation and Unicode IDs are preserved without
trimming or normalization. Rows convey visibility and selection, never release
authority.

Pagination accepts only the exact non-null cursor currently offered by its list;
project pagination also requires the current organization. Organization page
replacement synchronously clears all rows/selections. Project page replacement
synchronously clears its rows and project selection. Responses replace the page;
they are never merged. Missing/stale callbacks and retries while loading make no
request. A retry is allowed only for an `error` or transport `unavailable` list,
and reuses that list's last attempted canonical page parameters. Changing the
organization or session discards the former project attempt.

## Response identity and failures

Each request captures a unique generation, session generation, client and
`AbortController`. Completion must still match the current request object and
generation, current session and, for projects, the current visible organization.
Identity is checked before and after strict response parsing. An aborted client
that ignores cancellation cannot restore rows, change selections or expire a
replacement session. Synchronous client throws and promise rejections are handled
within the same request boundary.

The existing `parseWorkspaceOrganizations` and `parseWorkspaceProjects` validators
copy and deeply freeze every accepted page. `getState()` returns an immutable
snapshot whose nested list states are frozen too. Mutating a client's original
response after completion cannot change a saved snapshot.

Only the client's closed `WorkspaceClientError` class supplies these mappings:

| Client category | Controller outcome |
| --- | --- |
| `unauthenticated` (401) | Invalidate the entire session, abort requests, clear all data and publish organizations `unauthenticated` / projects `unselected` |
| `permission_denied` (403) | Matching list `error` / `permission_denied` |
| `not_found` (404) | Matching list `error` / `not_found` |
| `unavailable` | Matching list `unavailable` |
| `invalid_response`, `invalid_request`, current `aborted`, parser failures, unknown errors | Matching list `error` / `request_failed` |

Error messages, URLs, bodies and arbitrary error-object properties never enter
the state. An old failure cannot affect a newer request or session.

## Subscription and disposal

`subscribe` immediately delivers the current snapshot and returns an idempotent
unsubscribe function. Separate registrations of the same function are independent.
Each live registration receives a revision at most once. Notifications are
synchronous; if an observer changes state, the new revision supersedes the old
notification round, so later observers receive the current snapshot. Removed
observers are skipped; observers added during notification receive the current
revision. Observer throws and returned promise rejections are isolated.

Request slots and state are updated before abort handlers or observers run. A
session change or disposal during notification can therefore prevent the newly
invalidated request from starting. `dispose()` aborts active work, drops the
client/attempts/listeners, and clears the state to `unavailable` / `unselected`.
It sends no final notification to removed listeners. All subsequent actions,
subscriptions and late completions are inert; `getState()` remains readable.

## Evidence and limitations

Run from the repository root:

```sh
python3 verification/console-workspace-controller/run.py
```

The runner records 27 focused tests against TypeScript-emitted controller code,
console typechecking, tool versions, the source revision and a hash-bound input
snapshot, including all console source files used by typechecking. Controlled deferred promises exercise stale successes/failures,
session/logout/scope replacement, canonical pagination/retries, arbitrary IDs,
response mutation, errors, notifications, reentrancy and cleanup. Test-generated
JavaScript is removed after success and compiler failure.

This is host controller evidence. App/session/login composition, actual browser
interaction and accessibility runtime, provider and deployed tenant isolation,
native simulator/emulator runtime, physical phones, immutable FieldLog release
dogfooding and GA acceptance remain pending. Computer use, capture and native
runtime tests remain paused; this lane starts none of those processes. No new
dependency, production publication or GA qualification is implied. The frozen
hosted lanes are neither imported nor executed by this runner.
