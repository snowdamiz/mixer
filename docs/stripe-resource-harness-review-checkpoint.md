# Private Linux resource harness review checkpoint

The private harness now implements bounded R14 termination phases and R18 fault
boundaries, but it is **not approved for runtime qualification**. Production
transport and provider behavior are unchanged. All thirty Linux runtime matrix
rows remain pending.

The first independent review rejected V2 because later rows could start after
incomplete cleanup and the holder scan omitted nonleader thread metadata. V3
adds suite/backend admission barriers and per-thread namespace/descriptor
inventory. Its sealed source contains the original four R14 phases and thirty-
four R18 boundaries. The original resource ceilings, control protocol and
deadlines remain unchanged.

The V3 review verifies ninety sealed producer files, reruns all fifty-two host
controls, and adds eight independent controls against actual Python adapter and
session code with OS/runtime calls mocked. The admission barrier now survives
cleanup retries. Two defects remain reproduced:

- A thread can retain an owned PID namespace through `pid_for_children` while
  its current PID namespace differs. The inventory omits that lifetime pin and
  can incorrectly report zero holders.
- A later successful cleanup overwrites the first positive holder observation.
  The backend still blocks new work, but the failed attempt's evidence is lost.

Root selected a separate V4 correction for these exact findings. Each cleanup
attempt must retain its observed counts or explicit unknown state, failure
reason and timing. A later physical disposal must preserve the first failure
and admission barrier. Child-PID-namespace metadata must obey the original
identity, complete-inventory and deadline rules; missing or ambiguous data must
not become a zero count. No foreign holder may be signaled.

The macOS preflight exits 78 with all eighteen environment checks unavailable.
No Linux compiler, process inventory, signal or runtime result is claimed by
the host controls. The launcher, NIF, Elixir role and signal-authority bytes
remain unchanged. Independent V4 review and actual Linux compilation/runtime
are required before any acceptance; no native, provider or GA gate passes.

Evidence:

- [V2 independent review](stripe-resource-harness-v2-independent-review.md)
- [V3 independent review](stripe-resource-harness-v3-independent-review.md)
- [V3 producer seal](../verification/stripe-webhook-linux-resource-harness/v3/seal.json)
- [V3 independent controls](../verification/stripe-resource-harness-v3-independent-review/independent-host-controls.json)
- [Root V4 repair selection](../verification/stripe-webhook-resource-ingress-root-review/v3-cleanup-review-repair-selection.json)

Every earlier packet, failed observation and review remains immutable. The
withdrawn V2 NIF-source mismatch is not a finding; those bytes were identical.
