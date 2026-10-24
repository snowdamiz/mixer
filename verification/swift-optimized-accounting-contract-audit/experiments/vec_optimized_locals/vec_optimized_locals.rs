#[inline(never)] pub fn first(v:&[u32])->Option<&u32>{v.first()}
fn main(){assert_eq!(first(&[7]),Some(&7));}
