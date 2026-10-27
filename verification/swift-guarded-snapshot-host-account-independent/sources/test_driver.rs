#![allow(dead_code)]
mod account {
    include!("frozen_host_account.rs");
    #[cfg(test)] mod independent {
        use super::*;
        use std::panic::{catch_unwind, AssertUnwindSafe};
        use std::rc::Rc;
        fn account(work:u64, storage:u64)->TrustedHostAccountV1 {
            TrustedHostAccountV1::from_preexisting_root_v1(TrustedRootPolicyV1 {
                child_limits:CostV1{work,storage},p0_preexisting_allocation:CostV1{work:1,storage:1},source_and_review_binding:[0;32],
            })
        }
        fn quote(work:u64,storage:u64)->ReviewedWholeQuoteV1 {ReviewedWholeQuoteV1{total:CostV1{work,storage}}}
        fn denied<T>(value:Result<T,RefusalV1>)->RefusalV1 {match value {Err(e)=>e,Ok(_)=>panic!("expected refusal")}}
        #[test] fn explicit_destroy_unwind_keeps_all_charge_and_drops_payload_once() {
            struct Bomb<'a>{a:&'a TrustedHostAccountV1,count:Rc<Cell<u32>>}
            impl Drop for Bomb<'_>{fn drop(&mut self){assert_eq!(self.a.usage_v1().storage,21);self.count.set(self.count.get()+1);panic!("expected explicit retirement panic")}}
            let a=account(9,21);let count=Rc::new(Cell::new(0));
            let owned=a.reserve_whole_v1(quote(9,21)).unwrap().dispatch_v1(||Bomb{a:&a,count:count.clone()});
            let result=catch_unwind(AssertUnwindSafe(||owned.destroy_owned_v1()));
            assert!(result.is_err());assert_eq!(count.get(),1);
            assert_eq!(a.usage_v1(),UsageV1{work:9,storage:21,peak_storage:21});
        }
        #[test] fn discarding_completed_token_keeps_charge_after_payload_has_died() {
            struct Count(Rc<Cell<u32>>);impl Drop for Count{fn drop(&mut self){self.0.set(self.0.get()+1)}}
            let a=account(50,50);let count=Rc::new(Cell::new(0));
            let owned=a.reserve_whole_v1(quote(13,17)).unwrap().dispatch_v1(||Count(count.clone()));
            let token=owned.destroy_owned_v1().unwrap();assert_eq!(count.get(),1);
            drop(token);assert_eq!(a.usage_v1(),UsageV1{work:13,storage:17,peak_storage:17});
        }
        #[test] fn forgotten_ticket_and_owner_cannot_refund() {
            let a=account(100,100);
            std::mem::forget(a.reserve_whole_v1(quote(4,11)).unwrap());
            std::mem::forget(a.reserve_whole_v1(quote(6,13)).unwrap().dispatch_v1(||17u64));
            assert_eq!(a.usage_v1(),UsageV1{work:10,storage:24,peak_storage:24});
        }
        #[test] fn storage_reuse_does_not_replenish_work_or_lower_peak() {
            let a=account(15,7);
            for amount in [4,4,7]{
                let owned=a.reserve_whole_v1(quote(amount,7)).unwrap().dispatch_v1(||());
                owned.destroy_owned_v1().unwrap().release_destroyed_v1();
            }
            assert_eq!(a.usage_v1(),UsageV1{work:15,storage:0,peak_storage:7});
            assert_eq!(denied(a.reserve_whole_v1(quote(1,1))),RefusalV1::InsufficientWork);
            assert_eq!(a.usage_v1(),UsageV1{work:15,storage:0,peak_storage:7});
        }
        #[test] fn reentrant_callback_sees_precharge_and_cannot_bypass_capacity() {
            let a=account(100,25);
            let first=a.reserve_whole_v1(quote(7,10)).unwrap().dispatch_v1(||{
                let inner=a.reserve_whole_v1(quote(9,15)).unwrap().dispatch_v1(||());
                assert_eq!(denied(a.reserve_whole_v1(quote(1,1))),RefusalV1::InsufficientStorage);
                assert_eq!(a.usage_v1(),UsageV1{work:16,storage:25,peak_storage:25});
                inner.destroy_owned_v1().unwrap().release_destroyed_v1();
                assert_eq!(a.usage_v1(),UsageV1{work:16,storage:10,peak_storage:25});
            });
            first.destroy_owned_v1().unwrap().release_destroyed_v1();
            assert_eq!(a.usage_v1(),UsageV1{work:16,storage:0,peak_storage:25});
        }
        #[test] fn corrupted_subtraction_invariant_fails_closed_without_wrap_or_panic() {
            let a=account(100,100);
            let token=a.reserve_whole_v1(quote(7,19)).unwrap().dispatch_v1(||()).destroy_owned_v1().unwrap();
            // Deliberate private test mutation; no public path exposes Cell.
            let inconsistent=UsageV1{work:7,storage:18,peak_storage:19};a.usage.set(inconsistent);
            token.release_destroyed_v1();assert_eq!(a.usage_v1(),inconsistent);
        }
        #[test] fn out_of_order_retirements_release_only_their_own_storage() {
            let a=account(100,100);
            let one=a.reserve_whole_v1(quote(2,3)).unwrap().dispatch_v1(||1);
            let two=a.reserve_whole_v1(quote(5,7)).unwrap().dispatch_v1(||2);
            let three=a.reserve_whole_v1(quote(11,13)).unwrap().dispatch_v1(||3);
            let second=two.destroy_owned_v1().unwrap();let first=one.destroy_owned_v1().unwrap();
            assert_eq!(a.usage_v1().storage,23);first.release_destroyed_v1();
            assert_eq!(a.usage_v1().storage,20);second.release_destroyed_v1();
            assert_eq!(three.inspect_v1(),Some(&3));assert_eq!(a.usage_v1().storage,13);
            three.destroy_owned_v1().unwrap().release_destroyed_v1();
            assert_eq!(a.usage_v1(),UsageV1{work:18,storage:0,peak_storage:23});
        }
        #[test] fn refusals_preserve_preexisting_live_and_retired_peak_usage() {
            let a=account(20,40);
            let retired=a.reserve_whole_v1(quote(4,25)).unwrap().dispatch_v1(||());
            retired.destroy_owned_v1().unwrap().release_destroyed_v1();
            let live=a.reserve_whole_v1(quote(6,10)).unwrap().dispatch_v1(||());
            let before=UsageV1{work:10,storage:10,peak_storage:25};assert_eq!(a.usage_v1(),before);
            for (work,storage,error) in [(11,1,RefusalV1::InsufficientWork),(1,31,RefusalV1::InsufficientStorage),(u64::MAX,1,RefusalV1::WorkOverflow),(1,u64::MAX,RefusalV1::StorageOverflow)]{
                assert_eq!(denied(a.reserve_whole_v1(quote(work,storage))),error);assert_eq!(a.usage_v1(),before);
            }
            live.destroy_owned_v1().unwrap().release_destroyed_v1();
            assert_eq!(a.usage_v1(),UsageV1{work:10,storage:0,peak_storage:25});
        }
    }
}
