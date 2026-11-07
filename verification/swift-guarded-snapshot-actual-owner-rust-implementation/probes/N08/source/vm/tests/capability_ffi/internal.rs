use super::*;
use std::mem::{align_of, offset_of, size_of};
#[test]
fn fixed_lp64_layouts_match_every_frozen_offset() {
    assert_eq!(size_of::<usize>(), 8);
    assert_eq!(
        (
            size_of::<MixerVmCapabilityLimitsV1>(),
            align_of::<MixerVmCapabilityLimitsV1>()
        ),
        (32, 8)
    );
    assert_eq!(
        [
            offset_of!(MixerVmCapabilityLimitsV1, struct_size),
            offset_of!(MixerVmCapabilityLimitsV1, abi_version),
            offset_of!(MixerVmCapabilityLimitsV1, maximum_requests),
            offset_of!(MixerVmCapabilityLimitsV1, timeout_milliseconds),
            offset_of!(MixerVmCapabilityLimitsV1, turn_milliseconds),
            offset_of!(MixerVmCapabilityLimitsV1, reserved),
            offset_of!(MixerVmCapabilityLimitsV1, reservation_bytes)
        ],
        [0, 4, 8, 12, 16, 20, 24]
    );
    assert_eq!(
        (
            size_of::<MixerVmCapabilityMessageV1>(),
            align_of::<MixerVmCapabilityMessageV1>()
        ),
        (40, 8)
    );
    assert_eq!(
        [
            offset_of!(MixerVmCapabilityMessageV1, struct_size),
            offset_of!(MixerVmCapabilityMessageV1, abi_version),
            offset_of!(MixerVmCapabilityMessageV1, kind),
            offset_of!(MixerVmCapabilityMessageV1, operation),
            offset_of!(MixerVmCapabilityMessageV1, token),
            offset_of!(MixerVmCapabilityMessageV1, remaining_milliseconds),
            offset_of!(MixerVmCapabilityMessageV1, payload_length),
            offset_of!(MixerVmCapabilityMessageV1, reserved)
        ],
        [0, 4, 8, 12, 16, 24, 28, 32]
    );
    assert_eq!(
        (
            size_of::<MixerVmCapabilityResultV1>(),
            align_of::<MixerVmCapabilityResultV1>()
        ),
        (24, 8)
    );
    assert_eq!(
        [
            offset_of!(MixerVmCapabilityResultV1, struct_size),
            offset_of!(MixerVmCapabilityResultV1, abi_version),
            offset_of!(MixerVmCapabilityResultV1, kind),
            offset_of!(MixerVmCapabilityResultV1, remaining_milliseconds),
            offset_of!(MixerVmCapabilityResultV1, reserved)
        ],
        [0, 4, 8, 12, 16]
    );
}
#[test]
fn all_preflight_plans_reject_report_aliases_without_accessing_storage() {
    let report = 4096usize as *mut crate::MixerVmReport;
    assert!(preflight::validate(
        report.cast(),
        10,
        1024usize as *const u8,
        1,
        std::ptr::null(),
        std::ptr::null(),
        report
    )
    .is_err());
    assert!(preflight::create(
        32usize as *const u8,
        10,
        1024usize as *const u8,
        1,
        std::ptr::null(),
        std::ptr::null(),
        report.cast(),
        report
    )
    .is_err());
    assert!(preflight::invoke(1024usize as *const u8, 1, report.cast(), 1, report).is_err());
    assert!(preflight::wake(report.cast(), report).is_err());
    assert!(preflight::read_memory(report.cast(), 1, report).is_err());
    assert!(preflight::write_memory(report.cast(), 1, report).is_err());
    assert!(preflight::take(32usize as *mut _, report.cast(), 1, report).is_err());
    assert!(preflight::post(report.cast(), 1, 32usize as *mut _, report).is_err());
    assert!(preflight::result(report.cast(), report).is_err());
    assert!(preflight::simple(std::ptr::null_mut()).is_err());
}
#[test]
fn optional_limits_and_empty_buffers_are_numeric_empty_ranges() {
    let r = 1024usize as *mut crate::MixerVmReport;
    assert!(preflight::validate(
        std::ptr::null(),
        0,
        std::ptr::null(),
        0,
        std::ptr::null(),
        std::ptr::null(),
        r
    )
    .is_ok());
    assert!(preflight::invoke(std::ptr::null(), 0, std::ptr::null(), 0, r).is_ok());
    assert!(preflight::take(4096usize as *mut _, r.cast(), 0, r).is_ok());
    assert!(preflight::result(usize::MAX as *mut _, r).is_err());
    assert!(preflight::invoke(
        4096usize as *const u8,
        1,
        32usize as *const _,
        usize::MAX,
        r
    )
    .is_err());
}
#[test]
fn create_preflight_covers_every_input_output_alias_pair() {
    let base = [64usize, 128, 256, 512, 768, 1024];
    let mut cases = 0;
    for a in 0..6 {
        for b in a + 1..6 {
            let mut address = base;
            address[b] = address[a];
            let result = preflight::create(
                address[0] as *const u8,
                8,
                address[1] as *const u8,
                5,
                address[2] as *const crate::MixerVmLimits,
                address[3] as *const MixerVmCapabilityLimitsV1,
                address[4] as *mut u64,
                address[5] as *mut crate::MixerVmReport,
            );
            assert_eq!(result.is_err(), b >= 4, "pair{a}/{b}");
            cases += 1;
        }
    }
    assert_eq!(cases, 15);
}
