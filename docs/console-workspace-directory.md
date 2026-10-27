# Console workspace directory

`console/src/components/WorkspaceDirectory.tsx` is the controlled SolidJS organization/project directory. It uses the console's existing website-derived palette, typography, card treatment, focus styling and system icons. The existing shell owns the unchanged Flick logo and lowercase Mixer wordmark. No additional brand asset, font or dependency is introduced.

## API boundary

`console/src/domain/workspace-directory.ts` validates the coordinated customer workspace responses:

```text
GET /v3/orgs?limit=<1..100>&cursor=<opaque>
{organizations: [{id, display_name, organization_roles}], next_cursor}

GET /v3/projects?organization_id=<percent-encoded full ID>&limit=<1..100>&cursor=<opaque>
{projects: [{organization_id, id, display_name, roles}], next_cursor}
```

The caller owns requests and ordinary customer authorization: human bearer token with `mixer.workspace.read`. The default page size is 50. Project selection uses the query parameter so valid identifiers such as `.`, `..`, `/`, `:` and Unicode are not interpreted as route segments. This component does not construct requests or attach credentials.

`parseWorkspaceOrganizations(input)` and `parseWorkspaceProjects(input, organizationId)` reject unknown/missing fields, duplicate rows, more than 100 rows, malformed text, unsupported roles and mismatched organization ancestry. They copy and deeply freeze the validated response. IDs preserve the complete `Scope.identifier?` alphabet, use 1–128 UTF-8 bytes and reject C0/C1/DEL controls, invalid Unicode and the exact wildcard `*`. Nullable stored display names use 1–256 printable UTF-8 bytes and permit `*`. Neither IDs nor names are trimmed or normalized. Names fall back to the exact ID only when `display_name` is null. Labels are rendered as escaped text inside bidirectional isolation elements.

Both role arrays are lexicographically sorted, unique and limited to `administrator`, `billing_manager`, `developer`, `owner`, `release_manager`, and `viewer`. Project roles must be nonempty. `organization_roles: []` is legitimate for access granted through a project; the UI labels this as “Project access” and never invents an organization administrator role. Organization-only access may produce an empty project page. A directory row grants no artifact, build, release or administrative authority.

`next_cursor` is null or an unpadded base64url string of 1–1400 bytes. An empty page must have a null cursor. It remains opaque to the console. The component returns the exact validated value to the page callback and never presents a page count as a total.

## Controlled view state

`WorkspaceDirectoryProps` extends `WorkspaceDirectoryState`:

| Field | Meaning |
| --- | --- |
| `organizations` | `loading`, `unauthenticated`, `unavailable`, `error` or `ready` with raw `input` |
| `projects` | `unselected`, or the same load states with the exact `organizationId` |
| `selectedOrganizationId` | Optional controlled selection within the current organization page |
| `selectedProjectId` | Optional controlled selection within the current project page |
| `canReturnToFirstOrganizations` | Optional boolean from the caller's nonfirst organization-page attempt |
| `canReturnToFirstProjects` | Optional boolean from the caller's nonfirst project-page attempt in the current organization |

`error.reason` is `permission_denied`, `not_found` or `request_failed`. Error messages are fixed customer-facing copy and never echo HTTP details. `resolveWorkspaceDirectory` validates every ready page and resolves selection only against its copied current rows. Missing/stale organization selection hides all project data. A project response from another organization fails closed even when the project ID matches. A malformed page hides every row from that page; it cannot leave a prior project highlighted.

The caller supplies these callbacks:

```ts
onSelectOrganization(organizationId: string): void
onSelectProject({ organizationId, projectId }): void
onNextOrganizations?(cursor: string): void
onNextProjects?({ organizationId, cursor }): void
onFirstOrganizations?(): void
onFirstProjects?(organizationId: string): void
onRetryOrganizations?(): void
onRetryProjects?(organizationId: string): void
```

Selecting another organization, paging and replacing authentication state are caller-owned operations. Update the selected IDs and corresponding scoped project state together; clear a project selection when its page or organization changes. Next controls appear only for an available validated cursor and are disabled without their callback. First controls appear only for an explicitly true navigation flag with a valid current list state; a project First control also requires the current organization scope. They remain reachable after a later-page error or unavailability, and are disabled while their list is loading or their callback is absent. Signed-out, invalid or stale scoped state hides them. The controller supplies the navigation flags and makes a fresh cursor-free request; no earlier response is cached and no cursor is decoded. The current page is replaced rather than merged by this component.

The view supplies semantic headings and lists, native keyboard-operable buttons, `aria-pressed` selection, focus outlines, polite selected-project announcements and distinct loading/authentication/unavailable/error/empty messages. An empty organization list and an accessible organization with no accessible projects are different states. There are no unimplemented creation/import actions or fabricated production rows.

## Verification and limits

From `console/`:

```sh
node --test tests/workspace-directory*.test.mjs
npm run typecheck
npm run build
node --test tests/brand-parity.test.mjs
```

The 21 focused tests exercise byte/Unicode boundaries, closed response/role shape, opaque cursor bounds, immutable copies, organization/project scope separation, selection changes and all load states, plus actual Vite-compiled Solid server rendering for escaped labels, semantic/accessibility markup, pagination controls and stale-data suppression. The parity test loads only the standalone ordinary `authorization/scope.ex` helper with `elixir -r` and compares 85 identifier vectors, including control/noncharacter ranges and invalid surrogate bytes. It does not compile or start the hosted application. Test fixtures exist only in test code. Temporary SSR output is removed after each test process.

Evidence is in `verification/console-workspace-directory/`. The initial focused run contained three test-fixture default-argument mistakes; `undefined` test inputs were replaced by factory defaults rather than reaching the boundary. The corrected fixture construction and successful rerun are recorded separately. No production validator correction was needed for those failures.

First-page navigation adds strict availability and compiled rendering cases,
including failed later pages and disabled controls during loading. Its separate
source and execution record is `verification/console-workflow-next-slice-review/`.

This lane delivers the reusable component/data boundary. The root lane owns the actual API client, session/authentication and `App.tsx` composition; a standalone component test is not connected customer workflow evidence. The initial production build predates that composition and may tree-shake the unreferenced component; the focused SSR test independently compiles and renders it. Source parity confirms the shared website brand tokens and exact logo bytes, not visual layout acceptance. Browser interaction, screen capture and native runtime tests were not run because they are paused. Live identity/provider behavior, deployed API isolation, Cloudflare hosting, operational qualification, physical devices and G22 remain pending; no GA gate is passed by these host results.
