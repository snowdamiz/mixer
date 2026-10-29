# Controlled editor adapter declarations

Root authorized this scope after the live-roster packet was sealed. Both earlier
packets remain unchanged. This packet supersedes their pending declaration-gap
observation for closure B.

Only closure B's controlled `InputConnection` declarations, five request or result
types, and the live roster's five explicit substitute entries change. Added
methods return inert refusal values. Later-API declarations use defaults so the
production adapter's earlier-API base can compile against this combined host
interface. Existing instrumented `BaseInputConnection` behavior stays unchanged.

These declarations provide host compilation contracts. They do not prove Android
platform signatures, device behavior, input-method behavior, API-floor safety,
native acceptance, or release readiness. Compilation and host assertions remain
pending fresh ordinary CI. No local compiler or subject test runs here.
