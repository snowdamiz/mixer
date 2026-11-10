use mixer_vm::{Cancellation, Limits, Module, Profile};
use mixer_vm::experimental_swift_reactor::{validate_swift_command, validate_swift_reactor,
    execute_swift_command, SwiftValidationBudget, SwiftRunBudget};
use mixer_vm::experimental_wasi::{WasiBudget, WasiGrants, WasiFunction};
use std::{fs::File, io::Read};
pub fn main() {
    let args = [std::ffi::OsString::from("R110"),
        std::env::var_os("MIXER_R110_MODULE").expect("module path"),
        std::env::var_os("MIXER_R110_STDOUT").expect("guest stdout path"),
        std::env::var_os("MIXER_R110_STDERR").expect("guest stderr path")];
    let mut input = Vec::new();
    File::open(&args[1]).unwrap().take(64 * 1024 * 1024 + 1).read_to_end(&mut input).unwrap();
    assert!(input.len() <= 64 * 1024 * 1024);
    println!("test=FieldLogTaskEditorBurstAndSaveDifferentialOwnedVM; bytes={}",input.len());
    let limits = Limits { profile: Profile::TableMemoryV3, ..Default::default() };
    match Module::decode(&input, &limits) {
        Ok(_) => println!("strict_table_memory_v3=validated"),
        Err(e) => println!("strict_table_memory_v3={}",e.json()),
    }
    let budget = SwiftValidationBudget { deadline_ms: 30_000, ..Default::default() };
    match validate_swift_reactor(&input,budget,&Cancellation::default()) {
        Ok(_) => println!("fixed_reactor=validated"),
        Err(e) => println!("fixed_reactor={e:?}"),
    }
    let cancellation = Cancellation::default();
    let proof = match validate_swift_command(&input,budget,&cancellation) {
        Ok(proof) => proof,
        Err(e) => {
            println!("command_validation={e:?}");
            if let Some(byte) = input.get(e.offset) { println!("first_failure_byte=0x{byte:02x}"); }
            println!("ownedVMExecution=false"); std::process::exit(10);
        }
    };
    println!("command_policy={}; entry={}; observations={:?}; validation_usage={:?}",
        proof.policy_identity(),proof.entry_function(),proof.observations(),proof.usage());
    drop(input);
    let mut stdout = File::create(&args[2]).unwrap();
    let mut stderr = File::create(&args[3]).unwrap();
    let grants = WasiGrants { secure_random:true,realtime:true,monotonic:true,stdout:true,stderr:true };
    println!("run_budget={:?}; wasi_budget={:?}; grants={grants:?}", SwiftRunBudget::default(),WasiBudget::default());
    let report = execute_swift_command(proof,SwiftRunBudget::default(),grants,WasiBudget::default(),
        cancellation,&mut stdout,&mut stderr);
    println!("owned_command_report={report:?}");
    for (f,count) in WasiFunction::ALL.iter().zip(report.calls_by_function) {
        if count != 0 { println!("called_import={} count={count}",String::from_utf8_lossy(f.name())); }
    }
    println!("command_succeeded={}",report.succeeded());
    if !report.succeeded() { std::process::exit(20); }
}
