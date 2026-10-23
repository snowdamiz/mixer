#![cfg(feature = "experimental-capability-native")]
//! Original isolated allocator probe: no deployment/RSS/physical heap claim.
use mixer_vm::*;
use std::{ptr, sync::atomic::Ordering::SeqCst};
#[path = "common/legacy_allocation_observer.rs"]
mod allocation_observer;
#[path = "capability_ffi/fixture.rs"]
mod fixture;
use allocation_observer::{Lane, Observed, Operation, CALLS, LARGEST, LIVE, MAX_SLOTS, PEAK};
#[global_allocator]
static ALLOCATOR: Observed = Observed;
fn end(operation: Operation<'_>) -> (usize, usize, usize, usize) {
    let base = operation.finish();
    (
        CALLS.load(SeqCst),
        LIVE.load(SeqCst).saturating_sub(base),
        PEAK.load(SeqCst).saturating_sub(base),
        LARGEST.load(SeqCst),
    )
}
#[test]
fn validation_has_no_instance_memory_and_post_allocation_failure_remains_retryable() {
    let observer = Lane::new();
    unsafe {
        let source = fixture::wasm_with_memory(32);
        let mut r = MixerVmReport::default();
        let base = observer.begin(0, 0);
        assert_eq!(
            mixer_vm_capability_validate_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut r
            ),
            0
        );
        let validation = end(base);
        assert_eq!(validation.1, 0);
        assert!(validation.2 < 65536);
        assert!(validation.3 < 65536);
        println!("native validate-only requested(calls,retained,logical_peak,largest)={validation:?};32-page module not instantiated");
        let base = observer.begin(0, 0);
        let mut handle = 0;
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut handle,
                &mut r
            ),
            0
        );
        let construction = end(base);
        assert_eq!(construction.3, 32 * 65536);
        assert!(construction.1 >= 32 * 65536);
        println!("native create32pages requested(calls,retained,logical_peak,largest)={construction:?};includes shared registry first-use overhead if any");
        assert_eq!(mixer_vm_capability_session_close_v1(handle, &mut r), 0);
        let source = fixture::wasm();
        let mut handle = 0;
        assert_eq!(
            mixer_vm_capability_session_create_v1(
                source.as_ptr(),
                source.len(),
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                &mut handle,
                &mut r
            ),
            0
        );
        assert_eq!(mixer_vm_capability_session_startup_v1(handle, &mut r), 0);
        assert_eq!(mixer_vm_capability_session_enable_v1(handle, &mut r), 0);
        let args = [
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 0,
            },
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 4,
            },
            MixerVmValue {
                value_type: 1,
                reserved: 0,
                value: 32,
            },
        ];
        assert_eq!(
            mixer_vm_capability_session_invoke_v1(
                handle,
                b"get".as_ptr(),
                3,
                args.as_ptr(),
                3,
                &mut r
            ),
            0
        );
        let mut message = MixerVmCapabilityMessageV1::default();
        let mut output = [0u8; 4];
        assert_eq!(
            mixer_vm_capability_take_v1(handle, &mut message, output.as_mut_ptr(), 4, &mut r),
            0
        );
        let payload = vec![7u8; 1024];
        let mut result = MixerVmCapabilityResultV1::default();
        let base = observer.begin(0, 1);
        assert_eq!(
            mixer_vm_capability_post_v1(
                handle,
                message.token,
                2,
                payload.as_ptr(),
                payload.len(),
                &mut result,
                &mut r
            ),
            2
        );
        let refusal = end(base);
        assert_eq!(refusal, (1, 0, 0, 1024));
        assert_eq!(r.status, 2);
        assert_eq!(result.kind, 0);
        let base = observer.begin(0, 0);
        assert_eq!(
            mixer_vm_capability_post_v1(
                handle,
                message.token,
                2,
                payload.as_ptr(),
                payload.len(),
                &mut result,
                &mut r
            ),
            0
        );
        assert_eq!(end(base), (1, 1024, 1024, 1024));
        println!("native post allocation refusal={refusal:?};retry succeeded;no quarantine/terminal/exit fabricated");
        assert_eq!(mixer_vm_capability_session_close_v1(handle, &mut r), 0);
        let base = observer.begin(0, 1);
        assert_eq!(
            mixer_vm_capability_ack_exit_v1(handle, message.token, 2, &mut result, &mut r),
            0
        );
        assert_eq!(end(base).0, 0);
        let mut sentinel = vec![0xa5u8; std::mem::size_of::<MixerVmReport>() + 1];
        let report = sentinel.as_mut_ptr().add(1).cast::<MixerVmReport>();
        let base = observer.begin(0, 1);
        assert_eq!(
            mixer_vm_capability_validate_v1(
                report.cast(),
                8,
                b"start".as_ptr(),
                5,
                ptr::null(),
                ptr::null(),
                report
            ),
            3
        );
        assert_eq!(end(base), (0, 0, 0, 0));
        assert!(sentinel.iter().all(|b| *b == 0xa5));
    }
    println!(
        "observer maximum ownership slots={} capacity=4096 background_noise={}",
        MAX_SLOTS.load(SeqCst),
        std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some()
    );
}
