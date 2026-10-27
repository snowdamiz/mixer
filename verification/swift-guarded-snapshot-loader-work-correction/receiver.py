"""Exact supported PartialEq receiver shapes for the frozen219 MIR definitions.

This resolves authored callbacks, not semantic equality or generic verifier
permission. New/ambiguous receiver or RHS shapes fail closed.
"""
from dataclasses import dataclass
import re

class UnsupportedReceiver(ValueError): pass

@dataclass(frozen=True)
class EqualityDispatch:
    kind: str
    receiver: str
    rhs: str | None
    method: str
    authored_type: str | None
    callbacks: int
    reason: str

SCALARS={'Type','Profile','BlockKind','FileIdentityV1','swift::SwiftValidationBudget','descriptor::WasiFunction'}
# Every listed primitive shape occurs in the frozen extraction. Requested native
# bytes/standard logical calls remain in their existing separate ledger terms.
PRIMITIVES={
 '&[u8]':{None,'&[u8;20]','&[u8;22]','&[u8;5]','&[u8;8]','[u8;32]','[u8;64]'},
 '[u8;32]':{None,'&[u8]'}, 'ErrorKind':{None},
 'Option<&[u8]>':{None},'Option<&u8>':{None},'Option<(u32,u32)>':{None},
 'Option<u32>':{None},'std::cmp::Ordering':{None},'str':{None},
}
def normalized(value): return re.sub(r'\s+','',value)

def classify_partial_eq(target):
    if 'PartialEq' not in target:return None
    match=re.fullmatch(r'<(.+) as PartialEq(?:<(.+)>)?>::(eq|ne)',target)
    if match is None:raise UnsupportedReceiver('unsupported-PartialEq-target:'+target)
    receiver,rhs,method=match.groups();receiver=normalized(receiver);rhs=normalized(rhs) if rhs else None
    # Container and slice shapes precede scalar matches. Substring matching Type
    # inside &[Type] or Option<Type> is never sufficient for scalar dispatch.
    if receiver=='&[Type]':
        if rhs is None:count=128;reason='selected signature parameter ceiling128'
        elif rhs=='[Type;1]':count=1;reason='fixed RHS array cardinality1'
        else:raise UnsupportedReceiver('unsupported-Type-slice-RHS:'+str(rhs))
        return EqualityDispatch('type-slice',receiver,rhs,method,'Type',count,reason)
    if receiver=='Option<Type>':
        if rhs not in (None,'Option<Type>'):raise UnsupportedReceiver('unsupported-Type-option-RHS:'+str(rhs))
        return EqualityDispatch('type-option',receiver,rhs,method,'Type',1,'one inhabited Type payload at most')
    if receiver in SCALARS:
        if rhs not in (None,receiver):raise UnsupportedReceiver('unsupported-authored-scalar-RHS:'+str(rhs))
        return EqualityDispatch('authored-scalar',receiver,rhs,method,receiver,1,'exact authored scalar receiver')
    if receiver in PRIMITIVES and rhs in PRIMITIVES[receiver]:
        return EqualityDispatch('primitive',receiver,rhs,method,None,0,'explicit primitive/std element shape; no authored callback, primitive/native costs retained')
    raise UnsupportedReceiver('unsupported-or-ambiguous-PartialEq-shape:'+target)
