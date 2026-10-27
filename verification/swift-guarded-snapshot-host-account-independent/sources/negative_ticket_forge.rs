#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(a:&account::TrustedHostAccountV1)->account::ReservationV1<'_>{account::ReservationV1{account:a,storage:1}}
fn main(){}
