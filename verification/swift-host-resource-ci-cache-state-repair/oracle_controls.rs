
// Repair-lane controls only. Not part of the proposed frozen fixture change.
mod fixture_repair_oracle {
    use super::*;
    use std::path::Path;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::OnceLock;

    struct Row { label: String, context: Vec<u8> }
    struct Oracle { stream: Vec<u8>, profile: Vec<u8>, context: Vec<u8>, rows: Vec<Row> }
    static ORACLE: OnceLock<Oracle> = OnceLock::new();
    static CHECKED: AtomicUsize = AtomicUsize::new(0);
    static FRESH: AtomicUsize = AtomicUsize::new(0);
    static COMPLETED: AtomicUsize = AtomicUsize::new(0);

    fn oracle() -> &'static Oracle {
        ORACLE.get_or_init(|| {
            let root=PathBuf::from(std::env::var_os("MIXER_REPAIR_ORACLE").expect("independent oracle required"));
            let raw=fs::read(root.join("cases.bin")).unwrap();
            let mut position=0;
            let mut rows=Vec::new();
            while position<raw.len() {
                let label_len=u32::from_le_bytes(raw[position..position+4].try_into().unwrap()) as usize;
                let context_len=u32::from_le_bytes(raw[position+4..position+8].try_into().unwrap()) as usize;
                position+=8;
                let label=String::from_utf8(raw[position..position+label_len].to_vec()).unwrap();
                position+=label_len;
                let context=raw[position..position+context_len].to_vec();
                position+=context_len;
                rows.push(Row{label,context});
            }
            assert_eq!(position,raw.len());
            assert_eq!(rows.len(),1003);
            Oracle {stream:fs::read(root.join("stream.bin")).unwrap(),profile:fs::read(root.join("profile.bin")).unwrap(),
                    context:fs::read(root.join("context.bin")).unwrap(),rows}
        })
    }

    fn matches(f:&Fixture,framing:bool,label:&str,row:&Row) -> bool {
        let oracle=oracle();
        !framing && label==row.label && f.stream==oracle.stream && f.profile==oracle.profile && f.context==row.context
    }

    pub(super) fn check(f:&Fixture,framing:bool,label:&str) {
        let index=CHECKED.fetch_add(1,Ordering::SeqCst);
        assert!(matches(f,framing,label,&oracle().rows[index]),"independent exact input differs at {index}: {label}");
    }

    pub(super) fn fresh(stream:&mut File,profile:&mut File,context:&mut File,output:&mut File) {
        for file in [stream,profile,context,&mut *output] {assert_eq!(file.stream_position().unwrap(),0);}
        assert_eq!(output.metadata().unwrap().len(),0);
        FRESH.fetch_add(1,Ordering::SeqCst);
    }

    pub(super) fn completed(path:&Path) {
        assert!(!path.exists(),"original case scratch cleanup incomplete");
        let count=COMPLETED.fetch_add(1,Ordering::SeqCst)+1;
        if count==1003 {
            assert_eq!(CHECKED.load(Ordering::SeqCst),1003);
            assert_eq!(FRESH.load(Ordering::SeqCst),1003);
            println!("REPAIR_ORACLE exact_input_cases=1003 fresh_file_cases=1003 completed_case_cleanups=1003");
        }
    }

    #[test]
    fn altered_input_label_and_framing_negative_controls() {
        let baseline=Fixture::new();
        let oracle=oracle();
        assert_eq!(baseline.stream,oracle.stream);assert_eq!(baseline.profile,oracle.profile);assert_eq!(baseline.context,oracle.context);
        let mut candidate=baseline.clone();
        assert_ne!(candidate.stream.as_ptr(),baseline.stream.as_ptr());
        assert_ne!(candidate.profile.as_ptr(),baseline.profile.as_ptr());
        assert_ne!(candidate.context.as_ptr(),baseline.context.as_ptr());
        let row=&oracle.rows[0];
        candidate.context(1,2);
        assert!(matches(&candidate,false,&row.label,row));
        assert!(!matches(&candidate,true,&row.label,row));
        assert!(!matches(&candidate,false,"different-label",row));
        assert!(!matches(&candidate,false,&oracle.rows[1].label,&oracle.rows[1]));
        for index in [0,candidate.stream.len()-1] {
            candidate.stream[index]^=1;assert!(!matches(&candidate,false,&row.label,row));candidate.stream[index]^=1;
        }
        for index in [0,512,candidate.profile.len()-1] {
            candidate.profile[index]^=1;assert!(!matches(&candidate,false,&row.label,row));candidate.profile[index]^=1;
        }
        for index in [0,8,candidate.context.len()-1] {
            candidate.context[index]^=1;assert!(!matches(&candidate,false,&row.label,row));candidate.context[index]^=1;
        }
        candidate.context.pop();assert!(!matches(&candidate,false,&row.label,row));
        candidate.context.push(0);candidate.profile.pop();assert!(!matches(&candidate,false,&row.label,row));
        assert_eq!(baseline.stream,oracle.stream);assert_eq!(baseline.profile,oracle.profile);assert_eq!(baseline.context,oracle.context);
        println!("REPAIR_ORACLE negative_controls=changed-stream,changed-profile,changed-context,truncated-context,truncated-profile,wrong-label,wrong-order,wrong-framing clone_allocations=independent");
    }
}
