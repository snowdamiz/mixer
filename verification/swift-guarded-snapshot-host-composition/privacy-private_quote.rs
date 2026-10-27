#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn fake() -> host_account::ReviewedWholeQuoteV1 { host_account::ReviewedWholeQuoteV1 { total: panic!() } }
