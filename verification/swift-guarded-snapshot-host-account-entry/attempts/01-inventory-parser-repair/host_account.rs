// Private trusted-local accounting primitive. No guest/public constructor,
// allocator, environment input, product-counter borrowing or refund of work.
use std::cell::Cell;

const COMPONENT_COUNT_V1: usize = 6;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct CostV1 {
    work: u64,
    storage: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct UsageV1 {
    work: u64,
    storage: u64,
    peak_storage: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum RefusalV1 {
    RootPolicyPending,
    WholeQuotePending,
    UnpricedComponent(usize),
    QuoteOverflow,
    WorkOverflow,
    StorageOverflow,
    InsufficientWork,
    InsufficientStorage,
}

// A source-reviewed authority root must provision P0 before account creation.
// Both this root record and the account/call/return bookkeeping reside there.
// No selected policy/price exists in this packet; there is no production
// constructor for this opaque type or a completed ReviewedWholeQuoteV1.
struct TrustedRootPolicyV1 {
    child_limits: CostV1,
    p0_preexisting_allocation: CostV1,
    source_and_review_binding: [u8; 32],
}

pub(super) struct ReviewedWholeQuoteV1 {
    total: CostV1,
}

impl ReviewedWholeQuoteV1 {
    // All six required components are explicit: P1 setup, P1 loader (including
    // separately priced original validation), P2 arguments, P3 pre-store shell,
    // P4 selected route, P5 returned owners/diagnostics and their destruction.
    // This checks arithmetic, not evidence; only the private reviewed policy
    // producer may eventually call it. No source-authority claim follows from
    // a digest or from successfully adding arbitrary numbers.
    fn checked_components_v1(parts: [CostV1; COMPONENT_COUNT_V1])
        -> Result<Self, RefusalV1>
    {
        let mut total = CostV1 { work: 0, storage: 0 };
        for (index, part) in parts.into_iter().enumerate() {
            if part.work == 0 || part.storage == 0 {
                return Err(RefusalV1::UnpricedComponent(index));
            }
            total.work = total.work.checked_add(part.work)
                .ok_or(RefusalV1::QuoteOverflow)?;
            total.storage = total.storage.checked_add(part.storage)
                .ok_or(RefusalV1::QuoteOverflow)?;
        }
        Ok(Self { total })
    }
}

pub(super) fn selected_whole_quote_v1()
    -> Result<ReviewedWholeQuoteV1, RefusalV1>
{
    // No unpriced component is assigned zero; no cap or old partial union is
    // converted into a price. Root must change and independently review this
    // source with the final fixture, whole source and every P0..P5 component.
    Err(RefusalV1::WholeQuotePending)
}

pub(super) fn selected_parent_account_v1()
    -> Result<TrustedHostAccountV1, RefusalV1>
{
    // No environment-minted limit and no guessed fixed host budget. A selected
    // root policy must pre-exist fixture setup and must fund this primitive.
    Err(RefusalV1::RootPolicyPending)
}

pub(super) struct TrustedHostAccountV1 {
    limits: CostV1,
    usage: Cell<UsageV1>,
    // Retain the independently provisioned P0 authority/allocation record.
    root: TrustedRootPolicyV1,
}

impl TrustedHostAccountV1 {
    fn from_preexisting_root_v1(root: TrustedRootPolicyV1) -> Self {
        Self {
            limits: root.child_limits,
            usage: Cell::new(UsageV1 { work: 0, storage: 0, peak_storage: 0 }),
            root,
        }
    }

    pub(super) fn usage_v1(&self) -> UsageV1 { self.usage.get() }

    pub(super) fn reserve_whole_v1(&self, quote: ReviewedWholeQuoteV1)
        -> Result<ReservationV1<'_>, RefusalV1>
    {
        let before = self.usage.get();
        let work = before.work.checked_add(quote.total.work)
            .ok_or(RefusalV1::WorkOverflow)?;
        let storage = before.storage.checked_add(quote.total.storage)
            .ok_or(RefusalV1::StorageOverflow)?;
        if work > self.limits.work { return Err(RefusalV1::InsufficientWork); }
        if storage > self.limits.storage { return Err(RefusalV1::InsufficientStorage); }
        let after = UsageV1 {
            work, storage, peak_storage: before.peak_storage.max(storage),
        };
        // Cell is !Sync. No callback, allocation or fallible operation occurs
        // between the comparisons and this single state commit. No partial
        // work/storage/peak update is possible on any refusal above.
        self.usage.set(after);
        Ok(ReservationV1 { account: self, storage: quote.total.storage })
    }
}

// Neither Clone nor Copy; dispatch consumes the only ticket. Dropping an
// unused ticket conservatively retains its charge. There is no refund method.
pub(super) struct ReservationV1<'a> {
    account: &'a TrustedHostAccountV1,
    storage: u64,
}

impl<'a> ReservationV1<'a> {
    pub(super) fn dispatch_v1<T>(self, action: impl FnOnce() -> T)
        -> PrepaidOwnedV1<'a, T>
    {
        // If action unwinds, no release runs. Work and storage stay charged.
        let owned = action();
        PrepaidOwnedV1 { owned: Some(owned), reservation: Some(self) }
    }
}

#[must_use = "Retain the prepaid owner until every original resource/result is destroyed"]
pub(super) struct PrepaidOwnedV1<'a, T> {
    owned: Option<T>,
    reservation: Option<ReservationV1<'a>>,
}

impl<'a, T> PrepaidOwnedV1<'a, T> {
    pub(super) fn inspect_v1(&self) -> Option<&T> { self.owned.as_ref() }
    pub(super) fn destroy_owned_v1(mut self) -> Option<DestroyedStorageV1<'a>> {
        // A successful return certifies that this inner source frame and all
        // payload places/backing ended. The returned token is P0 bookkeeping,
        // independently provisioned by the parent; it contains no T or File.
        // This function itself does NOT release storage.
        if let Some(owned) = self.owned.take() { drop(owned); }
        let reservation = self.reservation.take();
        drop(self);
        reservation.map(|reservation| DestroyedStorageV1 { reservation })
    }
    // Deliberately no mutable access, parts/owned extraction, transfer, Clone,
    // forget-and-refund, result-only or File-only release API.
}

impl<T> Drop for PrepaidOwnedV1<'_, T> {
    fn drop(&mut self) {
        // Ordinary Drop destroys the payload but NEVER releases storage: this
        // wrapper/source frame is still live here. Explicit destruction must
        // return its private token to P0 first. Unwind/no token leaks charge.
        if let Some(owned) = self.owned.take() { drop(owned); }
    }
}

pub(super) struct DestroyedStorageV1<'a> { reservation: ReservationV1<'a> }

impl DestroyedStorageV1<'_> {
    pub(super) fn release_destroyed_v1(self) {
        // Runs only after destroy_owned_v1 returned, in pre-existing P0.
        // This token cannot carry a resource, payload, File or diagnostic.
        let before = self.reservation.account.usage.get();
        if let Some(storage) = before.storage.checked_sub(self.reservation.storage) {
            self.reservation.account.usage.set(UsageV1 { storage, ..before });
        }
        // Impossible inconsistent subtraction also keeps the charge; never
        // wrap, panic while unwinding, or change consumed work/peak here.
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::panic::{catch_unwind, AssertUnwindSafe};
    use std::rc::Rc;

    fn cost(work: u64, storage: u64) -> CostV1 { CostV1 { work, storage } }
    fn quote(work: u64, storage: u64) -> ReviewedWholeQuoteV1 {
        // Pure account tests only. This is not the selected production quote.
        ReviewedWholeQuoteV1 { total: cost(work, storage) }
    }
    fn account(work: u64, storage: u64) -> TrustedHostAccountV1 {
        TrustedHostAccountV1::from_preexisting_root_v1(TrustedRootPolicyV1 {
            child_limits: cost(work, storage),
            p0_preexisting_allocation: cost(1, 1),
            source_and_review_binding: [0; 32],
        })
    }
    fn refusal<T>(result: Result<T, RefusalV1>) -> RefusalV1 {
        match result { Err(e) => e, Ok(_) => panic!("expected refusal") }
    }

    #[test]
    fn production_quote_and_root_policy_fail_closed() {
        assert_eq!(refusal(selected_whole_quote_v1()), RefusalV1::WholeQuotePending);
        assert_eq!(refusal(selected_parent_account_v1()), RefusalV1::RootPolicyPending);
    }

    #[test]
    fn all_six_quote_components_required_and_checked() {
        let q = ReviewedWholeQuoteV1::checked_components_v1([cost(3, 7); 6]).unwrap();
        assert_eq!(q.total, cost(18, 42));
        for index in 0..6 {
            for empty in [cost(0, 1), cost(1, 0)] {
                let mut parts = [cost(1, 1); 6];
                parts[index] = empty;
                assert_eq!(refusal(ReviewedWholeQuoteV1::checked_components_v1(parts)),
                           RefusalV1::UnpricedComponent(index));
            }
        }
        for large in [cost(u64::MAX, 1), cost(1, u64::MAX)] {
            let mut parts = [cost(1, 1); 6];
            parts[0] = large;
            assert_eq!(refusal(ReviewedWholeQuoteV1::checked_components_v1(parts)),
                       RefusalV1::QuoteOverflow);
        }
    }

    #[test]
    fn both_limits_refuse_without_any_partial_mutation_or_callback() {
        for (work, storage, expected) in [
            (9, 30, RefusalV1::InsufficientWork),
            (30, 9, RefusalV1::InsufficientStorage),
            (9, 9, RefusalV1::InsufficientWork),
        ] {
            let a = account(work, storage);
            let before = a.usage_v1();
            let calls = Cell::new(0);
            let result = a.reserve_whole_v1(quote(10, 10));
            match result {
                Ok(r) => { let _ = r.dispatch_v1(|| calls.set(calls.get()+1)); }
                Err(e) => assert_eq!(e, expected),
            }
            assert_eq!(a.usage_v1(), before);
            assert_eq!(calls.get(), 0);
        }
    }

    #[test]
    fn existing_usage_addition_overflow_is_atomic_in_each_dimension() {
        for (before, expected) in [
            (UsageV1 { work: u64::MAX, storage: 0, peak_storage: 0 }, RefusalV1::WorkOverflow),
            (UsageV1 { work: 0, storage: u64::MAX, peak_storage: u64::MAX }, RefusalV1::StorageOverflow),
        ] {
            let a = account(u64::MAX, u64::MAX);
            a.usage.set(before);
            assert_eq!(refusal(a.reserve_whole_v1(quote(1, 1))), expected);
            assert_eq!(a.usage_v1(), before);
        }
    }

    #[test]
    fn exact_limits_charge_before_single_dispatch_and_work_never_refunds() {
        let a = account(7, 11);
        let calls = Cell::new(0);
        let mut once = Some(a.reserve_whole_v1(quote(7, 11)).unwrap());
        assert_eq!(a.usage_v1(), UsageV1 { work: 7, storage: 11, peak_storage: 11 });
        let retained = once.take().unwrap().dispatch_v1(|| {
            calls.set(calls.get()+1);
            assert_eq!(a.usage_v1().storage, 11);
            23
        });
        assert!(once.take().is_none());
        assert_eq!(calls.get(), 1);
        assert_eq!(retained.inspect_v1(), Some(&23));
        retained.destroy_owned_v1().unwrap().release_destroyed_v1();
        assert_eq!(a.usage_v1(), UsageV1 { work: 7, storage: 0, peak_storage: 11 });
        assert_eq!(refusal(a.reserve_whole_v1(quote(1, 1))), RefusalV1::InsufficientWork);
    }

    struct Resource<'a> {
        account: &'a TrustedHostAccountV1,
        sequence: &'a Cell<u64>,
        expected: u64,
        bytes_live: u64,
    }
    impl Drop for Resource<'_> {
        fn drop(&mut self) {
            assert_eq!(self.account.usage_v1().storage, self.bytes_live);
            assert_eq!(self.sequence.get(), self.expected);
            self.sequence.set(self.expected+1);
        }
    }

    #[test]
    fn original_refusal_output_and_diagnostic_owners_keep_storage_through_drop() {
        let a = account(20, 100);
        let sequence = Cell::new(0);
        let retained = a.reserve_whole_v1(quote(8, 70)).unwrap().dispatch_v1(|| {
            let make = |expected| Resource { account: &a, sequence: &sequence, expected, bytes_live: 70 };
            // Pure fake owners; these exercise retention, not genuine ingress.
            (make(0), Err::<Resource<'_>, _>(make(1)), make(2), make(3))
        });
        assert_eq!(sequence.get(), 0);
        assert_eq!(a.usage_v1().storage, 70);
        assert!(retained.inspect_v1().unwrap().1.is_err());
        let destroyed = retained.destroy_owned_v1().unwrap();
        assert_eq!(sequence.get(), 4);
        assert_eq!(a.usage_v1().storage, 70);
        destroyed.release_destroyed_v1();
        assert_eq!(a.usage_v1(), UsageV1 { work: 8, storage: 0, peak_storage: 70 });
    }

    #[test]
    fn releasing_one_owned_payload_does_not_release_another_live_result() {
        let a = account(20, 100);
        let one = a.reserve_whole_v1(quote(3, 30)).unwrap().dispatch_v1(|| 1);
        let two = a.reserve_whole_v1(quote(4, 50)).unwrap().dispatch_v1(|| 2);
        one.destroy_owned_v1().unwrap().release_destroyed_v1();
        assert_eq!(a.usage_v1(), UsageV1 { work: 7, storage: 50, peak_storage: 80 });
        assert_eq!(two.inspect_v1(), Some(&2));
        two.destroy_owned_v1().unwrap().release_destroyed_v1();
        assert_eq!(a.usage_v1(), UsageV1 { work: 7, storage: 0, peak_storage: 80 });
    }

    #[test]
    fn destroyed_token_releases_only_its_original_borrowed_account() {
        let one = account(20, 100);
        let two = account(20, 100);
        let first = one.reserve_whole_v1(quote(3, 30)).unwrap().dispatch_v1(|| 1);
        let second = two.reserve_whole_v1(quote(4, 50)).unwrap().dispatch_v1(|| 2);
        let destroyed = first.destroy_owned_v1().unwrap();
        assert_eq!(one.usage_v1().storage, 30);
        assert_eq!(two.usage_v1().storage, 50);
        destroyed.release_destroyed_v1();
        assert_eq!(one.usage_v1().storage, 0);
        assert_eq!(two.usage_v1().storage, 50);
        second.destroy_owned_v1().unwrap().release_destroyed_v1();
        assert_eq!(two.usage_v1().storage, 0);
    }

    #[test]
    fn callback_unwind_or_unused_ticket_never_refunds() {
        let a = account(20, 100);
        let r = a.reserve_whole_v1(quote(3, 20)).unwrap();
        let result = catch_unwind(AssertUnwindSafe(|| r.dispatch_v1(|| panic!("fake setup panic"))));
        assert!(result.is_err());
        drop(a.reserve_whole_v1(quote(4, 30)).unwrap());
        assert_eq!(a.usage_v1(), UsageV1 { work: 7, storage: 50, peak_storage: 50 });
    }

    #[test]
    fn ordinary_owner_drop_never_refunds_while_source_frame_is_live() {
        let a = account(20, 100);
        let owned = a.reserve_whole_v1(quote(3, 20)).unwrap().dispatch_v1(|| 1);
        drop(owned);
        assert_eq!(a.usage_v1(), UsageV1 { work: 3, storage: 20, peak_storage: 20 });
    }

    #[test]
    fn destructor_unwind_does_not_claim_storage_was_released() {
        struct Panics(Rc<Cell<bool>>);
        impl Drop for Panics { fn drop(&mut self) { self.0.set(true); panic!("fake destructor panic"); } }
        let a = account(20, 100);
        let ran = Rc::new(Cell::new(false));
        let retained = a.reserve_whole_v1(quote(5, 60)).unwrap().dispatch_v1(|| Panics(ran.clone()));
        let result = catch_unwind(AssertUnwindSafe(|| drop(retained)));
        assert!(result.is_err());
        assert!(ran.get());
        assert_eq!(a.usage_v1(), UsageV1 { work: 5, storage: 60, peak_storage: 60 });
    }
}
