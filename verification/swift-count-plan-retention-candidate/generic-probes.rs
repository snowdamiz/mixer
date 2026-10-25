#[test]
fn count_candidate_generic_exact_differential() {
    use super::borrowed::*;
    use std::mem::size_of;
    println!("GENERIC_LAYOUT {{\"cache\":{},\"slot\":{},\"parts\":{},\"fields\":{},\"meter\":{},\"scratch\":{},\"scan\":{},\"result\":{}}}",
        size_of::<FunctionCache>(),size_of::<Slot>(),size_of::<CacheParts<'static,FrozenMode>>(),
        size_of::<CacheFields<'static,FrozenMode>>(),size_of::<Meter<'static>>(),size_of::<()>(),
        size_of::<decode::Counts>(),size_of::<Result<decode::Counts,CacheFailure>>());
    let bytes=module(&[1,1,0x0b],Profile::IntegerV1);
    let mut c=cache(&bytes,Profile::IntegerV1);
    for n in 0..6 {
        let p=c.pin(0,&Cancellation::default()).unwrap();
        let v=c.view(&p).unwrap();
        println!("GENERIC_ACCESS {n} function={} locals={:?} instructions={:?} targets={:?}",v.function,v.locals,v.instructions,v.branch_targets);
        c.release(p).unwrap();
        println!("GENERIC_STATE {n} usage={:?} slots={:?} pins={:?}",c.usage(),c.slots.iter().map(|s|(s.entry.as_ref().map(|e|e.function),s.pins,s.last_used)).collect::<Vec<_>>(),c.pins.iter().map(|p|(p.entry,p.nonce)).collect::<Vec<_>>());
    }
    let mut c=cache(&bytes,Profile::IntegerV1);
    let start=c.usage.work_used;
    let p=c.pin(0,&Cancellation::default()).unwrap();c.release(p).unwrap();
    let amount=c.usage.work_used-start;
    for prefix in 0..amount {
        let mut c=cache(&bytes,Profile::IntegerV1);c.budget.work_credits=start+prefix;
        let e=c.pin(0,&Cancellation::default()).unwrap_err();
        println!("GENERIC_PREFIX {prefix} {e:?}");assert_eq!(c.usage.active_pins,0);
    }
    for cancelled in [false,true] {
        let mut c=cache(&bytes,Profile::IntegerV1);let cancel=Cancellation::default();
        if cancelled { cancel.cancel(); }
        match c.pin(0,&cancel) {
            Ok(p)=>{ c.release(p).unwrap();println!("GENERIC_CANCEL false {:?}",c.usage()); }
            Err(e)=>println!("GENERIC_CANCEL true {e:?}"),
        }
    }
}
