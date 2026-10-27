# Proposed console directory first-page return

The current directory replaces its only organization/project page when the customer clicks Next. It renders no return-to-first or previous control. The controller has no reset action, and choosing the current organization again is inert. A customer on a later organization page cannot select an earlier organization without resetting the whole session; a customer on a later project page cannot return to an earlier project through the directory.

Source: console/src/components/WorkspaceDirectory.tsx lines 111-114 and 146-152; console/src/state/workspace-controller.ts lines 165-183, 218-221 and 230-238. Existing docs explicitly retain no controller pagination history.

Propose controller-owned firstOrganizations() and scoped firstProjects(organizationId) actions, wired through the shared Solid binding and WorkspacePage to native button controls. A first-page action sends the existing immutable empty page request through the same ordinary WorkspaceClient and request-generation/abort boundary, clears dependent selection synchronously, and discards previous rows. Expose only bounded navigation availability; retain no response cache or cursor history. Cursor values stay opaque. A return action must also work after a later-page error, because retry alone preserves a failed/expired cursor.

The ordinary API contract already specifies cursor absence for the first page and default limit 50. No API path, permission, response envelope, transport, identity/provider, backend or dependency change is required. The W14 section 17 requirement is complete customer workflows using ordinary authorization and accessible controls.

Focused executable verification should cover later-to-first success, later-page errors, exact project organization, current loading double actions, immediate stale selection removal, session replacement/disposal and late old responses. Existing tests use tsc/Vite internally; no compiler has been started while the Rust lane owns compiler execution. Source/test changes await root assignment.

The production App still has no admitted workspace session by default, and builds/releases remain unavailable. This slice improves the existing injectable customer workspace flow only; it cannot qualify real login, deployed workflow, browser accessibility, Cloudflare operation or any GA gate. UI/native/capture/device checks remain paused and pending.
