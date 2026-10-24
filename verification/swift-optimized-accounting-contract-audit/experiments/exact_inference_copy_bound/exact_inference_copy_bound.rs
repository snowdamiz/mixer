use std::sync::{Arc,atomic::AtomicBool};
use std::mem::{size_of,align_of,size_of_val};
const fn bytes<T>(_: &T) -> usize { size_of::<T>() }
const fn alignment<T>(_: &T) -> usize { align_of::<T>() }
const ITEM_BYTES: usize = bytes(&Arc::<AtomicBool>::clone);
const ITEM_ALIGNMENT: usize = alignment(&Arc::<AtomicBool>::clone);
const fn factory(v: usize) -> impl Fn() -> usize + Copy { move || v }
const CLOSURE_BYTES: usize = bytes(&factory(7));
const CLOSURE_ALIGNMENT: usize = alignment(&factory(7));
fn main() {
 let f=Arc::<AtomicBool>::clone;
 let c=factory(7);
 println!("item {} {} {}", ITEM_BYTES, ITEM_ALIGNMENT, std::any::type_name_of_val(&f));
 println!("closure {} {} {}", CLOSURE_BYTES,CLOSURE_ALIGNMENT,std::any::type_name_of_val(&c));
 println!("public_alias {} {}",size_of::<Arc<AtomicBool>>(),size_of_val(&Arc::new(AtomicBool::new(false))));
 assert_eq!(ITEM_BYTES,0);
 assert_eq!(CLOSURE_BYTES,size_of_val(&c));
}
