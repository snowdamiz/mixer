use mixer_vm::experimental::cache::{FunctionCache,FunctionPin};fn f(c:&mut FunctionCache,p:FunctionPin){let v=c.view(&p).unwrap();let _=c.release(p);let _=v.instructions.len();}
