#![cfg(feature = "experimental-capability-native")]
//! Original caller-thread requested-allocation probe; no process heap/RSS claim.
use mixer_vm::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    cell::Cell,
    ptr,
    sync::Mutex,
};
#[path = "guest_ui/fixture.rs"]
mod fixture;
static SERIAL: Mutex<()> = Mutex::new(());
#[derive(Clone, Copy, Default, Debug)]
struct Counts {
    enabled: bool,
    calls: usize,
    live: isize,
    peak: usize,
    largest: usize,
}
thread_local! { static COUNTS: Cell<Counts> = const { Cell::new(Counts { enabled: false, calls: 0, live: 0, peak: 0, largest: 0 }) }; }
struct Probe;
fn record(add: usize, remove: usize, allocation: bool) {
    let _ = COUNTS.try_with(|cell| {
        let mut c = cell.get();
        if c.enabled {
            c.calls += usize::from(allocation);
            c.live += add as isize - remove as isize;
            c.peak = c.peak.max(c.live.max(0) as usize);
            c.largest = c.largest.max(add);
            cell.set(c);
        }
    });
}
unsafe impl GlobalAlloc for Probe {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(l) };
        if !p.is_null() {
            record(l.size(), 0, true);
        }
        p
    }
    unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc_zeroed(l) };
        if !p.is_null() {
            record(l.size(), 0, true);
        }
        p
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        let q = unsafe { System.realloc(p, l, n) };
        if !q.is_null() {
            record(n, l.size(), true);
        }
        q
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        record(0, l.size(), false);
        unsafe { System.dealloc(p, l) };
    }
}
#[global_allocator]
static ALLOCATOR: Probe = Probe;
fn measured<F: FnOnce() -> u32>(f: F) -> (u32, Counts) {
    COUNTS.with(|c| {
        c.set(Counts {
            enabled: true,
            ..Counts::default()
        })
    });
    let status = f();
    let counts = COUNTS.with(|c| {
        let v = c.get();
        c.set(Counts::default());
        v
    });
    (status, counts)
}
fn measured_validation(bytes: &[u8]) -> (u32, MixerVmReport, Counts) {
    let mut r = MixerVmReport::default();
    let (status, validation) = measured(|| unsafe {
        mixer_vm_capability_guest_ui_validate_v1(
            bytes.as_ptr(),
            bytes.len(),
            ptr::null(),
            ptr::null(),
            &mut r,
        )
    });
    (status, r, validation)
}

#[test]
fn validation_has_no_instance_memory_or_retained_owner_and_creation_probe_detects_memory() {
    let _serial = SERIAL.lock().unwrap();
    let p = fixture::Program {
        memory: Some(vec![1, 1, 32, 32]),
        ..fixture::Program::default()
    };
    let bytes = p.bytes();
    let (status, mut r, validation) = measured_validation(&bytes);
    assert_eq!(status, 0);
    assert_eq!(validation.live, 0);
    assert!(validation.largest < 65536 && validation.peak < 65536);
    assert_eq!((r.fuel_used, r.host_calls_used), (0, 0));
    let mut handle = 0;
    let (status, creation) = measured(|| unsafe {
        mixer_vm_capability_session_create_v1(
            bytes.as_ptr(),
            bytes.len(),
            fixture::NAMES[0].as_ptr(),
            fixture::NAMES[0].len(),
            ptr::null(),
            ptr::null(),
            &mut handle,
            &mut r,
        )
    });
    assert_eq!(status, 0);
    assert_ne!(handle, 0);
    assert_eq!(creation.largest, 32 * 65536);
    assert!(creation.live >= 32 * 65536);
    assert_eq!(
        unsafe { mixer_vm_capability_session_close_v1(handle, &mut r) },
        0
    );
    println!("guest-UI native validation requested counts={validation:?}; construction positive-control={creation:?}; caller-thread requested allocation sizes only, no heap/RSS claim");
}

#[test]
fn guest_ui_v1_export_name_mutations_refuse_without_instantiation() {
    let _serial = SERIAL.lock().unwrap();
    let seed = fixture::Program::default().bytes();
    let (status, mut report, _) = measured_validation(&seed);
    assert_eq!((status, report.status), (0, 0));
    println!("Guest UI V1 seed (hex): {seed:02x?}");

    let mut candidate = seed.clone();
    for name in fixture::NAMES {
        let start = seed
            .windows(name.len())
            .position(|bytes| bytes == name.as_bytes())
            .expect("required export name in owned seed");
        let mut max_peak = 0;
        for offset in start..start + name.len() {
            for bit in 0..8 {
                candidate[offset] ^= 1 << bit;
                let (status, report, counts) = measured_validation(&candidate);
                candidate[offset] = seed[offset];

                let case = format_args!("{name} at seed byte {offset}, bit {bit}");
                assert_eq!(
                    (status, report.status, report.abi_version),
                    (1, 1, 1),
                    "{case}"
                );
                assert_eq!(
                    (
                        report.fuel_used,
                        report.host_calls_used,
                        report.value_type,
                        report.value
                    ),
                    (0, 0, 0, 0),
                    "{case}"
                );
                let code = report.code.split(|&byte| byte == 0).next().unwrap();
                if bit == 7 {
                    assert_eq!(code, b"malformed", "{case}");
                } else {
                    assert_eq!(code, b"capability_export", "{case}");
                    assert_eq!((report.function, report.offset), (u32::MAX, 0), "{case}");
                }
                assert_eq!(counts.live, 0, "{case}: {counts:?}");
                assert!(
                    counts.largest < 65_536 && counts.peak < 65_536,
                    "{case}: {counts:?}"
                );
                max_peak = max_peak.max(counts.peak);
            }
        }
        println!(
            "{name}: start={start}, length={}, capability_export={}, malformed={}, max_peak={max_peak}",
            name.len(),
            name.len() * 7,
            name.len()
        );
    }

    // Fill the shared registry to its public ABI capacity after all refusals.
    let mut handles = [0; 16];
    let startup = fixture::NAMES[0];
    for handle in &mut handles {
        let status = unsafe {
            mixer_vm_capability_session_create_v1(
                seed.as_ptr(),
                seed.len(),
                startup.as_ptr(),
                startup.len(),
                ptr::null(),
                ptr::null(),
                handle,
                &mut report,
            )
        };
        assert_eq!(status, 0, "registry capacity after V1 refusals");
        assert_ne!(*handle, 0);
    }
    for handle in handles {
        assert_eq!(
            unsafe { mixer_vm_capability_session_close_v1(handle, &mut report) },
            0
        );
    }
    println!("Guest UI V1 registry after refusals: 16 sessions created and closed");
}
