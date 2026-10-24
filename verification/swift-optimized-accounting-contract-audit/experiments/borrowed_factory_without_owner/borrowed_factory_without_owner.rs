use std::mem::{size_of,align_of};
#[allow(dead_code)] struct Roles<T>{source:T,argument:T,returned:T,caller:T}
fn factory(v:&mut usize)->impl FnMut()->usize+'_ {move||{*v+=1;*v}}
const fn return_roles<T>(_:fn(&'static mut usize)->T)->(usize,usize){(size_of::<Roles<T>>(),align_of::<Roles<T>>())}
const EXACT:(usize,usize)=return_roles(factory);
fn main(){println!("exact borrowed closure four roles {:?}; constructor never called",EXACT);assert_eq!(EXACT,(32,8));}
