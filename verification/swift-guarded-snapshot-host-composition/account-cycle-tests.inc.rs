
// Composition-only test support: small fake prices are never production prices.
#[cfg(test)]
pub(super) fn composition_synthetic_cycle_v1(
    action: impl FnOnce(&dyn Fn() -> (u64, u64, u64)), implicit_drop: bool,
) {
    let account = TrustedHostAccountV1::from_preexisting_root_v1(TrustedRootPolicyV1 {
        child_limits: CostV1 { work: 17, storage: 29 },
        p0_preexisting_allocation: CostV1 { work: 1, storage: 1 },
        source_and_review_binding: [0; 32],
    });
    let observe = || {
        let usage = account.usage_v1();
        (usage.work, usage.storage, usage.peak_storage)
    };
    assert_eq!(observe(), (0, 0, 0));
    let retained = account.reserve_whole_v1(ReviewedWholeQuoteV1 {
        total: CostV1 { work: 17, storage: 29 },
    }).unwrap().dispatch_v1(|| {
        assert_eq!(observe(), (17, 29, 29));
        action(&observe);
    });
    assert_eq!(observe(), (17, 29, 29));
    if implicit_drop {
        drop(retained);
        assert_eq!(observe(), (17, 29, 29));
    } else {
        let destroyed = retained.destroy_owned_v1().unwrap();
        assert_eq!(observe(), (17, 29, 29));
        destroyed.release_destroyed_v1();
        assert_eq!(observe(), (17, 0, 29));
    }
    match selected_whole_quote_v1() {
        Err(RefusalV1::WholeQuotePending) => (),
        _ => panic!("selected whole quote must remain pending"),
    }
    match selected_parent_account_v1() {
        Err(RefusalV1::RootPolicyPending) => (),
        _ => panic!("selected root policy must remain pending"),
    }
}
