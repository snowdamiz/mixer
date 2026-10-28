# Resolution v3 source correction

This unexecuted successor addresses the independently reviewed R01/R02 findings
and root's control-byte binding correction. Both earlier sealed preparations
remain unchanged; v2 has no attempt directory.

The five commands, selected local tools, two target versions, nineteen unchanged
lock entries, signed-registry/TLS checks and 40/46/52/55-second cutoffs remain.
Root must pass the exact selected plan SHA with `--plan-sha256`; the concrete
release argv is recorded in `preparation-receipt-v3.json`.

The controller verifies the one in-memory plan byte string before parsing it.
Preparation bytes are then verified against the hash from that pinned plan
before parsing. Candidate metadata and copied project/lock/inetrc bytes are
similarly bound before use. A separate later file hash is not used to authorize
previously parsed commands.

The exact private inetrc is `{lookup,[dns,file]}.` plus LF. It is pinned in the
plan, copied from verified bytes and rechecked before every command.
`ERL_INETRC` selects it for all five commands. Shell HOME stays unchanged;
BEAM receives a private scratch `-home`. The root-selected independent review
and installed OTP source hashes support this choice; no DNS/network/process
probe was performed and no native fallback is selected.

Successful output/source hashing and scratch cleanup must finish before the
one-way signal cutoff. The controller permanently blocks SIGINT/SIGTERM,
establishes the cutoff timestamp, then snapshots pending signals while protected
and combines them with handled cancellation. Any observed cancellation through
that boundary prevents success. Snapshot arrivals just after the timestamp may
conservatively fail; later blocked signals are outside the guaranteed receipt
scope. No output/source hash follows that cutoff. Incomplete hashing cannot
produce a successful cutoff.

Only static AST, ordering and byte-custody checks have passed. The controller
has not been imported/executed; no actual lock exists. The sealed source is
ready for root's focused review. Remote Phoenix CI and the two HTTP/2 wire
qualifications remain separate and pending.
