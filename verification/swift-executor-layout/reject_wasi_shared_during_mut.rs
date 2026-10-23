fn probe(op: &mut SwiftExecutionOperation<'_>) { let a=&*op.wasi; let b=&mut *op.wasi; std::hint::black_box((a,b)); }
