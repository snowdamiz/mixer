# Source-bound proof excerpts

Frozen correction1 cache source hash: 1ffc4ee5bb37c4ca2794c456f66bfcd9f1916090a0de3a548c19b6c82a3767b9.

```text
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

```text
328:     if f.slots == 0
329:         || f.slots > 64
330:         || f.pins == 0
331:         || f.pins > 64
332:         || p.terminal() != 0
333:         || p.latch >> 8 > f.pins
334:         || p.q[3] > 10
```

```text
362:     for slot in 0..f.slots as usize {
363:         let occupied = rr(b, slot, 0);
364:         let function = rr(b, slot, 1);
365:         let bytes = rr(b, slot, 2);
366:         let pins = rr(b, slot, 3);
367:         if occupied > 1 || pins > f.pins || rr(b, slot, 6) != 0 || rr(b, slot, 7) != 0 {
368:             return reject(13);
369:         }
370:         if occupied == 1 {
371:             // At most64 rows and at most64 pins per row prove this sum <=4096.
372:             resident_pins += pins;
373:             if function >= 80000 || bytes == 0 || bytes > f.entry {
374:                 return reject(13);
375:             }
376:             let Some(sum) = total.checked_add(bytes) else {
377:                 return reject(10);
378:             };
379:             total = sum;
380:             count += 1;
381:             if function == w[6] {
382:                 if found != ABSENT {
383:                     return reject(7);
384:                 }
385:                 found = slot as u64;
386:             }
387:         } else if function != ABSENT || bytes != 0 || pins != 0 {
388:             return reject(13);
389:         } else if first_empty == ABSENT {
390:             first_empty = slot as u64;
391:         }
392:         st(c, slot * 8, rr(b, slot, 4));
393:         st(
394:             c,
395:             512 + slot * 8,
396:             if occupied == 1 && pins == 0 {
397:                 slot as u64
398:             } else {
399:                 ABSENT
400:             },
401:         );
402:     }
403:     for slot in f.slots as usize..64 {
404:         st(c, slot * 8, 0);
405:         st(c, 512 + slot * 8, ABSENT);
```

```text
526:             if w[13] == 0
527:                 || w[13] > f.entry
528:                 || w[14] != f.base
529:                 || w[15] != f.capacity
530:                 || f.base.checked_add(w[13]).is_none_or(|v| v > f.capacity)
531:             {
532:                 return reject(10);
533:             }
534:             c[1648..1688].copy_from_slice(&b[PLAN.base + 40 * cell..PLAN.base + 40 * cell + 40]);
535:             st(c, 1680, w[13]);
536:             plan_delta = cell as u64;
537:             sq(c, 18, w[13]);
538:             merge(c);
```
