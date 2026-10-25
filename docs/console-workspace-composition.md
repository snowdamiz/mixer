# Console workspace composition

The actual Solid Router application now exposes `/workspace` from the existing
website-branded navigation. It renders the organization/project directory using
one application-owned controller. Switching between workspace, builds and releases
does not replace that owner. Builds/releases retain their honest unavailable
states until their own customer workflows are connected. Header labels come from
the actual matched route, including trailing slashes, instead of separately
interpreting the URL. The website's logo, palette and typography remain unchanged.

`App` accepts an optional typed `workspaceSession` capability. `ready` contains a
`WorkspaceClient`; `unauthenticated` and `unavailable` contain no credentials.
Every new immutable session object denotes a new session epoch, even if it
reuses the same client. The production entry currently supplies no adapter and
therefore renders unavailable. There is no token-entry field, global credential
object, browser storage or production login implied by this composition. The
proposed same-origin server-session adapter is separately documented in
`docs/console-identity-flow-contract.md` and remains unimplemented.

The controller retrieves organizations, validates and copies each page, selects
only exact currently visible IDs, and retrieves projects for that organization.
Pagination replaces the current page and clears dependent selections. Retry
preserves the last attempted page cursor. New sessions, organization changes,
pagination and disposal invalidate obsolete request generations and abort their
signals. A response from an uncooperative client cannot restore obsolete rows.
Authentication failure clears the entire workspace. Other errors use fixed safe
messages and never render transport/provider text.

The Solid binding checks the live session against the admitted session on every
public state read and action. This is necessary because a pure reactive consumer
can run before a session-change effect. A mismatched session exposes only a
row-free loading, signed-out or unavailable state; actions are inert until the
replacement is admitted. The UI receives six selection/pagination/retry actions,
without access to session replacement or lifetime methods. Disposing the app
owner clears retained data and cancels work. Server rendering never executes
client requests or serializes the adapter.

## Evidence and limitations

`verification/console-workspace-composition/run.py` records source hashes, exact
commands/tool versions, outputs, static build hashes and owned-cache cleanup for
console typecheck, the entire host test suite and production build. The accepted
root run is `attempts/20261025T144613993605Z/receipt.json`. The binding tests use the
actual Solid client reactive runtime in a separate Node process, plus the actual
workspace API client and a temporary loopback HTTP server. They exercise exact
Unicode/query IDs, account replacement, stale failures, synchronous pure-consumer
reads/actions, child-owner disposal and app cleanup. SSR tests compile the actual
route tree, shell and page and check active navigation, route labels, safe empty
states and zero session-adapter calls. Independent review is recorded separately.

Initial root testing preserved a harness failure: the child process inherited
Node's parent test context and ran no tests. The wrapper now explicitly starts an
independent test context and requires all four child tests with zero failures.
Independent review reproduced the initial effect-order stale-state window and
trailing-slash header mismatch; both have permanent regression coverage. Earlier
attempts and source snapshots remain retained, rather than rewritten as passes.

This is host-level application composition. No browser was opened, no screenshot
was taken, and no simulator/emulator/physical-device work was performed. Visual
layout, keyboard/screen-reader interaction, live login/provider sessions, Cloudflare
ingress, lifecycle writers and customer/FieldLog/GA qualification remain pending.
The product plan is unchanged.
