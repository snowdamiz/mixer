#![allow(dead_code)]
mod writer{include!("writer.rs");}
use writer::Writer;use std::fs::File;use std::mem::{size_of,align_of,offset_of};
fn main(){
 println!("Writer<File> size={} align={} File size={} align={}",size_of::<Writer<File>>(),align_of::<Writer<File>>(),size_of::<File>(),align_of::<File>());
 macro_rules! field{($name:ident)=>{println!("offset {} {}",stringify!($name),offset_of!(Writer<File>,$name));}}
 field!(buffer);field!(record);field!(stored);field!(attempted);field!(dropped);field!(used);field!(cap);field!(last_work);field!(last_instructions);field!(operation);field!(phase);field!(observed_mask);field!(expected_mask);field!(attempts);field!(code_count);field!(bindings);field!(pin_failed);field!(terminal_failed);field!(ended);field!(flags);field!(sink);
 println!("RefCell<Option<Writer>> size={} align={} Cell<u64> size={} align={} RefMut size={} BorrowResult size={}",size_of::<std::cell::RefCell<Option<Writer<File>>>>(),align_of::<std::cell::RefCell<Option<Writer<File>>>>(),size_of::<std::cell::Cell<u64>>(),align_of::<std::cell::Cell<u64>>(),size_of::<std::cell::RefMut<'static,Option<Writer<File>>>>(),size_of::<Result<std::cell::RefMut<'static,Option<Writer<File>>>,std::cell::BorrowMutError>>());
}
