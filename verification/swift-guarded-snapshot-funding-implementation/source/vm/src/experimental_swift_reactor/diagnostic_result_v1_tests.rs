//! Actual imported-type tests. Proposal and independent controls are ported here.
use super::*;
fn bytes<const N: usize>(words: &[u64]) -> [u8; N] {
    let mut out = [0; N];
    write_words(&mut out, words);
    out
}
fn encode_usage(u: &SwiftRunUsage) -> Result<[u8; 512], Refusal> {
    let mut out = [0; 512];
    encode_usage_v1(u, &mut out)?;
    Ok(out)
}
fn decode_usage(raw: &[u8; 512]) -> Result<SwiftRunUsage, Refusal> {
    decode_usage_v1(raw)
}
fn encode_failure_meta(f: &SwiftRunFailure) -> Result<[u8; 256], Refusal> {
    let mut out = [0; 256];
    encode_failure_scalar_v1(f, &mut out)?;
    Ok(out)
}
fn decode_failure_meta(raw: &[u8; 256]) -> Result<UnverifiedFailureScalarsV1<'_>, Refusal> {
    decode_failure_scalar_v1(raw)
}
fn ledger(u: &SwiftRunUsage) -> [u64; 15] {
    let r = &u.reservations;
    let l = &u.live;
    [
        r.retained_source.current as u64,
        r.retained_metadata.current as u64,
        r.cache.current as u64,
        r.state.current as u64,
        r.wasi.current as u64,
        r.shared.current as u64,
        r.construction.current as u64,
        r.combined.current as u64,
        r.live_tickets as u64,
        l.cache_entries.current as u64,
        l.active_pins.current as u64,
        l.frames.current as u64,
        l.values.current as u64,
        l.controls.current as u64,
        l.memory_pages.current as u64,
    ]
}
fn usage() -> SwiftRunUsage {
    let mut w = std::array::from_fn::<_, 64, _>(|i| 100 + i as u64);
    w[35] = 5;
    w[38] = 2;
    w[50] = 1;
    decode_usage(&bytes(&w)).unwrap()
}
fn failure() -> SwiftRunFailure {
    SwiftRunFailure {
        stage: SwiftRunStage::Adoption,
        kind: SwiftRunFailureKind::InvalidBudget,
        code: "swift_run_fixture",
        function: None,
        offset: None,
        resource: None,
        attempted: u64::MAX,
        limit: 0,
        observed_capacity: None,
        deadline_origin: SwiftDeadlineOrigin::Run,
        wasi_failure: None,
        guest_exit: None,
        at_failure: usage(),
        after_cleanup: Some(usage()),
    }
}
fn compare(f: &SwiftRunFailure) {
    let raw = encode_failure_meta(f).unwrap();
    let d = decode_failure_meta(&raw).unwrap();
    assert_eq!((d.stage, d.kind, d.code), (f.stage, f.kind, f.code));
    assert_eq!(
        (d.function, d.offset, d.resource),
        (f.function, f.offset, f.resource)
    );
    assert_eq!(
        (d.attempted, d.limit, d.observed_capacity),
        (f.attempted, f.limit, f.observed_capacity)
    );
    assert_eq!(
        (d.deadline_origin, d.wasi_failure, d.guest_exit),
        (f.deadline_origin, f.wasi_failure, f.guest_exit)
    );
}
#[test]
fn all_usage_fields_roundtrip() {
    let u = usage();
    assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(), u);
    let w = words::<64>(&encode_usage(&u).unwrap());
    for i in 0..64 {
        if ![35, 38, 50].contains(&i) {
            assert_eq!(w[i], 100 + i as u64);
        }
    }
}
#[test]
fn all_stage_kind_cleanup_origin_variants() {
    for s in 1..=6 {
        for k in 1..=21 {
            let mut f = failure();
            f.stage = word_stage(s).unwrap();
            f.kind = word_kind(k).unwrap();
            compare(&f);
        }
    }
    for c in 0..=5 {
        for d in 1..=2 {
            let mut u = usage();
            u.cleanup_invariant = if c == 0 {
                None
            } else {
                Some(word_cleanup(c).unwrap())
            };
            u.deadline_origin = word_origin(d).unwrap();
            assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(), u);
        }
    }
}
#[test]
fn all_resource_payloads() {
    for tag in 1..=17 {
        for p in if tag == 1 { 1..=7 } else { 0..=0 } {
            let mut f = failure();
            f.resource = Some(words_resource(tag, p).unwrap());
            compare(&f);
        }
    }
}
#[test]
fn all_wasi_failure_payloads() {
    for tag in 1..=8 {
        for p in if tag == 5 { 1..=5 } else { 0..=0 } {
            let mut f = failure();
            f.wasi_failure = Some(words_wasi(tag, p).unwrap());
            compare(&f);
        }
    }
}
#[test]
fn optional_fields_none_zero_and_max() {
    for mask in 0..64 {
        let mut f = failure();
        if mask & 1 != 0 {
            f.function = Some(0);
        }
        if mask & 2 != 0 {
            f.offset = Some(0);
        }
        if mask & 4 != 0 {
            f.resource = Some(SwiftRunResource::Reservation(
                SwiftReservationCategory::Construction,
            ));
        }
        if mask & 8 != 0 {
            f.observed_capacity = Some(0);
        }
        if mask & 16 != 0 {
            f.wasi_failure = Some(WasiFailure::InvalidMemory);
        }
        if mask & 32 != 0 {
            f.guest_exit = Some(0);
        }
        compare(&f);
    }
    let mut f = failure();
    f.function = Some(u32::MAX);
    f.offset = Some(usize::MAX);
    f.observed_capacity = Some(usize::MAX);
    f.guest_exit = Some(u32::MAX);
    compare(&f);
}
#[test]
fn wasi_none_is_distinct_from_some_zero() {
    let mut u = usage();
    u.wasi = None;
    let a = encode_usage(&u).unwrap();
    assert_eq!(decode_usage(&a).unwrap(), u);
    u.wasi = Some(WasiUsage::default());
    let b = encode_usage(&u).unwrap();
    assert_ne!(a, b);
    assert_eq!(decode_usage(&b).unwrap(), u);
}
#[test]
fn source_width_boundaries() {
    let mut u = usage();
    u.reservations.retained_source.current = usize::MAX;
    u.validation.source_bytes = usize::MAX;
    u.cache_work = u64::MAX;
    assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(), u);
    assert!(usize::BITS <= 64);
}
#[test]
fn unknown_and_inactive_enums_refuse() {
    assert!(word_stage(0).is_err());
    assert!(word_stage(7).is_err());
    assert!(word_kind(0).is_err());
    assert!(word_kind(22).is_err());
    assert!(word_cleanup(6).is_err());
    assert!(word_origin(0).is_err());
    assert!(word_category(8).is_err());
    assert!(word_wasi_resource(6).is_err());
    assert!(words_resource(18, 0).is_err());
    assert!(words_resource(2, 1).is_err());
    assert!(words_resource(1, 0).is_err());
    assert!(words_wasi(9, 0).is_err());
    assert!(words_wasi(1, 1).is_err());
    assert!(words_wasi(5, 0).is_err());
}
#[test]
fn optional_and_reserved_bytes_refuse() {
    let f = failure();
    let original = encode_failure_meta(&f).unwrap();
    for i in [4, 5, 6, 7, 10, 12, 13, 14, 15] {
        let mut b = original;
        b[i * 8] = 1;
        assert!(decode_failure_meta(&b).is_err(), "word {i}");
    }
    for value in [64, 128, u64::MAX] {
        let mut b = original;
        b[16..24].copy_from_slice(&value.to_le_bytes());
        assert!(decode_failure_meta(&b).is_err());
    }
    let mut b = original;
    b[255] = 1;
    assert!(decode_failure_meta(&b).is_err());
}
#[test]
fn u32_overflow_refuses_without_truncation() {
    let mut f = failure();
    f.function = Some(0);
    f.guest_exit = Some(0);
    let raw = encode_failure_meta(&f).unwrap();
    for i in [4, 14] {
        let mut b = raw;
        b[i * 8..i * 8 + 8].copy_from_slice(&(u32::MAX as u64 + 1).to_le_bytes());
        assert!(decode_failure_meta(&b).is_err());
    }
}
#[test]
fn exact_code_bytes_and_overflow_refusal() {
    let mut f = failure();
    f.code = " ";
    compare(&f);
    f.code="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
    compare(&f);
    f.code="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
    assert!(encode_failure_meta(&f).is_err());
    f.code = "";
    assert!(encode_failure_meta(&f).is_err());
    f.code = "not\ncanonical";
    assert!(encode_failure_meta(&f).is_err());
    f.code = "é";
    assert!(encode_failure_meta(&f).is_err());
}
#[test]
fn all_fifteen_ledger_words_are_independent() {
    let u = usage();
    let base = ledger(&u);
    let raw = encode_usage(&u).unwrap();
    for (slot, wire_word) in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        .iter()
        .enumerate()
    {
        let mut w = words::<64>(&raw);
        w[*wire_word] += 1;
        let next = ledger(&decode_usage(&bytes(&w)).unwrap());
        for i in 0..15 {
            assert_eq!(next[i], base[i] + u64::from(i == slot));
        }
    }
}
#[test]
fn original_snapshots_and_final_consumption_stay_distinct() {
    let mut f = failure();
    let mut after = f.after_cleanup.unwrap();
    after.reservations.construction.current = 331496;
    after.reservations.live_tickets = 1;
    f.after_cleanup = Some(after);
    let mut final_u = after;
    final_u.elapsed_micros += 1;
    final_u.reservations.construction.current = 0;
    final_u.reservations.live_tickets = 0;
    let zero = [0; 32];
    let refs = references(0, 0, &zero, &zero);
    let mut raw = [0; 2048];
    encode_result_v1(
        ResultObservationV1 {
            failure: Some(&f),
            final_consuming: Some(&final_u),
            references: refs,
        },
        &mut raw,
    )
    .unwrap();
    let d = decode_result_v1(&raw).unwrap();
    assert_eq!(d.at_failure(), Some(&f.at_failure));
    assert_eq!(d.after_cleanup(), Some(&after));
    assert_eq!(d.final_consuming(), Some(&final_u));
    assert_ne!(ledger(&after), ledger(&final_u));
}
#[test]
fn absent_wasi_tail_and_presence_refuse() {
    let mut u = usage();
    u.wasi = None;
    let raw = encode_usage(&u).unwrap();
    for i in 51..64 {
        let mut b = raw;
        b[i * 8] = 1;
        assert!(decode_usage(&b).is_err());
    }
    let mut b = raw;
    b[400] = 2;
    assert!(decode_usage(&b).is_err());
}
#[cfg(test)]
mod independent_envelope_controls {
    use super::*;

    fn usage(marker: u64) -> SwiftRunUsage {
        SwiftRunUsage {
            reservations: SwiftReservations::default(),
            live: SwiftLiveUsage::default(),
            cache_work: marker,
            execution_work: marker + 1,
            instruction_fuel: marker + 2,
            instructions: marker + 3,
            host_calls: marker + 4,
            cleanup_invariant: None,
            elapsed_micros: marker + 5,
            deadline_ms: marker + 6,
            deadline_origin: SwiftDeadlineOrigin::Run,
            deadline_overshoot_micros: marker + 7,
            validation: SwiftValidationUsage::default(),
            wasi: None,
        }
    }
    fn failure() -> SwiftRunFailure {
        SwiftRunFailure {
            stage: SwiftRunStage::Cleanup,
            kind: SwiftRunFailureKind::Invariant,
            code: "unregistered_data_observation",
            function: Some(0),
            offset: Some(usize::MAX),
            resource: Some(SwiftRunResource::Reservation(
                SwiftReservationCategory::Construction,
            )),
            attempted: u64::MAX,
            limit: 0,
            observed_capacity: Some(0),
            deadline_origin: SwiftDeadlineOrigin::Wasi,
            wasi_failure: Some(WasiFailure::Budget(Resource::Iovecs)),
            guest_exit: Some(u32::MAX),
            at_failure: usage(41),
            after_cleanup: Some(usage(73)),
        }
    }
    fn set_word(raw: &mut [u8], index: usize, value: u64) {
        raw[index * 8..index * 8 + 8].copy_from_slice(&value.to_le_bytes());
    }
    fn record(mask: u64, constructor: u64) -> [u8; 2048] {
        let zero = [0; 32];
        let opaque = [23; 32];
        let raw_digest = [11; 32];
        let session = [13; 32];
        let schema = [17; 32];
        let writer = [19; 32];
        let refs = UnverifiedResultReferencesV1 {
            raw_original_bytes: 17,
            constructor_tag: constructor,
            constructor_bytes: if constructor == 0 { 0 } else { 65536 },
            raw_original_digest: &raw_digest,
            constructor_digest: if constructor == 0 { &zero } else { &opaque },
            session_digest: &session,
            typed_result_schema_digest: &schema,
            writer_digest: &writer,
        };
        let mut f = failure();
        if mask & 2 == 0 {
            f.after_cleanup = None;
        }
        let final_u = usage(109);
        let mut out = [0; 2048];
        encode_result_v1(
            ResultObservationV1 {
                failure: if mask & 1 == 0 { None } else { Some(&f) },
                final_consuming: if mask & 4 == 0 { None } else { Some(&final_u) },
                references: refs,
            },
            &mut out,
        )
        .unwrap();
        let d = decode_result_v1(&out).unwrap();
        assert_eq!(d.encoded(), &out);
        assert_eq!(d.references(), &refs);
        assert_eq!(
            d.at_failure(),
            if mask & 1 == 0 {
                None
            } else {
                Some(&f.at_failure)
            }
        );
        assert_eq!(
            d.after_cleanup(),
            if mask & 2 == 0 {
                None
            } else {
                f.after_cleanup.as_ref()
            }
        );
        assert_eq!(
            d.final_consuming(),
            if mask & 4 == 0 { None } else { Some(&final_u) }
        );
        if let Some(s) = d.failure_scalars() {
            assert_eq!((s.stage, s.kind, s.code()), (f.stage, f.kind, f.code));
            assert_eq!(
                (s.function, s.offset, s.resource),
                (f.function, f.offset, f.resource)
            );
            assert_eq!(
                (s.attempted, s.limit, s.observed_capacity),
                (f.attempted, f.limit, f.observed_capacity)
            );
            assert_eq!(
                (s.deadline_origin, s.wasi_failure, s.guest_exit),
                (f.deadline_origin, f.wasi_failure, f.guest_exit)
            );
            assert_eq!(s.code().as_ptr(), out[384..].as_ptr());
        } else {
            assert_eq!(mask & 1, 0);
        }
        out
    }
    fn check(raw: &[u8]) -> Result<(), Refusal> {
        decode_result_v1(raw).map(|_| ())
    }

    #[test]
    fn all_six_presence_masks_and_nine_constructor_states() {
        for mask in [0, 1, 3, 4, 5, 7] {
            for tag in 0..=8 {
                assert!(check(&record(mask, tag)).is_ok(), "mask={mask} tag={tag}");
            }
        }
    }
    #[test]
    fn malformed_present_scalar_payloads_refuse_inside_envelope() {
        let good = record(7, 8);
        for (i, value) in [
            (0, 0),
            (0, 7),
            (1, 0),
            (1, 22),
            (2, 64),
            (3, 0),
            (3, 129),
            (4, u32::MAX as u64 + 1),
            (6, 18),
            (7, 8),
            (11, 0),
            (12, 9),
            (13, 6),
            (14, u32::MAX as u64 + 1),
            (15, 1),
        ] {
            let mut r = good;
            set_word(&mut r[256..512], i, value);
            assert!(check(&r).is_err(), "scalar word {i}={value}");
        }
        for offset in [384, 511] {
            let mut r = good;
            r[offset] = 255;
            assert!(check(&r).is_err());
        }
        let mut r = good;
        let mask = words::<16>(&r[256..384])[2] & !1;
        set_word(&mut r[256..512], 2, mask);
        set_word(&mut r[256..512], 4, 1);
        assert!(check(&r).is_err(), "hidden optional function");
    }
    #[test]
    fn every_present_usage_is_decoded_not_merely_sliced() {
        for start in [512, 1024, 1536] {
            for (i, value) in [(35, 6), (38, 0), (38, 3), (50, 2), (51, 1)] {
                let mut r = record(7, 8);
                set_word(&mut r[start..start + 512], i, value);
                assert!(check(&r).is_err(), "snapshot {start} word {i}");
            }
        }
    }
    #[test]
    fn hidden_payloads_masks_extents_and_reserved_bytes_refuse() {
        for mask in [2, 6, 8, u64::MAX] {
            let mut r = record(0, 0);
            set_word(&mut r, 4, mask);
            assert!(check(&r).is_err());
        }
        for start in [256, 512, 1024, 1536] {
            let mut r = record(0, 0);
            r[start] = 1;
            assert!(check(&r).is_err());
        }
        for offset in 224..256 {
            let mut r = record(7, 8);
            r[offset] = 1;
            assert!(check(&r).is_err());
        }
        let r = record(7, 8);
        for n in [0, 1, 255, 256, 2047] {
            assert!(check(&r[..n]).is_err());
        }
        assert!(check(&[0u8; 2049]).is_err());
    }
    #[test]
    fn constructor_receipt_presence_and_exact_cap_refuse_malformed_joins() {
        for tag in 1..=8 {
            for len in [0, 65537, u64::MAX] {
                let mut r = record(7, tag);
                set_word(&mut r, 7, len);
                assert!(check(&r).is_err());
            }
            for len in [1, 65536] {
                let mut r = record(7, tag);
                set_word(&mut r, 7, len);
                assert!(check(&r).is_ok());
            }
        }
        let mut r = record(0, 0);
        set_word(&mut r, 7, 1);
        assert!(check(&r).is_err());
        let mut r = record(0, 0);
        r[96] = 1;
        assert!(check(&r).is_err());
        let mut r = record(0, 0);
        set_word(&mut r, 5, 9);
        assert!(check(&r).is_err());
    }
    #[test]
    fn final_observation_is_independent_and_all_fifteen_ledgers_survive() {
        let original = record(7, 8);
        let final_start = 1536;
        for (slot, wire_word) in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
            .iter()
            .enumerate()
        {
            let mut r = original;
            set_word(&mut r[final_start..], *wire_word, slot as u64 + 1);
            assert!(check(&r).is_ok());
            assert_eq!(&r[256..1536], &original[256..1536]);
            let final_u = decode_usage(r[1536..].try_into().unwrap()).unwrap();
            assert_eq!(ledger(&final_u)[slot], slot as u64 + 1);
        }
        let mut r = record(4, 0);
        set_word(&mut r[1536..], 12, 331496);
        set_word(&mut r[1536..], 14, 331496);
        set_word(&mut r[1536..], 16, 1);
        set_word(&mut r[1536..], 35, 4);
        assert!(check(&r).is_ok());
        let final_u = decode_usage(r[1536..].try_into().unwrap()).unwrap();
        assert_eq!(
            (
                final_u.reservations.construction.current,
                final_u.reservations.live_tickets
            ),
            (331496, 1)
        );
        assert_eq!(
            final_u.cleanup_invariant,
            Some(SwiftCleanupInvariant::ConstructionBound)
        );
    }
    #[test]
    fn unknown_code_and_anomalous_observations_are_data_without_semantic_admission() {
        let r = record(7, 8);
        let f = decode_failure_meta(r[256..512].try_into().unwrap()).unwrap();
        assert_eq!(f.code, "unregistered_data_observation");
        assert_eq!(f.guest_exit, Some(u32::MAX));
        let mut u = usage(1);
        u.reservations.cache.current = 99;
        u.reservations.cache.peak = 1;
        assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(), u);
    }
}

fn references<'a>(
    tag: u64,
    len: u64,
    zero: &'a [u8; 32],
    opaque: &'a [u8; 32],
) -> UnverifiedResultReferencesV1<'a> {
    UnverifiedResultReferencesV1 {
        raw_original_bytes: 0,
        constructor_tag: tag,
        constructor_bytes: len,
        raw_original_digest: zero,
        constructor_digest: if tag == 0 { zero } else { opaque },
        session_digest: zero,
        typed_result_schema_digest: zero,
        writer_digest: zero,
    }
}
#[test]
fn every_wrong_extent_refuses_without_writing() {
    let f = failure();
    let u = usage();
    let zero = [0; 32];
    let observation = ResultObservationV1 {
        failure: Some(&f),
        final_consuming: Some(&u),
        references: references(0, 0, &zero, &zero),
    };
    for n in 0..=2049 {
        let mut out = [0xa5; 2049];
        let before = out;
        if n != 2048 {
            assert_eq!(
                encode_result_v1(observation, &mut out[..n]),
                Err(CodecRefusalV1::Extent)
            );
            assert_eq!(out, before);
        }
        if n != 512 {
            assert_eq!(
                encode_usage_v1(&u, &mut out[..n]),
                Err(CodecRefusalV1::Extent)
            );
            assert_eq!(out, before);
        }
        if n != 256 {
            assert_eq!(
                encode_failure_scalar_v1(&f, &mut out[..n]),
                Err(CodecRefusalV1::Extent)
            );
            assert_eq!(out, before);
        }
        let input = [0; 2049];
        if n != 2048 {
            assert_eq!(
                decode_result_v1(&input[..n]).unwrap_err(),
                CodecRefusalV1::Extent
            );
        }
        if n != 512 {
            assert_eq!(decode_usage_v1(&input[..n]), Err(CodecRefusalV1::Extent));
        }
        if n != 256 {
            assert_eq!(
                decode_failure_scalar_v1(&input[..n]),
                Err(CodecRefusalV1::Extent)
            );
        }
    }
}
#[test]
fn full_and_scalar_refusal_preserves_caller_bytes_and_originals() {
    let zero = [0; 32];
    let opaque = [77; 32];
    let u = usage();
    for code in ["","bad\ncode","bad\0code","\u{7f}","é", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"] {
        let mut f=failure();f.code=code;let original=f;
        let mut scalar=[0xa5;256];let mut output=[0x3c;2048];
        assert!(encode_failure_scalar_v1(&f,&mut scalar).is_err());assert_eq!(scalar,[0xa5;256]);
        assert!(encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&u),references:references(1,1,&zero,&opaque)},&mut output).is_err());
        assert_eq!(output,[0x3c;2048]);assert_eq!(f,original);
    }
    for (tag, len, digest) in [
        (0, 1, &zero),
        (0, 0, &opaque),
        (1, 0, &zero),
        (1, 65537, &zero),
        (8, u64::MAX, &opaque),
        (9, 1, &opaque),
        (u64::MAX, 1, &opaque),
    ] {
        let f = failure();
        let original = f;
        let mut output = [0x7e; 2048];
        let mut refs = references(tag, len, &zero, &opaque);
        refs.constructor_digest = digest;
        assert!(encode_result_v1(
            ResultObservationV1 {
                failure: Some(&f),
                final_consuming: Some(&u),
                references: refs
            },
            &mut output
        )
        .is_err());
        assert_eq!(output, [0x7e; 2048]);
        assert_eq!(f, original);
    }
}
#[test]
fn raw_zero_length_and_arbitrary_digests_are_required_unverified_data() {
    for len in [0, 1, u64::MAX] {
        for digest in [[0; 32], [255; 32], [0x42; 32]] {
            for tag in 0..=8 {
                let zero = [0; 32];
                let mut refs = references(tag, if tag == 0 { 0 } else { 1 }, &zero, &digest);
                refs.raw_original_bytes = len;
                refs.raw_original_digest = &digest;
                refs.session_digest = &digest;
                refs.typed_result_schema_digest = &digest;
                refs.writer_digest = &digest;
                let mut raw = [0x55; 2048];
                encode_result_v1(
                    ResultObservationV1 {
                        failure: None,
                        final_consuming: None,
                        references: refs,
                    },
                    &mut raw,
                )
                .unwrap();
                let d = decode_result_v1(&raw).unwrap();
                assert_eq!(d.references(), &refs);
                assert!(d.failure_scalars().is_none());
            }
        }
    }
}
#[test]
fn full_header_magic_version_length_and_form_are_exact() {
    let zero = [0; 32];
    let mut good = [0; 2048];
    encode_result_v1(
        ResultObservationV1 {
            failure: None,
            final_consuming: None,
            references: references(0, 0, &zero, &zero),
        },
        &mut good,
    )
    .unwrap();
    for i in 0..8 {
        let mut bad = good;
        bad[i] ^= 1;
        assert!(decode_result_v1(&bad).is_err());
    }
    for (word, valid) in [(1, 1u64), (2, 2048), (3, 1)] {
        for value in [0, valid + 1, u64::MAX] {
            let mut bad = good;
            bad[word * 8..word * 8 + 8].copy_from_slice(&value.to_le_bytes());
            assert!(decode_result_v1(&bad).is_err());
        }
    }
}
#[test]
fn decoded_view_borrows_input_without_fabricating_static_failure() {
    let mut f = failure();
    f.code = "unknown printable code";
    let zero = [0; 32];
    let mut raw = [0; 2048];
    encode_result_v1(
        ResultObservationV1 {
            failure: Some(&f),
            final_consuming: None,
            references: references(0, 0, &zero, &zero),
        },
        &mut raw,
    )
    .unwrap();
    let d = decode_result_v1(&raw).unwrap();
    assert_eq!(d.encoded().as_ptr(), raw.as_ptr());
    assert_eq!(
        d.failure_scalars().unwrap().code().as_ptr(),
        raw[384..].as_ptr()
    );
    assert_eq!(
        d.references().raw_original_digest.as_ptr(),
        raw[64..].as_ptr()
    );
    assert_eq!(f.code, "unknown printable code");
}
#[test]
fn codec_data_layouts_are_reported_separately_from_owner_inventory() {
    macro_rules! show {($($t:ty),* $(,)?)=>{$(println!("CODEC_DATA\t{}\t{}\t{}",stringify!($t),std::mem::size_of::<$t>(),std::mem::align_of::<$t>());)*};}
    show!(
        CodecRefusalV1,
        UnverifiedFailureScalarsV1<'static>,
        UnverifiedResultReferencesV1<'static>,
        ResultObservationV1<'static>,
        UnverifiedResultViewV1<'static>,
        [u64; 64],
        Option<[u64; 64]>,
        [u64; 16],
        Option<[u64; 16]>,
        [u8; 512],
        [u8; 256],
        [u8; 2048]
    );
}
