#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(t:account::DestroyedStorageV1<'_>,a:&account::TrustedHostAccountV1){t.release_destroyed_v1(a);}
fn main(){}
