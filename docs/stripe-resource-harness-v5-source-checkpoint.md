# Private Linux resource harness V5 source checkpoint

The private resource harness now has independent and root source/host-method
acceptance with no open findings. All 82 producer controls and eight independent
controls pass. These use the actual adapter, descriptor iterator and cleanup
session with finite OS mocks; they do not demonstrate Linux enforcement.

V4 repaired child-PID-namespace lifetime tracking and immutable cleanup history.
Its independent review then found that a successful descriptor read could be
lost when a later read failed or the task exited. V5 immediately hands each
sanitized successful read to the fixed inventory consumer. A later error or
proved exit preserves the historical observation while final physical-zero
proof remains separate. Retry history stays immutable, first failure stays
sticky, and a later successful cleanup does not reopen admission.

The prior source packets and failed review cases remain intact. The backend,
lifecycle, C launcher, NIF, role and signal-authority bytes are unchanged from V4.
The four stop phases, 34 fault boundaries, resource limits and original deadlines
remain unchanged. The reviewer reproduced the V4 evidence loss before checking
V5's generator failures, deadline boundaries, retries and detached history.

See [the independent review](stripe-resource-harness-v5-independent-review.md)
and [root source acceptance](../verification/stripe-webhook-resource-ingress-root-review/v5-source-acceptance/receipt.json).
The selected producer seal is
`22e44e7b2a5d507e0fa2d6cd84aa1b835123d322d8b91baf7004b827490e8c85`;
the independent review seal is
`829f24609f9033c462ffb0b72f276535da68721acf438f0571e432cef6732348`.

All 30 actual runtime matrix rows remain pending. The macOS capability preflight
exited 78 with all 18 rows unavailable and zero executed. An actual Linux
artifact and isolated environment must be selected and qualified before running
resource tests. No Linux compilation, resource enforcement, deployment, trailer,
TLS, provider, production or GA acceptance follows from this checkpoint.
