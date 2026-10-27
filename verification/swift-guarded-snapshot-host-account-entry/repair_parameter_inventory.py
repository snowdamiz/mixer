#!/usr/bin/env python3
"""Final producer self-audit: recover FnOnce() parameters from retained MIR."""
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('entry_inventory',HERE/'run_inventory.py')
inventory=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)

def main():
    assert not (HERE/'seal.json').exists()
    raw=(HERE/'entry-and-account.mir').read_text()
    mir=json.loads((HERE/'mir-roles.json').read_text())
    measured=json.loads((HERE/'caller-inventory.json').read_text())
    sizes=measured['actual_type_sizes']
    concrete=measured['actual_compiler_anonymous_types']
    # Anonymous closure bytes are present in the original compiler print-type
    # output. Only the actual production FnOnce type is the generic substitute.
    closure=next(v for k,v in concrete.items() if '{closure@' in k)
    concrete['impl FnOnce() -> T']=closure
    before=measured['role_count']
    for fn,record,old in zip(inventory.functions(raw),mir['functions'],measured['functions'],strict=True):
        roles=inventory.role_inventory(fn)
        assert record['header']==old['header']==fn.split('\n',1)[0]
        record['roles']=roles
        for role in roles:
            ty=role['compiler_type']
            if ty in concrete:
                role.update(concrete_production_type=concrete[ty]['compiler_type'],
                            bytes=concrete[ty]['bytes'],size_status='actual-compiler-print-type-size')
            else:
                resolved=__import__('re').sub(r'\bT\b','OwnedFixtureOutcomeV1',ty)
                if resolved not in sizes:
                    aliases=[full for full in sizes if full.endswith('::'+resolved)]
                    assert len(aliases)==1,(resolved,aliases)
                    resolved=aliases[0]
                assert resolved in sizes,resolved
                role.update(concrete_production_type=resolved,bytes=sizes[resolved])
        old.update(roles=roles,role_count=len(roles),measured_logical_bytes=sum(r['bytes'] for r in roles),unmeasured_roles=0)
    # Parameter identities are unique within every function. In particular the
    # actual dispatch signature contributes its16-byte ticket and8-byte closure.
    dispatch=next(f for f in measured['functions'] if '::dispatch_v1(' in f['header'])
    parameters=[r for r in dispatch['roles'] if r['kind']=='parameter']
    assert [(r['local'],r['bytes']) for r in parameters]==[('_1',16),('_2',8)]
    measured['role_count']=sum(len(f['roles']) for f in measured['functions'])
    measured['measured_logical_bytes']=sum(f['measured_logical_bytes'] for f in measured['functions'])
    assert before==394 and measured['role_count']==396 and measured['measured_logical_bytes']==311071
    inventory.write('mir-roles.json',mir)
    inventory.write('caller-inventory.json',measured)
    inventory.write('parameter-repair.json',dict(schema=1,producer_audit=True,
          prior_roles=394,final_roles=396,prior_bytes=311047,final_bytes=311071,
          recovered_parameters=parameters,compiler_reinvoked=False,
          source_changed=False,complete_quote_or_grant_created=False))

if __name__=='__main__':main()
