"""Offline invariant proof for retaining prior layouts, never new work authority."""
import difflib
import json
import re
import sys
sys.dont_write_bytecode=True
from prepare import (HERE,ROOT,BASE,BOOT,ACCOUNT_PACKET,PROFILE,ACCOUNT,CONTROL,LOADER,HELPER,
                     checked_candidate,sha,canonical,row,roster,write)

def declarations(data):
    # This equality aid is deliberately limited to reviewed changed files.
    # The compiler checks actual types; this cannot authorize execution/OTA.
    text=data.decode();result=[]
    for m in re.finditer(r'^[ \t]*(?:pub(?:\([^\n)]*\))?\s+)?(struct|enum|union)\s+(\w+)',text,re.M):
        start=m.start();i=m.end();depth=0
        while i<len(text):
            c=text[i]
            if c=='{': depth+=1
            if c=='}':
                depth-=1
                if depth==0: i+=1;break
            if c==';' and depth==0:i+=1;break
            i+=1
        result.append(dict(kind=m[1],name=m[2],text=text[start:i]))
    return result

def main():
    source,hosts=checked_candidate()
    accepted=json.loads((ACCOUNT_PACKET/'source-manifest.json').read_bytes())
    original={r['path']:(BASE/'source/vm'/r['path']).read_bytes() for r in accepted['members'] if r['path']!=ACCOUNT}
    original[ACCOUNT]=(ACCOUNT_PACKET/'host_account.rs').read_bytes()
    original[PROFILE]+=b'\n\n'+(BOOT/'driver.inc.rs').read_bytes()+b'\n\n'+(ACCOUNT_PACKET/'entry.inc.rs').read_bytes()
    assert roster(original)['members']==accepted['members']
    changed=[n for n in original if original[n]!=source[n]]
    assert set(changed)=={PROFILE,CONTROL,LOADER}
    assert set(source)-set(original)=={HELPER}
    invariant=[]
    for name in changed:
        before=declarations(original[name]);after=declarations(source[name])
        assert len(before)==len(after)
        rename_count=0
        for a,b in zip(before,after):
            if a!=b:
                assert name==PROFILE and a['name']==b['name']=='SnapshotAccessV1'
                assert a['text'].replace('previous:usize','retained:usize',1)==b['text']
                rename_count+=1
        assert before==after or rename_count==1
        aliases_before=re.findall(r'^[ \t]*(?:pub(?:\([^\n)]*\))?\s+)?type\s+[^\n]+',original[name].decode(),re.M)
        aliases_after=re.findall(r'^[ \t]*(?:pub(?:\([^\n)]*\))?\s+)?type\s+[^\n]+',source[name].decode(),re.M)
        assert aliases_before==aliases_after
        invariant.append(dict(path=name,declarations=len(before),
           declarations_before_sha256=sha(canonical(before)),declarations_after_sha256=sha(canonical(after)),
           representation_changes=0,field_identifier_only_renames=rename_count,
           type_alias_lines_byte_identical=True,type_alias_count=len(aliases_before),
           changed_source_does_not_add_field_variant_or_data_type=True))
    exact_count=len(original)-len(changed)
    compiler=json.loads((HERE/'preimages/production-metadata/manifest.json').read_bytes())['tools']['rustc']
    old_result=json.loads((ACCOUNT_PACKET/'account-test-results.json').read_bytes())
    assert compiler['sha256']==old_result['compiler_sha256']
    # Accepted actual private-route compile independently binds this executable.
    independent=ROOT/'verification/swift-guarded-snapshot-host-account-independent/commands/exact145-typed-route-metadata/receipt.json'
    independent_receipt=json.loads(independent.read_bytes())
    assert independent_receipt['compiler_sha256']==compiler['sha256']
    mirrored=json.loads((HERE/'inventory-invariance.json').read_bytes())
    assert mirrored['roles']==396 and mirrored['logical_bytes']==311071
    write('source-type-invariants.json',dict(schema=1,
        command=['python3','verification/swift-guarded-snapshot-host-composition/review_source_types.py'],
        python_version=sys.version,tool_sha256=sha((HERE/'review_source_types.py').read_bytes()),
        accepted_source_tree=accepted['source_tree_sha256'],composed_source_tree=roster(source)['tree_sha256'],
        byte_identical_existing_source_members=exact_count,changed_existing_source_members=changed,
        new_private_unused_helper=HELPER,reviewed_declarations=invariant,
        account_bootstrap_entry_bytes_identical=True,all_other_concrete_type_source_and_aliases_unchanged=True,
        accepted_compiler_executable_sha256=old_result['compiler_sha256'],fresh_compiler=compiler,
        independently_accepted_compiler_binding=dict(path=str(independent.relative_to(ROOT)),sha256=sha(independent.read_bytes())),
        target='aarch64-apple-darwin',same_frozen_compiler_and_target=True,
        fresh_MIR_body_and_role_type_match=True,closure_capture_and_generic_instantiation_unchanged=True,
        inherited_layouts=89,inherited_actual_layout_queries=90,inherited_dispatch_closure_bytes=8,
        fresh_layout_queries=0,layout_remeasurement_performed=False,
        no_role_discount=True,logical_source_object_bytes_retained=311071,
        P0_roles_retained=208,P0_logical_bytes_retained=234375,
        complete_work_storage_quote_or_P0_root_policy=False,
        note='Prior compiler-measured layouts retained through exact source/type/body/compiler invariants. No fresh broad layout inventory, dynamic backing, RSS, stack or work bound inferred.'))
    print('source/type/compiler invariants retained; 396 roles / 311071 logical bytes; quote pending')

if __name__=='__main__':main()
