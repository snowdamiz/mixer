#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(o:account::PrepaidOwnedV1<'_,u64>){let _=o.clone();}
fn main(){}
