//! Same public frozen-route witnesses compiled against old and reviewed snapshots.
use mixer_vm::experimental::{validate_spans, ValidationBudget};
use mixer_vm::{Cancellation, Limits, Profile};
fn u(mut n: u32) -> Vec<u8> {
    let mut v = Vec::new();
    loop {
        let b = (n & 127) as u8;
        n >>= 7;
        v.push(b | if n > 0 { 128 } else { 0 });
        if n == 0 {
            return v;
        }
    }
}
fn sec(out: &mut Vec<u8>, id: u8, p: Vec<u8>) {
    out.push(id);
    out.extend(u(p.len() as u32));
    out.extend(p)
}
fn input(case: &str) -> Vec<u8> {
    let mut b = b"\0asm\x01\0\0\0".to_vec();
    match case {
        "empty" => {}
        "function" => {
            sec(&mut b, 1, vec![1, 0x60, 0, 0]);
            sec(&mut b, 3, vec![1, 0]);
            sec(&mut b, 10, vec![1, 2, 0, 0x0b]);
        }
        "active-data-beyond-initial" => {
            sec(&mut b, 5, vec![1, 0, 1]);
            let mut d = vec![1, 0, 0x41];
            d.extend(u(65_536));
            d.extend([0x0b, 1, 7]);
            sec(&mut b, 11, d);
        }
        "depth-at-limit" | "depth-over-limit" => {
            sec(&mut b, 1, vec![1, 0x60, 0, 0]);
            sec(&mut b, 3, vec![1, 0]);
            let n = if case == "depth-at-limit" { 127 } else { 128 };
            let mut body = vec![0];
            for _ in 0..n {
                body.extend([2, 0x40]);
            }
            body.extend(vec![0x0b; n + 1]);
            let mut c = vec![1];
            c.extend(u(body.len() as u32));
            c.extend(body);
            sec(&mut b, 10, c);
        }
        _ => panic!("unknown case"),
    }
    b
}
fn main() {
    let args: Vec<_> = std::env::args().collect();
    let cases: Vec<&str> = if args.len() > 1 {
        vec![&args[1]]
    } else {
        vec![
            "empty",
            "function",
            "active-data-beyond-initial",
            "depth-at-limit",
            "depth-over-limit",
        ]
    };
    for case in cases {
        let mut budget = ValidationBudget::default();
        if args.len() == 5 {
            budget.metadata_bytes = args[2].parse().unwrap();
            budget.scratch_bytes = args[3].parse().unwrap();
            budget.work_credits = args[4].parse().unwrap();
        }
        let result = validate_spans(
            &input(case),
            Limits {
                profile: Profile::TableMemoryV3,
                ..Limits::default()
            },
            budget,
            &Cancellation::default(),
        );
        match result {
            Ok(p) => {
                let x = p.usage();
                println!("{{\"case\":\"{case}\",\"ok\":true,\"source\":{},\"metadata\":{},\"scratch\":{},\"metadata_peak\":{},\"scratch_peak\":{},\"total_peak\":{},\"work\":{},\"profile\":\"{:?}\"}}",x.source_bytes,x.metadata_reserved,x.scratch_reserved,x.metadata_peak_reserved,x.scratch_peak_reserved,x.total_peak_reserved,x.work_used,p.profile());
            }
            Err(e) => {
                let x = e.usage;
                println!("{{\"case\":\"{case}\",\"ok\":false,\"kind\":\"{:?}\",\"code\":\"{}\",\"function\":{:?},\"offset\":{},\"attempted\":{},\"limit\":{},\"source\":{},\"metadata\":{},\"scratch\":{},\"metadata_peak\":{},\"scratch_peak\":{},\"total_peak\":{},\"work\":{}}}",e.kind,e.code,e.function.map_or(-1,|n|n as i64),e.offset,e.attempted,e.limit,x.source_bytes,x.metadata_reserved,x.scratch_reserved,x.metadata_peak_reserved,x.scratch_peak_reserved,x.total_peak_reserved,x.work_used);
            }
        }
    }
}
