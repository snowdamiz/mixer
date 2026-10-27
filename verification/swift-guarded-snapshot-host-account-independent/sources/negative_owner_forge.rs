#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check<'a>()->account::PrepaidOwnedV1<'a,u64>{account::PrepaidOwnedV1{owned:None,reservation:None}}
fn main(){}
