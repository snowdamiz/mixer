//! Independent public-API composition tests and binary builder. No engine test
//! helpers or fixtures are imported; no native adapter or endpoint is executed.
use mixer_vm::{
    experimental_capability as mb,
    experimental_capability_guest::{
        CapabilityGuest, CapabilityPort, DispatchLease, GuestLimits, NativeTake, IMPORT_MODULE,
        WAKE_EXPORT,
    },
    Limits, Module, Profile, Type, Value,
};
use std::time::{Duration, Instant};
const TOKEN: u32 = 1023;
const WORD: u32 = 1043;
const OUT: u32 = 4093;
fn unsigned(mut n: u32) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        b.push(x | if n == 0 { 0 } else { 128 });
        if n == 0 {
            return b;
        }
    }
}
fn signed(mut n: i32) -> Vec<u8> {
    let mut b = vec![0x41];
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        let done = (n == 0 && x & 64 == 0) || (n == -1 && x & 64 != 0);
        b.push(x | if done { 0 } else { 128 });
        if done {
            return b;
        }
    }
}
fn text(s: &str) -> Vec<u8> {
    [unsigned(s.len() as u32), s.as_bytes().to_vec()].concat()
}
fn sec(m: &mut Vec<u8>, kind: u8, body: Vec<u8>) {
    m.push(kind);
    m.extend(unsigned(body.len() as u32));
    m.extend(body);
}
fn sig(p: &[u8], r: Option<u8>) -> Vec<u8> {
    let mut b = vec![0x60];
    b.extend(unsigned(p.len() as u32));
    b.extend(p);
    b.push(u8::from(r.is_some()));
    b.extend(r);
    b
}
fn locals(n: u8) -> Vec<u8> {
    (0..n).flat_map(|i| [0x20, i]).collect()
}
fn enqueue_code(op: u8) -> Vec<u8> {
    [
        signed(128),
        signed(13),
        signed(TOKEN as i32),
        vec![0x10, op],
    ]
    .concat()
}
struct Binary {
    module: String,
    names: Vec<String>,
    types: Vec<(Vec<u8>, Option<u8>)>,
    funcs: Vec<(u32, Vec<u8>)>,
    memory: bool,
    exports: Vec<(String, u32)>,
    table: Vec<u32>,
}
impl Binary {
    fn new() -> Self {
        let types = vec![
            (vec![0x7f; 3], Some(0x7f)),
            (vec![0x7e], Some(0x7f)),
            (vec![0x7e, 0x7f, 0x7f, 0x7f], Some(0x7f)),
            (vec![], None),
            (vec![], Some(0x7f)),
            (vec![0x7f; 4], Some(0x7f)),
            (vec![0x7f; 2], None),
            (vec![0x7e], None),
        ];
        let mut funcs = vec![(4, [signed(42), vec![0x0b]].concat()), (3, vec![0x0b])];
        for op in 0..4 {
            funcs.push((
                0,
                [locals(3), vec![0x10, op], signed(100), vec![0x6a, 0x0b]].concat(),
            ));
        }
        funcs.push((
            5,
            [
                locals(3),
                vec![0x20, 3, 0x11, 0, 0],
                signed(100),
                vec![0x6a, 0x0b],
            ]
            .concat(),
        ));
        funcs.push((3, [enqueue_code(1), vec![0x1a, 0x00, 0x0b]].concat()));
        funcs.push((
            3,
            [enqueue_code(1), vec![0x1a, 0x03, 0x40, 0x0c, 0, 0x0b, 0x0b]].concat(),
        ));
        funcs.push((6, [locals(2), vec![0x3a, 0, 0, 0x0b]].concat()));
        funcs.push((4, [signed(1), vec![0x40, 0, 0x0b]].concat()));
        funcs.push((
            7,
            [signed(TOKEN as i32), locals(1), vec![0x37, 0, 0, 0x0b]].concat(),
        ));
        let mut exports = vec![
            ("boot".into(), 6),
            (WAKE_EXPORT.into(), 7),
            ("indirect".into(), 12),
            ("trap".into(), 13),
            ("spin".into(), 14),
            ("store8".into(), 15),
            ("grow".into(), 16),
            ("replace_token".into(), 17),
        ];
        for (i, label) in ["http", "get", "put", "delete", "cancel", "poll"]
            .iter()
            .enumerate()
        {
            exports.push((label.to_string(), i as u32));
        }
        for (i, label) in ["direct_http", "direct_get", "direct_put", "direct_delete"]
            .iter()
            .enumerate()
        {
            exports.push((label.to_string(), i as u32 + 8));
        }
        Self {
            module: IMPORT_MODULE.into(),
            names: [
                "http_request",
                "storage_get",
                "storage_put",
                "storage_delete",
                "cancel",
                "poll",
            ]
            .map(str::to_string)
            .to_vec(),
            types,
            funcs,
            memory: true,
            exports,
            table: vec![0, 1, 2, 3, 4, 5],
        }
    }
    fn bytes(&self) -> Vec<u8> {
        let mut m = b"\0asm\x01\0\0\0".to_vec();
        let mut b = unsigned(self.types.len() as u32);
        for (p, r) in &self.types {
            b.extend(sig(p, *r));
        }
        sec(&mut m, 1, b);
        let mut b = unsigned(self.names.len() as u32);
        for (i, n) in self.names.iter().enumerate() {
            b.extend(text(&self.module));
            b.extend(text(n));
            b.push(0);
            b.extend(unsigned(if i < 4 {
                0
            } else if i == 4 {
                1
            } else {
                2
            }));
        }
        sec(&mut m, 2, b);
        let mut b = unsigned(self.funcs.len() as u32);
        for (t, _) in &self.funcs {
            b.extend(unsigned(*t));
        }
        sec(&mut m, 3, b);
        sec(&mut m, 4, vec![1, 0x70, 1, 8, 8]);
        if self.memory {
            sec(&mut m, 5, vec![1, 1, 1, 2]);
        }
        let mut b = unsigned(self.exports.len() as u32);
        for (n, i) in &self.exports {
            b.extend(text(n));
            b.push(0);
            b.extend(unsigned(*i));
        }
        sec(&mut m, 7, b);
        let mut b = vec![1, 0, 0x41, 0, 0x0b];
        b.extend(unsigned(self.table.len() as u32));
        for t in &self.table {
            b.extend(unsigned(*t));
        }
        sec(&mut m, 9, b);
        let mut b = unsigned(self.funcs.len() as u32);
        for (_, code) in &self.funcs {
            let body = [vec![0], code.clone()].concat();
            b.extend(unsigned(body.len() as u32));
            b.extend(body);
        }
        sec(&mut m, 10, b);
        if self.memory {
            let mut b = vec![1, 0, 0x41, 0, 0x0b];
            b.extend(unsigned(65536));
            b.extend((0..65536).map(|n| ((n * 17 + 0x51) % 256) as u8));
            sec(&mut m, 11, b);
        }
        m
    }
}
fn limits() -> Limits {
    Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    }
}
fn make(b: &Binary, l: Limits) -> CapabilityGuest {
    CapabilityGuest::new(
        &b.bytes(),
        l,
        mb::Limits::default(),
        GuestLimits::default(),
        "boot",
    )
    .unwrap()
}
fn ready(b: &Binary, l: Limits) -> (CapabilityGuest, CapabilityPort) {
    let mut g = make(b, l);
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    (g, p)
}
fn call(
    g: &mut CapabilityGuest,
    name: &str,
    a: u32,
    n: u32,
    t: u32,
) -> Result<Option<Value>, mixer_vm::Error> {
    g.invoke(
        name,
        &[
            Value::I32(a as i32),
            Value::I32(n as i32),
            Value::I32(t as i32),
        ],
    )
}
fn poll(
    g: &mut CapabilityGuest,
    t: u64,
    o: u32,
    n: u32,
    w: u32,
) -> Result<Option<Value>, mixer_vm::Error> {
    g.invoke(
        "poll",
        &[
            Value::I64(t as i64),
            Value::I32(o as i32),
            Value::I32(n as i32),
            Value::I32(w as i32),
        ],
    )
}
fn token(g: &CapabilityGuest) -> u64 {
    u64::from_le_bytes(
        g.memory()[TOKEN as usize..TOKEN as usize + 8]
            .try_into()
            .unwrap(),
    )
}
fn word(g: &CapabilityGuest) -> u32 {
    u32::from_le_bytes(
        g.memory()[WORD as usize..WORD as usize + 4]
            .try_into()
            .unwrap(),
    )
}
fn taken(p: &CapabilityPort) -> (DispatchLease, Vec<u8>) {
    let mut out = vec![0; 65536];
    match p.take(&mut out).unwrap() {
        NativeTake::Call {
            lease,
            length,
            remaining_milliseconds,
        } => {
            assert!((1..=30_000).contains(&remaining_milliseconds));
            out.truncate(length);
            (lease, out)
        }
        _ => panic!("expected native call"),
    }
}
fn valid(a: u32, n: u32, max: u32) -> bool {
    u64::from(a) + u64::from(n) <= u64::from(max)
}
fn disjoint(a: u32, n: u32, b: u32, m: u32) -> bool {
    n == 0
        || m == 0
        || u64::from(a) + u64::from(n) <= u64::from(b)
        || u64::from(b) + u64::from(m) <= u64::from(a)
}

#[test]
fn import_values_survive_three_entry_shapes_and_indirect_stack_arithmetic() {
    for (op, kind) in [
        mb::Operation::HttpRequest,
        mb::Operation::Get,
        mb::Operation::Put,
        mb::Operation::Delete,
    ]
    .into_iter()
    .enumerate()
    {
        for shape in 0..3 {
            let (mut g, p) = ready(&Binary::new(), limits());
            let before = g.memory()[128..141].to_vec();
            let result = match shape {
                0 => call(&mut g, ["http", "get", "put", "delete"][op], 128, 13, TOKEN),
                1 => call(
                    &mut g,
                    ["direct_http", "direct_get", "direct_put", "direct_delete"][op],
                    128,
                    13,
                    TOKEN,
                ),
                _ => g.invoke(
                    "indirect",
                    &[
                        Value::I32(128),
                        Value::I32(13),
                        Value::I32(TOKEN as i32),
                        Value::I32(op as i32),
                    ],
                ),
            }
            .unwrap();
            assert_eq!(result, Some(Value::I32(if shape == 0 { 0 } else { 100 })));
            let (lease, args) = taken(&p);
            assert_eq!(lease.operation(), kind);
            assert_eq!(args, before);
            assert_eq!(lease.token_bits(), token(&g));
            g.invoke("store8", &[Value::I32(128), Value::I32(0)])
                .unwrap();
            assert_eq!(g.invoke("grow", &[]).unwrap(), Some(Value::I32(1)));
            assert_eq!(g.memory().len(), 131072);
            assert_eq!(args, before);
            p.post_trusted(&lease, b"owned reply").unwrap();
            assert_eq!(
                poll(&mut g, lease.token_bits(), OUT, 11, WORD).unwrap(),
                Some(Value::I32(0))
            );
            assert_eq!(word(&g), 11);
            assert_eq!(&g.memory()[OUT as usize..OUT as usize + 11], b"owned reply");
            assert_eq!(p.usage().unwrap().native_leases, 1);
            lease.ack_exit().unwrap();
            assert_eq!(p.usage().unwrap().reserved_bytes, 0);
        }
    }
    for index in [4, 6, 8] {
        let (mut g, p) = ready(&Binary::new(), limits());
        let before = g.memory().to_vec();
        assert!(g
            .invoke(
                "indirect",
                &[
                    Value::I32(128),
                    Value::I32(13),
                    Value::I32(TOKEN as i32),
                    Value::I32(index)
                ]
            )
            .is_err());
        assert_eq!(g.memory(), before);
        assert!(p.usage().unwrap().closed);
        assert_eq!(p.usage().unwrap().outstanding_requests, 0);
    }
}

#[test]
fn unsigned_range_and_overlap_matrix_preserves_every_byte_on_rejection() {
    let points = [0, 1, 127, 128, 129, 65528, 65529, 65535, 65536, u32::MAX];
    let lens = [0, 1, 8, 13, 65536, 524289, u32::MAX];
    let mut rejected = 0;
    for i in 0..points.len() {
        for j in 0..lens.len() {
            let a = points[i];
            let n = lens[j];
            let t = points[(i * 3 + j) % points.len()];
            let expected = valid(a, n, 65536)
                && n > 0
                && n <= 524288
                && valid(t, 8, 65536)
                && disjoint(a, n, t, 8);
            let (mut g, p) = ready(&Binary::new(), limits());
            let before = g.memory().to_vec();
            assert_eq!(
                call(&mut g, "get", a, n, t).unwrap(),
                Some(Value::I32(if expected { 0 } else { 3 })),
                "a={a} n={n} t={t}"
            );
            if !expected {
                rejected += 1;
                assert_eq!(g.memory(), before);
                assert_eq!(p.usage().unwrap().reserved_bytes, 0);
            } else {
                assert_eq!(p.usage().unwrap().reserved_bytes, n as usize + 524288);
                assert_eq!(&g.memory()[..t as usize], &before[..t as usize]);
                assert_eq!(&g.memory()[t as usize + 8..], &before[t as usize + 8..]);
            }
        }
    }
    println!("independent enqueue matrix=70 cases; rejection count={rejected}; u64 oracle for all i32 bit-pattern ranges");
}

#[test]
fn poll_range_matrix_cannot_consume_or_partially_write_a_ready_payload() {
    let cases = [
        (65536, 1, WORD),
        (u32::MAX, 0, WORD),
        (OUT, 524289, WORD),
        (OUT, 8, u32::MAX),
        (WORD - 1, 2, WORD),
        (OUT, 16, OUT + 15),
        (OUT, 16, OUT - 3),
        (WORD + 1, 0, WORD),
        (65536, 0, WORD),
        (OUT, 0, WORD),
        (OUT, 7, WORD),
        (OUT, 8, WORD),
    ];
    for (o, n, w) in cases {
        let (mut g, p) = ready(&Binary::new(), limits());
        call(&mut g, "get", 128, 13, TOKEN).unwrap();
        let (lease, _) = taken(&p);
        p.post_trusted(&lease, b"12345678").unwrap();
        let before = g.memory().to_vec();
        let valid_ranges =
            valid(o, n, 65536) && n <= 524288 && valid(w, 4, 65536) && disjoint(o, n, w, 4);
        let status = if !valid_ranges {
            3
        } else if n < 8 {
            2
        } else {
            0
        };
        assert_eq!(
            poll(&mut g, lease.token_bits(), o, n, w).unwrap(),
            Some(Value::I32(status))
        );
        if status == 3 {
            assert_eq!(g.memory(), before);
            assert_eq!(p.usage().unwrap().completion_bytes, 8);
        } else if status == 2 {
            let mut expected = before;
            expected[w as usize..w as usize + 4].copy_from_slice(&8u32.to_le_bytes());
            assert_eq!(g.memory(), expected);
            assert_eq!(p.usage().unwrap().completion_bytes, 8);
        } else {
            assert_eq!(&g.memory()[o as usize..o as usize + 8], b"12345678");
            assert_eq!(p.usage().unwrap().completion_bytes, 0);
        }
        if status != 0 {
            assert_eq!(
                poll(&mut g, lease.token_bits(), OUT, 8, WORD).unwrap(),
                Some(Value::I32(0))
            );
        }
        let consumed = g.memory().to_vec();
        assert_eq!(
            poll(&mut g, lease.token_bits(), OUT, 8, WORD).unwrap(),
            Some(Value::I32(4))
        );
        assert_eq!(g.memory(), consumed);
        lease.ack_exit().unwrap();
    }
}

#[test]
fn byte_fuel_boundary_controls_token_and_payload_transaction_visibility() {
    for n in [1usize, 56, 57, 120, 121, 4096] {
        let cost = 1 + (n + 8).div_ceil(64) as u64;
        for fuel in [cost - 1, cost] {
            let mut b = Binary::new();
            b.funcs[0] = (3, vec![0x0b]);
            let (mut g, p) = ready(&b, Limits { fuel, ..limits() });
            let before = g.memory().to_vec();
            let result = call(&mut g, "put", 128, n as u32, TOKEN);
            assert_eq!(g.host_calls_used(), 1);
            if fuel < cost {
                assert_eq!(result.unwrap_err().code, "fuel_exhausted");
                assert_eq!(g.memory(), before);
                assert!(p.usage().unwrap().closed);
                assert_eq!(p.usage().unwrap().outstanding_requests, 0);
            } else {
                assert_eq!(result.unwrap(), Some(Value::I32(0)));
                assert_eq!(g.fuel_remaining(), 0);
            }
        }
    }
    for n in [61usize, 124, 125, 4096] {
        let cost = 1 + (n + 4).div_ceil(64) as u64;
        for fuel in [cost - 1, cost] {
            let mut b = Binary::new();
            b.funcs[0] = (3, vec![0x0b]);
            let (mut g, p) = ready(&b, Limits { fuel, ..limits() });
            call(&mut g, "put", 128, 1, TOKEN).unwrap();
            let (lease, _) = taken(&p);
            p.post_trusted(&lease, &vec![0x7c; n]).unwrap();
            let before = g.memory().to_vec();
            let result = poll(&mut g, lease.token_bits(), OUT, n as u32, WORD);
            if fuel < cost {
                assert_eq!(result.unwrap_err().code, "fuel_exhausted");
                assert_eq!(g.memory(), before);
                assert!(p.usage().unwrap().closed);
                assert_eq!(p.usage().unwrap().native_leases, 1);
            } else {
                assert_eq!(result.unwrap(), Some(Value::I32(0)));
                assert_eq!(g.fuel_remaining(), 0);
                assert_eq!(&g.memory()[OUT as usize..OUT as usize + n], vec![0x7c; n]);
            }
            drop(g);
            drop(p);
            assert_eq!(lease.ack_exit(), Ok(()));
            assert_eq!(lease.ack_exit(), Err(mb::Error::StaleRequest));
        }
    }
}

#[test]
fn startup_disabled_requests_are_unavailable_and_wake_consumes_only_fixed_entry() {
    let mut b = Binary::new();
    b.funcs[0] = (0, vec![]); // overwritten with a defined no-argument result signature below
    b.funcs[0] = (4, [enqueue_code(1), vec![0x0b]].concat());
    b.funcs[1] = (
        3,
        [
            signed(TOKEN as i32),
            vec![0x29, 0, 0],
            signed(OUT as i32),
            signed(512),
            signed(WORD as i32),
            vec![0x10, 5, 0x1a, 0x0b],
        ]
        .concat(),
    );
    let mut g = make(&b, limits());
    let p = g.native_port();
    assert_eq!(g.enable_effects().unwrap_err().code, "capability_state");
    assert!(g.wake_once().is_err());
    assert_eq!(g.startup().unwrap(), Some(Value::I32(0)));
    let old = token(&g);
    g.enable_effects().unwrap();
    assert!(matches!(p.take(&mut []).unwrap(), NativeTake::None));
    assert!(g.wake_once().unwrap());
    let payload = &g.memory()[OUT as usize..OUT as usize + word(&g) as usize];
    assert_eq!(payload,b"{\"abi\":1,\"capability\":\"storage.keyValue.v1\",\"operation\":\"get\",\"outcome\":{\"code\":\"unavailable\",\"kind\":\"failure\"},\"schemaHash\":\"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd\"}");
    assert!(!g.wake_once().unwrap());
    assert_eq!(
        poll(&mut g, old, OUT, 512, WORD).unwrap(),
        Some(Value::I32(4))
    );
    call(&mut g, "get", 128, 13, TOKEN).unwrap();
    let (lease, _) = taken(&p);
    p.post_trusted(&lease, b"wake-owned").unwrap();
    assert!(g.wake_once().unwrap());
    assert_eq!(&g.memory()[OUT as usize..OUT as usize + 10], b"wake-owned");
    assert!(!g.wake_once().unwrap());
    assert_eq!(p.usage().unwrap().native_leases, 1);
    lease.ack_exit().unwrap();
}

#[test]
fn trap_close_cancel_and_foreign_tickets_preserve_distinct_ownership_obligations() {
    let (mut a, pa) = ready(&Binary::new(), limits());
    let (mut b, pb) = ready(&Binary::new(), limits());
    call(&mut a, "get", 128, 13, TOKEN).unwrap();
    call(&mut b, "get", 128, 13, TOKEN).unwrap();
    assert_eq!(token(&a), token(&b));
    let (lease, _) = taken(&pa);
    assert_eq!(
        pb.post_trusted(&lease, b"foreign"),
        Err(mb::Error::StaleRequest)
    );
    assert_eq!(pb.ack_exit(&lease), Err(mb::Error::StaleRequest));
    assert_eq!(pb.limit_deadline(&lease, 1), Err(mb::Error::StaleRequest));
    let before = pa.usage().unwrap();
    assert_eq!(a.invoke("trap", &[]).unwrap_err().code, "unreachable");
    let after = pa.usage().unwrap();
    assert!(after.closed);
    assert_eq!(
        (
            after.native_leases,
            after.reserved_bytes,
            after.argument_bytes
        ),
        (
            before.native_leases,
            before.reserved_bytes,
            before.argument_bytes
        )
    );
    assert_eq!(
        pa.post_trusted(&lease, b"late"),
        Err(mb::Error::SessionClosed)
    );
    drop(a);
    drop(pa);
    lease.ack_exit().unwrap();
    let cancellation = b.cancellation();
    cancellation.cancel();
    assert_eq!(b.invoke("get", &[]).unwrap_err().code, "capability_closed");
    assert_eq!(pb.usage().unwrap().outstanding_requests, 0);
    assert!(b.startup().is_err());
    assert!(b.wake_once().is_err());
}

#[test]
fn active_wasm_turn_cannot_drain_then_external_cancel_discards_it() {
    let (mut g, p) = ready(
        &Binary::new(),
        Limits {
            fuel: u64::MAX,
            ..limits()
        },
    );
    let cancellation = g.cancellation();
    std::thread::scope(|scope| {
        let native = scope.spawn(|| {
            let stop = Instant::now() + Duration::from_secs(2);
            while Instant::now() < stop {
                let u = p.usage().unwrap();
                if u.turn_active && u.outstanding_requests == 1 {
                    assert!(matches!(p.take(&mut [0; 64]).unwrap(), NativeTake::None));
                    cancellation.cancel();
                    return true;
                }
                if u.closed {
                    return false;
                }
                std::thread::yield_now();
            }
            false
        });
        let result = g.invoke("spin", &[]);
        assert_eq!(result.unwrap_err().code, "cancelled");
        assert!(native.join().unwrap());
    });
    assert!(p.usage().unwrap().closed);
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
}

#[test]
fn full_validation_and_legacy_api_rejection_do_not_depend_on_execution_reachability() {
    let original = Binary::new();
    let bytes = original.bytes();
    for profile in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let l = Limits {
            profile,
            ..Limits::default()
        };
        assert_eq!(Module::decode(&bytes, &l).unwrap_err().code, "unsupported");
        assert!(mixer_vm::validation_inventory(&bytes, &l).error.is_some());
    }
    for variant in 0..6 {
        let mut b = Binary::new();
        match variant {
            0 => b.module = "mixer.capability.v1.extra".into(),
            1 => b.names[3] = "checkpoint".into(),
            2 => b.memory = false,
            3 => b.exports.retain(|(name, _)| name != WAKE_EXPORT),
            4 => {
                b.exports
                    .iter_mut()
                    .find(|(name, _)| name == WAKE_EXPORT)
                    .unwrap()
                    .1 = 0
            }
            _ => b.funcs.push((3, vec![0, 0xff, 0x0b])),
        };
        assert!(
            CapabilityGuest::new(
                &b.bytes(),
                limits(),
                mb::Limits::default(),
                GuestLimits::default(),
                "boot"
            )
            .is_err(),
            "variant {variant}"
        );
    }
    let (mut g, p) = ready(
        &original,
        Limits {
            host_calls: 0,
            ..limits()
        },
    );
    let before = g.memory().to_vec();
    assert_eq!(
        call(&mut g, "get", 128, 13, TOKEN).unwrap_err().code,
        "host_call_limit"
    );
    assert_eq!(g.host_calls_used(), 0);
    assert_eq!(g.memory(), before);
    assert!(p.usage().unwrap().closed);
    // Imports may be exported for ordinary calls, but never selected as startup.
    assert!(CapabilityGuest::new(
        &bytes,
        limits(),
        mb::Limits::default(),
        GuestLimits::default(),
        "get"
    )
    .is_err());
}
