//! Host-only measurement instrumentation, added to an immutable source export.
use crate::*;
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};
static LIVE: AtomicUsize = AtomicUsize::new(0);
static COUNT: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static PEAK_COUNT: AtomicUsize = AtomicUsize::new(0);
struct Tracking;
fn add(bytes: usize, allocation: bool) {
    let live = LIVE.fetch_add(bytes, Ordering::Relaxed) + bytes;
    PEAK.fetch_max(live, Ordering::Relaxed);
    if allocation {
        let count = COUNT.fetch_add(1, Ordering::Relaxed) + 1;
        PEAK_COUNT.fetch_max(count, Ordering::Relaxed);
    }
}
unsafe impl GlobalAlloc for Tracking {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(layout) };
        if !p.is_null() {
            add(layout.size(), true);
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let p = unsafe { System.alloc_zeroed(layout) };
        if !p.is_null() {
            add(layout.size(), true);
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        unsafe { System.dealloc(p, layout) };
        LIVE.fetch_sub(layout.size(), Ordering::Relaxed);
        COUNT.fetch_sub(1, Ordering::Relaxed);
    }
    unsafe fn realloc(&self, p: *mut u8, layout: Layout, next: usize) -> *mut u8 {
        let result = unsafe { System.realloc(p, layout, next) };
        if !result.is_null() {
            if next >= layout.size() {
                add(next - layout.size(), false);
            } else {
                LIVE.fetch_sub(layout.size() - next, Ordering::Relaxed);
            }
        }
        result
    }
}
#[global_allocator]
static ALLOCATOR: Tracking = Tracking;
#[derive(Clone, Copy)]
struct Phase {
    name: &'static str,
    live: usize,
    count: usize,
    peak: usize,
    peak_count: usize,
}
fn snapshot(name: &'static str) -> Phase {
    Phase {
        name,
        live: LIVE.load(Ordering::Relaxed),
        count: COUNT.load(Ordering::Relaxed),
        peak: PEAK.load(Ordering::Relaxed),
        peak_count: PEAK_COUNT.load(Ordering::Relaxed),
    }
}
fn leb(mut n: u32) -> Vec<u8> {
    let mut b = vec![];
    loop {
        let x = (n & 127) as u8;
        n >>= 7;
        b.push(x | if n != 0 { 128 } else { 0 });
        if n == 0 {
            return b;
        }
    }
}
fn section(m: &mut Vec<u8>, id: u8, b: Vec<u8>) {
    m.push(id);
    m.extend(leb(b.len() as u32));
    m.extend(b);
}
fn fixture(name: &str) -> Vec<u8> {
    let mut m = b"\0asm\x01\0\0\0".to_vec();
    section(&mut m, 1, vec![1, 0x60, 0, 0]);
    let functions = if name == "many-functions" {
        2048
    } else if name == "frames" {
        64
    } else {
        1
    };
    let mut f = leb(functions);
    f.extend(std::iter::repeat_n(0, functions as usize));
    section(&mut m, 3, f);
    if name == "table" {
        let mut t = vec![1, 0x70, 1];
        t.extend(leb(65536));
        t.extend(leb(65536));
        section(&mut m, 4, t);
    }
    if matches!(name, "data" | "combined") {
        section(&mut m, 5, vec![1, 1, 64, 64]);
    }
    if name == "globals" {
        let mut g = leb(1024);
        for _ in 0..1024 {
            g.extend([0x7e, 1, 0x42, 0, 0x0b]);
        }
        section(&mut m, 6, g);
    }
    section(&mut m, 7, vec![1, 3, b'r', b'u', b'n', 0, 0]);
    if name == "table" {
        let mut e = vec![1, 0, 0x41, 0, 0x0b];
        e.extend(leb(65536));
        e.extend(std::iter::repeat_n(0, 65536));
        section(&mut m, 9, e);
    }
    let mut code = leb(functions);
    for index in 0..functions {
        let mut b = vec![0];
        match name {
            "dense" | "combined" => {
                for _ in 0..99999 {
                    b.extend([0x41, 0, 0x1a]);
                }
            }
            "branches" => {
                for _ in 0..500 {
                    b.extend([2, 0x40, 0x41, 0, 0x0e]);
                    b.extend(leb(4096));
                    b.extend(std::iter::repeat_n(0, 4097));
                    b.push(0x0b);
                }
            }
            "frames" => {
                b = vec![1];
                b.extend(leb(4096));
                b.push(0x7e);
                if index + 1 < functions {
                    b.push(0x10);
                    b.extend(leb(index + 1));
                }
            }
            _ => {}
        }
        b.push(0x0b);
        code.extend(leb(b.len() as u32));
        code.extend(b);
    }
    section(&mut m, 10, code);
    if matches!(name, "data" | "combined") {
        let mut d = vec![1, 0, 0x41, 0, 0x0b];
        d.extend(leb(3 * 1024 * 1024));
        d.extend((0..3 * 1024 * 1024).map(|i| ((i * 31 + i / 251) & 255) as u8));
        section(&mut m, 11, d);
    }
    m
}
#[test]
fn generate() {
    let dir = std::path::PathBuf::from(std::env::var("MIXER_PROBE_FIXTURES").unwrap());
    std::fs::create_dir_all(&dir).unwrap();
    for name in [
        "empty",
        "dense",
        "many-functions",
        "branches",
        "frames",
        "data",
        "combined",
        "globals",
        "table",
    ] {
        std::fs::write(dir.join(format!("{name}.wasm")), fixture(name)).unwrap();
    }
}
fn shape(m: &Module) -> (usize, usize, usize, usize, usize, usize) {
    let instructions = m.functions.iter().map(|f| f.code.len()).sum();
    let code_capacity = m
        .functions
        .iter()
        .map(|f| f.code.capacity() * std::mem::size_of::<Instruction>())
        .sum();
    let branches = m
        .functions
        .iter()
        .flat_map(|f| f.code.iter())
        .map(|i| match &i.op {
            Op::BrTable(v, _) => v.capacity() * 4,
            _ => 0,
        })
        .sum();
    let locals = m
        .functions
        .iter()
        .map(|f| f.locals.capacity() * std::mem::size_of::<Type>())
        .sum();
    let data = m.data.iter().map(|(_, d)| d.capacity()).sum();
    (
        instructions,
        code_capacity,
        branches,
        locals,
        data,
        m.functions.len(),
    )
}
#[test]
fn probe() {
    let case = std::env::var("MIXER_PROBE_CASE").unwrap();
    let path = std::env::var("MIXER_PROBE_FILE").unwrap();
    let mut phases = Vec::with_capacity(12);
    let mut limits = Limits::default();
    if case == "table" {
        limits.profile = Profile::TableMemoryV3;
    }
    let mut baseline = snapshot("baseline");
    PEAK.store(baseline.live, Ordering::Relaxed);
    PEAK_COUNT.store(baseline.count, Ordering::Relaxed);
    baseline.peak = baseline.live;
    baseline.peak_count = baseline.count;
    phases.push(baseline);
    let source = std::fs::read(&path).unwrap();
    let source_bytes = source.len();
    let source_capacity = source.capacity();
    phases.push(snapshot("source_read"));
    let mut details = (0, 0, 0, 0, 0, 0);
    let mut memory = 0;
    let mut returned = "not-invoked";
    if case == "source-only" {
        drop(source);
        phases.push(snapshot("all_dropped"));
    } else if case.starts_with("sessions") {
        let count = if case == "sessions16" { 16 } else { 1 };
        let mut handles = [0u64; 16];
        for slot in handles.iter_mut().take(count) {
            let mut report = MixerVmReport::default();
            let status = unsafe {
                mixer_vm_session_create_v1(
                    1,
                    source.as_ptr(),
                    source.len(),
                    std::ptr::null(),
                    slot,
                    &mut report,
                )
            };
            assert_eq!(status, 0);
        }
        phases.push(snapshot("sessions_retained"));
        drop(source);
        phases.push(snapshot("source_dropped"));
        for handle in handles.into_iter().take(count) {
            let mut report = MixerVmReport::default();
            assert_eq!(unsafe { mixer_vm_session_close_v1(handle, &mut report) }, 0);
        }
        phases.push(snapshot("all_sessions_closed"));
    } else {
        let module = Module::decode(&source, &limits).unwrap();
        details = shape(&module);
        phases.push(snapshot("decoded"));
        if case == "decode-only" {
            drop(source);
            phases.push(snapshot("source_dropped"));
            drop(module);
            phases.push(snapshot("all_dropped"));
        } else if case == "data-retain" {
            let mut instance = Instance::new(module, limits).unwrap();
            memory = instance.memory().len();
            phases.push(snapshot("instantiated_source_retained"));
            assert_eq!(instance.invoke("run", &[]).unwrap(), None);
            returned = "success-void";
            phases.push(snapshot("invoked"));
            drop(instance);
            drop(source);
            phases.push(snapshot("all_dropped"));
        } else {
            drop(source);
            phases.push(snapshot("source_dropped"));
            let mut instance = Instance::new(module, limits).unwrap();
            memory = instance.memory().len();
            phases.push(snapshot("instantiated"));
            assert_eq!(instance.invoke("run", &[]).unwrap(), None);
            returned = "success-void";
            phases.push(snapshot("invoked"));
            drop(instance);
            phases.push(snapshot("all_dropped"));
        }
    }
    let (frame_size, frame_align, label_size, label_align) =
        crate::execute::measurement_frame_layout();
    println!("ALIGNMENT_JSON {{\"op\":{},\"instruction\":{},\"function\":{},\"module\":{},\"signature\":{},\"value\":{},\"type\":{}}}",
        std::mem::align_of::<Op>(), std::mem::align_of::<Instruction>(), std::mem::align_of::<Function>(),
        std::mem::align_of::<Module>(), std::mem::align_of::<Signature>(), std::mem::align_of::<Value>(), std::mem::align_of::<Type>());
    let phase_text=phases.iter().map(|p|format!("{{\"name\":\"{}\",\"live_requested_bytes\":{},\"live_allocations\":{},\"peak_requested_bytes\":{},\"peak_live_allocations\":{}}}",p.name,p.live,p.count,p.peak,p.peak_count)).collect::<Vec<_>>().join(",");
    println!("MEASURE_JSON {{\"case\":{},\"source_bytes\":{},\"source_capacity\":{},\"instructions\":{},\"instruction_vec_capacity_bytes\":{},\"branch_label_capacity_bytes\":{},\"local_type_capacity_bytes\":{},\"retained_data_capacity_bytes\":{},\"defined_functions\":{},\"linear_memory_bytes\":{},\"invoke\":{},\"layout\":{{\"op\":{},\"instruction\":{},\"function\":{},\"module\":{},\"signature\":{},\"value\":{},\"type\":{},\"frame\":{},\"frame_alignment\":{},\"label\":{},\"label_alignment\":{}}},\"phases\":[{}]}}",json_string(&case),source_bytes,source_capacity,details.0,details.1,details.2,details.3,details.4,details.5,memory,json_string(returned),std::mem::size_of::<Op>(),std::mem::size_of::<Instruction>(),std::mem::size_of::<Function>(),std::mem::size_of::<Module>(),std::mem::size_of::<Signature>(),std::mem::size_of::<Value>(),std::mem::size_of::<Type>(),frame_size,frame_align,label_size,label_align,phase_text);
}
