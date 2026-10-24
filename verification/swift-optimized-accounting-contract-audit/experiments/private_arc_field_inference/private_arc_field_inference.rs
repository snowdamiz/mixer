use std::sync::{Arc,atomic::AtomicBool};
fn main(){let arc=Arc::new(AtomicBool::new(false));let private=arc.ptr; println!("{}",std::mem::size_of_val(&private));}
