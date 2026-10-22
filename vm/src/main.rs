use mixer_vm::{
    inventory, json_string, validation_inventory, Error, Instance, Limits, Module, Profile, Value,
};
use std::{fs::File, io::Read, process::ExitCode};
fn failure(e: Error) -> String {
    format!("{{\"ok\":false,\"error\":{}}}", e.json())
}
fn run() -> Result<(String, bool), Error> {
    let mut args = std::env::args().skip(1).collect::<Vec<_>>();
    let mut limits = Limits::default();
    let mut i = 0;
    while i < args.len() {
        if args[i].starts_with("--") {
            let flag = args.remove(i);
            if i >= args.len() {
                return Err(Error::new("usage", "missing limit value", None, 0));
            }
            if flag == "--profile" {
                let value = args.remove(i);
                limits.profile = match value.as_str() {
                    "mixer-integer-v1" => Profile::IntegerV1,
                    "mixer-numeric-v2" => Profile::NumericV2,
                    _ => return Err(Error::new("usage", "unknown profile", None, 0)),
                };
                continue;
            }
            let v = args
                .remove(i)
                .parse::<u64>()
                .map_err(|_| Error::new("usage", "limit must be unsigned integer", None, 0))?;
            match flag.as_str() {
                "--fuel" => limits.fuel = v,
                "--memory-pages" => {
                    limits.memory_pages = u32::try_from(v)
                        .map_err(|_| Error::new("usage", "memory pages exceed u32", None, 0))?
                }
                "--call-depth" => {
                    limits.call_depth = usize::try_from(v)
                        .map_err(|_| Error::new("usage", "call depth exceeds usize", None, 0))?
                }
                "--stack" => {
                    limits.operand_stack = usize::try_from(v)
                        .map_err(|_| Error::new("usage", "stack exceeds usize", None, 0))?
                }
                "--host-calls" => limits.host_calls = v,
                _ => {
                    return Err(Error::new(
                        "usage",
                        format!("unknown option {flag}"),
                        None,
                        0,
                    ))
                }
            }
        } else {
            i += 1;
        }
    }
    limits.check()?;
    if args.len() < 2 {
        return Err(Error::new("usage","mixer-vm validate|inventory FILE; mixer-vm invoke FILE EXPORT [i32:N|i64:N|f32:N|f64:N ...]; options --profile mixer-integer-v1|mixer-numeric-v2 --fuel N --memory-pages N --call-depth N --stack N --host-calls N",None,0));
    }
    let read_limit = if args[0] == "inventory" {
        128 * 1024 * 1024
    } else {
        limits.module_bytes
    };
    let mut bytes = vec![];
    File::open(&args[1])
        .map_err(|e| Error::new("io", e.to_string(), None, 0))?
        .take(read_limit as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| Error::new("io", e.to_string(), None, 0))?;
    match args[0].as_str() {
        "validate" | "inventory" => {
            if args.len() != 2 {
                return Err(Error::new("usage", "unexpected arguments", None, 0));
            }
            let inv = if args[0] == "inventory" {
                inventory(&bytes, &limits)
            } else {
                validation_inventory(&bytes, &limits)
            };
            let ok = inv.error.is_none();
            Ok((inv.json(), ok))
        }
        "invoke" => {
            if args.len() < 3 {
                return Err(Error::new(
                    "usage",
                    "invoke requires an export name",
                    None,
                    0,
                ));
            }
            let mut values = vec![];
            for a in &args[3..] {
                let (t, v) = a.split_once(':').ok_or_else(|| {
                    Error::new("usage", "arguments require i32:N or i64:N", None, 0)
                })?;
                let value = match t {
                    "i32" => Value::I32(
                        v.parse()
                            .map_err(|_| Error::new("usage", "invalid i32 argument", None, 0))?,
                    ),
                    "i64" => Value::I64(
                        v.parse()
                            .map_err(|_| Error::new("usage", "invalid i64 argument", None, 0))?,
                    ),
                    "f32" => Value::F32(
                        v.parse::<f32>()
                            .map_err(|_| Error::new("usage", "invalid f32 argument", None, 0))?
                            .to_bits(),
                    ),
                    "f64" => Value::F64(
                        v.parse::<f64>()
                            .map_err(|_| Error::new("usage", "invalid f64 argument", None, 0))?
                            .to_bits(),
                    ),
                    _ => return Err(Error::new("usage", "unknown argument type", None, 0)),
                };
                values.push(value);
            }
            let module = Module::decode(&bytes, &limits)?;
            let mut instance = Instance::new(module, limits.clone())?;
            let result = instance.invoke(&args[2], &values)?;
            Ok((format!("{{\"ok\":true,\"profile\":{},\"export\":{},\"result\":{},\"fuel_used\":{},\"host_calls_used\":{}}}",json_string(limits.profile.name()),json_string(&args[2]),result.map(Value::json).unwrap_or_else(||"null".into()),limits.fuel-instance.fuel_remaining,instance.host_calls_used),true))
        }
        _ => Err(Error::new("usage", "unknown command", None, 0)),
    }
}
fn main() -> ExitCode {
    match run() {
        Ok((json, ok)) => {
            println!("{json}");
            if ok {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(2)
            }
        }
        Err(e) => {
            println!("{}", failure(e));
            ExitCode::from(2)
        }
    }
}
