#![cfg(feature = "experimental-swift-wasi")]
use mixer_vm::experimental_wasi::*;
use mixer_vm::{Cancellation, Type, Value};

fn i(n: u32) -> Value {
    Value::I32(n as i32)
}
fn ok() -> WasiOutcome {
    WasiOutcome::Errno(Errno::Success)
}
fn e(errno: Errno) -> WasiOutcome {
    WasiOutcome::Errno(errno)
}
fn grants() -> WasiGrants {
    WasiGrants {
        secure_random: true,
        realtime: true,
        monotonic: true,
        stdout: true,
        stderr: true,
    }
}
fn ctx() -> WasiContext {
    WasiContext::new(grants(), WasiBudget::default(), Cancellation::default()).unwrap()
}
fn get32(memory: &[u8], at: usize) -> u32 {
    u32::from_le_bytes(memory[at..at + 4].try_into().unwrap())
}
fn get64(memory: &[u8], at: usize) -> u64 {
    u64::from_le_bytes(memory[at..at + 8].try_into().unwrap())
}
fn vector(memory: &mut [u8], at: usize, pointer: u32, length: u32) {
    memory[at..at + 4].copy_from_slice(&pointer.to_le_bytes());
    memory[at + 4..at + 8].copy_from_slice(&length.to_le_bytes());
}

#[test]
fn exact_all_34_names_and_complete_signatures() {
    use Type::{I32 as I, I64 as L};
    let descriptors: [(&[u8], &[Type]); 34] = [
        (b"args_get", &[I, I]),
        (b"args_sizes_get", &[I, I]),
        (b"environ_get", &[I, I]),
        (b"environ_sizes_get", &[I, I]),
        (b"clock_res_get", &[I, I]),
        (b"clock_time_get", &[I, L, I]),
        (b"fd_close", &[I]),
        (b"fd_fdstat_get", &[I, I]),
        (b"fd_fdstat_set_flags", &[I, I]),
        (b"fd_filestat_get", &[I, I]),
        (b"fd_filestat_set_size", &[I, L]),
        (b"fd_filestat_set_times", &[I, L, L, I]),
        (b"fd_pread", &[I, I, I, L, I]),
        (b"fd_prestat_get", &[I, I]),
        (b"fd_prestat_dir_name", &[I, I, I]),
        (b"fd_read", &[I, I, I, I]),
        (b"fd_readdir", &[I, I, I, L, I]),
        (b"fd_seek", &[I, L, I, I]),
        (b"fd_sync", &[I]),
        (b"fd_tell", &[I, I]),
        (b"fd_write", &[I, I, I, I]),
        (b"path_create_directory", &[I, I, I]),
        (b"path_filestat_get", &[I, I, I, I, I]),
        (b"path_filestat_set_times", &[I, I, I, I, L, L, I]),
        (b"path_link", &[I, I, I, I, I, I, I]),
        (b"path_open", &[I, I, I, I, I, L, L, I, I]),
        (b"path_readlink", &[I, I, I, I, I, I]),
        (b"path_remove_directory", &[I, I, I]),
        (b"path_rename", &[I, I, I, I, I, I]),
        (b"path_symlink", &[I, I, I, I, I]),
        (b"path_unlink_file", &[I, I, I]),
        (b"poll_oneoff", &[I, I, I, I]),
        (b"proc_exit", &[I]),
        (b"random_get", &[I, I]),
    ];
    for (function, (name, parameters)) in WasiFunction::ALL.into_iter().zip(descriptors) {
        let results: &[Type] = if function == WasiFunction::ProcExit {
            &[]
        } else {
            &[I]
        };
        assert_eq!(function.name(), name);
        assert_eq!(function.parameters(), parameters);
        assert_eq!(function.results(), results);
        assert_eq!(
            WasiFunction::resolve(b"wasi_snapshot_preview1", name, parameters, results),
            Ok(function)
        );
        assert_eq!(
            WasiFunction::resolve(b"wasi_unstable", name, parameters, results),
            Err(ResolveError::Module)
        );
        assert_eq!(
            WasiFunction::resolve(
                b"wasi_snapshot_preview1",
                name,
                &parameters[..parameters.len() - 1],
                results
            ),
            Err(ResolveError::Signature)
        );
        let mut extra = parameters.to_vec();
        extra.push(I);
        assert_eq!(
            WasiFunction::resolve(b"wasi_snapshot_preview1", name, &extra, results),
            Err(ResolveError::Signature)
        );
        for at in 0..parameters.len() {
            for wrong in [Type::I32, Type::I64, Type::F32, Type::F64] {
                if wrong == parameters[at] {
                    continue;
                }
                let mut altered = parameters.to_vec();
                altered[at] = wrong;
                assert_eq!(
                    WasiFunction::resolve(b"wasi_snapshot_preview1", name, &altered, results),
                    Err(ResolveError::Signature)
                );
            }
        }
        for wrong in [&[Type::F32][..], &[I, I][..], &[L][..]] {
            assert_eq!(
                WasiFunction::resolve(b"wasi_snapshot_preview1", name, parameters, wrong),
                Err(ResolveError::Signature)
            );
        }
    }
    for name in [&b"args_get\0"[..], &b"sock_open"[..], &[0xff][..], &b""[..]] {
        assert_eq!(
            WasiFunction::resolve(b"wasi_snapshot_preview1", name, &[], &[]),
            Err(ResolveError::Name)
        );
    }
}

#[test]
fn every_declared_operation_has_an_explicit_denied_or_layout_outcome() {
    use WasiFunction::*;
    for function in WasiFunction::ALL {
        let mut context = WasiContext::new(
            WasiGrants::default(),
            WasiBudget::default(),
            Cancellation::default(),
        )
        .unwrap();
        let args: Vec<_> = function
            .parameters()
            .iter()
            .map(|t| match t {
                Type::I64 => Value::I64(-1),
                _ => i(u32::MAX),
            })
            .collect();
        let mut memory = [0xa5; 64];
        let expected = match function {
            ArgsGet | ArgsSizesGet | EnvironGet | EnvironSizesGet => e(Errno::Fault),
            ClockResGet | ClockTimeGet => e(Errno::Inval),
            RandomGet => e(Errno::Notcapable),
            PollOneoff => e(Errno::Notsup),
            ProcExit => WasiOutcome::Exit(u32::MAX),
            FdClose | FdFdstatGet | FdFdstatSetFlags | FdFilestatGet | FdFilestatSetSize
            | FdFilestatSetTimes | FdPread | FdPrestatGet | FdPrestatDirName | FdRead
            | FdReaddir | FdSeek | FdSync | FdTell | FdWrite | PathCreateDirectory
            | PathFilestatGet | PathFilestatSetTimes | PathLink | PathOpen | PathReadlink
            | PathRemoveDirectory | PathRename | PathSymlink | PathUnlinkFile => e(Errno::Badf),
        };
        assert_eq!(
            context.dispatch(function, &args, &mut memory),
            expected,
            "{function:?}"
        );
        assert_eq!(memory, [0xa5; 64], "{function:?}");
        assert!(context.stdout().is_empty());
        assert!(context.stderr().is_empty());
    }
}

#[test]
fn fixed_argv_and_empty_environment_are_little_endian_and_atomic() {
    let mut context = ctx();
    let mut memory = [0xa5; 64];
    assert_eq!(
        context.dispatch(WasiFunction::ArgsSizesGet, &[i(0), i(4)], &mut memory),
        ok()
    );
    assert_eq!((get32(&memory, 0), get32(&memory, 4)), (1, 6));
    assert_eq!(
        context.dispatch(WasiFunction::ArgsGet, &[i(8), i(16)], &mut memory),
        ok()
    );
    assert_eq!(get32(&memory, 8), 16);
    assert_eq!(&memory[16..22], b"mixer\0");
    assert_eq!(
        context.dispatch(WasiFunction::EnvironSizesGet, &[i(24), i(28)], &mut memory),
        ok()
    );
    assert_eq!(&memory[24..32], &[0; 8]);
    let prior = memory;
    assert_eq!(
        context.dispatch(WasiFunction::EnvironGet, &[i(64), i(64)], &mut memory),
        ok()
    );
    assert_eq!(memory, prior);
    for (function, args, expected) in [
        (WasiFunction::ArgsGet, [i(0), i(1)], Errno::Inval),
        (WasiFunction::ArgsSizesGet, [i(0), i(2)], Errno::Inval),
        (WasiFunction::EnvironSizesGet, [i(0), i(0)], Errno::Inval),
        (WasiFunction::ArgsGet, [i(63), i(16)], Errno::Fault),
        (WasiFunction::EnvironGet, [i(65), i(64)], Errno::Fault),
        (WasiFunction::ArgsGet, [i(u32::MAX), i(16)], Errno::Fault),
    ] {
        assert_eq!(context.dispatch(function, &args, &mut memory), e(expected));
        assert_eq!(memory, prior);
    }
}

#[test]
fn granted_sink_metadata_denials_close_and_captures_are_context_local() {
    let mut context = ctx();
    let mut memory = [0xa5; 128];
    assert_eq!(
        context.dispatch(WasiFunction::FdFdstatGet, &[i(1), i(8)], &mut memory),
        ok()
    );
    let mut expected = [0; 24];
    expected[8] = 64;
    assert_eq!(&memory[8..32], &expected);
    for function in [
        WasiFunction::FdFdstatSetFlags,
        WasiFunction::FdFilestatGet,
        WasiFunction::FdFilestatSetSize,
        WasiFunction::FdFilestatSetTimes,
        WasiFunction::FdPread,
        WasiFunction::FdRead,
        WasiFunction::FdReaddir,
        WasiFunction::FdSeek,
        WasiFunction::FdSync,
        WasiFunction::FdTell,
    ] {
        for fd in [0, 1, 2, 3, u32::MAX] {
            let mut args: Vec<_> = function
                .parameters()
                .iter()
                .map(|t| {
                    if *t == Type::I64 {
                        Value::I64(-1)
                    } else {
                        i(u32::MAX)
                    }
                })
                .collect();
            args[0] = i(fd);
            let prior = memory;
            assert_eq!(
                context.dispatch(function, &args, &mut memory),
                e(if fd == 1 || fd == 2 {
                    Errno::Notcapable
                } else {
                    Errno::Badf
                })
            );
            assert_eq!(memory, prior);
        }
    }
    assert_eq!(
        context.dispatch(WasiFunction::FdClose, &[i(1)], &mut memory),
        ok()
    );
    assert_eq!(
        context.dispatch(WasiFunction::FdClose, &[i(1)], &mut memory),
        e(Errno::Badf)
    );
    assert_eq!(
        context.dispatch(WasiFunction::FdFdstatGet, &[i(1), i(u32::MAX)], &mut memory),
        e(Errno::Badf)
    );
    assert_eq!(
        context.dispatch(WasiFunction::FdFdstatGet, &[i(2), i(u32::MAX)], &mut memory),
        e(Errno::Fault)
    );
    let mut other = ctx();
    assert_eq!(
        other.dispatch(WasiFunction::FdFdstatGet, &[i(1), i(0)], &mut memory),
        ok()
    );
}

#[test]
fn exact_multivector_log_combined_capacity_zero_progress_and_zero_length() {
    let mut context = WasiContext::new(
        grants(),
        WasiBudget {
            log_bytes: 8,
            ..WasiBudget::default()
        },
        Cancellation::default(),
    )
    .unwrap();
    let mut memory = [0xa5; 128];
    vector(&mut memory, 0, 40, 3);
    vector(&mut memory, 8, 50, 2);
    memory[40..43].copy_from_slice(b"abc");
    memory[50..52].copy_from_slice(b"de");
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(2), i(120)],
            &mut memory
        ),
        ok()
    );
    assert_eq!(context.stdout(), b"abcde");
    assert_eq!(get32(&memory, 120), 5);
    vector(&mut memory, 0, 40, 3);
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(2), i(0), i(1), i(120)],
            &mut memory
        ),
        ok()
    );
    assert_eq!(context.stderr(), b"abc");
    assert_eq!(context.usage().log_bytes, 8);
    let prior = memory;
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(1), i(120)],
            &mut memory
        ),
        e(Errno::Nospc)
    );
    assert_eq!(memory, prior);
    assert_eq!(context.stdout(), b"abcde");
    assert_eq!(context.stderr(), b"abc");
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(128), i(0), i(120)],
            &mut memory
        ),
        ok()
    );
    assert_eq!(get32(&memory, 120), 0);
    assert_eq!(context.usage().log_bytes, 8);
    vector(&mut memory, 0, 128, 0);
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(1), i(120)],
            &mut memory
        ),
        ok()
    );
    vector(&mut memory, 0, 129, 0);
    let prior = memory;
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(1), i(120)],
            &mut memory
        ),
        e(Errno::Fault)
    );
    assert_eq!(memory, prior);
}

#[test]
fn iovec_fault_alias_unsigned_and_boundaries_fail_without_progress() {
    for (pointer, count, written, payload, length, expected) in [
        (0, 1, 0, 32, 4, Errno::Inval),
        (0, 1, 32, 32, 4, Errno::Inval),
        (0, 1, 33, 32, 4, Errno::Inval),
        (0, 1, 125, 32, 4, Errno::Fault),
        (u32::MAX, 1, 120, 32, 4, Errno::Fault),
        (125, 1, 120, 32, 4, Errno::Fault),
        (0, 1, 120, u32::MAX, 1, Errno::Fault),
        (0, 1, 120, 0, u32::MAX, Errno::Fault),
        (129, 0, 120, 32, 4, Errno::Fault),
        (0, 1, 120, 129, 0, Errno::Fault),
    ] {
        let mut context = ctx();
        let mut memory = [0xa5; 128];
        vector(&mut memory, 0, payload, length);
        let prior = memory;
        assert_eq!(
            context.dispatch(
                WasiFunction::FdWrite,
                &[i(1), i(pointer), i(count), i(written)],
                &mut memory
            ),
            e(expected)
        );
        assert_eq!(memory, prior);
        assert!(context.stdout().is_empty());
    }
    let mut memory = vec![0xa5; 70_000];
    for total in [65_536u32, 65_537] {
        let mut context = ctx();
        vector(&mut memory, 0, 1024, total);
        let prior = memory.clone();
        let outcome = context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(1), i(16)],
            &mut memory,
        );
        if total == 65_536 {
            assert_eq!(outcome, ok());
            assert_eq!(context.stdout().len(), 65_536);
        } else {
            assert_eq!(
                outcome,
                WasiOutcome::Failure(WasiFailure::Budget(Resource::TransferSize))
            );
            assert_eq!(memory, prior);
        }
    }
    let mut context = ctx();
    let mut memory = [0; 1024];
    for at in 0..64 {
        vector(&mut memory, at * 8, 1024, 0);
    }
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(64), i(600)],
            &mut memory
        ),
        ok()
    );
    let mut context = ctx();
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(u32::MAX), i(600)],
            &mut memory
        ),
        WasiOutcome::Failure(WasiFailure::Budget(Resource::Iovecs))
    );
}

#[test]
fn real_os_random_and_clock_services_and_independent_grants() {
    let mut context = ctx();
    let mut memory = [0xa5; 1024];
    assert_eq!(
        context.dispatch(WasiFunction::RandomGet, &[i(16), i(512)], &mut memory),
        ok()
    );
    assert_ne!(&memory[16..528], &[0xa5; 512]);
    assert_eq!(&memory[..16], &[0xa5; 16]);
    assert_eq!(&memory[528..], &[0xa5; 496]);
    assert_eq!(context.usage().random_bytes, 512);
    let prior = memory;
    assert_eq!(
        context.dispatch(WasiFunction::RandomGet, &[i(1024), i(0)], &mut memory),
        ok()
    );
    assert_eq!(memory, prior);
    assert_eq!(
        context.dispatch(WasiFunction::RandomGet, &[i(1025), i(0)], &mut memory),
        e(Errno::Fault)
    );
    for id in [0, 1] {
        assert_eq!(
            context.dispatch(WasiFunction::ClockResGet, &[i(id), i(0)], &mut memory),
            ok()
        );
        assert!(get64(&memory, 0) > 0);
        let before = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        assert_eq!(
            context.dispatch(
                WasiFunction::ClockTimeGet,
                &[i(id), Value::I64(-1), i(8)],
                &mut memory
            ),
            ok()
        );
        let first = get64(&memory, 8);
        let after = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        if id == 0 {
            assert!((before..=after).contains(&(first as u128)));
        }
        assert_eq!(
            context.dispatch(
                WasiFunction::ClockTimeGet,
                &[i(id), Value::I64(0), i(8)],
                &mut memory
            ),
            ok()
        );
        assert!(get64(&memory, 8) >= first);
    }
    for id in [2, 3, 4, u32::MAX] {
        let prior = memory;
        assert_eq!(
            context.dispatch(
                WasiFunction::ClockResGet,
                &[i(id), i(u32::MAX)],
                &mut memory
            ),
            e(if id < 4 {
                Errno::Notcapable
            } else {
                Errno::Inval
            })
        );
        assert_eq!(memory, prior);
    }
    for native in [
        WasiGrants::default(),
        WasiGrants {
            realtime: true,
            ..WasiGrants::default()
        },
        WasiGrants {
            monotonic: true,
            ..WasiGrants::default()
        },
    ] {
        let mut context =
            WasiContext::new(native, WasiBudget::default(), Cancellation::default()).unwrap();
        for id in [0, 1] {
            assert_eq!(
                context.dispatch(WasiFunction::ClockResGet, &[i(id), i(0)], &mut memory),
                if (id == 0 && native.realtime) || (id == 1 && native.monotonic) {
                    ok()
                } else {
                    e(Errno::Notcapable)
                }
            );
        }
        let prior = memory;
        assert_eq!(
            context.dispatch(
                WasiFunction::RandomGet,
                &[i(u32::MAX), i(u32::MAX)],
                &mut memory
            ),
            e(Errno::Notcapable)
        );
        assert_eq!(memory, prior);
    }
}

#[test]
fn budget_widening_and_exit_unsigned_terminal_state() {
    let max = WasiBudget::default();
    for invalid in [
        WasiBudget {
            calls: max.calls + 1,
            ..max
        },
        WasiBudget {
            transfer_bytes: u64::MAX,
            ..max
        },
        WasiBudget {
            work: max.work + 1,
            ..max
        },
        WasiBudget {
            one_transfer_bytes: u32::MAX,
            ..max
        },
        WasiBudget {
            iovecs: max.iovecs + 1,
            ..max
        },
        WasiBudget {
            log_bytes: max.log_bytes + 1,
            ..max
        },
        WasiBudget {
            deadline_ms: u64::MAX,
            ..max
        },
    ] {
        assert!(matches!(
            WasiContext::new(grants(), invalid, Cancellation::default()),
            Err(WasiFailure::InvalidBudget)
        ));
    }
    let mut context = ctx();
    let mut memory = [0xa5; 8];
    assert_eq!(
        context.dispatch(WasiFunction::ProcExit, &[i(u32::MAX)], &mut memory),
        WasiOutcome::Exit(u32::MAX)
    );
    let usage = context.usage();
    assert_eq!(
        context.dispatch(WasiFunction::RandomGet, &[Value::F32(0)], &mut memory),
        WasiOutcome::Exit(u32::MAX)
    );
    assert_eq!(context.usage(), usage);
    assert_eq!(usage.failures, 1);
    assert_eq!(memory, [0xa5; 8]);
    let r = usage.reservations;
    assert_eq!(r.staging_bytes, 65_536);
    assert_eq!(r.rollback_bytes, 65_536);
    assert_eq!(r.stdout_bytes, 65_536);
    assert_eq!(r.stderr_bytes, 65_536);
    assert_eq!(
        r.current_bytes,
        r.fixed_state_bytes + r.staging_bytes + r.rollback_bytes + r.stdout_bytes + r.stderr_bytes
    );
    assert_eq!(r.current_bytes, r.peak_bytes);
}

#[test]
fn dispatch_types_and_denied_paths_cannot_bypass_the_boundary() {
    for function in WasiFunction::ALL {
        let valid: Vec<_> = function
            .parameters()
            .iter()
            .map(|ty| Value::zero(*ty))
            .collect();
        for malformed in [
            Vec::new(),
            {
                let mut wrong = valid.clone();
                wrong[0] = Value::F64(0);
                wrong
            },
            {
                let mut extra = valid.clone();
                extra.push(i(0));
                extra
            },
        ] {
            let mut context = ctx();
            let mut memory = [0xa5; 64];
            assert_eq!(
                context.dispatch(function, &malformed, &mut memory),
                WasiOutcome::Failure(WasiFailure::InvalidArguments)
            );
            assert_eq!(context.usage().calls, 0);
            assert_eq!(memory, [0xa5; 64]);
        }
    }
    for function in [
        WasiFunction::PathCreateDirectory,
        WasiFunction::PathFilestatGet,
        WasiFunction::PathFilestatSetTimes,
        WasiFunction::PathLink,
        WasiFunction::PathOpen,
        WasiFunction::PathReadlink,
        WasiFunction::PathRemoveDirectory,
        WasiFunction::PathRename,
        WasiFunction::PathSymlink,
        WasiFunction::PathUnlinkFile,
        WasiFunction::FdPrestatGet,
        WasiFunction::FdPrestatDirName,
    ] {
        let mut args: Vec<_> = function
            .parameters()
            .iter()
            .map(|ty| {
                if *ty == Type::I64 {
                    Value::I64(-1)
                } else {
                    i(u32::MAX)
                }
            })
            .collect();
        args[0] = i(1);
        let mut context = ctx();
        let mut memory = [0xa5; 64];
        assert_eq!(
            context.dispatch(function, &args, &mut memory),
            e(Errno::Badf)
        );
        assert_eq!(memory, [0xa5; 64]);
    }
    let mut context = ctx();
    let mut memory = [0xa5; 8];
    assert_eq!(
        context.dispatch(WasiFunction::ClockResGet, &[i(0), i(1)], &mut memory),
        e(Errno::Fault)
    );
    assert_eq!(
        context.dispatch(
            WasiFunction::RandomGet,
            &[i(u32::MAX), i(u32::MAX)],
            &mut memory
        ),
        e(Errno::Fault)
    );
    assert_eq!(memory, [0xa5; 8]);
    let mut context = WasiContext::new(
        grants(),
        WasiBudget {
            log_bytes: 0,
            ..WasiBudget::default()
        },
        Cancellation::default(),
    )
    .unwrap();
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(8), i(0), i(0)],
            &mut memory
        ),
        ok()
    );
    assert_eq!(get32(&memory, 0), 0);
    let mut context = ctx();
    let mut memory = vec![0xa5; 70_000];
    vector(&mut memory, 0, 1024, 65_536);
    vector(&mut memory, 8, 1024, 65_536);
    let prior = memory.clone();
    assert_eq!(
        context.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(2), i(32)],
            &mut memory
        ),
        WasiOutcome::Failure(WasiFailure::Budget(Resource::TransferSize))
    );
    assert_eq!(memory, prior);
    assert!(context.stdout().is_empty());
}
