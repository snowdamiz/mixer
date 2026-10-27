"""In-memory adversarial checks; all frozen bytes remain unchanged."""
import contextlib
import copy
import importlib.util
import io
import json
import struct
import sys

import audit as a

sys.dont_write_bytecode = True


def producer_module():
    # Used only to preserve comparative findings about the candidate checker.
    # No producer function contributes to independent custody/semantic results.
    sys.path.insert(0, str(a.C))
    spec = importlib.util.spec_from_file_location('frozen_producer_audit', a.C / 'audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


def main():
    result, inputs = a.main()
    ir, native, parsed = inputs['ir'], inputs['native'], inputs['parsed']
    controls = []
    failures = (AssertionError, ValueError, IndexError, KeyError, struct.error, StopIteration)
    def refuses(name, fn):
        try:
            fn()
        except failures as e:
            controls.append(dict(name=name, result='refused', exception=type(e).__name__))
            return
        raise AssertionError('independent review accepted mutation: ' + name)
    def modified_ir(name, old, new):
        assert ir[name]['body'].count(old) == 1, (name, old)
        f = copy.deepcopy(ir)
        f[name]['body'] = f[name]['body'].replace(old, new, 1)
        return f
    mutations = []
    for ty, size, align in a.TYPES:
        n = '<alloc::raw_vec::RawVec<' + ty + '> as core::ops::drop::Drop>::drop'
        for label, old, new in [('size', f'i64 {size})', f'i64 {size + 8})'),
                                ('alignment', f'i64 {align}, i64', f'i64 {align * 2}, i64')]:
            f = modified_ir(n, old, new)
            refuses(label + ':' + ty, lambda f=f: a.check_ir_semantics(f))
    pre = 'std::sys::fs::unix::debug_assert_fd_is_open'
    # Each decoy keeps the old spelling in a comment and alters only an active op.
    decoys = [
        ('fcntl-command-comment-decoy', pre,
         '%_2 = call i32 (i32, i32, ...) @fcntl(i32 %fd, i32 1) #36',
         '%_2 = call i32 (i32, i32, ...) @unreviewed_fcntl(i32 %fd, i32 2) #36'),
        ('EBADF-comment-decoy', pre, '%1 = icmp eq i32 %_3, 9', '%1 = icmp eq i32 %_3, 4'),
        ('abort-comment-decoy', pre,
         'call void @_RNvNtCs1SSuMAdGM58_3std7process5abort() #34',
         'call void @_RNvNtCs1SSuMAdGM58_3std7process5other() #34'),
        ('live-length-offset-comment-decoy', '<alloc::vec::Vec<' + a.SLOT + '> as core::ops::drop::Drop>::drop',
         '%1 = getelementptr inbounds i8, ptr %self, i64 16',
         '%1 = getelementptr inbounds i8, ptr %self, i64 0'),
        ('live-loop-exit-reversed', 'core::ptr::drop_glue::<[' + a.SLOT + ']>',
         'br i1 %_7, label %bb1, label %bb5', 'br i1 %_7, label %bb5, label %bb1'),
        ('unwind-loop-exit-reversed', 'core::ptr::drop_glue::<[' + a.SLOT + ']>',
         'br i1 %_5, label %bb2, label %bb3', 'br i1 %_5, label %bb3, label %bb2'),
    ]
    for label, name, old, new in decoys:
        f = modified_ir(name, old, '; retained evidence decoy: ' + old + '\n  ' + new)
        refuses(label, lambda f=f: a.check_ir_semantics(f))
        mutations.append((label, f))
    owned = '<std::os::fd::owned::OwnedFd as core::ops::drop::Drop>::drop'
    f = modified_ir(owned, '  ret void', '  %extra = call i32 @close(i32 %self2)\n  ret void')
    refuses('duplicate-close-request', lambda: a.check_ir_semantics(f))
    f = modified_ir(owned, '%_5 = call i32 @close(i32 %self2) #36',
                    '%_5 = call i32 @close(i32 0) #36')
    refuses('close-fd-substituted', lambda: a.check_ir_semantics(f))
    dec = native[a.DEALLOC]
    u8 = native[a.U8]
    mul = next(i for i in dec['instructions'] if i['word'] & 0xffe0fc00 == 0x9b007c00)
    branch = dec['relocations'][0]['instruction_address']
    def request(changed=None, relchanged=None, start=a.DEALLOC, size=136, align=8):
        got = a.rawvec_machine(parsed['gimli'], start, 7, size, align,
                               changed=changed, relchanged=relchanged)
        assert got['request'] == ([0x2000, 7, 1] if start == a.U8 else [0x2000, 952, 8])
    refuses('native-capacity-multiply-uses-alignment',
            lambda: request({mul['address']: (mul['word'] & ~(31 << 16)) | (1 << 16)}))
    refuses('native-multiply-removed', lambda: request({mul['address']: 0xd503201f}))
    refuses('native-request-pointer-from-capacity',
            lambda: request({mul['address'] + 4: 0xf9400000}))
    refuses('native-unknown-deallocation-relocation', lambda: request(relchanged={branch: '_unreviewed_allocator'}))
    refuses('native-u8-alignment-substituted',
            lambda: request({u8['address']: 0x52800041}, start=a.U8, size=999, align=999))
    refuses('native-u8-size-substituted',
            lambda: request({u8['address'] + 4: 0x52800042}, start=a.U8, size=999, align=999))
    osrow = next(r for n, r in native.items() if 'Read4read' in n and '4File' in n)
    tagidx = next(i for i, r in enumerate(osrow['instructions']) if r['word'] == 0x52800048)
    for label, change in [
        ('native-Os-tag-to-Custom', lambda r: r['instructions'][tagidx].update(word=0x52800028)),
        ('native-Os-shift-32-to-16', lambda r: r['instructions'][tagidx + 1].update(
            word=(r['instructions'][tagidx + 1]['word'] & ~(63 << 10)) | (16 << 10))),
        ('native-Os-errno-register-substituted', lambda r: r['instructions'][tagidx + 1].update(
            word=(r['instructions'][tagidx + 1]['word'] & ~(31 << 16)) | (21 << 16))),
        ('native-Os-orr-removed-with-annotation-retained', lambda r: r['instructions'][tagidx + 1].update(word=0xd503201f)),
    ]:
        row = copy.deepcopy(osrow)
        change(row)
        refuses(label, lambda row=row: a.os_constructor_words(row))
    refuses('archive-bad-magic', lambda: a.read_archive(b'bad ar!\n'))
    refuses('archive-truncated-record', lambda: a.read_archive(b'!<arch>\nshort'))
    refuses('object-truncated-load-commands', lambda: a.parse_object(parsed['std']['data'][:256]))
    data = bytearray(parsed['std']['data'])
    data[:4] = b'bad!'
    refuses('object-wrong-magic', lambda: a.parse_object(bytes(data)))
    refuses('object-address-outside-sections', lambda: a.bytes_at(parsed['std'], (1 << 64) - 1, 4))
    assert a.uncomment('  ; call void @fake()') == ''
    assert a.uncomment('call void @"name;kept"() ; ignored') == 'call void @"name;kept"()'
    producer = producer_module()
    observed_weaknesses = []
    for label, f in mutations:
        try:
            producer.check_ir(f)
        except failures:
            producer_result = 'refused'
        else:
            producer_result = 'accepted-at-semantic-helper-layer'
            observed_weaknesses.append(label)
        next(r for r in controls if r['name'] == label)['producer_helper_result'] = producer_result
    assert len(observed_weaknesses) == 6
    # The producer native helper's ORR assertion trusts the assembly annotation.
    # Its full outer object/hash custody would still reject changed frozen data.
    n = copy.deepcopy(native)
    target = next(r for k, r in n.items() if 'Read4read' in k and '4File' in k)
    i = next(i for i, r in enumerate(target['instructions']) if r['word'] == 0x52800048)
    target['instructions'][i + 1]['word'] = 0xd503201f
    producer_parsed = producer.native_inputs()
    producer.check_native_semantics(n, producer_parsed)
    observed_weaknesses.append('native-Os-orr-removed-with-annotation-retained')
    next(r for r in controls if r['name'] == observed_weaknesses[-1])['producer_helper_result'] = 'accepted-at-semantic-helper-layer'
    # Read-only replay of the producer baseline and original 24 controls.
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        p_result, _, _ = producer.main()
        spec = importlib.util.spec_from_file_location('frozen_producer_controls', a.C / 'test_controls.py')
        pc = importlib.util.module_from_spec(spec)
        # test_controls imports "audit"; bind that import only while loading it.
        prior = sys.modules.get('audit')
        sys.modules['audit'] = producer
        try:
            spec.loader.exec_module(pc)
            pc_result = pc.main()
        finally:
            sys.modules['audit'] = prior
    assert pc_result['hostile_controls'] == 24
    assert len(p_result['LLVM_functions']) == 29 and len(p_result['native_functions']) == 16
    assert p_result['native_byte_and_relocation_checks'] == 539
    return dict(schema=1, status='passed', independent_mutations=len(controls), controls=controls,
                preserved_producer_helper_coverage_findings=observed_weaknesses,
                finding_scope='Helper checks are incomplete in isolation; frozen whole-packet/object hash custody rejects data substitution. Independent checks reject all listed mutations.',
                producer_original_controls=pc_result, producer_replay_stdout=log.getvalue(),
                product_or_native_execution=False, frozen_input_writes=False,
                compiler_disassembler_subprocesses=0)


if __name__ == '__main__':
    result = main()
    if '--write' in sys.argv:
        (a.D / 'controls.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    else:
        assert result == a.load(a.D / 'controls.json')
    print(json.dumps(dict(status='passed', independent_mutations=result['independent_mutations'],
                          preserved_coverage_findings=len(result['preserved_producer_helper_coverage_findings']),
                          producer_original_controls=result['producer_original_controls']['hostile_controls'])))
