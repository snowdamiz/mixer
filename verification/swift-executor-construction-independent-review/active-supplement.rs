// Independently authored supplemental logical whole-object inventory.
// Conservative sum of complete authored preflight call frames; no old slot is reclaimed.
#[allow(dead_code)]
struct ActiveSupplementStateEmpty {
    object_0: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_1: std::vec::Vec<u8>,
    object_2: std::vec::Vec<std::option::Option<u32>>,
    object_3: std::vec::Vec<Value>,
    object_4: std::vec::Vec<Value>,
    object_5: std::vec::Vec<crate::experimental::execution::Control>,
    object_6: std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_7: [std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6],
    object_8: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
}
#[allow(dead_code)]
struct ActiveSupplementStateEmptyCallback0 {
    object_0: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_1: &'static mut (),
    object_2: usize,
}
#[allow(dead_code)]
struct ActiveSupplementStateUnpublishedCleanup {
    object_0: (),
    object_1: SwiftExecutionState,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: (),
    object_5: &'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_6: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_7: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_8: isize,
    object_9: crate::experimental_swift_reactor::control::ReservationTicket,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_12: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_13: crate::experimental_wasi::WasiUsage,
    object_14: bool,
    object_15: bool,
}
#[allow(dead_code)]
struct ActiveSupplementStateDropArenas {
    object_0: (),
    object_1: &'static mut SwiftExecutionState,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_5: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_6: usize,
    object_7: bool,
    object_8: isize,
    object_9: crate::experimental_swift_reactor::control::ReservationTicket,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::vec::Vec<Value>,
    object_12: &'static mut std::vec::Vec<Value>,
    object_13: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_14: crate::experimental_wasi::WasiUsage,
    object_15: (),
    object_16: std::vec::Vec<Value>,
    object_17: &'static mut std::vec::Vec<Value>,
    object_18: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_19: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_20: usize,
    object_21: bool,
    object_22: isize,
    object_23: crate::experimental_swift_reactor::control::ReservationTicket,
    object_24: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_25: std::vec::Vec<crate::experimental::execution::Control>,
    object_26: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    object_27: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_28: crate::experimental_wasi::WasiUsage,
    object_29: (),
    object_30: std::vec::Vec<crate::experimental::execution::Control>,
    object_31: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    object_32: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_33: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_34: usize,
    object_35: bool,
    object_36: isize,
    object_37: crate::experimental_swift_reactor::control::ReservationTicket,
    object_38: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_39: std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_40: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_41: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_42: crate::experimental_wasi::WasiUsage,
    object_43: (),
    object_44: std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_45: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_46: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_47: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_48: usize,
    object_49: bool,
    object_50: isize,
    object_51: crate::experimental_swift_reactor::control::ReservationTicket,
    object_52: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_53: std::vec::Vec<u8>,
    object_54: &'static mut std::vec::Vec<u8>,
    object_55: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_56: crate::experimental_wasi::WasiUsage,
    object_57: (),
    object_58: std::vec::Vec<u8>,
    object_59: &'static mut std::vec::Vec<u8>,
    object_60: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_61: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_62: usize,
    object_63: bool,
    object_64: isize,
    object_65: crate::experimental_swift_reactor::control::ReservationTicket,
    object_66: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_67: std::vec::Vec<std::option::Option<u32>>,
    object_68: &'static mut std::vec::Vec<std::option::Option<u32>>,
    object_69: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_70: crate::experimental_wasi::WasiUsage,
    object_71: (),
    object_72: std::vec::Vec<std::option::Option<u32>>,
    object_73: &'static mut std::vec::Vec<std::option::Option<u32>>,
    object_74: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_75: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_76: usize,
    object_77: bool,
    object_78: isize,
    object_79: crate::experimental_swift_reactor::control::ReservationTicket,
    object_80: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_81: std::vec::Vec<Value>,
    object_82: &'static mut std::vec::Vec<Value>,
    object_83: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_84: crate::experimental_wasi::WasiUsage,
    object_85: (),
    object_86: std::vec::Vec<Value>,
    object_87: &'static mut std::vec::Vec<Value>,
    object_88: bool,
    object_89: bool,
    object_90: bool,
    object_91: bool,
    object_92: bool,
    object_93: bool,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstruct {
    object_0: std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: bool,
    object_3: &'static mut bool,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_5: crate::experimental_swift_reactor::control::Cursor,
    object_6: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_7: crate::experimental_swift_reactor::execution::PartialState,
    object_8: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_9: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: &'static mut crate::experimental_swift_reactor::execution::PartialState,
    object_11: isize,
    object_12: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_13: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_14: (),
    object_15: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_16: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_17: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_18: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_19: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_20: bool,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartial {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut PartialState,
    object_3: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_4: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_5: crate::experimental_swift_reactor::control::Cursor,
    object_6: isize,
    object_7: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_8: crate::experimental_swift_reactor::control::SwiftRunBudget,
    object_9: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_10: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>,
    object_11: std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_12: std::option::Option<crate::experimental::descriptors::MemoryExecutionView>,
    object_13: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_14: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_15: &'static crate::experimental_swift_reactor::control::Cursor,
    object_16: isize,
    object_17: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_18: crate::experimental::descriptors::MemoryExecutionView,
    object_19: bool,
    object_20: u32,
    object_21: u32,
    object_22: crate::experimental_swift_reactor::control::Fault,
    object_23: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_24: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>,
    object_25: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_26: u32,
    object_27: u32,
    object_28: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_29: crate::experimental_swift_reactor::control::Cursor,
    object_30: crate::experimental_swift_reactor::control::Fault,
    object_31: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_32: crate::experimental_wasi::WasiUsage,
    object_33: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>,
    object_34: std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_35: std::option::Option<crate::experimental::descriptors::TableExecutionView>,
    object_36: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_37: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_38: &'static crate::experimental_swift_reactor::control::Cursor,
    object_39: isize,
    object_40: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_41: crate::experimental::descriptors::TableExecutionView,
    object_42: usize,
    object_43: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_44: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>,
    object_45: std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_46: std::option::Option<[usize; 6]>,
    object_47: usize,
    object_48: usize,
    object_49: usize,
    object_50: usize,
    object_51: u32,
    object_52: usize,
    object_53: u32,
    object_54: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_55: &'static crate::experimental_swift_reactor::control::Cursor,
    object_56: isize,
    object_57: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_58: [usize; 6],
    object_59: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_60: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_61: std::option::Option<usize>,
    object_62: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_63: &'static crate::experimental_swift_reactor::control::Cursor,
    object_64: isize,
    object_65: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_66: usize,
    object_67: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_68: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_69: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_70: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_71: crate::experimental_swift_reactor::control::Cursor,
    object_72: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_73: crate::experimental_wasi::WasiUsage,
    object_74: isize,
    object_75: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_76: crate::experimental_swift_reactor::control::ReservationTicket,
    object_77: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_78: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_79: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_80: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_81: usize,
    object_82: usize,
    object_83: bool,
    object_84: crate::experimental_swift_reactor::control::Cursor,
    object_85: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_86: crate::experimental_wasi::WasiUsage,
    object_87: isize,
    object_88: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_89: crate::experimental_swift_reactor::control::ReservationTicket,
    object_90: usize,
    object_91: bool,
    object_92: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_93: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_94: &'static mut std::vec::Vec<Value>,
    object_95: usize,
    object_96: isize,
    object_97: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_98: (usize, bool),
    object_99: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_100: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_101: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_102: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_103: usize,
    object_104: usize,
    object_105: bool,
    object_106: crate::experimental_swift_reactor::control::Cursor,
    object_107: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_108: crate::experimental_wasi::WasiUsage,
    object_109: isize,
    object_110: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_111: crate::experimental_swift_reactor::control::ReservationTicket,
    object_112: usize,
    object_113: bool,
    object_114: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_115: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_116: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    object_117: usize,
    object_118: isize,
    object_119: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_120: (usize, bool),
    object_121: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_122: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_123: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_124: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_125: usize,
    object_126: usize,
    object_127: bool,
    object_128: crate::experimental_swift_reactor::control::Cursor,
    object_129: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_130: crate::experimental_wasi::WasiUsage,
    object_131: isize,
    object_132: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_133: crate::experimental_swift_reactor::control::ReservationTicket,
    object_134: usize,
    object_135: bool,
    object_136: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_137: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_138: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    object_139: usize,
    object_140: isize,
    object_141: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_142: (usize, bool),
    object_143: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_144: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_145: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_146: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_147: usize,
    object_148: usize,
    object_149: bool,
    object_150: crate::experimental_swift_reactor::control::Cursor,
    object_151: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_152: crate::experimental_wasi::WasiUsage,
    object_153: isize,
    object_154: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_155: crate::experimental_swift_reactor::control::ReservationTicket,
    object_156: usize,
    object_157: bool,
    object_158: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_159: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_160: &'static mut std::vec::Vec<u8>,
    object_161: usize,
    object_162: usize,
    object_163: bool,
    object_164: isize,
    object_165: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_166: (usize, bool),
    object_167: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_168: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_169: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_170: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_171: usize,
    object_172: usize,
    object_173: bool,
    object_174: crate::experimental_swift_reactor::control::Cursor,
    object_175: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_176: crate::experimental_wasi::WasiUsage,
    object_177: isize,
    object_178: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_179: crate::experimental_swift_reactor::control::ReservationTicket,
    object_180: usize,
    object_181: bool,
    object_182: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_183: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_184: &'static mut std::vec::Vec<std::option::Option<u32>>,
    object_185: usize,
    object_186: u32,
    object_187: isize,
    object_188: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_189: (usize, bool),
    object_190: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_191: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>,
    object_192: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_193: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_194: usize,
    object_195: usize,
    object_196: bool,
    object_197: crate::experimental_swift_reactor::control::Cursor,
    object_198: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_199: crate::experimental_wasi::WasiUsage,
    object_200: isize,
    object_201: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_202: crate::experimental_swift_reactor::control::ReservationTicket,
    object_203: usize,
    object_204: bool,
    object_205: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_206: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_207: &'static mut std::vec::Vec<Value>,
    object_208: isize,
    object_209: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_210: (usize, bool),
    object_211: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_212: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_213: std::option::Option<usize>,
    object_214: std::option::Option<usize>,
    object_215: usize,
    object_216: usize,
    object_217: bool,
    object_218: usize,
    object_219: u32,
    object_220: (&'static usize,),
    object_221: &'static usize,
    object_222: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_223: &'static crate::experimental_swift_reactor::control::Cursor,
    object_224: isize,
    object_225: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_226: usize,
    object_227: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_228: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_229: crate::experimental_swift_reactor::control::Cursor,
    object_230: isize,
    object_231: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_232: bool,
    object_233: usize,
    object_234: &'static std::vec::Vec<u8>,
    object_235: usize,
    object_236: usize,
    object_237: bool,
    object_238: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_239: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_240: crate::experimental_swift_reactor::control::Cursor,
    object_241: isize,
    object_242: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_243: usize,
    object_244: usize,
    object_245: usize,
    object_246: &'static std::vec::Vec<u8>,
    object_247: (usize, bool),
    object_248: usize,
    object_249: usize,
    object_250: bool,
    object_251: (),
    object_252: &'static mut std::vec::Vec<u8>,
    object_253: std::ops::Range<u32>,
    object_254: std::ops::Range<u32>,
    object_255: u32,
    object_256: std::ops::Range<u32>,
    object_257: std::option::Option<u32>,
    object_258: &'static mut std::ops::Range<u32>,
    object_259: isize,
    object_260: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_261: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_262: crate::experimental_swift_reactor::control::Cursor,
    object_263: isize,
    object_264: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_265: (),
    object_266: &'static mut std::vec::Vec<std::option::Option<u32>>,
    object_267: std::option::Option<u32>,
    object_268: std::ops::Range<usize>,
    object_269: std::ops::Range<usize>,
    object_270: std::ops::Range<usize>,
    object_271: std::option::Option<usize>,
    object_272: &'static mut std::ops::Range<usize>,
    object_273: isize,
    object_274: usize,
    object_275: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_276: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_277: crate::experimental_swift_reactor::control::Cursor,
    object_278: isize,
    object_279: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_280: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>,
    object_281: std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_282: std::option::Option<crate::experimental::descriptors::GlobalView<'static>>,
    object_283: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_284: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_285: &'static crate::experimental_swift_reactor::control::Cursor,
    object_286: isize,
    object_287: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_288: crate::experimental::descriptors::GlobalView<'static>,
    object_289: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_290: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_291: std::option::Option<usize>,
    object_292: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_293: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_294: &'static crate::experimental_swift_reactor::control::Cursor,
    object_295: isize,
    object_296: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_297: usize,
    object_298: crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_299: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>,
    object_300: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_301: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_302: Type,
    object_303: crate::experimental_swift_reactor::control::Cursor,
    object_304: isize,
    object_305: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_306: Value,
    object_307: (),
    object_308: &'static mut std::vec::Vec<Value>,
    object_309: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_310: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_311: &'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_312: isize,
    object_313: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_314: crate::experimental_swift_reactor::control::Live,
    object_315: usize,
    object_316: u32,
    object_317: crate::experimental_swift_reactor::control::Cursor,
    object_318: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_319: crate::experimental_wasi::WasiUsage,
    object_320: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_321: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_322: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_323: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_324: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_325: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_326: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_327: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_328: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_329: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_330: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_331: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_332: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_333: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_334: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_335: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_336: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_337: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_338: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_339: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_340: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_341: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_342: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_343: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_344: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_345: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_346: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_347: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_348: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_349: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_350: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_351: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_352: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_353: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_354: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_355: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_356: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_357: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_358: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_359: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_360: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_361: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_362: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_363: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_364: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_365: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_366: &'static [u8],
    object_367: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_368: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_369: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_370: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback2 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback3 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback4 {
    object_0: std::option::Option<usize>,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback5 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback6 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateConstructPartialCallback7 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveValue {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut Vec<Value>,
    object_3: usize,
    object_4: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::result::Result<(), std::collections::TryReserveError>,
    object_12: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_13: &'static usize,
    object_14: &'static crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: &'static std::vec::Vec<Value>,
    object_19: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_20: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_21: crate::experimental_swift_reactor::control::Cursor,
    object_22: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_23: crate::experimental_wasi::WasiUsage,
    object_24: isize,
    object_25: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: crate::experimental_swift_reactor::control::Cursor,
    object_27: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_28: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_29: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_30: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_31: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_32: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_33: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_34: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveValueCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: std::collections::TryReserveError,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: &'static usize,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: &'static crate::experimental_swift_reactor::control::Cursor,
    object_13: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveControl {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut Vec<Control>,
    object_3: usize,
    object_4: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::result::Result<(), std::collections::TryReserveError>,
    object_12: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_13: &'static usize,
    object_14: &'static crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: &'static std::vec::Vec<Control>,
    object_19: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_20: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_21: crate::experimental_swift_reactor::control::Cursor,
    object_22: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_23: crate::experimental_wasi::WasiUsage,
    object_24: isize,
    object_25: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: crate::experimental_swift_reactor::control::Cursor,
    object_27: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_28: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_29: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_30: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_31: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_32: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_33: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_34: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveControlCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: std::collections::TryReserveError,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: &'static usize,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: &'static crate::experimental_swift_reactor::control::Cursor,
    object_13: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveFrame {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut Vec<SwiftFrame>,
    object_3: usize,
    object_4: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::result::Result<(), std::collections::TryReserveError>,
    object_12: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_13: &'static usize,
    object_14: &'static crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: &'static std::vec::Vec<SwiftFrame>,
    object_19: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_20: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_21: crate::experimental_swift_reactor::control::Cursor,
    object_22: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_23: crate::experimental_wasi::WasiUsage,
    object_24: isize,
    object_25: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: crate::experimental_swift_reactor::control::Cursor,
    object_27: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_28: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_29: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_30: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_31: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_32: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_33: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_34: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveFrameCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: std::collections::TryReserveError,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: &'static usize,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: &'static crate::experimental_swift_reactor::control::Cursor,
    object_13: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveMemory {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut Vec<u8>,
    object_3: usize,
    object_4: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::result::Result<(), std::collections::TryReserveError>,
    object_12: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_13: &'static usize,
    object_14: &'static crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: &'static std::vec::Vec<u8>,
    object_19: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_20: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_21: crate::experimental_swift_reactor::control::Cursor,
    object_22: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_23: crate::experimental_wasi::WasiUsage,
    object_24: isize,
    object_25: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: crate::experimental_swift_reactor::control::Cursor,
    object_27: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_28: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_29: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_30: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_31: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_32: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_33: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_34: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveMemoryCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: std::collections::TryReserveError,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: &'static usize,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: &'static crate::experimental_swift_reactor::control::Cursor,
    object_13: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveTable {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut Vec<Option<u32>>,
    object_3: usize,
    object_4: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_10: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::result::Result<(), std::collections::TryReserveError>,
    object_12: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_13: &'static usize,
    object_14: &'static crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: &'static std::vec::Vec<Option<u32>>,
    object_19: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_20: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_21: crate::experimental_swift_reactor::control::Cursor,
    object_22: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_23: crate::experimental_wasi::WasiUsage,
    object_24: isize,
    object_25: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: crate::experimental_swift_reactor::control::Cursor,
    object_27: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_28: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_29: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_30: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_31: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_32: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_33: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_34: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateReserveTableCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: std::collections::TryReserveError,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: &'static usize,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: &'static crate::experimental_swift_reactor::control::Cursor,
    object_13: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegments {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: &'static mut SwiftExecutionState,
    object_3: std::ops::Range<usize>,
    object_4: std::ops::Range<usize>,
    object_5: usize,
    object_6: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_7: std::ops::Range<usize>,
    object_8: std::option::Option<usize>,
    object_9: &'static mut std::ops::Range<usize>,
    object_10: isize,
    object_11: usize,
    object_12: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_13: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_14: crate::experimental_swift_reactor::control::Cursor,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_18: std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_19: std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_20: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_21: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_22: &'static crate::experimental_swift_reactor::control::Cursor,
    object_23: isize,
    object_24: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_25: crate::experimental::descriptors::SegmentExecutionView<'static>,
    object_26: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_27: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_28: usize,
    object_29: &'static std::vec::Vec<u8>,
    object_30: isize,
    object_31: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_32: bool,
    object_33: usize,
    object_34: u32,
    object_35: usize,
    object_36: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_37: std::ops::Range<usize>,
    object_38: std::ops::Range<usize>,
    object_39: usize,
    object_40: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_41: std::ops::Range<usize>,
    object_42: std::option::Option<usize>,
    object_43: &'static mut std::ops::Range<usize>,
    object_44: isize,
    object_45: usize,
    object_46: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_47: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_48: crate::experimental_swift_reactor::control::Cursor,
    object_49: isize,
    object_50: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_51: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_52: std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_53: std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_54: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_55: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_56: &'static crate::experimental_swift_reactor::control::Cursor,
    object_57: isize,
    object_58: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_59: crate::experimental::descriptors::SegmentExecutionView<'static>,
    object_60: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_61: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_62: usize,
    object_63: &'static std::vec::Vec<std::option::Option<u32>>,
    object_64: isize,
    object_65: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_66: std::ops::Range<usize>,
    object_67: std::ops::Range<usize>,
    object_68: usize,
    object_69: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_70: std::ops::Range<usize>,
    object_71: std::option::Option<usize>,
    object_72: &'static mut std::ops::Range<usize>,
    object_73: isize,
    object_74: usize,
    object_75: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_76: std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_77: std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_78: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_79: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_80: &'static crate::experimental_swift_reactor::control::Cursor,
    object_81: isize,
    object_82: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_83: crate::experimental::descriptors::SegmentExecutionView<'static>,
    object_84: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_85: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_86: crate::experimental_swift_reactor::control::Cursor,
    object_87: usize,
    object_88: isize,
    object_89: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_90: usize,
    object_91: bool,
    object_92: usize,
    object_93: usize,
    object_94: crate::experimental_swift_reactor::control::Cursor,
    object_95: std::option::Option<usize>,
    object_96: usize,
    object_97: usize,
    object_98: usize,
    object_99: (usize, bool),
    object_100: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_101: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_102: isize,
    object_103: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_104: usize,
    object_105: usize,
    object_106: usize,
    object_107: (usize, bool),
    object_108: usize,
    object_109: usize,
    object_110: usize,
    object_111: u32,
    object_112: usize,
    object_113: (usize, bool),
    object_114: (),
    object_115: &'static mut [u8],
    object_116: &'static mut std::vec::Vec<u8>,
    object_117: std::ops::Range<usize>,
    object_118: usize,
    object_119: usize,
    object_120: (usize, bool),
    object_121: usize,
    object_122: (usize, bool),
    object_123: &'static [u8],
    object_124: std::ops::Range<usize>,
    object_125: usize,
    object_126: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_127: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_128: crate::experimental_swift_reactor::control::Cursor,
    object_129: std::option::Option<usize>,
    object_130: usize,
    object_131: usize,
    object_132: usize,
    object_133: (usize, bool),
    object_134: isize,
    object_135: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_136: std::ops::Range<usize>,
    object_137: std::ops::Range<usize>,
    object_138: usize,
    object_139: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_140: std::ops::Range<usize>,
    object_141: std::option::Option<usize>,
    object_142: &'static mut std::ops::Range<usize>,
    object_143: isize,
    object_144: usize,
    object_145: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_146: std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_147: std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>,
    object_148: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_149: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_150: &'static crate::experimental_swift_reactor::control::Cursor,
    object_151: isize,
    object_152: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_153: crate::experimental::descriptors::SegmentExecutionView<'static>,
    object_154: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_155: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_156: crate::experimental_swift_reactor::control::Cursor,
    object_157: usize,
    object_158: isize,
    object_159: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_160: crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_161: usize,
    object_162: std::ops::Range<usize>,
    object_163: std::ops::Range<usize>,
    object_164: usize,
    object_165: u32,
    object_166: std::ops::Range<usize>,
    object_167: std::option::Option<usize>,
    object_168: &'static mut std::ops::Range<usize>,
    object_169: isize,
    object_170: usize,
    object_171: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>,
    object_172: std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_173: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_174: crate::experimental_swift_reactor::control::Cursor,
    object_175: isize,
    object_176: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_177: u32,
    object_178: bool,
    object_179: &'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    object_180: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    object_181: &'static crate::experimental::swift::ValidatedSwiftReactor,
    object_182: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_183: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_184: crate::experimental_swift_reactor::control::Cursor,
    object_185: std::option::Option<u32>,
    object_186: &'static mut std::option::Option<u32>,
    object_187: &'static mut std::vec::Vec<std::option::Option<u32>>,
    object_188: usize,
    object_189: usize,
    object_190: u32,
    object_191: (usize, bool),
    object_192: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_193: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_194: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_195: crate::experimental_swift_reactor::control::Cursor,
    object_196: isize,
    object_197: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_198: crate::experimental_swift_reactor::control::Cursor,
    object_199: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_200: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_201: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_202: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_203: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_204: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_205: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_206: &'static [u8],
    object_207: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_208: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_209: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_210: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_211: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_212: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_213: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_214: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_215: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_216: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_217: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_218: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_219: &'static [u8],
    object_220: &'static [u8],
    object_221: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_222: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_223: &'static [u8],
    object_224: &'static [u8],
    object_225: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_226: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_227: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_228: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_229: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_230: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_231: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_232: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_233: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_234: &'static [u8],
    object_235: &'static [u8],
    object_236: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_237: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_238: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_239: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_240: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_241: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_242: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegmentsCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegmentsCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegmentsCallback2 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegmentsCallback3 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementStateRange {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: SegmentExecutionView<'static>,
    object_3: usize,
    object_4: &'static str,
    object_5: bool,
    object_6: std::option::Option<usize>,
    object_7: usize,
    object_8: u32,
    object_9: usize,
    object_10: u32,
    object_11: (&'static usize,),
    object_12: &'static usize,
    object_13: crate::experimental_swift_reactor::control::SwiftRunFailure,
}
#[allow(dead_code)]
struct ActiveSupplementStateRangeCallback0 {
    object_0: bool,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct ActiveSupplementStateSegmentFailure {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut ExecutionConstructionPhase<'static>,
    object_2: SegmentExecutionView<'static>,
    object_3: &'static str,
    object_4: crate::experimental_swift_reactor::control::Cursor,
    object_5: std::option::Option<usize>,
    object_6: usize,
    object_7: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_8: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_9: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct ActiveSupplementStatePhaseComplete {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: ExecutionConstructionPhase<'static>,
    object_2: Option<Result<SwiftExecutionState,SwiftRunFailure>>,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: usize,
    object_6: Option<Result<SwiftExecutionState,SwiftRunFailure>>,
    object_7: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_8: crate::experimental_wasi::WasiUsage,
    object_9: bool,
}
#[allow(dead_code)]
struct ActiveSupplementReaderFailure {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: super::control::Cursor,
    object_5: &'static str,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: std::option::Option<usize>,
    object_8: usize,
    object_9: usize,
    object_10: usize,
    object_11: (usize, bool),
    object_12: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
struct ActiveSupplementReaderByte {
    object_0: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: super::control::Cursor,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_6: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: crate::experimental_swift_reactor::control::Cursor,
    object_8: std::option::Option<usize>,
    object_9: usize,
    object_10: usize,
    object_11: usize,
    object_12: (usize, bool),
    object_13: isize,
    object_14: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_15: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_16: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: std::option::Option<u8>,
    object_18: std::option::Option<&'static u8>,
    object_19: usize,
    object_20: (&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_21: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_22: &'static crate::experimental_swift_reactor::control::Cursor,
    object_23: isize,
    object_24: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_25: u8,
    object_26: (usize, bool),
    object_27: &'static [u8],
}
#[allow(dead_code)]
struct ActiveSupplementReaderByteCallback0 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_4: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_5: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_6: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementReaderUnsigned {
    object_0: std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: super::control::Cursor,
    object_5: u32,
    object_6: std::iter::StepBy<std::ops::Range<i32>>,
    object_7: std::iter::StepBy<std::ops::Range<i32>>,
    object_8: std::ops::Range<i32>,
    object_9: std::iter::StepBy<std::ops::Range<i32>>,
    object_10: std::option::Option<i32>,
    object_11: &'static mut std::iter::StepBy<std::ops::Range<i32>>,
    object_12: isize,
    object_13: i32,
    object_14: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_15: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_16: isize,
    object_17: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_18: u8,
    object_19: bool,
    object_20: bool,
    object_21: u8,
    object_22: (usize, bool),
    object_23: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_24: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_25: u32,
    object_26: u32,
    object_27: u8,
    object_28: u32,
    object_29: bool,
    object_30: bool,
    object_31: u8,
    object_32: u32,
    object_33: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_34: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
}
#[allow(dead_code)]
struct ActiveSupplementReaderSigned {
    object_0: std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: u32,
    object_3: &'static mut super::control::RuntimeControl,
    object_4: &'static AccountedWasi,
    object_5: super::control::Cursor,
    object_6: u64,
    object_7: u32,
    object_8: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_9: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: isize,
    object_11: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_12: u8,
    object_13: u32,
    object_14: u32,
    object_15: (u32, bool),
    object_16: bool,
    object_17: u8,
    object_18: u8,
    object_19: bool,
    object_20: bool,
    object_21: u8,
    object_22: u8,
    object_23: u32,
    object_24: (u32, bool),
    object_25: bool,
    object_26: bool,
    object_27: u8,
    object_28: bool,
    object_29: u8,
    object_30: u8,
    object_31: (usize, bool),
    object_32: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_33: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_34: u64,
    object_35: u64,
    object_36: u8,
    object_37: u32,
    object_38: bool,
    object_39: (u32, bool),
    object_40: bool,
    object_41: u8,
    object_42: bool,
    object_43: u32,
    object_44: bool,
    object_45: u8,
    object_46: u64,
    object_47: u32,
    object_48: bool,
    object_49: i64,
    object_50: u64,
}
#[allow(dead_code)]
struct ActiveSupplementReaderConstant {
    object_0: std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: Type,
    object_3: &'static mut super::control::RuntimeControl,
    object_4: &'static AccountedWasi,
    object_5: super::control::Cursor,
    object_6: Value,
    object_7: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_8: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: isize,
    object_10: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: u8,
    object_12: i32,
    object_13: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>,
    object_14: std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: i64,
    object_18: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>,
    object_19: std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_20: isize,
    object_21: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_22: i64,
    object_23: [u8; 4],
    object_24: std::slice::IterMut<'static, u8>,
    object_25: &'static mut [u8; 4],
    object_26: std::slice::IterMut<'static, u8>,
    object_27: std::option::Option<&'static mut u8>,
    object_28: &'static mut std::slice::IterMut<'static, u8>,
    object_29: isize,
    object_30: &'static mut u8,
    object_31: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_32: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_33: isize,
    object_34: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_35: u8,
    object_36: u32,
    object_37: [u8; 4],
    object_38: [u8; 8],
    object_39: std::slice::IterMut<'static, u8>,
    object_40: &'static mut [u8; 8],
    object_41: std::slice::IterMut<'static, u8>,
    object_42: std::option::Option<&'static mut u8>,
    object_43: &'static mut std::slice::IterMut<'static, u8>,
    object_44: isize,
    object_45: &'static mut u8,
    object_46: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_47: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_48: isize,
    object_49: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_50: u8,
    object_51: u64,
    object_52: [u8; 8],
    object_53: (usize, bool),
    object_54: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_55: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_56: bool,
    object_57: &'static Type,
    object_58: Type,
    object_59: Value,
    object_60: &'static Type,
    object_61: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_62: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_63: bool,
    object_64: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>,
    object_65: std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_66: isize,
    object_67: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_68: u8,
    object_69: (usize, bool),
    object_70: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_71: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_72: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_73: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_74: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_75: isize,
    object_76: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_77: Value,
}
#[allow(dead_code)]
struct ActiveSupplementReaderEnd {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: &'static AccountedWasi,
    object_4: super::control::Cursor,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_6: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: crate::experimental_swift_reactor::control::Cursor,
    object_8: std::option::Option<usize>,
    object_9: usize,
    object_10: usize,
    object_11: usize,
    object_12: (usize, bool),
    object_13: isize,
    object_14: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_15: bool,
    object_16: usize,
    object_17: usize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_19: &'static [u8],
}
#[allow(dead_code)]
struct ActiveSupplementComposedConstruct {
    object_0: std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>,
    object_2: WasiGrants,
    object_3: WasiBudget,
    object_4: Instant,
    object_5: super::control::Cursor,
    object_6: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_7: &'static mut crate::experimental_swift_reactor::control::AdoptedProof,
    object_8: &'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof),
    object_9: std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>,
    object_10: &'static str,
    object_11: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_12: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_13: &'static crate::experimental_swift_reactor::control::AdoptedProof,
    object_14: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunUsage,
    object_19: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_20: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_21: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_22: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_23: std::option::Option<usize>,
    object_24: std::option::Option<usize>,
    object_25: (&'static usize,),
    object_26: &'static usize,
    object_27: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_28: &'static crate::experimental_swift_reactor::control::Cursor,
    object_29: isize,
    object_30: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_31: usize,
    object_32: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_33: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_34: isize,
    object_35: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_36: crate::experimental_swift_reactor::control::RuntimeControl,
    object_37: crate::experimental_swift_reactor::control::AdoptedProof,
    object_38: (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof),
    object_39: std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>,
    object_40: &'static str,
    object_41: crate::experimental_swift_reactor::execution::PartialInstance,
    object_42: std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_43: crate::experimental_swift_reactor::control::RuntimeControl,
    object_44: std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_45: std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_46: std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_47: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_48: &'static mut crate::experimental_swift_reactor::execution::PartialInstance,
    object_49: crate::experimental_swift_reactor::control::AdoptedProof,
    object_50: isize,
    object_51: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_52: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_53: crate::experimental_swift_reactor::execution::PartialInstance,
    object_54: crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    object_55: std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_56: &'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_57: std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_58: &'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_59: std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_60: &'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_61: std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_62: &'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_63: crate::experimental_swift_reactor::execution::Lifecycle,
    object_64: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_65: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_66: std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>,
    object_67: &'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_68: (crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>),
    object_69: crate::experimental_swift_reactor::execution::PartialInstance,
    object_70: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_71: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_72: &'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_73: isize,
    object_74: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_75: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_76: crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    object_77: crate::experimental_swift_reactor::execution::SwiftReactorInstance,
    object_78: bool,
    object_79: bool,
    object_80: bool,
    object_81: bool,
    object_82: bool,
}
#[allow(dead_code)]
struct ActiveSupplementComposedConstructCallback0 {
    object_0: std::option::Option<usize>,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct ActiveSupplementComposedConstructCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_6: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_7: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct ActiveSupplementPartialConstruct {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut PartialInstance,
    object_2: super::control::AdoptedProof,
    object_3: WasiGrants,
    object_4: WasiBudget,
    object_5: Instant,
    object_6: super::control::Cursor,
    object_7: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_8: std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>,
    object_9: &'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_10: std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_12: &'static crate::experimental_swift_reactor::control::AdoptedProof,
    object_13: isize,
    object_14: crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>,
    object_15: std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>,
    object_16: std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>,
    object_17: &'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>,
    object_18: crate::experimental_swift_reactor::control::AdoptedProof,
    object_19: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_20: std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>,
    object_21: std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>,
    object_22: &'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>,
    object_23: isize,
    object_24: crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_25: std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_26: crate::experimental_swift_reactor::cache::CacheConstructionFailure,
    object_27: bool,
    object_28: &'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>,
    object_30: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_31: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_32: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_33: crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>,
    object_34: std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>,
    object_35: isize,
    object_36: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_37: isize,
    object_38: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_39: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_40: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_41: crate::experimental_swift_reactor::control::AdoptedProof,
    object_42: crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    object_43: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>,
    object_44: std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_45: isize,
    object_46: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_47: crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    object_48: std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_49: std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_50: &'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    object_51: std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_52: std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_53: &'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_54: isize,
    object_55: crate::experimental_wasi::accounted::AccountedWasi,
    object_56: std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_57: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_58: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_59: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_60: crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    object_61: isize,
    object_62: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_63: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_64: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_65: crate::experimental_wasi::accounted::WasiConstructionPhase<'static>,
    object_66: isize,
    object_67: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_68: crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
    object_69: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>,
    object_70: std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_71: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    object_72: std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_73: &'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_74: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_75: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_76: &'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_77: isize,
    object_78: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_79: crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
    object_80: std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_81: std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_82: &'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
    object_83: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_84: std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_85: std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_86: &'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_87: isize,
    object_88: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_89: std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_90: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_91: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_92: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_93: crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
    object_94: std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_95: isize,
    object_96: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_97: isize,
    object_98: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_99: bool,
    object_100: bool,
    object_101: bool,
}
#[allow(dead_code)]
struct ActiveSupplementPartialCleanupFailed {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: PartialInstance,
    object_2: usize,
    object_3: super::control::SwiftRunFailure,
    object_4: crate::experimental_swift_reactor::control::RuntimeControl,
    object_5: std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_6: &'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>,
    object_7: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_8: std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_9: &'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>,
    object_10: isize,
    object_11: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_12: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_13: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_14: &'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_15: usize,
    object_16: usize,
    object_17: &'static std::vec::Vec<u8>,
    object_18: bool,
    object_19: (),
    object_20: &'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_21: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_22: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_23: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_24: crate::experimental_swift_reactor::control::Live,
    object_25: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_26: crate::experimental_wasi::WasiUsage,
    object_27: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_28: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_29: (),
    object_30: crate::experimental_swift_reactor::execution::SwiftExecutionState,
    object_31: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_32: (),
    object_33: bool,
    object_34: &'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_35: std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_36: &'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_37: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_38: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_39: &'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_40: isize,
    object_41: crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>,
    object_42: std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_43: &'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>,
    object_44: &'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_45: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_46: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_47: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_48: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_49: &'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_50: std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_51: &'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>,
    object_52: isize,
    object_53: crate::experimental_wasi::accounted::AccountedWasi,
    object_54: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_55: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_56: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_57: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_58: crate::experimental_swift_reactor::execution::PartialInstance,
    object_59: crate::experimental_swift_reactor::execution::ExecutionCleanupTail,
    object_60: crate::experimental_swift_reactor::control::RuntimeControl,
    object_61: std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_62: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_63: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_64: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>,
    object_65: (),
    object_66: &'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_67: &'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>,
    object_68: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_69: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_70: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>,
    object_71: bool,
    object_72: bool,
    object_73: bool,
}
#[allow(dead_code)]
struct ActiveSupplementWork {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static AccountedWasi,
    object_3: super::control::Cursor,
    object_4: usize,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_6: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: crate::experimental_swift_reactor::control::Work,
    object_10: u64,
    object_11: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_12: crate::experimental_wasi::WasiUsage,
}
#[allow(dead_code)]
struct ActiveSupplementArenasFormula {
    object_0: std::option::Option<[usize; 6]>,
    object_1: usize,
    object_2: usize,
    object_3: usize,
    object_4: usize,
    object_5: usize,
    object_6: usize,
    object_7: [usize; 6],
    object_8: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_9: std::option::Option<usize>,
    object_10: usize,
    object_11: isize,
    object_12: usize,
    object_13: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_14: std::option::Option<usize>,
    object_15: usize,
    object_16: isize,
    object_17: usize,
    object_18: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_19: std::option::Option<usize>,
    object_20: usize,
    object_21: isize,
    object_22: usize,
    object_23: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_24: std::option::Option<usize>,
    object_25: isize,
    object_26: usize,
    object_27: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_28: std::option::Option<usize>,
    object_29: usize,
    object_30: isize,
    object_31: usize,
    object_32: std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>,
    object_33: std::option::Option<usize>,
    object_34: usize,
    object_35: isize,
    object_36: usize,
}
#[allow(dead_code)]
struct ActiveSupplementControlAdmit {
    object_0: std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::SwiftReservationCategory,
    object_3: usize,
    object_4: super::control::Cursor,
    object_5: Option<WasiUsage>,
    object_6: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_7: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_8: isize,
    object_9: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: bool,
    object_11: usize,
    object_12: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_13: crate::experimental_swift_reactor::control::Fault,
    object_14: crate::experimental_swift_reactor::control::Fault,
    object_15: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_16: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_17: u64,
    object_18: u64,
    object_19: usize,
    object_20: (u64, bool),
    object_21: u64,
    object_22: usize,
    object_23: usize,
    object_24: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>,
    object_25: std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_26: isize,
    object_27: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_28: (usize, usize),
    object_29: (),
    object_30: (usize, bool),
    object_31: usize,
    object_32: usize,
    object_33: usize,
    object_34: crate::experimental_swift_reactor::control::ReservationTicket,
    object_35: u64,
}
#[allow(dead_code)]
struct ActiveSupplementControlExact {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: usize,
    object_3: usize,
    object_4: super::control::Cursor,
    object_5: Option<WasiUsage>,
    object_6: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_7: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_8: isize,
    object_9: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: bool,
    object_11: crate::experimental_swift_reactor::control::Fault,
    object_12: crate::experimental_swift_reactor::control::Fault,
    object_13: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_14: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_15: u64,
    object_16: u64,
    object_17: std::option::Option<usize>,
    object_18: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_19: crate::experimental_swift_reactor::control::Fault,
}
#[allow(dead_code)]
struct ActiveSupplementControlWork {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Work,
    object_3: u64,
    object_4: super::control::Cursor,
    object_5: Option<WasiUsage>,
    object_6: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_7: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_8: isize,
    object_9: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: u64,
    object_11: u64,
    object_12: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_13: (u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource),
    object_14: isize,
    object_15: u64,
    object_16: u64,
    object_17: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_18: u64,
    object_19: u64,
    object_20: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_21: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_22: crate::experimental_swift_reactor::control::Fault,
    object_23: crate::experimental_swift_reactor::control::Fault,
    object_24: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_25: u64,
    object_26: u64,
    object_27: std::option::Option<u64>,
    object_28: std::option::Option<u64>,
    object_29: (&'static u64,),
    object_30: &'static u64,
    object_31: isize,
    object_32: isize,
}
#[allow(dead_code)]
struct ActiveSupplementControlWorkCallback0 {
    object_0: bool,
    object_1: (&'static u64,),
    object_2: &'static u64,
    object_3: u64,
    object_4: u64,
    object_5: &'static u64,
}
#[allow(dead_code)]
struct ActiveSupplementControlAddLive {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Live,
    object_3: usize,
    object_4: super::control::Cursor,
    object_5: Option<WasiUsage>,
    object_6: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_7: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_8: isize,
    object_9: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_11: usize,
    object_12: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_13: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_14: (crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind),
    object_15: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_16: std::option::Option<usize>,
    object_17: usize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_19: crate::experimental_swift_reactor::control::Fault,
    object_20: crate::experimental_swift_reactor::control::Fault,
    object_21: u64,
    object_22: u64,
    object_23: usize,
    object_24: std::option::Option<usize>,
    object_25: (&'static usize,),
    object_26: &'static usize,
    object_27: isize,
    object_28: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_29: usize,
    object_30: usize,
}
#[allow(dead_code)]
struct ActiveSupplementControlAddLiveCallback0 {
    object_0: bool,
    object_1: (&'static usize,),
    object_2: &'static usize,
    object_3: usize,
    object_4: usize,
    object_5: &'static usize,
}
#[allow(dead_code)]
struct ActiveSupplementControlAddLiveCallback1 {
    object_0: u64,
    object_1: (),
    object_2: usize,
}
#[allow(dead_code)]
struct ActiveSupplementControlRemoveLive {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Live,
    object_3: usize,
    object_4: Option<WasiUsage>,
    object_5: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_6: (crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind),
    object_7: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_8: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_9: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_10: usize,
    object_11: std::option::Option<usize>,
    object_12: usize,
    object_13: isize,
    object_14: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
}
#[allow(dead_code)]
struct ActiveSupplementControlLiveParts {
    object_0: (crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind),
    object_1: &'static super::control::RuntimeControl,
    object_2: super::control::Live,
    object_3: isize,
    object_4: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_5: usize,
    object_6: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_7: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_8: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_9: usize,
    object_10: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_11: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_12: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_13: usize,
    object_14: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_15: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_16: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_17: usize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_19: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_20: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_21: usize,
    object_22: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_23: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_24: crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_25: usize,
    object_26: u32,
    object_27: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_28: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
struct ActiveSupplementControlLiveMut {
    object_0: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Live,
    object_3: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_4: isize,
    object_5: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_6: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_7: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_8: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_9: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_10: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
}
#[allow(dead_code)]
struct ActiveSupplementControlRefund {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::ReservationTicket,
    object_3: Option<WasiUsage>,
    object_4: bool,
    object_5: u64,
    object_6: u64,
    object_7: bool,
    object_8: u64,
    object_9: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_10: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_11: std::option::Option<usize>,
    object_12: usize,
    object_13: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_14: &'static crate::experimental_swift_reactor::control::SwiftReservations,
    object_15: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_16: usize,
    object_17: std::option::Option<usize>,
    object_18: usize,
    object_19: usize,
    object_20: std::option::Option<usize>,
    object_21: usize,
    object_22: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_23: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_24: usize,
    object_25: usize,
    object_26: usize,
    object_27: (std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>),
    object_28: isize,
    object_29: isize,
    object_30: isize,
    object_31: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_32: &'static mut crate::experimental_swift_reactor::control::SwiftReservations,
    object_33: crate::experimental_swift_reactor::control::SwiftReservationCategory,
}
#[allow(dead_code)]
struct ActiveSupplementDropValue {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Vec<Value>,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementDropControl {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Vec<Control>,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementDropFrame {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Vec<SwiftFrame>,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementDropMemory {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Vec<u8>,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementDropTable {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Vec<Option<u32>>,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementDropState {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: SwiftExecutionState,
    object_3: super::control::ReservationTicket,
    object_4: Option<WasiUsage>,
    object_5: (),
}
#[allow(dead_code)]
struct ActiveSupplementControlCleanupFault {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::SwiftCleanupInvariant,
    object_3: &'static str,
    object_4: Option<WasiUsage>,
    object_5: &'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_6: &'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>,
    object_7: crate::experimental_swift_reactor::control::Cursor,
    object_8: crate::experimental_swift_reactor::control::SwiftRunStage,
    object_9: std::option::Option<u32>,
    object_10: std::option::Option<usize>,
    object_11: crate::experimental_swift_reactor::control::Fault,
    object_12: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
pub(super) struct ConstructionActiveSupplement {
    state_empty: ActiveSupplementStateEmpty,
    state_empty_callback_0: ActiveSupplementStateEmptyCallback0,
    state_unpublished_cleanup: ActiveSupplementStateUnpublishedCleanup,
    state_drop_arenas: ActiveSupplementStateDropArenas,
    state_construct: ActiveSupplementStateConstruct,
    state_construct_partial: ActiveSupplementStateConstructPartial,
    state_construct_partial_callback_0: ActiveSupplementStateConstructPartialCallback0,
    state_construct_partial_callback_1: ActiveSupplementStateConstructPartialCallback1,
    state_construct_partial_callback_2: ActiveSupplementStateConstructPartialCallback2,
    state_construct_partial_callback_3: ActiveSupplementStateConstructPartialCallback3,
    state_construct_partial_callback_4: ActiveSupplementStateConstructPartialCallback4,
    state_construct_partial_callback_5: ActiveSupplementStateConstructPartialCallback5,
    state_construct_partial_callback_6: ActiveSupplementStateConstructPartialCallback6,
    state_construct_partial_callback_7: ActiveSupplementStateConstructPartialCallback7,
    state_reserve_value: ActiveSupplementStateReserveValue,
    state_reserve_value_callback_0: ActiveSupplementStateReserveValueCallback0,
    state_reserve_control: ActiveSupplementStateReserveControl,
    state_reserve_control_callback_0: ActiveSupplementStateReserveControlCallback0,
    state_reserve_frame: ActiveSupplementStateReserveFrame,
    state_reserve_frame_callback_0: ActiveSupplementStateReserveFrameCallback0,
    state_reserve_memory: ActiveSupplementStateReserveMemory,
    state_reserve_memory_callback_0: ActiveSupplementStateReserveMemoryCallback0,
    state_reserve_table: ActiveSupplementStateReserveTable,
    state_reserve_table_callback_0: ActiveSupplementStateReserveTableCallback0,
    state_segments: ActiveSupplementStateSegments,
    state_segments_callback_0: ActiveSupplementStateSegmentsCallback0,
    state_segments_callback_1: ActiveSupplementStateSegmentsCallback1,
    state_segments_callback_2: ActiveSupplementStateSegmentsCallback2,
    state_segments_callback_3: ActiveSupplementStateSegmentsCallback3,
    state_range: ActiveSupplementStateRange,
    state_range_callback_0: ActiveSupplementStateRangeCallback0,
    state_segment_failure: ActiveSupplementStateSegmentFailure,
    state_phase_complete: ActiveSupplementStatePhaseComplete,
    reader_failure: ActiveSupplementReaderFailure,
    reader_byte: ActiveSupplementReaderByte,
    reader_byte_callback_0: ActiveSupplementReaderByteCallback0,
    reader_unsigned: ActiveSupplementReaderUnsigned,
    reader_signed: ActiveSupplementReaderSigned,
    reader_constant: ActiveSupplementReaderConstant,
    reader_end: ActiveSupplementReaderEnd,
    composed_construct: ActiveSupplementComposedConstruct,
    composed_construct_callback_0: ActiveSupplementComposedConstructCallback0,
    composed_construct_callback_1: ActiveSupplementComposedConstructCallback1,
    partial_construct: ActiveSupplementPartialConstruct,
    partial_cleanup_failed: ActiveSupplementPartialCleanupFailed,
    work: ActiveSupplementWork,
    arenas_formula: ActiveSupplementArenasFormula,
    control_admit: ActiveSupplementControlAdmit,
    control_exact: ActiveSupplementControlExact,
    control_work: ActiveSupplementControlWork,
    control_work_callback_0: ActiveSupplementControlWorkCallback0,
    control_add_live: ActiveSupplementControlAddLive,
    control_add_live_callback_0: ActiveSupplementControlAddLiveCallback0,
    control_add_live_callback_1: ActiveSupplementControlAddLiveCallback1,
    control_remove_live: ActiveSupplementControlRemoveLive,
    control_live_parts: ActiveSupplementControlLiveParts,
    control_live_mut: ActiveSupplementControlLiveMut,
    control_refund: ActiveSupplementControlRefund,
    drop_value: ActiveSupplementDropValue,
    drop_control: ActiveSupplementDropControl,
    drop_frame: ActiveSupplementDropFrame,
    drop_memory: ActiveSupplementDropMemory,
    drop_table: ActiveSupplementDropTable,
    drop_state: ActiveSupplementDropState,
    control_cleanup_fault: ActiveSupplementControlCleanupFault,
}
pub(super) const CONSTRUCTION_ACTIVE_SUPPLEMENT_BYTES: usize = std::mem::size_of::<ConstructionActiveSupplement>();
pub(crate) fn independent_active_supplement_probe(){
 use std::mem::{size_of,align_of,offset_of};
println!("iactive|state_empty|{}|{}",size_of::<ActiveSupplementStateEmpty>(),align_of::<ActiveSupplementStateEmpty>());
println!("iactivefield|state_empty|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_0),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_empty|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_1),size_of::<std::vec::Vec<u8>>(),align_of::<std::vec::Vec<u8>>());
println!("iactivefield|state_empty|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_2),size_of::<std::vec::Vec<std::option::Option<u32>>>(),align_of::<std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_empty|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_3),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_empty|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_4),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_empty|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_5),size_of::<std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_empty|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_6),size_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_empty|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_7),size_of::<[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>(),align_of::<[std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>; 6]>());
println!("iactivefield|state_empty|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateEmpty,object_8),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactive|state_empty_callback_0|{}|{}",size_of::<ActiveSupplementStateEmptyCallback0>(),align_of::<ActiveSupplementStateEmptyCallback0>());
println!("iactivefield|state_empty_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateEmptyCallback0,object_0),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_empty_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateEmptyCallback0,object_1),size_of::<&'static mut ()>(),align_of::<&'static mut ()>());
println!("iactivefield|state_empty_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateEmptyCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactive|state_unpublished_cleanup|{}|{}",size_of::<ActiveSupplementStateUnpublishedCleanup>(),align_of::<ActiveSupplementStateUnpublishedCleanup>());
println!("iactivefield|state_unpublished_cleanup|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_0),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_unpublished_cleanup|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_1),size_of::<SwiftExecutionState>(),align_of::<SwiftExecutionState>());
println!("iactivefield|state_unpublished_cleanup|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|state_unpublished_cleanup|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|state_unpublished_cleanup|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_4),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_unpublished_cleanup|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_5),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_unpublished_cleanup|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_6),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_unpublished_cleanup|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_7),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_unpublished_cleanup|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_unpublished_cleanup|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_9),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_unpublished_cleanup|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_unpublished_cleanup|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_11),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_unpublished_cleanup|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_12),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_unpublished_cleanup|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_13),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_unpublished_cleanup|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_14),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_unpublished_cleanup|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateUnpublishedCleanup,object_15),size_of::<bool>(),align_of::<bool>());
println!("iactive|state_drop_arenas|{}|{}",size_of::<ActiveSupplementStateDropArenas>(),align_of::<ActiveSupplementStateDropArenas>());
println!("iactivefield|state_drop_arenas|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_0),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_1),size_of::<&'static mut SwiftExecutionState>(),align_of::<&'static mut SwiftExecutionState>());
println!("iactivefield|state_drop_arenas|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|state_drop_arenas|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|state_drop_arenas|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_4),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_5),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_6),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_7),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_9),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_11),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_12),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_13),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_14),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_15),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_16),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_17),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_18),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_19),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_20),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_21),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_22),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_23),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_24),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_25),size_of::<std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_drop_arenas|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_26),size_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_drop_arenas|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_27),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_28),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_29),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_30),size_of::<std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_drop_arenas|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_31),size_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_drop_arenas|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_32),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_33),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_34),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_35|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_35),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_36|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_36),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_37|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_37),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_38|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_38),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_39|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_39),size_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_drop_arenas|object_40|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_40),size_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_drop_arenas|object_41|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_41),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_42|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_42),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_43|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_43),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_44|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_44),size_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_drop_arenas|object_45|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_45),size_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_drop_arenas|object_46|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_46),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_47|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_47),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_48|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_48),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_49|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_49),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_50|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_50),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_51|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_51),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_52|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_52),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_53|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_53),size_of::<std::vec::Vec<u8>>(),align_of::<std::vec::Vec<u8>>());
println!("iactivefield|state_drop_arenas|object_54|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_54),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("iactivefield|state_drop_arenas|object_55|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_55),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_56|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_56),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_57|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_57),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_58|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_58),size_of::<std::vec::Vec<u8>>(),align_of::<std::vec::Vec<u8>>());
println!("iactivefield|state_drop_arenas|object_59|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_59),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("iactivefield|state_drop_arenas|object_60|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_60),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_61|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_61),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_62|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_62),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_63|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_63),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_64|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_64),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_65|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_65),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_66|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_66),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_67|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_67),size_of::<std::vec::Vec<std::option::Option<u32>>>(),align_of::<std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_drop_arenas|object_68|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_68),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_drop_arenas|object_69|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_69),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_70|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_70),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_71|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_71),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_72|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_72),size_of::<std::vec::Vec<std::option::Option<u32>>>(),align_of::<std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_drop_arenas|object_73|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_73),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_drop_arenas|object_74|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_74),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_75|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_75),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_drop_arenas|object_76|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_76),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_drop_arenas|object_77|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_77),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_78|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_78),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_drop_arenas|object_79|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_79),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_drop_arenas|object_80|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_80),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_drop_arenas|object_81|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_81),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_82|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_82),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_83|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_83),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_drop_arenas|object_84|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_84),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_drop_arenas|object_85|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_85),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_drop_arenas|object_86|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_86),size_of::<std::vec::Vec<Value>>(),align_of::<std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_87|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_87),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_drop_arenas|object_88|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_88),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_89|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_89),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_90|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_90),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_91|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_91),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_92|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_92),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_drop_arenas|object_93|{}|{}|{}",offset_of!(ActiveSupplementStateDropArenas,object_93),size_of::<bool>(),align_of::<bool>());
println!("iactive|state_construct|{}|{}",size_of::<ActiveSupplementStateConstruct>(),align_of::<ActiveSupplementStateConstruct>());
println!("iactivefield|state_construct|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_0),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_construct|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_2),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_3),size_of::<&'static mut bool>(),align_of::<&'static mut bool>());
println!("iactivefield|state_construct|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_5),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_6),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_construct|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_7),size_of::<crate::experimental_swift_reactor::execution::PartialState>(),align_of::<crate::experimental_swift_reactor::execution::PartialState>());
println!("iactivefield|state_construct|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_8),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_construct|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_9),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_10),size_of::<&'static mut crate::experimental_swift_reactor::execution::PartialState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::PartialState>());
println!("iactivefield|state_construct|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_11),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_12),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_construct|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_13),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_14),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_construct|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_15),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_construct|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_16),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_17),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_18),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_19),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateConstruct,object_20),size_of::<bool>(),align_of::<bool>());
println!("iactive|state_construct_partial|{}|{}",size_of::<ActiveSupplementStateConstructPartial>(),align_of::<ActiveSupplementStateConstructPartial>());
println!("iactivefield|state_construct_partial|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_construct_partial|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_2),size_of::<&'static mut PartialState>(),align_of::<&'static mut PartialState>());
println!("iactivefield|state_construct_partial|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_3),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_4),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_5),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_6),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_7),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunBudget>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunBudget>());
println!("iactivefield|state_construct_partial|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_9),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_10),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::MemoryExecutionView>>());
println!("iactivefield|state_construct_partial|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_11),size_of::<std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::MemoryExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_12),size_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>());
println!("iactivefield|state_construct_partial|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_13),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_construct_partial|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_14),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_15),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_16),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_17),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_18),size_of::<crate::experimental::descriptors::MemoryExecutionView>(),align_of::<crate::experimental::descriptors::MemoryExecutionView>());
println!("iactivefield|state_construct_partial|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_19),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_20),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_21),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_22),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_construct_partial|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_construct_partial|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_24),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("iactivefield|state_construct_partial|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_25),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|state_construct_partial|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_26),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_27),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_28),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_29),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_30),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_construct_partial|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_31),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_32),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_33),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::TableExecutionView>>());
println!("iactivefield|state_construct_partial|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_34),size_of::<std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::TableExecutionView, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_35|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_35),size_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>());
println!("iactivefield|state_construct_partial|object_36|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_36),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_construct_partial|object_37|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_37),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_38|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_38),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_39|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_39),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_40|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_40),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_41|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_41),size_of::<crate::experimental::descriptors::TableExecutionView>(),align_of::<crate::experimental::descriptors::TableExecutionView>());
println!("iactivefield|state_construct_partial|object_42|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_42),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_43|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_43),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_construct_partial|object_44|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_44),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, [usize; 6]>>());
println!("iactivefield|state_construct_partial|object_45|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_45),size_of::<std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<[usize; 6], crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_46|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_46),size_of::<std::option::Option<[usize; 6]>>(),align_of::<std::option::Option<[usize; 6]>>());
println!("iactivefield|state_construct_partial|object_47|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_47),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_48|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_48),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_49|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_49),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_50|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_50),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_51|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_51),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_52|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_52),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_53|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_53),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_54|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_54),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_55|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_55),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_56|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_56),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_57|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_57),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_58|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_58),size_of::<[usize; 6]>(),align_of::<[usize; 6]>());
println!("iactivefield|state_construct_partial|object_59|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_59),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("iactivefield|state_construct_partial|object_60|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_60),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_61|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_61),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial|object_62|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_62),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_63|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_63),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_64|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_64),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_65|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_65),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_66|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_66),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_67|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_67),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_68|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_68),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_69|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_69),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_70|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_70),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_71|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_71),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_72|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_72),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_73|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_73),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_74|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_74),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_75|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_75),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_76|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_76),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_77|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_77),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_78|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_78),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_79|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_79),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_80|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_80),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_81|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_81),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_82|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_82),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_83|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_83),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_84|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_84),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_85|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_85),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_86|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_86),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_87|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_87),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_88|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_88),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_89|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_89),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_90|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_90),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_91|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_91),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_92|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_92),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_93|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_93),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_94|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_94),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_construct_partial|object_95|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_95),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_96|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_96),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_97|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_97),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_98|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_98),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_99|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_99),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_100|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_100),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_101|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_101),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_102|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_102),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_103|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_103),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_104|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_104),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_105|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_105),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_106|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_106),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_107|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_107),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_108|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_108),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_109|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_109),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_110|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_110),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_111|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_111),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_112|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_112),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_113|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_113),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_114|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_114),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_115|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_115),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_116|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_116),size_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>(),align_of::<&'static mut std::vec::Vec<crate::experimental::execution::Control>>());
println!("iactivefield|state_construct_partial|object_117|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_117),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_118|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_118),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_119|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_119),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_120|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_120),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_121|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_121),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_122|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_122),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_123|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_123),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_124|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_124),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_125|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_125),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_126|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_126),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_127|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_127),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_128|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_128),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_129|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_129),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_130|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_130),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_131|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_131),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_132|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_132),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_133|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_133),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_134|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_134),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_135|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_135),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_136|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_136),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_137|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_137),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_138|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_138),size_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>(),align_of::<&'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>>());
println!("iactivefield|state_construct_partial|object_139|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_139),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_140|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_140),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_141|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_141),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_142|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_142),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_143|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_143),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_144|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_144),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_145|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_145),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_146|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_146),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_147|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_147),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_148|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_148),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_149|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_149),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_150|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_150),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_151|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_151),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_152|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_152),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_153|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_153),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_154|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_154),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_155|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_155),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_156|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_156),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_157|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_157),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_158|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_158),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_159|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_159),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_160|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_160),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("iactivefield|state_construct_partial|object_161|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_161),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_162|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_162),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_163|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_163),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_164|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_164),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_165|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_165),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_166|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_166),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_167|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_167),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_168|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_168),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_169|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_169),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_170|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_170),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_171|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_171),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_172|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_172),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_173|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_173),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_174|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_174),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_175|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_175),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_176|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_176),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_177|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_177),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_178|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_178),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_179|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_179),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_180|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_180),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_181|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_181),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_182|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_182),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_183|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_183),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_184|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_184),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_construct_partial|object_185|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_185),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_186|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_186),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_187|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_187),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_188|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_188),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_189|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_189),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_190|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_190),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_191|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_191),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|state_construct_partial|object_192|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_192),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_193|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_193),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|state_construct_partial|object_194|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_194),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_195|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_195),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_196|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_196),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_197|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_197),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_198|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_198),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_199|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_199),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_200|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_200),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_201|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_201),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_202|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_202),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|state_construct_partial|object_203|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_203),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_204|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_204),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_205|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_205),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_206|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_206),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_207|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_207),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_construct_partial|object_208|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_208),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_209|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_209),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_210|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_210),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_211|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_211),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("iactivefield|state_construct_partial|object_212|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_212),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_213|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_213),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial|object_214|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_214),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial|object_215|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_215),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_216|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_216),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_217|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_217),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_218|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_218),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_219|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_219),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_220|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_220),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|state_construct_partial|object_221|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_221),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_construct_partial|object_222|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_222),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_223|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_223),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_224|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_224),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_225|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_225),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_226|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_226),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_227|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_227),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_228|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_228),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_229|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_229),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_230|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_230),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_231|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_231),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_232|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_232),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_233|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_233),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_234|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_234),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("iactivefield|state_construct_partial|object_235|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_235),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_236|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_236),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_237|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_237),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_238|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_238),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_239|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_239),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_240|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_240),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_241|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_241),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_242|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_242),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_243|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_243),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_244|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_244),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_245|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_245),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_246|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_246),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("iactivefield|state_construct_partial|object_247|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_247),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_construct_partial|object_248|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_248),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_249|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_249),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_250|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_250),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_construct_partial|object_251|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_251),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_construct_partial|object_252|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_252),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("iactivefield|state_construct_partial|object_253|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_253),size_of::<std::ops::Range<u32>>(),align_of::<std::ops::Range<u32>>());
println!("iactivefield|state_construct_partial|object_254|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_254),size_of::<std::ops::Range<u32>>(),align_of::<std::ops::Range<u32>>());
println!("iactivefield|state_construct_partial|object_255|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_255),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_256|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_256),size_of::<std::ops::Range<u32>>(),align_of::<std::ops::Range<u32>>());
println!("iactivefield|state_construct_partial|object_257|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_257),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("iactivefield|state_construct_partial|object_258|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_258),size_of::<&'static mut std::ops::Range<u32>>(),align_of::<&'static mut std::ops::Range<u32>>());
println!("iactivefield|state_construct_partial|object_259|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_259),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_260|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_260),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_261|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_261),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_262|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_262),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_263|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_263),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_264|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_264),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_265|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_265),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_construct_partial|object_266|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_266),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_construct_partial|object_267|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_267),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("iactivefield|state_construct_partial|object_268|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_268),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_construct_partial|object_269|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_269),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_construct_partial|object_270|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_270),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_construct_partial|object_271|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_271),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial|object_272|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_272),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_construct_partial|object_273|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_273),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_274|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_274),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_275|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_275),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_276|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_276),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_277|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_277),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_278|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_278),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_279|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_279),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_280|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_280),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::GlobalView<'static>>>());
println!("iactivefield|state_construct_partial|object_281|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_281),size_of::<std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::GlobalView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_282|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_282),size_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>());
println!("iactivefield|state_construct_partial|object_283|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_283),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_construct_partial|object_284|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_284),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_285|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_285),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_286|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_286),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_287|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_287),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_288|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_288),size_of::<crate::experimental::descriptors::GlobalView<'static>>(),align_of::<crate::experimental::descriptors::GlobalView<'static>>());
println!("iactivefield|state_construct_partial|object_289|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_289),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("iactivefield|state_construct_partial|object_290|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_290),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_291|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_291),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial|object_292|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_292),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_construct_partial|object_293|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_293),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial|object_294|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_294),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_295|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_295),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_296|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_296),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_297|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_297),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_298|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_298),size_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_construct_partial|object_299|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_299),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, Value>>());
println!("iactivefield|state_construct_partial|object_300|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_300),size_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_301|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_301),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_construct_partial|object_302|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_302),size_of::<Type>(),align_of::<Type>());
println!("iactivefield|state_construct_partial|object_303|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_303),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_304|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_304),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_305|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_305),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_306|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_306),size_of::<Value>(),align_of::<Value>());
println!("iactivefield|state_construct_partial|object_307|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_307),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_construct_partial|object_308|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_308),size_of::<&'static mut std::vec::Vec<Value>>(),align_of::<&'static mut std::vec::Vec<Value>>());
println!("iactivefield|state_construct_partial|object_309|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_309),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_construct_partial|object_310|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_310),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_311|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_311),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|state_construct_partial|object_312|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_312),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_construct_partial|object_313|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_313),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_construct_partial|object_314|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_314),size_of::<crate::experimental_swift_reactor::control::Live>(),align_of::<crate::experimental_swift_reactor::control::Live>());
println!("iactivefield|state_construct_partial|object_315|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_315),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial|object_316|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_316),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_construct_partial|object_317|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_317),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial|object_318|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_318),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_construct_partial|object_319|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_319),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_construct_partial|object_320|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_320),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_321|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_321),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_322|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_322),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_323|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_323),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_construct_partial|object_324|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_324),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_325|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_325),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_326|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_326),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_construct_partial|object_327|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_327),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_328|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_328),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_329|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_329),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_330|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_330),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_331|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_331),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_construct_partial|object_332|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_332),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_333|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_333),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_334|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_334),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_335|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_335),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_336|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_336),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_337|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_337),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_338|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_338),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_339|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_339),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_340|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_340),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_341|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_341),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_342|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_342),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_343|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_343),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_344|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_344),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_345|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_345),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_346|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_346),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_347|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_347),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_348|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_348),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_349|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_349),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_350|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_350),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_351|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_351),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_352|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_352),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_353|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_353),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_354|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_354),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_355|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_355),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_356|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_356),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_357|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_357),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_358|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_358),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_359|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_359),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_360|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_360),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_construct_partial|object_361|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_361),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_362|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_362),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_363|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_363),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_construct_partial|object_364|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_364),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_365|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_365),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_366|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_366),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_construct_partial|object_367|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_367),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_368|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_368),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial|object_369|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_369),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial|object_370|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartial,object_370),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_construct_partial_callback_0|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback0>(),align_of::<ActiveSupplementStateConstructPartialCallback0>());
println!("iactivefield|state_construct_partial_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback0,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_1|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback1>(),align_of::<ActiveSupplementStateConstructPartialCallback1>());
println!("iactivefield|state_construct_partial_callback_1|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_1|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_1|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_1|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_1|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_1|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback1,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_2|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback2>(),align_of::<ActiveSupplementStateConstructPartialCallback2>());
println!("iactivefield|state_construct_partial_callback_2|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_2|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_2|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_2|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_2|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_2|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback2,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_3|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback3>(),align_of::<ActiveSupplementStateConstructPartialCallback3>());
println!("iactivefield|state_construct_partial_callback_3|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_3|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_3|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_3|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_3|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_3|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback3,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_4|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback4>(),align_of::<ActiveSupplementStateConstructPartialCallback4>());
println!("iactivefield|state_construct_partial_callback_4|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback4,object_0),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_construct_partial_callback_4|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback4,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|state_construct_partial_callback_4|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback4,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial_callback_4|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback4,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_construct_partial_callback_4|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback4,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactive|state_construct_partial_callback_5|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback5>(),align_of::<ActiveSupplementStateConstructPartialCallback5>());
println!("iactivefield|state_construct_partial_callback_5|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_5|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_5|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_5|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_5|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_5|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback5,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_6|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback6>(),align_of::<ActiveSupplementStateConstructPartialCallback6>());
println!("iactivefield|state_construct_partial_callback_6|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_6|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_6|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_6|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_6|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_6|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback6,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_construct_partial_callback_7|{}|{}",size_of::<ActiveSupplementStateConstructPartialCallback7>(),align_of::<ActiveSupplementStateConstructPartialCallback7>());
println!("iactivefield|state_construct_partial_callback_7|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_construct_partial_callback_7|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_construct_partial_callback_7|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_construct_partial_callback_7|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_construct_partial_callback_7|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_construct_partial_callback_7|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateConstructPartialCallback7,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_reserve_value|{}|{}",size_of::<ActiveSupplementStateReserveValue>(),align_of::<ActiveSupplementStateReserveValue>());
println!("iactivefield|state_reserve_value|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_reserve_value|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_2),size_of::<&'static mut Vec<Value>>(),align_of::<&'static mut Vec<Value>>());
println!("iactivefield|state_reserve_value|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_value|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_4),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_value|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_5),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_value|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_value|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_11),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("iactivefield|state_reserve_value|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_12),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_value|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_13),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_value|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_14),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_value|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_value|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_18),size_of::<&'static std::vec::Vec<Value>>(),align_of::<&'static std::vec::Vec<Value>>());
println!("iactivefield|state_reserve_value|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_19),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_value|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_20),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_22),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_value|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_23),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_value|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_24),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_value|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_25),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_value|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_26),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_27),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_value|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_28),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_value|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_value|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_30),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_value|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_value|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_32),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_value|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_33),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_value|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValue,object_34),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_value_callback_0|{}|{}",size_of::<ActiveSupplementStateReserveValueCallback0>(),align_of::<ActiveSupplementStateReserveValueCallback0>());
println!("iactivefield|state_reserve_value_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_reserve_value_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_1),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_value_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_2),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("iactivefield|state_reserve_value_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_value_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_reserve_value_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_value_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value_callback_0|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_value_callback_0|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_8),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_value_callback_0|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_value_callback_0|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_10),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_value_callback_0|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_value_callback_0|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_12),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_value_callback_0|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveValueCallback0,object_13),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_control|{}|{}",size_of::<ActiveSupplementStateReserveControl>(),align_of::<ActiveSupplementStateReserveControl>());
println!("iactivefield|state_reserve_control|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_reserve_control|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_2),size_of::<&'static mut Vec<Control>>(),align_of::<&'static mut Vec<Control>>());
println!("iactivefield|state_reserve_control|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_control|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_4),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_control|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_5),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_control|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_control|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_11),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("iactivefield|state_reserve_control|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_12),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_control|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_13),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_control|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_14),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_control|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_control|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_18),size_of::<&'static std::vec::Vec<Control>>(),align_of::<&'static std::vec::Vec<Control>>());
println!("iactivefield|state_reserve_control|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_19),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_control|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_20),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_22),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_control|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_23),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_control|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_24),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_control|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_25),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_control|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_26),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_27),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_control|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_28),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_control|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_control|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_30),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_control|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_control|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_32),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_control|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_33),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_control|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControl,object_34),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_control_callback_0|{}|{}",size_of::<ActiveSupplementStateReserveControlCallback0>(),align_of::<ActiveSupplementStateReserveControlCallback0>());
println!("iactivefield|state_reserve_control_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_reserve_control_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_1),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_control_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_2),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("iactivefield|state_reserve_control_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_control_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_reserve_control_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_control_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control_callback_0|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_control_callback_0|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_8),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_control_callback_0|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_control_callback_0|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_10),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_control_callback_0|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_control_callback_0|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_12),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_control_callback_0|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveControlCallback0,object_13),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_frame|{}|{}",size_of::<ActiveSupplementStateReserveFrame>(),align_of::<ActiveSupplementStateReserveFrame>());
println!("iactivefield|state_reserve_frame|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_reserve_frame|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_2),size_of::<&'static mut Vec<SwiftFrame>>(),align_of::<&'static mut Vec<SwiftFrame>>());
println!("iactivefield|state_reserve_frame|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_frame|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_4),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_frame|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_5),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_frame|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_frame|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_11),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("iactivefield|state_reserve_frame|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_12),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_frame|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_13),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_frame|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_14),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_frame|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_frame|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_18),size_of::<&'static std::vec::Vec<SwiftFrame>>(),align_of::<&'static std::vec::Vec<SwiftFrame>>());
println!("iactivefield|state_reserve_frame|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_19),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_frame|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_20),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_22),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_frame|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_23),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_frame|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_24),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_frame|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_25),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_frame|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_26),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_27),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_frame|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_28),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_frame|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_frame|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_30),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_frame|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_frame|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_32),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_frame|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_33),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_frame|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrame,object_34),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_frame_callback_0|{}|{}",size_of::<ActiveSupplementStateReserveFrameCallback0>(),align_of::<ActiveSupplementStateReserveFrameCallback0>());
println!("iactivefield|state_reserve_frame_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_reserve_frame_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_1),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_frame_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_2),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("iactivefield|state_reserve_frame_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_frame_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_reserve_frame_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_frame_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame_callback_0|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_frame_callback_0|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_8),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_frame_callback_0|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_frame_callback_0|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_10),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_frame_callback_0|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_frame_callback_0|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_12),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_frame_callback_0|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveFrameCallback0,object_13),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_memory|{}|{}",size_of::<ActiveSupplementStateReserveMemory>(),align_of::<ActiveSupplementStateReserveMemory>());
println!("iactivefield|state_reserve_memory|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_reserve_memory|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_2),size_of::<&'static mut Vec<u8>>(),align_of::<&'static mut Vec<u8>>());
println!("iactivefield|state_reserve_memory|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_memory|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_4),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_memory|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_5),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_memory|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_memory|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_11),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("iactivefield|state_reserve_memory|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_12),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_memory|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_13),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_memory|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_14),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_memory|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_memory|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_18),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("iactivefield|state_reserve_memory|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_19),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_memory|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_20),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_22),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_memory|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_23),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_memory|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_24),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_memory|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_25),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_memory|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_26),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_27),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_memory|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_28),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_memory|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_memory|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_30),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_memory|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_memory|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_32),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_memory|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_33),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_memory|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemory,object_34),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_memory_callback_0|{}|{}",size_of::<ActiveSupplementStateReserveMemoryCallback0>(),align_of::<ActiveSupplementStateReserveMemoryCallback0>());
println!("iactivefield|state_reserve_memory_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_reserve_memory_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_1),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_memory_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_2),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("iactivefield|state_reserve_memory_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_memory_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_reserve_memory_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_memory_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory_callback_0|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_memory_callback_0|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_8),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_memory_callback_0|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_memory_callback_0|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_10),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_memory_callback_0|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_memory_callback_0|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_12),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_memory_callback_0|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveMemoryCallback0,object_13),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_table|{}|{}",size_of::<ActiveSupplementStateReserveTable>(),align_of::<ActiveSupplementStateReserveTable>());
println!("iactivefield|state_reserve_table|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_reserve_table|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_2),size_of::<&'static mut Vec<Option<u32>>>(),align_of::<&'static mut Vec<Option<u32>>>());
println!("iactivefield|state_reserve_table|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_table|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_4),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_table|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_5),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_table|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_table|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_10),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_11),size_of::<std::result::Result<(), std::collections::TryReserveError>>(),align_of::<std::result::Result<(), std::collections::TryReserveError>>());
println!("iactivefield|state_reserve_table|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_12),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_table|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_13),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_table|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_14),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_table|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_table|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_18),size_of::<&'static std::vec::Vec<Option<u32>>>(),align_of::<&'static std::vec::Vec<Option<u32>>>());
println!("iactivefield|state_reserve_table|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_19),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_reserve_table|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_20),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_21),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_22),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_table|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_23),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_table|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_24),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_reserve_table|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_25),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_reserve_table|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_26),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_27),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_table|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_28),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_table|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_table|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_30),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_table|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_table|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_32),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_reserve_table|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_33),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_table|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTable,object_34),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_reserve_table_callback_0|{}|{}",size_of::<ActiveSupplementStateReserveTableCallback0>(),align_of::<ActiveSupplementStateReserveTableCallback0>());
println!("iactivefield|state_reserve_table_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_reserve_table_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_1),size_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static usize,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_reserve_table_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_2),size_of::<std::collections::TryReserveError>(),align_of::<std::collections::TryReserveError>());
println!("iactivefield|state_reserve_table_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_table_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_reserve_table_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_reserve_table_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table_callback_0|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|state_reserve_table_callback_0|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_8),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_reserve_table_callback_0|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_reserve_table_callback_0|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_10),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_reserve_table_callback_0|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_reserve_table_callback_0|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_12),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_reserve_table_callback_0|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateReserveTableCallback0,object_13),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_segments|{}|{}",size_of::<ActiveSupplementStateSegments>(),align_of::<ActiveSupplementStateSegments>());
println!("iactivefield|state_segments|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_segments|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_2),size_of::<&'static mut SwiftExecutionState>(),align_of::<&'static mut SwiftExecutionState>());
println!("iactivefield|state_segments|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_3),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_4),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_6),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_7),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_8),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_9),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_10),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_11),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_12),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_13),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_14|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_14),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_15|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_16|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_17|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_17),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_18|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_18),size_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_19|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_19),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_20|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_20),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_21|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_21),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments|object_22|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_22),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_23|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_23),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_24|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_24),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_25|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_25),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("iactivefield|state_segments|object_26|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_26),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_27|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_27),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_28|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_28),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_29|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_29),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("iactivefield|state_segments|object_30|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_30),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_31|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_31),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_32|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_32),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_segments|object_33|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_33),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_34|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_34),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_segments|object_35|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_35),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_36|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_36),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments|object_37|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_37),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_38|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_38),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_39|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_39),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_40|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_40),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_41|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_41),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_42|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_42),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_43|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_43),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_44|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_44),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_45|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_45),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_46|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_46),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_47|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_47),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_48|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_48),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_49|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_49),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_50|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_50),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_51|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_51),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_52|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_52),size_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_53|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_53),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_54|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_54),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_55|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_55),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments|object_56|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_56),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_57|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_57),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_58|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_58),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_59|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_59),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("iactivefield|state_segments|object_60|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_60),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_61|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_61),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_62|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_62),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_63|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_63),size_of::<&'static std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_segments|object_64|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_64),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_65|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_65),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_66|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_66),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_67|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_67),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_68|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_68),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_69|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_69),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_70|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_70),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_71|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_71),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_72|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_72),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_73|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_73),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_74|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_74),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_75|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_75),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_76|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_76),size_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_77|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_77),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_78|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_78),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_79|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_79),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments|object_80|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_80),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_81|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_81),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_82|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_82),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_83|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_83),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("iactivefield|state_segments|object_84|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_84),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_85|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_85),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_86|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_86),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_87|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_87),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_88|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_88),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_89|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_89),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_90|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_90),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_91|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_91),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_segments|object_92|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_92),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_93|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_93),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_94|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_94),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_95|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_95),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_96|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_96),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_97|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_97),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_98|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_98),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_99|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_99),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_100|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_100),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_101|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_101),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_102|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_102),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_103|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_103),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_104|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_104),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_105|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_105),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_106|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_106),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_107|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_107),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_108|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_108),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_109|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_109),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_110|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_110),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_111|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_111),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_segments|object_112|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_112),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_113|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_113),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_114|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_114),size_of::<()>(),align_of::<()>());
println!("iactivefield|state_segments|object_115|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_115),size_of::<&'static mut [u8]>(),align_of::<&'static mut [u8]>());
println!("iactivefield|state_segments|object_116|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_116),size_of::<&'static mut std::vec::Vec<u8>>(),align_of::<&'static mut std::vec::Vec<u8>>());
println!("iactivefield|state_segments|object_117|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_117),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_118|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_118),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_119|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_119),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_120|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_120),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_121|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_121),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_122|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_122),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_123|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_123),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_124|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_124),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_125|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_125),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_126|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_126),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_127|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_127),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_128|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_128),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_129|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_129),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_130|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_130),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_131|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_131),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_132|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_132),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_133|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_133),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_134|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_134),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_135|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_135),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_136|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_136),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_137|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_137),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_138|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_138),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_139|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_139),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_140|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_140),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_141|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_141),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_142|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_142),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_143|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_143),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_144|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_144),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_145|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_145),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_146|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_146),size_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental::descriptors::SegmentExecutionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_147|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_147),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("iactivefield|state_segments|object_148|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_148),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_149|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_149),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments|object_150|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_150),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_151|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_151),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_152|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_152),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_153|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_153),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("iactivefield|state_segments|object_154|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_154),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_155|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_155),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_156|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_156),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_157|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_157),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_158|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_158),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_159|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_159),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_160|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_160),size_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_segments|object_161|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_161),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_162|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_162),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_163|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_163),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_164|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_164),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_165|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_165),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_segments|object_166|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_166),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_167|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_167),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segments|object_168|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_168),size_of::<&'static mut std::ops::Range<usize>>(),align_of::<&'static mut std::ops::Range<usize>>());
println!("iactivefield|state_segments|object_169|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_169),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_170|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_170),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_171|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_171),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u32>>());
println!("iactivefield|state_segments|object_172|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_172),size_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_173|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_173),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_segments|object_174|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_174),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_175|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_175),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_176|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_176),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_177|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_177),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_segments|object_178|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_178),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_segments|object_179|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_179),size_of::<&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>(),align_of::<&'static std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>());
println!("iactivefield|state_segments|object_180|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_180),size_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>());
println!("iactivefield|state_segments|object_181|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_181),size_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>(),align_of::<&'static crate::experimental::swift::ValidatedSwiftReactor>());
println!("iactivefield|state_segments|object_182|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_182),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments|object_183|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_183),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_segments|object_184|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_184),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_185|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_185),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("iactivefield|state_segments|object_186|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_186),size_of::<&'static mut std::option::Option<u32>>(),align_of::<&'static mut std::option::Option<u32>>());
println!("iactivefield|state_segments|object_187|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_187),size_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>(),align_of::<&'static mut std::vec::Vec<std::option::Option<u32>>>());
println!("iactivefield|state_segments|object_188|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_188),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_189|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_189),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segments|object_190|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_190),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_segments|object_191|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_191),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|state_segments|object_192|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_192),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|state_segments|object_193|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_193),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_194|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_194),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|state_segments|object_195|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_195),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_196|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_196),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|state_segments|object_197|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_197),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_segments|object_198|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_198),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments|object_199|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_199),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_200|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_200),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_201|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_201),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_202|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_202),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_203|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_203),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_204|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_204),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_205|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_205),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_206|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_206),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_207|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_207),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_208|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_208),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_209|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_209),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_210|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_210),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_211|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_211),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_212|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_212),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_213|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_213),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_214|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_214),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_215|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_215),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_216|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_216),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_217|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_217),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_218|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_218),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_219|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_219),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_220|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_220),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_221|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_221),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_222|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_222),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_223|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_223),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_224|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_224),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_225|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_225),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_226|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_226),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_227|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_227),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_228|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_228),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_229|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_229),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_230|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_230),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_231|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_231),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_232|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_232),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_233|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_233),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_234|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_234),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_235|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_235),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactivefield|state_segments|object_236|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_236),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_237|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_237),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_238|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_238),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_239|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_239),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments|object_240|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_240),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|state_segments|object_241|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_241),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments|object_242|{}|{}|{}",offset_of!(ActiveSupplementStateSegments,object_242),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_segments_callback_0|{}|{}",size_of::<ActiveSupplementStateSegmentsCallback0>(),align_of::<ActiveSupplementStateSegmentsCallback0>());
println!("iactivefield|state_segments_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback0,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_segments_callback_1|{}|{}",size_of::<ActiveSupplementStateSegmentsCallback1>(),align_of::<ActiveSupplementStateSegmentsCallback1>());
println!("iactivefield|state_segments_callback_1|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments_callback_1|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments_callback_1|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments_callback_1|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments_callback_1|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments_callback_1|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback1,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_segments_callback_2|{}|{}",size_of::<ActiveSupplementStateSegmentsCallback2>(),align_of::<ActiveSupplementStateSegmentsCallback2>());
println!("iactivefield|state_segments_callback_2|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments_callback_2|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments_callback_2|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments_callback_2|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments_callback_2|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments_callback_2|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback2,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_segments_callback_3|{}|{}",size_of::<ActiveSupplementStateSegmentsCallback3>(),align_of::<ActiveSupplementStateSegmentsCallback3>());
println!("iactivefield|state_segments_callback_3|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segments_callback_3|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|state_segments_callback_3|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segments_callback_3|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segments_callback_3|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_segments_callback_3|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentsCallback3,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|state_range|{}|{}",size_of::<ActiveSupplementStateRange>(),align_of::<ActiveSupplementStateRange>());
println!("iactivefield|state_range|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_range|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_range|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_2),size_of::<SegmentExecutionView<'static>>(),align_of::<SegmentExecutionView<'static>>());
println!("iactivefield|state_range|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_range|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_4),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|state_range|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_5),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_range|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_6),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_range|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_7),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_range|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_8),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_range|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_9),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_range|object_10|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_10),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|state_range|object_11|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_11),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|state_range|object_12|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_12),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|state_range|object_13|{}|{}|{}",offset_of!(ActiveSupplementStateRange,object_13),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactive|state_range_callback_0|{}|{}",size_of::<ActiveSupplementStateRangeCallback0>(),align_of::<ActiveSupplementStateRangeCallback0>());
println!("iactivefield|state_range_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateRangeCallback0,object_0),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|state_range_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateRangeCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|state_range_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateRangeCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_range_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateRangeCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_range_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateRangeCallback0,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactive|state_segment_failure|{}|{}",size_of::<ActiveSupplementStateSegmentFailure>(),align_of::<ActiveSupplementStateSegmentFailure>());
println!("iactivefield|state_segment_failure|object_0|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|state_segment_failure|object_1|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_1),size_of::<&'static mut ExecutionConstructionPhase<'static>>(),align_of::<&'static mut ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_segment_failure|object_2|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_2),size_of::<SegmentExecutionView<'static>>(),align_of::<SegmentExecutionView<'static>>());
println!("iactivefield|state_segment_failure|object_3|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_3),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|state_segment_failure|object_4|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_4),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|state_segment_failure|object_5|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_5),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|state_segment_failure|object_6|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_6),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_segment_failure|object_7|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_7),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|state_segment_failure|object_8|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_8),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_segment_failure|object_9|{}|{}|{}",offset_of!(ActiveSupplementStateSegmentFailure,object_9),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactive|state_phase_complete|{}|{}",size_of::<ActiveSupplementStatePhaseComplete>(),align_of::<ActiveSupplementStatePhaseComplete>());
println!("iactivefield|state_phase_complete|object_0|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|state_phase_complete|object_1|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_1),size_of::<ExecutionConstructionPhase<'static>>(),align_of::<ExecutionConstructionPhase<'static>>());
println!("iactivefield|state_phase_complete|object_2|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_2),size_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>(),align_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>());
println!("iactivefield|state_phase_complete|object_3|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|state_phase_complete|object_4|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|state_phase_complete|object_5|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|state_phase_complete|object_6|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_6),size_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>(),align_of::<Option<Result<SwiftExecutionState,SwiftRunFailure>>>());
println!("iactivefield|state_phase_complete|object_7|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_7),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|state_phase_complete|object_8|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_8),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|state_phase_complete|object_9|{}|{}|{}",offset_of!(ActiveSupplementStatePhaseComplete,object_9),size_of::<bool>(),align_of::<bool>());
println!("iactive|reader_failure|{}|{}",size_of::<ActiveSupplementReaderFailure>(),align_of::<ActiveSupplementReaderFailure>());
println!("iactivefield|reader_failure|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_failure|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_1),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_failure|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_failure|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_failure|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_failure|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_5),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|reader_failure|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|reader_failure|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_7),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|reader_failure|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_8),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_failure|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_9),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_failure|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_10),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_failure|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_11),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_failure|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderFailure,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactive|reader_byte|{}|{}",size_of::<ActiveSupplementReaderByte>(),align_of::<ActiveSupplementReaderByte>());
println!("iactivefield|reader_byte|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_0),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_byte|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_1),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_byte|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_byte|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_byte|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_byte|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|reader_byte|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_6),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_byte|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_7),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|reader_byte|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_8),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|reader_byte|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_9),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_byte|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_10),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_byte|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_11),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_byte|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_12),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_byte|object_13|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_13),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_byte|object_14|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_14),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_byte|object_15|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_15),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_byte|object_16|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_16),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_byte|object_17|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_17),size_of::<std::option::Option<u8>>(),align_of::<std::option::Option<u8>>());
println!("iactivefield|reader_byte|object_18|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_18),size_of::<std::option::Option<&'static u8>>(),align_of::<std::option::Option<&'static u8>>());
println!("iactivefield|reader_byte|object_19|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_19),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_byte|object_20|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_20),size_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|reader_byte|object_21|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_21),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_byte|object_22|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_22),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|reader_byte|object_23|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_23),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_byte|object_24|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_24),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_byte|object_25|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_25),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_byte|object_26|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_26),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_byte|object_27|{}|{}|{}",offset_of!(ActiveSupplementReaderByte,object_27),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactive|reader_byte_callback_0|{}|{}",size_of::<ActiveSupplementReaderByteCallback0>(),align_of::<ActiveSupplementReaderByteCallback0>());
println!("iactivefield|reader_byte_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_byte_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_1),size_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>,&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|reader_byte_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|reader_byte_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_3),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_byte_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_4),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|reader_byte_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_5),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|reader_byte_callback_0|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderByteCallback0,object_6),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|reader_unsigned|{}|{}",size_of::<ActiveSupplementReaderUnsigned>(),align_of::<ActiveSupplementReaderUnsigned>());
println!("iactivefield|reader_unsigned|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_0),size_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u32, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_unsigned|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_1),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_unsigned|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_unsigned|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_unsigned|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_unsigned|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_5),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_unsigned|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_6),size_of::<std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<std::iter::StepBy<std::ops::Range<i32>>>());
println!("iactivefield|reader_unsigned|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_7),size_of::<std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<std::iter::StepBy<std::ops::Range<i32>>>());
println!("iactivefield|reader_unsigned|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_8),size_of::<std::ops::Range<i32>>(),align_of::<std::ops::Range<i32>>());
println!("iactivefield|reader_unsigned|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_9),size_of::<std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<std::iter::StepBy<std::ops::Range<i32>>>());
println!("iactivefield|reader_unsigned|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_10),size_of::<std::option::Option<i32>>(),align_of::<std::option::Option<i32>>());
println!("iactivefield|reader_unsigned|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_11),size_of::<&'static mut std::iter::StepBy<std::ops::Range<i32>>>(),align_of::<&'static mut std::iter::StepBy<std::ops::Range<i32>>>());
println!("iactivefield|reader_unsigned|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_12),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_unsigned|object_13|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_13),size_of::<i32>(),align_of::<i32>());
println!("iactivefield|reader_unsigned|object_14|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_14),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_unsigned|object_15|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_15),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_unsigned|object_16|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_16),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_unsigned|object_17|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_17),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_unsigned|object_18|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_18),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_unsigned|object_19|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_19),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_unsigned|object_20|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_20),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_unsigned|object_21|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_21),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_unsigned|object_22|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_22),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_unsigned|object_23|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_unsigned|object_24|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_24),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_unsigned|object_25|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_25),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_unsigned|object_26|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_26),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_unsigned|object_27|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_27),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_unsigned|object_28|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_28),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_unsigned|object_29|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_29),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_unsigned|object_30|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_30),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_unsigned|object_31|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_31),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_unsigned|object_32|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_32),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_unsigned|object_33|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_33),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_unsigned|object_34|{}|{}|{}",offset_of!(ActiveSupplementReaderUnsigned,object_34),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactive|reader_signed|{}|{}",size_of::<ActiveSupplementReaderSigned>(),align_of::<ActiveSupplementReaderSigned>());
println!("iactivefield|reader_signed|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_0),size_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_signed|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_1),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_signed|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_2),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_3),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_signed|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_4),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_signed|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_5),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_signed|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_6),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|reader_signed|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_7),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_8),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_signed|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_9),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_signed|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_10),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_signed|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_11),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_signed|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_12),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_13|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_13),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_14|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_14),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_15|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_15),size_of::<(u32, bool)>(),align_of::<(u32, bool)>());
println!("iactivefield|reader_signed|object_16|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_16),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_17|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_17),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_18|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_18),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_19|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_19),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_20|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_20),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_21|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_21),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_22|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_22),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_23|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_23),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_24|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_24),size_of::<(u32, bool)>(),align_of::<(u32, bool)>());
println!("iactivefield|reader_signed|object_25|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_25),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_26|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_26),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_27|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_27),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_28|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_28),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_29|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_29),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_30|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_30),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_31|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_31),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_signed|object_32|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_32),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_signed|object_33|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_33),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_signed|object_34|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_34),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|reader_signed|object_35|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_35),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|reader_signed|object_36|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_36),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_37|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_37),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_38|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_38),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_39|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_39),size_of::<(u32, bool)>(),align_of::<(u32, bool)>());
println!("iactivefield|reader_signed|object_40|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_40),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_41|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_41),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_42|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_42),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_43|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_43),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_44|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_44),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_45|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_45),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_signed|object_46|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_46),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|reader_signed|object_47|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_47),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_signed|object_48|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_48),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_signed|object_49|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_49),size_of::<i64>(),align_of::<i64>());
println!("iactivefield|reader_signed|object_50|{}|{}|{}",offset_of!(ActiveSupplementReaderSigned,object_50),size_of::<u64>(),align_of::<u64>());
println!("iactive|reader_constant|{}|{}",size_of::<ActiveSupplementReaderConstant>(),align_of::<ActiveSupplementReaderConstant>());
println!("iactivefield|reader_constant|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_0),size_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<Value, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_1),size_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_constant|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_2),size_of::<Type>(),align_of::<Type>());
println!("iactivefield|reader_constant|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_3),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_constant|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_4),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_constant|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_5),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_constant|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_6),size_of::<Value>(),align_of::<Value>());
println!("iactivefield|reader_constant|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_7),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_constant|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_8),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_9),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_10),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_11),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_constant|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_12),size_of::<i32>(),align_of::<i32>());
println!("iactivefield|reader_constant|object_13|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_13),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>());
println!("iactivefield|reader_constant|object_14|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_14),size_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_15|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_16|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_17|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_17),size_of::<i64>(),align_of::<i64>());
println!("iactivefield|reader_constant|object_18|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_18),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, i64>>());
println!("iactivefield|reader_constant|object_19|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_19),size_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<i64, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_20|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_20),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_21|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_21),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_22|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_22),size_of::<i64>(),align_of::<i64>());
println!("iactivefield|reader_constant|object_23|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_23),size_of::<[u8; 4]>(),align_of::<[u8; 4]>());
println!("iactivefield|reader_constant|object_24|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_24),size_of::<std::slice::IterMut<'static, u8>>(),align_of::<std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_25|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_25),size_of::<&'static mut [u8; 4]>(),align_of::<&'static mut [u8; 4]>());
println!("iactivefield|reader_constant|object_26|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_26),size_of::<std::slice::IterMut<'static, u8>>(),align_of::<std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_27|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_27),size_of::<std::option::Option<&'static mut u8>>(),align_of::<std::option::Option<&'static mut u8>>());
println!("iactivefield|reader_constant|object_28|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_28),size_of::<&'static mut std::slice::IterMut<'static, u8>>(),align_of::<&'static mut std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_29|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_29),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_30|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_30),size_of::<&'static mut u8>(),align_of::<&'static mut u8>());
println!("iactivefield|reader_constant|object_31|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_31),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_constant|object_32|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_32),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_33|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_33),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_34|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_34),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_35|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_35),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_constant|object_36|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_36),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|reader_constant|object_37|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_37),size_of::<[u8; 4]>(),align_of::<[u8; 4]>());
println!("iactivefield|reader_constant|object_38|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_38),size_of::<[u8; 8]>(),align_of::<[u8; 8]>());
println!("iactivefield|reader_constant|object_39|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_39),size_of::<std::slice::IterMut<'static, u8>>(),align_of::<std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_40|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_40),size_of::<&'static mut [u8; 8]>(),align_of::<&'static mut [u8; 8]>());
println!("iactivefield|reader_constant|object_41|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_41),size_of::<std::slice::IterMut<'static, u8>>(),align_of::<std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_42|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_42),size_of::<std::option::Option<&'static mut u8>>(),align_of::<std::option::Option<&'static mut u8>>());
println!("iactivefield|reader_constant|object_43|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_43),size_of::<&'static mut std::slice::IterMut<'static, u8>>(),align_of::<&'static mut std::slice::IterMut<'static, u8>>());
println!("iactivefield|reader_constant|object_44|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_44),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_45|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_45),size_of::<&'static mut u8>(),align_of::<&'static mut u8>());
println!("iactivefield|reader_constant|object_46|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_46),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_constant|object_47|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_47),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_48|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_48),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_49|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_49),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_50|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_50),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_constant|object_51|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_51),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|reader_constant|object_52|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_52),size_of::<[u8; 8]>(),align_of::<[u8; 8]>());
println!("iactivefield|reader_constant|object_53|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_53),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_constant|object_54|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_54),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_constant|object_55|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_55),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_constant|object_56|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_56),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_constant|object_57|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_57),size_of::<&'static Type>(),align_of::<&'static Type>());
println!("iactivefield|reader_constant|object_58|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_58),size_of::<Type>(),align_of::<Type>());
println!("iactivefield|reader_constant|object_59|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_59),size_of::<Value>(),align_of::<Value>());
println!("iactivefield|reader_constant|object_60|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_60),size_of::<&'static Type>(),align_of::<&'static Type>());
println!("iactivefield|reader_constant|object_61|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_61),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_constant|object_62|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_62),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_constant|object_63|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_63),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_constant|object_64|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_64),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, u8>>());
println!("iactivefield|reader_constant|object_65|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_65),size_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<u8, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_66|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_66),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_67|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_67),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_68|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_68),size_of::<u8>(),align_of::<u8>());
println!("iactivefield|reader_constant|object_69|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_69),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_constant|object_70|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_70),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_constant|object_71|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_71),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_constant|object_72|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_72),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|reader_constant|object_73|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_73),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_74|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_74),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_constant|object_75|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_75),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_constant|object_76|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_76),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_constant|object_77|{}|{}|{}",offset_of!(ActiveSupplementReaderConstant,object_77),size_of::<Value>(),align_of::<Value>());
println!("iactive|reader_end|{}|{}",size_of::<ActiveSupplementReaderEnd>(),align_of::<ActiveSupplementReaderEnd>());
println!("iactivefield|reader_end|object_0|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_end|object_1|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_1),size_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>(),align_of::<&'static crate::experimental_swift_reactor::execution::ScalarReader<'static>>());
println!("iactivefield|reader_end|object_2|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|reader_end|object_3|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|reader_end|object_4|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|reader_end|object_5|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|reader_end|object_6|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_6),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_end|object_7|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_7),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|reader_end|object_8|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_8),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|reader_end|object_9|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_9),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_end|object_10|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_10),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_end|object_11|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_11),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_end|object_12|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_12),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|reader_end|object_13|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_13),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|reader_end|object_14|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_14),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|reader_end|object_15|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_15),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|reader_end|object_16|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_16),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_end|object_17|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|reader_end|object_18|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|reader_end|object_19|{}|{}|{}",offset_of!(ActiveSupplementReaderEnd,object_19),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("iactive|composed_construct|{}|{}",size_of::<ActiveSupplementComposedConstruct>(),align_of::<ActiveSupplementComposedConstruct>());
println!("iactivefield|composed_construct|object_0|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_0),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_1|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_1),size_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>(),align_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>());
println!("iactivefield|composed_construct|object_2|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_2),size_of::<WasiGrants>(),align_of::<WasiGrants>());
println!("iactivefield|composed_construct|object_3|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_3),size_of::<WasiBudget>(),align_of::<WasiBudget>());
println!("iactivefield|composed_construct|object_4|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_4),size_of::<Instant>(),align_of::<Instant>());
println!("iactivefield|composed_construct|object_5|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_5),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|composed_construct|object_6|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct|object_7|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_7),size_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|composed_construct|object_8|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_8),size_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("iactivefield|composed_construct|object_9|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_9),size_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("iactivefield|composed_construct|object_10|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_10),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|composed_construct|object_11|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_11),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|composed_construct|object_12|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_12),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_13|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_13),size_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|composed_construct|object_14|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_14),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|composed_construct|object_15|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_15),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|composed_construct|object_16|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_17|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|composed_construct|object_18|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("iactivefield|composed_construct|object_19|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_19),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct|object_20|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_20),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|composed_construct|object_21|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_21),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("iactivefield|composed_construct|object_22|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_22),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_23|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_23),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|composed_construct|object_24|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_24),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|composed_construct|object_25|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_25),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|composed_construct|object_26|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_26),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|composed_construct|object_27|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_27),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|composed_construct|object_28|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_28),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|composed_construct|object_29|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_29),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|composed_construct|object_30|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_30),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_31|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_31),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|composed_construct|object_32|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_32),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|composed_construct|object_33|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_33),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_34|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_34),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|composed_construct|object_35|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_35),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_36|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_36),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct|object_37|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_37),size_of::<crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|composed_construct|object_38|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_38),size_of::<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("iactivefield|composed_construct|object_39|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_39),size_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<(crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("iactivefield|composed_construct|object_40|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_40),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|composed_construct|object_41|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_41),size_of::<crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<crate::experimental_swift_reactor::execution::PartialInstance>());
println!("iactivefield|composed_construct|object_42|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_42),size_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|composed_construct|object_43|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_43),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct|object_44|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_44),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|composed_construct|object_45|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_45),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|composed_construct|object_46|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_46),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|composed_construct|object_47|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_47),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_48|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_48),size_of::<&'static mut crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::PartialInstance>());
println!("iactivefield|composed_construct|object_49|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_49),size_of::<crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|composed_construct|object_50|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_50),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|composed_construct|object_51|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_51),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|composed_construct|object_52|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_52),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|composed_construct|object_53|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_53),size_of::<crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<crate::experimental_swift_reactor::execution::PartialInstance>());
println!("iactivefield|composed_construct|object_54|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_54),size_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("iactivefield|composed_construct|object_55|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_55),size_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|composed_construct|object_56|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_56),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|composed_construct|object_57|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_57),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|composed_construct|object_58|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_58),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|composed_construct|object_59|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_59),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|composed_construct|object_60|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_60),size_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|composed_construct|object_61|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_61),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|composed_construct|object_62|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_62),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|composed_construct|object_63|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_63),size_of::<crate::experimental_swift_reactor::execution::Lifecycle>(),align_of::<crate::experimental_swift_reactor::execution::Lifecycle>());
println!("iactivefield|composed_construct|object_64|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_64),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|composed_construct|object_65|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_65),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct|object_66|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_66),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|composed_construct|object_67|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_67),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|composed_construct|object_68|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_68),size_of::<(crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>)>(),align_of::<(crate::experimental_swift_reactor::execution::PartialInstance, std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>)>());
println!("iactivefield|composed_construct|object_69|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_69),size_of::<crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<crate::experimental_swift_reactor::execution::PartialInstance>());
println!("iactivefield|composed_construct|object_70|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_70),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|composed_construct|object_71|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_71),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|composed_construct|object_72|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_72),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|composed_construct|object_73|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_73),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|composed_construct|object_74|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_74),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|composed_construct|object_75|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_75),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|composed_construct|object_76|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_76),size_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("iactivefield|composed_construct|object_77|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_77),size_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>(),align_of::<crate::experimental_swift_reactor::execution::SwiftReactorInstance>());
println!("iactivefield|composed_construct|object_78|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_78),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|composed_construct|object_79|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_79),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|composed_construct|object_80|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_80),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|composed_construct|object_81|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_81),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|composed_construct|object_82|{}|{}|{}",offset_of!(ActiveSupplementComposedConstruct,object_82),size_of::<bool>(),align_of::<bool>());
println!("iactive|composed_construct_callback_0|{}|{}",size_of::<ActiveSupplementComposedConstructCallback0>(),align_of::<ActiveSupplementComposedConstructCallback0>());
println!("iactivefield|composed_construct_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback0,object_0),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|composed_construct_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|composed_construct_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|composed_construct_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|composed_construct_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback0,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactive|composed_construct_callback_1|{}|{}",size_of::<ActiveSupplementComposedConstructCallback1>(),align_of::<ActiveSupplementComposedConstructCallback1>());
println!("iactivefield|composed_construct_callback_1|object_0|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|composed_construct_callback_1|object_1|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("iactivefield|composed_construct_callback_1|object_2|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|composed_construct_callback_1|object_3|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|composed_construct_callback_1|object_4|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|composed_construct_callback_1|object_5|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_5),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|composed_construct_callback_1|object_6|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|composed_construct_callback_1|object_7|{}|{}|{}",offset_of!(ActiveSupplementComposedConstructCallback1,object_7),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("iactive|partial_construct|{}|{}",size_of::<ActiveSupplementPartialConstruct>(),align_of::<ActiveSupplementPartialConstruct>());
println!("iactivefield|partial_construct|object_0|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_1|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_1),size_of::<&'static mut PartialInstance>(),align_of::<&'static mut PartialInstance>());
println!("iactivefield|partial_construct|object_2|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_2),size_of::<super::control::AdoptedProof>(),align_of::<super::control::AdoptedProof>());
println!("iactivefield|partial_construct|object_3|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_3),size_of::<WasiGrants>(),align_of::<WasiGrants>());
println!("iactivefield|partial_construct|object_4|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_4),size_of::<WasiBudget>(),align_of::<WasiBudget>());
println!("iactivefield|partial_construct|object_5|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_5),size_of::<Instant>(),align_of::<Instant>());
println!("iactivefield|partial_construct|object_6|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_6),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|partial_construct|object_7|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_7),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_construct|object_8|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_8),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|partial_construct|object_9|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_9),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|partial_construct|object_10|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_10),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_11|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_11),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_construct|object_12|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_12),size_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|partial_construct|object_13|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_13),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_14|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_14),size_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_15|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_15),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("iactivefield|partial_construct|object_16|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_16),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>());
println!("iactivefield|partial_construct|object_17|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_17),size_of::<&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_18|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_18),size_of::<crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|partial_construct|object_19|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_19),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_20|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_20),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>());
println!("iactivefield|partial_construct|object_21|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_21),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("iactivefield|partial_construct|object_22|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_22),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("iactivefield|partial_construct|object_23|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_23),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_24|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_24),size_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|partial_construct|object_25|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_25),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_construct|object_26|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_26),size_of::<crate::experimental_swift_reactor::cache::CacheConstructionFailure>(),align_of::<crate::experimental_swift_reactor::cache::CacheConstructionFailure>());
println!("iactivefield|partial_construct|object_27|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_27),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_construct|object_28|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_28),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::AdoptedProof>>());
println!("iactivefield|partial_construct|object_30|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_30),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_31|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_31),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_32|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_32),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_33|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_33),size_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_34|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_34),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::cache::SwiftFunctionCache, crate::experimental_swift_reactor::cache::CacheConstructionFailure>>>());
println!("iactivefield|partial_construct|object_35|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_35),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_36|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_36),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_37|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_37),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_38|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_38),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_39|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_39),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_40|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_40),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_41|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_41),size_of::<crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<crate::experimental_swift_reactor::control::AdoptedProof>());
println!("iactivefield|partial_construct|object_42|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_42),size_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_43|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_43),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>>());
println!("iactivefield|partial_construct|object_44|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_44),size_of::<std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_45|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_45),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_46|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_46),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_47|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_47),size_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_48|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_48),size_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_49|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_49),size_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_50|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_50),size_of::<&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_51|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_51),size_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_52|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_52),size_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_53|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_53),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_wasi::accounted::AccountedWasi, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_54|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_54),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_55|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_55),size_of::<crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|partial_construct|object_56|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_56),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_construct|object_57|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_57),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_58|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_58),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_59|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_59),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_60|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_60),size_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_61|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_61),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_62|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_62),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_63|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_63),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_64|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_64),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_65|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_65),size_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>(),align_of::<crate::experimental_wasi::accounted::WasiConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_66|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_66),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_67|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_67),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_68|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_68),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_69|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_69),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>>());
println!("iactivefield|partial_construct|object_70|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_70),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_71|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_71),size_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>(),align_of::<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>());
println!("iactivefield|partial_construct|object_72|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_72),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_construct|object_73|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_73),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_construct|object_74|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_74),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|partial_construct|object_75|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_75),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_construct|object_76|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_76),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_construct|object_77|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_77),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_78|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_78),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_79|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_79),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_80|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_80),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_81|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_81),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_82|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_82),size_of::<&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_83|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_83),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_84|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_84),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_85|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_85),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_86|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_86),size_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<&'static mut std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_87|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_87),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_88|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_88),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|partial_construct|object_89|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_89),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|partial_construct|object_90|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_90),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_91|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_91),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_92|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_92),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_93|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_93),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("iactivefield|partial_construct|object_94|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_94),size_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_swift_reactor::execution::SwiftExecutionState, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|partial_construct|object_95|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_95),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_96|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_96),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_construct|object_97|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_97),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_construct|object_98|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_98),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_construct|object_99|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_99),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_construct|object_100|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_100),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_construct|object_101|{}|{}|{}",offset_of!(ActiveSupplementPartialConstruct,object_101),size_of::<bool>(),align_of::<bool>());
println!("iactive|partial_cleanup_failed|{}|{}",size_of::<ActiveSupplementPartialCleanupFailed>(),align_of::<ActiveSupplementPartialCleanupFailed>());
println!("iactivefield|partial_cleanup_failed|object_0|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_cleanup_failed|object_1|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_1),size_of::<PartialInstance>(),align_of::<PartialInstance>());
println!("iactivefield|partial_cleanup_failed|object_2|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|partial_cleanup_failed|object_3|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_3),size_of::<super::control::SwiftRunFailure>(),align_of::<super::control::SwiftRunFailure>());
println!("iactivefield|partial_cleanup_failed|object_4|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_4),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_5|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_5),size_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|partial_cleanup_failed|object_6|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_6),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::RuntimeControl>>());
println!("iactivefield|partial_cleanup_failed|object_7|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_7),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|partial_cleanup_failed|object_8|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_8),size_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|partial_cleanup_failed|object_9|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_9),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::execution::SwiftExecutionState>>());
println!("iactivefield|partial_cleanup_failed|object_10|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_10),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_cleanup_failed|object_11|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_11),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|partial_cleanup_failed|object_12|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_12),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|partial_cleanup_failed|object_13|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_13),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_14|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_14),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_15|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_15),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|partial_cleanup_failed|object_16|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_16),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|partial_cleanup_failed|object_17|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_17),size_of::<&'static std::vec::Vec<u8>>(),align_of::<&'static std::vec::Vec<u8>>());
println!("iactivefield|partial_cleanup_failed|object_18|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_18),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_cleanup_failed|object_19|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_19),size_of::<()>(),align_of::<()>());
println!("iactivefield|partial_cleanup_failed|object_20|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_20),size_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<&'static mut crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|partial_cleanup_failed|object_21|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_21),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_22|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_22),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_23|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_23),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_24|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_24),size_of::<crate::experimental_swift_reactor::control::Live>(),align_of::<crate::experimental_swift_reactor::control::Live>());
println!("iactivefield|partial_cleanup_failed|object_25|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_25),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|partial_cleanup_failed|object_26|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_26),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactivefield|partial_cleanup_failed|object_27|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_27),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|partial_cleanup_failed|object_28|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_28),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|partial_cleanup_failed|object_29|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_29),size_of::<()>(),align_of::<()>());
println!("iactivefield|partial_cleanup_failed|object_30|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_30),size_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>(),align_of::<crate::experimental_swift_reactor::execution::SwiftExecutionState>());
println!("iactivefield|partial_cleanup_failed|object_31|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_31),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_32|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_32),size_of::<()>(),align_of::<()>());
println!("iactivefield|partial_cleanup_failed|object_33|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_33),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_cleanup_failed|object_34|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_34),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_cleanup_failed|object_35|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_35),size_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_36|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_36),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_cleanup_failed|object_37|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_37),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_38|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_38),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_39|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_39),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_40|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_40),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_cleanup_failed|object_41|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_41),size_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheCleanupTail<'static>>());
println!("iactivefield|partial_cleanup_failed|object_42|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_42),size_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_cleanup_failed|object_43|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_43),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::cache::SwiftFunctionCache>>());
println!("iactivefield|partial_cleanup_failed|object_44|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_44),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_45|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_45),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_cleanup_failed|object_46|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_46),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_47|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_47),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|partial_cleanup_failed|object_48|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_48),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_49|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_49),size_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_50|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_50),size_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_51|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_51),size_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<&'static mut std::option::Option<crate::experimental_wasi::accounted::AccountedWasi>>());
println!("iactivefield|partial_cleanup_failed|object_52|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_52),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|partial_cleanup_failed|object_53|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_53),size_of::<crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<crate::experimental_wasi::accounted::AccountedWasi>());
println!("iactivefield|partial_cleanup_failed|object_54|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_54),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_55|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_55),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_56|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_56),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_57|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_57),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_58|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_58),size_of::<crate::experimental_swift_reactor::execution::PartialInstance>(),align_of::<crate::experimental_swift_reactor::execution::PartialInstance>());
println!("iactivefield|partial_cleanup_failed|object_59|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_59),size_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionCleanupTail>());
println!("iactivefield|partial_cleanup_failed|object_60|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_60),size_of::<crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|partial_cleanup_failed|object_61|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_61),size_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("iactivefield|partial_cleanup_failed|object_62|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_62),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_63|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_63),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_64|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_64),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("iactivefield|partial_cleanup_failed|object_65|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_65),size_of::<()>(),align_of::<()>());
println!("iactivefield|partial_cleanup_failed|object_66|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_66),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_67|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_67),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("iactivefield|partial_cleanup_failed|object_68|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_68),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|partial_cleanup_failed|object_69|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_69),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|partial_cleanup_failed|object_70|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_70),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("iactivefield|partial_cleanup_failed|object_71|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_71),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_cleanup_failed|object_72|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_72),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|partial_cleanup_failed|object_73|{}|{}|{}",offset_of!(ActiveSupplementPartialCleanupFailed,object_73),size_of::<bool>(),align_of::<bool>());
println!("iactive|work|{}|{}",size_of::<ActiveSupplementWork>(),align_of::<ActiveSupplementWork>());
println!("iactivefield|work|object_0|{}|{}|{}",offset_of!(ActiveSupplementWork,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|work|object_1|{}|{}|{}",offset_of!(ActiveSupplementWork,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|work|object_2|{}|{}|{}",offset_of!(ActiveSupplementWork,object_2),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("iactivefield|work|object_3|{}|{}|{}",offset_of!(ActiveSupplementWork,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|work|object_4|{}|{}|{}",offset_of!(ActiveSupplementWork,object_4),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|work|object_5|{}|{}|{}",offset_of!(ActiveSupplementWork,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|work|object_6|{}|{}|{}",offset_of!(ActiveSupplementWork,object_6),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|work|object_7|{}|{}|{}",offset_of!(ActiveSupplementWork,object_7),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|work|object_8|{}|{}|{}",offset_of!(ActiveSupplementWork,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|work|object_9|{}|{}|{}",offset_of!(ActiveSupplementWork,object_9),size_of::<crate::experimental_swift_reactor::control::Work>(),align_of::<crate::experimental_swift_reactor::control::Work>());
println!("iactivefield|work|object_10|{}|{}|{}",offset_of!(ActiveSupplementWork,object_10),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|work|object_11|{}|{}|{}",offset_of!(ActiveSupplementWork,object_11),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("iactivefield|work|object_12|{}|{}|{}",offset_of!(ActiveSupplementWork,object_12),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("iactive|arenas_formula|{}|{}",size_of::<ActiveSupplementArenasFormula>(),align_of::<ActiveSupplementArenasFormula>());
println!("iactivefield|arenas_formula|object_0|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_0),size_of::<std::option::Option<[usize; 6]>>(),align_of::<std::option::Option<[usize; 6]>>());
println!("iactivefield|arenas_formula|object_1|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_1),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_2|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_3|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_4|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_4),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_5|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_6|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_6),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_7|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_7),size_of::<[usize; 6]>(),align_of::<[usize; 6]>());
println!("iactivefield|arenas_formula|object_8|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_8),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_9|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_9),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_10|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_10),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_11|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_11),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_12|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_12),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_13|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_13),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_14|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_14),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_15|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_15),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_16|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_16),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_17|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_18|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_18),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_19|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_19),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_20|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_20),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_21|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_21),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_22|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_22),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_23|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_23),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_24|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_24),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_25|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_25),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_26|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_26),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_27|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_27),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_28|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_28),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_29|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_29),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_30|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_30),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_31|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_31),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_32|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_32),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, usize>>());
println!("iactivefield|arenas_formula|object_33|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_33),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|arenas_formula|object_34|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_34),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|arenas_formula|object_35|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_35),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|arenas_formula|object_36|{}|{}|{}",offset_of!(ActiveSupplementArenasFormula,object_36),size_of::<usize>(),align_of::<usize>());
println!("iactive|control_admit|{}|{}",size_of::<ActiveSupplementControlAdmit>(),align_of::<ActiveSupplementControlAdmit>());
println!("iactivefield|control_admit|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_0),size_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::control::ReservationTicket, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_admit|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_admit|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("iactivefield|control_admit|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|control_admit|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_admit|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_6),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|control_admit|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_7),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_admit|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_admit|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_admit|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_10),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_admit|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_11),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_admit|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_13),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_admit|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_14),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_admit|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_15),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_admit|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_16),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_admit|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_17),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_admit|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_18),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_admit|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_19),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_20|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_20),size_of::<(u64, bool)>(),align_of::<(u64, bool)>());
println!("iactivefield|control_admit|object_21|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_21),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_admit|object_22|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_22),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_23|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_23),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_24|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_24),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>());
println!("iactivefield|control_admit|object_25|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_25),size_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_admit|object_26|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_26),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_admit|object_27|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_27),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_admit|object_28|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_28),size_of::<(usize, usize)>(),align_of::<(usize, usize)>());
println!("iactivefield|control_admit|object_29|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_29),size_of::<()>(),align_of::<()>());
println!("iactivefield|control_admit|object_30|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_30),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("iactivefield|control_admit|object_31|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_31),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_32|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_32),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_33|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_33),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_admit|object_34|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_34),size_of::<crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<crate::experimental_swift_reactor::control::ReservationTicket>());
println!("iactivefield|control_admit|object_35|{}|{}|{}",offset_of!(ActiveSupplementControlAdmit,object_35),size_of::<u64>(),align_of::<u64>());
println!("iactive|control_exact|{}|{}",size_of::<ActiveSupplementControlExact>(),align_of::<ActiveSupplementControlExact>());
println!("iactivefield|control_exact|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_exact|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_exact|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_exact|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_exact|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|control_exact|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_exact|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_6),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|control_exact|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_7),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_exact|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_exact|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_exact|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_10),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_exact|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_11),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_exact|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_12),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_exact|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_13),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_exact|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_14),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_exact|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_15),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_exact|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_16),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_exact|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_17),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_exact|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_exact|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlExact,object_19),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactive|control_work|{}|{}",size_of::<ActiveSupplementControlWork>(),align_of::<ActiveSupplementControlWork>());
println!("iactivefield|control_work|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_work|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_work|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_2),size_of::<super::control::Work>(),align_of::<super::control::Work>());
println!("iactivefield|control_work|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_3),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|control_work|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_work|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_6),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|control_work|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_7),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_work|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_work|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_work|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_10),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_11),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_work|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_13),size_of::<(u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource)>(),align_of::<(u64, u64, crate::experimental_swift_reactor::control::SwiftRunResource)>());
println!("iactivefield|control_work|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_14),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_work|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_15),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_16),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_17),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_work|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_18),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_19),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_20|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_20),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_work|object_21|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_21),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_work|object_22|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_22),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_work|object_23|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_23),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_work|object_24|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_24),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_work|object_25|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_25),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_26|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_26),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work|object_27|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_27),size_of::<std::option::Option<u64>>(),align_of::<std::option::Option<u64>>());
println!("iactivefield|control_work|object_28|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_28),size_of::<std::option::Option<u64>>(),align_of::<std::option::Option<u64>>());
println!("iactivefield|control_work|object_29|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_29),size_of::<(&'static u64,)>(),align_of::<(&'static u64,)>());
println!("iactivefield|control_work|object_30|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_30),size_of::<&'static u64>(),align_of::<&'static u64>());
println!("iactivefield|control_work|object_31|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_31),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_work|object_32|{}|{}|{}",offset_of!(ActiveSupplementControlWork,object_32),size_of::<isize>(),align_of::<isize>());
println!("iactive|control_work_callback_0|{}|{}",size_of::<ActiveSupplementControlWorkCallback0>(),align_of::<ActiveSupplementControlWorkCallback0>());
println!("iactivefield|control_work_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_0),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_work_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_1),size_of::<(&'static u64,)>(),align_of::<(&'static u64,)>());
println!("iactivefield|control_work_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_2),size_of::<&'static u64>(),align_of::<&'static u64>());
println!("iactivefield|control_work_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_3),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_4),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_work_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlWorkCallback0,object_5),size_of::<&'static u64>(),align_of::<&'static u64>());
println!("iactive|control_add_live|{}|{}",size_of::<ActiveSupplementControlAddLive>(),align_of::<ActiveSupplementControlAddLive>());
println!("iactivefield|control_add_live|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_add_live|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_add_live|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_2),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("iactivefield|control_add_live|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("iactivefield|control_add_live|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_add_live|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_6),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("iactivefield|control_add_live|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_7),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_add_live|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_8),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_add_live|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_add_live|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_10),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_add_live|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_11),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_add_live|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_13),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_add_live|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_14),size_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>());
println!("iactivefield|control_add_live|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_15),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|control_add_live|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_16),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_add_live|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_add_live|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_19),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_add_live|object_20|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_20),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_add_live|object_21|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_21),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_add_live|object_22|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_22),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_add_live|object_23|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_23),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live|object_24|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_24),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_add_live|object_25|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_25),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|control_add_live|object_26|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_26),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|control_add_live|object_27|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_27),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_add_live|object_28|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_28),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_add_live|object_29|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_29),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live|object_30|{}|{}|{}",offset_of!(ActiveSupplementControlAddLive,object_30),size_of::<usize>(),align_of::<usize>());
println!("iactive|control_add_live_callback_0|{}|{}",size_of::<ActiveSupplementControlAddLiveCallback0>(),align_of::<ActiveSupplementControlAddLiveCallback0>());
println!("iactivefield|control_add_live_callback_0|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_0),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_add_live_callback_0|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("iactivefield|control_add_live_callback_0|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_2),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactivefield|control_add_live_callback_0|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live_callback_0|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_4),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_add_live_callback_0|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback0,object_5),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("iactive|control_add_live_callback_1|{}|{}",size_of::<ActiveSupplementControlAddLiveCallback1>(),align_of::<ActiveSupplementControlAddLiveCallback1>());
println!("iactivefield|control_add_live_callback_1|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback1,object_0),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_add_live_callback_1|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback1,object_1),size_of::<()>(),align_of::<()>());
println!("iactivefield|control_add_live_callback_1|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlAddLiveCallback1,object_2),size_of::<usize>(),align_of::<usize>());
println!("iactive|control_remove_live|{}|{}",size_of::<ActiveSupplementControlRemoveLive>(),align_of::<ActiveSupplementControlRemoveLive>());
println!("iactivefield|control_remove_live|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_remove_live|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_remove_live|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_2),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("iactivefield|control_remove_live|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_3),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_remove_live|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_remove_live|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_5),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_remove_live|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_6),size_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>());
println!("iactivefield|control_remove_live|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_7),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("iactivefield|control_remove_live|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_remove_live|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_9),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("iactivefield|control_remove_live|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_10),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_remove_live|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_11),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_remove_live|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_12),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_remove_live|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_13),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_remove_live|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlRemoveLive,object_14),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactive|control_live_parts|{}|{}",size_of::<ActiveSupplementControlLiveParts>(),align_of::<ActiveSupplementControlLiveParts>());
println!("iactivefield|control_live_parts|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_0),size_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftReservationUsage, usize, crate::experimental_swift_reactor::control::SwiftRunResource, crate::experimental_swift_reactor::control::SwiftRunFailureKind)>());
println!("iactivefield|control_live_parts|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_1),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("iactivefield|control_live_parts|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_2),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("iactivefield|control_live_parts|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_3),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_live_parts|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_5),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_6),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_7),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_live_parts|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_9),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_10),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_11),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_live_parts|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_13),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_14),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_15),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_live_parts|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_16),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_17),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_19),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_live_parts|object_20|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_20),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_21|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_21),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_22|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_22),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_23|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivefield|control_live_parts|object_24|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_24),size_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_parts|object_25|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_25),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_live_parts|object_26|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_26),size_of::<u32>(),align_of::<u32>());
println!("iactivefield|control_live_parts|object_27|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_27),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("iactivefield|control_live_parts|object_28|{}|{}|{}",offset_of!(ActiveSupplementControlLiveParts,object_28),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactive|control_live_mut|{}|{}",size_of::<ActiveSupplementControlLiveMut>(),align_of::<ActiveSupplementControlLiveMut>());
println!("iactivefield|control_live_mut|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_0),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_live_mut|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_2),size_of::<super::control::Live>(),align_of::<super::control::Live>());
println!("iactivefield|control_live_mut|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_4),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_live_mut|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_5),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_7),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_8),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_9),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_live_mut|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlLiveMut,object_10),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactive|control_refund|{}|{}",size_of::<ActiveSupplementControlRefund>(),align_of::<ActiveSupplementControlRefund>());
println!("iactivefield|control_refund|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|control_refund|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_refund|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_2),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|control_refund|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_3),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_refund|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_4),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_refund|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_5),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_refund|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_6),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_refund|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_7),size_of::<bool>(),align_of::<bool>());
println!("iactivefield|control_refund|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_8),size_of::<u64>(),align_of::<u64>());
println!("iactivefield|control_refund|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_9),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_refund|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_10),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("iactivefield|control_refund|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_11),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_refund|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_12),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_13|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_13),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_refund|object_14|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_14),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("iactivefield|control_refund|object_15|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_15),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactivefield|control_refund|object_16|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_16),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_17|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_17),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_refund|object_18|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_18),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_19|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_19),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_20|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_20),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_refund|object_21|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_21),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_22|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_22),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_refund|object_23|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("iactivefield|control_refund|object_24|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_24),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_25|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_25),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_26|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_26),size_of::<usize>(),align_of::<usize>());
println!("iactivefield|control_refund|object_27|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_27),size_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>(),align_of::<(std::option::Option<usize>, std::option::Option<usize>, std::option::Option<usize>)>());
println!("iactivefield|control_refund|object_28|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_28),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_refund|object_29|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_29),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_refund|object_30|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_30),size_of::<isize>(),align_of::<isize>());
println!("iactivefield|control_refund|object_31|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_31),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("iactivefield|control_refund|object_32|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_32),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>());
println!("iactivefield|control_refund|object_33|{}|{}|{}",offset_of!(ActiveSupplementControlRefund,object_33),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("iactive|drop_value|{}|{}",size_of::<ActiveSupplementDropValue>(),align_of::<ActiveSupplementDropValue>());
println!("iactivefield|drop_value|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_value|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_value|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_2),size_of::<Vec<Value>>(),align_of::<Vec<Value>>());
println!("iactivefield|drop_value|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_value|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_value|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropValue,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|drop_control|{}|{}",size_of::<ActiveSupplementDropControl>(),align_of::<ActiveSupplementDropControl>());
println!("iactivefield|drop_control|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_control|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_control|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_2),size_of::<Vec<Control>>(),align_of::<Vec<Control>>());
println!("iactivefield|drop_control|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_control|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_control|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropControl,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|drop_frame|{}|{}",size_of::<ActiveSupplementDropFrame>(),align_of::<ActiveSupplementDropFrame>());
println!("iactivefield|drop_frame|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_frame|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_frame|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_2),size_of::<Vec<SwiftFrame>>(),align_of::<Vec<SwiftFrame>>());
println!("iactivefield|drop_frame|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_frame|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_frame|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropFrame,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|drop_memory|{}|{}",size_of::<ActiveSupplementDropMemory>(),align_of::<ActiveSupplementDropMemory>());
println!("iactivefield|drop_memory|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_memory|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_memory|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_2),size_of::<Vec<u8>>(),align_of::<Vec<u8>>());
println!("iactivefield|drop_memory|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_memory|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_memory|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropMemory,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|drop_table|{}|{}",size_of::<ActiveSupplementDropTable>(),align_of::<ActiveSupplementDropTable>());
println!("iactivefield|drop_table|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_table|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_table|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_2),size_of::<Vec<Option<u32>>>(),align_of::<Vec<Option<u32>>>());
println!("iactivefield|drop_table|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_table|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_table|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropTable,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|drop_state|{}|{}",size_of::<ActiveSupplementDropState>(),align_of::<ActiveSupplementDropState>());
println!("iactivefield|drop_state|object_0|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("iactivefield|drop_state|object_1|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|drop_state|object_2|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_2),size_of::<SwiftExecutionState>(),align_of::<SwiftExecutionState>());
println!("iactivefield|drop_state|object_3|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_3),size_of::<super::control::ReservationTicket>(),align_of::<super::control::ReservationTicket>());
println!("iactivefield|drop_state|object_4|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|drop_state|object_5|{}|{}|{}",offset_of!(ActiveSupplementDropState,object_5),size_of::<()>(),align_of::<()>());
println!("iactive|control_cleanup_fault|{}|{}",size_of::<ActiveSupplementControlCleanupFault>(),align_of::<ActiveSupplementControlCleanupFault>());
println!("iactivefield|control_cleanup_fault|object_0|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("iactivefield|control_cleanup_fault|object_1|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("iactivefield|control_cleanup_fault|object_2|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_2),size_of::<super::control::SwiftCleanupInvariant>(),align_of::<super::control::SwiftCleanupInvariant>());
println!("iactivefield|control_cleanup_fault|object_3|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_3),size_of::<&'static str>(),align_of::<&'static str>());
println!("iactivefield|control_cleanup_fault|object_4|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("iactivefield|control_cleanup_fault|object_5|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_5),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("iactivefield|control_cleanup_fault|object_6|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_6),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("iactivefield|control_cleanup_fault|object_7|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_7),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("iactivefield|control_cleanup_fault|object_8|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunStage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunStage>());
println!("iactivefield|control_cleanup_fault|object_9|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_9),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("iactivefield|control_cleanup_fault|object_10|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_10),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("iactivefield|control_cleanup_fault|object_11|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_11),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("iactivefield|control_cleanup_fault|object_12|{}|{}|{}",offset_of!(ActiveSupplementControlCleanupFault,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("iactivetotal|{}|{}",size_of::<ConstructionActiveSupplement>(),align_of::<ConstructionActiveSupplement>());
}
