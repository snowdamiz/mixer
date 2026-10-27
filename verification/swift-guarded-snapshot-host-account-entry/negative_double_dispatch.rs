#![allow(dead_code)]
#[path = "host_account.rs"] mod host_account;
fn double_dispatch(ticket: host_account::ReservationV1<'_>) {
    let _first = ticket.dispatch_v1(|| 1);
    let _second = ticket.dispatch_v1(|| 2);
}
fn main() {}
