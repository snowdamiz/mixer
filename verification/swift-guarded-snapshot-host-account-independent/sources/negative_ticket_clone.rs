#![allow(dead_code)]
#[path="frozen_host_account.rs"] mod account;
fn check(t:account::ReservationV1<'_>){let _=t.clone();}
fn main(){}
