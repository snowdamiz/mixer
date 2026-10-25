// Independent review controls. Shared verbatim between pristine baseline and
// candidate copies; assertions use a separate timestamp/slot/pin model.
fn independent_review_state(cache: &SwiftFunctionCache, model: &[(Option<u32>, usize, u64)], control: &RuntimeControl, empty_tickets: usize) {
    let actual = inspection::elision_slots(cache);
    assert_eq!(actual.len(), model.len());
    for (slot, &(function, pins, tick)) in model.iter().enumerate() {
        let rank = model.iter().filter(|(f, _, t)| f.is_some() && *t < tick).count();
        assert_eq!(actual[slot], [slot as u64, function.map(u64::from).unwrap_or(u64::MAX), pins as u64, rank as u64]);
    }
    let live = model.iter().filter(|(f,_,_)| f.is_some()).count();
    let active: usize = model.iter().map(|(_,pins,_)| *pins).sum();
    assert_eq!(control.usage(None).live.cache_entries.current, live);
    assert_eq!(control.usage(None).live.active_pins.current, active);
    assert_eq!(control.usage(None).reservations.live_tickets, empty_tickets+live);
    assert_eq!(control.usage(None).reservations.cache.current, cache.usage().fixed_reserved+cache.usage().resident_bytes);
    independent_review_extra(cache);
}
#[test]
fn independent_review_long_model_lru_pins_and_slot_reuse() {
    let bytes = fixture(0, &[0, 0x0b], 2048);
    let mut trace = 0xcbf2_9ce4_8422_2325u64;
    for capacity in [1, 3, 16, 64] {
        hooks(Hooks::default());
        let (mut c, mut cache) = new(&bytes, SwiftRunBudget {cache_entries: capacity, ..SwiftRunBudget::default()});
        let empty_tickets = c.usage(None).reservations.live_tickets;
        let mut slots = vec![(None, 0usize, 0u64); capacity];
        let mut held: Vec<(SwiftFunctionPin, usize, u32)> = Vec::new();
        let mut rng = 0xe892_776au64;
        let mut tick = 0u64;
        let mut hits = 0u64;
        let mut misses = 0u64;
        let mut evictions = 0u64;
        for _ in 0..2048 {
            rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
            if !held.is_empty() && (rng % 5 == 0 || held.len() >= 24) {
                let index = (rng as usize) % held.len();
                let (p, slot, f) = held.swap_remove(index);
                assert_eq!(cache.view(&p, &mut c, None).unwrap().function, f);
                let (_, allocation) = measure(|| cache.release(p, &mut c, None).map_err(|e|e.failure).unwrap());
                assert_eq!(allocation.attempts, 0);
                slots[slot].1 -= 1;
            } else {
                let mut f = 34 + (rng % 160) as u32;
                if f == 62 { f = 194; }
                if slots.iter().all(|(f,p,_)| f.is_some() && *p > 0) && !slots.iter().any(|(v,_,_)| *v == Some(f)) {
                    f = slots[(rng as usize) % slots.len()].0.unwrap();
                }
                let hit = slots.iter().position(|(v,_,_)| *v == Some(f));
                let selected = if let Some(s) = hit {hits += 1; s} else {
                    misses += 1;
                    if let Some(s) = slots.iter().position(|(v,_,_)|v.is_none()) {s} else {
                        evictions += 1;
                        slots.iter().enumerate().filter(|(_,(_,p,_))|*p==0).min_by_key(|(_,(_,_,t))|*t).unwrap().0
                    }
                };
                let (p, allocation) = measure(|| pin(&mut cache, &mut c, f, None).unwrap());
                if hit.is_some() {assert_eq!(allocation.attempts, 0);}
                assert_eq!(cache.view(&p, &mut c, None).unwrap().function, f);
                tick += 1;
                assert_eq!(inspection::elision_pin_parts(&p)[1], tick);
                slots[selected] = (Some(f), slots[selected].1+1, tick);
                held.push((p,selected,f));
            }
            independent_review_state(&cache, &slots, &c, empty_tickets);
            assert_eq!((cache.usage().hits,cache.usage().misses,cache.usage().decodes,cache.usage().evictions),(hits,misses,misses,evictions));
            for row in inspection::elision_slots(&cache) { for value in row { trace = (trace ^ value).wrapping_mul(0x100_0000_01b3); } }
        }
        for (p, slot, f) in held { assert_eq!(cache.view(&p,&mut c,None).unwrap().function,f);cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap(); slots[slot].1-=1; }
        independent_review_state(&cache,&slots,&c,empty_tickets);
        println!("INDEPENDENT_MODEL capacity={capacity} operations=2048 hits={hits} misses={misses} evictions={evictions} trace={trace:016x}");
        finish(cache,c);
    }
}
#[test]
fn independent_review_cold_and_hit_actual_credit_comparison() {
    hooks(Hooks::default());
    let bytes = fixture(0,&[0,0x0b],100);
    let (mut c, mut cache) = new(&bytes,SwiftRunBudget::default());
    let constructor = c.usage(None).cache_work;
    for f in 34..98 {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}
    let cold=c.usage(None).cache_work-constructor;
    let before=c.usage(None).cache_work;
    let (_,stats)=measure(||for _ in 0..4 {for f in 34..98 {let p=pin(&mut cache,&mut c,f,None).unwrap();cache.release(p,&mut c,None).map_err(|e|e.failure).unwrap();}});
    assert_eq!(stats.attempts,0);
    println!("INDEPENDENT_COST constructor={constructor} cold={} hits={} resident={} fixed={} hit_allocations={}",cold,c.usage(None).cache_work-before,cache.usage().resident_bytes,cache.usage().fixed_reserved,stats.attempts);
    finish(cache,c);
}
