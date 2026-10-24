use std::mem::{size_of,align_of};
#[allow(dead_code)] struct Roles<T> { source:T,argument:T,returned:T,caller:T }
const fn roles_of_value<T:Copy>(_:T)->(usize,usize) { (size_of::<Roles<T>>(),align_of::<Roles<T>>()) }
const fn roles_of_return<T>(_:fn()->T)->(usize,usize){ (size_of::<Roles<T>>(),align_of::<Roles<T>>()) }
fn never()->!{panic!("never executed")}
const NEVER:(usize,usize)=roles_of_return(never);
const ITEM:(usize,usize)=roles_of_value(never);
const fn factory(v:usize)->impl Fn()->usize+Copy{move||v}
const CLOSURE:(usize,usize)=roles_of_value(factory(7));
fn main(){println!("exact four typed roles never {:?} item {:?} closure {:?}",NEVER,ITEM,CLOSURE);assert_eq!(NEVER,(0,1));assert_eq!(ITEM,(0,1));assert_eq!(CLOSURE,(32,8));}
