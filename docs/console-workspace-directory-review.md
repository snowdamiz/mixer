# Workspace directory read-only review

The source and host review found one actionable accessibility defect. The existing tests passed, so the missing case required a separate SSR reproduction. No product source was edited during this initial review.

## Finding: valid whitespace identifiers produce unnamed selection buttons (P2)

The identifier contract permits whitespace-only identifiers, including a single ASCII space. With `display_name: null`, `workspaceDisplayName` correctly preserves the ID, but the organization/project buttons render that whitespace as their only text alongside an `aria-hidden` SVG. The result is a valid, focusable selection control with no accessible name and no readable visible identity. This affects a valid organization ID `" "` and valid project ID `"  "`; selection can even be active while its announcement contains no project name.

The initial source locations are `console/src/domain/workspace-directory.ts:137`, `console/src/components/WorkspaceDirectory.tsx:96`, `console/src/components/WorkspaceDirectory.tsx:130` and `console/src/components/WorkspaceDirectory.tsx:158`. The initial source snapshots preserve these exact locations after correction.

`verification/console-workspace-directory-review/initial-review/whitespace-identities.html` contains the actual Vite-compiled Solid SSR reproduction. Its two row buttons both have whitespace-normalized names `""`, as recorded in `ssr-probe.json`. The recommended correction is descriptive organization/project text with a visible quoted/escaped identity marker for an unnamed whitespace-only ID. Preserve the exact stored ID in the response snapshot, selection and callbacks; preserve every non-null stored display name without trimming, normalization or replacement. Add domain and SSR coverage for ASCII and Unicode whitespace identifiers, distinct counts of spaces, and ordinary/non-null names.

The root lane authorized a correction after recording the initial review. Correction evidence remains separate from the preserved initial source and SSR output.

## Other observed behavior

- **Branding:** The live brand parity test confirms the website's ordered root token declarations and exact Flick/favicon bytes. Current source uses the same lowercase Mixer wordmark, orange accent, warm paper/cream surfaces, system sans/mono typography, quiet borders, card radii and outline icon style. Existing website desktop and console 320px images were inspected offline as historical style references; they are not new renders of this component.
- **Mobile CSS:** The workspace columns collapse at 900px. At 720px the directory uses smaller padding and stacked pagination controls. Names/IDs wrap, grid/flex children permit shrinking, and role pills wrap. These rules are coherent in source, but actual 320px/375px layout, zoom, focus visibility and touch behavior remain unverified under the current runtime pause.
- **Accessibility markup:** Headings form a page/section/message hierarchy; choices are native buttons with `aria-pressed`; decorative SVG is hidden from accessibility; roles remain separate readable lists; retry controls are native buttons; selected-project text is a polite atomic status. Actual keyboard and screen-reader operation remains pending. The small retry target is a possible touch-comfort refinement, not a demonstrated conformance failure in this review.
- **State and scope:** Fresh domain/SSR tests confirm malformed data and stale organization selections suppress project rows, mismatched project ancestry fails closed, current-page selection does not invent missing records, organization-only access has an honest empty-project state, and project grants do not become organization roles. Pagination exposes only validated opaque cursors and no invented totals or creation/import actions.
- **Composition:** At the reviewed snapshot, `App.tsx` contains Builds/Releases routes and does not import or route to `WorkspaceDirectory`. The reusable component is tested directly; API/session composition and connected customer workflow evidence belong to the root lane and remain pending.

## Verification boundary

The fresh focused host run passed 22 tests: 21 workspace tests plus the website brand parity test. `npm run typecheck` passed. The standalone SSR probe reproduced the two unnamed buttons and separately confirmed stale-selection suppression. The 85-vector standalone Elixir Scope parity test loaded only the ordinary `authorization/scope.ex` helper; no hosted application or frozen transport/catalog lane was started or inspected.

Exact commands, outputs, tool versions, source hashes, historical image hashes and cleanup are recorded in `verification/console-workspace-directory-review/initial-review/receipt.json`. An initial attempt to read a nonexistent old screenshot receipt was preserved as discovery failure evidence; the actual historical image and website receipt were then inspected directly.

No browser, computer use, new capture, native runtime, physical device, deployment or production publication was performed. No GA gate is passed by this review. Browser visual/interaction acceptance, live identity/API behavior, hosted operation and accountable reviewer acceptance remain pending.

## Authorized correction

The confirmed finding is corrected in host/SSR scope. Unnamed whitespace identifiers now receive a visible `Organization ID "\u0020"` or `Project ID "\u0020\u0020"` annotation. The same identity appears in the selected organization header and selected project status. Distinct counts/types of spaces produce distinct quoted Unicode escapes. Named rows retain their exact non-null name text and receive a separate escaped identity marker when their ID is whitespace-only. Ordinary names and identifiers keep their existing presentation.

`workspaceDisplayName` still returns the exact stored name or, only for null names, the exact identifier. The added `workspaceIdentifierMarker` helper is presentation-only. It never becomes a selected ID, callback argument or request ID. Selection snapshots retain their original strings; the component callbacks still pass `organization.id`, `project.organization_id` and `project.id` directly.

At the root lane's request, the existing identifier predicate is now exported as `isWorkspaceIdentifier` for the API client. Its acceptance semantics are unchanged; the same 85-vector parity check now verifies both the exported predicate and response boundary against standalone Elixir `Scope.identifier?`.

The corrected focused run passes 25 checks: 24 workspace tests plus the brand parity test. Three new tests cover exact identity/selection preservation, readable ASCII/Unicode whitespace identities in compiled SSR, and unchanged non-null names with a separate marker. Strict TypeScript also passes. The correction SSR probe records two nonempty descriptive button names and unchanged exact input IDs. Its initial test run exposed two over-specific SSR assertions that required `<bdi>` without Solid hydration attributes; those assertions now allow attributes while still verifying exact content, and the initial failure output is retained.

Correction commands, source hashes, old/new source diff, output and cleanup are in `verification/console-workspace-directory-review/correction/receipt.json`. The initial review receipt and source snapshot were retained unchanged. All original browser/native/hosted/GA limitations still apply. This is a host correction, not screen-reader or touch-device acceptance.
