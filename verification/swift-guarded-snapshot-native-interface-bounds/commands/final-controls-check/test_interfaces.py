"""Meaningful pure controls; synthetic bytes are never actual root inputs."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
from model import *
HERE=Path(__file__).resolve().parent
CONTRACT=json.loads((HERE/'contract.json').read_text())

class Interfaces(unittest.TestCase):
    checks=0
    def eq(self,a,b):
        type(self).checks+=1;self.assertEqual(a,b)
    def refuses(self,f,*args):
        type(self).checks+=1
        with self.assertRaises((Refused,TypeError)):f(*args)
    def path(self,n,backing=None):return PathExtent(n,n if backing is None else backing,'synthetic-control-only')

    def test_boundary_cases_and_raw_unix_bytes(self):
        for n in [0,1,2,31,255,382,383,384,385,4095,4096,4097,8193,100000]:
            for nul in [False,True]:
                raw=b'x'*n
                if nul:
                    if not n:continue
                    raw=raw[:n//2]+b'\0'+raw[n//2+1:]
                c=path_case(raw);b=path_bounds(self.path(n),CONTRACT)
                self.eq(c['encoded_bytes'],n)
                self.eq(c['semantic_open_requests'],int(not nul))
                self.eq(c['allocation_before_nul_validation'],n>=384)
                self.eq(c['heap_request_bytes'],n+1 if n>=384 else 0)
                self.eq(b['extra_requested_heap_bytes_max'],c['heap_request_bytes'])
                self.eq(b['positive_conversion_interface_envelope'],max(384,n+1))
                self.eq(b['native_path_span'],n+1)
                self.eq(c['retained_error_heap_bytes'],0)
        for raw in [b'\xff',b'/\x80\xfe',b'\xff'*384,b'\xff\0\xfe',b'\0',b'']:
            c=path_case(raw)
            self.eq(c['utf8_required'],False)
            self.eq(c['semantic_open_requests'],int(b'\0' not in raw))
        self.eq(path_case(b'')['empty_path_native_result'],'OS-decides')
        self.refuses(path_case,'UTF8 string is not actual encoded bytes')

    def test_open_formula_independent_per_byte_enumeration(self):
        # Independently enumerate full declared payload accesses for small n.
        # Seven native extents: read/copy source+destination, validation,
        # request, public open path, and two alternative disposal requests.
        for n in list(range(90))+[383,384,385,4096,4097]:
            native=751+sum(1 for _ in range(n) for _ in range(7))
            b=path_bounds(self.path(n),CONTRACT)
            self.eq(b['native_operand_and_request_bytes'],native)
            self.eq(b['price'],768+7*n)
            self.eq(b['semantic_open_requests_max'],1)
            self.eq(b['finite_private_open_syscall_attempt_bound'],False)
        for n in [10**5,10**6,2**31]:
            self.eq(path_bounds(self.path(n),CONTRACT)['price'],768+7*n)
        self.eq(records_price(CONTRACT['error_records'])['price'],23)

    def test_prefix_refusal_and_options(self):
        self.eq(CONTRACT['setup_options'],['read-only']*3+['write-create_new']*2)
        self.eq(CONTRACT['setup_roles'],['input','build','session','rows','snapshot'])
        self.eq(CONTRACT['setup_truncate'],False)
        self.eq(CONTRACT['executable_open_separate'],True)
        # Each ordinary Err terminates the five-attempt loop and retains all
        # earlier actual Files. The failed attempt owns no returned File.
        for failed_stage in range(5):
            requests=list(range(failed_stage+1));retained=list(range(failed_stage))
            self.eq(len(requests),failed_stage+1)
            self.eq(len(retained),failed_stage)
            self.eq(all(r<failed_stage for r in retained),True)
        # All five successful setup owners coexist; executable sixth is loader.
        self.eq(len(CONTRACT['setup_roles'])+int(CONTRACT['executable_open_separate']),6)

    def test_required_p0_extents_and_empty_path(self):
        paths=tuple(self.path(n,n+9) for n in [0,3,384,4097,9000])
        p=(Pointee('compiled diagnostic',9,9,'synthetic compiled-string binding'),
           Pointee('immutable identity',32,64,'synthetic identity-binding'))
        r=p0_bounds(paths,512,p)
        self.eq(r['path_p0_backing_bytes'],sum(x.p0_backing_bytes for x in paths))
        self.eq(r['identity_diagnostic_pointee_backing_bytes'],73)
        self.eq(r['reviewed_binding_object_bytes'],512)
        self.eq(path_bounds(self.path(0,0),CONTRACT)['p0_backing_bytes'],0)
        for n in [0,1,2,3,4,6]:self.refuses(p0_bounds,paths[:n] if n<5 else paths+(paths[0],),512,p)
        self.refuses(p0_bounds,paths,511,p)
        self.refuses(p0_bounds,paths,512,())
        self.refuses(p0_bounds,paths,512,(p[0],p[0]))
        self.refuses(p0_bounds,paths,512,(Pointee('bad',10,9,'bound'),))
        self.refuses(p0_bounds,paths,512,(Pointee('missing evidence',1,1,''),))
        self.refuses(path_bounds,self.path(10,9),CONTRACT)

    def test_full_entry_equation_and_monotonicity(self):
        paths=tuple(self.path(n) for n in [1,383,384,4097,8193])
        d=1210256815
        r=child_entry(paths,CONTRACT,d)
        self.eq(r['entry_price'],64143735004+7*sum(p.encoded_bytes for p in paths))
        self.eq(r['entry_destructor_visits'],53)
        self.eq(r['whole_host_grant'],False)
        for i in range(5):
            more=list(paths);more[i]=self.path(paths[i].encoded_bytes+123)
            self.eq(child_entry(tuple(more),CONTRACT,d)['entry_price']-r['entry_price'],7*123)
        self.eq(child_entry(paths,CONTRACT,d+1)['entry_price']-r['entry_price'],53)
        for d0 in [0,-1,True,None,'unknown',U64]:self.refuses(child_entry,paths,CONTRACT,d0)
        self.refuses(child_entry,paths[:4],CONTRACT,d)
        self.refuses(child_entry,list(paths),CONTRACT,d)
        self.refuses(child_entry,paths,CONTRACT)

    def test_source_closed_no_extra_allocations(self):
        details=json.loads((HERE/'interface-derivation.json').read_text())
        amendment=json.loads((HERE/'storage-interface-amendment.json').read_text())
        for row in details['payload_drop_rows']:
            z=closed_extra_requests('source146-owned-file-route',row['resource_frontiers'])
            self.eq(z['extra_requested_heap_bytes'],0)
            self.eq(row['owned_backing_deallocated_not_allocated'],True)
            self.eq(row['extra_requested_heap_bytes'],0)
            self.eq(row['native_interface_operand_union_bytes']<=29394,True)
        self.eq(len(details['payload_drop_rows']),33)
        self.eq(details['stat_bytes'],144)
        self.eq(details['File_bytes'],4)
        self.eq(details['Error_bytes'],8)
        self.eq(details['errno_c_int_bytes'],4)
        self.eq(amendment['file_resource_backing_each'],73)
        self.eq(amendment['error_backing_each'],32)
        self.eq(amendment['loader_native_temporaries'],8572)
        self.eq(amendment['all_payload_destructor_temporaries'],29394)
        self.eq(amendment['exact_extra_requested_heap_bytes_for_each_of_those_four_interfaces'],0)
        c=amendment['error_count_derivation']
        self.eq(c['complete_fixed_inline_plus_retention_bytes'],3175386)
        self.eq(amendment['error_owner_count'],3175386//8+1)
        # All possible disjoint eight-byte Errors fit this bound; count does not
        # depend on the53 work visits or a single aggregate result field.
        self.eq(amendment['error_owner_count']*8>c['complete_fixed_inline_plus_retention_bytes'],True)
        self.refuses(closed_extra_requests,'custom-Error',{'Error':1})
        for unknown in ['Vec<CustomDrop>','Error<callback>','Arc<Foreign>','Box<Callback>']:
            self.refuses(closed_extra_requests,'source146-owned-file-route',{unknown:1})

    def test_reject_bad_unknown_overflow_and_mutation(self):
        for bad in [True,False,-1,U64+1,None,1.0,'1']:
            self.refuses(path_bounds,self.path(bad),CONTRACT)
        self.refuses(path_bounds,PathExtent(1,1,''),CONTRACT)
        self.refuses(path_bounds,self.path(ISIZE_MAX),CONTRACT)
        self.refuses(path_bounds,self.path(ISIZE_MAX-1),CONTRACT)
        self.refuses(add,U64,1);self.refuses(mul,U64,2)
        for field,value in [('setup_truncate',True),('path_branch_threshold',4096),('closed_error_owned_backing_bytes',1)]:
            c=copy.deepcopy(CONTRACT);c[field]=value
            self.refuses(path_bounds,self.path(5),c)
        c=copy.deepcopy(CONTRACT);c['open_records'][0]['fixed_bytes']-=1
        self.refuses(path_bounds,self.path(5),c)
        self.refuses(path_bounds,{},CONTRACT)
        self.refuses(records_price,[{'event':'unknown','fixed_bytes':1,'path_byte_multiplicity':0,'extra':1}])

def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Interfaces))
    output={'schema':1,'methods':result.testsRun,'assertions':Interfaces.checks,'all_passed':result.wasSuccessful(),
      'synthetic_data_only':True,'actual_native_or_root_execution':False}
    if '--check-only' in sys.argv:
        assert json.loads((HERE/'controls.json').read_text())==output
    else:(HERE/'controls.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(json.dumps(output,sort_keys=True));raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
