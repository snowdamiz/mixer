# Hosted build lifecycle checkpoint

Root accepts the first pure Elixir build-attempt component at source/test tree
`c00622e2b2794ca647130a4cbf7622faffaccd4ad2c89e49f38daa50419e7aea`.
The producer and root each pass 21 tests. Independent review passes those 21
plus ten hostile controls; root verifies all 21 producer and 50 review files.

Each platform build retains immutable source/toolchain/build identity. Scoped
worker references reject stale or cross-build results. Exact event redelivery
returns current state without replaying effects. Cancellation and expiry retain
the old worker until a matching terminal observation; retries are bounded and
limited to allowed infrastructure failures. Known compiler, test and policy
failures remain nonretryable even when their reports arrive after the deadline.
Successful output contains seven immutable typed artifact references.

This is trusted in-memory application logic. It does not provide authentication,
durable compare-and-set, atomic Oban scheduling, real worker termination,
artifact content verification, signing, publication or billing. Those adapters
and operational tests remain required; W12 and all GA gates remain open.

The [root receipt](../verification/hosted-build-lifecycle-root-review/acceptance.json)
binds exact producer/review inputs and the fresh local run. The
[independent review](hosted-build-lifecycle-independent-review.md) records the
hostile controls and limits. Initial test and recorder errors remain preserved;
the root recorder expected an older ExUnit summary format, then recorded the
actual `Result: 21 passed` output without rerunning or changing the source.
No native instance, provider, database or persistent service was started.

Before commit, root removed one extra empty EOF line from each product/test file.
The original sealed snapshots are unchanged; the exact two-line normalization
and a fresh 21-test pass are recorded in `normalization.json` beside the root receipt.
