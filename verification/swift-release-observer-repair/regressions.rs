
// Independently authored observer regression over actual original owners,
// entries, finishes, pins and consuming cleanup. No reactor/engine substitute.
fn observer_original_entry_finish(owner: &mut SwiftReactorInstance) {
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    assert!(matches!(phase.finish().unwrap(), FrameReturn::Outermost(None)));
    complete_ok(phase, preparation);
    let live = usage(owner).live;
    assert_eq!(live.active_pins.current + live.frames.current + live.values.current + live.controls.current, 0);
    assert_eq!(owner.cache.as_ref().unwrap().usage().active_pins, 0);
    assert!(owner.state.as_ref().unwrap().frame_cleanup.is_empty());
}

#[test]
fn swift_release_observer_default_allows_130_actual_serial_releases() {
    let mut owner = owner();
    for n in 1..=130 {
        observer_original_entry_finish(&mut owner);
        if n == 64 || n == 130 { println!("OBSERVER default actual_completed_releases={n}"); }
    }
    HOOKS.with(|slot| {
        let observed = slot.get();
        assert_eq!(observed.release_mask, 0);
        assert_eq!(observed.release_seen, 0);
        assert_eq!(observed.release_order, [0; 64]);
    });
    retire(owner);
}

#[test]
fn swift_release_observer_enabled_bit63_retains_real_pin_then_zero_reset_cleans() {
    let mut foreign = owner();
    let mut owner = owner();
    install_foreign(&mut foreign);
    hooks(Hooks { release_mask: 1u64 << 63, ..Hooks::default() });
    for _ in 0..63 { observer_original_entry_finish(&mut owner); }
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 63);
    let mut preparation = Some(owner.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    phase.enter(34).unwrap();
    let failure = phase.finish().unwrap_err();
    assert_eq!(failure.code, "swift_run_reservation_owner");
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 64);
    assert_eq!(HOOKS.with(|slot| slot.get().release_order), [34; 64]);
    assert_eq!(phase.phase.parts.cache.usage().active_pins, 1);
    assert_eq!(phase.phase.parts.frames.len(), 1);
    assert!(matches!(complete(phase, preparation), FrameCompletion::Retained(_)));
    restore_foreign(&mut foreign); // Original helper resets actual hook state.
    drain_complete(&mut owner);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 0);
    assert!(matches!(owner.lifecycle, Lifecycle::Terminal));
    println!("OBSERVER enabled record_count=64 bit63_rejected=true original_pin_drained=true zero_reset=true");
    retire(owner);
    retire(foreign);
}

#[test]
fn swift_release_observer_zero_reset_after_enabled_recording_allows_130_releases() {
    let mut owner = owner();
    hooks(Hooks { release_mask: 1u64 << 63, ..Hooks::default() });
    for _ in 0..17 { observer_original_entry_finish(&mut owner); }
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 17);
    hooks(Hooks::default());
    for _ in 0..130 { observer_original_entry_finish(&mut owner); }
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 0);
    assert_eq!(HOOKS.with(|slot| slot.get().release_order), [0; 64]);
    println!("OBSERVER reset earlier_enabled_records=17 later_default_releases=130 no_recording=true");
    retire(owner);
}
