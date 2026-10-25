# Identity session prerequisite for workspace discovery

`Session.prepare_identity!/2` reuses the existing profile, principal, family and
credential lock sequence with empty tenant scope. It returns linkage only; it
creates no artifact Context and grants no authority. The ordinary
`Session.prepare!/2` still takes those identity locks before organization and
project heads. Both paths clear inherited directory mode.

`Context` includes `mixer.authz.directory_mode` in its complete connection binding.
Changing that mode invalidates an ordinary artifact transaction, even if the
caller restores the old value after a failed checkpoint; pending writes roll back.

The producer's 20 PostgreSQL transaction tests pass. Independent review replays
those 20 and adds six controls for real identity row locks, absence of tenant-head
locks, credential revocation in both orders, inherited settings, failure latching
and inability to authorize effects with linkage or a stale Context. See
`verification/hosted-workspace-identity-session/run-1` and
`docs/hosted-workspace-identity-session-review.md`. The counts overlap, and both
owned clusters/scratch were cleaned. This prerequisite does not by itself qualify
the workspace directory, HTTP API, production lifecycle writers or GA gates.
