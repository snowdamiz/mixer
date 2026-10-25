from pathlib import Path
H=Path(__file__).resolve().parent;P=H/'source/src/experimental_swift_reactor/cache_tests.rs';s=P.read_text()
s=s.replace('assert_eq!(s.allocations, 3);','assert_eq!(s.allocations, 4);',1)
s=s.replace('+ 512 * size_of::<decode::Patch>();','+ 512 * size_of::<decode::Patch>() + 192;',1)
s=s.replace('assert_eq!(n, 3);','assert_eq!(n, 4);',1)
s=s.replace('    for ordinal in 0..3 {\n        hooks(Hooks::default());\n        let (mut c, a) = adopt','    for ordinal in 0..4 {\n        hooks(Hooks::default());\n        let (mut c, a) = adopt',1)
s=s.replace('reservations.live_tickets, 73','reservations.live_tickets, 74')
s=s.replace('assert_eq!(allocations.attempts, 3);','assert_eq!(allocations.attempts, 4);')
s=s.replace('assert_eq!(allocations.allocations, 3);','assert_eq!(allocations.allocations, 4);')
s=s.replace('actual_constructor_allocations=3','actual_constructor_allocations=4')
s=s.replace('assert_eq!(c.usage(None).cache_work, 640);','assert_eq!(c.usage(None).cache_work, 832);')
s=s.replace('assert_eq!(hit.stage_work.iter().sum::<u64>(), 3);','assert_eq!(hit.stage_work.iter().sum::<u64>(), 8);')
s=s.replace('\\"constructorWork\\":640','\\"constructorWork\\":832').replace('\\"hitWork\\":3','\\"hitWork\\":8')
start=s.index('    for ceiling in [\n        header - 1,',s.index('fn review_exact_phase'))
end=s.index('\n}\n\n// Exercises',start)
s=s[:start]+'''    for ceiling in [header - 1, header, header + patch_bytes - 1,
        header + patch_bytes, header + patch_bytes + 191, header + patch_bytes + 192] {
        let (mut c, a) = adopt(&bytes, SwiftRunBudget {
            cache_bytes: ceiling, cache_entries: 0, active_pins: 0,
            ..SwiftRunBudget::default()
        });
        let (result, stats) = measure(|| construct(&mut c, a, None));
        if ceiling == header + patch_bytes + 192 {
            assert_eq!(stats.attempts, 2);
            let cache = result.unwrap();
            assert_eq!(c.usage(None).reservations.cache.current, ceiling);
            finish(cache, c);
        } else {
            assert_eq!(stats.attempts, usize::from(ceiling >= header + patch_bytes));
            let failure = result.err().unwrap();
            assert_eq!(failure.kind, SwiftRunFailureKind::CategoryExhausted);
            assert_eq!(c.usage(None).reservations.cache.peak,
                if ceiling < header { 0 } else if ceiling < header + patch_bytes { header }
                else { header + patch_bytes });
            assert_eq!(c.usage(None).reservations.cache.current, 0);
            assert_eq!(c.finish_owned_cleanup(None).reservations.combined.current, 0);
        }
    }'''+s[end:]
P.write_text(s)
C=H/'source/src/experimental_swift_reactor/cache.rs';s=C.read_text();needle='    // Test-only snapshots of the actual owner, never stored in production state.\n';assert s.count(needle)==1
s=s.replace(needle,needle+'''    pub fn resident_index(cache: &SwiftFunctionCache) -> &[u8] { &cache.index }
    pub fn corrupt_index(cache: &mut SwiftFunctionCache, cell: usize, value: u8) {
        cache.index[cell] = value;
    }
''');C.write_text(s)
