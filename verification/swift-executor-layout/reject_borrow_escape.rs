fn probe(p: &mut ExecutionOperationPhase<'_>) -> &'static mut RuntimeControl { with_cache_operation(p,|_,o| o.control) }
