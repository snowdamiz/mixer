#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(t:account::DestroyedStorageV1<'_>){t.release_destroyed_v1();t.release_destroyed_v1();}
fn main(){}
