#[cfg(test)]
mod review {
    use mixer_vm::{Cancellation, Limits, Profile, Value};
    use mixer_vm::experimental::{cache::{CacheBudget, FunctionCache}, execution::{ExecutionBudget, ExecutionFailureKind, SpanInstance}, validate_spans, ValidationBudget};

    // Original literal encodings: () -> i32 function returning 7, and a directly
    // exported exact legacy () -> () checkpoint import. No external fixture code.
    const SCALAR: &[u8] = b"\0asm\x01\0\0\0\x01\x05\x01\x60\0\x01\x7f\x03\x02\x01\0\x07\x07\x01\x03run\0\0\x0a\x06\x01\x04\0\x41\x07\x0b";
    const IMPORT: &[u8] = b"\0asm\x01\0\0\0\x01\x04\x01\x60\0\0\x02\x14\x01\x05mixer\x0acheckpoint\0\0\x07\x07\x01\x03run\0\0";
    fn cache(bytes: &[u8], limits: Limits) -> FunctionCache {
        let token = Cancellation::default();
        let proof = validate_spans(bytes, limits, ValidationBudget::default(), &token).unwrap();
        FunctionCache::new(proof, CacheBudget::default(), &token).unwrap()
    }
    fn instance(bytes: &[u8], limits: Limits, budget: ExecutionBudget) -> SpanInstance {
        SpanInstance::new(cache(bytes, limits), budget, Cancellation::default()).unwrap()
    }
    fn clean(instance: &SpanInstance) {
        let u=instance.usage();
        assert_eq!((u.frames,u.live_values,u.live_controls,u.active_pins),(0,0,0,0));
        assert_eq!((instance.cache_usage().active_pins,instance.cache_usage().pinned_bytes),(0,0));
    }
    #[test]
    fn direct_import_uses_no_value_control_arena_and_limits_stay_cumulative() {
        let mut vm=instance(IMPORT, Limits {fuel:3, host_calls:2,..Limits::default()}, ExecutionBudget {live_values:0,live_controls:0,..ExecutionBudget::default()});
        for _ in 0..2 {assert_eq!(vm.invoke("run", &[]).unwrap(),None); clean(&vm);}
        let error=vm.invoke("run", &[]).unwrap_err();
        assert_eq!(error.kind,ExecutionFailureKind::HostCallLimit);
        assert_eq!((vm.usage().instructions,vm.usage().fuel_used,vm.usage().host_calls),(3,3,2));
        clean(&vm); let usage=vm.usage(); vm.cancellation().cancel();
        assert_eq!(vm.invoke("missing", &[Value::I32(999)]),Err(error));
        assert_eq!(vm.usage(),usage);
    }
    #[test]
    fn work_limit_is_lifetime_cumulative_and_fails_before_extra_dispatch() {
        let mut probe=instance(SCALAR,Limits::default(),ExecutionBudget::default());
        assert_eq!(probe.invoke("run",&[]).unwrap(),Some(Value::I32(7)));
        let exact=probe.usage().work_used;
        let mut vm=instance(SCALAR,Limits::default(),ExecutionBudget {work_credits:exact,..ExecutionBudget::default()});
        assert_eq!(vm.invoke("run",&[]).unwrap(),Some(Value::I32(7)));
        let before=vm.usage(); let error=vm.invoke("run",&[]).unwrap_err();
        assert_eq!(error.kind,ExecutionFailureKind::WorkExhausted);
        assert_eq!(vm.usage().work_used,exact);
        assert_eq!(vm.usage().instructions,before.instructions);
        clean(&vm);
    }
    #[test]
    fn constructor_failure_reports_no_live_pins_after_consuming_pre_pinned_cache() {
        let token=Cancellation::default();
        let mut owned=cache(SCALAR,Limits::default());
        let external_token=owned.pin(0,&token).unwrap();
        let error=SpanInstance::new(owned,ExecutionBudget::default(),token).err().unwrap();
        assert_eq!(error.code,"preexisting_cache_pins");
        assert_eq!(error.attempted,1);
        assert_eq!(error.usage.state_reserved,0);
        // The consumed cache has been destroyed: its pin record has no live owner.
        assert_eq!(error.usage.active_pins,0,"construction diagnostic must describe post-cleanup live state");
        drop(external_token);
    }
    #[cfg(all(target_vendor="apple",target_arch="aarch64"))]
    #[test]
    fn changed_host_rounding_fails_closed_and_becomes_sticky_without_dispatch() {
        unsafe extern "C" {fn fegetround()->i32; fn fesetround(mode:i32)->i32;}
        struct Restore(i32);
        impl Drop for Restore {fn drop(&mut self){unsafe {assert_eq!(fesetround(self.0),0);}}}
        let old=unsafe {fegetround()}; let _restore=Restore(old);
        assert_eq!(unsafe {fesetround(0)},0);
        let mut floats=instance(SCALAR,Limits {profile:Profile::NumericV2,..Limits::default()},ExecutionBudget::default());
        assert_eq!(floats.invoke("run",&[]).unwrap(),Some(Value::I32(7)));
        let before=floats.usage();
        // Official SDK fenv.h arm64 FE_UPWARD = 0x00400000.
        assert_eq!(unsafe {fesetround(0x00400000)},0);
        let error=floats.invoke("run",&[]).unwrap_err();
        assert_eq!(error.kind,ExecutionFailureKind::UnsupportedEnvironment);
        assert_eq!(floats.usage().instructions,before.instructions);
        clean(&floats);
        assert_eq!(unsafe {fesetround(0)},0);
        assert_eq!(floats.invoke("run",&[]),Err(error));
        // Integer-v1 does not use floating arithmetic and retains its scope.
        let mut integers=instance(SCALAR,Limits::default(),ExecutionBudget::default());
        assert_eq!(unsafe {fesetround(0x00400000)},0);
        assert_eq!(integers.invoke("run",&[]).unwrap(),Some(Value::I32(7)));
        clean(&integers);
    }
}
