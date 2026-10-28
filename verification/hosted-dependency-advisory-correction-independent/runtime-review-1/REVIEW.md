# Independent terminal lock-resolution review

Recommend root apply the two selected dependency versions, the actual generated
lock and corresponding THIRD_PARTY inventory update, then run ordinary remote CI.
No terminal finding blocks that next step. This is successful lock generation;
integration, product behavior, remote CI, HTTP/2 wire checks and GA remain pending.

The exact released v4 controller and plan match the previously reviewed hashes.
The retained attempt `fe41774456c8435e841b30f9b48cb7ec` completed in 3.861683 seconds,
with five exact commands returning zero, empty stderr and no recorded error.
Version output reports Elixir/Mix 1.20.4, OTP 29 / erts-17.1. Selected installed
Hex 2.5.1 and tool/source/archive pins remain intact.

The retained Mix-generated lock SHA256 is
`1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837`.
Independent raw-line comparison finds exactly Bandit 1.13.1 → 1.14.0 and JOSE
1.11.12 → 1.11.13 changed; all nineteen other complete entries are byte identical.
The target build tools and dependency requirements are unchanged. The generated
outer checksums match the hash-pinned official Hex metadata retained by the prior
advisory investigation. No fresh metadata request was made. All twenty-one entry
records and nineteen before/after hashes agree with the emitted lock inventory.
The source-bound successful offline check requires unchanged resolved-lock bytes.

Each owned leader (97646, 97714, 97764, 97809, 97881) has a zero-status WNOWAIT exit
witness, no-signal reap path and confirmed group closure in sequential command
records. No nonzero cleanup signal or EPERM is recorded. The last-32-call trace
ends with wait then group signal-0 observations for the final command. Scratch is
recorded removed and is absent on an independent read-only filesystem check.
This review did not repeat any process query, cleanup or signal operation.

The recorded environment exactly expands the pinned private Mix/Hex/deps/build,
TMPDIR, DNS/file inetrc and BEAM-home paths, with shell HOME unchanged. TLS,
registry signature and repository-origin bypasses remain disabled. The final
HEX_OFFLINE override and per-command inetrc/project checks are bound to the frozen
source; no independent child-environment or network transcript was collected.
No cancellation was handled/pending through the finite cutoff. Output/source
hashing precedes it and all recorded stages finish within the reserved limits.

Fresh hashes verify thirteen exact ordinary execution files, their twelve
receipt-bound retained-output hashes, controller/plan/seals and selected
canonical/source/tool/archive/advisory pins. The generated files remain separate
from canonical sources. deps.get stdout also records staging rebar3 in private
scratch mix-home; no compile, product test or application command was selected.

Only bounded Python file/hash/receipt checks ran during this independent review;
the controller was not imported or replayed. These successful normal-exit records
do not prove cancellation/EPERM fault handling or the separate Swift failure's
cause. Later product and CI evidence must establish upgrade acceptance.
