#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(o:&account::PrepaidOwnedV1<'_,Vec<u8>>){o.inspect_v1().unwrap().push(1);}
fn main(){}
