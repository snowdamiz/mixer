"""Authored source-expression ledger, NOT compiler MIR or LLVM instruction prices.

Each row expands a source expression into typed logical operand occurrences.
Helper entry, each argument/result/return and all finite role ends are charged.
Both branches are conservatively retained. Only the named safe precondition
failure edges are impossible; they never give a refund or a physical bound.
"""
P='mixer_vm::experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::outer_parent_v1::existing_owner_candidate_v1::'
CALLBACK=P+'describe_existing_owner_candidate_v1::{closure#0}'
REFUSAL=P+'CandidateShapeRefusalV1'
SOURCE='official-source/library/'
NATIVE='verification/swift-guarded-snapshot-native-interface-bounds/official-source/library/'

def node(key, source, first, last, params, returns, locals_, rows, calls=(), llvm=None, safe=None):
    roles=[{'id':'_0','type':returns,'kind':'return'}]
    roles += [{'id':'_'+str(i+1),'type':ty,'kind':'parameter'} for i,ty in enumerate(params)]
    roles += [{'id':'_'+str(len(params)+i+1),'type':ty,'kind':'source-expression-place'} for i,ty in enumerate(locals_)]
    return {'id':key,'source':source,'first':first,'last':last,'roles':roles,'rows':[{'line':line,'code':code,'body_iterations':iterations} for line,code,iterations in rows], 'calls':[{'node':name,'count':count} for name,count in calls], 'llvm_name':llvm,'safe_context':safe}
def r(line,code,n=False):return (line,code,n)

def nodes():
    a=[]
    def n(*args,**kwargs):a.append(node(*args,**kwargs))
    n('range_into_iter',SOURCE+'core/src/iter/traits/collect.rs',322,324,
      ['Range<usize>'],'Range<usize>',[],[r(323,'_0 = move _1;'),r(324,'return;')],
      llvm='<core::ops::range::Range<usize> as core::iter::traits::collect::IntoIterator>::into_iter')
    n('range_next',SOURCE+'core/src/iter/range.rs',1184,1186,
      ['&mut Range<usize>'],'Option<usize>',[],[r(1185,'_0 = range_spec_next(copy _1);'),r(1186,'return;')],
      [('range_spec_next',1),('RANGE_NEXT_SOURCE_CLOSURE_FRONTIER',1)],llvm='<core::ops::range::Range<usize> as core::iter::traits::iterator::Iterator>::next')
    n('range_spec_next',SOURCE+'core/src/iter/range.rs',1099,1108,
      ['&mut Range<usize>'],'Option<usize>',['usize','usize','bool','usize','usize'],
      [r(1100,'_2 = copy ((*_1).start: usize);'),r(1100,'_3 = copy ((*_1).end: usize);'),r(1100,'_4 = Lt(copy _2, copy _3);'),r(1100,'switchInt(copy _4);'),r(1101,'_5 = copy ((*_1).start: usize);'),r(1103,'_6 = step_forward(copy _5, const 1_usize);'),r(1103,'((*_1).start: usize) = move _6;'),r(1104,'_0 = Option::<usize>::Some(copy _5);'),r(1106,'_0 = Option::<usize>::None;'),r(1108,'return;')],
      [('step_forward',1)],llvm='<core::ops::range::Range<usize> as core::iter::range::RangeIteratorImpl>::spec_next',safe='Only exact authored0..12/0..5 ranges; start<end implies old+1 does not overflow usize. Generic Step::forward_checked/expect is not selected.')
    n('step_forward',SOURCE+'core/src/iter/range.rs',263,266,
      ['usize','usize'],'usize',['usize'],[r(265,'_3 = copy _2 as usize;'),r(265,'_0 = unchecked_add_adapter(copy _1, copy _3);'),r(266,'return;')],
      [('unchecked_add_adapter',1)],llvm='<usize as core::iter::range::Step>::forward_unchecked')
    n('unchecked_add_adapter',SOURCE+'core/src/num/uint_macros.rs',1001,1015,
      ['usize','usize'],'usize',['bool'],[r(1002,'_3 = language_ub_check();'),r(1002,'switchInt(copy _3);'),r(1008,'unchecked_add_precondition(copy _1, copy _2);'),r(1013,'_0 = unchecked_add_intrinsic(copy _1, copy _2);'),r(1015,'return;')],
      [('language_ub_check',1),('unchecked_add_precondition',1),('unchecked_add_intrinsic',1)],safe='Expand assert_unsafe_precondition macro53..80 with lhs/rhs usize and !overflowing_add. Charge optional gate and check once even if disabled; safe exact range proves panic edge unreachable.')
    n('language_ub_check',SOURCE+'core/src/ub_checks.rs',96,108,[], 'bool',['bool','bool'],
      [r(98,'_1 = ConstEvalSelectResidual();'),r(98,'switchInt(copy _1);'),r(107,'_2 = ub_checks_intrinsic();'),r(107,'_0 = copy _2;'),r(107,'_0 = const false;'),r(108,'return;')],[('ub_checks_intrinsic',1)],safe='Exact non-const retained provider function. ConstEvalSelectResidual is ONLY a bool boundary result consumed by the source && switch; both result arms are conservatively charged. Full selected runtime fn() -> bool body, unit/callable intrinsic inputs, intrinsic result/return and positive finite endings are explicitly unresolved in RANGE_NEXT_SOURCE_CLOSURE_FRONTIER, once per range context. Non-selected compiletime body excluded, but its function item argument remains mandatory. No synthetic unused result or helper closure claim.')
    n('unchecked_add_precondition',SOURCE+'core/src/ub_checks.rs',68,75,
      ['usize','usize'],'()',['(usize, bool)','bool','bool','bool'],[r(69,'_3 = OverflowingAddResidual(copy _1, copy _2);'),r(69,'_4 = copy (_3.1: bool);'),r(69,'_5 = Not(copy _4);'),r(69,'_6 = Not(copy _5);'),r(69,'switchInt(copy _6);'),r(75,'_0 = const ();'),r(75,'return;')],
      [],llvm='<usize>::unchecked_add::precondition_check',safe='Macro replacement $e=!lhs.overflowing_add(rhs).1. OverflowingAddResidual returns the observed full (usize,bool)16/8 at this boundary only; its exact ActualT=u64 casts, (u64,bool) intrinsic aggregate and complete helper work/storage remain mandatory in RANGE_NEXT_SOURCE_CLOSURE_FRONTIER. The source panic/format construction70..73 is unreachable only by exact valid Range bounds; no claim on panic implementation. Track-caller boundary additionally charged by native compiler operand supplement.')
    n('add_with_overflow_intrinsic',SOURCE+'core/src/intrinsics/mod.rs',2053,2055,
      ['usize','usize'],'(usize, bool)',[],[r(2055,'_0 = AddWithOverflow(copy _1, copy _2);'),r(2055,'return;')],safe='Exact nounwind compiler intrinsic boundary, result aggregate16/8 independently observed; not compiler lowering instruction pricing.')
    n('unchecked_add_intrinsic',SOURCE+'core/src/intrinsics/mod.rs',2172,2174,
      ['usize','usize'],'usize',[],[r(2174,'_0 = AddUnchecked(copy _1, copy _2);'),r(2174,'return;')],safe='Exact nounwind primitive with no-overflow precondition established in caller; private compiler implementation remains outside logical unit.')
    n('ub_checks_intrinsic',SOURCE+'core/src/intrinsics/mod.rs',2783,2785,
      [],'bool',[],[r(2784,'_0 = CompilerCfgUbChecks();'),r(2785,'return;')],safe='Exact compiler intrinsic source cfg!(ub_checks) boundary; actual retained opt0 precondition edges are present. Not a price for private compiler work.')
    n('unlikely_adapter',SOURCE+'core/src/intrinsics/mod.rs',477,484,
      ['bool'],'bool',[],[r(478,'switchInt(copy _1);'),r(479,'cold_path_helper();'),r(480,'_0 = const true;'),r(482,'_0 = const false;'),r(484,'return;')],[('cold_path_helper',1)],safe='Exact nounwind unlikely source helper and cold_path empty source helper boundary; both branches positively charged.')
    n('cold_path_helper',SOURCE+'core/src/intrinsics/mod.rs',438,438,
      [],'()',[],[r(438,'_0 = const ();'),r(438,'return;')],safe='Exact nounwind #[cold] helper has empty source body. Entry, unit return, source actions and finite end are positive; no arbitrary zero-cost leaf.')
    n('slice_len',SOURCE+'core/src/slice/mod.rs',116,118,
      ['&[u8]'],'usize',['*const [u8]'],[r(117,'_2 = copy _1 as *const [u8];'),r(117,'_0 = ptr_metadata_adapter(copy _2);'),r(118,'return;')],[('ptr_metadata_adapter',1)],llvm='<[u8]>::len')
    n('ptr_metadata_adapter',SOURCE+'core/src/ptr/metadata.rs',100,102,
      ['*const [u8]'],'usize',[],[r(101,'_0 = PtrMetadata(copy _1);'),r(102,'return;')],safe='Exact ptr_metadata intrinsic source boundary specialized to slice metadata usize; does not scan a pointee.')
    n('usize_checked_add',SOURCE+'core/src/num/uint_macros.rs',930,944,
      ['usize','usize'],'Option<usize>',['(usize, bool)','bool','bool','usize'],
      [r(938,'_3 = add_with_overflow_intrinsic(copy _1, copy _2);'),r(938,'_4 = copy (_3.1: bool);'),r(938,'_5 = unlikely_adapter(copy _4);'),r(938,'switchInt(copy _5);'),r(939,'_0 = Option::<usize>::None;'),r(942,'_6 = unchecked_add_intrinsic(copy _1, copy _2);'),r(942,'_0 = Option::<usize>::Some(copy _6);'),r(944,'return;')],
      [('add_with_overflow_intrinsic',1),('unchecked_add_intrinsic',1),('unlikely_adapter',1)],llvm='<usize>::checked_add',safe='Both overflow/None and non-overflow/Some source arms conservatively charged; unchecked_add is called only after false overflow. Unlikely source helper and its cold_path intrinsic boundary are included.')
    n('option_ok_or_shape_refusal',SOURCE+'core/src/option.rs',1333,1338,
      ['Option<usize>','CandidateShapeRefusalV1'],'Result<usize,CandidateShapeRefusalV1>',['isize','usize'],
      [r(1334,'_3 = discriminant(_1);'),r(1334,'switchInt(copy _3);'),r(1335,'_4 = copy ((_1 as Some).0: usize);'),r(1335,'_0 = Result::Ok(copy _4);'),r(1336,'_0 = Result::Err(move _2);'),r(1338,'return;')],
      llvm='<core::option::Option<usize>>::ok_or::<'+REFUSAL+'>',safe='CandidateShapeRefusalV1 exact Copy enum of unit/usize only; unused err gets positive finite-end charge. No owned Drop frontier; LLVM has no call/invoke.')
    n('result_try_branch',SOURCE+'core/src/result.rs',2176,2181,
      ['Result<usize,CandidateShapeRefusalV1>'],'ControlFlow<Residual,usize>',['isize','usize','CandidateShapeRefusalV1','Residual'],
      [r(2177,'_2 = discriminant(_1);'),r(2177,'switchInt(copy _2);'),r(2178,'_3 = copy ((_1 as Ok).0: usize);'),r(2178,'_0 = ControlFlow::Continue(copy _3);'),r(2179,'_4 = copy ((_1 as Err).0: CandidateShapeRefusalV1);'),r(2179,'_5 = Result::Err(move _4);'),r(2179,'_0 = ControlFlow::Break(move _5);'),r(2181,'return;')],
      llvm='<core::result::Result<usize, '+REFUSAL+'> as core::ops::try_trait::Try>::branch',safe='Both Ok/Err paths retain all source places and finite ends; exact Copy enum has no owned destructors.')
    n('candidate_result_from_residual',SOURCE+'core/src/result.rs',2191,2195,
      ['Residual'],'CandidateResult',['CandidateShapeRefusalV1','CandidateShapeRefusalV1'],
      [r(2192,'_2 = copy ((_1 as Err).0: CandidateShapeRefusalV1);'),r(2193,'_3 = refusal_from_identity(move _2);'),r(2193,'_0 = Result::Err(move _3);'),r(2195,'return;')],[('refusal_from_identity',1)],
      llvm='<core::result::Result<'+P+'UnqualifiedExistingOwnerCandidateV1, '+REFUSAL+'> as core::ops::try_trait::FromResidual<core::result::Result<core::convert::Infallible, '+REFUSAL+'>>>::from_residual',safe='Residual Ok(Infallible) is uninhabited. F=E exactly; generic error conversions refused. Track-caller compiler boundary separately charged.')
    n('refusal_from_identity',SOURCE+'core/src/convert/mod.rs',791,793,
      ['CandidateShapeRefusalV1'],'CandidateShapeRefusalV1',[],[r(792,'_0 = move _1;'),r(793,'return;')],safe='Exact reflexive From<T> for T with T=CandidateShapeRefusalV1. LLVM inlines the Copy move; no arbitrary conversion closure.')
    n('path_as_os_str',SOURCE+'std/src/path.rs',2436,2438,
      ['&Path'],'&OsStr',[],[r(2437,'_0 = &((*_1).inner: OsStr);'),r(2438,'return;')],llvm='<std::path::Path>::as_os_str')
    n('osstr_as_bytes',NATIVE+'std/src/os/unix/ffi/os_str.rs',60,62,
      ['&OsStr'],'&[u8]',['&UnixOsSlice'],[r(61,'_2 = osstr_as_inner(copy _1);'),r(61,'_0 = &((*_2).inner: [u8]);'),r(62,'return;')],[('osstr_as_inner',1)],llvm='<std::ffi::os_str::OsStr as std::os::unix::ffi::os_str::OsStrExt>::as_bytes')
    n('osstr_as_inner',NATIVE+'std/src/ffi/os_str.rs',1800,1802,
      ['&OsStr'],'&UnixOsSlice',[],[r(1801,'_0 = &((*_1).inner: UnixOsSlice);'),r(1802,'return;')],safe='Exact aarch64-apple-darwin unix bytes Slice, repr(transparent) inner[u8]; OsStr repr(transparent) innerSlice. No encoding conversion or owned allocation.')
    n('slice_is_empty',SOURCE+'core/src/slice/mod.rs',136,138,
      ['&[u8]'],'bool',['usize'],[r(137,'_2 = slice_len(copy _1);'),r(137,'_0 = Eq(copy _2, const 0_usize);'),r(138,'return;')],[('slice_len',1)],llvm='<[u8]>::is_empty')
    n('option_and_then_excluding_authored_callback',SOURCE+'core/src/option.rs',1537,1545,
      ['Option<usize>','ProductionClosure'],'Option<usize>',['isize','usize','Option<usize>'],
      [r(1541,'_3 = discriminant(_1);'),r(1541,'switchInt(copy _3);'),r(1542,'_4 = copy ((_1 as Some).0: usize);'),r(1542,'_5 = AUTHORED_CALLBACK(move _2, move _4);'),r(1542,'_0 = move _5;'),r(1543,'_0 = Option::<usize>::None;'),r(1545,'return;')],[('AUTHORED_CALLBACK',1)],
      llvm='<core::option::Option<usize>>::and_then::<usize, '+CALLBACK+'>',safe='Exact actual closure16/8, two shared references. Its body cap5 and all11 compiler roles already charged by provider base. This source ledger adds only the adapter call boundary, result forwarding and positive finite ends; None/unwind gives no refund.')
    n('digest_array_ne32',SOURCE+'core/src/array/equality.rs',14,16,
      ['&[u8;32]','&[u8;32]'],'bool',[],[r(15,'_0 = array_spec_ne32(copy _1, copy _2);'),r(16,'return;')],[('array_spec_ne32',1)],llvm='<[u8; 32] as core::cmp::PartialEq>::ne')
    n('array_spec_ne32',SOURCE+'core/src/array/equality.rs',159,161,
      ['&[u8;32]','&[u8;32]'],'bool',['bool'],[r(160,'_3 = array_spec_eq32(copy _1, copy _2);'),r(160,'_0 = Not(copy _3);'),r(161,'return;')],[('array_spec_eq32',1)],llvm='<u8 as core::array::equality::SpecArrayEq<u8, 32>>::spec_ne')
    n('array_spec_eq32',SOURCE+'core/src/array/equality.rs',153,158,
      ['&[u8;32]','&[u8;32]'],'bool',['&[u8;32]'],[r(157,'_3 = Transmute(copy _2);'),r(157,'_0 = RAW_EQ32_FRONTIER(copy _1, copy _3);'),r(158,'return;')],[('DIGEST_MEMCMP_FRONTIER',1)],safe='u8 BytewiseEq specialization, raw_eq exactly32 readable bytes on each side. Retained LLVM calls external memcmp32; no generic element loop, vector-bound inference or private memcmp price.')
    n('slice_reference_ne',SOURCE+'core/src/cmp.rs',2354,2356,
      ['&&[u8]','&&[u8]'],'bool',['&[u8]','&[u8]'],[r(2355,'_3 = copy (*_1);'),r(2355,'_4 = copy (*_2);'),r(2355,'_0 = slice_default_ne(copy _3, copy _4);'),r(2356,'return;')],[('slice_default_ne',1)],llvm='<&[u8] as core::cmp::PartialEq>::ne')
    n('slice_default_ne',SOURCE+'core/src/cmp.rs',275,277,
      ['&[u8]','&[u8]'],'bool',['bool'],[r(276,'_3 = slice_eq(copy _1, copy _2);'),r(276,'_0 = Not(copy _3);'),r(277,'return;')],[('slice_eq',1)],llvm='<[u8] as core::cmp::PartialEq>::ne')
    n('slice_eq',SOURCE+'core/src/slice/cmp.rs',19,28,
      ['&[u8]','&[u8]'],'bool',['usize','usize','bool','*const u8','*const u8'],
      [r(20,'_3 = slice_len(copy _1);'),r(21,'_4 = slice_len(copy _2);'),r(21,'_5 = Eq(copy _3, copy _4);'),r(21,'switchInt(copy _5);'),r(24,'_6 = slice_as_ptr(copy _1);'),r(24,'_7 = slice_as_ptr(copy _2);'),r(24,'_0 = bytewise_eq(copy _6, copy _7, copy _3);'),r(26,'_0 = const false;'),r(28,'return;')],[('slice_len',2),('slice_as_ptr',2),('bytewise_eq',1)],llvm='<[u8] as core::cmp::PartialEq>::eq',safe='u8 BytewiseEq selected; unequal lengths skip comparison, but entire shell and residual reserve retained. Exact source as_ptr helper and each primitive cast are included; no ownership transfer.')
    n('slice_as_ptr',SOURCE+'core/src/slice/mod.rs',728,730,
      ['&[u8]'],'*const u8',['*const [u8]'],[r(729,'_2 = copy _1 as *const [u8];'),r(729,'_0 = copy _2 as *const u8;'),r(730,'return;')],safe='Exact reference→wide raw→thin raw casts; source/typed native operands are charged, no buffer allocation or backing credit.')
    n('bytewise_eq',SOURCE+'core/src/slice/cmp.rs',151,159,
      ['*const u8','*const u8','usize'],'bool',['usize','i32'],[r(156,'_4 = MulUnchecked(copy _3, const 1_usize);'),r(157,'_5 = PATH_MEMCMP_FRONTIER(copy _1, copy _2, copy _4);'),r(157,'_0 = Eq(copy _5, const 0_i32);'),r(159,'return;')],[('PATH_MEMCMP_FRONTIER',1)],llvm='<u8 as core::slice::cmp::SlicePartialEq<u8>>::equal_same_length',safe='Equal readable slice lengths; len*size_of(u8)=len, so no overflow. External memcmp length is actual native path length when equal, conservatively max(actual native,retained)<=B for every path.')
    n('slice_contains_u8',SOURCE+'core/src/slice/mod.rs',2600,2605,
      ['&[u8]','&u8'],'bool',[],[r(2604,'_0 = u8_contains_shell(copy _2, copy _1);'),r(2605,'return;')],[('u8_contains_shell',1)],llvm='<[u8]>::contains')
    n('u8_contains_shell',SOURCE+'core/src/slice/cmp.rs',396,408,
      ['&u8','&[u8]'],'bool',['usize','bool','u8','&[u8]','Option<usize>'],
      [r(397,'_3 = SizeOf::<u8>();'),r(397,'_4 = Eq(copy _3, const 1_usize);'),r(397,'switchInt(copy _4);'),r(402,'_5 = TransmuteCopyU8(copy _1);'),r(402,'_6 = FromRawPartsU8(copy _2);'),r(404,'_7 = memchr_shell(copy _5, copy _6);'),r(404,'_0 = OptionIsSomeResidual(copy _7);'),r(408,'return;')],[('memchr_shell',1),('CONTAINS_RESIDUAL_FRONTIER',1)],llvm='<u8 as core::slice::cmp::SliceContains>::slice_contains',safe='size_of(u8)=1, so source else406 Iter::any and macro vector specialization411..435 are unselected. All actual transmute_copy/from_raw_parts instrumented helper work, native operands/slots and assert_unchecked checking remain required inside the positive composite residual. Source primitive boundary occurrences above are additional shell work, never a claim to close those helpers. OptionIsSomeResidual is ONLY the caller bool boundary, not a source helper closure: receiver auto-borrow &Option<usize>, complete Option::is_some and matches/match expansion with typed operand/result/return and positive finite endings remain explicitly mandatory in CONTAINS_RESIDUAL_FRONTIER.')
    n('memchr_shell',SOURCE+'core/src/slice/memchr.rs',25,34,
      ['u8','&[u8]'],'Option<usize>',['usize','bool','Option<usize>','isize','usize','bool'],
      [r(28,'_3 = slice_len(copy _2);'),r(28,'_4 = Lt(copy _3, const 16_usize);'),r(28,'switchInt(copy _4);'),r(28,'_5 = memchr_naive(copy _1, copy _2);'),r(28,'_5 = MEMCHR_ALIGNED_FRONTIER(copy _1, copy _2);'),r(29,'_6 = discriminant(_5);'),r(29,'switchInt(copy _6);'),r(29,'_7 = copy ((_5 as Some).0: usize);'),r(31,'_8 = Lt(copy _7, copy _3);'),r(31,'AssertUncheckedBoundary(copy _8);'),r(33,'_0 = copy _5;'),r(34,'return;')],[('slice_len',1),('memchr_naive',1)],llvm='core::slice::memchr::memchr',safe='16=2*observed usize8, exact compiler/source branch. Aligned branch belongs to CONTAINS_RESIDUAL_FRONTIER, not a second term. Source result Some index<len assertion and all its helper work remain in that residual.')
    n('memchr_naive',SOURCE+'core/src/slice/memchr.rs',37,50,
      ['u8','&[u8]'],'Option<usize>',['usize','usize','bool','u8','bool'],
      [r(38,'_3 = const 0_usize;'),r(41,'_4 = slice_len(copy _2);',True),r(41,'_5 = Lt(copy _3, copy _4);',True),r(41,'switchInt(copy _5);',True),r(42,'_6 = copy (*_2)[_3];',True),r(42,'_7 = Eq(copy _6, copy _1);',True),r(42,'switchInt(copy _7);',True),r(43,'_0 = Option::<usize>::Some(copy _3);',True),r(43,'return;',True),r(46,'_3 = Add(copy _3, const 1_usize);',True),r(49,'_0 = Option::<usize>::None;'),r(50,'return;')],[('slice_len','body+1')],safe='Selected only when n<16. Loop uses n+1 conservatively for every row, n<=B actual path length; source ledger retains B² body allowances rather than selecting15 as an arbitrary maximum. Monotone i, valid slice and exact LLVM bound checks prove panic edge unreachable. No extra callback; this is not Iter::any.')
    return a

COUNTS={'range_into_iter':2,'range_next':19,'slice_len':33,'usize_checked_add':22,'option_ok_or_shape_refusal':17,'result_try_branch':17,'candidate_result_from_residual':2,'digest_array_ne32':1,'path_as_os_str':5,'osstr_as_bytes':5,'slice_is_empty':5,'slice_contains_u8':5,'slice_reference_ne':5,'option_and_then_excluding_authored_callback':5}
PARTIAL={'range_next':'RANGE_NEXT_SOURCE_CLOSURE_FRONTIER','digest_array_ne32':'DIGEST_MEMCMP_FRONTIER','slice_reference_ne':'PATH_MEMCMP_FRONTIER','slice_contains_u8':'CONTAINS_RESIDUAL_FRONTIER'}
FRONTIERS={
 'DIGEST_MEMCMP_FRONTIER':{'count':1,'source_interface':'raw_eq::<[u8;32]>','source_argument_types':['&[u8;32]','&[u8;32]'],'source_return_type':'bool','argument_types':['*const u8','*const u8','usize'],'return_type':'i32','length':'exact32','native_target':'memcmp','remaining':'Actual composed raw_eq→external memcmp32 logical native/helper work and residual source/ABI places; no private memcmp implementation or time bound.'},
 'PATH_MEMCMP_FRONTIER':{'count':5,'argument_types':['*const u8','*const u8','usize'],'return_type':'i32','length':'max(actual_native_path[i],actual_separately_retained_path[i])','native_target':'memcmp','remaining':'Actual composed compare_bytes→external memcmp at exact equal readable byte length; no selected generic element loop or zero price on unequal-length/refusal paths.'},
 'CONTAINS_RESIDUAL_FRONTIER':{'count':5,'source_interface':'<u8 as SliceContains>::slice_contains, residual after charged scalar/short-loop shell','argument_types':['&u8','&[u8]'],'return_type':'bool','length':'actual_native_path[i]','native_target':'_RNvNtNtCsjIpoRzUjyHQ_4core5slice6memchr14memchr_aligned','aligned_argument_types':['u8','&[u8]'],'aligned_return_type':'Option<usize>','remaining':'Full Option::<usize>::is_some: receiver auto-borrow &Option<usize>, helper entry, dereference operand Option<usize>, matches! expansion to match Some(_) => true / _ => false, bool result and return, every finite source place ending; exact typed native operands and full storage, never an LLVM discriminant-only replacement. Full transmute_copy::<u8,u8>/from_raw_parts::<u8> precondition helper work/operands/slots, source tuple(u8,&[u8]) place if materialized, assert_unchecked precondition, and installed memchr_aligned including its argument/result/return and source/compiler/private-native frontier. Short naive-loop source shell is charged separately. No finite CPU/allocator/kernel bound.'}
}

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
