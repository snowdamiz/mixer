//! Independently chosen assertions over the producer's original-owner fixture
//! and authority-preserving fault leaves. Compiled only in archived test source.
use super::*;

#[test]
fn independent_af_every_four_frame_release_mask_retains_same_actual_pins() {
    for mask in 0..16u64 {
        let mut foreign = owner();
        let mut actual = owner();
        install_foreign(&mut foreign);
        let mut preparation = Some(actual.prepare_frames(cursor()));
        let mut phase = preparation.take().unwrap().unwrap();
        for function in [34, 36, 34, 36] { phase.enter(function).unwrap(); }
        let ids = pin_ids(&phase);
        let arena = phase.phase.parts.frames.as_ptr();
        let initial = phase.phase.parts.cache.usage();
        hooks(Hooks { release_mask: mask, ..Hooks::default() });
        let report = phase.drain();
        let expected: Vec<_> = ids.iter().enumerate().filter(|(i, _)| mask & (1 << (3 - i)) != 0).map(|(_, id)| *id).collect();
        assert_eq!(pin_ids(&phase), expected, "mask={mask}");
        assert_eq!(phase.phase.parts.frames.as_ptr(), arena);
        assert_eq!(report.retained_frames, mask.count_ones() as usize);
        assert_eq!(report.live.frames.current, report.retained_frames);
        assert_eq!(report.live.active_pins.current, report.retained_frames);
        assert_eq!(report.cache.resident_bytes, initial.resident_bytes);
        assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 4);
        assert_eq!(HOOKS.with(|slot| slot.get().release_order[..4].to_vec()), vec![36, 34, 36, 34]);
        phase.drain();
        assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 4, "completed pass retried a pin");
        let result = complete(phase, preparation);
        assert!(if mask == 0 { matches!(result, FrameCompletion::Completed) } else { matches!(result, FrameCompletion::Retained(_)) });
        restore_foreign(&mut foreign);
        if mask != 0 { drain_complete(&mut actual); }
        retire(actual); retire(foreign);
    }
}

#[test]
fn independent_af_guard_and_retained_frame_resume_reject_enter_intact() {
    let mut foreign = owner();
    let mut actual = owner();
    install_foreign(&mut foreign);
    let mut preparation = Some(actual.prepare_frames(cursor()));
    let mut phase = preparation.take().unwrap().unwrap();
    for function in [34, 36, 34] { phase.enter(function).unwrap(); }
    let ids = pin_ids(&phase);
    let admitted = phase.cleanup.bound.unwrap().admitted;
    hooks(Hooks { reject_cache_completion: true, release_mask: 0b1011, ..Hooks::default() });
    let failure = phase.enter(36).unwrap_err();
    let guard = phase.cleanup.entry.as_ref().unwrap();
    let guard_id = (guard.pin.as_ref().unwrap().owner(), guard.pin.as_ref().unwrap().slot(), guard.pin.as_ref().unwrap().nonce());
    assert_eq!(phase.cleanup.nested_restore, Some(admitted));
    assert!(phase.phase.operation.control.usage(None).reservations.construction.current > admitted);
    assert_eq!(phase.enter(34).unwrap_err().code, failure.code);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 1);
    let report = phase.drain();
    assert_eq!(pin_ids(&phase), vec![ids[0], ids[2]]);
    assert!(report.retained_entry);
    assert_eq!(report.live.active_pins.current, 3);
    assert_eq!(report.live.frames.current, 2);
    assert_eq!(report.nested_restore, None);
    assert_eq!(report.usage.reservations.construction.current, admitted);
    assert!(matches!(complete(phase, preparation), FrameCompletion::Retained(_)));

    hooks(Hooks { release_mask: 1, ..Hooks::default() });
    let mut preparation = Some(actual.resume_frame_cleanup());
    let mut phase = preparation.take().unwrap().unwrap();
    assert!(!phase.cleanup.entry_attempted);
    assert_eq!(phase.enter(34).unwrap_err().code, failure.code);
    assert_eq!(phase.finish().unwrap_err().code, failure.code);
    assert!(!phase.cleanup.entry_attempted, "rejected enter attempted retained guard");
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 0);
    let guard = phase.cleanup.entry.as_ref().unwrap();
    assert_eq!((guard.pin.as_ref().unwrap().owner(), guard.pin.as_ref().unwrap().slot(), guard.pin.as_ref().unwrap().nonce()), guard_id);
    assert_eq!((guard.values_debited, guard.controls_debited, guard.frame_debited), (0, 0, false));
    let report = phase.drain();
    assert!(report.retained_entry);
    assert_eq!(report.retained_frames, 0);
    assert_eq!(report.live.active_pins.current, 1);
    assert_eq!(HOOKS.with(|slot| slot.get().release_seen), 3);
    assert!(matches!(complete(phase, preparation), FrameCompletion::Retained(_)));
    let mut owned = Some(actual);
    assert!(SwiftReactorInstance::cleanup_owned(&mut owned).is_err());
    actual = owned.take().expect("retained guard must preserve actual owner");
    restore_foreign(&mut foreign);
    drain_complete(&mut actual);
    retire(actual); retire(foreign);
}
