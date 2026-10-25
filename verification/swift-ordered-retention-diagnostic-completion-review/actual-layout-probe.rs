    #[test]
    fn independent_review_complete_owner_layouts(){
        use std::mem::size_of;
        println!("REVIEW_ACTUAL guard={} option_guard={} receipt={} option_receipt={} rows={} outcome={} outcome_return={} cleanup_return={} receipt_writer={} option_frame={}",
            size_of::<DispatchGuard>(),size_of::<Option<DispatchGuard>>(),size_of::<EndReceipt>(),size_of::<Option<EndReceipt>>(),size_of::<Rows>(),size_of::<Outcome>(),size_of::<(Outcome,Option<EndReceipt>)>(),size_of::<(SwiftRunUsage,Option<SwiftRunFailure>,Option<DispatchGuard>)>(),size_of::<ReceiptWriter>(),size_of::<Option<[u8;512]>>());
    }
