#!/usr/bin/env python3
"""Offline compiler evidence comparison; never invokes rustc or product code."""
import collections
import difflib
import gzip
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True
from prepare import HERE, INDEPENDENT, sha, write

INERT_NAMES=('outer_parent_layout_query_v1','outer_parent_account_layout_query_v1',
             'scoped_result_layout_query_v1','scoped_local_binding_compiles_v1')
LIFETIME_TYPES=('ReviewedFixtureBindingV1','FrozenFixtureV1','ImmutableIdentityPreimageV1',
                'ImmutableFixtureIdentitiesV1','PreexistingImmutableBindingV1','OneFixtureOuterRequestV1')

def blocks(text):
    # A MIR body's outer closing brace is in column zero. Inner scopes/blocks
    # are indented. Include const/static/anonymous const and allocation blocks.
    return re.findall(r'^[^\s/}][^\n]* \{\n.*?^\}',text,re.M|re.S)

def is_inert(block):
    header=block.split('\n',1)[0]
    return any(header.startswith('fn '+n+'(') or header.startswith(n+'::{constant#') for n in INERT_NAMES)

def strip_comment(line):
    # Remove rustc display comments only; preserve // inside string literals.
    quoted=False; escaped=False
    for i,c in enumerate(line):
        if escaped: escaped=False; continue
        if quoted and c=='\\': escaped=True; continue
        if c=='"': quoted=not quoted; continue
        if not quoted and line[i:i+2]=='//': return line[:i].rstrip()
    return line.rstrip()

def outside_strings(line, transform):
    # Preserve every literal exactly, including any literal allocNNN token.
    pieces=re.split(r'("(?:[^"\\]|\\.)*")',line)
    return ''.join(piece if index%2 else transform(piece) for index,piece in enumerate(pieces))

def normalize(block, allocation_map=None):
    block='\n'.join(strip_comment(line) for line in block.splitlines())
    # These two prefixes are compiler-owned scratch paths, not product data.
    for prefix in [str(INDEPENDENT/'owned-work/compiler-metadata-mir/vm'),str(HERE/'owned-work/positive/vm')]:
        block=block.replace(prefix,'<SOURCE>')
    # Only compiler-displayed impl/closure source coordinates. Do not remove
    # operation constants, calls, moves, drops, projections or arbitrary numbers.
    block=re.sub(r'(?<= at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+',r'<SOURCE>/\1:<SPAN>',block)
    def erase_display(text):
        for name in LIFETIME_TYPES:
            text=re.sub(r'\b'+name+r"(?:::)?<'_>",name,text)
        text=text.replace("selected_outer_request_v1::<'_>",'selected_outer_request_v1')
        if allocation_map:
            text=re.sub(r'\balloc\d+\b',lambda m:allocation_map.get(m.group(),m.group()),text)
        return text
    block='\n'.join(outside_strings(line,erase_display) for line in block.splitlines())
    return '\n'.join(line for line in block.splitlines() if line.strip())

def compare(before,after):
    before_blocks=[x for x in blocks(before) if not is_inert(x)]
    after_blocks=[x for x in blocks(after) if not is_inert(x)]
    old_alloc=[re.match(r'alloc\d+',x).group() for x in before_blocks if x.startswith('alloc')]
    new_alloc=[re.match(r'alloc\d+',x).group() for x in after_blocks if x.startswith('alloc')]
    assert len(old_alloc)==len(new_alloc)==1953
    allocation_map={}
    for old,new in zip(old_alloc,new_alloc):
        assert new not in allocation_map or allocation_map[new]==old
        allocation_map[new]=old
        assert int(new[5:])-int(old[5:])==4, (old,new)
    assert len(set(allocation_map.values()))==len(allocation_map)
    # A bijection derived from paired allocation headers is applied to actual
    # relocation references as well. All allocation size/alignment/bytes,
    # projections and operation bodies must then compare exactly.
    before=[normalize(x) for x in before_blocks]
    after=[normalize(x,allocation_map) for x in after_blocks]
    differences=[]
    for index,(a,b) in enumerate(zip(before,after)):
        if a!=b:
            differences.append(dict(index=index,before_header=a.split('\n',1)[0],after_header=b.split('\n',1)[0],
                before_sha256=sha(a.encode()),after_sha256=sha(b.encode()),
                diff=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True)))[:12000]))
    return dict(before_blocks=len(before),after_blocks=len(after),
        before_functions=sum(x.startswith('fn ') for x in before),
        after_functions=sum(x.startswith('fn ') for x in after),
        before_allocations=sum(x.startswith('alloc') for x in before),
        after_allocations=sum(x.startswith('alloc') for x in after),
        allocation_id_correspondence=dict(unique_ids=len(allocation_map),all_header_pairs_plus_4=True,bijection=allocation_map,
            validation='All 1953 ordered allocation blocks, including extent/alignment/raw bytes/relocation target structure, must compare exactly after this ID bijection; ordinal correspondence alone does not pass'),
        compared_exact_in_order=len(before)==len(after),differing_blocks=len(differences),differences=differences,
        before_normalized_sha256=sha('\n\n'.join(before).encode()),
        after_normalized_sha256=sha('\n\n'.join(after).encode()),
        equality=len(before)==len(after) and not differences)

def derive():
    frozen=INDEPENDENT/'commands/compiler-metadata-mir/query.mir.gz'
    accepted=frozen.read_bytes()
    assert sha(accepted)=='a4578f8057adbd11c5cccc2db439db80d8d7dc12adaa2cffcae16ef8c2d2d958'
    before=gzip.decompress(accepted)
    assert sha(before)=='822f8f178e71e7ff594158ae08123a2172c3d7f5ee930c6eeba9ce71b6b62ddf'
    candidate=(HERE/'commands/compiler-positive/query.mir.gz').read_bytes()
    after=gzip.decompress(candidate)
    report=compare(before.decode(),after.decode())
    report.update(schema=1,accepted_gzip_sha256=sha(accepted),accepted_raw_sha256=sha(before),
        candidate_gzip_sha256=sha(candidate),candidate_raw_sha256=sha(after),
        normalization='Exact scratch prefixes, rustc comments outside literals, displayed impl spans; only the six reviewed types and selected_outer_request_v1 added anonymous lifetime arguments; verified bijective allocation-ID renumbering (+4 in every paired header). Every operation, place, non-lifetime type, literal, allocation byte, size and alignment remains exact.',
        excluded_inert_query_names=list(INERT_NAMES),scope='All production MIR function, const/static, anonymous-constant and allocation blocks in sequence; compiler-only, not runtime qualification')
    old=json.loads((INDEPENDENT/'commands/compiler-metadata-mir/layouts.json').read_bytes())['rows']
    tails=[('query-layout.inc.rs','outer_parent_layout_query_v1'),('query-account-layout.inc.rs','outer_parent_account_layout_query_v1'),('query-result-layout.inc.rs','scoped_result_layout_query_v1')]
    rows=[]
    for file_name,fn_name in tails:
        decl=(HERE/file_name).read_text()
        names=re.findall(r'\s+_(\w+): \[u8;',decl)
        headers=[x.split('\n',1)[0] for x in blocks(after.decode()) if x.startswith('fn '+fn_name+'(')]
        assert len(headers)==1
        values=[int(n) for n in re.findall(r'_\d+: \[u8; (\d+)\]',headers[0])]
        assert len(names)==len(values)
        rows += [dict(query=n,observed=v) for n,v in zip(names,values)]
    assert len(rows)==46
    layout=dict(schema=1,rows=rows,accepted_44=old,first_44_identical=rows[:44]==old,
        result_two_expected=[dict(query='selection_result_size',observed=8),dict(query='selection_result_align',observed=8)],
        result_two_match=rows[44:]==[dict(query='selection_result_size',observed=8),dict(query='selection_result_align',observed=8)],
        scope='Exact aarch64-apple-darwin compiler inline layouts only; dynamic/native backing not priced')
    stderr=(HERE/'commands/compiler-negative/stderr').read_text()
    codes=re.findall(r'^error\[(E\d+)\]:',stderr,re.M)
    expected=['E0515','E0515','E0506','E0505','E0382']
    negative=dict(schema=1,actual_codes=codes,expected_codes=expected,exact_order_and_count_match=codes==expected,
        source_tail_sha256=sha((HERE/'negative.inc.rs').read_bytes()),stderr_sha256=sha(stderr.encode()),
        probes=[dict(name=n,error=e) for n,e in zip(['reject_escaping_request_v1','reject_stack_identity_static_v1','reject_mutation_live_identity_v1','reject_drop_live_identity_v1','reject_double_consume_request_v1'],expected)],
        scope='Compiler-only production metadata rejection; no test cfg, binary/codegen or runtime')
    return report,layout,negative

def main():
    assert sys.argv[1:]==['--derive']
    report,layout,negative=derive()
    write(HERE/'mir-comparison.json',report);write(HERE/'layouts.json',layout);write(HERE/'negative-results.json',negative)
    print(json.dumps(dict(mir_equal=report['equality'],production_functions=report['before_functions'],blocks=report['before_blocks'],differing_blocks=report['differing_blocks'],layouts_44_equal=layout['first_44_identical'],result_layout_8_8=layout['result_two_match'],negative_codes_exact=negative['exact_order_and_count_match'])))
    if not (report['equality'] and layout['first_44_identical'] and layout['result_two_match'] and negative['exact_order_and_count_match']): sys.exit(1)

if __name__=='__main__': main()
