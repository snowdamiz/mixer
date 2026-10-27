struct M { parameters: Vec<u8> }
const fn probe(m: &M)->[usize;2] {let c=|n:usize| n<=m.parameters.len();[std::mem::size_of_val(&c),std::mem::align_of_val(&c)]}
#[used] static B:fn(&M)->[usize;2]=probe;
