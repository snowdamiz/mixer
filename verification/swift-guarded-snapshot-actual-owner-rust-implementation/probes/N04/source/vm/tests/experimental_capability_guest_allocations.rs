#![cfg(feature = "experimental-capability-guest")]
//! Isolated allocator observations; requested bytes, not allocator overhead/RSS.
mod common;
use common::{section, u32leb};
use mixer_vm::{
    experimental_capability as mb, experimental_capability_guest::*, Limits, Profile, Value,
};
#[path = "common/legacy_allocation_observer.rs"]
mod allocation_observer;
use allocation_observer::{Lane, Observed, Operation, CALLS, LIVE, MAX_SLOTS, PEAK, SIZES};
use std::sync::atomic::Ordering::SeqCst;
#[global_allocator]
static ALLOCATOR: Observed = Observed;
fn end(operation: Operation<'_>) -> (usize, usize, usize) {
    let base = operation.finish();
    (
        CALLS.load(SeqCst),
        LIVE.load(SeqCst).saturating_sub(base),
        PEAK.load(SeqCst).saturating_sub(base),
    )
}
fn name(n: &str) -> Vec<u8> {
    let mut b = u32leb(n.len() as u32);
    b.extend(n.as_bytes());
    b
}
// Independent minimal original module: three imported functions and two void
// defined startup/wake functions; exported imports avoid interpreter frame noise.
fn wasm() -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    section(
        &mut m,
        1,
        vec![
            4, 0x60, 3, 0x7f, 0x7f, 0x7f, 1, 0x7f, 0x60, 1, 0x7e, 1, 0x7f, 0x60, 4, 0x7e, 0x7f,
            0x7f, 0x7f, 1, 0x7f, 0x60, 0, 0,
        ],
    );
    let mut imports = vec![3];
    for (i, n) in ["storage_get", "cancel", "poll"].iter().enumerate() {
        imports.extend(name(IMPORT_MODULE));
        imports.extend(name(n));
        imports.extend([0, i as u8]);
    }
    section(&mut m, 2, imports);
    section(&mut m, 3, vec![2, 3, 3]);
    section(&mut m, 5, vec![1, 1, 9, 9]);
    let mut exports = vec![5];
    for (i, n) in ["get", "cancel", "poll", "start", WAKE_EXPORT]
        .iter()
        .enumerate()
    {
        exports.extend(name(n));
        exports.extend([0, i as u8]);
    }
    section(&mut m, 7, exports);
    section(&mut m, 10, vec![2, 2, 0, 0x0b, 2, 0, 0x0b]);
    m
}
const TOKEN: usize = mb::MAX_PAYLOAD_BYTES;
const LENGTH: i32 = (TOKEN + 8) as i32;
fn construct(w: &[u8]) -> CapabilityGuest {
    CapabilityGuest::new(
        w,
        Limits {
            profile: Profile::TableMemoryV3,
            ..Limits::default()
        },
        mb::Limits::default(),
        GuestLimits::default(),
        "start",
    )
    .unwrap()
}
fn get(g: &mut CapabilityGuest, len: usize) -> i32 {
    match g
        .invoke(
            "get",
            &[
                Value::I32(0),
                Value::I32(len as i32),
                Value::I32(TOKEN as i32),
            ],
        )
        .unwrap()
    {
        Some(Value::I32(n)) => n,
        _ => panic!("status"),
    }
}
fn token(g: &CapabilityGuest) -> u64 {
    u64::from_le_bytes(g.memory()[TOKEN..TOKEN + 8].try_into().unwrap())
}
fn take(p: &CapabilityPort, output: &mut [u8]) -> DispatchLease {
    match p.take(output).unwrap() {
        NativeTake::Call { lease, .. } => lease,
        _ => panic!("expected call"),
    }
}
#[test]
fn guest_allocations_are_measured_and_payload_failures_are_atomic() {
    let observer = Lane::new();
    let w = wasm();
    if let Some(size) = std::env::var_os("MIXER_GUEST_ARC_OOM_SIZE") {
        let operation = observer.begin(0, 0);
        allocation_observer::fail_size(size.to_str().unwrap().parse().unwrap());
        let _ = construct(&w);
        operation.finish();
        return;
    }
    let base = observer.begin(0, 0);
    let mut g = construct(&w);
    let construction = end(base);
    let sizes: Vec<_> = SIZES
        .iter()
        .take(construction.0.min(128))
        .map(|x| x.load(SeqCst))
        .collect();
    println!("constructor requested allocation events={sizes:?}; (calls,live,peak)={construction:?}; fixture bytes={}",w.len());
    // On this host the Shared payload is1000B, with a16B Arc header. The
    // observation is explicitly platform-specific, not a portable ABI promise.
    if sizes.contains(&1016) {
        let child = std::process::Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "guest_allocations_are_measured_and_payload_failures_are_atomic",
                "--nocapture",
            ])
            .env("MIXER_GUEST_ARC_OOM_SIZE", "1016")
            .output()
            .unwrap();
        assert!(!child.status.success());
        assert!(String::from_utf8_lossy(&child.stderr)
            .contains("memory allocation of 1016 bytes failed"));
        println!(
            "known Shared Arc OOM abort: status={}; stderr={}",
            child.status,
            String::from_utf8_lossy(&child.stderr).trim()
        );
    }
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    let base = observer.begin(0, 1);
    assert_eq!(
        g.invoke(
            "get",
            &[Value::I32(-1), Value::I32(1), Value::I32(TOKEN as i32)]
        )
        .unwrap(),
        Some(Value::I32(3))
    );
    assert_eq!(end(base), (0, 0, 0));
    assert_eq!(token(&g), 0);
    let before = p.usage().unwrap();
    let base = observer.begin(0, 1);
    let failure = g
        .invoke(
            "get",
            &[Value::I32(0), Value::I32(1024), Value::I32(TOKEN as i32)],
        )
        .unwrap_err();
    let failed = end(base);
    assert_eq!(failure.code, "capability_allocation");
    assert_eq!(token(&g), 0);
    assert_eq!(p.usage().unwrap().reserved_bytes, before.reserved_bytes);
    assert!(failed.0 >= 2);
    assert_eq!(SIZES[0].load(SeqCst), 1024);
    println!("fallible argument allocation refusal: {failed:?}; subsequent bounded Error String included");
    drop(failure);
    drop(g);
    drop(p);
    let mut g = construct(&w);
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    let mut output = vec![0; mb::MAX_PAYLOAD_BYTES];
    let completion = vec![7; mb::MAX_PAYLOAD_BYTES];
    let mut tokens = [0u64; mb::MAX_REQUESTS];
    let mut tickets: [Option<DispatchLease>; mb::MAX_REQUESTS] = std::array::from_fn(|_| None);
    let base = observer.begin(0, 0);
    for t in &mut tokens {
        assert_eq!(get(&mut g, mb::MAX_PAYLOAD_BYTES), 0);
        *t = token(&g);
    }
    for ticket in &mut tickets {
        let lease = take(&p, &mut output);
        p.post_trusted(&lease, &completion).unwrap();
        *ticket = Some(lease);
    }
    let occupancy = end(base);
    assert_eq!(
        occupancy,
        (16, mb::MAX_RESERVATION_BYTES, mb::MAX_RESERVATION_BYTES)
    );
    assert_eq!(p.usage().unwrap().reserved_bytes, mb::MAX_RESERVATION_BYTES);
    println!("eight argument/completion payloads: {occupancy:?}; caller buffers and preexisting owner/VM excluded");
    let before = token(&g);
    let base = observer.begin(0, 1);
    assert_eq!(get(&mut g, 1), 5);
    assert_eq!(end(base), (0, 0, 0));
    assert_eq!(token(&g), before);
    let base = observer.begin(0, 1);
    for (t, ticket) in tokens.into_iter().zip(tickets.iter()) {
        assert_eq!(
            g.invoke(
                "poll",
                &[
                    Value::I64(t as i64),
                    Value::I32(0),
                    Value::I32(mb::MAX_PAYLOAD_BYTES as i32),
                    Value::I32(LENGTH)
                ]
            )
            .unwrap(),
            Some(Value::I32(0))
        );
        ticket.as_ref().unwrap().ack_exit().unwrap();
    }
    let delivery = end(base);
    assert_eq!(delivery.0, 0);
    assert_eq!(p.usage().unwrap().reserved_bytes, 0);
    println!(
        "ready-poll/ack allocation calls={}; ready payloads copied without staging",
        delivery.0
    );
    assert_eq!(&g.memory()[..mb::MAX_PAYLOAD_BYTES], completion.as_slice());
    drop(tickets);
    // Reuse now has no retained first-generation payloads. Drop closes but native
    // ticket keeps its argument bytes until acknowledged; dropping ticket alone
    // is deliberately not an exit acknowledgement.
    assert_eq!(get(&mut g, 1024), 0);
    let ticket = take(&p, &mut output);
    let base = observer.begin(0, 1);
    drop(g);
    drop(p);
    assert_eq!(CALLS.load(SeqCst), 0);
    let before_ack = LIVE.load(SeqCst);
    ticket.ack_exit().unwrap();
    assert_eq!(before_ack - LIVE.load(SeqCst), 1024);
    let before_last_drop = LIVE.load(SeqCst);
    drop(ticket);
    let last_owner_freed = before_last_drop - LIVE.load(SeqCst);
    let after_drop = end(base);
    assert_eq!(after_drop.0, 0);
    println!(
        "close/drop/last-ticket-ack allocation calls={}; final owner requested bytes freed={last_owner_freed}",
        after_drop.0,
    );
    println!(
        "observer maximum ownership slots={} capacity=4096 background_noise={}",
        MAX_SLOTS.load(SeqCst),
        std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some()
    );
}
