#[test]
fn framepin_campaign_recursive_frame_and_pin_boundaries() {
    for cap in [63, 64, 65, 127, 128] {
        let mut owner = owner_with(&Function::empty(), SwiftRunBudget { frames: cap, ..SwiftRunBudget::default() });
        assert_eq!(owner.state.as_ref().unwrap().frames.capacity(), cap);
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        for _ in 0..cap { phase.enter(34).unwrap(); }
        let ids = pin_ids(&phase);
        assert_eq!(ids.len(), cap);
        for (slot, id) in ids.iter().enumerate() { assert_eq!(id.2, slot); }
        assert!(ids.windows(2).all(|w| w[0].1 == w[1].1 && w[0].3 != w[1].3));
        let failure = phase.enter(34).unwrap_err();
        assert_eq!(failure.kind, SwiftRunFailureKind::FrameLimit);
        assert_eq!((failure.attempted, failure.limit), ((cap + 1) as u64, cap as u64));
        assert_eq!(pin_ids(&phase), ids);
        let report = phase.drain();
        assert_eq!(report.retained_frames, 0);
        complete_ok(phase, preparation);
        retire(owner);
    }
    for cap in [63, 64, 65, 127] {
        let mut owner = owner_with(&Function::empty(), SwiftRunBudget { active_pins: cap, ..SwiftRunBudget::default() });
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        for _ in 0..cap { phase.enter(34).unwrap(); }
        let ids = pin_ids(&phase);
        assert_eq!(phase.enter(34).unwrap_err().kind, SwiftRunFailureKind::PinLimit);
        assert_eq!(pin_ids(&phase), ids);
        phase.drain();
        complete_ok(phase, preparation);
        retire(owner);
    }
    println!("FRAMEPIN recursive_frame_caps=63,64,65,127,128 recursive_pin_caps=63,64,65,127 cleanup_zero=true");
}

#[test]
fn framepin_campaign_deep_entry_rollback_preserves_callers() {
    for depth in [63, 64, 127] {
        let mut owner = owner();
        let mut preparation = Some(owner.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        for _ in 0..depth { phase.enter(34).unwrap(); }
        let ids = pin_ids(&phase);
        hooks(Hooks { predebit_resource: Some(2), predebit_ordinal: 0, ..Hooks::default() });
        assert!(phase.enter(34).is_err());
        hooks(Hooks::default());
        assert_eq!(pin_ids(&phase), ids);
        assert_eq!(phase.phase.parts.cache.usage().active_pins, depth);
        assert!(phase.cleanup.entry.is_none());
        phase.drain();
        complete_ok(phase, preparation);
        retire(owner);
    }
    println!("FRAMEPIN deep_entry_rollback_depths=63,64,127 caller_pins_preserved=true cleanup_zero=true");
}

#[test]
fn framepin_campaign_retained_128_frames_restore_and_consume() {
    let mut foreign = owner();
    let mut owner = owner();
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    for _ in 0..128 { phase.enter(34).unwrap(); }
    let ids = pin_ids(&phase);
    for slot in [63, 64, 127] { assert_eq!(ids[slot].2, slot); }
    let foreign_header = super::super::super::cache::inspection::replace_header(foreign.cache.as_mut().unwrap(), None);
    let original = super::super::super::cache::inspection::replace_header(phase.phase.parts.cache, foreign_header);
    let before = phase.phase.operation.control.usage(None).reservations;
    let report = phase.drain();
    assert_eq!(report.retained_frames, 128);
    assert_eq!(pin_ids(&phase), ids);
    assert_eq!((report.live.frames.current, report.live.active_pins.current), (128, 128));
    assert_eq!(report.usage.reservations.state.current, before.state.current);
    let foreign_header = super::super::super::cache::inspection::replace_header(phase.phase.parts.cache, original);
    super::super::super::cache::inspection::replace_header(foreign.cache.as_mut().unwrap(), foreign_header);
    assert!(matches!(complete(phase, preparation), FrameCompletion::Retained(_)));
    drain_complete(&mut owner);
    retire(owner);
    retire(foreign);
    println!("FRAMEPIN retained_actual_frames=128 release_slots=63,64,127 original_tickets_restored=true cleanup_zero=true");
}

#[test]
fn framepin_campaign_frame_arena_geometry() {
    let mut rows = Vec::new();
    for frames in [64, 128] {
        let owner = owner_with(&Function::empty(), SwiftRunBudget { frames, ..SwiftRunBudget::default() });
        let u = usage(&owner);
        assert_eq!(owner.state.as_ref().unwrap().frames.capacity(), frames);
        rows.push((u.reservations.state.current, u.execution_work, u.reservations.live_tickets));
        retire(owner);
    }
    assert_eq!(size_of::<SwiftFrame>(), 64); // selected x86_64 CI target
    assert_eq!(rows[1].0 - rows[0].0, 64 * size_of::<SwiftFrame>());
    assert_eq!(rows[1].1, rows[0].1); // uninitialized reserved frame storage
    assert_eq!(rows[1].2, rows[0].2); // same arena ticket, no per-frame tickets
    println!("FRAMEPIN frame_payload_delta=4096 frame_size=64 frame_construction_work_delta=0 additional_tickets=0");
}
