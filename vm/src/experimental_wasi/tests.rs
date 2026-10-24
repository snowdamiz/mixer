use super::*;
use std::cell::Cell;

#[derive(Clone, Copy, Default)]
enum Service {
    #[default]
    Os,
    PartialRandomError,
    SecondRandomError,
    CancelRandom,
    ClockError,
    CancelClock,
    ExpireClock,
    SlowRealClock,
    CancelRealClock,
}
#[derive(Default)]
pub(super) struct TestState {
    service: Service,
    checks: Cell<usize>,
    cancel_at: Cell<Option<usize>>,
    services: Cell<usize>,
}
impl TestState {
    pub(super) fn check(&self, cancellation: &Cancellation) {
        let n = self.checks.get();
        self.checks.set(n + 1);
        if self.cancel_at.get() == Some(n) {
            cancellation.cancel();
        }
    }
    pub(super) fn random(
        &self,
        bytes: &mut [u8],
        cancellation: &Cancellation,
    ) -> Result<(), Errno> {
        self.services.set(self.services.get() + 1);
        match self.service {
            Service::SecondRandomError if self.services.get() == 1 => {
                bytes.fill(7);
                Ok(())
            }
            Service::SecondRandomError => {
                let half = bytes.len() / 2;
                bytes[..half].fill(7);
                Err(Errno::Io)
            }
            Service::PartialRandomError => {
                let half = bytes.len() / 2;
                bytes[..half].fill(7);
                Err(Errno::Io)
            }
            Service::CancelRandom => {
                bytes.fill(9);
                cancellation.cancel();
                Ok(())
            }
            _ => platform::random(bytes),
        }
    }
    pub(super) fn clock(
        &self,
        clock: platform::Clock,
        resolution: bool,
        cancellation: &Cancellation,
    ) -> Result<u64, Errno> {
        self.services.set(self.services.get() + 1);
        match self.service {
            Service::SlowRealClock => {let result=platform::clock(clock,resolution);std::thread::sleep(Duration::from_millis(600));result},
            Service::CancelRealClock => {let result=platform::clock(clock,resolution);cancellation.cancel();result},
            Service::ClockError => Err(Errno::Io),
            Service::CancelClock => {
                cancellation.cancel();
                Ok(42)
            }
            Service::ExpireClock => {
                std::thread::sleep(Duration::from_millis(3));
                Ok(42)
            }
            _ => platform::clock(clock, resolution),
        }
    }
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
fn context(budget: WasiBudget) -> WasiContext {
    WasiContext::new(grants(), budget, Cancellation::default()).unwrap()
}
fn i(n: u32) -> Value {
    Value::I32(n as i32)
}
fn errno(e: Errno) -> WasiOutcome {
    WasiOutcome::Errno(e)
}

#[test]
fn partial_random_failure_never_commits_and_does_not_fabricate_success() {
    let mut ctx = context(WasiBudget::default());
    ctx.test.service = Service::PartialRandomError;
    let mut memory = [0xa5; 512];
    assert_eq!(
        ctx.dispatch(WasiFunction::RandomGet, &[i(0), i(512)], &mut memory),
        errno(Errno::Io)
    );
    assert_eq!(memory, [0xa5; 512]);
    assert_eq!(ctx.usage.random_bytes, 0);
    assert_eq!(ctx.test.services.get(), 1);
    assert_eq!(ctx.usage.transfer_bytes, 512);
    let mut ctx = context(WasiBudget::default());
    ctx.test.service = Service::SecondRandomError;
    assert_eq!(
        ctx.dispatch(WasiFunction::RandomGet, &[i(0), i(512)], &mut memory),
        errno(Errno::Io)
    );
    assert_eq!(memory, [0xa5; 512]);
    assert_eq!(ctx.usage.random_bytes, 256);
    assert_eq!(ctx.test.services.get(), 2);
}

#[test]
fn cancellation_after_services_is_sticky_without_outputs_or_more_services() {
    for (function, args, service) in [
        (
            WasiFunction::RandomGet,
            vec![i(0), i(64)],
            Service::CancelRandom,
        ),
        (
            WasiFunction::ClockResGet,
            vec![i(0), i(0)],
            Service::CancelClock,
        ),
    ] {
        let mut ctx = context(WasiBudget::default());
        ctx.test.service = service;
        let mut memory = [0xa5; 64];
        assert_eq!(
            ctx.dispatch(function, &args, &mut memory),
            WasiOutcome::Failure(WasiFailure::Cancelled)
        );
        assert_eq!(memory, [0xa5; 64]);
        let usage = ctx.usage();
        assert_eq!(
            ctx.dispatch(WasiFunction::ProcExit, &[], &mut memory),
            WasiOutcome::Failure(WasiFailure::Cancelled)
        );
        assert_eq!(ctx.usage(), usage);
        assert_eq!(ctx.test.services.get(), 1);
    }
}

#[test]
fn clock_service_failure_and_expiration_preserve_output() {
    for service in [Service::ClockError, Service::ExpireClock] {
        let mut ctx = context(WasiBudget {
            deadline_ms: 2,
            ..WasiBudget::default()
        });
        ctx.test.service = service;
        let mut memory = [0xa5; 8];
        let result = ctx.dispatch(
            WasiFunction::ClockTimeGet,
            &[i(0), Value::I64(0), i(0)],
            &mut memory,
        );
        assert_eq!(
            result,
            match service {
                Service::ClockError => errno(Errno::Io),
                _ => WasiOutcome::Failure(WasiFailure::Deadline),
            }
        );
        assert_eq!(memory, [0xa5; 8]);
    }
}

#[test]
fn cancellation_at_every_copy_checkpoint_restores_all_outputs_and_logs() {
    for cancel_at in 0..30 {
        let mut ctx = context(WasiBudget::default());
        ctx.test.cancel_at.set(Some(cancel_at));
        let mut memory = [0xa5; 2048];
        let original = memory;
        let outcome = ctx.dispatch(WasiFunction::RandomGet, &[i(0), i(1024)], &mut memory);
        if matches!(outcome, WasiOutcome::Failure(_)) {
            assert_eq!(memory, original, "random checkpoint {cancel_at}");
        } else {
            assert_eq!(outcome, errno(Errno::Success));
        }

        let mut ctx = context(WasiBudget::default());
        ctx.test.cancel_at.set(Some(cancel_at));
        let mut memory = [0xa5; 2048];
        memory[..4].copy_from_slice(&16u32.to_le_bytes());
        memory[4..8].copy_from_slice(&1024u32.to_le_bytes());
        let original = memory;
        let outcome = ctx.dispatch(
            WasiFunction::FdWrite,
            &[i(1), i(0), i(1), i(2044)],
            &mut memory,
        );
        if matches!(outcome, WasiOutcome::Failure(_)) {
            assert_eq!(memory, original, "write checkpoint {cancel_at}");
            assert!(ctx.stdout().is_empty());
            assert_eq!(ctx.usage.log_bytes, 0);
        } else {
            assert_eq!(ctx.stdout(), &original[16..1040]);
        }
    }
    for cancel_at in 0..12 {
        let mut ctx = context(WasiBudget::default());
        ctx.test.cancel_at.set(Some(cancel_at));
        let mut memory = [0xa5; 32];
        let outcome = ctx.dispatch(WasiFunction::ArgsGet, &[i(0), i(8)], &mut memory);
        if matches!(outcome, WasiOutcome::Failure(_)) {
            assert_eq!(memory, [0xa5; 32]);
        }
    }
}

#[test]
fn every_resource_exhaustion_is_terminal_and_never_refills() {
    for (budget, function, args, resource) in [
        (
            WasiBudget {
                calls: 0,
                ..WasiBudget::default()
            },
            WasiFunction::RandomGet,
            vec![i(0), i(8)],
            Resource::Calls,
        ),
        (
            WasiBudget {
                work: 0,
                ..WasiBudget::default()
            },
            WasiFunction::RandomGet,
            vec![i(0), i(8)],
            Resource::Work,
        ),
        (
            WasiBudget {
                work: 8,
                ..WasiBudget::default()
            },
            WasiFunction::RandomGet,
            vec![i(0), i(8)],
            Resource::Work,
        ),
        (
            WasiBudget {
                transfer_bytes: 7,
                ..WasiBudget::default()
            },
            WasiFunction::RandomGet,
            vec![i(0), i(8)],
            Resource::Transfer,
        ),
        (
            WasiBudget {
                one_transfer_bytes: 7,
                ..WasiBudget::default()
            },
            WasiFunction::RandomGet,
            vec![i(0), i(8)],
            Resource::TransferSize,
        ),
        (
            WasiBudget {
                iovecs: 0,
                ..WasiBudget::default()
            },
            WasiFunction::FdWrite,
            vec![i(1), i(0), i(1), i(16)],
            Resource::Iovecs,
        ),
    ] {
        let mut ctx = context(budget);
        let mut memory = [0xa5; 32];
        let expected = WasiOutcome::Failure(WasiFailure::Budget(resource));
        assert_eq!(ctx.dispatch(function, &args, &mut memory), expected);
        assert_eq!(memory, [0xa5; 32]);
        assert_eq!(ctx.test.services.get(), 0);
        let usage = ctx.usage();
        assert_eq!(ctx.dispatch(function, &args, &mut memory), expected);
        assert_eq!(ctx.usage(), usage);
    }
    let mut ctx = context(WasiBudget {
        calls: 2,
        transfer_bytes: 16,
        ..WasiBudget::default()
    });
    let mut memory = [0; 8];
    for _ in 0..2 {
        assert_eq!(
            ctx.dispatch(WasiFunction::ClockResGet, &[i(0), i(0)], &mut memory),
            errno(Errno::Success)
        );
    }
    assert_eq!(
        ctx.dispatch(WasiFunction::ClockResGet, &[i(0), i(0)], &mut memory),
        WasiOutcome::Failure(WasiFailure::Budget(Resource::Calls))
    );
    let mut ctx = context(WasiBudget {
        transfer_bytes: 8,
        ..WasiBudget::default()
    });
    assert_eq!(
        ctx.dispatch(WasiFunction::ClockResGet, &[i(0), i(0)], &mut memory),
        errno(Errno::Success)
    );
    assert_eq!(
        ctx.dispatch(WasiFunction::ClockResGet, &[i(0), i(0)], &mut memory),
        WasiOutcome::Failure(WasiFailure::Budget(Resource::Transfer))
    );
}

#[test]
fn zero_deadline_and_precancelled_context_do_no_services() {
    let mut expired = context(WasiBudget {
        deadline_ms: 0,
        ..WasiBudget::default()
    });
    let mut memory = [0xa5; 8];
    assert_eq!(
        expired.dispatch(WasiFunction::ClockResGet, &[i(0), i(0)], &mut memory),
        WasiOutcome::Failure(WasiFailure::Deadline)
    );
    let cancellation = Cancellation::default();
    cancellation.cancel();
    let mut ctx = WasiContext::new(grants(), WasiBudget::default(), cancellation).unwrap();
    assert_eq!(
        ctx.dispatch(WasiFunction::RandomGet, &[i(0), i(8)], &mut memory),
        WasiOutcome::Failure(WasiFailure::Cancelled)
    );
    assert_eq!(ctx.test.services.get(), 0);
    assert_eq!(memory, [0xa5; 8]);
}

#[test]
fn invalid_args_precede_budget_and_terminal_precedes_invalid_args() {
    let mut ctx = context(WasiBudget {
        calls: 0,
        ..WasiBudget::default()
    });
    assert_eq!(
        ctx.dispatch(WasiFunction::ClockTimeGet, &[i(0), i(0), i(0)], &mut []),
        WasiOutcome::Failure(WasiFailure::InvalidArguments)
    );
    assert_eq!(
        ctx.dispatch(WasiFunction::RandomGet, &[i(0), i(0)], &mut []),
        WasiOutcome::Failure(WasiFailure::InvalidArguments)
    );
    assert_eq!(ctx.usage.calls, 0);
}

impl TestState {
 pub(super) fn host_set_cancel(&self,at:usize){self.cancel_at.set(Some(at));}
 pub(super) fn host_set_service(&mut self,kind:u8){self.service=match kind{1=>Service::PartialRandomError,5=>Service::CancelRandom,8=>Service::SlowRealClock,9=>Service::CancelRealClock,_=>Service::Os};}
 pub(super) fn host_services(&self)->usize{self.services.get()}
}
