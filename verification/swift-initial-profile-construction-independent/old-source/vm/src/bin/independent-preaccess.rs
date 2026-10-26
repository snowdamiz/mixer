fn main(){ let a:Vec<_>=std::env::args().collect(); assert_eq!(a.len(),3); mixer_vm::run_independent_preaccess(std::path::Path::new(&a[1]),std::path::Path::new(&a[2])); }
