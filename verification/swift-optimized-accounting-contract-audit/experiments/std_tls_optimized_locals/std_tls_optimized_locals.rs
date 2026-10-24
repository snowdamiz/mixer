use std::cell::Cell;
thread_local! { static VALUE: Cell<Option<usize>> = const { Cell::new(None) }; }
#[inline(never)] pub fn hook()->Option<usize>{VALUE.with(Cell::get)}
fn main(){assert_eq!(hook(),None);println!("tls hook executed");}
