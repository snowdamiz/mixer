#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check<T:Sync>(){} fn bad(){check::<account::TrustedHostAccountV1>();}
fn main(){}
