# Selected-contract behavioral preparation

Status: **prepared source and expectations only; every behavior check pending**.
No corrected candidate, producer packet or operation proposal was accessed. No
Rust compiler, analyzer, oracle or fixture runner was executed. The original
39-member pre-access baseline and its document remain byte-for-byte unchanged.

The root selection is pinned to SHA-256
`199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c`.
It selects leaf425, W24, B471, G112, T42, finish47 and outer F42, with setup534
unchanged. The public counter is `534*S_paid + 47*F_paid + 425*N_B`.
The 32 controls in `selected-cases.json` preserve the frozen behavioral IDs and
expectations, then bind them to this separate amendment. Their status is pending.
These values are expected assertions, not measured output or passing tests.

Exact expected public debits include:

| Main admission / record history | Public debit |
| --- | ---: |
| Main setup reservation fails | 0 |
| Setup paid, finish reservation fails | 534 |
| Setup and finish paid, guard reservation fails before candidate initialization | 581 |
| Setup and finish paid, no charged record | 581 |
| Setup and finish paid, one B471 charge; decode fails before a leaf reply | 1006 |
| Setup and finish paid, two B471 charges; second leaf skipped after a latch | 1431 |

Each successful B471 retains425 even after decode failure or a skipped leaf.
No charged record is inferred from leaf-call count. Failed reservations add
nothing. An actual input error zeros all eleven fixture extent fields while
preserving this paid debit and the actual framing error. An outer output,
allocation or report failure returns no aggregate.

Outer F42 is base29 plus dedicated F05 early-error13. Every returned input Err
uses F05, including when finish47 was paid. That paid finish remains unused
and unrefunded. Input Ok finalizes using finish47; F05 stays unused. The source
review must check this routing rather than assuming available aggregate credit,
adding a paid flag or reallocating an inactive branch's reservation. Setup,
finish and guard failures all precede candidate initialization.

Private underfunding checks cover **every remaining value0 through424** before
the first normal reply and after a committed reply. Valid and malformed next
records must both return actual Refused/Steps, unchanged prior state/coordinate,
debit0, unchanged budget and unchanged complete arena/candidate. Funds425 and426
are exact/one-above positive boundaries. Absent prior state retains its earlier
poison/debit0 priority. The separately prepaid G112 funds the complete guard
and can be used at most once; it is not another425-credit source.

`private_controls.rs` prepares independent direct controls against only private
names already admitted in the original immutable review. It covers the exact
R1 fault, poisoned scheduling/finalization, absent backing, all425 underfunded
thresholds, exact funding, and final checked-cell refusal. It has not compiled
and is not yet attached to any candidate. The future receipt must map each
private name mechanically to the exact admitted source and preserve that source
as an unchanged prefix. A changed API or behavior requires explicit review;
do not alter assertions to obtain a pass.

`expected_observation.rs` prepares normalized public assertions for debit,
error suppression and false acceptance flags. An actual safe-File adapter,
immutable fixture bytes, and the remaining bounded fault seams must be acquired
or authored after exact-source admission. This supplement does not claim that
the prepared files implement all32 controls or qualify their behavior.

`owned_runner.py` is unexecuted future runner source. Each invocation requires
an explicitly supplied exact command, cwd, output directory and deadline. It
starts a dedicated owned session, writes stdout/stderr directly to durable files,
preserves partial bytes, terminates the owned group on error or leftover members,
reaps the direct child and checks that the owned group is gone before reporting
cleanup. It never enumerates unrelated processes. A timeout, cleanup failure or
incomplete method remains unqualified. Scratch release is forbidden until cleanup
is confirmed. Its own behavior still needs bounded qualification after root
authorizes execution; source preparation is not runner qualification.

The next step requires root's exact final-source handoff. Retain the native/UI/
capture/simulator/emulator/device pause, the historical64 retry prohibition and
all fixture-only authority limits. No implementation acceptance, accounting
acceptance, semantic authority, gate, product publication or commit is promoted.
