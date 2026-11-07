#![cfg(feature = "experimental-capability-guest")]
mod common;
use common::{constant, section, u32leb, Function};
use mixer_vm::{
    experimental_capability as mb,
    experimental_capability_guest::{
        CapabilityGuest, CapabilityPort, DispatchLease, GuestLimits, NativeTake, IMPORT_MODULE,
        WAKE_EXPORT,
    },
    Instance, Limits, Module, Profile, Type, Value,
};
const TOKEN: u32 = 1025;
const LENGTH: u32 = 1041;
const OUT: u32 = 4096;
const ARG: &[u8] = b"{\"key\":\"note\",\"namespace\":\"review\"}";
fn l() -> Limits {
    Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    }
}
fn ty(t: Type) -> u8 {
    match t {
        Type::I32 => 0x7f,
        Type::I64 => 0x7e,
        Type::F32 => 0x7d,
        Type::F64 => 0x7c,
    }
}
fn name(s: &str) -> Vec<u8> {
    let mut b = u32leb(s.len() as u32);
    b.extend(s.as_bytes());
    b
}
fn signature(p: &[Type], r: Option<Type>) -> Vec<u8> {
    let mut b = vec![0x60];
    b.extend(u32leb(p.len() as u32));
    b.extend(p.iter().copied().map(ty));
    b.push(r.is_some() as u8);
    b.extend(r.map(ty));
    b
}
struct Spec {
    imports: Vec<(String, String, Vec<Type>, Option<Type>)>,
    functions: Vec<Function>,
    memory: Option<(u32, u32)>,
    table: Option<Vec<u32>>,
    table_spare: u32,
    data: Vec<(u32, Vec<u8>)>,
    wake_name: String,
    wake_index: Option<u32>,
    extra_section: Option<(u8, Vec<u8>)>,
}
impl Default for Spec {
    fn default() -> Self {
        Self {
            imports: [
                ("http_request", vec![Type::I32; 3]),
                ("storage_get", vec![Type::I32; 3]),
                ("storage_put", vec![Type::I32; 3]),
                ("storage_delete", vec![Type::I32; 3]),
                ("cancel", vec![Type::I64]),
                ("poll", vec![Type::I64, Type::I32, Type::I32, Type::I32]),
            ]
            .into_iter()
            .map(|(n, p)| (IMPORT_MODULE.into(), n.into(), p, Some(Type::I32)))
            .collect(),
            functions: vec![
                Function::new(vec![], None, vec![0x0b]),
                Function::new(
                    vec![Type::I32; 3],
                    Some(Type::I32),
                    vec![0x20, 0, 0x20, 1, 0x20, 2, 0x10, 1, 0x0b],
                ),
                Function::new(vec![], None, vec![0x0b]),
            ],
            memory: Some((1, 4)),
            table: None,
            table_spare: 0,
            data: vec![
                (0, ARG.to_vec()),
                (TOKEN, vec![0xa5; 8]),
                (LENGTH, vec![0xa5; 4]),
                (OUT, vec![0xa5; 512]),
            ],
            wake_name: WAKE_EXPORT.into(),
            wake_index: Some(8),
            extra_section: None,
        }
    }
}
impl Spec {
    fn bytes(&self) -> Vec<u8> {
        let mut m = b"\0asm\x01\0\0\0".to_vec();
        let mut t = u32leb((self.imports.len() + self.functions.len()) as u32);
        for (_, _, p, r) in &self.imports {
            t.extend(signature(p, *r));
        }
        for f in &self.functions {
            t.extend(signature(&f.params, f.result));
        }
        section(&mut m, 1, t);
        let mut i = u32leb(self.imports.len() as u32);
        for (n, (module, field, _, _)) in self.imports.iter().enumerate() {
            i.extend(name(module));
            i.extend(name(field));
            i.push(0);
            i.extend(u32leb(n as u32));
        }
        section(&mut m, 2, i);
        let mut f = u32leb(self.functions.len() as u32);
        for n in 0..self.functions.len() {
            f.extend(u32leb((self.imports.len() + n) as u32));
        }
        section(&mut m, 3, f);
        if let Some(entries) = &self.table {
            let mut t = vec![1, 0x70, 1];
            t.extend(u32leb(entries.len() as u32 + self.table_spare));
            t.extend(u32leb(entries.len() as u32 + self.table_spare));
            section(&mut m, 4, t);
        }
        if let Some((min, max)) = self.memory {
            let mut b = vec![1, 1];
            b.extend(u32leb(min));
            b.extend(u32leb(max));
            section(&mut m, 5, b);
        }
        let mut e =
            u32leb((2 + self.imports.len() + usize::from(self.wake_index.is_some())) as u32);
        for (label, index) in [
            ("start", self.imports.len() as u32),
            ("run", self.imports.len() as u32 + 1),
        ] {
            e.extend(name(label));
            e.push(0);
            e.extend(u32leb(index));
        }
        if let Some(index) = self.wake_index {
            e.extend(name(&self.wake_name));
            e.push(0);
            e.extend(u32leb(index));
        }
        for (n, label) in ["http", "get", "put", "delete", "cancel", "poll"]
            .iter()
            .enumerate()
            .take(self.imports.len())
        {
            e.extend(name(label));
            e.push(0);
            e.extend(u32leb(n as u32));
        }
        section(&mut m, 7, e);
        if let Some((id, b)) = &self.extra_section {
            section(&mut m, *id, b.clone());
        }
        if let Some(entries) = &self.table {
            let mut b = vec![1, 0, 0x41, 0, 0x0b];
            b.extend(u32leb(entries.len() as u32));
            for n in entries {
                b.extend(u32leb(*n));
            }
            section(&mut m, 9, b);
        }
        let mut c = u32leb(self.functions.len() as u32);
        for f in &self.functions {
            let mut b = u32leb(f.locals.len() as u32);
            for t in &f.locals {
                b.extend([1, ty(*t)]);
            }
            b.extend(&f.code);
            c.extend(u32leb(b.len() as u32));
            c.extend(b);
        }
        section(&mut m, 10, c);
        let mut d = u32leb(self.data.len() as u32);
        for (offset, bytes) in &self.data {
            d.push(0);
            d.extend(constant(Value::I32(*offset as i32)));
            d.push(0x0b);
            d.extend(u32leb(bytes.len() as u32));
            d.extend(bytes);
        }
        section(&mut m, 11, d);
        m
    }
}
fn build(s: &Spec) -> CapabilityGuest {
    CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits::default(),
        GuestLimits::default(),
        "start",
    )
    .unwrap()
}
fn enabled(s: &Spec) -> (CapabilityGuest, CapabilityPort) {
    let mut g = build(s);
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    (g, p)
}
fn enqueue(
    g: &mut CapabilityGuest,
    export: &str,
    start: u32,
    len: u32,
    token: u32,
) -> Result<Option<Value>, mixer_vm::Error> {
    g.invoke(
        export,
        &[
            Value::I32(start as i32),
            Value::I32(len as i32),
            Value::I32(token as i32),
        ],
    )
}
fn token(g: &CapabilityGuest, at: u32) -> u64 {
    u64::from_le_bytes(g.memory()[at as usize..at as usize + 8].try_into().unwrap())
}
fn length(g: &CapabilityGuest) -> u32 {
    u32::from_le_bytes(
        g.memory()[LENGTH as usize..LENGTH as usize + 4]
            .try_into()
            .unwrap(),
    )
}
fn poll(
    g: &mut CapabilityGuest,
    bits: u64,
    out: u32,
    capacity: u32,
    len: u32,
) -> Result<Option<Value>, mixer_vm::Error> {
    g.invoke(
        "poll",
        &[
            Value::I64(bits as i64),
            Value::I32(out as i32),
            Value::I32(capacity as i32),
            Value::I32(len as i32),
        ],
    )
}
fn take(p: &CapabilityPort) -> (DispatchLease, Vec<u8>) {
    let mut b = vec![0; mb::MAX_PAYLOAD_BYTES];
    match p.take(&mut b).unwrap() {
        NativeTake::Call { lease, length, .. } => {
            b.truncate(length);
            (lease, b)
        }
        _ => panic!("expected call"),
    }
}
fn expected(operation: &str, reason: &str) -> Vec<u8> {
    let (cap, hash, op) = match operation {
        "http" => (
            "network.http.v1",
            "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3",
            "request",
        ),
        "get" => (
            "storage.keyValue.v1",
            "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd",
            "get",
        ),
        "put" => (
            "storage.keyValue.v1",
            "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd",
            "put",
        ),
        _ => (
            "storage.keyValue.v1",
            "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd",
            "delete",
        ),
    };
    format!("{{\"abi\":1,\"capability\":\"{cap}\",\"operation\":\"{op}\",\"outcome\":{{\"code\":\"{reason}\",\"kind\":\"failure\"}},\"schemaHash\":\"{hash}\"}}").into_bytes()
}

#[test]
fn legacy_validators_and_c_routes_still_reject_capability_imports() {
    let b = Spec::default().bytes();
    for profile in [
        Profile::IntegerV1,
        Profile::NumericV2,
        Profile::TableMemoryV3,
    ] {
        let limits = Limits {
            profile,
            ..Limits::default()
        };
        assert_eq!(Module::decode(&b, &limits).unwrap_err().code, "unsupported");
        #[cfg(feature = "experimental-stream-validation")]
        assert!(mixer_vm::experimental::validate_spans(
            &b,
            limits,
            mixer_vm::experimental::ValidationBudget::default(),
            &mixer_vm::Cancellation::default()
        )
        .is_err());
    }
    let legacy = common::Spec::one(vec![], None, vec![0x0b]).bytes();
    assert!(Instance::new(Module::decode(&legacy, &l()).unwrap(), l()).is_ok());
    unsafe {
        let mut report = std::mem::zeroed::<mixer_vm::MixerVmReport>();
        assert_ne!(
            mixer_vm::mixer_vm_validate_table_memory_v3(
                b.as_ptr(),
                b.len(),
                std::ptr::null(),
                &mut report
            ),
            0
        );
        let mut handle = 0;
        assert_ne!(
            mixer_vm::mixer_vm_session_create_v1(
                4,
                b.as_ptr(),
                b.len(),
                std::ptr::null(),
                &mut handle,
                &mut report
            ),
            0
        );
        assert_eq!(handle, 0);
    }
}
#[test]
fn exact_import_memory_startup_and_wake_validation() {
    for mode in 0..8 {
        let mut s = Spec::default();
        match mode {
            0 => s.memory = None,
            1 => s.wake_index = None,
            2 => s.wake_name = "almost_wake".into(),
            3 => s.wake_index = Some(0),
            4 => s.functions[2].result = Some(Type::I32),
            5 => s.imports[0].0 = "wrong.module".into(),
            6 => s.imports[0].1 = "generic_dispatch".into(),
            _ => s.imports[0].3 = None,
        };
        assert!(CapabilityGuest::new(
            &s.bytes(),
            l(),
            mb::Limits::default(),
            GuestLimits::default(),
            "start"
        )
        .is_err());
    }
    let s = Spec {
        extra_section: Some((8, vec![6])),
        ..Spec::default()
    };
    assert!(CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits::default(),
        GuestLimits::default(),
        "start"
    )
    .is_err());
    let s = Spec::default();
    assert!(CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits::default(),
        GuestLimits::default(),
        "get"
    )
    .is_err());
    assert!(CapabilityGuest::new(
        &s.bytes(),
        Limits::default(),
        mb::Limits::default(),
        GuestLimits::default(),
        "start"
    )
    .is_err());
}
#[test]
fn startup_is_explicit_disabled_and_enable_never_retroactively_dispatches() {
    let mut g = build(&Spec::default());
    let p = g.native_port();
    assert_eq!(g.enable_effects().unwrap_err().code, "capability_state");
    assert!(g.invoke("get", &[]).is_err());
    assert!(!p.usage().unwrap().turn_active);
    g.startup().unwrap();
    assert_eq!(
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap(),
        Some(Value::I32(0))
    );
    let bits = token(&g, TOKEN);
    g.enable_effects().unwrap();
    g.enable_effects().unwrap();
    assert!(matches!(p.take(&mut [0; 64]).unwrap(), NativeTake::None));
    assert_eq!(
        poll(&mut g, bits, OUT, 512, LENGTH).unwrap(),
        Some(Value::I32(0))
    );
    let e = expected("get", "unavailable");
    assert_eq!(&g.memory()[OUT as usize..OUT as usize + e.len()], e);
    assert_eq!(g.startup().unwrap_err().code, "capability_state");
}
#[test]
fn all_four_typed_enqueue_imports_return_i32_and_fix_operation() {
    for (name, op) in [
        ("http", mb::Operation::HttpRequest),
        ("get", mb::Operation::Get),
        ("put", mb::Operation::Put),
        ("delete", mb::Operation::Delete),
    ] {
        let (mut g, p) = enabled(&Spec::default());
        assert_eq!(
            enqueue(&mut g, name, 0, ARG.len() as u32, TOKEN).unwrap(),
            Some(Value::I32(0))
        );
        let (lease, b) = take(&p);
        assert_eq!(lease.operation(), op);
        assert_eq!(b, ARG);
        assert_eq!(lease.token_bits(), token(&g, TOKEN));
        p.post_trusted(&lease, b"trusted opaque development completion")
            .unwrap();
        assert_eq!(
            poll(&mut g, lease.token_bits(), OUT, 512, LENGTH).unwrap(),
            Some(Value::I32(0))
        );
        p.ack_exit(&lease).unwrap();
        assert_eq!(p.usage().unwrap().outstanding_requests, 0);
    }
}
#[test]
fn direct_indirect_and_exported_import_return_paths_agree() {
    for indirect in [false, true] {
        let mut s = Spec::default();
        if indirect {
            s.table = Some(vec![1]);
            s.functions[1].code = vec![0x20, 0, 0x20, 1, 0x20, 2, 0x41, 0, 0x11, 0, 0, 0x0b];
        }
        let (mut g, p) = enabled(&s);
        assert_eq!(
            enqueue(&mut g, "run", 0, ARG.len() as u32, TOKEN).unwrap(),
            Some(Value::I32(0))
        );
        let (lease, _) = take(&p);
        p.ack_exit(&lease).unwrap();
    }
}
#[test]
fn indirect_null_and_wrong_signature_trap_before_capability_mutation() {
    for (target, selector, expected) in [
        (1, 1, "indirect_call_null"),
        (4, 0, "indirect_call_type_mismatch"),
    ] {
        let mut s = Spec {
            table: Some(vec![target]),
            table_spare: 1,
            ..Spec::default()
        };
        s.functions[1].code = vec![0x20, 0, 0x20, 1, 0x20, 2, 0x41, selector, 0x11, 0, 0, 0x0b];
        let (mut g, p) = enabled(&s);
        let before = g.memory().to_vec();
        assert_eq!(
            enqueue(&mut g, "run", 0, ARG.len() as u32, TOKEN)
                .unwrap_err()
                .code,
            expected
        );
        assert_eq!(g.memory(), before);
        assert_eq!(p.usage().unwrap().outstanding_requests, 0);
        assert!(matches!(p.take(&mut []), Err(mb::Error::SessionClosed)));
    }
}
#[test]
fn reservation_exact_boundary_accepts_and_one_byte_short_rejects_atomically() {
    for short in [false, true] {
        let s = Spec::default();
        let mut g = CapabilityGuest::new(
            &s.bytes(),
            l(),
            mb::Limits {
                reservation_bytes: mb::MAX_PAYLOAD_BYTES + ARG.len() - usize::from(short),
                ..mb::Limits::default()
            },
            GuestLimits::default(),
            "start",
        )
        .unwrap();
        g.startup().unwrap();
        g.enable_effects().unwrap();
        let before = g.memory().to_vec();
        assert_eq!(
            enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap(),
            Some(Value::I32(if short { 5 } else { 0 }))
        );
        let usage = g.native_port().usage().unwrap();
        assert_eq!(
            usage.reserved_bytes,
            if short {
                0
            } else {
                mb::MAX_PAYLOAD_BYTES + ARG.len()
            }
        );
        if short {
            assert_eq!(g.memory(), before);
        } else {
            assert_eq!(token(&g, TOKEN), 1u64 << 32 | 1);
        }
    }
}
#[test]
fn invalid_guest_ranges_never_write_or_issue_request() {
    for (start, len, token_at) in [
        (0, 0, TOKEN),
        (0, 524289, TOKEN),
        (u32::MAX, 1, TOKEN),
        (0, ARG.len() as u32, u32::MAX),
        (0, 8, 0),
        (0, 8, 7),
        (65535, 2, TOKEN),
        (0, 1, 65529),
    ] {
        let (mut g, p) = enabled(&Spec::default());
        let before = g.memory().to_vec();
        assert_eq!(
            enqueue(&mut g, "get", start, len, token_at).unwrap(),
            Some(Value::I32(3))
        );
        assert_eq!(g.memory(), before);
        assert_eq!(p.usage().unwrap().outstanding_requests, 0);
    }
}
#[test]
fn poll_pending_small_ready_and_repeat_are_atomic() {
    let (mut g, p) = enabled(&Spec::default());
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let bits = token(&g, TOKEN);
    assert_eq!(
        poll(&mut g, bits, OUT, 0, LENGTH).unwrap(),
        Some(Value::I32(1))
    );
    assert_eq!(length(&g), 0);
    let (lease, _) = take(&p);
    let bytes = b"complete opaque reply";
    p.post_trusted(&lease, bytes).unwrap();
    let before = g.memory()[OUT as usize..OUT as usize + 512].to_vec();
    assert_eq!(
        poll(&mut g, bits, OUT, bytes.len() as u32 - 1, LENGTH).unwrap(),
        Some(Value::I32(2))
    );
    assert_eq!(length(&g), bytes.len() as u32);
    assert_eq!(&g.memory()[OUT as usize..OUT as usize + 512], before);
    assert_eq!(
        poll(&mut g, bits, OUT, 512, LENGTH).unwrap(),
        Some(Value::I32(0))
    );
    assert_eq!(&g.memory()[OUT as usize..OUT as usize + bytes.len()], bytes);
    assert_eq!(
        poll(&mut g, bits, OUT, 512, LENGTH).unwrap(),
        Some(Value::I32(4))
    );
    assert_eq!(p.usage().unwrap().native_leases, 1);
    p.ack_exit(&lease).unwrap();
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
}
#[test]
fn poll_invalid_full_capacity_overlap_and_zero_capacity_edge() {
    for (out, cap, len) in [
        (65536, 1, LENGTH),
        (u32::MAX, 0, LENGTH),
        (OUT, 524289, LENGTH),
        (OUT, 1, u32::MAX),
        (LENGTH - 1, 2, LENGTH),
        (OUT, 512, OUT + 511),
    ] {
        let (mut g, p) = enabled(&Spec::default());
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
        let bits = token(&g, TOKEN);
        let before = g.memory().to_vec();
        assert_eq!(
            poll(&mut g, bits, out, cap, len).unwrap(),
            Some(Value::I32(3))
        );
        assert_eq!(g.memory(), before);
        assert_eq!(p.usage().unwrap().outstanding_requests, 1);
    }
    let (mut g, _) = enabled(&Spec::default());
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let bits = token(&g, TOKEN);
    assert_eq!(
        poll(&mut g, bits, 65536, 0, LENGTH).unwrap(),
        Some(Value::I32(1))
    );
    assert_eq!(
        poll(&mut g, bits, LENGTH + 1, 0, LENGTH).unwrap(),
        Some(Value::I32(1))
    );
}
#[test]
fn malformed_raw_tokens_cannot_select_other_owner_or_generation() {
    let (mut a, pa) = enabled(&Spec::default());
    let (mut b, pb) = enabled(&Spec::default());
    enqueue(&mut a, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    enqueue(&mut b, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let ta = token(&a, TOKEN);
    let tb = token(&b, TOKEN);
    assert_eq!(ta, tb);
    let (lease, _) = take(&pa);
    assert_eq!(
        pb.post_trusted(&lease, b"foreign"),
        Err(mb::Error::StaleRequest)
    );
    for raw in [
        0,
        1,
        1u64 << 32,
        (1u64 << 32) | 9,
        (2u64 << 32) | 1,
        u64::MAX,
    ] {
        let before = b.memory().to_vec();
        assert_eq!(
            poll(&mut b, raw, OUT, 512, LENGTH).unwrap(),
            Some(Value::I32(4))
        );
        assert_eq!(b.memory(), before);
        assert_eq!(
            b.invoke("cancel", &[Value::I64(raw as i64)]).unwrap(),
            Some(Value::I32(4))
        );
    }
    assert_eq!(
        b.invoke("cancel", &[Value::I64(ta as i64)]).unwrap(),
        Some(Value::I32(0))
    );
    assert_eq!(pa.usage().unwrap().native_leases, 1);
    pa.ack_exit(&lease).unwrap();
}
#[test]
fn generated_builtin_failures_have_exact_lengths_bytes_and_hashes() {
    for name in ["http", "get", "put", "delete"] {
        for reason in ["unavailable", "cancelled", "deadlineExceeded"] {
            let s = Spec::default();
            let mut g = build(&s);
            let p = g.native_port();
            g.startup().unwrap();
            if reason != "unavailable" {
                g.enable_effects().unwrap();
            }
            enqueue(&mut g, name, 0, ARG.len() as u32, TOKEN).unwrap();
            let bits = token(&g, TOKEN);
            if reason == "cancelled" {
                assert_eq!(
                    g.invoke("cancel", &[Value::I64(bits as i64)]).unwrap(),
                    Some(Value::I32(0))
                );
                assert_eq!(
                    g.invoke("cancel", &[Value::I64(bits as i64)]).unwrap(),
                    Some(Value::I32(7))
                );
            }
            if reason == "deadlineExceeded" {
                let (lease, _) = take(&p);
                p.limit_deadline(&lease, 1).unwrap();
                std::thread::sleep(std::time::Duration::from_millis(2));
                p.expire().unwrap();
                p.ack_exit(&lease).unwrap();
            }
            let expected = expected(name, reason);
            assert_eq!(
                poll(&mut g, bits, OUT, 0, LENGTH).unwrap(),
                Some(Value::I32(2))
            );
            assert_eq!(length(&g), expected.len() as u32);
            assert_eq!(
                poll(&mut g, bits, OUT, 512, LENGTH).unwrap(),
                Some(Value::I32(0))
            );
            assert_eq!(
                &g.memory()[OUT as usize..OUT as usize + expected.len()],
                expected
            );
        }
    }
}
#[test]
fn byte_fuel_is_charged_before_token_or_length_writes() {
    for fuel in [1, 2] {
        let s = Spec::default();
        let mut limits = l();
        limits.fuel = fuel;
        let mut g = CapabilityGuest::new(
            &s.bytes(),
            limits,
            mb::Limits::default(),
            GuestLimits::default(),
            "start",
        )
        .unwrap();
        g.startup().unwrap();
        g.enable_effects().unwrap();
        let p = g.native_port();
        let before = g.memory().to_vec();
        let result = enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN);
        if fuel == 1 {
            let e = result.unwrap_err();
            assert_eq!(e.code, "fuel_exhausted");
            assert_eq!(e.function, Some(1));
            assert_eq!(g.memory(), before);
            assert_eq!(p.usage().unwrap().outstanding_requests, 0);
        } else {
            assert_eq!(result.unwrap(), Some(Value::I32(0)));
            assert_eq!(g.fuel_remaining(), 0);
        }
    }
    // Pending writes its4-byte word: exported poll uses dispatch1 + byte1.
    let s = Spec::default();
    let mut limits = l();
    limits.fuel = 2;
    let mut g = CapabilityGuest::new(
        &s.bytes(),
        limits,
        mb::Limits::default(),
        GuestLimits::default(),
        "start",
    )
    .unwrap();
    g.startup().unwrap();
    g.enable_effects().unwrap();
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let bits = token(&g, TOKEN);
    assert_eq!(
        poll(&mut g, bits, OUT, 0, LENGTH).unwrap(),
        Some(Value::I32(1))
    );
    assert_eq!(g.fuel_remaining(), 0);
    assert_eq!(g.host_calls_used(), 1);
}
#[test]
fn successful_turn_publication_and_trapping_turn_discard() {
    let mut s = Spec::default();
    s.functions[1] = Function::new(vec![], None, {
        let mut c = constant(Value::I32(0));
        c.extend(constant(Value::I32(ARG.len() as i32)));
        c.extend(constant(Value::I32(TOKEN as i32)));
        c.extend([0x10, 1, 0x1a, 0, 0x0b]);
        c
    });
    let (mut g, p) = enabled(&s);
    assert_eq!(g.invoke("run", &[]).unwrap_err().code, "unreachable");
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
    assert_eq!(p.take(&mut [0; 64]).err(), Some(mb::Error::SessionClosed));
    assert!(g.invoke("get", &[]).is_err());
}
#[test]
fn snapshots_survive_guest_memory_mutation_and_growth() {
    let mut s = Spec::default();
    s.functions[1] = Function::new(
        vec![],
        None,
        vec![
            0x41, 0, 0x41, 0xc1, 0, 0x3a, 0, 0, 0x41, 1, 0x40, 0, 0x1a, 0x0b,
        ],
    );
    let (mut g, p) = enabled(&s);
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    g.invoke("run", &[]).unwrap();
    assert_eq!(g.memory()[0], 65);
    assert_eq!(g.memory().len(), 2 * 65536);
    let (lease, b) = take(&p);
    assert_eq!(b, ARG);
    p.ack_exit(&lease).unwrap();
}
#[test]
fn quotas_do_not_write_or_advance_and_generation_reuse_is_stale() {
    let s = Spec::default();
    let mut g = CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits {
            maximum_requests: 1,
            ..mb::Limits::default()
        },
        GuestLimits::default(),
        "start",
    )
    .unwrap();
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let first = token(&g, TOKEN);
    let before = g.memory().to_vec();
    assert_eq!(
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN + 16).unwrap(),
        Some(Value::I32(5))
    );
    assert_eq!(g.memory(), before);
    g.invoke("cancel", &[Value::I64(first as i64)]).unwrap();
    poll(&mut g, first, OUT, 512, LENGTH).unwrap();
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let second = token(&g, TOKEN);
    assert_eq!(second, first + (1u64 << 32));
    assert_eq!(
        poll(&mut g, first, OUT, 512, LENGTH).unwrap(),
        Some(Value::I32(4))
    );
    assert_eq!(p.usage().unwrap().outstanding_requests, 1);
}
#[test]
fn close_and_drop_retain_native_exit_obligations() {
    for explicit in [false, true] {
        let (mut g, p) = enabled(&Spec::default());
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
        let (lease, _) = take(&p);
        if explicit {
            let report = g.close().unwrap();
            assert_eq!(report.cancellations.iter().flatten().count(), 1);
        }
        drop(g);
        assert!(p.usage().unwrap().closed);
        assert_eq!(p.usage().unwrap().native_leases, 1);
        assert_eq!(p.take(&mut [0; 64]).err(), Some(mb::Error::SessionClosed));
        assert_eq!(
            p.post_trusted(&lease, b"late"),
            Err(mb::Error::SessionClosed)
        );
        p.ack_exit(&lease).unwrap();
        assert_eq!(p.usage().unwrap().reserved_bytes, 0);
        assert_eq!(p.ack_exit(&lease), Err(mb::Error::StaleRequest));
    }
}
#[test]
fn coalesced_wake_executes_only_after_turn_and_uses_fixed_export() {
    let (mut g, p) = enabled(&Spec::default());
    assert!(!g.wake_once().unwrap());
    for at in [TOKEN, TOKEN + 32] {
        enqueue(&mut g, "get", 0, ARG.len() as u32, at).unwrap();
        let (lease, _) = take(&p);
        p.post_trusted(&lease, b"ready").unwrap();
        p.ack_exit(&lease).unwrap();
    }
    assert!(g.wake_once().unwrap()); // This no-op wake leaves terminal work, so one later turn remains ready.
    assert!(g.wake_once().unwrap());
    for at in [TOKEN, TOKEN + 32] {
        let bits = token(&g, at);
        poll(&mut g, bits, OUT, 512, LENGTH).unwrap();
    }
    assert!(!g.wake_once().unwrap());
}
#[test]
fn whole_guest_cancellation_is_distinct_and_permanent() {
    let (mut g, p) = enabled(&Spec::default());
    let cancellation = g.cancellation();
    cancellation.cancel();
    assert_eq!(g.invoke("run", &[]).unwrap_err().code, "capability_closed");
    assert_eq!(p.take(&mut [0; 64]).err(), Some(mb::Error::SessionClosed));
    assert!(g.enable_effects().is_err());
    assert!(g.wake_once().is_err());
}
#[test]
fn cooperative_turn_timeout_closes_infinite_wasm_turn() {
    let mut s = Spec::default();
    s.functions[1] = Function::new(vec![], None, vec![3, 0x40, 0x0c, 0, 0x0b, 0x0b]);
    let mut g = CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits::default(),
        GuestLimits {
            turn_milliseconds: 1,
        },
        "start",
    )
    .unwrap();
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    assert_eq!(
        g.invoke("run", &[]).unwrap_err().code,
        "capability_turn_timeout"
    );
    assert!(p.usage().unwrap().closed);
}

#[test]
fn ready_poll_byte_fuel_traps_before_any_output_and_keeps_native_lease_ackable() {
    for fuel in [3, 4] {
        let s = Spec::default();
        let mut limits = l();
        limits.fuel = fuel;
        let mut g = CapabilityGuest::new(
            &s.bytes(),
            limits,
            mb::Limits::default(),
            GuestLimits::default(),
            "start",
        )
        .unwrap();
        g.startup().unwrap();
        g.enable_effects().unwrap();
        let p = g.native_port();
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
        let (lease, _) = take(&p);
        p.post_trusted(&lease, &[0x42; 128]).unwrap();
        let before = g.memory().to_vec();
        let result = poll(&mut g, lease.token_bits(), OUT, 128, LENGTH);
        if fuel == 3 {
            assert_eq!(result.unwrap_err().code, "fuel_exhausted");
            assert_eq!(g.memory(), before);
            assert_eq!(p.usage().unwrap().native_leases, 1);
            assert!(p.usage().unwrap().closed);
        } else {
            assert_eq!(result.unwrap(), Some(Value::I32(0)));
            assert_eq!(length(&g), 128);
            assert_eq!(g.fuel_remaining(), 0);
        }
        p.ack_exit(&lease).unwrap();
        assert_eq!(p.usage().unwrap().reserved_bytes, 0);
    }
}
#[test]
fn host_call_ceiling_is_independent_and_failed_import_writes_nothing() {
    let s = Spec::default();
    let mut limits = l();
    limits.host_calls = 0;
    let mut g = CapabilityGuest::new(
        &s.bytes(),
        limits,
        mb::Limits::default(),
        GuestLimits::default(),
        "start",
    )
    .unwrap();
    g.startup().unwrap();
    g.enable_effects().unwrap();
    let p = g.native_port();
    let before = g.memory().to_vec();
    assert_eq!(
        enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN)
            .unwrap_err()
            .code,
        "host_call_limit"
    );
    assert_eq!(g.memory(), before);
    assert_eq!(g.host_calls_used(), 0);
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
}
#[test]
fn taken_cancellation_controls_do_not_create_exit_acknowledgements() {
    let (mut g, p) = enabled(&Spec::default());
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let (lease, _) = take(&p);
    let bits = lease.token_bits();
    assert_eq!(
        g.invoke("cancel", &[Value::I64(bits as i64)]).unwrap(),
        Some(Value::I32(0))
    );
    assert_eq!(
        p.post_trusted(&lease, b"late"),
        Err(mb::Error::AlreadyTerminal)
    );
    match p.take(&mut []).unwrap() {
        NativeTake::Cancel { lease: control } => {
            assert_eq!(control.token_bits(), bits);
            drop(control);
        }
        _ => panic!("expected cancel"),
    }
    assert!(matches!(p.take(&mut []).unwrap(), NativeTake::None));
    assert_eq!(p.usage().unwrap().native_leases, 1);
    poll(&mut g, bits, OUT, 512, LENGTH).unwrap();
    assert_eq!(p.usage().unwrap().native_leases, 1);
    p.ack_exit(&lease).unwrap();
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
}
#[test]
fn early_exit_cannot_post_or_release_pending_guest_delivery() {
    let (mut g, p) = enabled(&Spec::default());
    enqueue(&mut g, "get", 0, ARG.len() as u32, TOKEN).unwrap();
    let (lease, _) = take(&p);
    p.ack_exit(&lease).unwrap();
    assert_eq!(
        p.post_trusted(&lease, b"after exit"),
        Err(mb::Error::AlreadyAcknowledged)
    );
    assert_eq!(p.usage().unwrap().outstanding_requests, 1);
    g.invoke("cancel", &[Value::I64(lease.token_bits() as i64)])
        .unwrap();
    poll(&mut g, lease.token_bits(), OUT, 512, LENGTH).unwrap();
    assert_eq!(p.usage().unwrap().outstanding_requests, 0);
}
#[test]
fn actual_turn_blocks_native_take_until_success_or_external_cancel() {
    let mut s = Spec::default();
    let mut code = constant(Value::I32(0));
    code.extend(constant(Value::I32(ARG.len() as i32)));
    code.extend(constant(Value::I32(TOKEN as i32)));
    code.extend([0x10, 1, 0x1a, 3, 0x40, 0x0c, 0, 0x0b, 0x0b]);
    s.functions[1] = Function::new(vec![], None, code);
    let (mut g, p) = enabled(&s);
    let cancellation = g.cancellation();
    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let ready = barrier.clone();
    let worker = std::thread::spawn(move || {
        ready.wait();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(2);
        loop {
            let u = p.usage().unwrap();
            if u.turn_active && u.outstanding_requests == 1 {
                let blocked = matches!(p.take(&mut [0; 128]).unwrap(), NativeTake::None);
                cancellation.cancel();
                return blocked;
            }
            if u.closed || std::time::Instant::now() > deadline {
                return false;
            }
            std::hint::spin_loop();
        }
    });
    barrier.wait();
    assert_eq!(g.invoke("run", &[]).unwrap_err().code, "cancelled");
    assert!(worker.join().unwrap());
}
#[test]
fn maximum_payload_length_and_full_mailbox_reservation_are_bounded() {
    let s = Spec {
        memory: Some((10, 10)),
        data: vec![(0, vec![0x41; mb::MAX_PAYLOAD_BYTES])],
        ..Spec::default()
    };
    let (mut g, p) = enabled(&s);
    let at = 600_001;
    for _ in 0..8 {
        assert_eq!(
            enqueue(&mut g, "put", 0, mb::MAX_PAYLOAD_BYTES as u32, at).unwrap(),
            Some(Value::I32(0))
        );
    }
    assert_eq!(p.usage().unwrap().reserved_bytes, mb::MAX_RESERVATION_BYTES);
    let before = g.memory().to_vec();
    assert_eq!(
        enqueue(&mut g, "put", 0, 1, at + 8).unwrap(),
        Some(Value::I32(5))
    );
    assert_eq!(g.memory(), before);
    let mut leases = vec![];
    for _ in 0..8 {
        let (lease, arguments) = take(&p);
        assert_eq!(arguments.len(), mb::MAX_PAYLOAD_BYTES);
        p.post_trusted(&lease, &vec![0x42; mb::MAX_PAYLOAD_BYTES])
            .unwrap();
        leases.push(lease);
    }
    assert_eq!(p.usage().unwrap().argument_bytes, 4 * 1024 * 1024);
    assert_eq!(p.usage().unwrap().completion_bytes, 4 * 1024 * 1024);
    for lease in leases {
        assert_eq!(
            poll(
                &mut g,
                lease.token_bits(),
                0,
                mb::MAX_PAYLOAD_BYTES as u32,
                600_020
            )
            .unwrap(),
            Some(Value::I32(0))
        );
        p.ack_exit(&lease).unwrap();
    }
    assert_eq!(p.usage().unwrap().reserved_bytes, 0);
}
#[test]
fn uncalled_malformed_body_and_imported_void_wake_fail_full_validation() {
    let mut s = Spec::default();
    s.functions
        .push(Function::new(vec![], None, vec![0, 0xff, 0x0b]));
    assert!(CapabilityGuest::new(
        &s.bytes(),
        l(),
        mb::Limits::default(),
        GuestLimits::default(),
        "start"
    )
    .is_err());
    let mut s = Spec::default();
    s.imports[0] = ("mixer".into(), "checkpoint".into(), vec![], None);
    s.wake_index = Some(0);
    assert!(
        matches!(CapabilityGuest::new(&s.bytes(),l(),mb::Limits::default(),GuestLimits::default(),"start"),Err(e)if e.code=="capability_export")
    );
}
