use std::mem::{size_of,align_of};
fn never() -> ! { panic!("never executed") }
const fn return_size<T>(_: fn() -> T) -> usize { size_of::<T>() }
const fn return_align<T>(_: fn() -> T) -> usize { align_of::<T>() }
const N:usize=return_size(never);
const A:usize=return_align(never);
fn main(){println!("never {} {}",N,A);assert_eq!(N,0);}
