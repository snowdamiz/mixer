#!/usr/bin/env python3
from pathlib import Path
P=Path(__file__).resolve().parent/'source/vm/src/experimental_swift_reactor'
p=P/'retained_profile_loader_v1.rs';s=p.read_text()
s=s.replace('storage_at_allocation: Cell<u64> }','storage_at_allocation: Cell<u64>, panic_on_drop: Cell<Option<usize>> }')
s=s.replace('impl Drop for Guard { fn drop(&mut self) { self.trace.drops.borrow_mut().push(self.tag); } }','''impl Drop for Guard { fn drop(&mut self) {
            self.trace.drops.borrow_mut().push(self.tag);
            if self.trace.panic_on_drop.get() == Some(self.tag) {
                self.trace.panic_on_drop.set(None);
                panic!("original guard destruction unwind");
            }
        } }''')
anchor='        // Independent desired-property witness.';a=s.index(anchor)
s=s[:a]+'''        #[test] fn h24_bound_payload_destruction_unwind_preserves_permanent_charge() {
            for kind in 0..4 {
                let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                let held={let(mut expected,attempt)=owner.correlation_scope_core_v1().unwrap();
                    let mut supplied=carrier(&owner.expected,&trace);
                    match kind {1=>supplied.selected=Err(LoaderFailureV1::new(Refusal::Io,Role::Source,24,3)),
                        2=>supplied.selected.as_mut().unwrap().provenance.source[0]^=1,3=>expected.association+=1,_=>{}}
                    correlate_core_v1(attempt,supplied,&expected)};
                let before=r.usage.get();trace.panic_on_drop.set(Some(21));
                assert!(catch_unwind(AssertUnwindSafe(||drop(held))).is_err());
                assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);
                assert_eq!(r.usage.get(),before);
                let retained=assert_correlation_barrier_v1(owner,&trace);drop(retained);
                assert_eq!(r.usage.get(),before);
                assert_eq!(*trace.drops.borrow(),(20..24).chain(0..13).collect::<Vec<_>>());
            }
        }
''' +s[a:]
s=s.replace('    // OWNER_PROBE_INSERTION','''    // Probe fragments contain compile-only functions, no constructor or unwrap
    // API. Their exact bytes and cfg/environment are in the separate roster.
    #[cfg(mixer_ir02_probe_owner_v1)]
    include!(env!("MIXER_IR02_PROBE_PATH_V1"));
    // OWNER_PROBE_INSERTION''')
s+='''\n#[cfg(mixer_ir02_probe_facade_v1)]\ninclude!(env!("MIXER_IR02_PROBE_PATH_V1"));\n'''
p.write_text(s)
p=P/'cache/initial_profile_v1.rs';s=p.read_text()
anchor='    fn invoke_loaded_leaf_once_v1(';a=s.index(anchor)
s=s[:a]+'''    #[cfg(test)]
    fn positive_admitted_child_after_owner_retirement_v1<'child, 'root>(
        account: &'child TrustedHostAccountV1, fixture: FrozenFixtureV1<'_>,
        owner: AdmittedImmutableOwnerV1<'root>,
    ) -> Result<PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>, RefusalV1> {
        let returned = {
            let (expected, attempt) = owner.correlation_scope_v1().unwrap();
            run_one_admitted_fixture_v1(account, fixture, attempt, &expected)
        };
        crate::experimental_swift_reactor::retained_profile_loader_v1::retire_admitted_owner_v1(owner);
        returned
    }
    #[cfg(mixer_ir02_probe_cache_v1)]
    include!(env!("MIXER_IR02_PROBE_PATH_V1"));

''' +s[a:]
p.write_text(s)
