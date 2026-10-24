// Private retained-descriptor typed accounting proposal.
#[allow(dead_code)]
pub(crate) struct ConstructionPositiveDescriptor{
 class_0: [usize;42],
 class_1: [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Global>;8],
 class_2: [&'static std::vec::Vec<crate::experimental::metadata::Global>;4],
 class_3: [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Segment>;10],
 class_4: [&'static std::vec::Vec<crate::experimental::metadata::Segment>;4],
 class_5: [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Import>;8],
 class_6: [&'static std::vec::Vec<crate::experimental::metadata::Import>;4],
 class_7: [&'static [Type];5],
 class_8: [&'static crate::experimental::account::Buffer<Type>;3],
 class_9: [&'static std::vec::Vec<Type>;2],
 class_10: [std::option::Option<&'static crate::experimental::metadata::Global>;5],
 class_11: [&'static [crate::experimental::metadata::Global];2],
 class_12: [std::option::Option<&'static crate::experimental::metadata::Segment>;5],
 class_13: [&'static [crate::experimental::metadata::Segment];2],
 class_14: [std::option::Option<&'static crate::experimental::metadata::Signature>;3],
 class_15: [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Signature>;3],
 class_16: [&'static [crate::experimental::metadata::Signature];2],
 class_17: [&'static std::vec::Vec<crate::experimental::metadata::Signature>;2],
 class_18: [std::option::Option<&'static crate::experimental::metadata::Function>;3],
 class_19: [&'static crate::experimental::account::Buffer<crate::experimental::metadata::Function>;3],
 class_20: [&'static [crate::experimental::metadata::Function];2],
 class_21: [&'static std::vec::Vec<crate::experimental::metadata::Function>;2],
 class_22: [std::option::Option<&'static crate::experimental::metadata::Import>;3],
 class_23: [&'static [crate::experimental::metadata::Import];2],
 class_24: [&'static [u8];9],
 class_25: [crate::experimental::metadata::Span;5],
 class_26: [std::ops::Range<usize>;4],
 class_27: [u32;19],
 class_28: [(usize, bool);3],
 class_29: [std::option::Option<crate::experimental::metadata::Signature>;3],
 class_30: [&'static crate::experimental::metadata::Metadata<crate::experimental::metadata::SwiftDeclaration>;6],
 class_31: [bool;2],
 class_32: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Import>;1],
 class_33: [isize;9],
 class_34: [&'static crate::experimental::metadata::Import;1],
 class_35: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Function>;1],
 class_36: [&'static crate::experimental::metadata::Function;1],
 class_37: [Option<std::convert::Infallible>;9],
 class_38: [crate::experimental::metadata::Signature;3],
 class_39: [std::option::Option<crate::experimental::descriptors::SignatureView<'static>>;1],
 class_40: [&'static ValidatedSwiftReactor;13],
 class_41: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, crate::experimental::metadata::Signature>;1],
 class_42: [crate::experimental::descriptors::SignatureView<'static>;1],
 class_43: [std::option::Option<Type>;1],
 class_44: [std::option::Option<crate::experimental::descriptors::GlobalView<'static>>;1],
 class_45: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Global>;2],
 class_46: [&'static crate::experimental::metadata::Global;2],
 class_47: [crate::experimental::descriptors::GlobalView<'static>;1],
 class_48: [Type;1],
 class_49: [&'static std::boxed::Box<[u8]>;2],
 class_50: [std::boxed::Box<[u8]>;2],
 class_51: [*const [u8];2],
 class_52: [std::option::Option<usize>;1],
 class_53: [std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>;2],
 class_54: [crate::experimental::descriptors::SegmentExecutionView<'static>;3],
 class_55: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Segment>;2],
 class_56: [&'static crate::experimental::metadata::Segment;5],
 class_57: [std::option::Option<crate::experimental::descriptors::MemoryExecutionView>;1],
 class_58: [std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, (u32, u32)>;2],
 class_59: [std::option::Option<(u32, u32)>;4],
 class_60: [(u32, u32);2],
 class_61: [crate::experimental::descriptors::MemoryExecutionView;1],
 class_62: [std::option::Option<u32>;2],
 class_63: [std::option::Option<crate::experimental::descriptors::TableExecutionView>;1],
 class_64: [crate::experimental::descriptors::TableExecutionView;1],
}
pub(crate)const CONSTRUCTION_POSITIVE_DESCRIPTOR_BYTES:usize=std::mem::size_of::<ConstructionPositiveDescriptor>();
pub(crate)fn independent_descriptor_accounting_probe(){use std::mem::{size_of,align_of,offset_of};
println!("positiveclass|descriptor|class_0|42|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_0),size_of::<usize>(),align_of::<usize>());
println!("positiveclass|descriptor|class_1|8|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_1),size_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Global>>(),align_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Global>>());
println!("positiveclass|descriptor|class_2|4|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_2),size_of::<&'static std::vec::Vec<crate::experimental::metadata::Global>>(),align_of::<&'static std::vec::Vec<crate::experimental::metadata::Global>>());
println!("positiveclass|descriptor|class_3|10|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_3),size_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Segment>>(),align_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Segment>>());
println!("positiveclass|descriptor|class_4|4|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_4),size_of::<&'static std::vec::Vec<crate::experimental::metadata::Segment>>(),align_of::<&'static std::vec::Vec<crate::experimental::metadata::Segment>>());
println!("positiveclass|descriptor|class_5|8|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_5),size_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Import>>(),align_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Import>>());
println!("positiveclass|descriptor|class_6|4|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_6),size_of::<&'static std::vec::Vec<crate::experimental::metadata::Import>>(),align_of::<&'static std::vec::Vec<crate::experimental::metadata::Import>>());
println!("positiveclass|descriptor|class_7|5|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_7),size_of::<&'static [Type]>(),align_of::<&'static [Type]>());
println!("positiveclass|descriptor|class_8|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_8),size_of::<&'static crate::experimental::account::Buffer<Type>>(),align_of::<&'static crate::experimental::account::Buffer<Type>>());
println!("positiveclass|descriptor|class_9|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_9),size_of::<&'static std::vec::Vec<Type>>(),align_of::<&'static std::vec::Vec<Type>>());
println!("positiveclass|descriptor|class_10|5|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_10),size_of::<std::option::Option<&'static crate::experimental::metadata::Global>>(),align_of::<std::option::Option<&'static crate::experimental::metadata::Global>>());
println!("positiveclass|descriptor|class_11|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_11),size_of::<&'static [crate::experimental::metadata::Global]>(),align_of::<&'static [crate::experimental::metadata::Global]>());
println!("positiveclass|descriptor|class_12|5|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_12),size_of::<std::option::Option<&'static crate::experimental::metadata::Segment>>(),align_of::<std::option::Option<&'static crate::experimental::metadata::Segment>>());
println!("positiveclass|descriptor|class_13|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_13),size_of::<&'static [crate::experimental::metadata::Segment]>(),align_of::<&'static [crate::experimental::metadata::Segment]>());
println!("positiveclass|descriptor|class_14|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_14),size_of::<std::option::Option<&'static crate::experimental::metadata::Signature>>(),align_of::<std::option::Option<&'static crate::experimental::metadata::Signature>>());
println!("positiveclass|descriptor|class_15|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_15),size_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Signature>>(),align_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Signature>>());
println!("positiveclass|descriptor|class_16|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_16),size_of::<&'static [crate::experimental::metadata::Signature]>(),align_of::<&'static [crate::experimental::metadata::Signature]>());
println!("positiveclass|descriptor|class_17|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_17),size_of::<&'static std::vec::Vec<crate::experimental::metadata::Signature>>(),align_of::<&'static std::vec::Vec<crate::experimental::metadata::Signature>>());
println!("positiveclass|descriptor|class_18|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_18),size_of::<std::option::Option<&'static crate::experimental::metadata::Function>>(),align_of::<std::option::Option<&'static crate::experimental::metadata::Function>>());
println!("positiveclass|descriptor|class_19|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_19),size_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Function>>(),align_of::<&'static crate::experimental::account::Buffer<crate::experimental::metadata::Function>>());
println!("positiveclass|descriptor|class_20|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_20),size_of::<&'static [crate::experimental::metadata::Function]>(),align_of::<&'static [crate::experimental::metadata::Function]>());
println!("positiveclass|descriptor|class_21|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_21),size_of::<&'static std::vec::Vec<crate::experimental::metadata::Function>>(),align_of::<&'static std::vec::Vec<crate::experimental::metadata::Function>>());
println!("positiveclass|descriptor|class_22|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_22),size_of::<std::option::Option<&'static crate::experimental::metadata::Import>>(),align_of::<std::option::Option<&'static crate::experimental::metadata::Import>>());
println!("positiveclass|descriptor|class_23|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_23),size_of::<&'static [crate::experimental::metadata::Import]>(),align_of::<&'static [crate::experimental::metadata::Import]>());
println!("positiveclass|descriptor|class_24|9|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_24),size_of::<&'static [u8]>(),align_of::<&'static [u8]>());
println!("positiveclass|descriptor|class_25|5|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_25),size_of::<crate::experimental::metadata::Span>(),align_of::<crate::experimental::metadata::Span>());
println!("positiveclass|descriptor|class_26|4|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_26),size_of::<std::ops::Range<usize>>(),align_of::<std::ops::Range<usize>>());
println!("positiveclass|descriptor|class_27|19|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_27),size_of::<u32>(),align_of::<u32>());
println!("positiveclass|descriptor|class_28|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_28),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("positiveclass|descriptor|class_29|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_29),size_of::<std::option::Option<crate::experimental::metadata::Signature>>(),align_of::<std::option::Option<crate::experimental::metadata::Signature>>());
println!("positiveclass|descriptor|class_30|6|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_30),size_of::<&'static crate::experimental::metadata::Metadata<crate::experimental::metadata::SwiftDeclaration>>(),align_of::<&'static crate::experimental::metadata::Metadata<crate::experimental::metadata::SwiftDeclaration>>());
println!("positiveclass|descriptor|class_31|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_31),size_of::<bool>(),align_of::<bool>());
println!("positiveclass|descriptor|class_32|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_32),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Import>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Import>>());
println!("positiveclass|descriptor|class_33|9|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_33),size_of::<isize>(),align_of::<isize>());
println!("positiveclass|descriptor|class_34|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_34),size_of::<&'static crate::experimental::metadata::Import>(),align_of::<&'static crate::experimental::metadata::Import>());
println!("positiveclass|descriptor|class_35|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_35),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Function>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Function>>());
println!("positiveclass|descriptor|class_36|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_36),size_of::<&'static crate::experimental::metadata::Function>(),align_of::<&'static crate::experimental::metadata::Function>());
println!("positiveclass|descriptor|class_37|9|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_37),size_of::<Option<std::convert::Infallible>>(),align_of::<Option<std::convert::Infallible>>());
println!("positiveclass|descriptor|class_38|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_38),size_of::<crate::experimental::metadata::Signature>(),align_of::<crate::experimental::metadata::Signature>());
println!("positiveclass|descriptor|class_39|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_39),size_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SignatureView<'static>>>());
println!("positiveclass|descriptor|class_40|13|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_40),size_of::<&'static ValidatedSwiftReactor>(),align_of::<&'static ValidatedSwiftReactor>());
println!("positiveclass|descriptor|class_41|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_41),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, crate::experimental::metadata::Signature>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, crate::experimental::metadata::Signature>>());
println!("positiveclass|descriptor|class_42|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_42),size_of::<crate::experimental::descriptors::SignatureView<'static>>(),align_of::<crate::experimental::descriptors::SignatureView<'static>>());
println!("positiveclass|descriptor|class_43|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_43),size_of::<std::option::Option<Type>>(),align_of::<std::option::Option<Type>>());
println!("positiveclass|descriptor|class_44|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_44),size_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::GlobalView<'static>>>());
println!("positiveclass|descriptor|class_45|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_45),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Global>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Global>>());
println!("positiveclass|descriptor|class_46|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_46),size_of::<&'static crate::experimental::metadata::Global>(),align_of::<&'static crate::experimental::metadata::Global>());
println!("positiveclass|descriptor|class_47|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_47),size_of::<crate::experimental::descriptors::GlobalView<'static>>(),align_of::<crate::experimental::descriptors::GlobalView<'static>>());
println!("positiveclass|descriptor|class_48|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_48),size_of::<Type>(),align_of::<Type>());
println!("positiveclass|descriptor|class_49|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_49),size_of::<&'static std::boxed::Box<[u8]>>(),align_of::<&'static std::boxed::Box<[u8]>>());
println!("positiveclass|descriptor|class_50|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_50),size_of::<std::boxed::Box<[u8]>>(),align_of::<std::boxed::Box<[u8]>>());
println!("positiveclass|descriptor|class_51|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_51),size_of::<*const [u8]>(),align_of::<*const [u8]>());
println!("positiveclass|descriptor|class_52|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_52),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("positiveclass|descriptor|class_53|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_53),size_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>(),align_of::<std::option::Option<crate::experimental::descriptors::SegmentExecutionView<'static>>>());
println!("positiveclass|descriptor|class_54|3|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_54),size_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>(),align_of::<crate::experimental::descriptors::SegmentExecutionView<'static>>());
println!("positiveclass|descriptor|class_55|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_55),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Segment>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, &'static crate::experimental::metadata::Segment>>());
println!("positiveclass|descriptor|class_56|5|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_56),size_of::<&'static crate::experimental::metadata::Segment>(),align_of::<&'static crate::experimental::metadata::Segment>());
println!("positiveclass|descriptor|class_57|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_57),size_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::MemoryExecutionView>>());
println!("positiveclass|descriptor|class_58|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_58),size_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, (u32, u32)>>(),align_of::<std::ops::ControlFlow<std::option::Option<std::convert::Infallible>, (u32, u32)>>());
println!("positiveclass|descriptor|class_59|4|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_59),size_of::<std::option::Option<(u32, u32)>>(),align_of::<std::option::Option<(u32, u32)>>());
println!("positiveclass|descriptor|class_60|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_60),size_of::<(u32, u32)>(),align_of::<(u32, u32)>());
println!("positiveclass|descriptor|class_61|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_61),size_of::<crate::experimental::descriptors::MemoryExecutionView>(),align_of::<crate::experimental::descriptors::MemoryExecutionView>());
println!("positiveclass|descriptor|class_62|2|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_62),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("positiveclass|descriptor|class_63|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_63),size_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>(),align_of::<std::option::Option<crate::experimental::descriptors::TableExecutionView>>());
println!("positiveclass|descriptor|class_64|1|{}|{}|{}",offset_of!(ConstructionPositiveDescriptor,class_64),size_of::<crate::experimental::descriptors::TableExecutionView>(),align_of::<crate::experimental::descriptors::TableExecutionView>());
println!("positivetotal|descriptor|{}|{}",size_of::<ConstructionPositiveDescriptor>(),align_of::<ConstructionPositiveDescriptor>());
}
