from pathlib import Path
import json,hashlib
b=Path(__file__).parent
# Preserve every original two-member source preimage for already executed work.
changed=['vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs']
for cmd in ['toolchain','production','build-debug','run-debug']:
 out=b/'commands'/cmd
 for name in changed:
  p=b/'source'/name;dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
  manifest=json.loads((out/'source-manifest.json').read_text())['members'];expected=next(r for r in manifest if r['path']==name);assert hashlib.sha256(dest.read_bytes()).hexdigest()==expected['sha256']
p=b/'source/vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs';s=p.read_text()
s=s.replace('build[88..107].copy_from_slice(b"aarch64-apple-darwin")','build[88..108].copy_from_slice(b"aarch64-apple-darwin")')
s=s.replace('interruptions:u32, chunk:usize, overreported:bool, error:Option<i32>,','interruptions:u32, eof_interruptions:u32, chunk:usize, overreported:bool, error:Option<i32>, fail_after:Option<usize>,')
s=s.replace('''                if let Some(code)=r.error.take() { return Err(io::Error::from_raw_os_error(code)); }''','''                if r.position>=r.identity.bytes as usize && r.eof_interruptions>0 {r.eof_interruptions-=1;return Err(io::Error::from(io::ErrorKind::Interrupted));}
                if r.fail_after.is_none_or(|at|r.position>=at) {if let Some(code)=r.error.take() { return Err(io::Error::from_raw_os_error(code)); }}''')
s=s.replace('position:0,interruptions:0,chunk:usize::MAX,overreported:false,error:None,meta_fail:false','position:0,interruptions:0,eof_interruptions:0,chunk:usize::MAX,overreported:false,error:None,fail_after:None,meta_fail:false')
s=s.replace('''            let(result,_,_)=read_case(3,|r|r.chunk=1);assert!(result.is_ok());''','''            let(result,_,_)=read_case(3,|r|r.chunk=1);assert!(result.is_ok());
            let(result,_,trace)=read_case(1,|r|r.eof_interruptions=31);assert!(result.is_ok());assert_eq!(trace.read_calls.get(),33);
            let(result,_,trace)=read_case(1,|r|r.eof_interruptions=32);assert_eq!(result.err().unwrap().kind,BootstrapFailureV1::Attempts);assert_eq!(trace.read_calls.get(),33);
            let(result,file,_)=read_case(3,|r|{r.chunk=1;r.error=Some(919);r.fail_after=Some(1);});
            let e=result.err().unwrap();assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(919));assert_eq!(file.body.as_ref().unwrap().initialized,1);''')
s=s.replace('''let mut owner=acquired(&r,&trace);if work {owner.reservation.operation_left=30;}else{owner.reservation.storage_left=42;}''','''let mut owner=acquired(&r,&trace);if work {
                    let actual=owner.actual.as_ref().unwrap();let final_work=(0..13).map(|i|body_v1(actual,i).unwrap().len() as u64).sum::<u64>()+13
                        +body_v1(actual,1).unwrap().len() as u64+body_v1(actual,2).unwrap().len() as u64+64;
                    owner.reservation.operation_left=final_work+30;
                }else{owner.reservation.storage_left=42;}''')
s=s.replace('''assert!(held.actual.as_ref().unwrap().partial.original.is_some());assert!(trace.drops.borrow().is_empty());}''','''assert_eq!(held.actual.as_ref().unwrap().partial.original.as_ref().unwrap().slot,13);assert!(trace.drops.borrow().is_empty());}''')
s=s.replace('''            let _original_claims=&owner.actual.as_ref().unwrap().claims;''','''            owner.actual.as_ref().unwrap().claims.test_prepaid_actual_owner_assert_eight_v1();''')
p.write_text(s)
p=b/'source/vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs';s=p.read_text();s=s.replace('''    pub(in crate::experimental_swift_reactor) fn test_prepaid_actual_owner_fixed_claims_v1() -> Self {''','''    pub(in crate::experimental_swift_reactor) fn test_prepaid_actual_owner_assert_eight_v1(&self) {
        assert_eq!([self.baseline,self.candidate,self.original_input,self.event_schema,self.profile_adapter_binary,
            self.layout_receipt,self.original_validated_snapshot,self.profile_row_body],
            [[1;32],[2;32],[3;32],[4;32],[5;32],[6;32],[7;32],[8;32]]);
    }
    pub(in crate::experimental_swift_reactor) fn test_prepaid_actual_owner_fixed_claims_v1() -> Self {''')
a=s.index('        #[test]\n        fn selected_outer_binding_remains_pending()')
s=s[:a]+'''        #[test]
        fn prepaid_actual_owner_v1_h01_all_three_original_selectors_remain_pending() {
            assert!(matches!(selected_outer_request_v1(),Err(BindingSelectionRefusalV1::ImmutableBindingAndP0ReviewPending)));
            assert!(matches!(host_account_v1::selected_parent_account_v1(),Err(RefusalV1::RootPolicyPending)));
            assert!(matches!(host_account_v1::selected_whole_quote_v1(),Err(RefusalV1::WholeQuotePending)));
        }
''' +s[a:];p.write_text(s)
# runner accepts one targeted Debug repair build/run and exact-source production
# recompile after the documented test-source correction.
p=b/'run_bounded.py';s=p.read_text()
s=s.replace("(out/'runner.py').write_bytes(Path(__file__).read_bytes())","""(out/'runner.py').write_bytes(Path(__file__).read_bytes())
 for name in ['vm/src/experimental_swift_reactor/cache/initial_profile_v1.rs','vm/src/experimental_swift_reactor/retained_profile_loader_v1.rs']:
  dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source/name).read_bytes())""")
s=s.replace("elif label=='production':","elif label in ('production','production-repair1'):")
s=s.replace("elif label in ('build-debug','build-opt'):","elif label in ('build-debug','build-opt','build-debug-repair1'):")
s=s.replace("mode='debug' if label=='build-debug' else 'opt'","mode='debug' if label.startswith('build-debug') else 'opt'")
s=s.replace("elif label in ('run-debug','run-opt'):","elif label in ('run-debug','run-opt','run-debug-repair1'):")
p.write_text(s)
