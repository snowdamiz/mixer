fn probe(p: &mut ExecutionParts<'_, SwiftMode>) { let a=&mut *p.cache; let b=&mut *p.cache; std::hint::black_box((a,b)); }
