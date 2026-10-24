// Independent positive named authored-object/callsite accounting.
// Class array indices map one-to-one to positive-accounting-map.json bindings.
// Every old inventory remains charged. No phase padding or diagnostic slot is reused.
#[allow(dead_code)]
pub(crate) struct ConstructionPositivePreflight{
 class_0: [bool;24],
 class_1: [&'static crate::execute::Cancellation;3],
 class_2: [&'static std::sync::atomic::AtomicBool;2],
 class_3: [&'static std::sync::Arc<std::sync::atomic::AtomicBool>;2],
 class_4: [std::sync::atomic::Ordering;2],
 class_5: [std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_6: [&'static mut super::control::RuntimeControl;37],
 class_7: [Option<&'static AccountedWasi>;3],
 class_8: [super::control::Cursor;38],
 class_9: [std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>;2],
 class_10: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor);6],
 class_11: [&'static crate::experimental_swift_reactor::control::Cursor;8],
 class_12: [std::option::Option<crate::experimental_wasi::WasiUsage>;28],
 class_13: [&'static CacheControl<'static>;1],
 class_14: [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>;6],
 class_15: [crate::experimental_swift_reactor::control::SwiftRunFailure;19],
 class_16: [&'static mut CacheControl<'static>;3],
 class_17: [crate::experimental::cache::CacheFailureKind;3],
 class_18: [&'static str;21],
 class_19: [crate::experimental_swift_reactor::control::SwiftRunFailureKind;27],
 class_20: [isize;24],
 class_21: [crate::experimental_swift_reactor::control::Cursor;14],
 class_22: [crate::experimental_swift_reactor::control::Fault;28],
 class_23: [&'static crate::experimental_swift_reactor::cache::CacheControl<'static>;4],
 class_24: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl;17],
 class_25: [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>;24],
 class_26: [&'static SwiftFunctionCache;7],
 class_27: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>;1],
 class_28: [std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>;22],
 class_29: [&'static crate::experimental_swift_reactor::control::ReservationTicket;9],
 class_30: [std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_31: [&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;6],
 class_32: [&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>;2],
 class_33: [crate::experimental_swift_reactor::cache::CacheControl<'static>;1],
 class_34: [crate::experimental_swift_reactor::cache::SwiftCacheUsage;2],
 class_35: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage;11],
 class_36: [&'static super::control::SwiftReservations;1],
 class_37: [super::control::SwiftReservationCategory;8],
 class_38: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage;10],
 class_39: [&'static mut super::control::SwiftReservations;1],
 class_40: [super::control::SwiftRunFailureKind;3],
 class_41: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>;3],
 class_42: [std::option::Option<usize>;24],
 class_43: [std::option::Option<crate::experimental_wasi::WasiFailure>;2],
 class_44: [std::option::Option<u32>;3],
 class_45: [super::control::Fault;2],
 class_46: [super::control::SwiftRunResource;1],
 class_47: [u64;32],
 class_48: [crate::experimental_swift_reactor::control::SwiftRunUsage;4],
 class_49: [&'static super::control::RuntimeControl;3],
 class_50: [Option<WasiUsage>;18],
 class_51: [std::time::Instant;6],
 class_52: [crate::experimental_swift_reactor::control::SwiftReservations;1],
 class_53: [crate::experimental_swift_reactor::control::SwiftLiveUsage;1],
 class_54: [std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>;1],
 class_55: [std::time::Duration;5],
 class_56: [&'static std::time::Instant;8],
 class_57: [crate::experimental_swift_reactor::control::SwiftDeadlineOrigin;2],
 class_58: [crate::experimental::swift::SwiftValidationUsage;1],
 class_59: [crate::experimental_swift_reactor::control::SwiftRunStage;1],
 class_60: [&'static crate::experimental_swift_reactor::control::RuntimeControl;10],
 class_61: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>;1],
 class_62: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_63: [usize;59],
 class_64: [std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_65: [&'static crate::experimental_swift_reactor::control::SwiftReservations;4],
 class_66: [(&'static usize,);12],
 class_67: [&'static usize;8],
 class_68: [crate::experimental_swift_reactor::control::SwiftRunResource;4],
 class_69: [(usize, usize);2],
 class_70: [();5],
 class_71: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations;2],
 class_72: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>;6],
 class_73: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>;2],
 class_74: [std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>;6],
 class_75: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>);3],
 class_76: [&'static std::option::Option<crate::experimental_wasi::WasiUsage>;2],
 class_77: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>;1],
 class_78: [crate::experimental_swift_reactor::control::SwiftReservationCategory;6],
 class_79: [(usize, bool);1],
 class_80: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket;1],
 class_81: [std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_82: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_83: [&'static super::control::AdoptedProof;1],
 class_84: [&'static super::control::ReservationTicket;3],
 class_85: [std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>;1],
 class_86: [(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str);2],
 class_87: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant;4],
 class_88: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant;1],
 class_89: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>;2],
 class_90: [std::result::Result<u64, std::num::TryFromIntError>;2],
 class_91: [u128;2],
 class_92: [&'static std::time::Duration;2],
 class_93: [&'static AccountedWasi;16],
 class_94: [crate::experimental_wasi::WasiUsage;9],
 class_95: [std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_96: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>;1],
 class_97: [std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>;4],
 class_98: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor);3],
 class_99: [crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>;1],
 class_100: [std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>;1],
 class_101: [&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>;2],
 class_102: [WasiGrants;1],
 class_103: [WasiBudget;1],
 class_104: [Instant;1],
 class_105: [&'static mut crate::experimental_swift_reactor::control::AdoptedProof;1],
 class_106: [&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof);1],
 class_107: [std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>;2],
 class_108: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>;2],
 class_109: [std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>;4],
 class_110: [&'static crate::experimental_swift_reactor::control::AdoptedProof;2],
 class_111: [std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>;6],
 class_112: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>;1],
 class_113: [std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>;2],
 class_114: [std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>;1],
 class_115: [&'static crate::experimental_wasi::WasiContext;7],
 class_116: [(&'static crate::experimental_wasi::accounted::AccountedWasi,);3],
 class_117: [crate::experimental_swift_reactor::execution::ConstructionFailure;1],
 class_118: [super::control::SwiftRunFailure;1],
 class_119: [&'static crate::experimental_wasi::accounted::AccountedWasi;3],
 class_120: [Result<SwiftReactorInstance,ConstructionFailure>;2],
 class_121: [Option<Result<SwiftReactorInstance,ConstructionFailure>>;2],
 class_122: [ConstructionFailure;1],
 class_123: [ConstructionCleanupTail;1],
 class_124: [(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>);1],
}
pub(crate)const CONSTRUCTION_POSITIVE_PREFLIGHT_BYTES:usize=std::mem::size_of::<ConstructionPositivePreflight>();
#[allow(dead_code)]
pub(crate) struct ConstructionPositiveActive{
 class_0: [std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>;15],
 class_1: [&'static mut super::control::RuntimeControl;84],
 class_2: [super::control::SwiftReservationCategory;3],
 class_3: [usize;319],
 class_4: [super::control::Cursor;47],
 class_5: [Option<WasiUsage>;42],
 class_6: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>;48],
 class_7: [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>;138],
 class_8: [isize;135],
 class_9: [std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>;160],
 class_10: [bool;89],
 class_11: [crate::experimental_swift_reactor::control::SwiftRunFailure;60],
 class_12: [crate::experimental_swift_reactor::control::Fault;39],
 class_13: [crate::experimental_swift_reactor::control::SwiftRunFailureKind;36],
 class_14: [crate::experimental_swift_reactor::control::SwiftRunResource;17],
 class_15: [u64;48],
 class_16: [(u64, bool);1],
 class_17: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>;1],
 class_18: [std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_19: [(usize, usize);1],
 class_20: [();29],
 class_21: [(usize, bool);25],
 class_22: [crate::experimental_swift_reactor::control::ReservationTicket;22],
 class_23: [&'static str;51],
 class_24: [Option<Result<SwiftExecutionState,SwiftRunFailure>>;5],
 class_25: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant;22],
 class_26: [&'static crate::experimental_swift_reactor::control::ReservationTicket;2],
 class_27: [std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_28: [&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_29: [&'static crate::experimental_swift_reactor::control::SwiftReservationCategory;8],
 class_30: [std::option::Option<usize>;59],
 class_31: [(std::option::Option<usize>, std::option::Option<usize>);2],
 class_32: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket;2],
 class_33: [std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_34: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;20],
 class_35: [(PartialInstance,Result<(),SwiftRunFailure>);2],
 class_36: [Vec<Value>;2],
 class_37: [super::control::ReservationTicket;13],
 class_38: [Vec<Control>;2],
 class_39: [Vec<SwiftFrame>;2],
 class_40: [Vec<u8>;2],
 class_41: [Vec<Option<u32>>;2],
 class_42: [SwiftExecutionState;3],
 class_43: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage;1],
 class_44: [&'static crate::experimental_swift_reactor::control::SwiftReservations;2],
 class_45: [crate::experimental_swift_reactor::control::SwiftReservationCategory;18],
 class_46: [(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>);1],
 class_47: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage;11],
 class_48: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations;2],
 class_49: [super::control::Work;1],
 class_50: [(u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource);1],
 class_51: [std::option::Option<u64>;3],
 class_52: [(&'static u64,);3],
 class_53: [&'static u64;3],
 class_54: [(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind);3],
 class_55: [&'static super::control::RuntimeControl;1],
 class_56: [super::control::Live;8],
 class_57: [crate::experimental_swift_reactor::control::SwiftReservationUsage;8],
 class_58: [u32;35],
 class_59: [&'static crate::experimental_swift_reactor::control::RuntimeControl;8],
 class_60: [(&'static usize,);12],
 class_61: [&'static usize;19],
 class_62: [super::control::SwiftCleanupInvariant;2],
 class_63: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant;1],
 class_64: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>;2],
 class_65: [crate::experimental_swift_reactor::control::Cursor;128],
 class_66: [crate::experimental_swift_reactor::control::SwiftRunStage;1],
 class_67: [std::option::Option<u32>;5],
 class_68: [(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize);1],
 class_69: [ConstructionCleanupTail;2],
 class_70: [(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>);3],
 class_71: [crate::experimental_swift_reactor::execution::ExecutionCleanupTail;5],
 class_72: [crate::experimental_swift_reactor::execution::HeaderCompletionParts;1],
 class_73: [std::option::Option<[usize; 6]>;3],
 class_74: [[usize; 6];2],
 class_75: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>;6],
 class_76: [Option<std::convert::Infallible>;6],
 class_77: [&'static AccountedWasi;38],
 class_78: [crate::experimental_swift_reactor::control::Work;2],
 class_79: [std::option::Option<crate::experimental_wasi::WasiUsage>;67],
 class_80: [crate::experimental_wasi::WasiUsage;29],
 class_81: [crate::experimental_swift_reactor::execution::SwiftExecutionState;11],
 class_82: [std::vec::Vec<u8>;5],
 class_83: [std::vec::Vec<std::option::Option<u32>>;5],
 class_84: [std::vec::Vec<Value>;10],
 class_85: [std::vec::Vec<crate::experimental::execution::Control>;5],
 class_86: [std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>;5],
 class_87: [[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6];1],
 class_88: [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;19],
 class_89: [&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState;6],
 class_90: [&'static mut SwiftExecutionState;2],
 class_91: [&'static mut std::vec::Vec<Value>;14],
 class_92: [&'static mut std::vec::Vec<crate::experimental::execution::Control>;6],
 class_93: [&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>;6],
 class_94: [&'static mut std::vec::Vec<u8>;10],
 class_95: [&'static mut std::vec::Vec<std::option::Option<u32>>;10],
 class_96: [std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_97: [&'static mut ExecutionConstructionPhase<'static>;22],
 class_98: [&'static mut bool;2],
 class_99: [crate::experimental_swift_reactor::execution::PartialState;1],
 class_100: [&'static mut crate::experimental_swift_reactor::execution::PartialState;2],
 class_101: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl;159],
 class_102: [&'static crate::experimental_wasi::accounted::AccountedWasi;143],
 class_103: [&'static mut PartialState;1],
 class_104: [crate::experimental_swift_reactor::control::SwiftRunBudget;1],
 class_105: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>;1],
 class_106: [std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_107: [std::option::Option<crate::experimental::descriptors::MemoryExecutionView>;2],
 class_108: [&'static crate::experimental::swift::ValidatedSwiftReactor;30],
 class_109: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor);33],
 class_110: [&'static crate::experimental_swift_reactor::control::Cursor;36],
 class_111: [crate::experimental::descriptors::MemoryExecutionView;1],
 class_112: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>;1],
 class_113: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>;1],
 class_114: [std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_115: [std::option::Option<crate::experimental::descriptors::TableExecutionView>;2],
 class_116: [crate::experimental::descriptors::TableExecutionView;1],
 class_117: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>;1],
 class_118: [std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_119: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>;3],
 class_120: [std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>;8],
 class_121: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>;7],
 class_122: [&'static std::vec::Vec<u8>;10],
 class_123: [std::ops::Range<u32>;4],
 class_124: [&'static mut std::ops::Range<u32>;2],
 class_125: [std::ops::Range<usize>;28],
 class_126: [&'static mut std::ops::Range<usize>;12],
 class_127: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>;1],
 class_128: [std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_129: [std::option::Option<crate::experimental::descriptors::GlobalView<'static>>;2],
 class_130: [crate::experimental::descriptors::GlobalView<'static>;1],
 class_131: [crate::experimental_swift_reactor::execution::ScalarReader<'static>;2],
 class_132: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>;1],
 class_133: [std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_134: [&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>;16],
 class_135: [Type;5],
 class_136: [Value;7],
 class_137: [crate::experimental_swift_reactor::control::Live;4],
 class_138: [&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache;30],
 class_139: [&'static [u8];14],
 class_140: [u8;21],
 class_141: [&'static mut Vec<Value>;2],
 class_142: [std::result::Result<(), std::collections::TryReserveError>;10],
 class_143: [(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor);15],
 class_144: [&'static std::vec::Vec<Value>;2],
 class_145: [&'static mut Vec<Control>;2],
 class_146: [&'static std::vec::Vec<Control>;2],
 class_147: [&'static mut Vec<SwiftFrame>;2],
 class_148: [&'static std::vec::Vec<SwiftFrame>;2],
 class_149: [&'static mut Vec<u8>;2],
 class_150: [&'static mut Vec<Option<u32>>;2],
 class_151: [&'static std::vec::Vec<Option<u32>>;2],
 class_152: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>;4],
 class_153: [std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;8],
 class_154: [std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>;8],
 class_155: [crate::experimental::descriptors::SegmentExecutionView<'static>;7],
 class_156: [&'static std::vec::Vec<std::option::Option<u32>>;2],
 class_157: [&'static mut [u8];2],
 class_158: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>;1],
 class_159: [std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_160: [&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>;2],
 class_161: [std::option::Option<crate::experimental::descriptors::SignatureView<'static>>;1],
 class_162: [&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>;24],
 class_163: [&'static mut std::option::Option<u32>;1],
 class_164: [SegmentExecutionView<'static>;3],
 class_165: [ExecutionConstructionPhase<'static>;1],
 class_166: [std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>;15],
 class_167: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>;7],
 class_168: [std::option::Option<u8>;2],
 class_169: [std::option::Option<&'static u8>;2],
 class_170: [(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor);3],
 class_171: [std::iter::StepBy<std::ops::Range<i32>>;4],
 class_172: [std::ops::Range<i32>;2],
 class_173: [std::option::Option<i32>;1],
 class_174: [&'static mut std::iter::StepBy<std::ops::Range<i32>>;2],
 class_175: [i32;2],
 class_176: [std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>;5],
 class_177: [(u32, bool);3],
 class_178: [i64;3],
 class_179: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>;2],
 class_180: [[u8; 4];3],
 class_181: [std::slice::IterMut<'static, u8>;4],
 class_182: [&'static mut [u8; 4];2],
 class_183: [std::option::Option<&'static mut u8>;2],
 class_184: [&'static mut std::slice::IterMut<'static, u8>;4],
 class_185: [&'static mut u8;2],
 class_186: [[u8; 8];3],
 class_187: [&'static mut [u8; 8];2],
 class_188: [&'static Type;4],
 class_189: [std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>;1],
 class_190: [&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>;3],
 class_191: [WasiGrants;4],
 class_192: [WasiBudget;4],
 class_193: [Instant;4],
 class_194: [&'static mut crate::experimental_swift_reactor::control::AdoptedProof;1],
 class_195: [&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof);1],
 class_196: [std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>;2],
 class_197: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>;2],
 class_198: [std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>;4],
 class_199: [&'static crate::experimental_swift_reactor::control::AdoptedProof;6],
 class_200: [std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>;6],
 class_201: [crate::experimental_swift_reactor::control::SwiftRunUsage;1],
 class_202: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>;1],
 class_203: [std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>;2],
 class_204: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor);3],
 class_205: [crate::experimental_swift_reactor::control::RuntimeControl;4],
 class_206: [crate::experimental_swift_reactor::control::AdoptedProof;7],
 class_207: [(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof);1],
 class_208: [std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>;2],
 class_209: [crate::experimental_swift_reactor::execution::PartialInstance;6],
 class_210: [std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>;4],
 class_211: [std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;5],
 class_212: [std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;4],
 class_213: [std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>;4],
 class_214: [&'static mut crate::experimental_swift_reactor::execution::PartialInstance;2],
 class_215: [crate::experimental_swift_reactor::execution::ConstructionFailure;2],
 class_216: [crate::experimental_swift_reactor::execution::ConstructionCleanupTail;4],
 class_217: [crate::experimental_swift_reactor::execution::SwiftReactorInstance;4],
 class_218: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>;8],
 class_219: [&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;6],
 class_220: [&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;4],
 class_221: [&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>;4],
 class_222: [crate::experimental_swift_reactor::execution::Lifecycle;1],
 class_223: [std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>;4],
 class_224: [(crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>);2],
 class_225: [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>;12],
 class_226: [&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;10],
 class_227: [SwiftReactorInstance;1],
 class_228: [super::control::SwiftRunFailure;2],
 class_229: [std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>;2],
 class_230: [std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>;4],
 class_231: [std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>;3],
 class_232: [&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>;2],
 class_233: [&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>;2],
 class_234: [(std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>, std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>);2],
 class_235: [&'static mut PartialInstance;1],
 class_236: [super::control::AdoptedProof;1],
 class_237: [std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_238: [crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>;3],
 class_239: [std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>;5],
 class_240: [std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>;2],
 class_241: [&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>;2],
 class_242: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;9],
 class_243: [&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>;2],
 class_244: [crate::experimental_swift_reactor::cache::SwiftFunctionCache;1],
 class_245: [crate::experimental_swift_reactor::cache::CacheConstructionFailure;1],
 class_246: [&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>;2],
 class_247: [crate::experimental_wasi::accounted::WasiConstructionPhase<'static>;6],
 class_248: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>;1],
 class_249: [std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_250: [std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>;3],
 class_251: [std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_252: [&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>;2],
 class_253: [&'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>;2],
 class_254: [crate::experimental_wasi::accounted::AccountedWasi;3],
 class_255: [crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>;4],
 class_256: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>;1],
 class_257: [std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_258: [std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>;2],
 class_259: [&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;4],
 class_260: [std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>;5],
 class_261: [&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>;2],
 class_262: [&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>;2],
 class_263: [PartialInstance;1],
 class_264: [std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_265: [crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>;2],
 class_266: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_267: [&'static SwiftFunctionCache;1],
 class_268: [&'static super::control::AdoptedProof;1],
 class_269: [&'static mut ();1],
 class_270: [std::collections::TryReserveError;5],
 class_271: [Result<SwiftReactorInstance,ConstructionFailure>;2],
 class_272: [Option<Result<SwiftReactorInstance,ConstructionFailure>>;2],
 class_273: [ConstructionFailure;1],
}
pub(crate)const CONSTRUCTION_POSITIVE_ACTIVE_BYTES:usize=std::mem::size_of::<ConstructionPositiveActive>();
#[allow(dead_code)]
pub(crate) struct ConstructionPositiveCleanup{
 class_0: [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>;21],
 class_1: [&'static mut super::control::RuntimeControl;26],
 class_2: [Vec<Value>;2],
 class_3: [super::control::ReservationTicket;11],
 class_4: [Option<WasiUsage>;17],
 class_5: [();16],
 class_6: [Vec<Control>;2],
 class_7: [Vec<SwiftFrame>;2],
 class_8: [Vec<u8>;2],
 class_9: [Vec<Option<u32>>;2],
 class_10: [bool;22],
 class_11: [u64;3],
 class_12: [crate::experimental_swift_reactor::control::SwiftRunFailure;8],
 class_13: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant;6],
 class_14: [std::option::Option<usize>;6],
 class_15: [usize;35],
 class_16: [&'static crate::experimental_swift_reactor::control::SwiftReservationUsage;1],
 class_17: [&'static crate::experimental_swift_reactor::control::SwiftReservations;2],
 class_18: [crate::experimental_swift_reactor::control::SwiftReservationCategory;4],
 class_19: [(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>);1],
 class_20: [isize;20],
 class_21: [&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage;10],
 class_22: [&'static mut crate::experimental_swift_reactor::control::SwiftReservations;2],
 class_23: [&'static str;20],
 class_24: [(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind);2],
 class_25: [&'static super::control::RuntimeControl;1],
 class_26: [super::control::Live;5],
 class_27: [crate::experimental_swift_reactor::control::SwiftReservationUsage;7],
 class_28: [crate::experimental_swift_reactor::control::SwiftRunResource;6],
 class_29: [crate::experimental_swift_reactor::control::SwiftRunFailureKind;14],
 class_30: [u32;1],
 class_31: [&'static crate::experimental_swift_reactor::control::RuntimeControl;2],
 class_32: [super::control::SwiftCleanupInvariant;2],
 class_33: [&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant;1],
 class_34: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>;2],
 class_35: [crate::experimental_swift_reactor::control::Cursor;17],
 class_36: [crate::experimental_swift_reactor::control::SwiftRunStage;2],
 class_37: [std::option::Option<u32>;2],
 class_38: [crate::experimental_swift_reactor::control::Fault;2],
 class_39: [&'static mut SwiftExecutionState;1],
 class_40: [&'static AccountedWasi;7],
 class_41: [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;7],
 class_42: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;14],
 class_43: [crate::experimental_swift_reactor::control::ReservationTicket;12],
 class_44: [std::vec::Vec<Value>;8],
 class_45: [&'static mut std::vec::Vec<Value>;8],
 class_46: [std::option::Option<crate::experimental_wasi::WasiUsage>;20],
 class_47: [crate::experimental_wasi::WasiUsage;11],
 class_48: [std::vec::Vec<crate::experimental::execution::Control>;4],
 class_49: [&'static mut std::vec::Vec<crate::experimental::execution::Control>;4],
 class_50: [std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>;4],
 class_51: [&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>;4],
 class_52: [std::vec::Vec<u8>;4],
 class_53: [&'static mut std::vec::Vec<u8>;4],
 class_54: [std::vec::Vec<std::option::Option<u32>>;4],
 class_55: [&'static mut std::vec::Vec<std::option::Option<u32>>;4],
 class_56: [std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_57: [&'static mut Option<SwiftReactorInstance>;3],
 class_58: [&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance;1],
 class_59: [std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance>;2],
 class_60: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl;20],
 class_61: [std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>;2],
 class_62: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>;4],
 class_63: [&'static crate::experimental_wasi::accounted::AccountedWasi;16],
 class_64: [std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>;6],
 class_65: [&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;2],
 class_66: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>;1],
 class_67: [std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_68: [std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>;12],
 class_69: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>;3],
 class_70: [&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache;4],
 class_71: [std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>;4],
 class_72: [&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;4],
 class_73: [&'static crate::experimental_swift_reactor::execution::SwiftExecutionState;1],
 class_74: [std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftExecutionState>;2],
 class_75: [&'static std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>;2],
 class_76: [std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, &'static crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_77: [std::result::Result<&'static crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>;4],
 class_78: [std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_79: [&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_80: [(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi);6],
 class_81: [&'static crate::experimental_swift_reactor::control::ReservationTicket;4],
 class_82: [std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>;2],
 class_83: [&'static [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6];2],
 class_84: [std::option::Option<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>;1],
 class_85: [&'static mut std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>;2],
 class_86: [&'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>;2],
 class_87: [&'static std::vec::Vec<Value>;2],
 class_88: [&'static std::vec::Vec<crate::experimental::execution::Control>;2],
 class_89: [crate::experimental_swift_reactor::cache::SwiftCacheUsage;1],
 class_90: [crate::experimental_swift_reactor::execution::SwiftReactorInstance;3],
 class_91: [std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>;2],
 class_92: [crate::experimental_swift_reactor::execution::Lifecycle;1],
 class_93: [crate::experimental_swift_reactor::control::RuntimeControl;2],
 class_94: [std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>;2],
 class_95: [crate::experimental_wasi::accounted::AccountedWasi;3],
 class_96: [std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;2],
 class_97: [&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>;2],
 class_98: [crate::experimental_swift_reactor::execution::SwiftExecutionState;3],
 class_99: [std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>;2],
 class_100: [&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>;2],
 class_101: [&'static std::vec::Vec<u8>;2],
 class_102: [&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState;2],
 class_103: [crate::experimental_swift_reactor::control::Live;2],
 class_104: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;7],
 class_105: [std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_106: [&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;4],
 class_107: [crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>;2],
 class_108: [std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>;2],
 class_109: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;2],
 class_110: [crate::experimental_swift_reactor::execution::ExecutionCleanupTail;1],
 class_111: [Result<SwiftReactorInstance,ConstructionFailure>;2],
 class_112: [Option<Result<SwiftReactorInstance,ConstructionFailure>>;2],
 class_113: [ConstructionFailure;1],
 class_114: [ConstructionCleanupTail;1],
 class_115: [(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>);1],
}
pub(crate)const CONSTRUCTION_POSITIVE_CLEANUP_BYTES:usize=std::mem::size_of::<ConstructionPositiveCleanup>();
#[allow(dead_code)]
pub(crate) struct ConstructionPositiveFinal{
 class_0: [std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>;4],
 class_1: [&'static mut super::control::RuntimeControl;7],
 class_2: [();9],
 class_3: [usize;16],
 class_4: [Option<WasiUsage>;7],
 class_5: [crate::experimental_swift_reactor::control::SwiftRunFailure;4],
 class_6: [crate::experimental_swift_reactor::control::SwiftCleanupInvariant;8],
 class_7: [&'static crate::experimental_swift_reactor::control::ReservationTicket;1],
 class_8: [std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>;1],
 class_9: [&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_10: [isize;4],
 class_11: [bool;5],
 class_12: [u64;2],
 class_13: [&'static crate::experimental_swift_reactor::control::SwiftReservationCategory;4],
 class_14: [std::option::Option<usize>;4],
 class_15: [(usize, bool);1],
 class_16: [(std::option::Option<usize>, std::option::Option<usize>);1],
 class_17: [&'static mut crate::experimental_swift_reactor::control::ReservationTicket;1],
 class_18: [std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_19: [&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;4],
 class_20: [&'static str;4],
 class_21: [super::control::ReservationTicket;2],
 class_22: [ConstructionCleanupTail;2],
 class_23: [(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>);2],
 class_24: [&'static mut Option<super::control::SwiftRunFailure>;1],
 class_25: [&'static mut Option<super::control::SwiftRunUsage>;1],
 class_26: [crate::experimental_swift_reactor::control::RuntimeControl;3],
 class_27: [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>;2],
 class_28: [std::option::Option<crate::experimental_wasi::WasiUsage>;5],
 class_29: [(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize);1],
 class_30: [&'static mut crate::experimental_swift_reactor::control::RuntimeControl;6],
 class_31: [crate::experimental_swift_reactor::control::ReservationTicket;2],
 class_32: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>;1],
 class_33: [std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>;1],
 class_34: [crate::experimental_swift_reactor::control::SwiftRunUsage;1],
}
pub(crate)const CONSTRUCTION_POSITIVE_FINAL_BYTES:usize=std::mem::size_of::<ConstructionPositiveFinal>();
// Unit-only engine-side hook call boundaries. Callback storage/Cell bodies are
// test harness instrumentation and are excluded, not production authority.
#[cfg(test)]
#[allow(dead_code)]
struct ConstructionPositiveTestHookArguments {
 checkpoint_reborrow: &'static RuntimeControl,
 checkpoint_argument: &'static RuntimeControl,
 checkpoint_callback_parameter: &'static RuntimeControl,
 checkpoint_cursor_argument: Cursor,
 checkpoint_cursor_callback_parameter: Cursor,
 checkpoint_call_return: (),
 checkpoint_callback_return: (),
 capacity_new_source: usize,
 capacity_argument: usize,
 capacity_callback_parameter: usize,
 capacity_callback_return: usize,
 restore_new_source: usize,
 restore_argument: usize,
 restore_callback_parameter: usize,
 restore_callback_return: usize,
}
#[cfg(test)]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES:usize=std::mem::size_of::<ConstructionPositiveTestHookArguments>();
#[cfg(not(test))]
pub(super) const CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES:usize=0;


pub(crate)fn independent_positive_accounting_probe(){use std::mem::{size_of,align_of,offset_of,size_of_val,align_of_val};
println!("positiveclass|preflight|class_0|24|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_0),size_of::<bool>(),align_of::<bool>());
println!("positiveclass|preflight|class_1|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_1),size_of::<&'static crate::execute::Cancellation>(),align_of::<&'static crate::execute::Cancellation>());
println!("positiveclass|preflight|class_2|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_2),size_of::<&'static std::sync::atomic::AtomicBool>(),align_of::<&'static std::sync::atomic::AtomicBool>());
println!("positiveclass|preflight|class_3|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_3),size_of::<&'static std::sync::Arc<std::sync::atomic::AtomicBool>>(),align_of::<&'static std::sync::Arc<std::sync::atomic::AtomicBool>>());
println!("positiveclass|preflight|class_4|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_4),size_of::<std::sync::atomic::Ordering>(),align_of::<std::sync::atomic::Ordering>());
println!("positiveclass|preflight|class_5|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_5),size_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_6|37|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_6),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("positiveclass|preflight|class_7|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_7),size_of::<Option<&'static AccountedWasi>>(),align_of::<Option<&'static AccountedWasi>>());
println!("positiveclass|preflight|class_8|38|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_8),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("positiveclass|preflight|class_9|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_9),size_of::<std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|preflight|class_10|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_10),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|preflight|class_11|8|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_11),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("positiveclass|preflight|class_12|28|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_12),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|preflight|class_13|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_13),size_of::<&'static CacheControl<'static>>(),align_of::<&'static CacheControl<'static>>());
println!("positiveclass|preflight|class_14|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_14),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|preflight|class_15|19|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_15),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("positiveclass|preflight|class_16|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_16),size_of::<&'static mut CacheControl<'static>>(),align_of::<&'static mut CacheControl<'static>>());
println!("positiveclass|preflight|class_17|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_17),size_of::<crate::experimental::cache::CacheFailureKind>(),align_of::<crate::experimental::cache::CacheFailureKind>());
println!("positiveclass|preflight|class_18|21|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_18),size_of::<&'static str>(),align_of::<&'static str>());
println!("positiveclass|preflight|class_19|27|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_19),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("positiveclass|preflight|class_20|24|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_20),size_of::<isize>(),align_of::<isize>());
println!("positiveclass|preflight|class_21|14|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("positiveclass|preflight|class_22|28|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_22),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("positiveclass|preflight|class_23|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_23),size_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("positiveclass|preflight|class_24|17|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_24),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|preflight|class_25|24|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_25),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_26|7|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_26),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("positiveclass|preflight|class_27|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_27),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>>());
println!("positiveclass|preflight|class_28|22|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_28),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_29|9|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_29),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|preflight|class_30|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_30),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|preflight|class_31|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_31),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|preflight|class_32|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_32),size_of::<&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("positiveclass|preflight|class_33|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_33),size_of::<crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("positiveclass|preflight|class_34|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_34),size_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>(),align_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>());
println!("positiveclass|preflight|class_35|11|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_35),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|preflight|class_36|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_36),size_of::<&'static super::control::SwiftReservations>(),align_of::<&'static super::control::SwiftReservations>());
println!("positiveclass|preflight|class_37|8|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_37),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("positiveclass|preflight|class_38|10|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_38),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|preflight|class_39|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_39),size_of::<&'static mut super::control::SwiftReservations>(),align_of::<&'static mut super::control::SwiftReservations>());
println!("positiveclass|preflight|class_40|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_40),size_of::<super::control::SwiftRunFailureKind>(),align_of::<super::control::SwiftRunFailureKind>());
println!("positiveclass|preflight|class_41|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_41),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("positiveclass|preflight|class_42|24|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_42),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("positiveclass|preflight|class_43|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_43),size_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>());
println!("positiveclass|preflight|class_44|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_44),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("positiveclass|preflight|class_45|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_45),size_of::<super::control::Fault>(),align_of::<super::control::Fault>());
println!("positiveclass|preflight|class_46|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_46),size_of::<super::control::SwiftRunResource>(),align_of::<super::control::SwiftRunResource>());
println!("positiveclass|preflight|class_47|32|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_47),size_of::<u64>(),align_of::<u64>());
println!("positiveclass|preflight|class_48|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_48),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("positiveclass|preflight|class_49|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_49),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("positiveclass|preflight|class_50|18|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_50),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("positiveclass|preflight|class_51|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_51),size_of::<std::time::Instant>(),align_of::<std::time::Instant>());
println!("positiveclass|preflight|class_52|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_52),size_of::<crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|preflight|class_53|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_53),size_of::<crate::experimental_swift_reactor::control::SwiftLiveUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftLiveUsage>());
println!("positiveclass|preflight|class_54|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_54),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("positiveclass|preflight|class_55|5|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_55),size_of::<std::time::Duration>(),align_of::<std::time::Duration>());
println!("positiveclass|preflight|class_56|8|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_56),size_of::<&'static std::time::Instant>(),align_of::<&'static std::time::Instant>());
println!("positiveclass|preflight|class_57|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_57),size_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>(),align_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>());
println!("positiveclass|preflight|class_58|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_58),size_of::<crate::experimental::swift::SwiftValidationUsage>(),align_of::<crate::experimental::swift::SwiftValidationUsage>());
println!("positiveclass|preflight|class_59|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_59),size_of::<crate::experimental_swift_reactor::control::SwiftRunStage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunStage>());
println!("positiveclass|preflight|class_60|10|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_60),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|preflight|class_61|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_61),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("positiveclass|preflight|class_62|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_62),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_63|59|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_63),size_of::<usize>(),align_of::<usize>());
println!("positiveclass|preflight|class_64|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_64),size_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_65|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_65),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|preflight|class_66|12|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_66),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("positiveclass|preflight|class_67|8|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_67),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("positiveclass|preflight|class_68|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_68),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("positiveclass|preflight|class_69|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_69),size_of::<(usize, usize)>(),align_of::<(usize, usize)>());
println!("positiveclass|preflight|class_70|5|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_70),size_of::<()>(),align_of::<()>());
println!("positiveclass|preflight|class_71|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_71),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|preflight|class_72|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_72),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|preflight|class_73|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_73),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("positiveclass|preflight|class_74|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_74),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_75|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_75),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>());
println!("positiveclass|preflight|class_76|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_76),size_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|preflight|class_77|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_77),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>());
println!("positiveclass|preflight|class_78|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_78),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("positiveclass|preflight|class_79|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_79),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("positiveclass|preflight|class_80|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_80),size_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|preflight|class_81|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_81),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|preflight|class_82|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_82),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|preflight|class_83|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_83),size_of::<&'static super::control::AdoptedProof>(),align_of::<&'static super::control::AdoptedProof>());
println!("positiveclass|preflight|class_84|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_84),size_of::<&'static super::control::ReservationTicket>(),align_of::<&'static super::control::ReservationTicket>());
println!("positiveclass|preflight|class_85|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_85),size_of::<std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>>(),align_of::<std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>>());
println!("positiveclass|preflight|class_86|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_86),size_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>());
println!("positiveclass|preflight|class_87|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_87),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|preflight|class_88|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_88),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|preflight|class_89|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_89),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("positiveclass|preflight|class_90|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_90),size_of::<std::result::Result<u64, std::num::TryFromIntError>>(),align_of::<std::result::Result<u64, std::num::TryFromIntError>>());
println!("positiveclass|preflight|class_91|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_91),size_of::<u128>(),align_of::<u128>());
println!("positiveclass|preflight|class_92|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_92),size_of::<&'static std::time::Duration>(),align_of::<&'static std::time::Duration>());
println!("positiveclass|preflight|class_93|16|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_93),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("positiveclass|preflight|class_94|9|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_94),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("positiveclass|preflight|class_95|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_95),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_96|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_96),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|preflight|class_97|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_97),size_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|preflight|class_98|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_98),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|preflight|class_99|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_99),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("positiveclass|preflight|class_100|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_100),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|preflight|class_101|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_101),size_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>(),align_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>());
println!("positiveclass|preflight|class_102|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_102),size_of::<WasiGrants>(),align_of::<WasiGrants>());
println!("positiveclass|preflight|class_103|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_103),size_of::<WasiBudget>(),align_of::<WasiBudget>());
println!("positiveclass|preflight|class_104|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_104),size_of::<Instant>(),align_of::<Instant>());
println!("positiveclass|preflight|class_105|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_105),size_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>());
println!("positiveclass|preflight|class_106|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_106),size_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("positiveclass|preflight|class_107|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_107),size_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("positiveclass|preflight|class_108|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_108),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>>());
println!("positiveclass|preflight|class_109|4|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_109),size_of::<std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|preflight|class_110|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_110),size_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>());
println!("positiveclass|preflight|class_111|6|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_111),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|preflight|class_112|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_112),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>>());
println!("positiveclass|preflight|class_113|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_113),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|preflight|class_114|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_114),size_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("positiveclass|preflight|class_115|7|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_115),size_of::<&'static crate::experimental_wasi::WasiContext>(),align_of::<&'static crate::experimental_wasi::WasiContext>());
println!("positiveclass|preflight|class_116|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_116),size_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>(),align_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>());
println!("positiveclass|preflight|class_117|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_117),size_of::<crate::experimental_swift_reactor::execution::ConstructionFailure>(),align_of::<crate::experimental_swift_reactor::execution::ConstructionFailure>());
println!("positiveclass|preflight|class_118|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_118),size_of::<super::control::SwiftRunFailure>(),align_of::<super::control::SwiftRunFailure>());
println!("positiveclass|preflight|class_119|3|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_119),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("positiveclass|preflight|class_120|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_120),size_of::<Result<SwiftReactorInstance,ConstructionFailure>>(),align_of::<Result<SwiftReactorInstance,ConstructionFailure>>());
println!("positiveclass|preflight|class_121|2|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_121),size_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>(),align_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>());
println!("positiveclass|preflight|class_122|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_122),size_of::<ConstructionFailure>(),align_of::<ConstructionFailure>());
println!("positiveclass|preflight|class_123|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_123),size_of::<ConstructionCleanupTail>(),align_of::<ConstructionCleanupTail>());
println!("positiveclass|preflight|class_124|1|{}|{}|{}",offset_of!(ConstructionPositivePreflight,class_124),size_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>(),align_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>());
println!("positiveclass|active|class_0|15|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_0),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_1|84|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("positiveclass|active|class_2|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("positiveclass|active|class_3|319|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_3),size_of::<usize>(),align_of::<usize>());
println!("positiveclass|active|class_4|47|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("positiveclass|active|class_5|42|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("positiveclass|active|class_6|48|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_6),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_7|138|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_7),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_8|135|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_8),size_of::<isize>(),align_of::<isize>());
println!("positiveclass|active|class_9|160|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_10|89|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_10),size_of::<bool>(),align_of::<bool>());
println!("positiveclass|active|class_11|60|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_11),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("positiveclass|active|class_12|39|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_12),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("positiveclass|active|class_13|36|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_13),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("positiveclass|active|class_14|17|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_14),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("positiveclass|active|class_15|48|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_15),size_of::<u64>(),align_of::<u64>());
println!("positiveclass|active|class_16|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_16),size_of::<(u64, bool)>(),align_of::<(u64, bool)>());
println!("positiveclass|active|class_17|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_17),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>());
println!("positiveclass|active|class_18|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_18),size_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_19|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_19),size_of::<(usize, usize)>(),align_of::<(usize, usize)>());
println!("positiveclass|active|class_20|29|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_20),size_of::<()>(),align_of::<()>());
println!("positiveclass|active|class_21|25|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_21),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("positiveclass|active|class_22|22|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_22),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|active|class_23|51|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_23),size_of::<&'static str>(),align_of::<&'static str>());
println!("positiveclass|active|class_24|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_24),size_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>(),align_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>());
println!("positiveclass|active|class_25|22|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_25),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|active|class_26|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_26),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|active|class_27|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_27),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_28|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_28),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_29|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_29),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("positiveclass|active|class_30|59|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_30),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("positiveclass|active|class_31|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_31),size_of::<(std::option::Option<usize>, std::option::Option<usize>)>(),align_of::<(std::option::Option<usize>, std::option::Option<usize>)>());
println!("positiveclass|active|class_32|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_32),size_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|active|class_33|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_33),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_34|20|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_34),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_35|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_35),size_of::<(PartialInstance,Result<(),SwiftRunFailure>)>(),align_of::<(PartialInstance,Result<(),SwiftRunFailure>)>());
println!("positiveclass|active|class_36|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_36),size_of::<Vec<Value>>(),align_of::<Vec<Value>>());
println!("positiveclass|active|class_37|13|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_37),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("positiveclass|active|class_38|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_38),size_of::<Vec<Control>>(),align_of::<Vec<Control>>());
println!("positiveclass|active|class_39|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_39),size_of::<Vec<SwiftFrame>>(),align_of::<Vec<SwiftFrame>>());
println!("positiveclass|active|class_40|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_40),size_of::<Vec<u8>>(),align_of::<Vec<u8>>());
println!("positiveclass|active|class_41|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_41),size_of::<Vec<Option<u32>>>(),align_of::<Vec<Option<u32>>>());
println!("positiveclass|active|class_42|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_42),size_of::<SwiftExecutionState>(),align_of::<SwiftExecutionState>());
println!("positiveclass|active|class_43|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_43),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|active|class_44|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_44),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|active|class_45|18|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_45),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("positiveclass|active|class_46|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_46),size_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>(),align_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>());
println!("positiveclass|active|class_47|11|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_47),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|active|class_48|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_48),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|active|class_49|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_49),size_of::<super::control::Work>(),align_of::<super::control::Work>());
println!("positiveclass|active|class_50|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_50),size_of::<(u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource)>(),align_of::<(u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource)>());
println!("positiveclass|active|class_51|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_51),size_of::<std::option::Option<u64>>(),align_of::<std::option::Option<u64>>());
println!("positiveclass|active|class_52|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_52),size_of::<(&'static u64,)>(),align_of::<(&'static u64,)>());
println!("positiveclass|active|class_53|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_53),size_of::<&'static u64>(),align_of::<&'static u64>());
println!("positiveclass|active|class_54|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_54),size_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>());
println!("positiveclass|active|class_55|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_55),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("positiveclass|active|class_56|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_56),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("positiveclass|active|class_57|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_57),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|active|class_58|35|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_58),size_of::<u32>(),align_of::<u32>());
println!("positiveclass|active|class_59|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_59),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|active|class_60|12|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_60),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("positiveclass|active|class_61|19|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_61),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("positiveclass|active|class_62|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_62),size_of::<super::control::SwiftCleanupInvariant>(),align_of::<super::control::SwiftCleanupInvariant>());
println!("positiveclass|active|class_63|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_63),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|active|class_64|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_64),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("positiveclass|active|class_65|128|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_65),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("positiveclass|active|class_66|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_66),size_of::<crate::experimental_swift_reactor::control::SwiftRunStage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunStage>());
println!("positiveclass|active|class_67|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_67),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("positiveclass|active|class_68|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_68),size_of::<(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize)>(),align_of::<(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize)>());
println!("positiveclass|active|class_69|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_69),size_of::<ConstructionCleanupTail>(),align_of::<ConstructionCleanupTail>());
println!("positiveclass|active|class_70|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_70),size_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>(),align_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>());
println!("positiveclass|active|class_71|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_71),size_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>());
println!("positiveclass|active|class_72|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_72),size_of::<crate::experimental_swift_reactor::execution::HeaderCompletionParts>(),align_of::<crate::experimental_swift_reactor::execution::HeaderCompletionParts>());
println!("positiveclass|active|class_73|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_73),size_of::<std::option::Option<[usize; 6]>>(),align_of::<std::option::Option<[usize; 6]>>());
println!("positiveclass|active|class_74|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_74),size_of::<[usize; 6]>(),align_of::<[usize; 6]>());
println!("positiveclass|active|class_75|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_75),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("positiveclass|active|class_76|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_76),size_of::<Option<std::convert::Infallible>>(),align_of::<Option<std::convert::Infallible>>());
println!("positiveclass|active|class_77|38|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_77),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("positiveclass|active|class_78|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_78),size_of::<crate::experimental_swift_reactor::control::Work>(),align_of::<crate::experimental_swift_reactor::control::Work>());
println!("positiveclass|active|class_79|67|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_79),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|active|class_80|29|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_80),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("positiveclass|active|class_81|11|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_81),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("positiveclass|active|class_82|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_82),size_of::<std::vec::Vec<u8>>(),align_of::<std::vec::Vec<u8>>());
println!("positiveclass|active|class_83|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_83),size_of::<std::vec::Vec<std::option::Option<u32>>>(),align_of::<std::vec::Vec<std::option::Option<u32>>>());
println!("positiveclass|active|class_84|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_84),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("positiveclass|active|class_85|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_85),size_of::<std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<std::vec::Vec<crate::experimental::execution::Control>>());
println!("positiveclass|active|class_86|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_86),size_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("positiveclass|active|class_87|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_87),size_of::<[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>(),align_of::<[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>());
println!("positiveclass|active|class_88|19|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_88),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_89|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_89),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("positiveclass|active|class_90|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_90),size_of::<&'static mut SwiftExecutionState>(),align_of::<&'static mut SwiftExecutionState>());
println!("positiveclass|active|class_91|14|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_91),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("positiveclass|active|class_92|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_92),size_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>());
println!("positiveclass|active|class_93|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_93),size_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("positiveclass|active|class_94|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_94),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("positiveclass|active|class_95|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_95),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("positiveclass|active|class_96|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_96),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_97|22|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_97),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("positiveclass|active|class_98|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_98),size_of::<&'static mut bool>(),align_of::<&'static mut bool>());
println!("positiveclass|active|class_99|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_99),size_of::<crate::experimental_swift_reactor::execution::PartialState>(),align_of::<crate::experimental_swift_reactor::execution::PartialState>());
println!("positiveclass|active|class_100|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_100),size_of::<&'static mut crate::experimental_swift_reactor::execution::PartialState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::PartialState>());
println!("positiveclass|active|class_101|159|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_101),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|active|class_102|143|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_102),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("positiveclass|active|class_103|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_103),size_of::<&'static mut PartialState>(),align_of::<&'static mut PartialState>());
println!("positiveclass|active|class_104|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_104),size_of::<crate::experimental_swift_reactor::control::SwiftRunBudget>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunBudget>());
println!("positiveclass|active|class_105|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_105),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>>());
println!("positiveclass|active|class_106|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_106),size_of::<std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_107|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_107),size_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>());
println!("positiveclass|active|class_108|30|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_108),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("positiveclass|active|class_109|33|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_109),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|active|class_110|36|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_110),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("positiveclass|active|class_111|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_111),size_of::<crate::experimental::descriptors::MemoryExecutionView>(),align_of::<crate::experimental::descriptors::MemoryExecutionView>());
println!("positiveclass|active|class_112|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_112),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("positiveclass|active|class_113|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_113),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>>());
println!("positiveclass|active|class_114|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_114),size_of::<std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_115|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_115),size_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>());
println!("positiveclass|active|class_116|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_116),size_of::<crate::experimental::descriptors::TableExecutionView>(),align_of::<crate::experimental::descriptors::TableExecutionView>());
println!("positiveclass|active|class_117|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_117),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>>());
println!("positiveclass|active|class_118|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_118),size_of::<std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_119|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_119),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("positiveclass|active|class_120|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_120),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_121|7|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_121),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|active|class_122|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_122),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("positiveclass|active|class_123|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_123),size_of::<std::ops::Range<u32>>(),align_of::<std::ops::Range<u32>>());
println!("positiveclass|active|class_124|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_124),size_of::<&'static mut std::ops::Range<u32>>(),align_of::<&'static mut std::ops::Range<u32>>());
println!("positiveclass|active|class_125|28|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_125),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("positiveclass|active|class_126|12|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_126),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("positiveclass|active|class_127|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_127),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>>());
println!("positiveclass|active|class_128|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_128),size_of::<std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_129|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_129),size_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>());
println!("positiveclass|active|class_130|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_130),size_of::<crate::experimental::descriptors::GlobalView<'static>>(),align_of::<crate::experimental::descriptors::GlobalView<'static>>());
println!("positiveclass|active|class_131|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_131),size_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("positiveclass|active|class_132|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_132),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>>());
println!("positiveclass|active|class_133|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_133),size_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_134|16|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_134),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("positiveclass|active|class_135|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_135),size_of::<Type>(),align_of::<Type>());
println!("positiveclass|active|class_136|7|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_136),size_of::<Value>(),align_of::<Value>());
println!("positiveclass|active|class_137|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_137),size_of::<crate::experimental_swift_reactor::control::Live>(),align_of::<crate::experimental_swift_reactor::control::Live>());
println!("positiveclass|active|class_138|30|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_138),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("positiveclass|active|class_139|14|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_139),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("positiveclass|active|class_140|21|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_140),size_of::<u8>(),align_of::<u8>());
println!("positiveclass|active|class_141|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_141),size_of::<&'static mut Vec<Value>>(),align_of::<&'static mut Vec<Value>>());
println!("positiveclass|active|class_142|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_142),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("positiveclass|active|class_143|15|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_143),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|active|class_144|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_144),size_of::<&'static std::vec::Vec<Value>>(),align_of::<&'static std::vec::Vec<Value>>());
println!("positiveclass|active|class_145|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_145),size_of::<&'static mut Vec<Control>>(),align_of::<&'static mut Vec<Control>>());
println!("positiveclass|active|class_146|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_146),size_of::<&'static std::vec::Vec<Control>>(),align_of::<&'static std::vec::Vec<Control>>());
println!("positiveclass|active|class_147|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_147),size_of::<&'static mut Vec<SwiftFrame>>(),align_of::<&'static mut Vec<SwiftFrame>>());
println!("positiveclass|active|class_148|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_148),size_of::<&'static std::vec::Vec<SwiftFrame>>(),align_of::<&'static std::vec::Vec<SwiftFrame>>());
println!("positiveclass|active|class_149|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_149),size_of::<&'static mut Vec<u8>>(),align_of::<&'static mut Vec<u8>>());
println!("positiveclass|active|class_150|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_150),size_of::<&'static mut Vec<Option<u32>>>(),align_of::<&'static mut Vec<Option<u32>>>());
println!("positiveclass|active|class_151|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_151),size_of::<&'static std::vec::Vec<Option<u32>>>(),align_of::<&'static std::vec::Vec<Option<u32>>>());
println!("positiveclass|active|class_152|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_152),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("positiveclass|active|class_153|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_153),size_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_154|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_154),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("positiveclass|active|class_155|7|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_155),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("positiveclass|active|class_156|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_156),size_of::<&'static std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static std::vec::Vec<std::option::Option<u32>>>());
println!("positiveclass|active|class_157|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_157),size_of::<&'static mut [u8]>(),align_of::<&'static mut [u8]>());
println!("positiveclass|active|class_158|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_158),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>>());
println!("positiveclass|active|class_159|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_159),size_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_160|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_160),size_of::<&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>(),align_of::<&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>());
println!("positiveclass|active|class_161|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_161),size_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>());
println!("positiveclass|active|class_162|24|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_162),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("positiveclass|active|class_163|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_163),size_of::<&'static mut std::option::Option<u32>>(),align_of::<&'static mut std::option::Option<u32>>());
println!("positiveclass|active|class_164|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_164),size_of::<SegmentExecutionView<'static>>(),align_of::<SegmentExecutionView<'static>>());
println!("positiveclass|active|class_165|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_165),size_of::<ExecutionConstructionPhase<'static>>(),align_of::<ExecutionConstructionPhase<'static>>());
println!("positiveclass|active|class_166|15|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_166),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_167|7|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_167),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("positiveclass|active|class_168|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_168),size_of::<std::option::Option<u8>>(),align_of::<std::option::Option<u8>>());
println!("positiveclass|active|class_169|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_169),size_of::<std::option::Option<&'static u8>>(),align_of::<std::option::Option<&'static u8>>());
println!("positiveclass|active|class_170|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_170),size_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|active|class_171|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_171),size_of::<std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<std::iter::StepBy<std::ops::Range<i32>>>());
println!("positiveclass|active|class_172|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_172),size_of::<std::ops::Range<i32>>(),align_of::<std::ops::Range<i32>>());
println!("positiveclass|active|class_173|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_173),size_of::<std::option::Option<i32>>(),align_of::<std::option::Option<i32>>());
println!("positiveclass|active|class_174|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_174),size_of::<&'static mut std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<&'static mut std::iter::StepBy<std::ops::Range<i32>>>());
println!("positiveclass|active|class_175|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_175),size_of::<i32>(),align_of::<i32>());
println!("positiveclass|active|class_176|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_176),size_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_177|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_177),size_of::<(u32, bool)>(),align_of::<(u32, bool)>());
println!("positiveclass|active|class_178|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_178),size_of::<i64>(),align_of::<i64>());
println!("positiveclass|active|class_179|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_179),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>());
println!("positiveclass|active|class_180|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_180),size_of::<[u8; 4]>(),align_of::<[u8; 4]>());
println!("positiveclass|active|class_181|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_181),size_of::<std::slice::IterMut<'static, u8>>(),align_of::<std::slice::IterMut<'static, u8>>());
println!("positiveclass|active|class_182|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_182),size_of::<&'static mut [u8; 4]>(),align_of::<&'static mut [u8; 4]>());
println!("positiveclass|active|class_183|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_183),size_of::<std::option::Option<&'static mut u8>>(),align_of::<std::option::Option<&'static mut u8>>());
println!("positiveclass|active|class_184|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_184),size_of::<&'static mut std::slice::IterMut<'static, u8>>(),align_of::<&'static mut std::slice::IterMut<'static, u8>>());
println!("positiveclass|active|class_185|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_185),size_of::<&'static mut u8>(),align_of::<&'static mut u8>());
println!("positiveclass|active|class_186|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_186),size_of::<[u8; 8]>(),align_of::<[u8; 8]>());
println!("positiveclass|active|class_187|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_187),size_of::<&'static mut [u8; 8]>(),align_of::<&'static mut [u8; 8]>());
println!("positiveclass|active|class_188|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_188),size_of::<&'static Type>(),align_of::<&'static Type>());
println!("positiveclass|active|class_189|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_189),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|active|class_190|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_190),size_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>(),align_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>());
println!("positiveclass|active|class_191|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_191),size_of::<WasiGrants>(),align_of::<WasiGrants>());
println!("positiveclass|active|class_192|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_192),size_of::<WasiBudget>(),align_of::<WasiBudget>());
println!("positiveclass|active|class_193|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_193),size_of::<Instant>(),align_of::<Instant>());
println!("positiveclass|active|class_194|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_194),size_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>());
println!("positiveclass|active|class_195|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_195),size_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("positiveclass|active|class_196|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_196),size_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("positiveclass|active|class_197|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_197),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>>());
println!("positiveclass|active|class_198|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_198),size_of::<std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|active|class_199|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_199),size_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>());
println!("positiveclass|active|class_200|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_200),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|active|class_201|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_201),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("positiveclass|active|class_202|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_202),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::execution::ConstructionFailure>, usize>>());
println!("positiveclass|active|class_203|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_203),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::execution::ConstructionFailure>>());
println!("positiveclass|active|class_204|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_204),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("positiveclass|active|class_205|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_205),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|active|class_206|7|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_206),size_of::<crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<crate::experimental_swift_reactor::control::AdoptedProof>());
println!("positiveclass|active|class_207|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_207),size_of::<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("positiveclass|active|class_208|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_208),size_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("positiveclass|active|class_209|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_209),size_of::<crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<crate::experimental_swift_reactor::execution::PartialInstance>());
println!("positiveclass|active|class_210|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_210),size_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|active|class_211|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_211),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|active|class_212|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_212),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|active|class_213|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_213),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|active|class_214|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_214),size_of::<&'static mut crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::PartialInstance>());
println!("positiveclass|active|class_215|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_215),size_of::<crate::experimental_swift_reactor::execution::ConstructionFailure>(),align_of::<crate::experimental_swift_reactor::execution::ConstructionFailure>());
println!("positiveclass|active|class_216|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_216),size_of::<crate::experimental_swift_reactor::execution::ConstructionCleanupTail>(),align_of::<crate::experimental_swift_reactor::execution::ConstructionCleanupTail>());
println!("positiveclass|active|class_217|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_217),size_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("positiveclass|active|class_218|8|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_218),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|active|class_219|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_219),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|active|class_220|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_220),size_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|active|class_221|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_221),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|active|class_222|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_222),size_of::<crate::experimental_swift_reactor::execution::Lifecycle>(),align_of::<crate::experimental_swift_reactor::execution::Lifecycle>());
println!("positiveclass|active|class_223|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_223),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|active|class_224|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_224),size_of::<(crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>)>(),align_of::<(crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>)>());
println!("positiveclass|active|class_225|12|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_225),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|active|class_226|10|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_226),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|active|class_227|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_227),size_of::<SwiftReactorInstance>(),align_of::<SwiftReactorInstance>());
println!("positiveclass|active|class_228|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_228),size_of::<super::control::SwiftRunFailure>(),align_of::<super::control::SwiftRunFailure>());
println!("positiveclass|active|class_229|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_229),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>());
println!("positiveclass|active|class_230|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_230),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_231|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_231),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_232|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_232),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>());
println!("positiveclass|active|class_233|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_233),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_234|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_234),size_of::<(std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>, std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>)>(),align_of::<(std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>, std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>)>());
println!("positiveclass|active|class_235|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_235),size_of::<&'static mut PartialInstance>(),align_of::<&'static mut PartialInstance>());
println!("positiveclass|active|class_236|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_236),size_of::<super::control::AdoptedProof>(),align_of::<super::control::AdoptedProof>());
println!("positiveclass|active|class_237|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_237),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_238|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_238),size_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>());
println!("positiveclass|active|class_239|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_239),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("positiveclass|active|class_240|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_240),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>());
println!("positiveclass|active|class_241|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_241),size_of::<&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>());
println!("positiveclass|active|class_242|9|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_242),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_243|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_243),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("positiveclass|active|class_244|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_244),size_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("positiveclass|active|class_245|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_245),size_of::<crate::experimental_swift_reactor::cache::CacheConstructionFailure>(),align_of::<crate::experimental_swift_reactor::cache::CacheConstructionFailure>());
println!("positiveclass|active|class_246|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_246),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>>());
println!("positiveclass|active|class_247|6|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_247),size_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("positiveclass|active|class_248|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_248),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>>());
println!("positiveclass|active|class_249|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_249),size_of::<std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_250|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_250),size_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_251|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_251),size_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_252|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_252),size_of::<&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("positiveclass|active|class_253|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_253),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_254|3|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_254),size_of::<crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<crate::experimental_wasi::accounted::AccountedWasi>());
println!("positiveclass|active|class_255|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_255),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("positiveclass|active|class_256|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_256),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>>());
println!("positiveclass|active|class_257|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_257),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_258|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_258),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|active|class_259|4|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_259),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|active|class_260|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_260),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_261|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_261),size_of::<&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("positiveclass|active|class_262|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_262),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|active|class_263|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_263),size_of::<PartialInstance>(),align_of::<PartialInstance>());
println!("positiveclass|active|class_264|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_264),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_265|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_265),size_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>());
println!("positiveclass|active|class_266|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_266),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|active|class_267|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_267),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("positiveclass|active|class_268|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_268),size_of::<&'static super::control::AdoptedProof>(),align_of::<&'static super::control::AdoptedProof>());
println!("positiveclass|active|class_269|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_269),size_of::<&'static mut ()>(),align_of::<&'static mut ()>());
println!("positiveclass|active|class_270|5|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_270),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("positiveclass|active|class_271|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_271),size_of::<Result<SwiftReactorInstance,ConstructionFailure>>(),align_of::<Result<SwiftReactorInstance,ConstructionFailure>>());
println!("positiveclass|active|class_272|2|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_272),size_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>(),align_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>());
println!("positiveclass|active|class_273|1|{}|{}|{}",offset_of!(ConstructionPositiveActive,class_273),size_of::<ConstructionFailure>(),align_of::<ConstructionFailure>());
println!("positiveclass|cleanup|class_0|21|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_1|26|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("positiveclass|cleanup|class_2|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_2),size_of::<Vec<Value>>(),align_of::<Vec<Value>>());
println!("positiveclass|cleanup|class_3|11|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("positiveclass|cleanup|class_4|17|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("positiveclass|cleanup|class_5|16|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_5),size_of::<()>(),align_of::<()>());
println!("positiveclass|cleanup|class_6|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_6),size_of::<Vec<Control>>(),align_of::<Vec<Control>>());
println!("positiveclass|cleanup|class_7|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_7),size_of::<Vec<SwiftFrame>>(),align_of::<Vec<SwiftFrame>>());
println!("positiveclass|cleanup|class_8|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_8),size_of::<Vec<u8>>(),align_of::<Vec<u8>>());
println!("positiveclass|cleanup|class_9|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_9),size_of::<Vec<Option<u32>>>(),align_of::<Vec<Option<u32>>>());
println!("positiveclass|cleanup|class_10|22|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_10),size_of::<bool>(),align_of::<bool>());
println!("positiveclass|cleanup|class_11|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_11),size_of::<u64>(),align_of::<u64>());
println!("positiveclass|cleanup|class_12|8|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("positiveclass|cleanup|class_13|6|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_13),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|cleanup|class_14|6|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_14),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("positiveclass|cleanup|class_15|35|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_15),size_of::<usize>(),align_of::<usize>());
println!("positiveclass|cleanup|class_16|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_16),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|cleanup|class_17|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_17),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|cleanup|class_18|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_18),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("positiveclass|cleanup|class_19|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_19),size_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>(),align_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>());
println!("positiveclass|cleanup|class_20|20|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_20),size_of::<isize>(),align_of::<isize>());
println!("positiveclass|cleanup|class_21|10|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_21),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|cleanup|class_22|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_22),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>());
println!("positiveclass|cleanup|class_23|20|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_23),size_of::<&'static str>(),align_of::<&'static str>());
println!("positiveclass|cleanup|class_24|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_24),size_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>());
println!("positiveclass|cleanup|class_25|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_25),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("positiveclass|cleanup|class_26|5|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_26),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("positiveclass|cleanup|class_27|7|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_27),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("positiveclass|cleanup|class_28|6|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_28),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("positiveclass|cleanup|class_29|14|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_29),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("positiveclass|cleanup|class_30|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_30),size_of::<u32>(),align_of::<u32>());
println!("positiveclass|cleanup|class_31|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_31),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|cleanup|class_32|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_32),size_of::<super::control::SwiftCleanupInvariant>(),align_of::<super::control::SwiftCleanupInvariant>());
println!("positiveclass|cleanup|class_33|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_33),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|cleanup|class_34|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_34),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("positiveclass|cleanup|class_35|17|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_35),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("positiveclass|cleanup|class_36|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_36),size_of::<crate::experimental_swift_reactor::control::SwiftRunStage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunStage>());
println!("positiveclass|cleanup|class_37|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_37),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("positiveclass|cleanup|class_38|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_38),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("positiveclass|cleanup|class_39|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_39),size_of::<&'static mut SwiftExecutionState>(),align_of::<&'static mut SwiftExecutionState>());
println!("positiveclass|cleanup|class_40|7|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_40),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("positiveclass|cleanup|class_41|7|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_41),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|cleanup|class_42|14|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_42),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|cleanup|class_43|12|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_43),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|cleanup|class_44|8|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_44),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("positiveclass|cleanup|class_45|8|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_45),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("positiveclass|cleanup|class_46|20|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_46),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|cleanup|class_47|11|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_47),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("positiveclass|cleanup|class_48|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_48),size_of::<std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<std::vec::Vec<crate::experimental::execution::Control>>());
println!("positiveclass|cleanup|class_49|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_49),size_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>());
println!("positiveclass|cleanup|class_50|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_50),size_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("positiveclass|cleanup|class_51|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_51),size_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("positiveclass|cleanup|class_52|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_52),size_of::<std::vec::Vec<u8>>(),align_of::<std::vec::Vec<u8>>());
println!("positiveclass|cleanup|class_53|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_53),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("positiveclass|cleanup|class_54|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_54),size_of::<std::vec::Vec<std::option::Option<u32>>>(),align_of::<std::vec::Vec<std::option::Option<u32>>>());
println!("positiveclass|cleanup|class_55|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_55),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("positiveclass|cleanup|class_56|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_56),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionCleanupTail, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_57|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_57),size_of::<&'static mut Option<SwiftReactorInstance>>(),align_of::<&'static mut Option<SwiftReactorInstance>>());
println!("positiveclass|cleanup|class_58|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_58),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("positiveclass|cleanup|class_59|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_59),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftReactorInstance>>());
println!("positiveclass|cleanup|class_60|20|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_60),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|cleanup|class_61|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_61),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|cleanup|class_62|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_62),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|cleanup|class_63|16|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_63),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("positiveclass|cleanup|class_64|6|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_64),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|cleanup|class_65|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_65),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|cleanup|class_66|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_66),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|cleanup|class_67|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_67),size_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_68|12|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_68),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_69|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_69),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("positiveclass|cleanup|class_70|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_70),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("positiveclass|cleanup|class_71|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_71),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|cleanup|class_72|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_72),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|cleanup|class_73|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_73),size_of::<&'static crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("positiveclass|cleanup|class_74|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_74),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|cleanup|class_75|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_75),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|cleanup|class_76|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_76),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, &'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, &'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|cleanup|class_77|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_77),size_of::<std::result::Result<&'static crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<&'static crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_78|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_78),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|cleanup|class_79|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_79),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|cleanup|class_80|6|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_80),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi)>());
println!("positiveclass|cleanup|class_81|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_81),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|cleanup|class_82|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_82),size_of::<std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>(),align_of::<std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>());
println!("positiveclass|cleanup|class_83|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_83),size_of::<&'static [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>(),align_of::<&'static [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>());
println!("positiveclass|cleanup|class_84|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_84),size_of::<std::option::Option<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>(),align_of::<std::option::Option<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>());
println!("positiveclass|cleanup|class_85|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_85),size_of::<&'static mut std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>(),align_of::<&'static mut std::slice::Iter<'static, std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>>());
println!("positiveclass|cleanup|class_86|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_86),size_of::<&'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("positiveclass|cleanup|class_87|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_87),size_of::<&'static std::vec::Vec<Value>>(),align_of::<&'static std::vec::Vec<Value>>());
println!("positiveclass|cleanup|class_88|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_88),size_of::<&'static std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static std::vec::Vec<crate::experimental::execution::Control>>());
println!("positiveclass|cleanup|class_89|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_89),size_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>(),align_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>());
println!("positiveclass|cleanup|class_90|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_90),size_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("positiveclass|cleanup|class_91|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_91),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftReactorInstance>>());
println!("positiveclass|cleanup|class_92|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_92),size_of::<crate::experimental_swift_reactor::execution::Lifecycle>(),align_of::<crate::experimental_swift_reactor::execution::Lifecycle>());
println!("positiveclass|cleanup|class_93|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_93),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|cleanup|class_94|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_94),size_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("positiveclass|cleanup|class_95|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_95),size_of::<crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<crate::experimental_wasi::accounted::AccountedWasi>());
println!("positiveclass|cleanup|class_96|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_96),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|cleanup|class_97|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_97),size_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("positiveclass|cleanup|class_98|3|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_98),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("positiveclass|cleanup|class_99|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_99),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|cleanup|class_100|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_100),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("positiveclass|cleanup|class_101|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_101),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("positiveclass|cleanup|class_102|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_102),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("positiveclass|cleanup|class_103|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_103),size_of::<crate::experimental_swift_reactor::control::Live>(),align_of::<crate::experimental_swift_reactor::control::Live>());
println!("positiveclass|cleanup|class_104|7|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_104),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_105|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_105),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_106|4|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_106),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|cleanup|class_107|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_107),size_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>());
println!("positiveclass|cleanup|class_108|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_108),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("positiveclass|cleanup|class_109|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_109),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|cleanup|class_110|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_110),size_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>());
println!("positiveclass|cleanup|class_111|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_111),size_of::<Result<SwiftReactorInstance,ConstructionFailure>>(),align_of::<Result<SwiftReactorInstance,ConstructionFailure>>());
println!("positiveclass|cleanup|class_112|2|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_112),size_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>(),align_of::<Option<Result<SwiftReactorInstance,ConstructionFailure>>>());
println!("positiveclass|cleanup|class_113|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_113),size_of::<ConstructionFailure>(),align_of::<ConstructionFailure>());
println!("positiveclass|cleanup|class_114|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_114),size_of::<ConstructionCleanupTail>(),align_of::<ConstructionCleanupTail>());
println!("positiveclass|cleanup|class_115|1|{}|{}|{}",offset_of!(ConstructionPositiveCleanup,class_115),size_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>(),align_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>());
println!("positiveclass|final|class_0|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|final|class_1|7|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("positiveclass|final|class_2|9|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_2),size_of::<()>(),align_of::<()>());
println!("positiveclass|final|class_3|16|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_3),size_of::<usize>(),align_of::<usize>());
println!("positiveclass|final|class_4|7|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("positiveclass|final|class_5|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_5),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("positiveclass|final|class_6|8|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_6),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("positiveclass|final|class_7|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_7),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|final|class_8|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_8),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|final|class_9|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_9),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|final|class_10|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_10),size_of::<isize>(),align_of::<isize>());
println!("positiveclass|final|class_11|5|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_11),size_of::<bool>(),align_of::<bool>());
println!("positiveclass|final|class_12|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_12),size_of::<u64>(),align_of::<u64>());
println!("positiveclass|final|class_13|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_13),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("positiveclass|final|class_14|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_14),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("positiveclass|final|class_15|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_15),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("positiveclass|final|class_16|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_16),size_of::<(std::option::Option<usize>, std::option::Option<usize>)>(),align_of::<(std::option::Option<usize>, std::option::Option<usize>)>());
println!("positiveclass|final|class_17|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_17),size_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|final|class_18|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_18),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|final|class_19|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_19),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|final|class_20|4|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_20),size_of::<&'static str>(),align_of::<&'static str>());
println!("positiveclass|final|class_21|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_21),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("positiveclass|final|class_22|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_22),size_of::<ConstructionCleanupTail>(),align_of::<ConstructionCleanupTail>());
println!("positiveclass|final|class_23|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_23),size_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>(),align_of::<(Option<(RuntimeControl,AdoptedProof)>,Option<Result<SwiftReactorInstance,ConstructionFailure>>)>());
println!("positiveclass|final|class_24|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_24),size_of::<&'static mut Option<super::control::SwiftRunFailure>>(),align_of::<&'static mut Option<super::control::SwiftRunFailure>>());
println!("positiveclass|final|class_25|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_25),size_of::<&'static mut Option<super::control::SwiftRunUsage>>(),align_of::<&'static mut Option<super::control::SwiftRunUsage>>());
println!("positiveclass|final|class_26|3|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_26),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|final|class_27|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_27),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("positiveclass|final|class_28|5|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_28),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("positiveclass|final|class_29|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_29),size_of::<(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize)>(),align_of::<(crate::experimental_swift_reactor::execution::HeaderCompletionParts, usize)>());
println!("positiveclass|final|class_30|6|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_30),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("positiveclass|final|class_31|2|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_31),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("positiveclass|final|class_32|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_32),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("positiveclass|final|class_33|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_33),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("positiveclass|final|class_34|1|{}|{}|{}",offset_of!(ConstructionPositiveFinal,class_34),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("positivetotal|preflight|{}|{}",size_of::<ConstructionPositivePreflight>(),align_of::<ConstructionPositivePreflight>());
println!("positivetotal|active|{}|{}",size_of::<ConstructionPositiveActive>(),align_of::<ConstructionPositiveActive>());
println!("positivetotal|cleanup|{}|{}",size_of::<ConstructionPositiveCleanup>(),align_of::<ConstructionPositiveCleanup>());
println!("positivetotal|final|{}|{}",size_of::<ConstructionPositiveFinal>(),align_of::<ConstructionPositiveFinal>());
println!("positivefunctionitem|AccountedWasi::usage|{}|{}",size_of_val(&AccountedWasi::usage),align_of_val(&AccountedWasi::usage));
println!("positivefunctionitem|ConstructionFailure::Rejected|{}|{}",size_of_val(&ConstructionFailure::Rejected),align_of_val(&ConstructionFailure::Rejected));
println!("positivetotal|test_hook|{}|{}",CONSTRUCTION_POSITIVE_TEST_HOOK_BYTES,8);
crate::experimental::swift::independent_descriptor_accounting_probe();}
