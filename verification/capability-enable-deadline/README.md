# Owned enable cutoff

The trusted lifecycle SPI carries the original startup uptime cutoff through the
existing command slot and checks it immediately before native enable. Queue delay
does not renew the deadline. Expiry records one typed terminal failure and closes
normally. The existing development enable API is unchanged.

`receipt.json` binds the 35-test debug/release/TSan matrix, the narrow consumer
fixture repair, and the independent review. The first standalone fixture lacked
required memory/wake ABI elements and failed. Its result is preserved; the repair
changes only that fixture and rebuilds all four platform targets. Eight consumers
link, and both macOS consumers execute. Independent debug/release checks prove
zero native enable calls after queued expiry, ordinary retirement and permit
reuse, successful real KV effects before cutoff, and first-failure preservation.

The cutoff is a sampled cooperative check. It does not establish hard real-time
enablement, signed activation, device execution, or any completed product gate.
