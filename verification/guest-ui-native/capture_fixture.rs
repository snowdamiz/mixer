//! Original evidence client; serializes the exact independent test builder.
#[path = "../../vm/tests/guest_ui/fixture.rs"]
mod fixture;
use fixture::Program;
fn capture(name: &str, program: &Program) {
    print!("{name} ");
    for byte in program.bytes() { print!("{byte:02x}"); }
    println!();
}
fn main() {
    capture("valid", &Program::default());
    let mut p = Program::default(); p.memory = Some(vec![1,1,0,0]); capture("zero_pages", &p);
    let mut p = Program::default(); p.memory = Some(vec![1,1,32,32]); capture("allocation_32pages", &p);
    let mut p = Program::default(); p.functions[0].1 = vec![0,0,0x0b]; capture("startup_would_trap", &p);
    let mut p = Program::default(); p.start_section = true; capture("forbidden_start_section", &p);
    let mut p = Program::default(); p.unknown_import = true; p.exports.remove(1); capture("unknown_import_missing_event", &p);
    let mut p = Program::default(); p.functions[0].1 = vec![0,0,0x0b]; p.functions.push((0,vec![0,0x42,0,0x0b])); p.exports.remove(1); capture("malformed_uncalled_missing_event", &p);
    let mut p = Program::default(); p.functions.push((2,vec![0,0xfd,0x0b])); capture("unsupported_uncalled", &p);
    for required in 0..3 {
        let mut p = Program::default(); p.exports.remove(required); capture(&format!("missing_{required}"), &p);
        let mut p = Program::default(); p.exports[required].1 = 2; p.exports[required].2 = 0; capture(&format!("memory_export_{required}"), &p);
        let mut p = Program::default(); p.exports[required].2 = if required==1 {1} else {0}; capture(&format!("imported_{required}"), &p);
    }
}
