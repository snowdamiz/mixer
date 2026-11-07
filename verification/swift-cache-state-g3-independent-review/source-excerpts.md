# Frozen source and binding cost excerpts

Source custody and hashes: custody.json. Text evidence only.

```text
149: fn ld(b: &[u8], at: usize) -> u64 {
150:     u64::from_le_bytes(
151:         *b[at..at + 8]
152:             .first_chunk::<8>()
153:             .expect("proved eight-byte range"),
154:     )
155: }
156: fn st(b: &mut [u8], at: usize, n: u64) {
157:     b[at..at + 8].copy_from_slice(&n.to_le_bytes());
158: }
159: fn cq(c: &Candidate2048, i: usize) -> u64 {
160:     ld(c, SC + 8 * i)
161: }
162: fn sq(c: &mut Candidate2048, i: usize, n: u64) {
163:     st(c, SC + 8 * i, n);
164: }
```

```text
238: // Eligibility uses index MAX, never timestamp MAX. Every timestamp is read once
239: // during the resident probe. Stable left preference resolves equal timestamps
240: // by the initial ascending slot order. Six fixed passes emit exactly384 moves;
241: // merge comparisons <=32+48+56+60+62+63=321, including tail MAX comparisons.
242: #[cfg(test)]
243: static SORT_COMPARISONS: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
244: #[cfg(test)]
245: static SORT_MOVES: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
246: fn merge(c: &mut Candidate2048) {
247:     let mut src = 512;
248:     let mut dst = 1024;
249:     let mut width = 1;
250:     while width < 64 {
251:         let mut base = 0;
252:         while base < 64 {
253:             let mut left = base;
254:             let mid = base + width;
255:             let end = base + 2 * width;
256:             let mut right = mid;
257:             for out in base..end {
258:                 let take_left = if left == mid {
259:                     false
260:                 } else if right == end {
261:                     true
262:                 } else {
263:                     #[cfg(test)]
264:                     SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
265:                     let a = ld(c, src + left * 8);
266:                     let b = ld(c, src + right * 8);
267:                     b == ABSENT || (a != ABSENT && ld(c, a as usize * 8) <= ld(c, b as usize * 8))
268:                 };
269:                 let index_at = if take_left {
270:                     let at = src + left * 8;
271:                     left += 1;
272:                     at
273:                 } else {
274:                     let at = src + right * 8;
275:                     right += 1;
276:                     at
277:                 };
278:                 c.copy_within(index_at..index_at + 8, dst + out * 8);
279:                 #[cfg(test)]
280:                 SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
281:             }
282:             base = end;
283:         }
284:         std::mem::swap(&mut src, &mut dst);
285:         width *= 2;
286:     }
287: }
```

## docs/swift-semantic-adapter-prerequisite.md

```text
244: Global ceilings stay arena8,388,608, complete named transients65,536,
245: reserved transients41,984, authored steps268,435,456, setup65,536,
246: report3,000,000, I/O263,584, next-record preflight8,192,
247: Rust report49,152 and aggregate report65,536. The proposed new-path ceilings are:
248: 
249: | Proposed semantic per-record group | Maximum authored debits |
250: | --- | ---: |
251: | admission, prior controls and record loan | 256 |
252: | up to64 resident probes plus64 token probes and scratch seeding | 2,560 |
253: | up to321 stable merge comparisons,8 each | 2,568 |
254: | up to384 index transfers,2 each | 768 |
255: | up to64 selected-prefix arithmetic steps,10 each | 640 |
256: | complete delta staging/commit plus candidate clear/restore | 640 |
257: | complete reply/received/progress transfers, audit and terminal paths | 248 |
258: | **semantic ceiling per successfully paid combined record** | **7,680** |
259: 
260: These are **proposed admissible source-work ceilings**, not a verified ledger
261: for missing Rust. Each micro-operation, loop guard, fixed copy, little-endian
262: conversion, full Result and caller move must map exactly once to a ledger row;
263: scalar blocks use at most16 named operations/group and copies at most128 bytes/
264: group. Group maxima are not interchangeable spare credits. Missing or
265: over-budget mapping blocks implementation acceptance; it never increases a cap.
266: No implicit optimizer elision supplies the bound.
```
