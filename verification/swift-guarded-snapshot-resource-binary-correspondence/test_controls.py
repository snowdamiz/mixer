"""Executable hostile controls over retained LLVM and native object data; no tool runs."""
import copy
import json
import struct
import sys

import audit as a
from binary_format import archive_members, macho

class ControlSetupError(Exception):pass

def main(write=False):
    report,parsed,f=a.main();passed=[]
    def refuse(label,fn):
        try:fn()
        except (AssertionError,ValueError,IndexError,KeyError,struct.error):passed.append(dict(name=label,result='refused'));return
        raise AssertionError('Hostile control accepted: '+label)
    def mutated_ir(name,old,new):
        if name not in f or old not in f[name]['body']:raise ControlSetupError(name+' / '+old)
        altered=copy.deepcopy(f);altered[name]['body']=altered[name]['body'].replace(old,new,1);a.check_ir(altered)
    for ty,(size,align) in a.VECTORS.items():
        n='<alloc::raw_vec::RawVec<'+ty+'> as core::ops::drop::Drop>::drop'
        refuse('wrong-element-size:'+ty,lambda n=n,size=size:mutated_ir(n,f'i64 {size})',f'i64 {size+8})'))
        refuse('wrong-element-alignment:'+ty,lambda n=n,align=align:mutated_ir(n,f'i64 {align}, i64',f'i64 {align*2}, i64'))
    owned='<std::os::fd::owned::OwnedFd as core::ops::drop::Drop>::drop'
    refuse('duplicate-close-call',lambda:mutated_ir(owned,'  ret void','  %extra = call i32 @close(i32 %self2)\n  ret void'))
    refuse('missing-owned-fd-precheck',lambda:mutated_ir(owned,'; call std::sys::fs::unix::debug_assert_fd_is_open\n  call void','; call std::sys::fs::unix::debug_assert_fd_is_open\n  ; removed call void'))
    pre='std::sys::fs::unix::debug_assert_fd_is_open'
    refuse('wrong-fcntl-command',lambda:mutated_ir(pre,'i32 %fd, i32 1','i32 %fd, i32 2'))
    refuse('wrong-EBADF-comparison',lambda:mutated_ir(pre,'icmp eq i32 %_3, 9','icmp eq i32 %_3, 4'))
    refuse('missing-abort-edge',lambda:mutated_ir(pre,'std7process5abort','std7process5other'))
    ty='mixer_vm::experimental_swift_reactor::cache::SwiftSlot'
    refuse('wrong-SwiftSlot-live-len-offset',lambda:mutated_ir('<alloc::vec::Vec<'+ty+'> as core::ops::drop::Drop>::drop','i64 16','i64 0'))
    refuse('missing-SwiftSlot-nested-destruction',lambda:mutated_ir('core::ptr::drop_glue::<'+ty+'>','  call void','  ; removed call void'))
    # Native mutation controls evaluate the bytes, rather than a regenerated model.
    native=report['native_functions'];dec=native['_'+a.DEALLOC];u8=native['_'+a.RAWU8]
    address=u8['instructions'][0]['address']
    def expect_u8(**kwargs):
        got=a.eval_rawvec(parsed,'_'+a.RAWU8,7,999,999,**kwargs)
        assert got['request']==[0x2000,7,1]
    refuse('native-u8-wrong-alignment',lambda:expect_u8(changed_words={address:0x52800041})) # mov w1,#2
    refuse('native-u8-wrong-size',lambda:expect_u8(changed_words={address+4:0x52800042})) # mov w2,#2
    mul=next(i for i in dec['instructions'] if i['assembly'].startswith('mul\t'))
    def expect_size(**kwargs):
        assert a.eval_rawvec(parsed,'_'+a.DEALLOC,7,136,8,**kwargs)['request']==[0x2000,952,8]
    refuse('native-multiply-uses-alignment',lambda:expect_size(changed_words={mul['address']:(mul['word']&~(31<<16))|(1<<16)}))
    refuse('native-unknown-instruction-fails-closed',lambda:expect_size(changed_words={mul['address']:0xd503201f}))
    branch=dec['relocations'][0]['instruction_address']
    refuse('native-deallocator-relocation-substituted',lambda:expect_size(changed_relocations={branch:'_unreviewed_allocator'}))
    def wrong_close():
        n=copy.deepcopy(native);row=next(v for k,v in n.items() if 'drop_glue' in k and 'FileDesc' in k);row['relocations'][0]['target']='_fsync';a.check_native_semantics(n,parsed)
    refuse('native-close-relocation-substituted',wrong_close)
    def wrong_tag():
        n=copy.deepcopy(native);row=next(v for k,v in n.items() if 'Read4read' in k and '4File' in k)
        for i in row['instructions']:
            if i['word']==0x52800048:i['word']=0x52800028
        a.check_native_semantics(n,parsed)
    refuse('native-File-Os-tag-substituted-by-Custom',wrong_tag)
    def wrong_static():
        n=copy.deepcopy(parsed);row,obj,m=n['std'];data=bytearray(obj['data']);off=report['static_File_error']['message_object_offset'];data[off]=ord('X');obj['data']=bytes(data);a.static_error_data(n,native)
    refuse('native-static-error-message-bytes-substituted',wrong_static)
    refuse('truncated-MachO',lambda:macho(parsed['std'][1]['data'][:256]))
    refuse('invalid-archive-magic',lambda:archive_members(b'bad ar!\n'))
    refuse('malformed-counted-preimage',lambda:a.counted(struct.pack('<Q',1)+struct.pack('<Q',3)+b'xx'))
    result=dict(schema=1,status='passed',hostile_controls=len(passed),controls=passed,positive_rawvec_native_dataflow_cases=46,product_runtime=False,new_tool_or_compiler_processes=False)
    if write:a.put('controls.json',result)
    elif (a.D/'controls.json').exists():assert a.read('controls.json')==result
    print(json.dumps(dict(status='passed',hostile_controls=len(passed),positive_native_dataflow_cases=46,runtime=False)))
    return result

if __name__=='__main__':main('--write-report' in sys.argv)
