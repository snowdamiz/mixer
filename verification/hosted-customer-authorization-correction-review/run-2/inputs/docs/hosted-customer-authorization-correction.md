# Customer authorization callback correction

Independent review found that the original repository facade accepted a Decision
with only matching action and target, even when the adapter never invoked the
policy callback and every remaining field was nil. The original producer and
review packets remain unchanged historical evidence. Their run inputs retain the
exact earlier source; the original review remains changes requested.

The corrected facade creates a fresh request-local reference captured only by its
policy callback. A successful result must carry that callback envelope, the exact
reference, and a complete closed Decision projection. Credential/profile fields,
action, target and evaluation time must match the current request. Principal and
membership identifiers, contributing action-compatible roles, unique sorted lists,
and all revision fields must meet the original bounds. Missing, wrong and reused
request markers, incomplete projections, wrong identity/target fields and invalid
role/revision/list data become authorization_unavailable. Legitimate success and
the bounded policy failures retain their public result shape. No process dictionary
or global mutable state is used by product code; test fixtures use per-test process
state to simulate faulty adapters.

The trusted adapter callback contract now returns an internal envelope unchanged,
or a bounded failure. This is adapter bug containment, not protection against
malicious BEAM code: a trusted adapter can inspect and deliberately alter terms.
The envelope is neither public authority nor a transferable ticket and does not
prove database freshness, locks or revocation. Principal resolution still comes
from server evidence, not token claims. The pure projection remains insufficient
for the future immutable audit schema and transaction-bound storage context.

The standalone run-1 compiles the five ordinary identity/authorization modules with
warnings as errors and passes 30/30 ExUnit tests on Darwin arm64, Elixir 1.20.4,
OTP 29.1.1 / ERTS 17.1. Four new methods cover the reported missing-callback failure,
missing/wrong/reused references, malformed/altered projections and preserved
success/error behavior. Exact sources, commands, versions, output, supplied
b375e55ded9e3e10c327891ab681beff2a471e26 revision context and source digest are
retained. The owned temporary directory was removed. No database, Mix startup,
network, routes, providers, native runtime or frozen lanes ran. No durable/public
customer authorization or GA gate is claimed. Independent correction review is
pending and may extend these finite checks.
