# Stripe resource harness v2 independent review

The sealed v2 candidate requires changes before private runtime selection. This
review independently checked the source, four R14 phase contracts, all 34 R18
boundary paths, immutable bindings, and host control method. It grants no Linux,
native, device, complete matrix, production, or GA acceptance.

The reviewed seal SHA-256 is
`35813b1f5194eeea3317f3e926ebde0f8a6a589d6f5724c69e27fd4c58a424b3`;
the harness digest is
`03f3564336af88586577803429c999c3eb213c4c1dbca8c8416d0b6451161e5c`;
the fault enum digest is
`3fea63bd9a41a3e91b8eb7922f87d52711c7d61b93c524d12c7bfaf6789b23e2`.
Both root amendments are bound in the review receipt. The live read-only sealed
verifier passed with 104 sealed files. The immutable v1 checkpoint remains
unchanged: 98 original bindings and 99 regular archive members, including its
seal. Git revision `cf52825dc552660c684ff60da530646b6c07684a` is context only;
the file hashes identify this uncommitted candidate.

1. **F1, P1: stop runtime scheduling after incomplete cleanup.**
   [run.py:184](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v2/run.py:184)
   unconditionally proceeds from R14 to R18. An R14 result can report
   `cleanup.complete=false` at lines 139–148 after both cleanup attempts fail,
   but the loop never inspects that result before calling `execute_row("R18")`.
   The new backend also carries no prior-session cleanup barrier. This can
   create another role while the previous role, cgroup, or holder remains
   unresolved, violating the selected one-role limit and independent cleanup
   requirement. The host reproduction executes the actual `main()` scheduler
   with row execution and writes mocked: it observes calls `R14, R18` after
   incomplete R14 cleanup. It creates no runtime resources. Retain the failed
   receipt and refuse subsequent runtime rows until complete disposal is proved.

2. **F2, P1: enumerate nonleader thread holders before accepting teardown.**
   [linux_backend.py:142](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-webhook-linux-resource-harness/v2/linux_backend.py:142)
   iterates top-level `/proc` entries, then examines only each process leader's
   `ns` and `fd` directories at lines 147–169. It never enumerates
   `/proc/<PID>/task/<TID>`. A nonleader thread can remain in the owned network
   namespace while its leader occupies a different namespace; the scanner can
   report `namespaceHolders=0` and the final numeric cleanup validator accepts
   it. Linux documents that nonleader `/proc/<TID>` entries are hidden from
   directory iteration and that `setns` changes the calling thread's namespace.
   See [proc_pid_task(5)](https://man7.org/linux/man-pages/man5/proc_pid_task.5.html)
   and [setns(2)](https://man7.org/linux/man-pages/man2/setns.2.html).
   The actual scanner reproduces the false zero with mocked PID 123 and TID 124
   holding selected netns inode 777; no live `/proc` is queried. Inventory every
   relevant TID's namespace and descriptor metadata within the original
   deadline, preserve stable identity checks, and refuse incomplete inventories.
   Unrelated holders must remain unsignaled.

The source implements the selected phase obligations as follows. These are
source observations, with Linux behavior still pending.

| R14 phase | Reviewed source obligation |
| --- | --- |
| `idle` | Listener info precedes arming; no active owner or capture. |
| `h1_body` | Original admitted owner has a fixed-length incomplete body; capture remains incomplete; waiting owner is rechecked at gate and actual TERM. |
| `h2_reader_frozen` | Original admitted owner is suspended; a positive queue count and bounded DATA/PING writes precede readiness; suspension, queue, owner identity and incomplete capture are rechecked at TERM. |
| `blocked_response` | Exact synthetic capture; original waiting response owner; unchanged progress for at least 200 ms and positive kernel send queue; progress and backpressure rechecked at TERM. The fixture uses bounded 418 chunks. |

`phase_gate` follows admission close and precedes the controller's unique owned
PID2 pidfd SIGTERM. The role checks original live owners and armed phase at
handling, observes owner DOWN and actual peer closure, and acknowledges the
fixed trap. The role sends the existing stopped tuple, and R14 validation
requires a positive `term_callback` completion record. The pinned official
[Elixir trap source](https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/elixir/lib/system.ex)
and [OTP default handler](https://raw.githubusercontent.com/erlang/otp/OTP-29.1.1/lib/kernel/src/erl_signal_handler.erl)
were read and their exact content hashes independently matched. This supports
the source interpretation that the custom handler runs on `erl_signal_server`
before default handling; actual bounded callback behavior remains untested.

All 34 fault selectors map to concrete source control flow: 22 controller
boundaries, eight launcher hooks, and four role hooks. The complete per-boundary
review is in
[enum-review.json](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v2-independent-review/enum-review.json).
The host model reaching 34 abstract stages does not prove Linux reachability.
Stages 28/29 deliberately freeze the owned domain before TERM/kill; cleanup has
no injected selector and preserves the first actual TERM clock. The selected
2000 ms grace, 2500 ms disposal deadline, shared 120 s row deadline, shared 900 s
suite deadline, and shared output allowances remain in source. Findings F1/F2
prevent acceptance of the complete lifecycle/teardown method.

The FD3 NIF checks UNIX `SOCK_SEQPACKET`, bounds control payloads to 256 bytes,
rejects every ancillary item, and closes received `SCM_RIGHTS`. Controller
receive applies the same rejection rule. `SO_PEERCRED` is explicitly treated as
creator identity rather than sender proof. The actual post-exec NIF sets and
reads back dumpable zero before transport/readiness; core and file-size limits
are zero and the inherited core-policy gate rejects piped collectors. Fixed
phase/fault enums add no arbitrary HTTP, path, FD, PID, callback, or command
selection. These checks were reviewed in source only.

All 31 producer pure/model/mock host controls passed once independently. The
retained macOS preflight records exit 78, 18 unavailable rows and zero Linux
runtime rows; it was inspected without rerunning or extending the sealed tree.
Both independent defect reproductions succeeded after withdrawing an initial
NIF-binding concern: v1 and v2 NIF source bytes are identical. The failed initial
reviewer-premise check is retained as historical evidence and is not a product
test failure or an outstanding finding.

No C/NIF/BEAM compilation, Linux/container/daemon/VM start, image pull, install,
stress, provider/cloud operation, native/device query, signal, live process
inventory, or physical run occurred. No producer file, tracker, or Git state was
changed. All 30 runtime matrix rows and physical/GA acceptance remain pending.
Repair should occur in a new immutable candidate, preserving failed v2, followed
by independent review of the changed source and focused host controls. Root owns
subsequent runtime selection.

Commands, versions, exact source bindings, outputs, limitations and finding
records are recorded in
[receipt.json](/Users/andreyyurlov/Documents/dev/mixer/verification/stripe-resource-harness-v2-independent-review/receipt.json).
