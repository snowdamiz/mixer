# Console cookie workspace transport

The console has a browser adapter for the proposed same-origin session boundary.
`createCookieWorkspaceClient()` implements the existing `WorkspaceClient`
interface, so it can feed the reviewed workspace controller and branded route.
It does not authenticate a browser, install a session in `App`, or add server
routes. The production entry remains unavailable until those pieces are joined.

The adapter permits only two fixed read routes: `/console-api/v1/orgs` and
`/console-api/v1/projects`. IDs remain exact query values, encoded once; they
cannot become paths or destinations. Fetch uses `credentials: "same-origin"`,
`redirect: "error"`, `cache: "no-store"` and `referrerPolicy: "no-referrer"`.
Only the JSON accept header is supplied. There is no bearer, cookie, arbitrary
header or origin option, and unknown configuration fields are rejected.

The existing bearer client and new cookie adapter now share one bounded reader.
The original public error class is re-exported, preserving existing `instanceof`
checks in the controller. The bearer client still resolves a fresh token for
each request, uses its validated configured origin, and omits browser cookies.
The shared reader retains the 256-KiB response limit, 4,096-read bound, strict
UTF-8/JSON and domain decoding, fixed public errors, and deadline covering
session resolution, fetch and body consumption. Abort, timeout and late responses
do not publish stale data; cancellation does not wait on a stalled body cleanup.

The logo, colors and fonts remain identical to the website. A separate small
responsive adjustment places the logo above the three navigation links on mobile;
the workspace column can shrink and wrap. This prevents the new third route from
competing with the logo for a single narrow row. Browser visual verification of
that adjustment remains paused. Existing route/controller checks remain in the
complete suite.

## Evidence

All **112 console host tests**, type checking and production build pass with zero
skips in [the final producer receipt](../verification/console-cookie-workspace-transport/attempts/20261025T151110812242Z/receipt.json).
This includes twelve new cookie-adapter methods, the existing bearer checks, and
the real Solid reactive binding tests. Counts overlap; the four nested binding
methods are not another four top-level console tests.

The new host tests exercise hostile IDs, closed configuration, scoped responses,
fixed error categories, byte/read bounds, noncooperative cancellation and late
bodies, session changes, and a temporary real HTTP server. That server checks
request routes and safe response handling. Node does not reproduce browser cookie
storage or enforcement, and the server is a synthetic fixture, not Phoenix login.
The runner records commands, tool versions, input hashes, outputs and build hashes.
Owned compilation directories and HTTP connections are cleaned after tests.

[Independent review](browser-auth-prerequisite-review.md) passes fifteen additional
transport methods and fifteen protocol/configuration methods, with no findings.
Those counts are separate from the producer suites; CSS is outside that review. Browser cookie policy,
ingress behavior, backend session routes, provider exchange, durable session
activation/logout, actual login UX, customer and GA acceptance remain pending.
No browser, screen capture, native runtime or physical phone was used.

See the [identity flow contract](console-identity-flow-contract.md) and
[durable session contract](hosted-browser-session-storage-contract.md) for the
required server boundary and remaining implementation.
