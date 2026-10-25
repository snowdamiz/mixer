    // Test-only snapshots of the actual owner, never stored in production state.
    pub fn elision_pin_parts(pin: &SwiftFunctionPin) -> [u64; 2] {
        [pin.slot as u64, pin.nonce]
    }
    pub fn elision_slots(cache: &SwiftFunctionCache) -> Vec<[u64; 4]> {
        cache
            .slots
            .iter()
            .enumerate()
            .map(|(index, slot)| {
                let function = slot
                    .resident
                    .as_ref()
                    .map(|r| r.decoded.function as u64)
                    .unwrap_or(u64::MAX);
                let rank = cache
                    .slots
                    .iter()
                    .filter(|other| other.resident.is_some() && other.last_used < slot.last_used)
                    .count();
                [index as u64, function, slot.pins as u64, rank as u64]
            })
            .collect()
    }
    pub fn elision_times(cache: &SwiftFunctionCache) -> Vec<u64> {
        cache.slots.iter().map(|slot| slot.last_used).collect()
    }
    pub fn elision_dirty_owner(cache: &mut SwiftFunctionCache) {
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
    }
    pub fn elision_malformed(cache: &mut SwiftFunctionCache, body: &[u8]) -> [&'static str; 2] {
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
        let limits = crate::Limits::default();
        let policy = crate::experimental::cache::borrowed::FrozenPolicy {
            limits: &limits,
            extent: body.len(),
        };
        let mut depth = 0;
        let mut counts = decode::Counts::default();
        let scan = decode::scan_borrowed(
            body,
            0,
            &policy,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
        .err()
        .expect("malformed scan must fail");
        // Independent generous exact capacities from a valid finite body;
        // malformed syntax must fail before count/build agreement is reached.
        const VALID: &[u8] = &[0, 1, 1, 1, 1, 1, 1, 1, 1, 0x0b];
        depth = 0;
        counts = decode::Counts::default();
        let expected = decode::scan_borrowed(
            VALID,
            0,
            &policy,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
            None,
        )
        .unwrap();
        super::super::cache_tests::elision_seed_patches(&mut cache.patches);
        depth = 0;
        counts = decode::Counts::default();
        let build = decode::build_borrowed(
            body,
            0,
            0,
            34,
            &policy,
            expected,
            &mut super::super::cache_tests::ElisionScratchMeter,
            decode::PassParts {
                controls: &mut cache.patches,
                depth: &mut depth,
                counts: &mut counts,
            },
        )
        .err()
        .expect("malformed build must fail");
        [scan, build]
    }
