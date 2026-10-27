"""One-time own-packet preparation from immutable producer, with explicit corrections."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from custody import HERE,ORIGINAL

def main():
 for name in ('derive.py','ledger.py','model.py'):
  (HERE/name).write_bytes((ORIGINAL/name).read_bytes())
 p=HERE/'derive.py';s=p.read_text();a=s.index('def input_roster():');b=s.index('def llvm_functions(',a)
 s=s[:a]+"def input_roster():\n    from custody import roster\n    return roster()\n"+s[b:]
 s=s.replace("def source_path(s):return HERE/s if s.startswith('official-source/') else ROOT/s","def source_path(s):\n    from custody import ORIGINAL\n    return ORIGINAL/s if s.startswith('official-source/') else ROOT/s")
 s=s.replace("'exact14 interfaces and3 positive composite frontier contracts'","'exact14 interfaces and4 positive composite frontier contracts'")
 s=s.replace("'mandatory, exact11 invocation contexts, no default or refund'","'mandatory, exact30 invocation contexts (1+5+5+19), no default or refund'")
 s=s.replace("'all15 phases',","'all15 phases', 'range_next R1+R2 composite residual exact19 contexts',")
 s=s.replace("'status':'separate-proposed-source-ledger-amendment-needs-independent-review-and-root-price-selection'","'status':'focused-R1-R3-source-correction-partial-range-next-needs-fresh-review-and-root-selection'")
 s=s.replace("'positive_residual_contracts':ledger.FRONTIERS,","'positive_residual_contracts':ledger.FRONTIERS,'source_closure_frontiers':ledger.closure_frontiers(),'source_closure_frontiers_sha256':sha(canon(ledger.closure_frontiers())),")
 s=s.replace("'contains':'u8 size1 constant branch", "'range_next_source_correction':'R1 exact64-bit usize ActualT=u64; three source casts and full (u64,bool) intrinsic aggregate remain in strict positive compound R1+R2 work/storage frontier. R2 selected runtime fn()->bool, unit/callable intrinsic arguments, full result/return/positive finite ends remain explicit in same exact19 frontier. No callable or aggregate layout is guessed.', 'contains':'u8 size1 constant branch")
 s=s.replace("All precondition helpers/assert_unchecked and missing aligned work/slots remain in positive composite residual.","All precondition helpers/assert_unchecked, missing aligned work/slots and full Option::<usize>::is_some receiver-auto-borrow/matches expansion/operands/results/returns/finite ends remain in positive composite residual.")
 s=s.replace("return {'proposal.json':proposal,", "return {'source-closure-frontiers.json':ledger.closure_frontiers(),'proposal.json':proposal,")
 p.write_text(s)
 p=HERE/'ledger.py';s=p.read_text();s=s.replace("[('range_spec_next',1)],llvm=","[('range_spec_next',1),('RANGE_NEXT_SOURCE_CLOSURE_FRONTIER',1)],llvm=")
 a=s.index("    n('language_ub_check'");b=s.index("    n('unchecked_add_precondition'",a)
 s=s[:a]+'''    n('language_ub_check',SOURCE+'core/src/ub_checks.rs',96,108,[], 'bool',['bool','bool'],
      [r(98,'_1 = ConstEvalSelectResidual();'),r(98,'switchInt(copy _1);'),r(107,'_2 = ub_checks_intrinsic();'),r(107,'_0 = copy _2;'),r(107,'_0 = const false;'),r(108,'return;')],[('ub_checks_intrinsic',1)],safe='Exact non-const retained provider function. ConstEvalSelectResidual is ONLY a bool boundary result consumed by the source && switch; both result arms are conservatively charged. Full selected runtime fn() -> bool body, unit/callable intrinsic inputs, intrinsic result/return and positive finite endings are explicitly unresolved in RANGE_NEXT_SOURCE_CLOSURE_FRONTIER, once per range context. Non-selected compiletime body excluded, but its function item argument remains mandatory. No synthetic unused result or helper closure claim.')
'''+s[b:]
 s=s.replace("_3 = overflowing_add_adapter(copy _1, copy _2);","_3 = OverflowingAddResidual(copy _1, copy _2);")
 s=s.replace("[('overflowing_add_adapter',1)],llvm=","[],llvm=")
 a=s.index("    n('overflowing_add_adapter'");b=s.index("    n('add_with_overflow_intrinsic'",a);s=s[:a]+s[b:]
 s=s.replace("Macro replacement $e=!lhs.overflowing_add(rhs).1.","Macro replacement $e=!lhs.overflowing_add(rhs).1. OverflowingAddResidual returns the observed full (usize,bool)16/8 at this boundary only; its exact ActualT=u64 casts, (u64,bool) intrinsic aggregate and complete helper work/storage remain mandatory in RANGE_NEXT_SOURCE_CLOSURE_FRONTIER.")
 s=s.replace("_0 = IsSome(copy _7);","_0 = OptionIsSomeResidual(copy _7);")
 s=s.replace("Source primitive boundary occurrences above are additional shell work, never a claim to close those helpers.","Source primitive boundary occurrences above are additional shell work, never a claim to close those helpers. OptionIsSomeResidual is ONLY the caller bool boundary, not a source helper closure: receiver auto-borrow &Option<usize>, complete Option::is_some and matches/match expansion with typed operand/result/return and positive finite endings remain explicitly mandatory in CONTAINS_RESIDUAL_FRONTIER.")
 s=s.replace("PARTIAL={'digest_array_ne32'","PARTIAL={'range_next':'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER','digest_array_ne32'")
 s=s.replace("'remaining':'Full transmute_copy", "'remaining':'Full Option::<usize>::is_some: receiver auto-borrow &Option<usize>, helper entry, dereference operand Option<usize>, matches! expansion to match Some(_) => true / _ => false, bool result and return, every finite source place ending; exact typed native operands and full storage, never an LLVM discriminant-only replacement. Full transmute_copy")
 s += '''
# Exact selected-source closure obligations. None means unpriced evidence missing,
# never a numeric zero, one, pointer-width surrogate, or guessed aggregate size.
def closure_frontiers():
    return {
      'schema':1,
      'range_next':{
        'frontier':'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER','count':19,'unit_pair':['work','bytes'],
        'exact_macro_selection':{'revision':'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4','source':'official-source/library/core/src/num/mod.rs','lines':[1450,1451,1452,1453,1454],'cfg':'target_pointer_width = "64"','Self':'usize','ActualT':'u64','not_inferred_from_LLVM_i64':True},
        'R1':{
          'source':'verification/swift-guarded-snapshot-owned-provider-callee-interfaces/official-source/library/core/src/num/uint_macros.rs','lines':[2989,2990,2991,2992],
          'signature':'overflowing_add(self: usize, rhs: usize) -> (usize, bool)',
          'roles':[{'id':name,'type':ty,'storage':'mandatory compound residual; not assigned a numeric layout'} for name,ty in [('self','usize'),('rhs','usize'),('self_cast','u64'),('rhs_cast','u64'),('intrinsic_result','(u64, bool)'),('a','u64'),('b','bool'),('result_cast','usize'),('return','(usize, bool)')]],
          'operations':['helper entry with self:usize and rhs:usize','self as u64','rhs as u64','intrinsics::add_with_overflow::<u64>(self_cast, rhs_cast)','full intrinsic argument/result/return and finite endings','destructure full (u64, bool) to a:u64,b:bool','a as usize','construct and return full (usize, bool)','positive finite ending for every argument/result/local/return place'],
          'casts':3,'unobserved_full_aggregate':{'type':'(u64, bool)','size':None,'align':None,'status':'pending exact full aggregate evidence; no field sum or usize tuple substitution'},
          'observed_outer_return':{'type':'(usize, bool)','size':16,'align':8,'evidence':'frozen source146-callee-storage-layouts/results.json'}},
        'R2':{
          'macro_source':'verification/swift-guarded-snapshot-owned-provider-callee-interfaces/official-source/library/core/src/intrinsics/mod.rs','macro_lines':[2613,2623,2629,2636],
          'call_site':'verification/swift-guarded-snapshot-owned-provider-callee-interfaces/official-source/library/core/src/ub_checks.rs:98-107',
          'expanded':'fn runtime() -> bool { !cfg!(miri) }; const fn compiletime() -> bool { false }; const_eval_select::<(), CompiletimeItem, RuntimeItem, bool>((), compiletime, runtime)',
          'roles':[{'id':name,'type':ty,'storage':'mandatory compound residual; unknown callable layout remains unpriced'} for name,ty in [('unit_argument','()'),('compiletime_argument','function item check_language_ub::{compiletime}, signature fn() -> bool'),('runtime_argument','function item check_language_ub::{runtime}, signature fn() -> bool'),('runtime_return','bool'),('runtime_not_operand','bool'),('runtime_not_result','bool'),('intrinsic_result','bool'),('intrinsic_return','bool')]],
          'operations':['construct empty captured-values tuple ()','materialize compiletime and runtime function-item arguments (not coerced fn pointers)','const_eval_select intrinsic entry with exact three arguments and bool return','selected runtime fn() -> bool entry','evaluate cfg!(miri) bool and unary !','runtime bool result and return','intrinsic bool result and return to source && consumer','positive finite endings of all unit/callable/operand/result/return places'],
          'selection':'non-const source146 provider path retained in exact LLVM; runtime helper selected, cfg(miri) absent in compiler plan. compiletime BODY unselected; compiletime function-item intrinsic argument is retained.',
          'callable_layouts':{'compiletime_item':None,'runtime_item':None,'status':'exact callable layouts pending; no 0/1 price or fn-pointer substitution'},
          'private_intrinsic_implementation':'outside inherited logical source unit; macro-generated runtime function is inside mandatory residual'},
        'conservative_schedule':[{'occurrence':i,'loop':'identity' if i<13 else 'path','limit':12 if i<13 else 5,'header_index':i if i<13 else i-13} for i in range(19)],
        'final_none_refusal_unwind':'all19 residual work and storage required; no inactive-helper, None, refusal or unwind refund'},
      'contains':{
        'frontier':'CONTAINS_RESIDUAL_FRONTIER','count':5,'unit_pair':['work','bytes'],
        'source':'verification/swift-guarded-snapshot-owned-provider-callee-interfaces/official-source/library/core/src/option.rs:633-635',
        'macro_source':'official-source/library/core/src/macros/mod.rs:431-439',
        'receiver':'auto-borrow memchr(...):Option<usize> as &Option<usize>',
        'signature':'Option::<usize>::is_some(self: &Option<usize>) -> bool',
        'expanded':'match *self { Some(_) => true, _ => false }',
        'roles':[{'id':name,'type':ty,'storage':'mandatory existing contains composite residual'} for name,ty in [('memchr_result','Option<usize>'),('receiver_autoborrow','&Option<usize>'),('self','&Option<usize>'),('deref_scrutinee','Option<usize>'),('some_pattern','Some(_) of Option<usize>'),('match_true','bool'),('match_false','bool'),('helper_return','bool'),('caller_result','bool')]],
        'operations':['receiver auto-borrow with full Option<usize> pointee','helper entry and receiver argument','dereference and match discriminant/pattern operand','both true/false bool match results conservatively retained','bool result/return and caller boundary','positive finite ending for each receiver/operand/result/return place'],
        'all_prior_obligations_preserved':['transmute_copy::<u8,u8> precondition/helper work and slots','from_raw_parts::<u8> precondition/helper work and slots','source tuple(u8,&[u8]) if materialized','assert_unchecked precondition/helpers','installed memchr_aligned full argument/result/return/source/compiler/private-native frontier'],
        'actual_lengths':'each actual native readable path length, separately typed for each of five contexts; storage and work individually positive'}
    }
FRONTIERS['RANGE_NEXT_SOURCE_CLOSURE_FRONTIER']={'count':19,'source_interface':'range_next R1 overflowing_add::<usize> ActualT=u64 + R2 check_language_ub const_eval_select runtime source closure','argument_types':['&mut Range<usize>'],'return_type':'Option<usize>','native_target':'source-closure-composite-not-a-native-symbol','length':'no byte-body argument; exact immutable loop/header context per occurrence','remaining':'All closure_frontiers.range_next R1 and R2 exact source/type/count compound work AND storage obligations; no missing aggregate or callable layout is assigned 0/1/field-sum/usize-tuple size. Full casts/intrinsic/helper/unit/callables/runtime result/return and positive finite endings mandatory.'}
'''
 p.write_text(s)
 p=HERE/'model.py';s=p.read_text().replace('from ledger import COUNTS, FRONTIERS','from ledger import COUNTS, FRONTIERS, closure_frontiers')
 s=s.replace("'exact14 interfaces and3 positive composite frontier contracts'","'exact14 interfaces and4 positive composite frontier contracts'")
 s=s.replace("    return p\ndef proposal():", "    import derive as D\n    need(p==expected_proposal(), 'exact corrected shell, phases, storage and typed source obligations')\n    return p\n@lru_cache(maxsize=1)\ndef expected_proposal():\n    import derive as D\n    return D.derive()['proposal.json']\ndef proposal():")
 s=s.replace('    obligation:str','    obligation:str\n    source_contract_sha256:str\n    invocation_context:tuple')
 s=s.replace("    return shape,x","    x += [{'frontier':'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER','occurrence':s['occurrence'],'body_lengths':(),'invocation_context':(s['loop'],s['limit'],s['header_index'])} for s in closure_frontiers()['range_next']['conservative_schedule']]\n    return shape,x")
 s=s.replace("need(len(items)==11,'exact1plus5plus5-frontier-contexts-required')","need(len(items)==30,'exact1plus5plus5plus19-frontier-contexts-required')")
 s=s.replace("        spec=p['positive_residual_contracts'][item.frontier]", "        need(item.source_contract_sha256==p['source_closure_frontiers_sha256'],'exact full R1-R3 source obligation contract digest')\n        need(type(item.invocation_context)is tuple and item.invocation_context==context.get('invocation_context',()),'exact immutable loop/header context required')\n        spec=p['positive_residual_contracts'][item.frontier]")
 p.write_text(s)
 print('Prepared owned correction source; no old packet or product files changed')
if __name__=='__main__':main()
