
    #[test]
    fn independent_review_publication_failure_preserves_result_and_no_publication() {
        let bytes=fixture(0,&[0,0x0b],100);
        let run=|enabled:bool| {
            let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());
            let mut guard=if enabled{Some(owned())}else{None};
            hooks(Hooks{pause:Some(CacheStep::Publication),cancel_pause:true,..Hooks::default()});
            let result=if let Some((ref mut g,_))=guard{g.dispatch(||pin(&mut cache,&mut c,34,None))}else{pin(&mut cache,&mut c,34,None)};hooks(Hooks::default());
            let failure=result.unwrap_err();assert_eq!(failure.kind,SwiftRunFailureKind::Cancelled);
            let actual=(failure.kind,failure.code,failure.at_failure.cache_work,c.usage(None).reservations,c.usage(None).live,cache.usage());
            if let Some((g,path))=guard {
                let receipt=terminal(g,&path,cache,c,Some(failure));assert_eq!(receipt.flags,0);
                let rows=read(&path);assert!(rows.iter().any(|r|r.0[1]==10));assert!(!rows.iter().any(|r|r.0[1]==11||r.0[1]==12));
                assert_eq!(rows.iter().filter(|r|r.0[1]==14).count(),2);
            }else{finish(cache,c);}
            actual
        };
        assert_eq!(run(false),run(true));println!("INDEPENDENT publication cancel: original result and complete ledgers equal, BuildReady present, no PinPublished/Release");
    }
    #[test]
    fn independent_review_release_failure_preserves_result_and_no_success_record() {
        let bytes=fixture(0,&[0,0x0b],100);
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let(mut g,path)=owned();
        let p=g.dispatch(||pin(&mut cache,&mut c,34,None)).unwrap();let stale=inspection::stale(&p);
        g.dispatch(||cache.release(p,&mut c,None)).map_err(|f|f.failure).unwrap();
        let before=cache.usage();let stored=ordered_observer::stored_for_fixture();let failure=g.dispatch(||cache.release(stale,&mut c,None)).err().unwrap();
        assert_eq!(failure.failure.kind,SwiftRunFailureKind::Invariant);assert_eq!(cache.usage(),before);assert_eq!(ordered_observer::stored_for_fixture(),stored);
        let original=failure.failure;drop(failure);let receipt=terminal(g,&path,cache,c,Some(original));assert_ne!(receipt.flags&CODE,0);
        println!("INDEPENDENT stale release: original code={} actual failure preserved, CODE invalid, no successful release after failed checked_record",original.code);
    }
    #[test]
    fn independent_review_inflight_end_never_touches_borrowed_writer_and_postend_refuses() {
        let (g,path)=owned();let initial=std::fs::read(&path).unwrap();assert_eq!(initial.len(),512);
        assert!(hold_entry_for_fixture());let mut receipt=None;
        with_borrowed(||{receipt=Some(g.end([0;64]));});
        let receipt=receipt.unwrap();assert!(!receipt.finalized);assert_eq!(receipt.attempts_before,0);assert_eq!(receipt.attempts_after,0);
        assert_eq!(std::fs::read(&path).unwrap(),initial);leave_for_fixture();
        let before=flags();assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));
        assert_eq!(flags(),before);assert_eq!(std::fs::read(&path).unwrap(),initial);retire_after_quiescence();
        println!("INDEPENDENT in-flight End under actual RefCell borrow: no panic/borrow/footer/write, closed callback refuses unchanged");
    }
    #[test]
    fn independent_review_wrongthread_sticky_is_independent_of_duplicate_begin() {
        let(g,path)=owned();std::thread::spawn(||{assert!(!observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));}).join().unwrap();
        assert_eq!(flags(),CONTEXT);assert!(observe([1,34,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0],(0,0)));assert_eq!(ordered_observer::stored_for_fixture(),0);
        let r=g.end([0;64]);assert!(r.finalized);assert_ne!(r.flags&CONTEXT,0);let bytes=std::fs::read(path).unwrap();assert_eq!(bytes.len(),1024);retire_after_quiescence();
        println!("INDEPENDENT wrong-thread only: isolated sticky context, later owner stores zero records");
    }
    #[test]
    fn independent_review_unknown_code_refuses_original_failure_without_replacement() {
        let bytes=fixture(0,&[0,0x0b],100);let(mut c,cache)=new(&bytes,SwiftRunBudget::default());let(g,path)=owned();
        let original=c.fail(cache_cursor(),Fault::new(SwiftRunFailureKind::Invariant,"independent_unrecognized_code"),None);
        let before=original;ordered_observer::failure(&original,true);assert_eq!(original,before);assert_ne!(flags()&CODE,0);
        let r=terminal(g,&path,cache,c,Some(original));assert_ne!(r.flags&CODE,0);assert_eq!(r.stored,0);
        println!("INDEPENDENT unknown source: exact full failure preserved, invalidity outside Result");
    }
