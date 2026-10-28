# KeyOwner lifecycle next-slice contract

Read contract.md for the selected correction and ownership limits, and
prospective-tests.json for exact prospective checks. This source-only packet
binds twelve current source files and nine retained evidence files. All eight
comparisons of the four relevant identity modules against dispatcher candidates
4 and 6 match. The accepted dispatcher freeze hash is verified.

The observed failure denies identity access but leaves stale graceful-shutdown
registry state. Proposed product work is limited to shared exit trapping and
expected-table/ETS-owner guarded cleanup, with ordinary supervisor ordering as a
required invariant. Forced-kill dead pointers remain an explicitly fail-closed
crash limitation until restart.

Run `python3 -B verification/console-key-owner-lifecycle-contract/verify_packet.py
--require-freeze` from the repository to audit this packet and bound current
source hashes without replaying runtime. audit.json records the prefreeze audit;
freeze.json seals every packet file except itself. No product implementation,
Elixir compilation, BEAM/Mix/DB/network fixture, native/capture/UI, global process
inventory, commit, or push was performed. Runtime behavior and final acceptance
remain pending. Root owns canonical metadata and delivery.
