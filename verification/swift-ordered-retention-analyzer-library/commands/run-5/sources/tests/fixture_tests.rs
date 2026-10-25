use super::*;
use std::mem::size_of;

// Independently encode fixture bytes here; never import the frozen writer.
fn words(values: &[u64]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(values.len() * 8);
    for value in values { bytes.extend_from_slice(&value.to_le_bytes()); }
    bytes
}
fn put(bytes: &mut [u8], word: usize, value: u64) { bytes[8 * word..8 * word + 8].copy_from_slice(&value.to_le_bytes()); }
fn get(bytes: &[u8], word: usize) -> u64 { u64::from_le_bytes(bytes[8 * word..8 * word + 8].try_into().unwrap()) }
fn fixture() -> Fixture { Fixture { cap: 1024, mask: 33, extent: 1_000_000, types: 2, slots: 4, pins: 4, base: 64, capacity: 4096, entry: 512 } }
fn context_bytes(f: Fixture) -> Vec<u8> {
    let mut out = vec![0; 8192];
    for (i, value) in [FIXTURE_MAGIC, 1, 8192, 1, f.cap, f.mask, f.extent, f.types, f.slots, f.pins, 1, f.base, f.capacity, f.entry, 0, 0].iter().enumerate() { put(&mut out, i, *value); }
    for i in 0..8 { out[128 + i * 32..160 + i * 32].fill((i + 1) as u8); }
    out
}
fn profile_bytes(f: Fixture) -> Vec<u8> {
    let mut out = vec![0; PROFILE_BYTES as usize];
    for (i, value) in [PROFILE_MAGIC, 1, 512, 32, 80000, f.extent, f.types, f.slots, f.pins, 1, f.base, f.capacity, f.entry, 0, 0, 0].iter().enumerate() { put(&mut out, i, *value); }
    out[128..160].fill(7); out[160..192].fill(8); out[224..256].fill(2);
    for row in 0..80000 { let off = 512 + row * 32; put(&mut out[off..off + 32], 0, (u32::MAX as u64) << 32); put(&mut out[off..off + 32], 1, ABSENT); }
    for row in [0, 1, 511, 512, 79999] { let off = 512 + row * 32; put(&mut out[off..off + 32], 0, (1u64 << 32) | 1); put(&mut out[off..off + 32], 1, 16 + row as u64 * 4); put(&mut out[off..off + 32], 2, 8); }
    out
}
fn head(f: Fixture) -> [u64; 64] {
    let mut h = [0; 64]; h[..10].copy_from_slice(&[HEADER_MAGIC, 1, 512, 128, 512, f.cap, 80000, 64, 512, f.mask]);
    for (slot, byte) in [(16, 1u8), (20, 2), (24, 7), (28, 8)] { for i in 0..4 { h[slot + i] = u64::from_le_bytes([byte; 8]); } }
    h
}
fn event(kind: u64) -> [u64; 16] {
    let mut w = [1, kind, 0, 1, 10, 20, 1, 20, 8, 1, ABSENT, ABSENT, 0, 0, 0, 0];
    match kind {
        1 => { w[7..10].fill(ABSENT); }
        2 => {}
        3 => { w[15] = 1; }
        4 => { w[14] = ABSENT; w[15] = 1; }
        5 => { w[13..16].copy_from_slice(&[128, 64, 4096]); }
        6..=8 => { w[10] = 0; w[13] = 128; }
        9 | 10 => { w[13] = 128; }
        11 => { w[10..16].copy_from_slice(&[0, 0, 1, 1, 128, 1]); }
        12 => { w[3] = 0; w[8] = ABSENT; w[10..16].copy_from_slice(&[0, 0, 1, 128, 0, 0]); }
        13 => { w[2] = 5; w[3] = 0; w[6..10].fill(ABSENT); w[13] = 5; }
        14 => { w[3] = 0; w[6..10].fill(ABSENT); w[13..16].copy_from_slice(&[10, 3, 4]); }
        _ => panic!("unsupported test kind"),
    }
    w
}
fn stream_bytes(f: Fixture, events: &[[u64; 16]], cap: bool) -> Vec<u8> {
    let h = head(f); let mut out = words(&h);
    let mut last = [0; 16]; let mut operation = 0;
    for (i, event) in events.iter().enumerate() { let mut w = *event; w[0] = i as u64 + 1; if w[1] == 1 { operation = w[3]; } out.extend_from_slice(&words(&w)); last = w; }
    let mut ft = [0; 64];
    ft[..16].copy_from_slice(&[FOOTER_MAGIC, 1, events.len() as u64, events.len() as u64 + u64::from(cap), u64::from(cap), events.len() as u64, last[4], last[5], operation, u64::from(cap), last[4], last[5], 0, 0, ABSENT, f.mask]);
    ft[33] = 5; ft[34] = 1; ft[35] = f.cap; ft[36..44].copy_from_slice(&h[16..24]); out.extend_from_slice(&words(&ft)); out
}

#[derive(Clone)]
struct Memory {
    bytes: Vec<u8>, pos: usize, quantum: usize, interrupts: usize, calls: usize,
    zero: bool, fail: bool, overreport: bool, regular: bool, declared_len: Option<u64>,
    stamp_calls: usize, drift: bool, stamp_fail: bool, position_fail: bool, identity: u64,
}
impl Memory {
    fn new(bytes: Vec<u8>) -> Self { Self { bytes, pos: 0, quantum: usize::MAX, interrupts: 0, calls: 0, zero: false, fail: false, overreport: false, regular: true, declared_len: None, stamp_calls: 0, drift: false, stamp_fail: false, position_fail: false, identity: 1 } }
    fn snapshot(&mut self) -> io::Result<Stamp> {
        self.stamp_calls += 1;
        if self.stamp_fail { return Err(io::ErrorKind::PermissionDenied.into()); }
        Ok(Stamp { fields: [1, if self.drift && self.stamp_calls > 2 { self.identity+10 } else { self.identity }, 0o100600, self.declared_len.unwrap_or(self.bytes.len() as u64), 0, 0, 0, 0], regular: u64::from(self.regular) })
    }
    fn position_value(&mut self) -> io::Result<u64> { if self.position_fail { Err(io::ErrorKind::Other.into()) } else { Ok(self.pos as u64) } }
}
impl Read for Memory {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        self.calls += 1;
        if self.interrupts > 0 { self.interrupts -= 1; return Err(io::ErrorKind::Interrupted.into()); }
        if self.fail { return Err(io::ErrorKind::Other.into()); }
        if self.overreport { return Ok(out.len() + 1); }
        if self.zero { return Ok(0); }
        let n = out.len().min(self.bytes.len().saturating_sub(self.pos)).min(self.quantum);
        out[..n].copy_from_slice(&self.bytes[self.pos..self.pos + n]); self.pos += n; Ok(n)
    }
}
impl Write for Memory {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.calls += 1;
        if self.interrupts > 0 { self.interrupts -= 1; return Err(io::ErrorKind::Interrupted.into()); }
        if self.fail { return Err(io::ErrorKind::Other.into()); }
        if self.overreport { return Ok(bytes.len() + 1); }
        if self.zero { return Ok(0); }
        let n = bytes.len().min(self.quantum);
        if self.pos + n > self.bytes.len() { self.bytes.resize(self.pos + n, 0); }
        self.bytes[self.pos..self.pos + n].copy_from_slice(&bytes[..n]); self.pos += n; Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> { Ok(()) }
}
impl InputFile for Memory { fn stamp(&mut self) -> io::Result<Stamp> { self.snapshot() } fn position(&mut self) -> io::Result<u64> { self.position_value() } }
impl OutputFile for Memory { fn stamp(&mut self) -> io::Result<Stamp> { self.snapshot() } fn position(&mut self) -> io::Result<u64> { self.position_value() } }
fn inputs(events: &[[u64; 16]], cap: bool) -> (Memory, Memory, Memory, Memory) {
    let mut f = fixture(); if cap { f.cap = events.len() as u64; }
    let mut all=(Memory::new(stream_bytes(f, events, cap)), Memory::new(profile_bytes(f)), Memory::new(context_bytes(f)), Memory::new(vec![]));
    all.1.identity=2;all.2.identity=3;all.3.identity=4;all
}
fn invoke(x: &mut (Memory, Memory, Memory, Memory)) -> ReplayOutcome { analyze_core(&mut x.0, &mut x.1, &mut x.2, &mut x.3, STEP_LIMIT).unwrap() }
fn loaded() -> (Arena, Budget, Fixture) {
    let mut budget = Budget::new(STEP_LIMIT).unwrap(); let mut arena = Arena::new(&mut budget).unwrap(); let f = fixture();
    fixture_context(&mut Memory::new(context_bytes(f)), &mut arena, &mut budget).unwrap();
    profile(&mut Memory::new(profile_bytes(f)), &mut arena, &mut budget, f).unwrap(); (arena, budget, f)
}

#[test]
fn no_fixture_can_grant_acceptance_or_populate_semantic_metrics() {
    let mut x = inputs(&[event(13)], false); let out = invoke(&mut x);
    assert_eq!(out.decision, Decision::Unavailable); assert!(out.fixture_framing_observed());
    assert!(!out.stored_prefix_validated()); assert!(!out.full_replay_accepted()); assert_eq!(out.framed_records, 1);
    assert_eq!(x.3.bytes.len(), REPORT_BYTES); assert_eq!(out.report_bytes, REPORT_BYTES as u64);
    assert_eq!(get(&x.3.bytes, 0), REPORT_MAGIC); assert_eq!(get(&x.3.bytes, 4), 0); assert_eq!(get(&x.3.bytes, 5), 0); assert_eq!(get(&x.3.bytes, 15), 1);
    assert!(x.3.bytes[512..].iter().all(|b| *b == 0));
    assert_eq!(out.input_bytes_read, (8192 + PROFILE_BYTES as usize + x.0.bytes.len()) as u64);
    assert_eq!(get(&x.3.bytes, 9), out.steps_used); assert!(out.steps_used < STEP_LIMIT);
    // A semantically impossible BuildReady still has legal wire fields. Prove
    // that syntax success is unavailable rather than an accepted prefix.
    let mut events = [event(1), event(10), event(13)]; events[2][4] = 10; events[2][5] = 20;
    let mut x = inputs(&events, false); let out = invoke(&mut x);
    assert!(out.fixture_framing_observed()); assert!(!out.stored_prefix_validated()); assert_eq!(out.decision, Decision::Unavailable);
}

#[test]
fn arena_checked_regions_fields_overflow_and_sentinels() {
    let (mut arena, _, _) = loaded();
    for r in REGIONS { assert!(Arena::range(r, r.rows, 0, 8).is_err()); assert!(Arena::range(r, 0, r.stride - 3, 8).is_err()); }
    assert!(Arena::range(Region { base: usize::MAX, rows: 3, stride: 8 }, 0, 0, 8).is_err());
    assert!(Arena::range(Region { base: 0, rows: usize::MAX, stride: usize::MAX }, 1, 0, 8).is_err());
    assert!(arena.put64(FUNCTION, 0, 93, 1).is_err()); assert!(arena.put32(FUNCTION, 80000, 0, 1).is_err());
    assert_eq!(arena.get64(RESIDENT, 63, 8), Ok(ABSENT)); assert_eq!(arena.get64(PIN, 63, 0), Ok(ABSENT));
    assert_eq!(arena.get64(WINDOW, 127, 112), Ok(ABSENT)); assert_eq!(arena.get32(FUNCTION, 79999, 40), Ok(u32::MAX));
    assert!(arena.bytes[7_873_120..].iter().all(|b| *b == 0));
}

#[test]
fn allocation_refusal_capacity_mismatch_and_initialization_budget() {
    fn no(v: &mut Vec<u8>, _: usize) -> Result<(), TryReserveError> { v.try_reserve_exact(usize::MAX) }
    fn extra(v: &mut Vec<u8>, n: usize) -> Result<(), TryReserveError> { v.try_reserve_exact(n + 1) }
    let mut b = Budget::new(STEP_LIMIT).unwrap(); assert_eq!(Arena::new_with(&mut b, no).err().unwrap().code, ALLOCATION);
    assert_eq!(Arena::new_with(&mut b, extra).err().unwrap().code, CAPACITY);
    let mut b = Budget::new(REPORT_RESERVE + IO_RESERVE + 10).unwrap(); assert_eq!(Arena::new(&mut b).err().unwrap().code, BUDGET);
    assert!(Budget::new(REPORT_RESERVE + IO_RESERVE - 1).is_err()); assert!(Budget::new(STEP_LIMIT + 1).is_err());
}

#[test]
fn header_every_scalar_reserved_word_and_digest_echo_mutations() {
    let (arena, mut b, f) = loaded(); let h = head(f); header(&arena, &h, f, &mut b).unwrap();
    for i in 0..64 { let mut candidate = h; candidate[i] ^= 1; assert!(header(&arena, &candidate, f, &mut b).is_err(), "header word {i}"); }
    for cap in [0, MAX_RECORDS + 1, ABSENT] { let mut candidate = h; candidate[5] = cap; assert!(header(&arena, &candidate, f, &mut b).is_err()); }
}

#[test]
fn record_all_kinds_closed_fields_and_immutable_identity() {
    let (arena, _, f) = loaded(); let mut checks = 0;
    for kind in 1..=14 {
        let w = event(kind); assert!(record_fields(&arena, &w, f), "kind {kind}");
        for (field, value) in [(0, 0), (1, 0), (1, 15), (2, 6)] { let mut x = w; x[field] = value; assert!(!record_fields(&arena, &x, f)); checks += 1; }
        for field in 7..10 { let mut x = w; x[field] = if w[field] == ABSENT { 0 } else { ABSENT }; assert!(!record_fields(&arena, &x, f), "kind{kind} body{field}"); checks += 1; }
        if (2..=11).contains(&kind) || kind == 12 {
            for (field, value) in [(6, 80000), (6, 2), (7, 21), (9, 0), (9, 2), (9, (u32::MAX as u64) + 1)] { let mut x = w; x[field] = value; assert!(!record_fields(&arena, &x, f), "kind{kind} identity{field}"); checks += 1; }
        }
        for field in 10..13 {
            let mut x = w; x[field] = match field { 10 | 11 => if w[field] == ABSENT { 0 } else { 64 }, _ => if w[field] == 0 { 1 } else { 0 } };
            assert!(!record_fields(&arena, &x, f), "kind{kind} slot{field}"); checks += 1;
        }
    }
    for (kind, field, value) in [(1, 3, 0),(1, 6,80000),(1,13,1),(1,14,1),(1,15,1),(2,13,2),(2,14,1),(2,15,1),(3,13,1),(3,14,1),(3,15,512),(4,13,3),(4,14,0),(4,15,512),(5,13,0),(5,13,513),(5,14,65),(5,15,4095),(6,13,0),(7,14,1),(8,15,1),(9,13,0),(10,13,513),(11,13,2),(11,14,0),(11,15,0),(11,15,5),(12,3,1),(12,13,0),(12,14,1),(12,15,4),(13,3,1),(13,6,0),(13,13,4),(13,14,1),(13,15,1),(14,6,80000),(14,13,0),(14,13,22),(14,14,0),(14,14,25),(14,15,0),(14,15,7)] { let mut w = event(kind); w[field] = value; assert!(!record_fields(&arena, &w, f), "kind{kind} field{field}"); checks += 1; }
    println!("RECORD_FIELD_NEGATIVES={checks}");
}

#[test]
fn footer_all_scalars_ranges_opaque_ledger_and_cap_shape() {
    let f = fixture(); let h = head(f); let bytes = stream_bytes(f, &[event(13)], false);
    let raw = &bytes[bytes.len()-512..]; let mut ft = [0; 64]; for (i,w) in ft.iter_mut().enumerate() { *w = get(raw,i); }
    let mut s = Framing::new(1); s.coordinate(&event(13)); let mut b = Budget::new(STEP_LIMIT).unwrap();
    footer(&h,&ft,bytes.len() as u64,&mut s,&mut b).unwrap();
    for i in 0..64 {
        let mut x = ft; x[i] ^= 1; let mut state = s;
        let result = footer(&h,&x,bytes.len() as u64,&mut state,&mut b);
        // Explicitly unconstrained fields are original-result observations,
        // not a real original-result adapter or accepted-ledger comparison.
        let opaque = (16..=31).contains(&i) || [10,11,34].contains(&i);
        if opaque { assert!(result.is_ok(), "opaque footer word{i}"); } else { assert!(result.is_err(), "closed footer word{i}"); }
    }
    for (field,value) in [(9,2),(9,128),(9,256),(9,512),(12,22),(13,25),(14,7),(15,64),(31,6),(32,2),(33,6),(34,4_194_337)] { let mut x=ft;x[field]=value;assert!(footer(&h,&x,bytes.len() as u64,&mut s,&mut b).is_err()); }
    let mut x = inputs(&[event(1)], true); let out=invoke(&mut x);assert!(out.fixture_framing_observed());assert_eq!(out.decision,Decision::Unavailable);assert_eq!(get(&x.3.bytes,14),1);
    let foot=x.0.bytes.len()/8-64;put(&mut x.0.bytes,foot+4,0);x.0.pos=0;x.1.pos=0;x.2.pos=0;x.3=Memory::new(vec![]);x.3.identity=4;assert_eq!(invoke(&mut x).decision,Decision::Invalid);
}

#[test]
fn coordinate_negative_sequences_work_instructions_phases_operations() {
    for (field, value) in [(0,2),(4,0),(5,0),(2,1),(3,2)] {
        let mut state=Framing::new(3);let first=event(1);assert!(state.coordinate(&first));let mut next=event(2);next[0]=2;next[field]=value;
        // seq field2 would be correct; deliberately force seq gap for that case.
        if field==0 { next[0]=3; }
        assert!(!state.coordinate(&next),"coordinate field{field}");
    }
    let mut state=Framing::new(2);let p=event(13);assert!(state.coordinate(&p));let mut again=p;again[0]=2;assert!(!state.coordinate(&again));
}

#[test]
fn context_closed_fields_reserved_lengths_and_no_real_binding() {
    let f=fixture(); let mut b=Budget::new(STEP_LIMIT).unwrap();let mut arena=Arena::new(&mut b).unwrap();
    for (field,value) in [(0,0),(1,2),(2,8191),(3,0),(3,2),(4,0),(4,MAX_RECORDS+1),(5,32),(5,65),(6,ABSENT),(7,1u64<<32),(8,0),(8,65),(9,0),(9,65),(10,2),(11,4097),(11,ABSENT),(12,ABSENT),(13,ABSENT),(14,1),(15,1),(48,1),(1023,1)] {
        let mut raw=context_bytes(f);put(&mut raw,field,value);let mut input=Memory::new(raw);let result=fixture_context(&mut input,&mut arena,&mut b);assert!(result.is_err(),"context word{field}");
    }
    let mut x=inputs(&[event(13)],false);put(&mut x.2.bytes,0,u64::from_le_bytes(*b"MIXCTX01"));let out=invoke(&mut x);assert_eq!(out.decision,Decision::Unavailable);assert!(!out.fixture_framing_observed());
    for n in [0,8191,8193] { let mut x=inputs(&[event(13)],false);x.2.bytes.resize(n,0);assert_eq!(invoke(&mut x).decision,Decision::Invalid); }
}

#[test]
fn empty_profile_zero_scalars_and_defined_zero_length_at_extent_are_finite_only() {
    let mut f=fixture();f.extent=0;f.types=0;f.base=0;f.capacity=0;f.entry=0;
    let mut raw=profile_bytes(f);
    for row in [0,1,511,512,79999] { let target=&mut raw[512+row*32..512+(row+1)*32];target.fill(0);put(target,0,(u32::MAX as u64)<<32);put(target,1,ABSENT); }
    let mut stream=Memory::new(stream_bytes(f,&[event(13)],false));let mut profile_input=Memory::new(raw);let mut context=Memory::new(context_bytes(f));let mut report=Memory::new(vec![]);profile_input.identity=2;context.identity=3;report.identity=4;
    let out=analyze_core(&mut stream,&mut profile_input,&mut context,&mut report,STEP_LIMIT).unwrap();assert!(out.fixture_framing_observed());assert!(!out.stored_prefix_validated());
    let f=fixture();let (mut arena,mut budget,_)=loaded();let mut raw=profile_bytes(f);put(&mut raw[512+79999*32..],1,f.extent);put(&mut raw[512+79999*32..],2,0);profile(&mut Memory::new(raw),&mut arena,&mut budget,f).unwrap();assert_eq!(arena.get64(FUNCTION,79999,8),Ok(0));
    for limit in [1,64] { let mut f=fixture();f.slots=limit;f.pins=limit;let mut budget=Budget::new(STEP_LIMIT).unwrap();let mut arena=Arena::new(&mut budget).unwrap();let admitted=fixture_context(&mut Memory::new(context_bytes(f)),&mut arena,&mut budget).unwrap();assert_eq!(admitted.slots,limit);assert_eq!(admitted.pins,limit); }
}

#[test]
fn profile_headers_rows_boundaries_and_reserved_words() {
    let (mut arena, mut b, f)=loaded();
    for (field,value) in [(0,0),(1,2),(2,511),(3,31),(4,79999),(5,999999),(6,3),(7,0),(8,65),(9,0),(10,65),(11,4095),(12,511),(13,1),(14,1),(15,1),(16,0),(20,0),(28,0),(48,1),(63,1)] {
        let mut raw=profile_bytes(f);put(&mut raw,field,value);assert!(profile(&mut Memory::new(raw),&mut arena,&mut b,f).is_err(),"profile header{field}");
    }
    for (row,field,value) in [(2,0,2),(2,0,0),(2,1,0),(2,2,1),(2,3,1),(1,0,(2u64<<32)|1),(1,1,ABSENT),(1,1,u64::MAX-1),(1,2,1_000_000),(1,2,ABSENT),(79999,3,1)] {
        let mut raw=profile_bytes(f);put(&mut raw[512+row*32..],field,value);let mut fresh=Budget::new(STEP_LIMIT).unwrap();assert!(profile(&mut Memory::new(raw),&mut arena,&mut fresh,f).is_err(),"profile row{row} field{field}");
    }
}

#[test]
fn io_short_interrupted_zero_error_overreported_and_exact_32_attempts() {
    for interrupts in [0,1,31] { let mut input=Memory::new(vec![9;16]);input.interrupts=interrupts;let mut b=Budget::new(STEP_LIMIT).unwrap();let mut out=[0;16];bounded_read(&mut input,&mut out,&mut b,1,0).unwrap();assert_eq!(input.calls,interrupts+1); }
    let mut input=Memory::new(vec![9;32]);input.quantum=1;let mut b=Budget::new(STEP_LIMIT).unwrap();let mut out=[0;32];bounded_read(&mut input,&mut out,&mut b,1,0).unwrap();assert_eq!(input.calls,32);
    for mode in 0..5 { let mut input=Memory::new(vec![9;33]);input.zero=mode==0;input.fail=mode==1;input.overreport=mode==2;input.interrupts=if mode==3{32}else{0};input.quantum=if mode==4{1}else{usize::MAX};let mut b=Budget::new(STEP_LIMIT).unwrap();let mut out=[0;33];let e=bounded_read(&mut input,&mut out,&mut b,1,0).unwrap_err();assert_eq!(e.code,[IO_ZERO,IO_ERROR,IO_OVERREPORTED,IO_EXHAUSTED,IO_EXHAUSTED][mode]);assert!(input.calls<=32); }
}

#[test]
fn eof_long_short_and_error_never_invent_complete_framing() {
    let mut b=Budget::new(STEP_LIMIT).unwrap();
    for mode in 0..4 { let mut input=Memory::new(if mode==0{vec![1]}else{vec![]});input.fail=mode==1;input.overreport=mode==2;input.interrupts=if mode==3{32}else{0};assert!(eof(&mut input,&mut b,1,0).is_err()); }
    for member in 0..3 { let mut x=inputs(&[event(13)],false);let target=match member{0=>&mut x.0,1=>&mut x.1,_=>&mut x.2};target.declared_len=Some(target.bytes.len() as u64);target.bytes.pop();let out=invoke(&mut x);assert_eq!(out.decision,Decision::Invalid);assert!(!out.fixture_framing_observed()); }
    let mut x=inputs(&[event(13)],false);x.0.declared_len=Some(x.0.bytes.len() as u64);x.0.bytes.push(0);assert_eq!(invoke(&mut x).decision,Decision::Invalid);
}

#[test]
fn metadata_offset_type_length_and_drift_refusals() {
    for member in 0..3 { for mode in 0..6 { let mut x=inputs(&[event(13)],false);let input=match member{0=>&mut x.0,1=>&mut x.1,_=>&mut x.2};input.regular=mode!=0;input.pos=usize::from(mode==1);input.drift=mode==2;input.stamp_fail=mode==3;input.position_fail=mode==4;if mode==5{input.declared_len=Some(0);}let result=analyze_core(&mut x.0,&mut x.1,&mut x.2,&mut x.3,STEP_LIMIT);if mode==3{assert_eq!(result.unwrap_err().code,IO_ERROR);assert!(x.3.bytes.is_empty());}else{let out=result.unwrap();assert_eq!(out.decision,Decision::Invalid,"member{member} mode{mode}");assert!(!out.fixture_framing_observed());} } }
}

#[test]
fn report_short_zero_interrupted_error_overreport_nonempty_and_metadata_failure() {
    for mode in 0..9 { let mut x=inputs(&[event(13)],false);x.3.zero=mode==0;x.3.fail=mode==1;x.3.overreport=mode==2;x.3.interrupts=if mode==3{32}else{0};x.3.quantum=if mode==4{1}else{usize::MAX};if mode==5{x.3.bytes.push(1);}x.3.regular=mode!=6;x.3.drift=mode==7;x.3.stamp_fail=mode==8;
        let e=analyze_core(&mut x.0,&mut x.1,&mut x.2,&mut x.3,STEP_LIMIT).unwrap_err();assert_eq!(e.stage,OUTPUT_STAGE);assert!(x.3.calls<=32);if mode==4{assert_eq!(x.3.bytes.len(),32);} }
    let mut x=inputs(&[event(13)],false);x.3.quantum=REPORT_BYTES.div_ceil(30);x.3.interrupts=2;let out=invoke(&mut x);assert_eq!(out.output_attempts,32);assert_eq!(x.3.bytes.len(),REPORT_BYTES);
}

#[test]
fn steps_preflight_exact_boundary_tail_drain_and_bad_footer_override() {
    let mut x=inputs(&[event(13)],false);let complete=invoke(&mut x);
    let setup_and_init=complete.steps_used-(6144+32+32+2+35)-complete.input_attempts-RECORD_STEPS-67;
    for (remaining,framed) in [(RECORD_PREFLIGHT-1,0),(RECORD_PREFLIGHT,1)] {
        let mut x=inputs(&[event(13)],false);let limit=REPORT_RESERVE+IO_RESERVE+setup_and_init+remaining;
        let out=analyze_core(&mut x.0,&mut x.1,&mut x.2,&mut x.3,limit).unwrap();assert_eq!(out.framed_records,framed);assert_eq!(x.3.bytes.len(),REPORT_BYTES);
        if framed==0 { assert_eq!(out.decision,Decision::AnalysisLimited);assert!(!out.fixture_framing_observed()); }
    }
    let mut x=inputs(&[event(13)],false);let len=x.0.bytes.len();put(&mut x.0.bytes,(len-512)/8,0);let limit=REPORT_RESERVE+IO_RESERVE+setup_and_init+RECORD_PREFLIGHT-100;
    let out=analyze_core(&mut x.0,&mut x.1,&mut x.2,&mut x.3,limit).unwrap();assert_eq!(out.decision,Decision::Invalid);
    let mut b=Budget::new(STEP_LIMIT).unwrap();b.setup_spent=SETUP_CAP;assert!(b.setup(1).is_err());b.io_spent=IO_RESERVE;assert!(b.io().is_err());b.report_spent=REPORT_RESERVE;assert!(b.report(1).is_err());
}

#[test]
fn block_boundaries_footer_straddle_and_bounded_drain() {
    for n in [508,509,510,511,512,513] {
        let mut events=vec![event(1);n];for (i,w) in events.iter_mut().enumerate(){w[3]=i as u64+1;}
        events.push(event(13));let mut x=inputs(&events,false);let out=invoke(&mut x);assert!(out.fixture_framing_observed(),"n{n}");assert_eq!(out.framed_records,n as u64+1);
    }
}

#[test]
fn public_file_borrows_report_scope_and_initial_offset() {
    let root=std::env::var_os("MIXER_ANALYZER_LIBRARY_TEST_SCRATCH").unwrap();let root=std::path::PathBuf::from(root);
    let f=fixture();let records=[event(13)];
    let mut files=Vec::new();
    for (name,bytes) in [("stream",stream_bytes(f,&records,false)),("profile",profile_bytes(f)),("context",context_bytes(f)),("report",vec![])] {
        let mut file=std::fs::OpenOptions::new().create_new(true).read(true).write(true).open(root.join(name)).unwrap();file.write_all(&bytes).unwrap();file.rewind().unwrap();files.push(file);
    }
    let mut report=files.pop().unwrap();let mut context=files.pop().unwrap();let mut profile=files.pop().unwrap();let mut stream=files.pop().unwrap();
    let out=analyze_fixture(&mut stream,&mut profile,&mut context,&mut report).unwrap();assert!(out.fixture_framing_observed());assert!(!out.full_replay_accepted());assert_eq!(report.metadata().unwrap().len(),REPORT_BYTES as u64);
    // Existing file owners survive the call and remain usable; no adoption/dup.
    stream.rewind().unwrap();profile.rewind().unwrap();context.rewind().unwrap();
    let mut short=std::fs::OpenOptions::new().create_new(true).read(true).write(true).open(root.join("offset-report")).unwrap();stream.seek(std::io::SeekFrom::Start(1)).unwrap();let out=analyze_fixture(&mut stream,&mut profile,&mut context,&mut short).unwrap();assert_eq!(out.decision,Decision::Invalid);
}

#[test]
fn pairwise_file_aliases_and_output_freshness_refuse_before_any_write() {
    for (a,b) in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)] {
        let mut x=inputs(&[event(13)],false);let ids=[1,2,3,4];let identity=ids[a];
        match b {1=>x.1.identity=identity,2=>x.2.identity=identity,3=>x.3.identity=identity,_=>unreachable!()};
        let e=analyze_core(&mut x.0,&mut x.1,&mut x.2,&mut x.3,STEP_LIMIT).unwrap_err();assert_eq!(e.code,BINDING);assert_eq!(x.3.calls,0);assert!(x.3.bytes.is_empty());
    }
    let root=std::path::PathBuf::from(std::env::var_os("MIXER_ANALYZER_LIBRARY_TEST_SCRATCH").unwrap());
    let f=fixture();let raw=stream_bytes(f,&[event(13)],false);
    let path=root.join("alias-stream");let mut source=std::fs::OpenOptions::new().create_new(true).read(true).write(true).open(&path).unwrap();source.write_all(&raw).unwrap();source.rewind().unwrap();
    let mut cloned=source.try_clone().unwrap();
    let mut profile=std::fs::OpenOptions::new().create_new(true).read(true).write(true).open(root.join("alias-profile")).unwrap();profile.write_all(&profile_bytes(f)).unwrap();profile.rewind().unwrap();
    let mut context=std::fs::OpenOptions::new().create_new(true).read(true).write(true).open(root.join("alias-context")).unwrap();context.write_all(&context_bytes(f)).unwrap();context.rewind().unwrap();
    let e=analyze_fixture(&mut source,&mut profile,&mut context,&mut cloned).unwrap_err();assert_eq!(e.code,OUTPUT);assert_eq!(std::fs::read(&path).unwrap(),raw);
    let link=root.join("alias-hardlink");std::fs::hard_link(&path,&link).unwrap();let mut alias=std::fs::OpenOptions::new().read(true).write(true).open(link).unwrap();
    let e=analyze_fixture(&mut source,&mut profile,&mut context,&mut alias).unwrap_err();assert_eq!(e.code,OUTPUT);assert_eq!(std::fs::read(&path).unwrap(),raw);
}

#[test]
fn concrete_layouts_and_named_role_caps() {
    println!("LAYOUT Arena={} Vec={} Error={} Outcome={} OutcomeResult={} ErrorResult={} File={} FileResult={} Metadata={} MetadataResult={} Stamp={} StampResult={} IoResult={} IoError={} Reader={} Budget={} Fixture={} Framing={} ReserveResult={} Range={} RangeResult={} WordResult512={} WordResult128={}",size_of::<Arena>(),size_of::<Vec<u8>>(),size_of::<AnalyzerError>(),size_of::<ReplayOutcome>(),size_of::<Result<ReplayOutcome,AnalyzerError>>(),size_of::<Result<(),AnalyzerError>>(),size_of::<File>(),size_of::<io::Result<File>>(),size_of::<std::fs::Metadata>(),size_of::<io::Result<std::fs::Metadata>>(),size_of::<Stamp>(),size_of::<io::Result<Stamp>>(),size_of::<io::Result<usize>>(),size_of::<io::Error>(),size_of::<Reader>(),size_of::<Budget>(),size_of::<Fixture>(),size_of::<Framing>(),size_of::<Result<(),TryReserveError>>(),size_of::<std::ops::Range<usize>>(),size_of::<Result<std::ops::Range<usize>,AnalyzerError>>(),size_of::<Result<[u64;64],AnalyzerError>>(),size_of::<Result<[u64;16],AnalyzerError>>());
    assert_eq!(size_of::<AnalyzerError>(),32);assert!(size_of::<ReplayOutcome>()<=256);assert_eq!(REGIONS.last().unwrap().base+REGIONS.last().unwrap().rows*REGIONS.last().unwrap().stride,7_873_120);
    assert_eq!(REPORT_BYTES+8192,57344);assert!(REPORT_BYTES+8192<=AGGREGATE_REPORT_CAP);assert_eq!(TRANSIENT_CAP,65536);
}

#[test]
fn immutable_captured_footer_observations_never_reclassify_sidecars() {
    let directory=std::path::PathBuf::from(std::env::var_os("MIXER_ANALYZER_LIBRARY_HISTORICAL").unwrap());
    let mut count=0;let mut grammar_refused=0;
    for item in std::fs::read_dir(directory).unwrap() {
        let path=item.unwrap().path();if path.extension().and_then(|s|s.to_str())!=Some("bin"){continue;}
        let raw=std::fs::read(&path).unwrap();assert!(raw.len()>=1024);
        let mut h=[0;64];let mut f=[0;64];for i in 0..64{h[i]=get(&raw,i);f[i]=get(&raw[raw.len()-512..],i);}
        let mut state=Framing::new(((raw.len()-1024)/128)as u64);state.framed=state.physical;state.last_work=f[6];state.last_instructions=f[7];state.last_operation=f[8];state.phase=f[33];state.mask=f[15];
        let mut budget=Budget::new(STEP_LIMIT).unwrap();if footer(&h,&f,raw.len()as u64,&mut state,&mut budget).is_err(){grammar_refused+=1;}count+=1;
    }
    assert_eq!(count,17);assert!(grammar_refused>0);println!("HISTORICAL_SIDECARS_INVALID=17 FOOTER_GRAMMAR_REFUSED={grammar_refused} FOOTER_ONLY_OBSERVED={}",count-grammar_refused);
}
