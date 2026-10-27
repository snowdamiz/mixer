#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check()->account::TrustedHostAccountV1{account::TrustedHostAccountV1::from_preexisting_root_v1(panic!())}
fn main(){}
