from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OVER=HERE/'overlay/src/experimental_swift_reactor';CAND=ROOT/'verification/swift-control-accounting-candidate-2/overlay/src/experimental_swift_reactor'
for name in ['frame_operations.rs','value_operations.rs','control.rs']:
 p=OVER/name
 if not p.exists():p.write_bytes(((CAND/name) if (CAND/name).exists() else ROOT/'vm/src/experimental_swift_reactor'/name).read_bytes())
p=OVER/'frame_operations.rs';s=p.read_text();s=s.replace('    fn work(&mut self, amount: usize) -> Result<(), SwiftRunFailure> {\n','    fn work(&mut self, amount: usize) -> Result<(), SwiftRunFailure> {\n        #[cfg(test)]\n        tests::control_work_checkpoint(self.phase.operation.control);\n',1)
s=s.replace('#[path = "control_operations.rs"]','#[cfg(test)]\npub(super) fn control_after_value_pop(control: &mut RuntimeControl) {\n    tests::control_after_value_pop(control);\n}\n#[cfg(test)]\npub(super) fn control_work_checkpoint(control: &RuntimeControl) {\n    tests::control_work_checkpoint(control);\n}\n#[path = "control_operations.rs"]',1);p.write_text(s)
p=OVER/'value_operations.rs';s=p.read_text();needle='    let value = values.pop().expect("checked operand exists");\n';assert s.count(needle)==1;s=s.replace(needle,needle+'    #[cfg(test)]\n    super::frame_operations::control_after_value_pop(operation.control);\n')
# Count both primitive pop/push work boundaries (saved close push included).
for fn in ['primitive_pop','primitive_push']:
 a=s.index('fn '+fn+'(');b=s.index('    operation.control.work_with_wasi(',a);s=s[:b]+'    #[cfg(test)]\n    super::frame_operations::control_work_checkpoint(operation.control);\n'+s[b:]
p.write_text(s)
p=OVER/'control.rs';s=p.read_text();needle='    pub(crate) fn test_replace_execution_work_limit(&mut self, ceiling: u64) -> u64 {';a=s.index(needle);s=s[:a]+'''    pub(crate) fn test_replace_combined_limit(&mut self, ceiling: usize) -> usize {
        std::mem::replace(&mut self.budget.combined_bytes, ceiling)
    }
    pub(crate) fn test_replace_state_limit(&mut self, ceiling: usize) -> usize {
        std::mem::replace(&mut self.budget.state_bytes, ceiling)
    }
'''+s[a:];p.write_text(s)
p=OVER/'frame_operations_tests.rs';s=p.read_text();s += '''
// Root-authorized one-shot after-pop fault. No shadow state, synthetic Err or
// direct ledger write: the primitive's original following removal must fail.
pub(super) fn control_after_value_pop(control: &mut RuntimeControl) {
    let inject = HOOKS.with(|slot| {
        let mut hooks = slot.get();
        let inject = hooks.push_fault == 5;
        if inject { hooks.push_fault = 0; slot.set(hooks); }
        inject
    });
    if inject {
        let current = control.usage(None).live.values.current;
        control.remove_live(Live::Values, current).unwrap();
    }
}
pub(super) fn control_work_checkpoint(control: &RuntimeControl) {
    let cancel = HOOKS.with(|slot| {
        let mut hooks = slot.get();
        if hooks.push_fault != 6 { return false; }
        let cancel = hooks.cancel_local == Some(hooks.predebit_seen);
        hooks.predebit_seen += 1;
        slot.set(hooks);
        cancel
    });
    if cancel { control.cancellation().cancel(); }
}
'''
# Cancellation at actual control predebit after its work debit and before publication.
needle='pub(super) fn before_predebit(control: &mut RuntimeControl, resource: Live) -> Option<usize> {\n';s=s.replace(needle,needle+'    if HOOKS.with(|slot| slot.get().push_fault == 7) { control.cancellation().cancel(); }\n',1)
# AF22 bound now may exceed constructor peak; retain either actual gate outcome.
a=s.index('    let tail = match returned.take().unwrap() {',s.index('fn af22_'));b=s.index('    assert_eq!(value_operations::VALUE_OPERATION_BYTES',a)
s=s[:a]+'''    match returned.take().unwrap() {
        Err(ConstructionFailure::Cleanup(tail)) => {
            let mut failure = None;
            let mut final_usage = None;
            tail.complete((pair, returned), &mut failure, &mut final_usage);
            let failure = failure.unwrap();
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(final_usage.unwrap().reservations.combined.current, 0);
            println!("AF22_NARROW constructor_rejection combined_limit={} attempted={} frame_admitted=false", ceiling, failure.attempted);
        }
        Ok(mut actual) => {
            let before = usage(&actual).reservations.construction.current;
            let failure = actual.prepare_frames(cursor()).err().expect("one byte below actual phase admission");
            assert_eq!(failure.kind, SwiftRunFailureKind::CombinedExhausted);
            assert_eq!(usage(&actual).reservations.construction.current, before);
            println!("AF22_NARROW phase_rejection combined_limit={} attempted={} frame_admitted=false", ceiling, failure.attempted);
            retire(actual);
        }
        Err(_) => panic!("unexpected constructor rejection"),
    }
'''+s[b:];p.write_text(s)
