pub(super) struct HostPermanentPositions {
    fixed_caller_storage_source: FrameOperationStorage<'static>,
    fixed_caller_storage_argument: FrameOperationStorage<'static>,
    fixed_caller_storage_returned: FrameOperationStorage<'static>,
    fixed_caller_storage_caller: FrameOperationStorage<'static>,
    fixed_completion_storage_source: FrameOperationStorage<'static>,
    fixed_completion_storage_argument: FrameOperationStorage<'static>,
    fixed_completion_storage_returned: FrameOperationStorage<'static>,
    fixed_completion_storage_caller: FrameOperationStorage<'static>,
    fixed_completion_drop_tuple_source: (ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>),
    fixed_completion_drop_tuple_argument: (ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>),
    fixed_completion_drop_tuple_returned: (ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>),
    fixed_completion_drop_tuple_caller: (ExecutionParts<'static,SwiftMode>,FrameOperationStorage<'static>),
    fixed_outcome_source: Option<Result<(),SwiftRunFailure>>,
    fixed_outcome_argument: Option<Result<(),SwiftRunFailure>>,
    fixed_outcome_returned: Option<Result<(),SwiftRunFailure>>,
    fixed_outcome_caller: Option<Result<(),SwiftRunFailure>>,
    fixed_outcome_result_source: Result<(),SwiftRunFailure>,
    fixed_outcome_result_argument: Result<(),SwiftRunFailure>,
    fixed_outcome_result_returned: Result<(),SwiftRunFailure>,
    fixed_outcome_result_caller: Result<(),SwiftRunFailure>,
    fixed_outer_publication_source: Result<(),SwiftRunFailure>,
    fixed_outer_publication_argument: Result<(),SwiftRunFailure>,
    fixed_outer_publication_returned: Result<(),SwiftRunFailure>,
    fixed_outer_publication_caller: Result<(),SwiftRunFailure>,
    fixed_first_failure_source: Option<SwiftRunFailure>,
    fixed_first_failure_argument: Option<SwiftRunFailure>,
    fixed_first_failure_returned: Option<SwiftRunFailure>,
    fixed_first_failure_caller: Option<SwiftRunFailure>,
    fixed_failure_source: SwiftRunFailure,
    fixed_failure_argument: SwiftRunFailure,
    fixed_failure_returned: SwiftRunFailure,
    fixed_failure_caller: SwiftRunFailure,
    fixed_drain_report_source: FrameDrainReport,
    fixed_drain_report_argument: FrameDrainReport,
    fixed_drain_report_returned: FrameDrainReport,
    fixed_drain_report_caller: FrameDrainReport,
    fixed_completion_source: FrameCompletion,
    fixed_completion_argument: FrameCompletion,
    fixed_completion_returned: FrameCompletion,
    fixed_completion_caller: FrameCompletion,
    fixed_after_cleanup_source: Option<SwiftRunUsage>,
    fixed_after_cleanup_argument: Option<SwiftRunUsage>,
    fixed_after_cleanup_returned: Option<SwiftRunUsage>,
    fixed_after_cleanup_caller: Option<SwiftRunUsage>,
}
pub(super) struct HostActivePositions {
    mir_production_0_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_4_source: bool,
    mir_production_0_4_argument: bool,
    mir_production_0_4_returned: bool,
    mir_production_0_4_caller: bool,
    mir_production_0_5_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_5_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_5_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_5_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_6_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_0_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_0_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_0_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_0_6_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_0_6_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_0_6_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_0_6_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_0_7_source: (),
    mir_production_0_7_argument: (),
    mir_production_0_7_returned: (),
    mir_production_0_7_caller: (),
    mir_production_0_8_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_8_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_8_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_8_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_0_8_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_0_8_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_0_8_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_0_8_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_9_source: bool,
    mir_production_0_9_argument: bool,
    mir_production_0_9_returned: bool,
    mir_production_0_9_caller: bool,
    mir_production_0_10_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_10_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_10_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_10_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_0_11_source: (),
    mir_production_0_11_argument: (),
    mir_production_0_11_returned: (),
    mir_production_0_11_caller: (),
    mir_production_0_12_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_12_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_12_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_12_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_0_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_0_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_0_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_0_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_0_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_0_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_0_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_0_2_source: u32,
    mir_production_0_2_argument: u32,
    mir_production_0_2_returned: u32,
    mir_production_0_2_caller: u32,
    alias_production_0_2_0_function_source: u32,
    alias_production_0_2_0_function_argument: u32,
    alias_production_0_2_0_function_returned: u32,
    alias_production_0_2_0_function_caller: u32,
    mir_production_0_3_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_3_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_3_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_0_3_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_0_3_0_returned_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_0_3_0_returned_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_0_3_0_returned_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    alias_production_0_3_0_returned_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    literal_production_0_0_source: &'static str,
    literal_production_0_0_argument: &'static str,
    literal_production_0_0_returned: &'static str,
    literal_production_0_0_caller: &'static str,
    mir_production_1_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_3_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_3_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_3_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_3_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_4_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_4_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_4_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_4_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_5_source: isize,
    mir_production_1_5_argument: isize,
    mir_production_1_5_returned: isize,
    mir_production_1_5_caller: isize,
    mir_production_1_6_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_6_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_6_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_6_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_6_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_6_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_6_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_6_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_7_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    mir_production_1_7_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    mir_production_1_7_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    mir_production_1_7_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    mir_production_1_8_source: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_8_argument: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_8_returned: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_8_caller: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_9_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_9_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_9_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_9_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_10_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_10_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_10_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_10_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_11_source: isize,
    mir_production_1_11_argument: isize,
    mir_production_1_11_returned: isize,
    mir_production_1_11_caller: isize,
    mir_production_1_12_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_12_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_12_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_13_source: crate::experimental_wasi::WasiUsage,
    mir_production_1_13_argument: crate::experimental_wasi::WasiUsage,
    mir_production_1_13_returned: crate::experimental_wasi::WasiUsage,
    mir_production_1_13_caller: crate::experimental_wasi::WasiUsage,
    alias_production_1_13_0_val_source: crate::experimental_wasi::WasiUsage,
    alias_production_1_13_0_val_argument: crate::experimental_wasi::WasiUsage,
    alias_production_1_13_0_val_returned: crate::experimental_wasi::WasiUsage,
    alias_production_1_13_0_val_caller: crate::experimental_wasi::WasiUsage,
    mir_production_1_14_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_14_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_14_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_14_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_15_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_15_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_15_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_15_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_16_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_16_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_16_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_16_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_17_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_1_17_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_1_17_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_1_17_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_1_18_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_18_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_18_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_18_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_19_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_19_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_19_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_19_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_20_source: isize,
    mir_production_1_20_argument: isize,
    mir_production_1_20_returned: isize,
    mir_production_1_20_caller: isize,
    mir_production_1_21_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_21_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_21_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_21_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_21_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_21_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_21_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_21_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_22_source: crate::experimental_wasi::WasiFunction,
    mir_production_1_22_argument: crate::experimental_wasi::WasiFunction,
    mir_production_1_22_returned: crate::experimental_wasi::WasiFunction,
    mir_production_1_22_caller: crate::experimental_wasi::WasiFunction,
    alias_production_1_22_0_descriptor_source: crate::experimental_wasi::WasiFunction,
    alias_production_1_22_0_descriptor_argument: crate::experimental_wasi::WasiFunction,
    alias_production_1_22_0_descriptor_returned: crate::experimental_wasi::WasiFunction,
    alias_production_1_22_0_descriptor_caller: crate::experimental_wasi::WasiFunction,
    mir_production_1_23_source: usize,
    mir_production_1_23_argument: usize,
    mir_production_1_23_returned: usize,
    mir_production_1_23_caller: usize,
    alias_production_1_23_0_params_source: usize,
    alias_production_1_23_0_params_argument: usize,
    alias_production_1_23_0_params_returned: usize,
    alias_production_1_23_0_params_caller: usize,
    mir_production_1_24_source: (crate::experimental_wasi::WasiFunction, usize),
    mir_production_1_24_argument: (crate::experimental_wasi::WasiFunction, usize),
    mir_production_1_24_returned: (crate::experimental_wasi::WasiFunction, usize),
    mir_production_1_24_caller: (crate::experimental_wasi::WasiFunction, usize),
    mir_production_1_25_source: std::option::Option<crate::experimental_wasi::WasiFunction>,
    mir_production_1_25_argument: std::option::Option<crate::experimental_wasi::WasiFunction>,
    mir_production_1_25_returned: std::option::Option<crate::experimental_wasi::WasiFunction>,
    mir_production_1_25_caller: std::option::Option<crate::experimental_wasi::WasiFunction>,
    mir_production_1_26_source: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    mir_production_1_26_argument: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    mir_production_1_26_returned: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    mir_production_1_26_caller: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    mir_production_1_27_source: &'static [crate::experimental_wasi::WasiFunction],
    mir_production_1_27_argument: &'static [crate::experimental_wasi::WasiFunction],
    mir_production_1_27_returned: &'static [crate::experimental_wasi::WasiFunction],
    mir_production_1_27_caller: &'static [crate::experimental_wasi::WasiFunction],
    mir_production_1_28_source: &'static [crate::experimental_wasi::WasiFunction; 34],
    mir_production_1_28_argument: &'static [crate::experimental_wasi::WasiFunction; 34],
    mir_production_1_28_returned: &'static [crate::experimental_wasi::WasiFunction; 34],
    mir_production_1_28_caller: &'static [crate::experimental_wasi::WasiFunction; 34],
    mir_production_1_29_source: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_29_argument: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_29_returned: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_29_caller: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_30_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_30_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_30_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_30_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_31_source: usize,
    mir_production_1_31_argument: usize,
    mir_production_1_31_returned: usize,
    mir_production_1_31_caller: usize,
    mir_production_1_32_source: isize,
    mir_production_1_32_argument: isize,
    mir_production_1_32_returned: isize,
    mir_production_1_32_caller: isize,
    mir_production_1_33_source: crate::experimental_wasi::WasiFunction,
    mir_production_1_33_argument: crate::experimental_wasi::WasiFunction,
    mir_production_1_33_returned: crate::experimental_wasi::WasiFunction,
    mir_production_1_33_caller: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_0_descriptor_source: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_0_descriptor_argument: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_0_descriptor_returned: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_0_descriptor_caller: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_1_descriptor_source: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_1_descriptor_argument: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_1_descriptor_returned: crate::experimental_wasi::WasiFunction,
    alias_production_1_33_1_descriptor_caller: crate::experimental_wasi::WasiFunction,
    mir_production_1_34_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_34_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_34_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_34_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_36_source: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    mir_production_1_36_argument: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    mir_production_1_36_returned: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    mir_production_1_36_caller: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    mir_production_1_37_source: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_37_argument: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_37_returned: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_37_caller: &'static crate::experimental::swift::ValidatedSwiftReactor,
    mir_production_1_38_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_38_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_38_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_38_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_39_source: isize,
    mir_production_1_39_argument: isize,
    mir_production_1_39_returned: isize,
    mir_production_1_39_caller: isize,
    mir_production_1_41_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_41_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_41_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_41_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_42_source: bool,
    mir_production_1_42_argument: bool,
    mir_production_1_42_returned: bool,
    mir_production_1_42_caller: bool,
    mir_production_1_43_source: &'static &'static [Type],
    mir_production_1_43_argument: &'static &'static [Type],
    mir_production_1_43_returned: &'static &'static [Type],
    mir_production_1_43_caller: &'static &'static [Type],
    mir_production_1_44_source: &'static &'static [Type],
    mir_production_1_44_argument: &'static &'static [Type],
    mir_production_1_44_returned: &'static &'static [Type],
    mir_production_1_44_caller: &'static &'static [Type],
    mir_production_1_45_source: &'static [Type],
    mir_production_1_45_argument: &'static [Type],
    mir_production_1_45_returned: &'static [Type],
    mir_production_1_45_caller: &'static [Type],
    mir_production_1_46_source: bool,
    mir_production_1_46_argument: bool,
    mir_production_1_46_returned: bool,
    mir_production_1_46_caller: bool,
    mir_production_1_47_source: &'static &'static [Type],
    mir_production_1_47_argument: &'static &'static [Type],
    mir_production_1_47_returned: &'static &'static [Type],
    mir_production_1_47_caller: &'static &'static [Type],
    mir_production_1_48_source: &'static [Type],
    mir_production_1_48_argument: &'static [Type],
    mir_production_1_48_returned: &'static [Type],
    mir_production_1_48_caller: &'static [Type],
    mir_production_1_49_source: &'static std::option::Option<Type>,
    mir_production_1_49_argument: &'static std::option::Option<Type>,
    mir_production_1_49_returned: &'static std::option::Option<Type>,
    mir_production_1_49_caller: &'static std::option::Option<Type>,
    mir_production_1_50_source: &'static &'static [Type],
    mir_production_1_50_argument: &'static &'static [Type],
    mir_production_1_50_returned: &'static &'static [Type],
    mir_production_1_50_caller: &'static &'static [Type],
    mir_production_1_51_source: &'static [Type],
    mir_production_1_51_argument: &'static [Type],
    mir_production_1_51_returned: &'static [Type],
    mir_production_1_51_caller: &'static [Type],
    mir_production_1_52_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_52_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_52_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_52_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_53_source: usize,
    mir_production_1_53_argument: usize,
    mir_production_1_53_returned: usize,
    mir_production_1_53_caller: usize,
    mir_production_1_54_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_54_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_54_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_54_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_55_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_55_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_55_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_55_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_56_source: isize,
    mir_production_1_56_argument: isize,
    mir_production_1_56_returned: isize,
    mir_production_1_56_caller: isize,
    mir_production_1_58_source: std::option::Option<usize>,
    mir_production_1_58_argument: std::option::Option<usize>,
    mir_production_1_58_returned: std::option::Option<usize>,
    mir_production_1_58_caller: std::option::Option<usize>,
    mir_production_1_59_source: usize,
    mir_production_1_59_argument: usize,
    mir_production_1_59_returned: usize,
    mir_production_1_59_caller: usize,
    mir_production_1_60_source: &'static std::vec::Vec<Value>,
    mir_production_1_60_argument: &'static std::vec::Vec<Value>,
    mir_production_1_60_returned: &'static std::vec::Vec<Value>,
    mir_production_1_60_caller: &'static std::vec::Vec<Value>,
    mir_production_1_61_source: isize,
    mir_production_1_61_argument: isize,
    mir_production_1_61_returned: isize,
    mir_production_1_61_caller: isize,
    mir_production_1_63_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_63_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_63_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_63_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_64_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_64_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_64_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_64_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_65_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_1_65_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_1_65_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_1_65_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_1_66_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_66_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_66_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_66_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_67_source: isize,
    mir_production_1_67_argument: isize,
    mir_production_1_67_returned: isize,
    mir_production_1_67_caller: isize,
    mir_production_1_69_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_69_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_69_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_69_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_70_source: bool,
    mir_production_1_70_argument: bool,
    mir_production_1_70_returned: bool,
    mir_production_1_70_caller: bool,
    mir_production_1_71_source: usize,
    mir_production_1_71_argument: usize,
    mir_production_1_71_returned: usize,
    mir_production_1_71_caller: usize,
    mir_production_1_72_source: usize,
    mir_production_1_72_argument: usize,
    mir_production_1_72_returned: usize,
    mir_production_1_72_caller: usize,
    mir_production_1_73_source: bool,
    mir_production_1_73_argument: bool,
    mir_production_1_73_returned: bool,
    mir_production_1_73_caller: bool,
    mir_production_1_74_source: usize,
    mir_production_1_74_argument: usize,
    mir_production_1_74_returned: usize,
    mir_production_1_74_caller: usize,
    mir_production_1_75_source: bool,
    mir_production_1_75_argument: bool,
    mir_production_1_75_returned: bool,
    mir_production_1_75_caller: bool,
    mir_production_1_76_source: usize,
    mir_production_1_76_argument: usize,
    mir_production_1_76_returned: usize,
    mir_production_1_76_caller: usize,
    mir_production_1_77_source: usize,
    mir_production_1_77_argument: usize,
    mir_production_1_77_returned: usize,
    mir_production_1_77_caller: usize,
    mir_production_1_78_source: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_78_argument: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_78_returned: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_78_caller: &'static std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_79_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_79_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_79_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_79_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_80_source: std::ops::Range<usize>,
    mir_production_1_80_argument: std::ops::Range<usize>,
    mir_production_1_80_returned: std::ops::Range<usize>,
    mir_production_1_80_caller: std::ops::Range<usize>,
    mir_production_1_81_source: std::ops::Range<usize>,
    mir_production_1_81_argument: std::ops::Range<usize>,
    mir_production_1_81_returned: std::ops::Range<usize>,
    mir_production_1_81_caller: std::ops::Range<usize>,
    mir_production_1_83_source: std::option::Option<usize>,
    mir_production_1_83_argument: std::option::Option<usize>,
    mir_production_1_83_returned: std::option::Option<usize>,
    mir_production_1_83_caller: std::option::Option<usize>,
    mir_production_1_84_source: &'static mut std::ops::Range<usize>,
    mir_production_1_84_argument: &'static mut std::ops::Range<usize>,
    mir_production_1_84_returned: &'static mut std::ops::Range<usize>,
    mir_production_1_84_caller: &'static mut std::ops::Range<usize>,
    mir_production_1_85_source: isize,
    mir_production_1_85_argument: isize,
    mir_production_1_85_returned: isize,
    mir_production_1_85_caller: isize,
    mir_production_1_87_source: bool,
    mir_production_1_87_argument: bool,
    mir_production_1_87_returned: bool,
    mir_production_1_87_caller: bool,
    mir_production_1_88_source: &'static Type,
    mir_production_1_88_argument: &'static Type,
    mir_production_1_88_returned: &'static Type,
    mir_production_1_88_caller: &'static Type,
    mir_production_1_89_source: Type,
    mir_production_1_89_argument: Type,
    mir_production_1_89_returned: Type,
    mir_production_1_89_caller: Type,
    mir_production_1_90_source: Value,
    mir_production_1_90_argument: Value,
    mir_production_1_90_returned: Value,
    mir_production_1_90_caller: Value,
    mir_production_1_91_source: &'static Value,
    mir_production_1_91_argument: &'static Value,
    mir_production_1_91_returned: &'static Value,
    mir_production_1_91_caller: &'static Value,
    mir_production_1_92_source: &'static std::vec::Vec<Value>,
    mir_production_1_92_argument: &'static std::vec::Vec<Value>,
    mir_production_1_92_returned: &'static std::vec::Vec<Value>,
    mir_production_1_92_caller: &'static std::vec::Vec<Value>,
    mir_production_1_93_source: usize,
    mir_production_1_93_argument: usize,
    mir_production_1_93_returned: usize,
    mir_production_1_93_caller: usize,
    mir_production_1_94_source: (usize, bool),
    mir_production_1_94_argument: (usize, bool),
    mir_production_1_94_returned: (usize, bool),
    mir_production_1_94_caller: (usize, bool),
    mir_production_1_95_source: &'static Type,
    mir_production_1_95_argument: &'static Type,
    mir_production_1_95_returned: &'static Type,
    mir_production_1_95_caller: &'static Type,
    mir_production_1_96_source: &'static [Type],
    mir_production_1_96_argument: &'static [Type],
    mir_production_1_96_returned: &'static [Type],
    mir_production_1_96_caller: &'static [Type],
    mir_production_1_97_source: usize,
    mir_production_1_97_argument: usize,
    mir_production_1_97_returned: usize,
    mir_production_1_97_caller: usize,
    mir_production_1_98_source: bool,
    mir_production_1_98_argument: bool,
    mir_production_1_98_returned: bool,
    mir_production_1_98_caller: bool,
    mir_production_1_99_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_99_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_99_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_99_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_100_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_100_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_100_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_100_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_1_101_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_101_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_101_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_101_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_102_source: isize,
    mir_production_1_102_argument: isize,
    mir_production_1_102_returned: isize,
    mir_production_1_102_caller: isize,
    mir_production_1_104_source: &'static [Value],
    mir_production_1_104_argument: &'static [Value],
    mir_production_1_104_returned: &'static [Value],
    mir_production_1_104_caller: &'static [Value],
    alias_production_1_104_0_arguments_source: &'static [Value],
    alias_production_1_104_0_arguments_argument: &'static [Value],
    alias_production_1_104_0_arguments_returned: &'static [Value],
    alias_production_1_104_0_arguments_caller: &'static [Value],
    mir_production_1_105_source: &'static std::vec::Vec<Value>,
    mir_production_1_105_argument: &'static std::vec::Vec<Value>,
    mir_production_1_105_returned: &'static std::vec::Vec<Value>,
    mir_production_1_105_caller: &'static std::vec::Vec<Value>,
    mir_production_1_106_source: std::ops::RangeFrom<usize>,
    mir_production_1_106_argument: std::ops::RangeFrom<usize>,
    mir_production_1_106_returned: std::ops::RangeFrom<usize>,
    mir_production_1_106_caller: std::ops::RangeFrom<usize>,
    mir_production_1_107_source: &'static mut [u8],
    mir_production_1_107_argument: &'static mut [u8],
    mir_production_1_107_returned: &'static mut [u8],
    mir_production_1_107_caller: &'static mut [u8],
    alias_production_1_107_0_memory_source: &'static mut [u8],
    alias_production_1_107_0_memory_argument: &'static mut [u8],
    alias_production_1_107_0_memory_returned: &'static mut [u8],
    alias_production_1_107_0_memory_caller: &'static mut [u8],
    mir_production_1_108_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    mir_production_1_108_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    mir_production_1_108_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    mir_production_1_108_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    mir_production_1_109_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_109_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_109_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_109_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_110_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_110_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_110_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_110_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_1_111_source: isize,
    mir_production_1_111_argument: isize,
    mir_production_1_111_returned: isize,
    mir_production_1_111_caller: isize,
    mir_production_1_114_source: bool,
    mir_production_1_114_argument: bool,
    mir_production_1_114_returned: bool,
    mir_production_1_114_caller: bool,
    mir_production_1_115_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_115_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_115_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_115_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_116_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_116_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_116_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_116_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_1_117_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_117_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_117_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_117_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_118_source: (),
    mir_production_1_118_argument: (),
    mir_production_1_118_returned: (),
    mir_production_1_118_caller: (),
    mir_production_1_119_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_119_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_119_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_119_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_120_source: crate::experimental_swift_reactor::control::Live,
    mir_production_1_120_argument: crate::experimental_swift_reactor::control::Live,
    mir_production_1_120_returned: crate::experimental_swift_reactor::control::Live,
    mir_production_1_120_caller: crate::experimental_swift_reactor::control::Live,
    mir_production_1_121_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_1_121_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_1_121_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_1_121_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_1_122_source: crate::experimental_wasi::WasiUsage,
    mir_production_1_122_argument: crate::experimental_wasi::WasiUsage,
    mir_production_1_122_returned: crate::experimental_wasi::WasiUsage,
    mir_production_1_122_caller: crate::experimental_wasi::WasiUsage,
    mir_production_1_123_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_123_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_123_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_123_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_124_source: isize,
    mir_production_1_124_argument: isize,
    mir_production_1_124_returned: isize,
    mir_production_1_124_caller: isize,
    mir_production_1_126_source: u16,
    mir_production_1_126_argument: u16,
    mir_production_1_126_returned: u16,
    mir_production_1_126_caller: u16,
    alias_production_1_126_0_official_errno_source: u16,
    alias_production_1_126_0_official_errno_argument: u16,
    alias_production_1_126_0_official_errno_returned: u16,
    alias_production_1_126_0_official_errno_caller: u16,
    mir_production_1_127_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_1_127_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_1_127_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_1_127_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    mir_production_1_128_source: Value,
    mir_production_1_128_argument: Value,
    mir_production_1_128_returned: Value,
    mir_production_1_128_caller: Value,
    mir_production_1_129_source: i32,
    mir_production_1_129_argument: i32,
    mir_production_1_129_returned: i32,
    mir_production_1_129_caller: i32,
    mir_production_1_130_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_130_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_130_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_130_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_131_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_131_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_131_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_131_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_132_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_132_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_132_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_132_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_133_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_133_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_133_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_133_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_134_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_134_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_134_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_134_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_135_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_135_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_135_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_135_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_136_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_136_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_136_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_136_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_1_137_source: &'static [Type],
    mir_production_1_137_argument: &'static [Type],
    mir_production_1_137_returned: &'static [Type],
    mir_production_1_137_caller: &'static [Type],
    mir_production_1_138_source: &'static mut std::vec::Vec<Value>,
    mir_production_1_138_argument: &'static mut std::vec::Vec<Value>,
    mir_production_1_138_returned: &'static mut std::vec::Vec<Value>,
    mir_production_1_138_caller: &'static mut std::vec::Vec<Value>,
    mir_production_1_139_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_139_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_139_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_139_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_1_140_source: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_140_argument: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_140_returned: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_140_caller: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    mir_production_1_141_source: &'static mut std::vec::Vec<Value>,
    mir_production_1_141_argument: &'static mut std::vec::Vec<Value>,
    mir_production_1_141_returned: &'static mut std::vec::Vec<Value>,
    mir_production_1_141_caller: &'static mut std::vec::Vec<Value>,
    mir_production_1_142_source: &'static mut std::vec::Vec<Value>,
    mir_production_1_142_argument: &'static mut std::vec::Vec<Value>,
    mir_production_1_142_returned: &'static mut std::vec::Vec<Value>,
    mir_production_1_142_caller: &'static mut std::vec::Vec<Value>,
    mir_production_1_143_source: &'static mut std::vec::Vec<u8>,
    mir_production_1_143_argument: &'static mut std::vec::Vec<u8>,
    mir_production_1_143_returned: &'static mut std::vec::Vec<u8>,
    mir_production_1_143_caller: &'static mut std::vec::Vec<u8>,
    mir_production_1_144_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_144_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_144_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_144_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_145_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_145_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_145_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_145_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_146_source: &'static mut std::vec::Vec<Value>,
    mir_production_1_146_argument: &'static mut std::vec::Vec<Value>,
    mir_production_1_146_returned: &'static mut std::vec::Vec<Value>,
    mir_production_1_146_caller: &'static mut std::vec::Vec<Value>,
    mir_production_1_147_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_147_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_147_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_147_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_1_148_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_148_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_148_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_148_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_1_149_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_1_149_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_1_149_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_1_149_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    mir_production_1_57_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_57_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_57_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_57_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_57_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_57_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_57_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_57_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_62_source: usize,
    mir_production_1_62_argument: usize,
    mir_production_1_62_returned: usize,
    mir_production_1_62_caller: usize,
    alias_production_1_62_0_base_source: usize,
    alias_production_1_62_0_base_argument: usize,
    alias_production_1_62_0_base_returned: usize,
    alias_production_1_62_0_base_caller: usize,
    alias_production_1_62_1_base_source: usize,
    alias_production_1_62_1_base_argument: usize,
    alias_production_1_62_1_base_returned: usize,
    alias_production_1_62_1_base_caller: usize,
    mir_production_1_68_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_1_68_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_1_68_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_1_68_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_1_68_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_1_82_source: std::ops::Range<usize>,
    mir_production_1_82_argument: std::ops::Range<usize>,
    mir_production_1_82_returned: std::ops::Range<usize>,
    mir_production_1_82_caller: std::ops::Range<usize>,
    alias_production_1_82_0_iter_source: std::ops::Range<usize>,
    alias_production_1_82_0_iter_argument: std::ops::Range<usize>,
    alias_production_1_82_0_iter_returned: std::ops::Range<usize>,
    alias_production_1_82_0_iter_caller: std::ops::Range<usize>,
    mir_production_1_103_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_103_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_103_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_103_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_103_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_103_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_103_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_103_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_86_source: usize,
    mir_production_1_86_argument: usize,
    mir_production_1_86_returned: usize,
    mir_production_1_86_caller: usize,
    alias_production_1_86_0_index_source: usize,
    alias_production_1_86_0_index_argument: usize,
    alias_production_1_86_0_index_returned: usize,
    alias_production_1_86_0_index_caller: usize,
    mir_production_1_125_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_125_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_125_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_125_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_1_125_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_1_125_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_1_125_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_1_125_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_1_112_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_112_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_112_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_112_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_112_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_112_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_112_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_1_112_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_1_113_source: crate::experimental_wasi::Errno,
    mir_production_1_113_argument: crate::experimental_wasi::Errno,
    mir_production_1_113_returned: crate::experimental_wasi::Errno,
    mir_production_1_113_caller: crate::experimental_wasi::Errno,
    alias_production_1_113_0_errno_source: crate::experimental_wasi::Errno,
    alias_production_1_113_0_errno_argument: crate::experimental_wasi::Errno,
    alias_production_1_113_0_errno_returned: crate::experimental_wasi::Errno,
    alias_production_1_113_0_errno_caller: crate::experimental_wasi::Errno,
    alias_production_1_113_1_val_source: crate::experimental_wasi::Errno,
    alias_production_1_113_1_val_argument: crate::experimental_wasi::Errno,
    alias_production_1_113_1_val_returned: crate::experimental_wasi::Errno,
    alias_production_1_113_1_val_caller: crate::experimental_wasi::Errno,
    mir_production_1_35_source: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_35_argument: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_35_returned: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_35_caller: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_35_0_signature_source: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_35_0_signature_argument: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_35_0_signature_returned: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_35_0_signature_caller: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_40_source: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_40_argument: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_40_returned: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_40_caller: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_40_0_signature_source: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_40_0_signature_argument: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_40_0_signature_returned: crate::experimental::descriptors::SignatureView<'static>,
    alias_production_1_40_0_signature_caller: crate::experimental::descriptors::SignatureView<'static>,
    mir_production_1_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_1_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_1_2_source: u32,
    mir_production_1_2_argument: u32,
    mir_production_1_2_returned: u32,
    mir_production_1_2_caller: u32,
    alias_production_1_2_0_function_source: u32,
    alias_production_1_2_0_function_argument: u32,
    alias_production_1_2_0_function_returned: u32,
    alias_production_1_2_0_function_caller: u32,
    literal_production_1_0_source: &'static str,
    literal_production_1_0_argument: &'static str,
    literal_production_1_0_returned: &'static str,
    literal_production_1_0_caller: &'static str,
    literal_production_1_1_source: &'static str,
    literal_production_1_1_argument: &'static str,
    literal_production_1_1_returned: &'static str,
    literal_production_1_1_caller: &'static str,
    literal_production_1_2_source: &'static str,
    literal_production_1_2_argument: &'static str,
    literal_production_1_2_returned: &'static str,
    literal_production_1_2_caller: &'static str,
    literal_production_1_3_source: &'static str,
    literal_production_1_3_argument: &'static str,
    literal_production_1_3_returned: &'static str,
    literal_production_1_3_caller: &'static str,
    literal_production_1_4_source: &'static str,
    literal_production_1_4_argument: &'static str,
    literal_production_1_4_returned: &'static str,
    literal_production_1_4_caller: &'static str,
    literal_production_1_5_source: &'static str,
    literal_production_1_5_argument: &'static str,
    literal_production_1_5_returned: &'static str,
    literal_production_1_5_caller: &'static str,
    literal_production_1_6_source: usize,
    literal_production_1_6_argument: usize,
    literal_production_1_6_returned: usize,
    literal_production_1_6_caller: usize,
    literal_production_1_7_source: usize,
    literal_production_1_7_argument: usize,
    literal_production_1_7_returned: usize,
    literal_production_1_7_caller: usize,
    literal_production_1_8_source: &'static str,
    literal_production_1_8_argument: &'static str,
    literal_production_1_8_returned: &'static str,
    literal_production_1_8_caller: &'static str,
    literal_production_1_9_source: &'static str,
    literal_production_1_9_argument: &'static str,
    literal_production_1_9_returned: &'static str,
    literal_production_1_9_caller: &'static str,
    literal_production_1_10_source: bool,
    literal_production_1_10_argument: bool,
    literal_production_1_10_returned: bool,
    literal_production_1_10_caller: bool,
    mir_production_2_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_3_source: bool,
    mir_production_2_3_argument: bool,
    mir_production_2_3_returned: bool,
    mir_production_2_3_caller: bool,
    mir_production_2_4_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_4_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_4_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_4_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_2_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_2_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_2_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_2_5_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_2_5_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_2_5_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_2_5_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_2_6_source: (),
    mir_production_2_6_argument: (),
    mir_production_2_6_returned: (),
    mir_production_2_6_caller: (),
    mir_production_2_7_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_7_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_7_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_7_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_2_7_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_2_7_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_2_7_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_2_7_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_8_source: bool,
    mir_production_2_8_argument: bool,
    mir_production_2_8_returned: bool,
    mir_production_2_8_caller: bool,
    mir_production_2_9_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_9_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_9_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_9_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_2_10_source: (),
    mir_production_2_10_argument: (),
    mir_production_2_10_returned: (),
    mir_production_2_10_caller: (),
    mir_production_2_11_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_11_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_11_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_11_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_2_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_2_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_2_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_2_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_2_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_2_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_2_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_2_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_2_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_2_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_2_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    mir_production_2_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_2_2_0_storage_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_2_2_0_storage_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_2_2_0_storage_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    alias_production_2_2_0_storage_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    literal_production_2_0_source: &'static str,
    literal_production_2_0_argument: &'static str,
    literal_production_2_0_returned: &'static str,
    literal_production_2_0_caller: &'static str,
    mir_production_3_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_3_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_3_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_3_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_3_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_4_source: isize,
    mir_production_3_4_argument: isize,
    mir_production_3_4_returned: isize,
    mir_production_3_4_caller: isize,
    mir_production_3_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_6_source: u32,
    mir_production_3_6_argument: u32,
    mir_production_3_6_returned: u32,
    mir_production_3_6_caller: u32,
    alias_production_3_6_0_function_source: u32,
    alias_production_3_6_0_function_argument: u32,
    alias_production_3_6_0_function_returned: u32,
    alias_production_3_6_0_function_caller: u32,
    mir_production_3_7_source: crate::experimental::cache::DecodedInstruction,
    mir_production_3_7_argument: crate::experimental::cache::DecodedInstruction,
    mir_production_3_7_returned: crate::experimental::cache::DecodedInstruction,
    mir_production_3_7_caller: crate::experimental::cache::DecodedInstruction,
    alias_production_3_7_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    alias_production_3_7_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    alias_production_3_7_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    alias_production_3_7_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    mir_production_3_8_source: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_3_8_argument: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_3_8_returned: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_3_8_caller: (u32, crate::experimental::cache::DecodedInstruction),
    mir_production_3_9_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_9_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_9_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_9_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_10_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_10_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_10_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_10_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_11_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_11_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_11_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_11_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_12_source: isize,
    mir_production_3_12_argument: isize,
    mir_production_3_12_returned: isize,
    mir_production_3_12_caller: isize,
    mir_production_3_13_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_13_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_13_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_13_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_13_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_14_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_14_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_14_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_14_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_15_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_3_15_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_3_15_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_3_15_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    mir_production_3_16_source: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_16_argument: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_16_returned: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_16_caller: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_17_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_17_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_17_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_17_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_18_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_3_18_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_3_18_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_3_18_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    mir_production_3_19_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_3_19_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_3_19_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_3_19_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    mir_production_3_20_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_20_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_20_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_20_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_21_source: isize,
    mir_production_3_21_argument: isize,
    mir_production_3_21_returned: isize,
    mir_production_3_21_caller: isize,
    mir_production_3_25_source: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_3_25_argument: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_3_25_returned: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_3_25_caller: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    mir_production_3_26_source: usize,
    mir_production_3_26_argument: usize,
    mir_production_3_26_returned: usize,
    mir_production_3_26_caller: usize,
    mir_production_3_27_source: isize,
    mir_production_3_27_argument: isize,
    mir_production_3_27_returned: isize,
    mir_production_3_27_caller: isize,
    mir_production_3_29_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_29_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_29_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_29_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_30_source: u32,
    mir_production_3_30_argument: u32,
    mir_production_3_30_returned: u32,
    mir_production_3_30_caller: u32,
    mir_production_3_31_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_31_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_31_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_31_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_32_source: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_3_32_argument: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_3_32_returned: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_3_32_caller: crate::experimental_swift_reactor::control::SwiftRunStage,
    mir_production_3_33_source: std::option::Option<u32>,
    mir_production_3_33_argument: std::option::Option<u32>,
    mir_production_3_33_returned: std::option::Option<u32>,
    mir_production_3_33_caller: std::option::Option<u32>,
    mir_production_3_34_source: std::option::Option<usize>,
    mir_production_3_34_argument: std::option::Option<usize>,
    mir_production_3_34_returned: std::option::Option<usize>,
    mir_production_3_34_caller: std::option::Option<usize>,
    mir_production_3_35_source: usize,
    mir_production_3_35_argument: usize,
    mir_production_3_35_returned: usize,
    mir_production_3_35_caller: usize,
    mir_production_3_36_source: isize,
    mir_production_3_36_argument: isize,
    mir_production_3_36_returned: isize,
    mir_production_3_36_caller: isize,
    mir_production_3_38_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_38_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_38_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_38_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_39_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_39_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_39_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_39_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_40_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_40_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_40_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_40_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_41_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_41_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_41_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_41_caller: crate::experimental_swift_reactor::control::Cursor,
    mir_production_3_42_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_3_42_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_3_42_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_3_42_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_3_43_source: crate::experimental_wasi::WasiUsage,
    mir_production_3_43_argument: crate::experimental_wasi::WasiUsage,
    mir_production_3_43_returned: crate::experimental_wasi::WasiUsage,
    mir_production_3_43_caller: crate::experimental_wasi::WasiUsage,
    mir_production_3_44_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_44_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_44_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_44_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_45_source: isize,
    mir_production_3_45_argument: isize,
    mir_production_3_45_returned: isize,
    mir_production_3_45_caller: isize,
    mir_production_3_47_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_47_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_47_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_47_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_3_48_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_48_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_48_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_48_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_49_source: isize,
    mir_production_3_49_argument: isize,
    mir_production_3_49_returned: isize,
    mir_production_3_49_caller: isize,
    mir_production_3_52_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_52_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_52_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_52_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_53_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_53_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_53_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_53_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_54_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_54_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_54_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_54_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_55_source: isize,
    mir_production_3_55_argument: isize,
    mir_production_3_55_returned: isize,
    mir_production_3_55_caller: isize,
    mir_production_3_57_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_57_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_57_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_57_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_58_source: std::option::Option<usize>,
    mir_production_3_58_argument: std::option::Option<usize>,
    mir_production_3_58_returned: std::option::Option<usize>,
    mir_production_3_58_caller: std::option::Option<usize>,
    mir_production_3_59_source: isize,
    mir_production_3_59_argument: isize,
    mir_production_3_59_returned: isize,
    mir_production_3_59_caller: isize,
    mir_production_3_61_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_61_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_61_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_61_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_3_62_source: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_62_argument: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_62_returned: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_62_caller: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_63_source: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_63_argument: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_63_returned: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_63_caller: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_64_source: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_64_argument: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_64_returned: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_64_caller: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    mir_production_3_65_source: &'static str,
    mir_production_3_65_argument: &'static str,
    mir_production_3_65_returned: &'static str,
    mir_production_3_65_caller: &'static str,
    mir_production_3_66_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_66_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_66_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_66_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_67_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_67_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_67_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_67_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    mir_production_3_68_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_68_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_68_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_68_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_69_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_69_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_69_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_69_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_70_source: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_3_70_argument: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_3_70_returned: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_3_70_caller: &'static [crate::experimental::cache::DecodedInstruction],
    mir_production_3_71_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_71_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_71_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_71_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_3_72_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_72_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_72_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_72_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_3_73_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_73_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_73_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_73_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_74_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_74_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_74_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_74_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    mir_production_3_37_source: u32,
    mir_production_3_37_argument: u32,
    mir_production_3_37_returned: u32,
    mir_production_3_37_caller: u32,
    alias_production_3_37_0_target_source: u32,
    alias_production_3_37_0_target_argument: u32,
    alias_production_3_37_0_target_returned: u32,
    alias_production_3_37_0_target_caller: u32,
    alias_production_3_37_1_target_source: u32,
    alias_production_3_37_1_target_argument: u32,
    alias_production_3_37_1_target_returned: u32,
    alias_production_3_37_1_target_caller: u32,
    mir_production_3_46_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_46_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_46_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_46_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_46_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_46_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_46_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_46_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_50_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_50_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_50_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_50_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_50_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_50_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_50_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_50_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_51_source: usize,
    mir_production_3_51_argument: usize,
    mir_production_3_51_returned: usize,
    mir_production_3_51_caller: usize,
    alias_production_3_51_0_current_pc_source: usize,
    alias_production_3_51_0_current_pc_argument: usize,
    alias_production_3_51_0_current_pc_returned: usize,
    alias_production_3_51_0_current_pc_caller: usize,
    mir_production_3_56_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_56_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_56_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_56_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_56_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_56_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_56_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    alias_production_3_56_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    mir_production_3_60_source: usize,
    mir_production_3_60_argument: usize,
    mir_production_3_60_returned: usize,
    mir_production_3_60_caller: usize,
    alias_production_3_60_0_pc_source: usize,
    alias_production_3_60_0_pc_argument: usize,
    alias_production_3_60_0_pc_returned: usize,
    alias_production_3_60_0_pc_caller: usize,
    alias_production_3_60_1_pc_source: usize,
    alias_production_3_60_1_pc_argument: usize,
    alias_production_3_60_1_pc_returned: usize,
    alias_production_3_60_1_pc_caller: usize,
    mir_production_3_22_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_22_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_22_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_22_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_22_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_22_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_22_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_3_22_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_3_23_source: crate::experimental::cache::FunctionView<'static>,
    mir_production_3_23_argument: crate::experimental::cache::FunctionView<'static>,
    mir_production_3_23_returned: crate::experimental::cache::FunctionView<'static>,
    mir_production_3_23_caller: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_0_view_source: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_0_view_argument: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_0_view_returned: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_0_view_caller: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_1_val_source: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_1_val_argument: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_1_val_returned: crate::experimental::cache::FunctionView<'static>,
    alias_production_3_23_1_val_caller: crate::experimental::cache::FunctionView<'static>,
    mir_production_3_24_source: crate::experimental::cache::DecodedInstruction,
    mir_production_3_24_argument: crate::experimental::cache::DecodedInstruction,
    mir_production_3_24_returned: crate::experimental::cache::DecodedInstruction,
    mir_production_3_24_caller: crate::experimental::cache::DecodedInstruction,
    alias_production_3_24_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    alias_production_3_24_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    alias_production_3_24_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    alias_production_3_24_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    mir_production_3_28_source: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_3_28_argument: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_3_28_returned: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_3_28_caller: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_3_28_0_instruction_source: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_3_28_0_instruction_argument: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_3_28_0_instruction_returned: &'static crate::experimental::cache::DecodedInstruction,
    alias_production_3_28_0_instruction_caller: &'static crate::experimental::cache::DecodedInstruction,
    mir_production_3_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    mir_production_3_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_3_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_3_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_3_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    alias_production_3_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    literal_production_3_0_source: &'static str,
    literal_production_3_0_argument: &'static str,
    literal_production_3_0_returned: &'static str,
    literal_production_3_0_caller: &'static str,
    literal_production_3_1_source: &'static str,
    literal_production_3_1_argument: &'static str,
    literal_production_3_1_returned: &'static str,
    literal_production_3_1_caller: &'static str,
    literal_production_3_2_source: &'static str,
    literal_production_3_2_argument: &'static str,
    literal_production_3_2_returned: &'static str,
    literal_production_3_2_caller: &'static str,
    literal_production_3_3_source: usize,
    literal_production_3_3_argument: usize,
    literal_production_3_3_returned: usize,
    literal_production_3_3_caller: usize,
    literal_production_3_4_source: &'static str,
    literal_production_3_4_argument: &'static str,
    literal_production_3_4_returned: &'static str,
    literal_production_3_4_caller: &'static str,
    literal_production_3_5_source: usize,
    literal_production_3_5_argument: usize,
    literal_production_3_5_returned: usize,
    literal_production_3_5_caller: usize,
    literal_production_3_6_source: &'static str,
    literal_production_3_6_argument: &'static str,
    literal_production_3_6_returned: &'static str,
    literal_production_3_6_caller: &'static str,
    literal_production_3_7_source: &'static str,
    literal_production_3_7_argument: &'static str,
    literal_production_3_7_returned: &'static str,
    literal_production_3_7_caller: &'static str,
    mir_production_4_0_source: crate::experimental_wasi::WasiUsage,
    mir_production_4_0_argument: crate::experimental_wasi::WasiUsage,
    mir_production_4_0_returned: crate::experimental_wasi::WasiUsage,
    mir_production_4_0_caller: crate::experimental_wasi::WasiUsage,
    mir_production_4_2_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_4_2_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_4_2_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_4_2_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_4_1_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_4_1_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_4_1_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_4_1_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_4_1_0_self_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_4_1_0_self_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_4_1_0_self_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_4_1_0_self_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_5_0_source: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_0_argument: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_0_returned: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_0_caller: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_4_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_5_5_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_5_5_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_5_5_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_5_5_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_5_6_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_5_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_5_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_5_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_5_7_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_7_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_7_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_7_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_8_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_5_8_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_5_8_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_5_8_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_5_8_0_header_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_5_8_0_header_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_5_8_0_header_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_5_8_0_header_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_5_9_source: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_9_argument: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_9_returned: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_9_caller: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_10_source: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_10_argument: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_10_returned: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_10_caller: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_5_11_source: isize,
    mir_production_5_11_argument: isize,
    mir_production_5_11_returned: isize,
    mir_production_5_11_caller: isize,
    mir_production_5_13_source: bool,
    mir_production_5_13_argument: bool,
    mir_production_5_13_returned: bool,
    mir_production_5_13_caller: bool,
    mir_production_5_14_source: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_14_argument: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_14_returned: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_14_caller: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_15_source: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_5_15_argument: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_5_15_returned: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_5_15_caller: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_5_16_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_5_16_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_5_16_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_5_16_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_5_17_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_17_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_17_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_17_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_18_source: isize,
    mir_production_5_18_argument: isize,
    mir_production_5_18_returned: isize,
    mir_production_5_18_caller: isize,
    mir_production_5_20_source: crate::experimental_wasi::WasiUsage,
    mir_production_5_20_argument: crate::experimental_wasi::WasiUsage,
    mir_production_5_20_returned: crate::experimental_wasi::WasiUsage,
    mir_production_5_20_caller: crate::experimental_wasi::WasiUsage,
    mir_production_5_21_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_5_21_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_5_21_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_5_21_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_5_12_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_12_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_12_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_12_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_5_12_0_observation_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_5_12_0_observation_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_5_12_0_observation_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_5_12_0_observation_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_5_19_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_19_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_19_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_19_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_5_19_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_5_19_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_5_19_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_5_19_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_5_1_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_5_1_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_5_1_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_5_1_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_5_1_0_self_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_5_1_0_self_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_5_1_0_self_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_5_1_0_self_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_5_2_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_2_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_2_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_2_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_5_2_0_control_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_5_2_0_control_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_5_2_0_control_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_5_2_0_control_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_5_3_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_5_3_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_5_3_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_5_3_caller: crate::experimental_swift_reactor::control::Cursor,
    alias_production_5_3_0_cursor_source: crate::experimental_swift_reactor::control::Cursor,
    alias_production_5_3_0_cursor_argument: crate::experimental_swift_reactor::control::Cursor,
    alias_production_5_3_0_cursor_returned: crate::experimental_swift_reactor::control::Cursor,
    alias_production_5_3_0_cursor_caller: crate::experimental_swift_reactor::control::Cursor,
    literal_production_5_0_source: &'static str,
    literal_production_5_0_argument: &'static str,
    literal_production_5_0_returned: &'static str,
    literal_production_5_0_caller: &'static str,
    mir_production_6_0_source: crate::experimental_wasi::WasiUsage,
    mir_production_6_0_argument: crate::experimental_wasi::WasiUsage,
    mir_production_6_0_returned: crate::experimental_wasi::WasiUsage,
    mir_production_6_0_caller: crate::experimental_wasi::WasiUsage,
    mir_production_6_2_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_6_2_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_6_2_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_6_2_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_6_3_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_6_3_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_6_3_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_6_3_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_6_1_source: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_6_1_argument: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_6_1_returned: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_6_1_caller: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    mir_production_7_0_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_0_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_0_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_0_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_7_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_7_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_7_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_7_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_7_7_0_usage_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_7_7_0_usage_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_7_7_0_usage_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    alias_production_7_7_0_usage_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_8_source: crate::experimental_wasi::WasiUsage,
    mir_production_7_8_argument: crate::experimental_wasi::WasiUsage,
    mir_production_7_8_returned: crate::experimental_wasi::WasiUsage,
    mir_production_7_8_caller: crate::experimental_wasi::WasiUsage,
    mir_production_7_9_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_9_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_9_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_9_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_10_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_10_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_10_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_10_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_11_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_11_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_11_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_11_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_12_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_12_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_12_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_12_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_14_source: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_14_argument: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_14_returned: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_14_caller: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_15_source: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_15_argument: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_15_returned: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_15_caller: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    mir_production_7_16_source: isize,
    mir_production_7_16_argument: isize,
    mir_production_7_16_returned: isize,
    mir_production_7_16_caller: isize,
    mir_production_7_17_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_17_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_17_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_17_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_18_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_18_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_18_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_18_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_19_source: isize,
    mir_production_7_19_argument: isize,
    mir_production_7_19_returned: isize,
    mir_production_7_19_caller: isize,
    mir_production_7_21_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_21_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_21_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_21_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_22_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_22_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_22_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_22_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_23_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_23_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_23_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_23_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_24_source: crate::experimental_wasi::WasiUsage,
    mir_production_7_24_argument: crate::experimental_wasi::WasiUsage,
    mir_production_7_24_returned: crate::experimental_wasi::WasiUsage,
    mir_production_7_24_caller: crate::experimental_wasi::WasiUsage,
    mir_production_7_25_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_25_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_25_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_25_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_26_source: isize,
    mir_production_7_26_argument: isize,
    mir_production_7_26_returned: isize,
    mir_production_7_26_caller: isize,
    mir_production_7_28_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_28_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_28_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_28_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    mir_production_7_29_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_29_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_29_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_29_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_30_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_30_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_30_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_30_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_31_source: crate::experimental_wasi::WasiUsage,
    mir_production_7_31_argument: crate::experimental_wasi::WasiUsage,
    mir_production_7_31_returned: crate::experimental_wasi::WasiUsage,
    mir_production_7_31_caller: crate::experimental_wasi::WasiUsage,
    mir_production_7_32_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_32_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_32_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_32_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_33_source: isize,
    mir_production_7_33_argument: isize,
    mir_production_7_33_returned: isize,
    mir_production_7_33_caller: isize,
    mir_production_7_36_source: &'static mut crate::experimental_wasi::WasiContext,
    mir_production_7_36_argument: &'static mut crate::experimental_wasi::WasiContext,
    mir_production_7_36_returned: &'static mut crate::experimental_wasi::WasiContext,
    mir_production_7_36_caller: &'static mut crate::experimental_wasi::WasiContext,
    mir_production_7_38_source: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_38_argument: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_38_returned: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_38_caller: &'static crate::experimental_wasi::WasiContext,
    mir_production_7_40_source: isize,
    mir_production_7_40_argument: isize,
    mir_production_7_40_returned: isize,
    mir_production_7_40_caller: isize,
    mir_production_7_43_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_43_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_43_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_43_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_44_source: std::option::Option<crate::experimental_wasi::WasiFailure>,
    mir_production_7_44_argument: std::option::Option<crate::experimental_wasi::WasiFailure>,
    mir_production_7_44_returned: std::option::Option<crate::experimental_wasi::WasiFailure>,
    mir_production_7_44_caller: std::option::Option<crate::experimental_wasi::WasiFailure>,
    mir_production_7_45_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_45_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_45_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_45_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_46_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_46_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_46_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_46_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_47_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_47_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_47_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_47_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_50_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_50_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_50_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_50_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    mir_production_7_51_source: std::option::Option<u32>,
    mir_production_7_51_argument: std::option::Option<u32>,
    mir_production_7_51_returned: std::option::Option<u32>,
    mir_production_7_51_caller: std::option::Option<u32>,
    mir_production_7_52_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_52_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_52_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_52_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_53_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_53_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_53_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_53_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_54_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_54_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_54_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_54_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_57_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_57_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_57_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_57_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    mir_production_7_58_source: isize,
    mir_production_7_58_argument: isize,
    mir_production_7_58_returned: isize,
    mir_production_7_58_caller: isize,
    mir_production_7_61_source: (&'static crate::experimental_wasi::Errno,),
    mir_production_7_61_argument: (&'static crate::experimental_wasi::Errno,),
    mir_production_7_61_returned: (&'static crate::experimental_wasi::Errno,),
    mir_production_7_61_caller: (&'static crate::experimental_wasi::Errno,),
    mir_production_7_62_source: &'static crate::experimental_wasi::Errno,
    mir_production_7_62_argument: &'static crate::experimental_wasi::Errno,
    mir_production_7_62_returned: &'static crate::experimental_wasi::Errno,
    mir_production_7_62_caller: &'static crate::experimental_wasi::Errno,
    mir_production_7_13_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_7_13_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_7_13_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_7_13_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_7_13_0_ticket_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_7_13_0_ticket_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_7_13_0_ticket_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    alias_production_7_13_0_ticket_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    mir_production_7_20_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_20_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_20_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_20_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_20_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_20_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_20_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_20_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_27_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_27_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_27_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_27_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_27_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_27_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_27_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_27_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_34_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_34_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_34_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_34_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_34_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_34_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_34_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_34_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_35_source: crate::experimental_wasi::WasiOutcome,
    mir_production_7_35_argument: crate::experimental_wasi::WasiOutcome,
    mir_production_7_35_returned: crate::experimental_wasi::WasiOutcome,
    mir_production_7_35_caller: crate::experimental_wasi::WasiOutcome,
    alias_production_7_35_0_outcome_source: crate::experimental_wasi::WasiOutcome,
    alias_production_7_35_0_outcome_argument: crate::experimental_wasi::WasiOutcome,
    alias_production_7_35_0_outcome_returned: crate::experimental_wasi::WasiOutcome,
    alias_production_7_35_0_outcome_caller: crate::experimental_wasi::WasiOutcome,
    mir_production_7_37_source: crate::experimental_wasi::WasiUsage,
    mir_production_7_37_argument: crate::experimental_wasi::WasiUsage,
    mir_production_7_37_returned: crate::experimental_wasi::WasiUsage,
    mir_production_7_37_caller: crate::experimental_wasi::WasiUsage,
    alias_production_7_37_0_usage_source: crate::experimental_wasi::WasiUsage,
    alias_production_7_37_0_usage_argument: crate::experimental_wasi::WasiUsage,
    alias_production_7_37_0_usage_returned: crate::experimental_wasi::WasiUsage,
    alias_production_7_37_0_usage_caller: crate::experimental_wasi::WasiUsage,
    mir_production_7_39_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_39_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_39_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_39_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_39_0_result_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_39_0_result_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_39_0_result_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_39_0_result_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_41_source: crate::experimental_wasi::WasiFailure,
    mir_production_7_41_argument: crate::experimental_wasi::WasiFailure,
    mir_production_7_41_returned: crate::experimental_wasi::WasiFailure,
    mir_production_7_41_caller: crate::experimental_wasi::WasiFailure,
    alias_production_7_41_0_error_source: crate::experimental_wasi::WasiFailure,
    alias_production_7_41_0_error_argument: crate::experimental_wasi::WasiFailure,
    alias_production_7_41_0_error_returned: crate::experimental_wasi::WasiFailure,
    alias_production_7_41_0_error_caller: crate::experimental_wasi::WasiFailure,
    mir_production_7_48_source: u32,
    mir_production_7_48_argument: u32,
    mir_production_7_48_returned: u32,
    mir_production_7_48_caller: u32,
    alias_production_7_48_0_code_source: u32,
    alias_production_7_48_0_code_argument: u32,
    alias_production_7_48_0_code_returned: u32,
    alias_production_7_48_0_code_caller: u32,
    mir_production_7_55_source: crate::experimental_wasi::Errno,
    mir_production_7_55_argument: crate::experimental_wasi::Errno,
    mir_production_7_55_returned: crate::experimental_wasi::Errno,
    mir_production_7_55_caller: crate::experimental_wasi::Errno,
    alias_production_7_55_0_errno_source: crate::experimental_wasi::Errno,
    alias_production_7_55_0_errno_argument: crate::experimental_wasi::Errno,
    alias_production_7_55_0_errno_returned: crate::experimental_wasi::Errno,
    alias_production_7_55_0_errno_caller: crate::experimental_wasi::Errno,
    mir_production_7_56_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_56_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_56_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_56_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_56_0_after_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_56_0_after_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_56_0_after_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    alias_production_7_56_0_after_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    mir_production_7_59_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_59_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_59_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_59_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_7_59_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_7_59_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_7_59_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    alias_production_7_59_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    mir_production_7_60_source: crate::experimental_wasi::Errno,
    mir_production_7_60_argument: crate::experimental_wasi::Errno,
    mir_production_7_60_returned: crate::experimental_wasi::Errno,
    mir_production_7_60_caller: crate::experimental_wasi::Errno,
    alias_production_7_60_0_errno_source: crate::experimental_wasi::Errno,
    alias_production_7_60_0_errno_argument: crate::experimental_wasi::Errno,
    alias_production_7_60_0_errno_returned: crate::experimental_wasi::Errno,
    alias_production_7_60_0_errno_caller: crate::experimental_wasi::Errno,
    mir_production_7_42_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_42_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_42_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_42_caller: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_42_0_fault_source: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_42_0_fault_argument: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_42_0_fault_returned: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_42_0_fault_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_49_source: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_49_argument: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_49_returned: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_49_caller: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_49_0_fault_source: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_49_0_fault_argument: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_49_0_fault_returned: crate::experimental_swift_reactor::control::Fault,
    alias_production_7_49_0_fault_caller: crate::experimental_swift_reactor::control::Fault,
    mir_production_7_1_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_7_1_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_7_1_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_7_1_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_7_1_0_self_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_7_1_0_self_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_7_1_0_self_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    alias_production_7_1_0_self_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    mir_production_7_2_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_7_2_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_7_2_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_7_2_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_7_2_0_control_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_7_2_0_control_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_7_2_0_control_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    alias_production_7_2_0_control_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    mir_production_7_3_source: WasiFunction,
    mir_production_7_3_argument: WasiFunction,
    mir_production_7_3_returned: WasiFunction,
    mir_production_7_3_caller: WasiFunction,
    alias_production_7_3_0_function_source: WasiFunction,
    alias_production_7_3_0_function_argument: WasiFunction,
    alias_production_7_3_0_function_returned: WasiFunction,
    alias_production_7_3_0_function_caller: WasiFunction,
    mir_production_7_4_source: &'static [Value],
    mir_production_7_4_argument: &'static [Value],
    mir_production_7_4_returned: &'static [Value],
    mir_production_7_4_caller: &'static [Value],
    alias_production_7_4_0_arguments_source: &'static [Value],
    alias_production_7_4_0_arguments_argument: &'static [Value],
    alias_production_7_4_0_arguments_returned: &'static [Value],
    alias_production_7_4_0_arguments_caller: &'static [Value],
    mir_production_7_5_source: &'static mut [u8],
    mir_production_7_5_argument: &'static mut [u8],
    mir_production_7_5_returned: &'static mut [u8],
    mir_production_7_5_caller: &'static mut [u8],
    alias_production_7_5_0_memory_source: &'static mut [u8],
    alias_production_7_5_0_memory_argument: &'static mut [u8],
    alias_production_7_5_0_memory_returned: &'static mut [u8],
    alias_production_7_5_0_memory_caller: &'static mut [u8],
    mir_production_7_6_source: crate::experimental_swift_reactor::control::Cursor,
    mir_production_7_6_argument: crate::experimental_swift_reactor::control::Cursor,
    mir_production_7_6_returned: crate::experimental_swift_reactor::control::Cursor,
    mir_production_7_6_caller: crate::experimental_swift_reactor::control::Cursor,
    alias_production_7_6_0_cursor_source: crate::experimental_swift_reactor::control::Cursor,
    alias_production_7_6_0_cursor_argument: crate::experimental_swift_reactor::control::Cursor,
    alias_production_7_6_0_cursor_returned: crate::experimental_swift_reactor::control::Cursor,
    alias_production_7_6_0_cursor_caller: crate::experimental_swift_reactor::control::Cursor,
    literal_production_7_0_source: &'static str,
    literal_production_7_0_argument: &'static str,
    literal_production_7_0_returned: &'static str,
    literal_production_7_0_caller: &'static str,
    literal_production_7_1_source: &'static str,
    literal_production_7_1_argument: &'static str,
    literal_production_7_1_returned: &'static str,
    literal_production_7_1_caller: &'static str,
    literal_production_7_2_source: &'static str,
    literal_production_7_2_argument: &'static str,
    literal_production_7_2_returned: &'static str,
    literal_production_7_2_caller: &'static str,
    mir_production_8_0_source: crate::experimental_wasi::Errno,
    mir_production_8_0_argument: crate::experimental_wasi::Errno,
    mir_production_8_0_returned: crate::experimental_wasi::Errno,
    mir_production_8_0_caller: crate::experimental_wasi::Errno,
    mir_production_8_3_source: &'static crate::experimental_wasi::Errno,
    mir_production_8_3_argument: &'static crate::experimental_wasi::Errno,
    mir_production_8_3_returned: &'static crate::experimental_wasi::Errno,
    mir_production_8_3_caller: &'static crate::experimental_wasi::Errno,
    mir_production_8_1_source: (&'static crate::experimental_wasi::Errno,),
    mir_production_8_1_argument: (&'static crate::experimental_wasi::Errno,),
    mir_production_8_1_returned: (&'static crate::experimental_wasi::Errno,),
    mir_production_8_1_caller: (&'static crate::experimental_wasi::Errno,),
    mir_production_8_2_source: (),
    mir_production_8_2_argument: (),
    mir_production_8_2_returned: (),
    mir_production_8_2_caller: (),
    mir_production_9_0_source: &'static [Type],
    mir_production_9_0_argument: &'static [Type],
    mir_production_9_0_returned: &'static [Type],
    mir_production_9_0_caller: &'static [Type],
    mir_production_9_2_source: &'static [Type],
    mir_production_9_2_argument: &'static [Type],
    mir_production_9_2_returned: &'static [Type],
    mir_production_9_2_caller: &'static [Type],
    mir_production_9_3_source: isize,
    mir_production_9_3_argument: isize,
    mir_production_9_3_returned: isize,
    mir_production_9_3_caller: isize,
    mir_production_9_4_source: &'static [Type; 1],
    mir_production_9_4_argument: &'static [Type; 1],
    mir_production_9_4_returned: &'static [Type; 1],
    mir_production_9_4_caller: &'static [Type; 1],
    mir_production_9_5_source: &'static [Type; 3],
    mir_production_9_5_argument: &'static [Type; 3],
    mir_production_9_5_returned: &'static [Type; 3],
    mir_production_9_5_caller: &'static [Type; 3],
    mir_production_9_6_source: &'static [Type; 2],
    mir_production_9_6_argument: &'static [Type; 2],
    mir_production_9_6_returned: &'static [Type; 2],
    mir_production_9_6_caller: &'static [Type; 2],
    mir_production_9_7_source: &'static [Type; 4],
    mir_production_9_7_argument: &'static [Type; 4],
    mir_production_9_7_returned: &'static [Type; 4],
    mir_production_9_7_caller: &'static [Type; 4],
    mir_production_9_8_source: &'static [Type; 5],
    mir_production_9_8_argument: &'static [Type; 5],
    mir_production_9_8_returned: &'static [Type; 5],
    mir_production_9_8_caller: &'static [Type; 5],
    mir_production_9_9_source: &'static [Type; 4],
    mir_production_9_9_argument: &'static [Type; 4],
    mir_production_9_9_returned: &'static [Type; 4],
    mir_production_9_9_caller: &'static [Type; 4],
    mir_production_9_10_source: &'static [Type; 3],
    mir_production_9_10_argument: &'static [Type; 3],
    mir_production_9_10_returned: &'static [Type; 3],
    mir_production_9_10_caller: &'static [Type; 3],
    mir_production_9_11_source: &'static [Type; 4],
    mir_production_9_11_argument: &'static [Type; 4],
    mir_production_9_11_returned: &'static [Type; 4],
    mir_production_9_11_caller: &'static [Type; 4],
    mir_production_9_12_source: &'static [Type; 5],
    mir_production_9_12_argument: &'static [Type; 5],
    mir_production_9_12_returned: &'static [Type; 5],
    mir_production_9_12_caller: &'static [Type; 5],
    mir_production_9_13_source: &'static [Type; 7],
    mir_production_9_13_argument: &'static [Type; 7],
    mir_production_9_13_returned: &'static [Type; 7],
    mir_production_9_13_caller: &'static [Type; 7],
    mir_production_9_14_source: &'static [Type; 7],
    mir_production_9_14_argument: &'static [Type; 7],
    mir_production_9_14_returned: &'static [Type; 7],
    mir_production_9_14_caller: &'static [Type; 7],
    mir_production_9_15_source: &'static [Type; 9],
    mir_production_9_15_argument: &'static [Type; 9],
    mir_production_9_15_returned: &'static [Type; 9],
    mir_production_9_15_caller: &'static [Type; 9],
    mir_production_9_16_source: &'static [Type; 6],
    mir_production_9_16_argument: &'static [Type; 6],
    mir_production_9_16_returned: &'static [Type; 6],
    mir_production_9_16_caller: &'static [Type; 6],
    mir_production_9_17_source: &'static [Type; 2],
    mir_production_9_17_argument: &'static [Type; 2],
    mir_production_9_17_returned: &'static [Type; 2],
    mir_production_9_17_caller: &'static [Type; 2],
    mir_production_9_1_source: WasiFunction,
    mir_production_9_1_argument: WasiFunction,
    mir_production_9_1_returned: WasiFunction,
    mir_production_9_1_caller: WasiFunction,
    alias_production_9_1_0_self_source: WasiFunction,
    alias_production_9_1_0_self_argument: WasiFunction,
    alias_production_9_1_0_self_returned: WasiFunction,
    alias_production_9_1_0_self_caller: WasiFunction,
    mir_production_10_0_source: &'static [Type],
    mir_production_10_0_argument: &'static [Type],
    mir_production_10_0_returned: &'static [Type],
    mir_production_10_0_caller: &'static [Type],
    mir_production_10_2_source: bool,
    mir_production_10_2_argument: bool,
    mir_production_10_2_returned: bool,
    mir_production_10_2_caller: bool,
    mir_production_10_3_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_3_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_3_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_3_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_4_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_4_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_4_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_4_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_10_5_source: &'static [Type; 0],
    mir_production_10_5_argument: &'static [Type; 0],
    mir_production_10_5_returned: &'static [Type; 0],
    mir_production_10_5_caller: &'static [Type; 0],
    mir_production_10_6_source: &'static [Type; 1],
    mir_production_10_6_argument: &'static [Type; 1],
    mir_production_10_6_returned: &'static [Type; 1],
    mir_production_10_6_caller: &'static [Type; 1],
    mir_production_10_1_source: WasiFunction,
    mir_production_10_1_argument: WasiFunction,
    mir_production_10_1_returned: WasiFunction,
    mir_production_10_1_caller: WasiFunction,
    alias_production_10_1_0_self_source: WasiFunction,
    alias_production_10_1_0_self_argument: WasiFunction,
    alias_production_10_1_0_self_returned: WasiFunction,
    alias_production_10_1_0_self_caller: WasiFunction,
    mir_production_11_0_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_11_0_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_11_0_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_11_0_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_11_1_source: crate::experimental_wasi::WasiFunction,
    mir_production_11_1_argument: crate::experimental_wasi::WasiFunction,
    mir_production_11_1_returned: crate::experimental_wasi::WasiFunction,
    mir_production_11_1_caller: crate::experimental_wasi::WasiFunction,
    mir_production_12_0_source: &'static [Type; 2],
    mir_production_12_0_argument: &'static [Type; 2],
    mir_production_12_0_returned: &'static [Type; 2],
    mir_production_12_0_caller: &'static [Type; 2],
    mir_production_12_1_source: [Type; 2],
    mir_production_12_1_argument: [Type; 2],
    mir_production_12_1_returned: [Type; 2],
    mir_production_12_1_caller: [Type; 2],
    mir_production_12_2_source: Type,
    mir_production_12_2_argument: Type,
    mir_production_12_2_returned: Type,
    mir_production_12_2_caller: Type,
    mir_production_12_3_source: Type,
    mir_production_12_3_argument: Type,
    mir_production_12_3_returned: Type,
    mir_production_12_3_caller: Type,
    mir_production_13_0_source: &'static [Type; 6],
    mir_production_13_0_argument: &'static [Type; 6],
    mir_production_13_0_returned: &'static [Type; 6],
    mir_production_13_0_caller: &'static [Type; 6],
    mir_production_13_1_source: [Type; 6],
    mir_production_13_1_argument: [Type; 6],
    mir_production_13_1_returned: [Type; 6],
    mir_production_13_1_caller: [Type; 6],
    mir_production_13_2_source: Type,
    mir_production_13_2_argument: Type,
    mir_production_13_2_returned: Type,
    mir_production_13_2_caller: Type,
    mir_production_13_3_source: Type,
    mir_production_13_3_argument: Type,
    mir_production_13_3_returned: Type,
    mir_production_13_3_caller: Type,
    mir_production_13_4_source: Type,
    mir_production_13_4_argument: Type,
    mir_production_13_4_returned: Type,
    mir_production_13_4_caller: Type,
    mir_production_13_5_source: Type,
    mir_production_13_5_argument: Type,
    mir_production_13_5_returned: Type,
    mir_production_13_5_caller: Type,
    mir_production_13_6_source: Type,
    mir_production_13_6_argument: Type,
    mir_production_13_6_returned: Type,
    mir_production_13_6_caller: Type,
    mir_production_13_7_source: Type,
    mir_production_13_7_argument: Type,
    mir_production_13_7_returned: Type,
    mir_production_13_7_caller: Type,
    mir_production_14_0_source: &'static [Type; 9],
    mir_production_14_0_argument: &'static [Type; 9],
    mir_production_14_0_returned: &'static [Type; 9],
    mir_production_14_0_caller: &'static [Type; 9],
    mir_production_14_1_source: [Type; 9],
    mir_production_14_1_argument: [Type; 9],
    mir_production_14_1_returned: [Type; 9],
    mir_production_14_1_caller: [Type; 9],
    mir_production_14_2_source: Type,
    mir_production_14_2_argument: Type,
    mir_production_14_2_returned: Type,
    mir_production_14_2_caller: Type,
    mir_production_14_3_source: Type,
    mir_production_14_3_argument: Type,
    mir_production_14_3_returned: Type,
    mir_production_14_3_caller: Type,
    mir_production_14_4_source: Type,
    mir_production_14_4_argument: Type,
    mir_production_14_4_returned: Type,
    mir_production_14_4_caller: Type,
    mir_production_14_5_source: Type,
    mir_production_14_5_argument: Type,
    mir_production_14_5_returned: Type,
    mir_production_14_5_caller: Type,
    mir_production_14_6_source: Type,
    mir_production_14_6_argument: Type,
    mir_production_14_6_returned: Type,
    mir_production_14_6_caller: Type,
    mir_production_14_7_source: Type,
    mir_production_14_7_argument: Type,
    mir_production_14_7_returned: Type,
    mir_production_14_7_caller: Type,
    mir_production_14_8_source: Type,
    mir_production_14_8_argument: Type,
    mir_production_14_8_returned: Type,
    mir_production_14_8_caller: Type,
    mir_production_14_9_source: Type,
    mir_production_14_9_argument: Type,
    mir_production_14_9_returned: Type,
    mir_production_14_9_caller: Type,
    mir_production_14_10_source: Type,
    mir_production_14_10_argument: Type,
    mir_production_14_10_returned: Type,
    mir_production_14_10_caller: Type,
    mir_production_15_0_source: &'static [Type; 7],
    mir_production_15_0_argument: &'static [Type; 7],
    mir_production_15_0_returned: &'static [Type; 7],
    mir_production_15_0_caller: &'static [Type; 7],
    mir_production_15_1_source: [Type; 7],
    mir_production_15_1_argument: [Type; 7],
    mir_production_15_1_returned: [Type; 7],
    mir_production_15_1_caller: [Type; 7],
    mir_production_15_2_source: Type,
    mir_production_15_2_argument: Type,
    mir_production_15_2_returned: Type,
    mir_production_15_2_caller: Type,
    mir_production_15_3_source: Type,
    mir_production_15_3_argument: Type,
    mir_production_15_3_returned: Type,
    mir_production_15_3_caller: Type,
    mir_production_15_4_source: Type,
    mir_production_15_4_argument: Type,
    mir_production_15_4_returned: Type,
    mir_production_15_4_caller: Type,
    mir_production_15_5_source: Type,
    mir_production_15_5_argument: Type,
    mir_production_15_5_returned: Type,
    mir_production_15_5_caller: Type,
    mir_production_15_6_source: Type,
    mir_production_15_6_argument: Type,
    mir_production_15_6_returned: Type,
    mir_production_15_6_caller: Type,
    mir_production_15_7_source: Type,
    mir_production_15_7_argument: Type,
    mir_production_15_7_returned: Type,
    mir_production_15_7_caller: Type,
    mir_production_15_8_source: Type,
    mir_production_15_8_argument: Type,
    mir_production_15_8_returned: Type,
    mir_production_15_8_caller: Type,
    mir_production_16_0_source: &'static [Type; 7],
    mir_production_16_0_argument: &'static [Type; 7],
    mir_production_16_0_returned: &'static [Type; 7],
    mir_production_16_0_caller: &'static [Type; 7],
    mir_production_16_1_source: [Type; 7],
    mir_production_16_1_argument: [Type; 7],
    mir_production_16_1_returned: [Type; 7],
    mir_production_16_1_caller: [Type; 7],
    mir_production_16_2_source: Type,
    mir_production_16_2_argument: Type,
    mir_production_16_2_returned: Type,
    mir_production_16_2_caller: Type,
    mir_production_16_3_source: Type,
    mir_production_16_3_argument: Type,
    mir_production_16_3_returned: Type,
    mir_production_16_3_caller: Type,
    mir_production_16_4_source: Type,
    mir_production_16_4_argument: Type,
    mir_production_16_4_returned: Type,
    mir_production_16_4_caller: Type,
    mir_production_16_5_source: Type,
    mir_production_16_5_argument: Type,
    mir_production_16_5_returned: Type,
    mir_production_16_5_caller: Type,
    mir_production_16_6_source: Type,
    mir_production_16_6_argument: Type,
    mir_production_16_6_returned: Type,
    mir_production_16_6_caller: Type,
    mir_production_16_7_source: Type,
    mir_production_16_7_argument: Type,
    mir_production_16_7_returned: Type,
    mir_production_16_7_caller: Type,
    mir_production_16_8_source: Type,
    mir_production_16_8_argument: Type,
    mir_production_16_8_returned: Type,
    mir_production_16_8_caller: Type,
    mir_production_17_0_source: &'static [Type; 5],
    mir_production_17_0_argument: &'static [Type; 5],
    mir_production_17_0_returned: &'static [Type; 5],
    mir_production_17_0_caller: &'static [Type; 5],
    mir_production_17_1_source: [Type; 5],
    mir_production_17_1_argument: [Type; 5],
    mir_production_17_1_returned: [Type; 5],
    mir_production_17_1_caller: [Type; 5],
    mir_production_17_2_source: Type,
    mir_production_17_2_argument: Type,
    mir_production_17_2_returned: Type,
    mir_production_17_2_caller: Type,
    mir_production_17_3_source: Type,
    mir_production_17_3_argument: Type,
    mir_production_17_3_returned: Type,
    mir_production_17_3_caller: Type,
    mir_production_17_4_source: Type,
    mir_production_17_4_argument: Type,
    mir_production_17_4_returned: Type,
    mir_production_17_4_caller: Type,
    mir_production_17_5_source: Type,
    mir_production_17_5_argument: Type,
    mir_production_17_5_returned: Type,
    mir_production_17_5_caller: Type,
    mir_production_17_6_source: Type,
    mir_production_17_6_argument: Type,
    mir_production_17_6_returned: Type,
    mir_production_17_6_caller: Type,
    mir_production_18_0_source: &'static [Type; 4],
    mir_production_18_0_argument: &'static [Type; 4],
    mir_production_18_0_returned: &'static [Type; 4],
    mir_production_18_0_caller: &'static [Type; 4],
    mir_production_18_1_source: [Type; 4],
    mir_production_18_1_argument: [Type; 4],
    mir_production_18_1_returned: [Type; 4],
    mir_production_18_1_caller: [Type; 4],
    mir_production_18_2_source: Type,
    mir_production_18_2_argument: Type,
    mir_production_18_2_returned: Type,
    mir_production_18_2_caller: Type,
    mir_production_18_3_source: Type,
    mir_production_18_3_argument: Type,
    mir_production_18_3_returned: Type,
    mir_production_18_3_caller: Type,
    mir_production_18_4_source: Type,
    mir_production_18_4_argument: Type,
    mir_production_18_4_returned: Type,
    mir_production_18_4_caller: Type,
    mir_production_18_5_source: Type,
    mir_production_18_5_argument: Type,
    mir_production_18_5_returned: Type,
    mir_production_18_5_caller: Type,
    mir_production_19_0_source: &'static [Type; 3],
    mir_production_19_0_argument: &'static [Type; 3],
    mir_production_19_0_returned: &'static [Type; 3],
    mir_production_19_0_caller: &'static [Type; 3],
    mir_production_19_1_source: [Type; 3],
    mir_production_19_1_argument: [Type; 3],
    mir_production_19_1_returned: [Type; 3],
    mir_production_19_1_caller: [Type; 3],
    mir_production_19_2_source: Type,
    mir_production_19_2_argument: Type,
    mir_production_19_2_returned: Type,
    mir_production_19_2_caller: Type,
    mir_production_19_3_source: Type,
    mir_production_19_3_argument: Type,
    mir_production_19_3_returned: Type,
    mir_production_19_3_caller: Type,
    mir_production_19_4_source: Type,
    mir_production_19_4_argument: Type,
    mir_production_19_4_returned: Type,
    mir_production_19_4_caller: Type,
    mir_production_20_0_source: &'static [Type; 4],
    mir_production_20_0_argument: &'static [Type; 4],
    mir_production_20_0_returned: &'static [Type; 4],
    mir_production_20_0_caller: &'static [Type; 4],
    mir_production_20_1_source: [Type; 4],
    mir_production_20_1_argument: [Type; 4],
    mir_production_20_1_returned: [Type; 4],
    mir_production_20_1_caller: [Type; 4],
    mir_production_20_2_source: Type,
    mir_production_20_2_argument: Type,
    mir_production_20_2_returned: Type,
    mir_production_20_2_caller: Type,
    mir_production_20_3_source: Type,
    mir_production_20_3_argument: Type,
    mir_production_20_3_returned: Type,
    mir_production_20_3_caller: Type,
    mir_production_20_4_source: Type,
    mir_production_20_4_argument: Type,
    mir_production_20_4_returned: Type,
    mir_production_20_4_caller: Type,
    mir_production_20_5_source: Type,
    mir_production_20_5_argument: Type,
    mir_production_20_5_returned: Type,
    mir_production_20_5_caller: Type,
    mir_production_21_0_source: &'static [Type; 5],
    mir_production_21_0_argument: &'static [Type; 5],
    mir_production_21_0_returned: &'static [Type; 5],
    mir_production_21_0_caller: &'static [Type; 5],
    mir_production_21_1_source: [Type; 5],
    mir_production_21_1_argument: [Type; 5],
    mir_production_21_1_returned: [Type; 5],
    mir_production_21_1_caller: [Type; 5],
    mir_production_21_2_source: Type,
    mir_production_21_2_argument: Type,
    mir_production_21_2_returned: Type,
    mir_production_21_2_caller: Type,
    mir_production_21_3_source: Type,
    mir_production_21_3_argument: Type,
    mir_production_21_3_returned: Type,
    mir_production_21_3_caller: Type,
    mir_production_21_4_source: Type,
    mir_production_21_4_argument: Type,
    mir_production_21_4_returned: Type,
    mir_production_21_4_caller: Type,
    mir_production_21_5_source: Type,
    mir_production_21_5_argument: Type,
    mir_production_21_5_returned: Type,
    mir_production_21_5_caller: Type,
    mir_production_21_6_source: Type,
    mir_production_21_6_argument: Type,
    mir_production_21_6_returned: Type,
    mir_production_21_6_caller: Type,
    mir_production_22_0_source: &'static [Type; 4],
    mir_production_22_0_argument: &'static [Type; 4],
    mir_production_22_0_returned: &'static [Type; 4],
    mir_production_22_0_caller: &'static [Type; 4],
    mir_production_22_1_source: [Type; 4],
    mir_production_22_1_argument: [Type; 4],
    mir_production_22_1_returned: [Type; 4],
    mir_production_22_1_caller: [Type; 4],
    mir_production_22_2_source: Type,
    mir_production_22_2_argument: Type,
    mir_production_22_2_returned: Type,
    mir_production_22_2_caller: Type,
    mir_production_22_3_source: Type,
    mir_production_22_3_argument: Type,
    mir_production_22_3_returned: Type,
    mir_production_22_3_caller: Type,
    mir_production_22_4_source: Type,
    mir_production_22_4_argument: Type,
    mir_production_22_4_returned: Type,
    mir_production_22_4_caller: Type,
    mir_production_22_5_source: Type,
    mir_production_22_5_argument: Type,
    mir_production_22_5_returned: Type,
    mir_production_22_5_caller: Type,
    mir_production_23_0_source: &'static [Type; 2],
    mir_production_23_0_argument: &'static [Type; 2],
    mir_production_23_0_returned: &'static [Type; 2],
    mir_production_23_0_caller: &'static [Type; 2],
    mir_production_23_1_source: [Type; 2],
    mir_production_23_1_argument: [Type; 2],
    mir_production_23_1_returned: [Type; 2],
    mir_production_23_1_caller: [Type; 2],
    mir_production_23_2_source: Type,
    mir_production_23_2_argument: Type,
    mir_production_23_2_returned: Type,
    mir_production_23_2_caller: Type,
    mir_production_23_3_source: Type,
    mir_production_23_3_argument: Type,
    mir_production_23_3_returned: Type,
    mir_production_23_3_caller: Type,
    mir_production_24_0_source: &'static [Type; 3],
    mir_production_24_0_argument: &'static [Type; 3],
    mir_production_24_0_returned: &'static [Type; 3],
    mir_production_24_0_caller: &'static [Type; 3],
    mir_production_24_1_source: [Type; 3],
    mir_production_24_1_argument: [Type; 3],
    mir_production_24_1_returned: [Type; 3],
    mir_production_24_1_caller: [Type; 3],
    mir_production_24_2_source: Type,
    mir_production_24_2_argument: Type,
    mir_production_24_2_returned: Type,
    mir_production_24_2_caller: Type,
    mir_production_24_3_source: Type,
    mir_production_24_3_argument: Type,
    mir_production_24_3_returned: Type,
    mir_production_24_3_caller: Type,
    mir_production_24_4_source: Type,
    mir_production_24_4_argument: Type,
    mir_production_24_4_returned: Type,
    mir_production_24_4_caller: Type,
    mir_production_25_0_source: &'static [Type; 1],
    mir_production_25_0_argument: &'static [Type; 1],
    mir_production_25_0_returned: &'static [Type; 1],
    mir_production_25_0_caller: &'static [Type; 1],
    mir_production_25_1_source: [Type; 1],
    mir_production_25_1_argument: [Type; 1],
    mir_production_25_1_returned: [Type; 1],
    mir_production_25_1_caller: [Type; 1],
    mir_production_25_2_source: Type,
    mir_production_25_2_argument: Type,
    mir_production_25_2_returned: Type,
    mir_production_25_2_caller: Type,
    mir_production_26_0_source: &'static [Type; 0],
    mir_production_26_0_argument: &'static [Type; 0],
    mir_production_26_0_returned: &'static [Type; 0],
    mir_production_26_0_caller: &'static [Type; 0],
    mir_production_26_1_source: [Type; 0],
    mir_production_26_1_argument: [Type; 0],
    mir_production_26_1_returned: [Type; 0],
    mir_production_26_1_caller: [Type; 0],
    mir_production_27_0_source: &'static [Type; 1],
    mir_production_27_0_argument: &'static [Type; 1],
    mir_production_27_0_returned: &'static [Type; 1],
    mir_production_27_0_caller: &'static [Type; 1],
    mir_production_27_1_source: [Type; 1],
    mir_production_27_1_argument: [Type; 1],
    mir_production_27_1_returned: [Type; 1],
    mir_production_27_1_caller: [Type; 1],
    mir_production_27_2_source: Type,
    mir_production_27_2_argument: Type,
    mir_production_27_2_returned: Type,
    mir_production_27_2_caller: Type,
    mir_production_28_0_source: &'static crate::experimental_wasi::WasiFunction,
    mir_production_28_0_argument: &'static crate::experimental_wasi::WasiFunction,
    mir_production_28_0_returned: &'static crate::experimental_wasi::WasiFunction,
    mir_production_28_0_caller: &'static crate::experimental_wasi::WasiFunction,
    mir_production_28_1_source: crate::experimental_wasi::WasiFunction,
    mir_production_28_1_argument: crate::experimental_wasi::WasiFunction,
    mir_production_28_1_returned: crate::experimental_wasi::WasiFunction,
    mir_production_28_1_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_0_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_4_source: bool,
    #[cfg(test)]
    mir_unit_0_4_argument: bool,
    #[cfg(test)]
    mir_unit_0_4_returned: bool,
    #[cfg(test)]
    mir_unit_0_4_caller: bool,
    #[cfg(test)]
    mir_unit_0_5_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_5_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_5_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_5_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_6_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_0_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_0_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_0_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_0_6_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_0_6_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_0_6_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_0_6_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_0_7_source: (),
    #[cfg(test)]
    mir_unit_0_7_argument: (),
    #[cfg(test)]
    mir_unit_0_7_returned: (),
    #[cfg(test)]
    mir_unit_0_7_caller: (),
    #[cfg(test)]
    mir_unit_0_8_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_8_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_8_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_8_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_0_8_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_0_8_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_0_8_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_0_8_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_9_source: bool,
    #[cfg(test)]
    mir_unit_0_9_argument: bool,
    #[cfg(test)]
    mir_unit_0_9_returned: bool,
    #[cfg(test)]
    mir_unit_0_9_caller: bool,
    #[cfg(test)]
    mir_unit_0_10_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_10_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_10_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_10_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_0_11_source: (),
    #[cfg(test)]
    mir_unit_0_11_argument: (),
    #[cfg(test)]
    mir_unit_0_11_returned: (),
    #[cfg(test)]
    mir_unit_0_11_caller: (),
    #[cfg(test)]
    mir_unit_0_12_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_12_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_12_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_12_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_0_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_0_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_0_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_0_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_0_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_0_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_0_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_0_2_source: u32,
    #[cfg(test)]
    mir_unit_0_2_argument: u32,
    #[cfg(test)]
    mir_unit_0_2_returned: u32,
    #[cfg(test)]
    mir_unit_0_2_caller: u32,
    #[cfg(test)]
    alias_unit_0_2_0_function_source: u32,
    #[cfg(test)]
    alias_unit_0_2_0_function_argument: u32,
    #[cfg(test)]
    alias_unit_0_2_0_function_returned: u32,
    #[cfg(test)]
    alias_unit_0_2_0_function_caller: u32,
    #[cfg(test)]
    mir_unit_0_3_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_3_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_3_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_0_3_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_0_3_0_returned_source: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_0_3_0_returned_argument: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_0_3_0_returned_returned: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    alias_unit_0_3_0_returned_caller: &'static mut Option<Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    literal_unit_0_0_source: &'static str,
    #[cfg(test)]
    literal_unit_0_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_0_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_0_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_1_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_3_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_3_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_3_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_3_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_4_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_4_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_4_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_4_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_5_source: isize,
    #[cfg(test)]
    mir_unit_1_5_argument: isize,
    #[cfg(test)]
    mir_unit_1_5_returned: isize,
    #[cfg(test)]
    mir_unit_1_5_caller: isize,
    #[cfg(test)]
    mir_unit_1_6_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_6_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_6_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_6_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_6_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_6_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_6_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_6_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_7_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_7_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_7_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_7_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_8_source: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_8_argument: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_8_returned: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_8_caller: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_9_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_9_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_9_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_9_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_10_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_10_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_10_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_10_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_11_source: isize,
    #[cfg(test)]
    mir_unit_1_11_argument: isize,
    #[cfg(test)]
    mir_unit_1_11_returned: isize,
    #[cfg(test)]
    mir_unit_1_11_caller: isize,
    #[cfg(test)]
    mir_unit_1_12_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_12_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_12_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_13_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_13_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_13_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_13_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_1_13_0_val_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_1_13_0_val_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_1_13_0_val_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_1_13_0_val_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_14_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_14_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_14_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_14_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_15_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_15_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_15_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_15_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_16_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_16_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_16_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_16_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_17_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_1_17_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_1_17_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_1_17_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_1_18_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_18_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_18_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_18_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_19_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_19_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_19_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_19_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_20_source: isize,
    #[cfg(test)]
    mir_unit_1_20_argument: isize,
    #[cfg(test)]
    mir_unit_1_20_returned: isize,
    #[cfg(test)]
    mir_unit_1_20_caller: isize,
    #[cfg(test)]
    mir_unit_1_21_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_21_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_21_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_21_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_21_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_21_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_21_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_21_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_22_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_22_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_22_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_22_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_22_0_descriptor_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_22_0_descriptor_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_22_0_descriptor_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_22_0_descriptor_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_23_source: usize,
    #[cfg(test)]
    mir_unit_1_23_argument: usize,
    #[cfg(test)]
    mir_unit_1_23_returned: usize,
    #[cfg(test)]
    mir_unit_1_23_caller: usize,
    #[cfg(test)]
    alias_unit_1_23_0_params_source: usize,
    #[cfg(test)]
    alias_unit_1_23_0_params_argument: usize,
    #[cfg(test)]
    alias_unit_1_23_0_params_returned: usize,
    #[cfg(test)]
    alias_unit_1_23_0_params_caller: usize,
    #[cfg(test)]
    mir_unit_1_24_source: (crate::experimental_wasi::WasiFunction, usize),
    #[cfg(test)]
    mir_unit_1_24_argument: (crate::experimental_wasi::WasiFunction, usize),
    #[cfg(test)]
    mir_unit_1_24_returned: (crate::experimental_wasi::WasiFunction, usize),
    #[cfg(test)]
    mir_unit_1_24_caller: (crate::experimental_wasi::WasiFunction, usize),
    #[cfg(test)]
    mir_unit_1_25_source: std::option::Option<crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_25_argument: std::option::Option<crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_25_returned: std::option::Option<crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_25_caller: std::option::Option<crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_26_source: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_26_argument: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_26_returned: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_26_caller: std::option::Option<&'static crate::experimental_wasi::WasiFunction>,
    #[cfg(test)]
    mir_unit_1_27_source: &'static [crate::experimental_wasi::WasiFunction],
    #[cfg(test)]
    mir_unit_1_27_argument: &'static [crate::experimental_wasi::WasiFunction],
    #[cfg(test)]
    mir_unit_1_27_returned: &'static [crate::experimental_wasi::WasiFunction],
    #[cfg(test)]
    mir_unit_1_27_caller: &'static [crate::experimental_wasi::WasiFunction],
    #[cfg(test)]
    mir_unit_1_28_source: &'static [crate::experimental_wasi::WasiFunction; 34],
    #[cfg(test)]
    mir_unit_1_28_argument: &'static [crate::experimental_wasi::WasiFunction; 34],
    #[cfg(test)]
    mir_unit_1_28_returned: &'static [crate::experimental_wasi::WasiFunction; 34],
    #[cfg(test)]
    mir_unit_1_28_caller: &'static [crate::experimental_wasi::WasiFunction; 34],
    #[cfg(test)]
    mir_unit_1_29_source: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_29_argument: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_29_returned: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_29_caller: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_30_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_30_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_30_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_30_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_31_source: usize,
    #[cfg(test)]
    mir_unit_1_31_argument: usize,
    #[cfg(test)]
    mir_unit_1_31_returned: usize,
    #[cfg(test)]
    mir_unit_1_31_caller: usize,
    #[cfg(test)]
    mir_unit_1_32_source: isize,
    #[cfg(test)]
    mir_unit_1_32_argument: isize,
    #[cfg(test)]
    mir_unit_1_32_returned: isize,
    #[cfg(test)]
    mir_unit_1_32_caller: isize,
    #[cfg(test)]
    mir_unit_1_33_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_33_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_33_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_33_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_0_descriptor_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_0_descriptor_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_0_descriptor_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_0_descriptor_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_1_descriptor_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_1_descriptor_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_1_descriptor_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_1_33_1_descriptor_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_34_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_34_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_34_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_34_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_36_source: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    #[cfg(test)]
    mir_unit_1_36_argument: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    #[cfg(test)]
    mir_unit_1_36_returned: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    #[cfg(test)]
    mir_unit_1_36_caller: std::option::Option<crate::experimental::descriptors::SignatureView<'static>>,
    #[cfg(test)]
    mir_unit_1_37_source: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_37_argument: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_37_returned: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_37_caller: &'static crate::experimental::swift::ValidatedSwiftReactor,
    #[cfg(test)]
    mir_unit_1_38_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_38_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_38_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_38_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_39_source: isize,
    #[cfg(test)]
    mir_unit_1_39_argument: isize,
    #[cfg(test)]
    mir_unit_1_39_returned: isize,
    #[cfg(test)]
    mir_unit_1_39_caller: isize,
    #[cfg(test)]
    mir_unit_1_41_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_41_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_41_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_41_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_42_source: bool,
    #[cfg(test)]
    mir_unit_1_42_argument: bool,
    #[cfg(test)]
    mir_unit_1_42_returned: bool,
    #[cfg(test)]
    mir_unit_1_42_caller: bool,
    #[cfg(test)]
    mir_unit_1_43_source: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_43_argument: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_43_returned: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_43_caller: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_44_source: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_44_argument: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_44_returned: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_44_caller: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_45_source: &'static [Type],
    #[cfg(test)]
    mir_unit_1_45_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_1_45_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_1_45_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_1_46_source: bool,
    #[cfg(test)]
    mir_unit_1_46_argument: bool,
    #[cfg(test)]
    mir_unit_1_46_returned: bool,
    #[cfg(test)]
    mir_unit_1_46_caller: bool,
    #[cfg(test)]
    mir_unit_1_47_source: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_47_argument: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_47_returned: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_47_caller: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_48_source: &'static [Type],
    #[cfg(test)]
    mir_unit_1_48_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_1_48_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_1_48_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_1_49_source: &'static std::option::Option<Type>,
    #[cfg(test)]
    mir_unit_1_49_argument: &'static std::option::Option<Type>,
    #[cfg(test)]
    mir_unit_1_49_returned: &'static std::option::Option<Type>,
    #[cfg(test)]
    mir_unit_1_49_caller: &'static std::option::Option<Type>,
    #[cfg(test)]
    mir_unit_1_50_source: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_50_argument: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_50_returned: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_50_caller: &'static &'static [Type],
    #[cfg(test)]
    mir_unit_1_51_source: &'static [Type],
    #[cfg(test)]
    mir_unit_1_51_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_1_51_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_1_51_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_1_52_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_52_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_52_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_52_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_53_source: usize,
    #[cfg(test)]
    mir_unit_1_53_argument: usize,
    #[cfg(test)]
    mir_unit_1_53_returned: usize,
    #[cfg(test)]
    mir_unit_1_53_caller: usize,
    #[cfg(test)]
    mir_unit_1_54_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_54_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_54_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_54_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_55_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_55_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_55_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_55_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_56_source: isize,
    #[cfg(test)]
    mir_unit_1_56_argument: isize,
    #[cfg(test)]
    mir_unit_1_56_returned: isize,
    #[cfg(test)]
    mir_unit_1_56_caller: isize,
    #[cfg(test)]
    mir_unit_1_58_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_58_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_58_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_58_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_59_source: usize,
    #[cfg(test)]
    mir_unit_1_59_argument: usize,
    #[cfg(test)]
    mir_unit_1_59_returned: usize,
    #[cfg(test)]
    mir_unit_1_59_caller: usize,
    #[cfg(test)]
    mir_unit_1_60_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_60_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_60_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_60_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_61_source: isize,
    #[cfg(test)]
    mir_unit_1_61_argument: isize,
    #[cfg(test)]
    mir_unit_1_61_returned: isize,
    #[cfg(test)]
    mir_unit_1_61_caller: isize,
    #[cfg(test)]
    mir_unit_1_63_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_63_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_63_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_63_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_64_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_64_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_64_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_64_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_65_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_1_65_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_1_65_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_1_65_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_1_66_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_66_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_66_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_66_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_67_source: isize,
    #[cfg(test)]
    mir_unit_1_67_argument: isize,
    #[cfg(test)]
    mir_unit_1_67_returned: isize,
    #[cfg(test)]
    mir_unit_1_67_caller: isize,
    #[cfg(test)]
    mir_unit_1_69_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_69_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_69_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_69_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_70_source: bool,
    #[cfg(test)]
    mir_unit_1_70_argument: bool,
    #[cfg(test)]
    mir_unit_1_70_returned: bool,
    #[cfg(test)]
    mir_unit_1_70_caller: bool,
    #[cfg(test)]
    mir_unit_1_71_source: usize,
    #[cfg(test)]
    mir_unit_1_71_argument: usize,
    #[cfg(test)]
    mir_unit_1_71_returned: usize,
    #[cfg(test)]
    mir_unit_1_71_caller: usize,
    #[cfg(test)]
    mir_unit_1_72_source: usize,
    #[cfg(test)]
    mir_unit_1_72_argument: usize,
    #[cfg(test)]
    mir_unit_1_72_returned: usize,
    #[cfg(test)]
    mir_unit_1_72_caller: usize,
    #[cfg(test)]
    mir_unit_1_73_source: bool,
    #[cfg(test)]
    mir_unit_1_73_argument: bool,
    #[cfg(test)]
    mir_unit_1_73_returned: bool,
    #[cfg(test)]
    mir_unit_1_73_caller: bool,
    #[cfg(test)]
    mir_unit_1_74_source: usize,
    #[cfg(test)]
    mir_unit_1_74_argument: usize,
    #[cfg(test)]
    mir_unit_1_74_returned: usize,
    #[cfg(test)]
    mir_unit_1_74_caller: usize,
    #[cfg(test)]
    mir_unit_1_75_source: bool,
    #[cfg(test)]
    mir_unit_1_75_argument: bool,
    #[cfg(test)]
    mir_unit_1_75_returned: bool,
    #[cfg(test)]
    mir_unit_1_75_caller: bool,
    #[cfg(test)]
    mir_unit_1_76_source: usize,
    #[cfg(test)]
    mir_unit_1_76_argument: usize,
    #[cfg(test)]
    mir_unit_1_76_returned: usize,
    #[cfg(test)]
    mir_unit_1_76_caller: usize,
    #[cfg(test)]
    mir_unit_1_77_source: usize,
    #[cfg(test)]
    mir_unit_1_77_argument: usize,
    #[cfg(test)]
    mir_unit_1_77_returned: usize,
    #[cfg(test)]
    mir_unit_1_77_caller: usize,
    #[cfg(test)]
    mir_unit_1_78_source: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_78_argument: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_78_returned: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_78_caller: &'static std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_79_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_79_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_79_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_79_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_80_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_80_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_80_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_80_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_81_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_81_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_81_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_81_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_83_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_83_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_83_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_83_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_1_84_source: &'static mut std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_84_argument: &'static mut std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_84_returned: &'static mut std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_84_caller: &'static mut std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_85_source: isize,
    #[cfg(test)]
    mir_unit_1_85_argument: isize,
    #[cfg(test)]
    mir_unit_1_85_returned: isize,
    #[cfg(test)]
    mir_unit_1_85_caller: isize,
    #[cfg(test)]
    mir_unit_1_87_source: bool,
    #[cfg(test)]
    mir_unit_1_87_argument: bool,
    #[cfg(test)]
    mir_unit_1_87_returned: bool,
    #[cfg(test)]
    mir_unit_1_87_caller: bool,
    #[cfg(test)]
    mir_unit_1_88_source: &'static Type,
    #[cfg(test)]
    mir_unit_1_88_argument: &'static Type,
    #[cfg(test)]
    mir_unit_1_88_returned: &'static Type,
    #[cfg(test)]
    mir_unit_1_88_caller: &'static Type,
    #[cfg(test)]
    mir_unit_1_89_source: Type,
    #[cfg(test)]
    mir_unit_1_89_argument: Type,
    #[cfg(test)]
    mir_unit_1_89_returned: Type,
    #[cfg(test)]
    mir_unit_1_89_caller: Type,
    #[cfg(test)]
    mir_unit_1_90_source: Value,
    #[cfg(test)]
    mir_unit_1_90_argument: Value,
    #[cfg(test)]
    mir_unit_1_90_returned: Value,
    #[cfg(test)]
    mir_unit_1_90_caller: Value,
    #[cfg(test)]
    mir_unit_1_91_source: &'static Value,
    #[cfg(test)]
    mir_unit_1_91_argument: &'static Value,
    #[cfg(test)]
    mir_unit_1_91_returned: &'static Value,
    #[cfg(test)]
    mir_unit_1_91_caller: &'static Value,
    #[cfg(test)]
    mir_unit_1_92_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_92_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_92_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_92_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_93_source: usize,
    #[cfg(test)]
    mir_unit_1_93_argument: usize,
    #[cfg(test)]
    mir_unit_1_93_returned: usize,
    #[cfg(test)]
    mir_unit_1_93_caller: usize,
    #[cfg(test)]
    mir_unit_1_94_source: (usize, bool),
    #[cfg(test)]
    mir_unit_1_94_argument: (usize, bool),
    #[cfg(test)]
    mir_unit_1_94_returned: (usize, bool),
    #[cfg(test)]
    mir_unit_1_94_caller: (usize, bool),
    #[cfg(test)]
    mir_unit_1_95_source: &'static Type,
    #[cfg(test)]
    mir_unit_1_95_argument: &'static Type,
    #[cfg(test)]
    mir_unit_1_95_returned: &'static Type,
    #[cfg(test)]
    mir_unit_1_95_caller: &'static Type,
    #[cfg(test)]
    mir_unit_1_96_source: &'static [Type],
    #[cfg(test)]
    mir_unit_1_96_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_1_96_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_1_96_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_1_97_source: usize,
    #[cfg(test)]
    mir_unit_1_97_argument: usize,
    #[cfg(test)]
    mir_unit_1_97_returned: usize,
    #[cfg(test)]
    mir_unit_1_97_caller: usize,
    #[cfg(test)]
    mir_unit_1_98_source: bool,
    #[cfg(test)]
    mir_unit_1_98_argument: bool,
    #[cfg(test)]
    mir_unit_1_98_returned: bool,
    #[cfg(test)]
    mir_unit_1_98_caller: bool,
    #[cfg(test)]
    mir_unit_1_99_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_99_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_99_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_99_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_100_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_100_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_100_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_100_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_1_101_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_101_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_101_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_101_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_102_source: isize,
    #[cfg(test)]
    mir_unit_1_102_argument: isize,
    #[cfg(test)]
    mir_unit_1_102_returned: isize,
    #[cfg(test)]
    mir_unit_1_102_caller: isize,
    #[cfg(test)]
    mir_unit_1_104_source: &'static [Value],
    #[cfg(test)]
    mir_unit_1_104_argument: &'static [Value],
    #[cfg(test)]
    mir_unit_1_104_returned: &'static [Value],
    #[cfg(test)]
    mir_unit_1_104_caller: &'static [Value],
    #[cfg(test)]
    alias_unit_1_104_0_arguments_source: &'static [Value],
    #[cfg(test)]
    alias_unit_1_104_0_arguments_argument: &'static [Value],
    #[cfg(test)]
    alias_unit_1_104_0_arguments_returned: &'static [Value],
    #[cfg(test)]
    alias_unit_1_104_0_arguments_caller: &'static [Value],
    #[cfg(test)]
    mir_unit_1_105_source: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_105_argument: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_105_returned: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_105_caller: &'static std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_106_source: std::ops::RangeFrom<usize>,
    #[cfg(test)]
    mir_unit_1_106_argument: std::ops::RangeFrom<usize>,
    #[cfg(test)]
    mir_unit_1_106_returned: std::ops::RangeFrom<usize>,
    #[cfg(test)]
    mir_unit_1_106_caller: std::ops::RangeFrom<usize>,
    #[cfg(test)]
    mir_unit_1_107_source: &'static mut [u8],
    #[cfg(test)]
    mir_unit_1_107_argument: &'static mut [u8],
    #[cfg(test)]
    mir_unit_1_107_returned: &'static mut [u8],
    #[cfg(test)]
    mir_unit_1_107_caller: &'static mut [u8],
    #[cfg(test)]
    alias_unit_1_107_0_memory_source: &'static mut [u8],
    #[cfg(test)]
    alias_unit_1_107_0_memory_argument: &'static mut [u8],
    #[cfg(test)]
    alias_unit_1_107_0_memory_returned: &'static mut [u8],
    #[cfg(test)]
    alias_unit_1_107_0_memory_caller: &'static mut [u8],
    #[cfg(test)]
    mir_unit_1_108_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    #[cfg(test)]
    mir_unit_1_108_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    #[cfg(test)]
    mir_unit_1_108_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    #[cfg(test)]
    mir_unit_1_108_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::Errno>,
    #[cfg(test)]
    mir_unit_1_109_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_109_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_109_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_109_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_110_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_110_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_110_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_110_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_1_111_source: isize,
    #[cfg(test)]
    mir_unit_1_111_argument: isize,
    #[cfg(test)]
    mir_unit_1_111_returned: isize,
    #[cfg(test)]
    mir_unit_1_111_caller: isize,
    #[cfg(test)]
    mir_unit_1_114_source: bool,
    #[cfg(test)]
    mir_unit_1_114_argument: bool,
    #[cfg(test)]
    mir_unit_1_114_returned: bool,
    #[cfg(test)]
    mir_unit_1_114_caller: bool,
    #[cfg(test)]
    mir_unit_1_115_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_115_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_115_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_115_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_116_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_116_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_116_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_116_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_1_117_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_117_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_117_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_117_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_118_source: (),
    #[cfg(test)]
    mir_unit_1_118_argument: (),
    #[cfg(test)]
    mir_unit_1_118_returned: (),
    #[cfg(test)]
    mir_unit_1_118_caller: (),
    #[cfg(test)]
    mir_unit_1_119_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_119_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_119_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_119_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_120_source: crate::experimental_swift_reactor::control::Live,
    #[cfg(test)]
    mir_unit_1_120_argument: crate::experimental_swift_reactor::control::Live,
    #[cfg(test)]
    mir_unit_1_120_returned: crate::experimental_swift_reactor::control::Live,
    #[cfg(test)]
    mir_unit_1_120_caller: crate::experimental_swift_reactor::control::Live,
    #[cfg(test)]
    mir_unit_1_121_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_121_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_121_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_121_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_1_122_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_122_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_122_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_122_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_1_123_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_123_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_123_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_123_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_124_source: isize,
    #[cfg(test)]
    mir_unit_1_124_argument: isize,
    #[cfg(test)]
    mir_unit_1_124_returned: isize,
    #[cfg(test)]
    mir_unit_1_124_caller: isize,
    #[cfg(test)]
    mir_unit_1_126_source: u16,
    #[cfg(test)]
    mir_unit_1_126_argument: u16,
    #[cfg(test)]
    mir_unit_1_126_returned: u16,
    #[cfg(test)]
    mir_unit_1_126_caller: u16,
    #[cfg(test)]
    alias_unit_1_126_0_official_errno_source: u16,
    #[cfg(test)]
    alias_unit_1_126_0_official_errno_argument: u16,
    #[cfg(test)]
    alias_unit_1_126_0_official_errno_returned: u16,
    #[cfg(test)]
    alias_unit_1_126_0_official_errno_caller: u16,
    #[cfg(test)]
    mir_unit_1_127_source: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_127_argument: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_127_returned: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_127_caller: &'static mut crate::experimental_swift_reactor::execution::ExecutionOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_128_source: Value,
    #[cfg(test)]
    mir_unit_1_128_argument: Value,
    #[cfg(test)]
    mir_unit_1_128_returned: Value,
    #[cfg(test)]
    mir_unit_1_128_caller: Value,
    #[cfg(test)]
    mir_unit_1_129_source: i32,
    #[cfg(test)]
    mir_unit_1_129_argument: i32,
    #[cfg(test)]
    mir_unit_1_129_returned: i32,
    #[cfg(test)]
    mir_unit_1_129_caller: i32,
    #[cfg(test)]
    mir_unit_1_130_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_130_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_130_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_130_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_131_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_131_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_131_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_131_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_132_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_132_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_132_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_132_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_133_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_133_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_133_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_133_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_134_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_134_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_134_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_134_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_135_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_135_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_135_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_135_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_136_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_136_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_136_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_136_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_1_137_source: &'static [Type],
    #[cfg(test)]
    mir_unit_1_137_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_1_137_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_1_137_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_1_138_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_138_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_138_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_138_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_139_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_139_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_139_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_139_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_1_140_source: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_140_argument: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_140_returned: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_140_caller: &'static mut std::vec::Vec<crate::experimental::execution::Control>,
    #[cfg(test)]
    mir_unit_1_141_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_141_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_141_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_141_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_142_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_142_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_142_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_142_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_143_source: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_143_argument: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_143_returned: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_143_caller: &'static mut std::vec::Vec<u8>,
    #[cfg(test)]
    mir_unit_1_144_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_144_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_144_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_144_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_145_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_145_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_145_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_145_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_146_source: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_146_argument: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_146_returned: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_146_caller: &'static mut std::vec::Vec<Value>,
    #[cfg(test)]
    mir_unit_1_147_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_147_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_147_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_147_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_1_148_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_148_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_148_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_148_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_1_149_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_1_149_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_1_149_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_1_149_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameCleanupState,
    #[cfg(test)]
    mir_unit_1_57_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_57_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_57_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_57_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_57_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_57_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_57_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_57_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_62_source: usize,
    #[cfg(test)]
    mir_unit_1_62_argument: usize,
    #[cfg(test)]
    mir_unit_1_62_returned: usize,
    #[cfg(test)]
    mir_unit_1_62_caller: usize,
    #[cfg(test)]
    alias_unit_1_62_0_base_source: usize,
    #[cfg(test)]
    alias_unit_1_62_0_base_argument: usize,
    #[cfg(test)]
    alias_unit_1_62_0_base_returned: usize,
    #[cfg(test)]
    alias_unit_1_62_0_base_caller: usize,
    #[cfg(test)]
    alias_unit_1_62_1_base_source: usize,
    #[cfg(test)]
    alias_unit_1_62_1_base_argument: usize,
    #[cfg(test)]
    alias_unit_1_62_1_base_returned: usize,
    #[cfg(test)]
    alias_unit_1_62_1_base_caller: usize,
    #[cfg(test)]
    mir_unit_1_68_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_1_68_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_1_68_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_1_68_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_1_68_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_1_82_source: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_82_argument: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_82_returned: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_82_caller: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_1_82_0_iter_source: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_1_82_0_iter_argument: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_1_82_0_iter_returned: std::ops::Range<usize>,
    #[cfg(test)]
    alias_unit_1_82_0_iter_caller: std::ops::Range<usize>,
    #[cfg(test)]
    mir_unit_1_103_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_103_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_103_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_103_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_103_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_103_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_103_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_103_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_86_source: usize,
    #[cfg(test)]
    mir_unit_1_86_argument: usize,
    #[cfg(test)]
    mir_unit_1_86_returned: usize,
    #[cfg(test)]
    mir_unit_1_86_caller: usize,
    #[cfg(test)]
    alias_unit_1_86_0_index_source: usize,
    #[cfg(test)]
    alias_unit_1_86_0_index_argument: usize,
    #[cfg(test)]
    alias_unit_1_86_0_index_returned: usize,
    #[cfg(test)]
    alias_unit_1_86_0_index_caller: usize,
    #[cfg(test)]
    mir_unit_1_125_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_125_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_125_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_125_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_1_125_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_1_125_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_1_125_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_1_125_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_1_112_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_112_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_112_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_112_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_112_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_112_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_112_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_1_112_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_1_113_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_1_113_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_1_113_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_1_113_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_0_errno_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_0_errno_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_0_errno_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_0_errno_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_1_val_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_1_val_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_1_val_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_1_113_1_val_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_1_35_source: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_35_argument: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_35_returned: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_35_caller: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_35_0_signature_source: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_35_0_signature_argument: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_35_0_signature_returned: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_35_0_signature_caller: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_40_source: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_40_argument: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_40_returned: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_40_caller: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_40_0_signature_source: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_40_0_signature_argument: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_40_0_signature_returned: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    alias_unit_1_40_0_signature_caller: crate::experimental::descriptors::SignatureView<'static>,
    #[cfg(test)]
    mir_unit_1_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_1_1_0_self_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_1_2_source: u32,
    #[cfg(test)]
    mir_unit_1_2_argument: u32,
    #[cfg(test)]
    mir_unit_1_2_returned: u32,
    #[cfg(test)]
    mir_unit_1_2_caller: u32,
    #[cfg(test)]
    alias_unit_1_2_0_function_source: u32,
    #[cfg(test)]
    alias_unit_1_2_0_function_argument: u32,
    #[cfg(test)]
    alias_unit_1_2_0_function_returned: u32,
    #[cfg(test)]
    alias_unit_1_2_0_function_caller: u32,
    #[cfg(test)]
    literal_unit_1_0_source: &'static str,
    #[cfg(test)]
    literal_unit_1_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_0_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_1_source: &'static str,
    #[cfg(test)]
    literal_unit_1_1_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_1_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_1_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_2_source: &'static str,
    #[cfg(test)]
    literal_unit_1_2_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_2_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_2_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_3_source: &'static str,
    #[cfg(test)]
    literal_unit_1_3_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_3_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_3_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_4_source: &'static str,
    #[cfg(test)]
    literal_unit_1_4_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_4_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_4_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_5_source: &'static str,
    #[cfg(test)]
    literal_unit_1_5_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_5_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_5_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_6_source: usize,
    #[cfg(test)]
    literal_unit_1_6_argument: usize,
    #[cfg(test)]
    literal_unit_1_6_returned: usize,
    #[cfg(test)]
    literal_unit_1_6_caller: usize,
    #[cfg(test)]
    literal_unit_1_7_source: usize,
    #[cfg(test)]
    literal_unit_1_7_argument: usize,
    #[cfg(test)]
    literal_unit_1_7_returned: usize,
    #[cfg(test)]
    literal_unit_1_7_caller: usize,
    #[cfg(test)]
    literal_unit_1_8_source: &'static str,
    #[cfg(test)]
    literal_unit_1_8_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_8_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_8_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_9_source: &'static str,
    #[cfg(test)]
    literal_unit_1_9_argument: &'static str,
    #[cfg(test)]
    literal_unit_1_9_returned: &'static str,
    #[cfg(test)]
    literal_unit_1_9_caller: &'static str,
    #[cfg(test)]
    literal_unit_1_10_source: bool,
    #[cfg(test)]
    literal_unit_1_10_argument: bool,
    #[cfg(test)]
    literal_unit_1_10_returned: bool,
    #[cfg(test)]
    literal_unit_1_10_caller: bool,
    #[cfg(test)]
    mir_unit_2_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_3_source: bool,
    #[cfg(test)]
    mir_unit_2_3_argument: bool,
    #[cfg(test)]
    mir_unit_2_3_returned: bool,
    #[cfg(test)]
    mir_unit_2_3_caller: bool,
    #[cfg(test)]
    mir_unit_2_4_source: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_4_argument: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_4_returned: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_4_caller: &'static std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_5_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_2_5_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_2_5_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_2_5_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_2_5_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_2_5_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_2_5_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_2_5_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_2_6_source: (),
    #[cfg(test)]
    mir_unit_2_6_argument: (),
    #[cfg(test)]
    mir_unit_2_6_returned: (),
    #[cfg(test)]
    mir_unit_2_6_caller: (),
    #[cfg(test)]
    mir_unit_2_7_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_7_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_7_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_7_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_2_7_0_result_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_2_7_0_result_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_2_7_0_result_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_2_7_0_result_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_8_source: bool,
    #[cfg(test)]
    mir_unit_2_8_argument: bool,
    #[cfg(test)]
    mir_unit_2_8_returned: bool,
    #[cfg(test)]
    mir_unit_2_8_caller: bool,
    #[cfg(test)]
    mir_unit_2_9_source: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_9_argument: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_9_returned: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_9_caller: &'static std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_2_10_source: (),
    #[cfg(test)]
    mir_unit_2_10_argument: (),
    #[cfg(test)]
    mir_unit_2_10_returned: (),
    #[cfg(test)]
    mir_unit_2_10_caller: (),
    #[cfg(test)]
    mir_unit_2_11_source: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_11_argument: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_11_returned: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_11_caller: std::option::Option<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_2_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_2_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_2_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_2_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_2_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_2_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_2_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_2_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_2_2_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_2_2_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_2_2_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    mir_unit_2_2_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_2_2_0_storage_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_2_2_0_storage_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_2_2_0_storage_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    alias_unit_2_2_0_storage_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationStorage<'static>,
    #[cfg(test)]
    literal_unit_2_0_source: &'static str,
    #[cfg(test)]
    literal_unit_2_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_2_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_2_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_3_0_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_0_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_0_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_0_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_2_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_2_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_2_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_2_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_3_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_3_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_3_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_3_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_4_source: isize,
    #[cfg(test)]
    mir_unit_3_4_argument: isize,
    #[cfg(test)]
    mir_unit_3_4_returned: isize,
    #[cfg(test)]
    mir_unit_3_4_caller: isize,
    #[cfg(test)]
    mir_unit_3_5_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_5_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_5_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_5_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_5_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_5_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_5_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_5_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_6_source: u32,
    #[cfg(test)]
    mir_unit_3_6_argument: u32,
    #[cfg(test)]
    mir_unit_3_6_returned: u32,
    #[cfg(test)]
    mir_unit_3_6_caller: u32,
    #[cfg(test)]
    alias_unit_3_6_0_function_source: u32,
    #[cfg(test)]
    alias_unit_3_6_0_function_argument: u32,
    #[cfg(test)]
    alias_unit_3_6_0_function_returned: u32,
    #[cfg(test)]
    alias_unit_3_6_0_function_caller: u32,
    #[cfg(test)]
    mir_unit_3_7_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_7_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_7_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_7_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_7_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_7_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_7_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_7_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_8_source: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_3_8_argument: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_3_8_returned: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_3_8_caller: (u32, crate::experimental::cache::DecodedInstruction),
    #[cfg(test)]
    mir_unit_3_9_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_9_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_9_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_9_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_10_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_10_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_10_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_10_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_11_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_11_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_11_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_11_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_12_source: isize,
    #[cfg(test)]
    mir_unit_3_12_argument: isize,
    #[cfg(test)]
    mir_unit_3_12_returned: isize,
    #[cfg(test)]
    mir_unit_3_12_caller: isize,
    #[cfg(test)]
    mir_unit_3_13_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_13_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_13_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_13_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_1_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_1_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_1_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_13_1_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_14_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_14_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_14_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_14_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_15_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_3_15_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_3_15_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_3_15_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental::cache::FunctionView<'static>>,
    #[cfg(test)]
    mir_unit_3_16_source: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_16_argument: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_16_returned: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_16_caller: std::result::Result<crate::experimental::cache::FunctionView<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_17_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_17_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_17_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_17_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_18_source: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_3_18_argument: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_3_18_returned: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_3_18_caller: &'static crate::experimental_swift_reactor::cache::SwiftFunctionPin,
    #[cfg(test)]
    mir_unit_3_19_source: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_3_19_argument: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_3_19_returned: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_3_19_caller: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    #[cfg(test)]
    mir_unit_3_20_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_20_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_20_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_20_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_21_source: isize,
    #[cfg(test)]
    mir_unit_3_21_argument: isize,
    #[cfg(test)]
    mir_unit_3_21_returned: isize,
    #[cfg(test)]
    mir_unit_3_21_caller: isize,
    #[cfg(test)]
    mir_unit_3_25_source: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_3_25_argument: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_3_25_returned: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_3_25_caller: std::option::Option<&'static crate::experimental::cache::DecodedInstruction>,
    #[cfg(test)]
    mir_unit_3_26_source: usize,
    #[cfg(test)]
    mir_unit_3_26_argument: usize,
    #[cfg(test)]
    mir_unit_3_26_returned: usize,
    #[cfg(test)]
    mir_unit_3_26_caller: usize,
    #[cfg(test)]
    mir_unit_3_27_source: isize,
    #[cfg(test)]
    mir_unit_3_27_argument: isize,
    #[cfg(test)]
    mir_unit_3_27_returned: isize,
    #[cfg(test)]
    mir_unit_3_27_caller: isize,
    #[cfg(test)]
    mir_unit_3_29_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_29_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_29_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_29_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_30_source: u32,
    #[cfg(test)]
    mir_unit_3_30_argument: u32,
    #[cfg(test)]
    mir_unit_3_30_returned: u32,
    #[cfg(test)]
    mir_unit_3_30_caller: u32,
    #[cfg(test)]
    mir_unit_3_31_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_31_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_31_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_31_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_32_source: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_3_32_argument: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_3_32_returned: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_3_32_caller: crate::experimental_swift_reactor::control::SwiftRunStage,
    #[cfg(test)]
    mir_unit_3_33_source: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_3_33_argument: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_3_33_returned: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_3_33_caller: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_3_34_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_34_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_34_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_34_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_35_source: usize,
    #[cfg(test)]
    mir_unit_3_35_argument: usize,
    #[cfg(test)]
    mir_unit_3_35_returned: usize,
    #[cfg(test)]
    mir_unit_3_35_caller: usize,
    #[cfg(test)]
    mir_unit_3_36_source: isize,
    #[cfg(test)]
    mir_unit_3_36_argument: isize,
    #[cfg(test)]
    mir_unit_3_36_returned: isize,
    #[cfg(test)]
    mir_unit_3_36_caller: isize,
    #[cfg(test)]
    mir_unit_3_38_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_38_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_38_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_38_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_39_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_39_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_39_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_39_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_40_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_40_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_40_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_40_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_41_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_41_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_41_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_41_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_3_42_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_3_42_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_3_42_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_3_42_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_3_43_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_3_43_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_3_43_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_3_43_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_3_44_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_44_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_44_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_44_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_45_source: isize,
    #[cfg(test)]
    mir_unit_3_45_argument: isize,
    #[cfg(test)]
    mir_unit_3_45_returned: isize,
    #[cfg(test)]
    mir_unit_3_45_caller: isize,
    #[cfg(test)]
    mir_unit_3_47_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_47_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_47_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_47_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_3_48_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_48_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_48_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_48_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_49_source: isize,
    #[cfg(test)]
    mir_unit_3_49_argument: isize,
    #[cfg(test)]
    mir_unit_3_49_returned: isize,
    #[cfg(test)]
    mir_unit_3_49_caller: isize,
    #[cfg(test)]
    mir_unit_3_52_source: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_52_argument: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_52_returned: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_52_caller: std::option::Option<&'static crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_53_source: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_53_argument: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_53_returned: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_53_caller: &'static [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_54_source: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_54_argument: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_54_returned: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_54_caller: &'static std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_55_source: isize,
    #[cfg(test)]
    mir_unit_3_55_argument: isize,
    #[cfg(test)]
    mir_unit_3_55_returned: isize,
    #[cfg(test)]
    mir_unit_3_55_caller: isize,
    #[cfg(test)]
    mir_unit_3_57_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_57_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_57_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_57_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_58_source: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_58_argument: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_58_returned: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_58_caller: std::option::Option<usize>,
    #[cfg(test)]
    mir_unit_3_59_source: isize,
    #[cfg(test)]
    mir_unit_3_59_argument: isize,
    #[cfg(test)]
    mir_unit_3_59_returned: isize,
    #[cfg(test)]
    mir_unit_3_59_caller: isize,
    #[cfg(test)]
    mir_unit_3_61_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_61_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_61_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_61_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_3_62_source: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_62_argument: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_62_returned: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_62_caller: &'static mut crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_63_source: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_63_argument: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_63_returned: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_63_caller: std::option::Option<&'static mut crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_64_source: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_64_argument: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_64_returned: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_64_caller: &'static mut [crate::experimental_swift_reactor::execution::SwiftFrame],
    #[cfg(test)]
    mir_unit_3_65_source: &'static str,
    #[cfg(test)]
    mir_unit_3_65_argument: &'static str,
    #[cfg(test)]
    mir_unit_3_65_returned: &'static str,
    #[cfg(test)]
    mir_unit_3_65_caller: &'static str,
    #[cfg(test)]
    mir_unit_3_66_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_66_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_66_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_66_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_67_source: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_67_argument: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_67_returned: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_67_caller: &'static mut crate::experimental_swift_reactor::cache::SwiftFunctionCache,
    #[cfg(test)]
    mir_unit_3_68_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_68_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_68_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_68_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_69_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_69_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_69_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_69_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_70_source: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_3_70_argument: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_3_70_returned: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_3_70_caller: &'static [crate::experimental::cache::DecodedInstruction],
    #[cfg(test)]
    mir_unit_3_71_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_71_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_71_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_71_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_3_72_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_72_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_72_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_72_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_3_73_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_73_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_73_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_73_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_74_source: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_74_argument: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_74_returned: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_74_caller: &'static mut std::vec::Vec<crate::experimental_swift_reactor::execution::SwiftFrame>,
    #[cfg(test)]
    mir_unit_3_37_source: u32,
    #[cfg(test)]
    mir_unit_3_37_argument: u32,
    #[cfg(test)]
    mir_unit_3_37_returned: u32,
    #[cfg(test)]
    mir_unit_3_37_caller: u32,
    #[cfg(test)]
    alias_unit_3_37_0_target_source: u32,
    #[cfg(test)]
    alias_unit_3_37_0_target_argument: u32,
    #[cfg(test)]
    alias_unit_3_37_0_target_returned: u32,
    #[cfg(test)]
    alias_unit_3_37_0_target_caller: u32,
    #[cfg(test)]
    alias_unit_3_37_1_target_source: u32,
    #[cfg(test)]
    alias_unit_3_37_1_target_argument: u32,
    #[cfg(test)]
    alias_unit_3_37_1_target_returned: u32,
    #[cfg(test)]
    alias_unit_3_37_1_target_caller: u32,
    #[cfg(test)]
    mir_unit_3_46_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_46_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_46_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_46_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_46_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_46_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_46_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_46_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_50_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_50_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_50_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_50_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_50_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_50_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_50_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_50_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_51_source: usize,
    #[cfg(test)]
    mir_unit_3_51_argument: usize,
    #[cfg(test)]
    mir_unit_3_51_returned: usize,
    #[cfg(test)]
    mir_unit_3_51_caller: usize,
    #[cfg(test)]
    alias_unit_3_51_0_current_pc_source: usize,
    #[cfg(test)]
    alias_unit_3_51_0_current_pc_argument: usize,
    #[cfg(test)]
    alias_unit_3_51_0_current_pc_returned: usize,
    #[cfg(test)]
    alias_unit_3_51_0_current_pc_caller: usize,
    #[cfg(test)]
    mir_unit_3_56_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_56_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_56_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_56_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_56_0_frame_source: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_56_0_frame_argument: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_56_0_frame_returned: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    alias_unit_3_56_0_frame_caller: &'static crate::experimental_swift_reactor::execution::SwiftFrame,
    #[cfg(test)]
    mir_unit_3_60_source: usize,
    #[cfg(test)]
    mir_unit_3_60_argument: usize,
    #[cfg(test)]
    mir_unit_3_60_returned: usize,
    #[cfg(test)]
    mir_unit_3_60_caller: usize,
    #[cfg(test)]
    alias_unit_3_60_0_pc_source: usize,
    #[cfg(test)]
    alias_unit_3_60_0_pc_argument: usize,
    #[cfg(test)]
    alias_unit_3_60_0_pc_returned: usize,
    #[cfg(test)]
    alias_unit_3_60_0_pc_caller: usize,
    #[cfg(test)]
    alias_unit_3_60_1_pc_source: usize,
    #[cfg(test)]
    alias_unit_3_60_1_pc_argument: usize,
    #[cfg(test)]
    alias_unit_3_60_1_pc_returned: usize,
    #[cfg(test)]
    alias_unit_3_60_1_pc_caller: usize,
    #[cfg(test)]
    mir_unit_3_22_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_22_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_22_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_22_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_22_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_22_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_22_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_3_22_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_3_23_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_3_23_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_3_23_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_3_23_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_0_view_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_0_view_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_0_view_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_0_view_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_1_val_source: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_1_val_argument: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_1_val_returned: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    alias_unit_3_23_1_val_caller: crate::experimental::cache::FunctionView<'static>,
    #[cfg(test)]
    mir_unit_3_24_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_24_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_24_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_24_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_24_0_instruction_source: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_24_0_instruction_argument: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_24_0_instruction_returned: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_24_0_instruction_caller: crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_28_source: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_28_argument: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_28_returned: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_28_caller: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_28_0_instruction_source: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_28_0_instruction_argument: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_28_0_instruction_returned: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    alias_unit_3_28_0_instruction_caller: &'static crate::experimental::cache::DecodedInstruction,
    #[cfg(test)]
    mir_unit_3_1_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_1_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_1_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    mir_unit_3_1_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_3_1_0_phase_source: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_3_1_0_phase_argument: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_3_1_0_phase_returned: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    alias_unit_3_1_0_phase_caller: &'static mut crate::experimental_swift_reactor::execution::frame_operations::FrameOperationPhase<'static>,
    #[cfg(test)]
    literal_unit_3_0_source: &'static str,
    #[cfg(test)]
    literal_unit_3_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_0_caller: &'static str,
    #[cfg(test)]
    literal_unit_3_1_source: &'static str,
    #[cfg(test)]
    literal_unit_3_1_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_1_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_1_caller: &'static str,
    #[cfg(test)]
    literal_unit_3_2_source: &'static str,
    #[cfg(test)]
    literal_unit_3_2_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_2_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_2_caller: &'static str,
    #[cfg(test)]
    literal_unit_3_3_source: usize,
    #[cfg(test)]
    literal_unit_3_3_argument: usize,
    #[cfg(test)]
    literal_unit_3_3_returned: usize,
    #[cfg(test)]
    literal_unit_3_3_caller: usize,
    #[cfg(test)]
    literal_unit_3_4_source: &'static str,
    #[cfg(test)]
    literal_unit_3_4_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_4_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_4_caller: &'static str,
    #[cfg(test)]
    literal_unit_3_5_source: usize,
    #[cfg(test)]
    literal_unit_3_5_argument: usize,
    #[cfg(test)]
    literal_unit_3_5_returned: usize,
    #[cfg(test)]
    literal_unit_3_5_caller: usize,
    #[cfg(test)]
    literal_unit_3_6_source: &'static str,
    #[cfg(test)]
    literal_unit_3_6_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_6_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_6_caller: &'static str,
    #[cfg(test)]
    literal_unit_3_7_source: &'static str,
    #[cfg(test)]
    literal_unit_3_7_argument: &'static str,
    #[cfg(test)]
    literal_unit_3_7_returned: &'static str,
    #[cfg(test)]
    literal_unit_3_7_caller: &'static str,
    #[cfg(test)]
    mir_unit_4_0_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_4_0_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_4_0_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_4_0_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_4_2_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_4_2_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_4_2_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_4_2_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_4_1_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_4_1_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_4_1_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_4_1_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_4_1_0_self_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_4_1_0_self_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_4_1_0_self_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_4_1_0_self_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_5_0_source: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_0_argument: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_0_returned: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_0_caller: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_4_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_4_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_4_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_4_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_5_5_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_5_5_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_5_5_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_5_5_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_5_6_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_5_6_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_5_6_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_5_6_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_5_7_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_7_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_7_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_7_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_8_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_5_8_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_5_8_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_5_8_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_5_8_0_header_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_5_8_0_header_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_5_8_0_header_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_5_8_0_header_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_5_9_source: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_9_argument: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_9_returned: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_9_caller: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_10_source: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_10_argument: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_10_returned: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_10_caller: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_5_11_source: isize,
    #[cfg(test)]
    mir_unit_5_11_argument: isize,
    #[cfg(test)]
    mir_unit_5_11_returned: isize,
    #[cfg(test)]
    mir_unit_5_11_caller: isize,
    #[cfg(test)]
    mir_unit_5_13_source: bool,
    #[cfg(test)]
    mir_unit_5_13_argument: bool,
    #[cfg(test)]
    mir_unit_5_13_returned: bool,
    #[cfg(test)]
    mir_unit_5_13_caller: bool,
    #[cfg(test)]
    mir_unit_5_14_source: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_14_argument: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_14_returned: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_14_caller: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_15_source: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_5_15_argument: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_5_15_returned: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_5_15_caller: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_5_16_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_5_16_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_5_16_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_5_16_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_5_17_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_17_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_17_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_17_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_18_source: isize,
    #[cfg(test)]
    mir_unit_5_18_argument: isize,
    #[cfg(test)]
    mir_unit_5_18_returned: isize,
    #[cfg(test)]
    mir_unit_5_18_caller: isize,
    #[cfg(test)]
    mir_unit_5_20_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_5_20_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_5_20_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_5_20_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_5_21_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_5_21_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_5_21_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_5_21_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_5_12_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_12_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_12_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_12_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_5_12_0_observation_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_5_12_0_observation_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_5_12_0_observation_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_5_12_0_observation_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_5_19_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_19_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_19_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_19_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_5_19_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_5_19_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_5_19_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_5_19_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_5_1_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_5_1_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_5_1_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_5_1_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_5_1_0_self_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_5_1_0_self_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_5_1_0_self_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_5_1_0_self_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_5_2_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_2_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_2_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_2_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_5_2_0_control_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_5_2_0_control_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_5_2_0_control_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_5_2_0_control_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_5_3_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_5_3_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_5_3_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_5_3_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_5_3_0_cursor_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_5_3_0_cursor_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_5_3_0_cursor_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_5_3_0_cursor_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    literal_unit_5_0_source: &'static str,
    #[cfg(test)]
    literal_unit_5_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_5_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_5_0_caller: &'static str,
    #[cfg(test)]
    mir_unit_6_0_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_6_0_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_6_0_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_6_0_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_6_2_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_6_2_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_6_2_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_6_2_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_6_3_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_6_3_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_6_3_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_6_3_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_6_1_source: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_6_1_argument: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_6_1_returned: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_6_1_caller: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    #[cfg(test)]
    mir_unit_7_0_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_0_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_0_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_0_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_7_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_7_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_7_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_7_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_7_7_0_usage_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_7_7_0_usage_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_7_7_0_usage_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    alias_unit_7_7_0_usage_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_8_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_8_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_8_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_8_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_9_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_9_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_9_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_9_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_10_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_10_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_10_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_10_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_11_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_11_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_11_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_11_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_12_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_12_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_12_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_12_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_14_source: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_14_argument: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_14_returned: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_14_caller: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_15_source: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_15_argument: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_15_returned: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_15_caller: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    #[cfg(test)]
    mir_unit_7_16_source: isize,
    #[cfg(test)]
    mir_unit_7_16_argument: isize,
    #[cfg(test)]
    mir_unit_7_16_returned: isize,
    #[cfg(test)]
    mir_unit_7_16_caller: isize,
    #[cfg(test)]
    mir_unit_7_17_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_17_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_17_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_17_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_18_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_18_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_18_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_18_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_19_source: isize,
    #[cfg(test)]
    mir_unit_7_19_argument: isize,
    #[cfg(test)]
    mir_unit_7_19_returned: isize,
    #[cfg(test)]
    mir_unit_7_19_caller: isize,
    #[cfg(test)]
    mir_unit_7_21_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_21_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_21_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_21_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_22_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_22_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_22_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_22_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_23_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_23_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_23_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_23_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_24_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_24_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_24_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_24_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_25_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_25_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_25_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_25_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_26_source: isize,
    #[cfg(test)]
    mir_unit_7_26_argument: isize,
    #[cfg(test)]
    mir_unit_7_26_returned: isize,
    #[cfg(test)]
    mir_unit_7_26_caller: isize,
    #[cfg(test)]
    mir_unit_7_28_source: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_28_argument: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_28_returned: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_28_caller: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    #[cfg(test)]
    mir_unit_7_29_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_29_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_29_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_29_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_30_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_30_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_30_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_30_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_31_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_31_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_31_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_31_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_32_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_32_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_32_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_32_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_33_source: isize,
    #[cfg(test)]
    mir_unit_7_33_argument: isize,
    #[cfg(test)]
    mir_unit_7_33_returned: isize,
    #[cfg(test)]
    mir_unit_7_33_caller: isize,
    #[cfg(test)]
    mir_unit_7_35_source: (),
    #[cfg(test)]
    mir_unit_7_35_argument: (),
    #[cfg(test)]
    mir_unit_7_35_returned: (),
    #[cfg(test)]
    mir_unit_7_35_caller: (),
    #[cfg(test)]
    mir_unit_7_36_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_36_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_36_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_36_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_38_source: &'static mut crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_38_argument: &'static mut crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_38_returned: &'static mut crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_38_caller: &'static mut crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_39_source: (),
    #[cfg(test)]
    mir_unit_7_39_argument: (),
    #[cfg(test)]
    mir_unit_7_39_returned: (),
    #[cfg(test)]
    mir_unit_7_39_caller: (),
    #[cfg(test)]
    mir_unit_7_40_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_40_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_40_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_40_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_42_source: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_42_argument: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_42_returned: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_42_caller: &'static crate::experimental_wasi::WasiContext,
    #[cfg(test)]
    mir_unit_7_44_source: isize,
    #[cfg(test)]
    mir_unit_7_44_argument: isize,
    #[cfg(test)]
    mir_unit_7_44_returned: isize,
    #[cfg(test)]
    mir_unit_7_44_caller: isize,
    #[cfg(test)]
    mir_unit_7_47_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_47_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_47_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_47_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_48_source: std::option::Option<crate::experimental_wasi::WasiFailure>,
    #[cfg(test)]
    mir_unit_7_48_argument: std::option::Option<crate::experimental_wasi::WasiFailure>,
    #[cfg(test)]
    mir_unit_7_48_returned: std::option::Option<crate::experimental_wasi::WasiFailure>,
    #[cfg(test)]
    mir_unit_7_48_caller: std::option::Option<crate::experimental_wasi::WasiFailure>,
    #[cfg(test)]
    mir_unit_7_49_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_49_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_49_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_49_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_50_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_50_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_50_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_50_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_51_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_51_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_51_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_51_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_54_source: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_54_argument: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_54_returned: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_54_caller: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    #[cfg(test)]
    mir_unit_7_55_source: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_7_55_argument: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_7_55_returned: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_7_55_caller: std::option::Option<u32>,
    #[cfg(test)]
    mir_unit_7_56_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_56_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_56_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_56_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_57_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_57_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_57_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_57_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_58_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_58_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_58_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_58_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_61_source: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_61_argument: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_61_returned: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_61_caller: std::option::Option<crate::experimental_wasi::WasiUsage>,
    #[cfg(test)]
    mir_unit_7_62_source: isize,
    #[cfg(test)]
    mir_unit_7_62_argument: isize,
    #[cfg(test)]
    mir_unit_7_62_returned: isize,
    #[cfg(test)]
    mir_unit_7_62_caller: isize,
    #[cfg(test)]
    mir_unit_7_65_source: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_7_65_argument: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_7_65_returned: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_7_65_caller: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_7_66_source: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_66_argument: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_66_returned: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_66_caller: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_13_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_7_13_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_7_13_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_7_13_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_7_13_0_ticket_source: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_7_13_0_ticket_argument: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_7_13_0_ticket_returned: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    alias_unit_7_13_0_ticket_caller: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    #[cfg(test)]
    mir_unit_7_20_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_20_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_20_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_20_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_20_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_20_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_20_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_20_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_27_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_27_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_27_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_27_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_27_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_27_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_27_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_27_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_34_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_34_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_34_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_34_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_34_0_residual_source: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_34_0_residual_argument: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_34_0_residual_returned: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_34_0_residual_caller: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_37_source: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    mir_unit_7_37_argument: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    mir_unit_7_37_returned: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    mir_unit_7_37_caller: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    alias_unit_7_37_0_outcome_source: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    alias_unit_7_37_0_outcome_argument: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    alias_unit_7_37_0_outcome_returned: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    alias_unit_7_37_0_outcome_caller: crate::experimental_wasi::WasiOutcome,
    #[cfg(test)]
    mir_unit_7_41_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_41_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_41_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_41_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_7_41_0_usage_source: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_7_41_0_usage_argument: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_7_41_0_usage_returned: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    alias_unit_7_41_0_usage_caller: crate::experimental_wasi::WasiUsage,
    #[cfg(test)]
    mir_unit_7_43_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_43_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_43_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_43_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_43_0_result_source: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_43_0_result_argument: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_43_0_result_returned: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_43_0_result_caller: std::result::Result<crate::experimental_wasi::Errno, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_45_source: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    mir_unit_7_45_argument: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    mir_unit_7_45_returned: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    mir_unit_7_45_caller: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    alias_unit_7_45_0_error_source: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    alias_unit_7_45_0_error_argument: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    alias_unit_7_45_0_error_returned: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    alias_unit_7_45_0_error_caller: crate::experimental_wasi::WasiFailure,
    #[cfg(test)]
    mir_unit_7_52_source: u32,
    #[cfg(test)]
    mir_unit_7_52_argument: u32,
    #[cfg(test)]
    mir_unit_7_52_returned: u32,
    #[cfg(test)]
    mir_unit_7_52_caller: u32,
    #[cfg(test)]
    alias_unit_7_52_0_code_source: u32,
    #[cfg(test)]
    alias_unit_7_52_0_code_argument: u32,
    #[cfg(test)]
    alias_unit_7_52_0_code_returned: u32,
    #[cfg(test)]
    alias_unit_7_52_0_code_caller: u32,
    #[cfg(test)]
    mir_unit_7_59_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_59_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_59_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_59_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_59_0_errno_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_59_0_errno_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_59_0_errno_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_59_0_errno_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_60_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_60_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_60_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_60_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_60_0_after_source: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_60_0_after_argument: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_60_0_after_returned: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    alias_unit_7_60_0_after_caller: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    #[cfg(test)]
    mir_unit_7_63_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_63_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_63_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_63_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_7_63_0_failure_source: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_7_63_0_failure_argument: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_7_63_0_failure_returned: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    alias_unit_7_63_0_failure_caller: crate::experimental_swift_reactor::control::SwiftRunFailure,
    #[cfg(test)]
    mir_unit_7_64_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_64_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_64_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_64_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_64_0_errno_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_64_0_errno_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_64_0_errno_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    alias_unit_7_64_0_errno_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_7_46_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_46_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_46_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_46_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_46_0_fault_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_46_0_fault_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_46_0_fault_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_46_0_fault_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_53_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_53_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_53_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_53_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_53_0_fault_source: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_53_0_fault_argument: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_53_0_fault_returned: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    alias_unit_7_53_0_fault_caller: crate::experimental_swift_reactor::control::Fault,
    #[cfg(test)]
    mir_unit_7_1_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_1_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_1_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_1_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_7_1_0_self_source: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_7_1_0_self_argument: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_7_1_0_self_returned: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_7_1_0_self_caller: &'static mut crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_7_2_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_7_2_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_7_2_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_7_2_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_7_2_0_control_source: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_7_2_0_control_argument: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_7_2_0_control_returned: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    alias_unit_7_2_0_control_caller: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    #[cfg(test)]
    mir_unit_7_3_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_7_3_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_7_3_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_7_3_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_7_3_0_function_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_7_3_0_function_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_7_3_0_function_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_7_3_0_function_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_7_4_source: &'static [Value],
    #[cfg(test)]
    mir_unit_7_4_argument: &'static [Value],
    #[cfg(test)]
    mir_unit_7_4_returned: &'static [Value],
    #[cfg(test)]
    mir_unit_7_4_caller: &'static [Value],
    #[cfg(test)]
    alias_unit_7_4_0_arguments_source: &'static [Value],
    #[cfg(test)]
    alias_unit_7_4_0_arguments_argument: &'static [Value],
    #[cfg(test)]
    alias_unit_7_4_0_arguments_returned: &'static [Value],
    #[cfg(test)]
    alias_unit_7_4_0_arguments_caller: &'static [Value],
    #[cfg(test)]
    mir_unit_7_5_source: &'static mut [u8],
    #[cfg(test)]
    mir_unit_7_5_argument: &'static mut [u8],
    #[cfg(test)]
    mir_unit_7_5_returned: &'static mut [u8],
    #[cfg(test)]
    mir_unit_7_5_caller: &'static mut [u8],
    #[cfg(test)]
    alias_unit_7_5_0_memory_source: &'static mut [u8],
    #[cfg(test)]
    alias_unit_7_5_0_memory_argument: &'static mut [u8],
    #[cfg(test)]
    alias_unit_7_5_0_memory_returned: &'static mut [u8],
    #[cfg(test)]
    alias_unit_7_5_0_memory_caller: &'static mut [u8],
    #[cfg(test)]
    mir_unit_7_6_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_7_6_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_7_6_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    mir_unit_7_6_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_7_6_0_cursor_source: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_7_6_0_cursor_argument: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_7_6_0_cursor_returned: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    alias_unit_7_6_0_cursor_caller: crate::experimental_swift_reactor::control::Cursor,
    #[cfg(test)]
    literal_unit_7_0_source: &'static str,
    #[cfg(test)]
    literal_unit_7_0_argument: &'static str,
    #[cfg(test)]
    literal_unit_7_0_returned: &'static str,
    #[cfg(test)]
    literal_unit_7_0_caller: &'static str,
    #[cfg(test)]
    literal_unit_7_1_source: bool,
    #[cfg(test)]
    literal_unit_7_1_argument: bool,
    #[cfg(test)]
    literal_unit_7_1_returned: bool,
    #[cfg(test)]
    literal_unit_7_1_caller: bool,
    #[cfg(test)]
    literal_unit_7_2_source: bool,
    #[cfg(test)]
    literal_unit_7_2_argument: bool,
    #[cfg(test)]
    literal_unit_7_2_returned: bool,
    #[cfg(test)]
    literal_unit_7_2_caller: bool,
    #[cfg(test)]
    literal_unit_7_3_source: &'static str,
    #[cfg(test)]
    literal_unit_7_3_argument: &'static str,
    #[cfg(test)]
    literal_unit_7_3_returned: &'static str,
    #[cfg(test)]
    literal_unit_7_3_caller: &'static str,
    #[cfg(test)]
    literal_unit_7_4_source: &'static str,
    #[cfg(test)]
    literal_unit_7_4_argument: &'static str,
    #[cfg(test)]
    literal_unit_7_4_returned: &'static str,
    #[cfg(test)]
    literal_unit_7_4_caller: &'static str,
    #[cfg(test)]
    mir_unit_8_0_source: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_0_argument: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_0_returned: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_0_caller: crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_3_source: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_3_argument: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_3_returned: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_3_caller: &'static crate::experimental_wasi::Errno,
    #[cfg(test)]
    mir_unit_8_1_source: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_8_1_argument: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_8_1_returned: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_8_1_caller: (&'static crate::experimental_wasi::Errno,),
    #[cfg(test)]
    mir_unit_8_2_source: (),
    #[cfg(test)]
    mir_unit_8_2_argument: (),
    #[cfg(test)]
    mir_unit_8_2_returned: (),
    #[cfg(test)]
    mir_unit_8_2_caller: (),
    #[cfg(test)]
    mir_unit_9_0_source: (),
    #[cfg(test)]
    mir_unit_9_0_argument: (),
    #[cfg(test)]
    mir_unit_9_0_returned: (),
    #[cfg(test)]
    mir_unit_9_0_caller: (),
    #[cfg(test)]
    mir_unit_9_3_source: bool,
    #[cfg(test)]
    mir_unit_9_3_argument: bool,
    #[cfg(test)]
    mir_unit_9_3_returned: bool,
    #[cfg(test)]
    mir_unit_9_3_caller: bool,
    #[cfg(test)]
    mir_unit_9_4_source: bool,
    #[cfg(test)]
    mir_unit_9_4_argument: bool,
    #[cfg(test)]
    mir_unit_9_4_returned: bool,
    #[cfg(test)]
    mir_unit_9_4_caller: bool,
    #[cfg(test)]
    mir_unit_9_5_source: (),
    #[cfg(test)]
    mir_unit_9_5_argument: (),
    #[cfg(test)]
    mir_unit_9_5_returned: (),
    #[cfg(test)]
    mir_unit_9_5_caller: (),
    #[cfg(test)]
    mir_unit_9_6_source: &'static crate::Cancellation,
    #[cfg(test)]
    mir_unit_9_6_argument: &'static crate::Cancellation,
    #[cfg(test)]
    mir_unit_9_6_returned: &'static crate::Cancellation,
    #[cfg(test)]
    mir_unit_9_6_caller: &'static crate::Cancellation,
    #[cfg(test)]
    mir_unit_9_7_source: bool,
    #[cfg(test)]
    mir_unit_9_7_argument: bool,
    #[cfg(test)]
    mir_unit_9_7_returned: bool,
    #[cfg(test)]
    mir_unit_9_7_caller: bool,
    #[cfg(test)]
    mir_unit_9_8_source: (),
    #[cfg(test)]
    mir_unit_9_8_argument: (),
    #[cfg(test)]
    mir_unit_9_8_returned: (),
    #[cfg(test)]
    mir_unit_9_8_caller: (),
    #[cfg(test)]
    mir_unit_9_9_source: std::time::Duration,
    #[cfg(test)]
    mir_unit_9_9_argument: std::time::Duration,
    #[cfg(test)]
    mir_unit_9_9_returned: std::time::Duration,
    #[cfg(test)]
    mir_unit_9_9_caller: std::time::Duration,
    #[cfg(test)]
    mir_unit_9_1_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_9_1_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_9_1_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_9_1_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_9_1_0_self_source: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_9_1_0_self_argument: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_9_1_0_self_returned: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    alias_unit_9_1_0_self_caller: &'static crate::experimental_wasi::accounted::AccountedWasi,
    #[cfg(test)]
    mir_unit_9_2_source: bool,
    #[cfg(test)]
    mir_unit_9_2_argument: bool,
    #[cfg(test)]
    mir_unit_9_2_returned: bool,
    #[cfg(test)]
    mir_unit_9_2_caller: bool,
    #[cfg(test)]
    alias_unit_9_2_0_after_source: bool,
    #[cfg(test)]
    alias_unit_9_2_0_after_argument: bool,
    #[cfg(test)]
    alias_unit_9_2_0_after_returned: bool,
    #[cfg(test)]
    alias_unit_9_2_0_after_caller: bool,
    #[cfg(test)]
    literal_unit_9_0_source: u64,
    #[cfg(test)]
    literal_unit_9_0_argument: u64,
    #[cfg(test)]
    literal_unit_9_0_returned: u64,
    #[cfg(test)]
    literal_unit_9_0_caller: u64,
    #[cfg(test)]
    mir_unit_10_0_source: &'static [Type],
    #[cfg(test)]
    mir_unit_10_0_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_10_0_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_10_0_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_10_2_source: &'static [Type],
    #[cfg(test)]
    mir_unit_10_2_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_10_2_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_10_2_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_10_3_source: isize,
    #[cfg(test)]
    mir_unit_10_3_argument: isize,
    #[cfg(test)]
    mir_unit_10_3_returned: isize,
    #[cfg(test)]
    mir_unit_10_3_caller: isize,
    #[cfg(test)]
    mir_unit_10_4_source: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_10_4_argument: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_10_4_returned: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_10_4_caller: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_10_5_source: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_5_argument: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_5_returned: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_5_caller: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_6_source: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_6_argument: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_6_returned: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_6_caller: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_7_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_7_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_7_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_7_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_8_source: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_8_argument: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_8_returned: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_8_caller: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_9_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_9_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_9_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_9_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_10_source: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_10_argument: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_10_returned: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_10_caller: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_10_11_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_11_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_11_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_11_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_10_12_source: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_12_argument: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_12_returned: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_12_caller: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_10_13_source: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_13_argument: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_13_returned: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_13_caller: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_14_source: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_14_argument: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_14_returned: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_14_caller: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_10_15_source: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_10_15_argument: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_10_15_returned: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_10_15_caller: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_10_16_source: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_10_16_argument: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_10_16_returned: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_10_16_caller: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_10_17_source: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_17_argument: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_17_returned: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_17_caller: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_10_1_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_10_1_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_10_1_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_10_1_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_10_1_0_self_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_10_1_0_self_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_10_1_0_self_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_10_1_0_self_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_0_source: &'static [Type],
    #[cfg(test)]
    mir_unit_11_0_argument: &'static [Type],
    #[cfg(test)]
    mir_unit_11_0_returned: &'static [Type],
    #[cfg(test)]
    mir_unit_11_0_caller: &'static [Type],
    #[cfg(test)]
    mir_unit_11_2_source: bool,
    #[cfg(test)]
    mir_unit_11_2_argument: bool,
    #[cfg(test)]
    mir_unit_11_2_returned: bool,
    #[cfg(test)]
    mir_unit_11_2_caller: bool,
    #[cfg(test)]
    mir_unit_11_3_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_3_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_3_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_3_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_4_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_4_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_4_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_4_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_5_source: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_11_5_argument: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_11_5_returned: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_11_5_caller: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_11_6_source: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_11_6_argument: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_11_6_returned: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_11_6_caller: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_11_1_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_1_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_1_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_11_1_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_11_1_0_self_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_11_1_0_self_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_11_1_0_self_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    alias_unit_11_1_0_self_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_0_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_0_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_0_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_0_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_1_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_1_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_1_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_12_1_caller: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_13_0_source: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_13_0_argument: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_13_0_returned: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_13_0_caller: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_13_1_source: [Type; 2],
    #[cfg(test)]
    mir_unit_13_1_argument: [Type; 2],
    #[cfg(test)]
    mir_unit_13_1_returned: [Type; 2],
    #[cfg(test)]
    mir_unit_13_1_caller: [Type; 2],
    #[cfg(test)]
    mir_unit_13_2_source: Type,
    #[cfg(test)]
    mir_unit_13_2_argument: Type,
    #[cfg(test)]
    mir_unit_13_2_returned: Type,
    #[cfg(test)]
    mir_unit_13_2_caller: Type,
    #[cfg(test)]
    mir_unit_13_3_source: Type,
    #[cfg(test)]
    mir_unit_13_3_argument: Type,
    #[cfg(test)]
    mir_unit_13_3_returned: Type,
    #[cfg(test)]
    mir_unit_13_3_caller: Type,
    #[cfg(test)]
    mir_unit_14_0_source: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_14_0_argument: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_14_0_returned: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_14_0_caller: &'static [Type; 6],
    #[cfg(test)]
    mir_unit_14_1_source: [Type; 6],
    #[cfg(test)]
    mir_unit_14_1_argument: [Type; 6],
    #[cfg(test)]
    mir_unit_14_1_returned: [Type; 6],
    #[cfg(test)]
    mir_unit_14_1_caller: [Type; 6],
    #[cfg(test)]
    mir_unit_14_2_source: Type,
    #[cfg(test)]
    mir_unit_14_2_argument: Type,
    #[cfg(test)]
    mir_unit_14_2_returned: Type,
    #[cfg(test)]
    mir_unit_14_2_caller: Type,
    #[cfg(test)]
    mir_unit_14_3_source: Type,
    #[cfg(test)]
    mir_unit_14_3_argument: Type,
    #[cfg(test)]
    mir_unit_14_3_returned: Type,
    #[cfg(test)]
    mir_unit_14_3_caller: Type,
    #[cfg(test)]
    mir_unit_14_4_source: Type,
    #[cfg(test)]
    mir_unit_14_4_argument: Type,
    #[cfg(test)]
    mir_unit_14_4_returned: Type,
    #[cfg(test)]
    mir_unit_14_4_caller: Type,
    #[cfg(test)]
    mir_unit_14_5_source: Type,
    #[cfg(test)]
    mir_unit_14_5_argument: Type,
    #[cfg(test)]
    mir_unit_14_5_returned: Type,
    #[cfg(test)]
    mir_unit_14_5_caller: Type,
    #[cfg(test)]
    mir_unit_14_6_source: Type,
    #[cfg(test)]
    mir_unit_14_6_argument: Type,
    #[cfg(test)]
    mir_unit_14_6_returned: Type,
    #[cfg(test)]
    mir_unit_14_6_caller: Type,
    #[cfg(test)]
    mir_unit_14_7_source: Type,
    #[cfg(test)]
    mir_unit_14_7_argument: Type,
    #[cfg(test)]
    mir_unit_14_7_returned: Type,
    #[cfg(test)]
    mir_unit_14_7_caller: Type,
    #[cfg(test)]
    mir_unit_15_0_source: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_15_0_argument: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_15_0_returned: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_15_0_caller: &'static [Type; 9],
    #[cfg(test)]
    mir_unit_15_1_source: [Type; 9],
    #[cfg(test)]
    mir_unit_15_1_argument: [Type; 9],
    #[cfg(test)]
    mir_unit_15_1_returned: [Type; 9],
    #[cfg(test)]
    mir_unit_15_1_caller: [Type; 9],
    #[cfg(test)]
    mir_unit_15_2_source: Type,
    #[cfg(test)]
    mir_unit_15_2_argument: Type,
    #[cfg(test)]
    mir_unit_15_2_returned: Type,
    #[cfg(test)]
    mir_unit_15_2_caller: Type,
    #[cfg(test)]
    mir_unit_15_3_source: Type,
    #[cfg(test)]
    mir_unit_15_3_argument: Type,
    #[cfg(test)]
    mir_unit_15_3_returned: Type,
    #[cfg(test)]
    mir_unit_15_3_caller: Type,
    #[cfg(test)]
    mir_unit_15_4_source: Type,
    #[cfg(test)]
    mir_unit_15_4_argument: Type,
    #[cfg(test)]
    mir_unit_15_4_returned: Type,
    #[cfg(test)]
    mir_unit_15_4_caller: Type,
    #[cfg(test)]
    mir_unit_15_5_source: Type,
    #[cfg(test)]
    mir_unit_15_5_argument: Type,
    #[cfg(test)]
    mir_unit_15_5_returned: Type,
    #[cfg(test)]
    mir_unit_15_5_caller: Type,
    #[cfg(test)]
    mir_unit_15_6_source: Type,
    #[cfg(test)]
    mir_unit_15_6_argument: Type,
    #[cfg(test)]
    mir_unit_15_6_returned: Type,
    #[cfg(test)]
    mir_unit_15_6_caller: Type,
    #[cfg(test)]
    mir_unit_15_7_source: Type,
    #[cfg(test)]
    mir_unit_15_7_argument: Type,
    #[cfg(test)]
    mir_unit_15_7_returned: Type,
    #[cfg(test)]
    mir_unit_15_7_caller: Type,
    #[cfg(test)]
    mir_unit_15_8_source: Type,
    #[cfg(test)]
    mir_unit_15_8_argument: Type,
    #[cfg(test)]
    mir_unit_15_8_returned: Type,
    #[cfg(test)]
    mir_unit_15_8_caller: Type,
    #[cfg(test)]
    mir_unit_15_9_source: Type,
    #[cfg(test)]
    mir_unit_15_9_argument: Type,
    #[cfg(test)]
    mir_unit_15_9_returned: Type,
    #[cfg(test)]
    mir_unit_15_9_caller: Type,
    #[cfg(test)]
    mir_unit_15_10_source: Type,
    #[cfg(test)]
    mir_unit_15_10_argument: Type,
    #[cfg(test)]
    mir_unit_15_10_returned: Type,
    #[cfg(test)]
    mir_unit_15_10_caller: Type,
    #[cfg(test)]
    mir_unit_16_0_source: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_16_0_argument: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_16_0_returned: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_16_0_caller: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_16_1_source: [Type; 7],
    #[cfg(test)]
    mir_unit_16_1_argument: [Type; 7],
    #[cfg(test)]
    mir_unit_16_1_returned: [Type; 7],
    #[cfg(test)]
    mir_unit_16_1_caller: [Type; 7],
    #[cfg(test)]
    mir_unit_16_2_source: Type,
    #[cfg(test)]
    mir_unit_16_2_argument: Type,
    #[cfg(test)]
    mir_unit_16_2_returned: Type,
    #[cfg(test)]
    mir_unit_16_2_caller: Type,
    #[cfg(test)]
    mir_unit_16_3_source: Type,
    #[cfg(test)]
    mir_unit_16_3_argument: Type,
    #[cfg(test)]
    mir_unit_16_3_returned: Type,
    #[cfg(test)]
    mir_unit_16_3_caller: Type,
    #[cfg(test)]
    mir_unit_16_4_source: Type,
    #[cfg(test)]
    mir_unit_16_4_argument: Type,
    #[cfg(test)]
    mir_unit_16_4_returned: Type,
    #[cfg(test)]
    mir_unit_16_4_caller: Type,
    #[cfg(test)]
    mir_unit_16_5_source: Type,
    #[cfg(test)]
    mir_unit_16_5_argument: Type,
    #[cfg(test)]
    mir_unit_16_5_returned: Type,
    #[cfg(test)]
    mir_unit_16_5_caller: Type,
    #[cfg(test)]
    mir_unit_16_6_source: Type,
    #[cfg(test)]
    mir_unit_16_6_argument: Type,
    #[cfg(test)]
    mir_unit_16_6_returned: Type,
    #[cfg(test)]
    mir_unit_16_6_caller: Type,
    #[cfg(test)]
    mir_unit_16_7_source: Type,
    #[cfg(test)]
    mir_unit_16_7_argument: Type,
    #[cfg(test)]
    mir_unit_16_7_returned: Type,
    #[cfg(test)]
    mir_unit_16_7_caller: Type,
    #[cfg(test)]
    mir_unit_16_8_source: Type,
    #[cfg(test)]
    mir_unit_16_8_argument: Type,
    #[cfg(test)]
    mir_unit_16_8_returned: Type,
    #[cfg(test)]
    mir_unit_16_8_caller: Type,
    #[cfg(test)]
    mir_unit_17_0_source: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_17_0_argument: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_17_0_returned: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_17_0_caller: &'static [Type; 7],
    #[cfg(test)]
    mir_unit_17_1_source: [Type; 7],
    #[cfg(test)]
    mir_unit_17_1_argument: [Type; 7],
    #[cfg(test)]
    mir_unit_17_1_returned: [Type; 7],
    #[cfg(test)]
    mir_unit_17_1_caller: [Type; 7],
    #[cfg(test)]
    mir_unit_17_2_source: Type,
    #[cfg(test)]
    mir_unit_17_2_argument: Type,
    #[cfg(test)]
    mir_unit_17_2_returned: Type,
    #[cfg(test)]
    mir_unit_17_2_caller: Type,
    #[cfg(test)]
    mir_unit_17_3_source: Type,
    #[cfg(test)]
    mir_unit_17_3_argument: Type,
    #[cfg(test)]
    mir_unit_17_3_returned: Type,
    #[cfg(test)]
    mir_unit_17_3_caller: Type,
    #[cfg(test)]
    mir_unit_17_4_source: Type,
    #[cfg(test)]
    mir_unit_17_4_argument: Type,
    #[cfg(test)]
    mir_unit_17_4_returned: Type,
    #[cfg(test)]
    mir_unit_17_4_caller: Type,
    #[cfg(test)]
    mir_unit_17_5_source: Type,
    #[cfg(test)]
    mir_unit_17_5_argument: Type,
    #[cfg(test)]
    mir_unit_17_5_returned: Type,
    #[cfg(test)]
    mir_unit_17_5_caller: Type,
    #[cfg(test)]
    mir_unit_17_6_source: Type,
    #[cfg(test)]
    mir_unit_17_6_argument: Type,
    #[cfg(test)]
    mir_unit_17_6_returned: Type,
    #[cfg(test)]
    mir_unit_17_6_caller: Type,
    #[cfg(test)]
    mir_unit_17_7_source: Type,
    #[cfg(test)]
    mir_unit_17_7_argument: Type,
    #[cfg(test)]
    mir_unit_17_7_returned: Type,
    #[cfg(test)]
    mir_unit_17_7_caller: Type,
    #[cfg(test)]
    mir_unit_17_8_source: Type,
    #[cfg(test)]
    mir_unit_17_8_argument: Type,
    #[cfg(test)]
    mir_unit_17_8_returned: Type,
    #[cfg(test)]
    mir_unit_17_8_caller: Type,
    #[cfg(test)]
    mir_unit_18_0_source: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_18_0_argument: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_18_0_returned: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_18_0_caller: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_18_1_source: [Type; 5],
    #[cfg(test)]
    mir_unit_18_1_argument: [Type; 5],
    #[cfg(test)]
    mir_unit_18_1_returned: [Type; 5],
    #[cfg(test)]
    mir_unit_18_1_caller: [Type; 5],
    #[cfg(test)]
    mir_unit_18_2_source: Type,
    #[cfg(test)]
    mir_unit_18_2_argument: Type,
    #[cfg(test)]
    mir_unit_18_2_returned: Type,
    #[cfg(test)]
    mir_unit_18_2_caller: Type,
    #[cfg(test)]
    mir_unit_18_3_source: Type,
    #[cfg(test)]
    mir_unit_18_3_argument: Type,
    #[cfg(test)]
    mir_unit_18_3_returned: Type,
    #[cfg(test)]
    mir_unit_18_3_caller: Type,
    #[cfg(test)]
    mir_unit_18_4_source: Type,
    #[cfg(test)]
    mir_unit_18_4_argument: Type,
    #[cfg(test)]
    mir_unit_18_4_returned: Type,
    #[cfg(test)]
    mir_unit_18_4_caller: Type,
    #[cfg(test)]
    mir_unit_18_5_source: Type,
    #[cfg(test)]
    mir_unit_18_5_argument: Type,
    #[cfg(test)]
    mir_unit_18_5_returned: Type,
    #[cfg(test)]
    mir_unit_18_5_caller: Type,
    #[cfg(test)]
    mir_unit_18_6_source: Type,
    #[cfg(test)]
    mir_unit_18_6_argument: Type,
    #[cfg(test)]
    mir_unit_18_6_returned: Type,
    #[cfg(test)]
    mir_unit_18_6_caller: Type,
    #[cfg(test)]
    mir_unit_19_0_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_19_0_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_19_0_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_19_0_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_19_1_source: [Type; 4],
    #[cfg(test)]
    mir_unit_19_1_argument: [Type; 4],
    #[cfg(test)]
    mir_unit_19_1_returned: [Type; 4],
    #[cfg(test)]
    mir_unit_19_1_caller: [Type; 4],
    #[cfg(test)]
    mir_unit_19_2_source: Type,
    #[cfg(test)]
    mir_unit_19_2_argument: Type,
    #[cfg(test)]
    mir_unit_19_2_returned: Type,
    #[cfg(test)]
    mir_unit_19_2_caller: Type,
    #[cfg(test)]
    mir_unit_19_3_source: Type,
    #[cfg(test)]
    mir_unit_19_3_argument: Type,
    #[cfg(test)]
    mir_unit_19_3_returned: Type,
    #[cfg(test)]
    mir_unit_19_3_caller: Type,
    #[cfg(test)]
    mir_unit_19_4_source: Type,
    #[cfg(test)]
    mir_unit_19_4_argument: Type,
    #[cfg(test)]
    mir_unit_19_4_returned: Type,
    #[cfg(test)]
    mir_unit_19_4_caller: Type,
    #[cfg(test)]
    mir_unit_19_5_source: Type,
    #[cfg(test)]
    mir_unit_19_5_argument: Type,
    #[cfg(test)]
    mir_unit_19_5_returned: Type,
    #[cfg(test)]
    mir_unit_19_5_caller: Type,
    #[cfg(test)]
    mir_unit_20_0_source: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_20_0_argument: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_20_0_returned: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_20_0_caller: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_20_1_source: [Type; 3],
    #[cfg(test)]
    mir_unit_20_1_argument: [Type; 3],
    #[cfg(test)]
    mir_unit_20_1_returned: [Type; 3],
    #[cfg(test)]
    mir_unit_20_1_caller: [Type; 3],
    #[cfg(test)]
    mir_unit_20_2_source: Type,
    #[cfg(test)]
    mir_unit_20_2_argument: Type,
    #[cfg(test)]
    mir_unit_20_2_returned: Type,
    #[cfg(test)]
    mir_unit_20_2_caller: Type,
    #[cfg(test)]
    mir_unit_20_3_source: Type,
    #[cfg(test)]
    mir_unit_20_3_argument: Type,
    #[cfg(test)]
    mir_unit_20_3_returned: Type,
    #[cfg(test)]
    mir_unit_20_3_caller: Type,
    #[cfg(test)]
    mir_unit_20_4_source: Type,
    #[cfg(test)]
    mir_unit_20_4_argument: Type,
    #[cfg(test)]
    mir_unit_20_4_returned: Type,
    #[cfg(test)]
    mir_unit_20_4_caller: Type,
    #[cfg(test)]
    mir_unit_21_0_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_21_0_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_21_0_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_21_0_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_21_1_source: [Type; 4],
    #[cfg(test)]
    mir_unit_21_1_argument: [Type; 4],
    #[cfg(test)]
    mir_unit_21_1_returned: [Type; 4],
    #[cfg(test)]
    mir_unit_21_1_caller: [Type; 4],
    #[cfg(test)]
    mir_unit_21_2_source: Type,
    #[cfg(test)]
    mir_unit_21_2_argument: Type,
    #[cfg(test)]
    mir_unit_21_2_returned: Type,
    #[cfg(test)]
    mir_unit_21_2_caller: Type,
    #[cfg(test)]
    mir_unit_21_3_source: Type,
    #[cfg(test)]
    mir_unit_21_3_argument: Type,
    #[cfg(test)]
    mir_unit_21_3_returned: Type,
    #[cfg(test)]
    mir_unit_21_3_caller: Type,
    #[cfg(test)]
    mir_unit_21_4_source: Type,
    #[cfg(test)]
    mir_unit_21_4_argument: Type,
    #[cfg(test)]
    mir_unit_21_4_returned: Type,
    #[cfg(test)]
    mir_unit_21_4_caller: Type,
    #[cfg(test)]
    mir_unit_21_5_source: Type,
    #[cfg(test)]
    mir_unit_21_5_argument: Type,
    #[cfg(test)]
    mir_unit_21_5_returned: Type,
    #[cfg(test)]
    mir_unit_21_5_caller: Type,
    #[cfg(test)]
    mir_unit_22_0_source: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_22_0_argument: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_22_0_returned: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_22_0_caller: &'static [Type; 5],
    #[cfg(test)]
    mir_unit_22_1_source: [Type; 5],
    #[cfg(test)]
    mir_unit_22_1_argument: [Type; 5],
    #[cfg(test)]
    mir_unit_22_1_returned: [Type; 5],
    #[cfg(test)]
    mir_unit_22_1_caller: [Type; 5],
    #[cfg(test)]
    mir_unit_22_2_source: Type,
    #[cfg(test)]
    mir_unit_22_2_argument: Type,
    #[cfg(test)]
    mir_unit_22_2_returned: Type,
    #[cfg(test)]
    mir_unit_22_2_caller: Type,
    #[cfg(test)]
    mir_unit_22_3_source: Type,
    #[cfg(test)]
    mir_unit_22_3_argument: Type,
    #[cfg(test)]
    mir_unit_22_3_returned: Type,
    #[cfg(test)]
    mir_unit_22_3_caller: Type,
    #[cfg(test)]
    mir_unit_22_4_source: Type,
    #[cfg(test)]
    mir_unit_22_4_argument: Type,
    #[cfg(test)]
    mir_unit_22_4_returned: Type,
    #[cfg(test)]
    mir_unit_22_4_caller: Type,
    #[cfg(test)]
    mir_unit_22_5_source: Type,
    #[cfg(test)]
    mir_unit_22_5_argument: Type,
    #[cfg(test)]
    mir_unit_22_5_returned: Type,
    #[cfg(test)]
    mir_unit_22_5_caller: Type,
    #[cfg(test)]
    mir_unit_22_6_source: Type,
    #[cfg(test)]
    mir_unit_22_6_argument: Type,
    #[cfg(test)]
    mir_unit_22_6_returned: Type,
    #[cfg(test)]
    mir_unit_22_6_caller: Type,
    #[cfg(test)]
    mir_unit_23_0_source: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_23_0_argument: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_23_0_returned: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_23_0_caller: &'static [Type; 4],
    #[cfg(test)]
    mir_unit_23_1_source: [Type; 4],
    #[cfg(test)]
    mir_unit_23_1_argument: [Type; 4],
    #[cfg(test)]
    mir_unit_23_1_returned: [Type; 4],
    #[cfg(test)]
    mir_unit_23_1_caller: [Type; 4],
    #[cfg(test)]
    mir_unit_23_2_source: Type,
    #[cfg(test)]
    mir_unit_23_2_argument: Type,
    #[cfg(test)]
    mir_unit_23_2_returned: Type,
    #[cfg(test)]
    mir_unit_23_2_caller: Type,
    #[cfg(test)]
    mir_unit_23_3_source: Type,
    #[cfg(test)]
    mir_unit_23_3_argument: Type,
    #[cfg(test)]
    mir_unit_23_3_returned: Type,
    #[cfg(test)]
    mir_unit_23_3_caller: Type,
    #[cfg(test)]
    mir_unit_23_4_source: Type,
    #[cfg(test)]
    mir_unit_23_4_argument: Type,
    #[cfg(test)]
    mir_unit_23_4_returned: Type,
    #[cfg(test)]
    mir_unit_23_4_caller: Type,
    #[cfg(test)]
    mir_unit_23_5_source: Type,
    #[cfg(test)]
    mir_unit_23_5_argument: Type,
    #[cfg(test)]
    mir_unit_23_5_returned: Type,
    #[cfg(test)]
    mir_unit_23_5_caller: Type,
    #[cfg(test)]
    mir_unit_24_0_source: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_24_0_argument: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_24_0_returned: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_24_0_caller: &'static [Type; 2],
    #[cfg(test)]
    mir_unit_24_1_source: [Type; 2],
    #[cfg(test)]
    mir_unit_24_1_argument: [Type; 2],
    #[cfg(test)]
    mir_unit_24_1_returned: [Type; 2],
    #[cfg(test)]
    mir_unit_24_1_caller: [Type; 2],
    #[cfg(test)]
    mir_unit_24_2_source: Type,
    #[cfg(test)]
    mir_unit_24_2_argument: Type,
    #[cfg(test)]
    mir_unit_24_2_returned: Type,
    #[cfg(test)]
    mir_unit_24_2_caller: Type,
    #[cfg(test)]
    mir_unit_24_3_source: Type,
    #[cfg(test)]
    mir_unit_24_3_argument: Type,
    #[cfg(test)]
    mir_unit_24_3_returned: Type,
    #[cfg(test)]
    mir_unit_24_3_caller: Type,
    #[cfg(test)]
    mir_unit_25_0_source: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_25_0_argument: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_25_0_returned: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_25_0_caller: &'static [Type; 3],
    #[cfg(test)]
    mir_unit_25_1_source: [Type; 3],
    #[cfg(test)]
    mir_unit_25_1_argument: [Type; 3],
    #[cfg(test)]
    mir_unit_25_1_returned: [Type; 3],
    #[cfg(test)]
    mir_unit_25_1_caller: [Type; 3],
    #[cfg(test)]
    mir_unit_25_2_source: Type,
    #[cfg(test)]
    mir_unit_25_2_argument: Type,
    #[cfg(test)]
    mir_unit_25_2_returned: Type,
    #[cfg(test)]
    mir_unit_25_2_caller: Type,
    #[cfg(test)]
    mir_unit_25_3_source: Type,
    #[cfg(test)]
    mir_unit_25_3_argument: Type,
    #[cfg(test)]
    mir_unit_25_3_returned: Type,
    #[cfg(test)]
    mir_unit_25_3_caller: Type,
    #[cfg(test)]
    mir_unit_25_4_source: Type,
    #[cfg(test)]
    mir_unit_25_4_argument: Type,
    #[cfg(test)]
    mir_unit_25_4_returned: Type,
    #[cfg(test)]
    mir_unit_25_4_caller: Type,
    #[cfg(test)]
    mir_unit_26_0_source: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_26_0_argument: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_26_0_returned: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_26_0_caller: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_26_1_source: [Type; 1],
    #[cfg(test)]
    mir_unit_26_1_argument: [Type; 1],
    #[cfg(test)]
    mir_unit_26_1_returned: [Type; 1],
    #[cfg(test)]
    mir_unit_26_1_caller: [Type; 1],
    #[cfg(test)]
    mir_unit_26_2_source: Type,
    #[cfg(test)]
    mir_unit_26_2_argument: Type,
    #[cfg(test)]
    mir_unit_26_2_returned: Type,
    #[cfg(test)]
    mir_unit_26_2_caller: Type,
    #[cfg(test)]
    mir_unit_27_0_source: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_27_0_argument: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_27_0_returned: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_27_0_caller: &'static [Type; 0],
    #[cfg(test)]
    mir_unit_27_1_source: [Type; 0],
    #[cfg(test)]
    mir_unit_27_1_argument: [Type; 0],
    #[cfg(test)]
    mir_unit_27_1_returned: [Type; 0],
    #[cfg(test)]
    mir_unit_27_1_caller: [Type; 0],
    #[cfg(test)]
    mir_unit_28_0_source: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_28_0_argument: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_28_0_returned: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_28_0_caller: &'static [Type; 1],
    #[cfg(test)]
    mir_unit_28_1_source: [Type; 1],
    #[cfg(test)]
    mir_unit_28_1_argument: [Type; 1],
    #[cfg(test)]
    mir_unit_28_1_returned: [Type; 1],
    #[cfg(test)]
    mir_unit_28_1_caller: [Type; 1],
    #[cfg(test)]
    mir_unit_28_2_source: Type,
    #[cfg(test)]
    mir_unit_28_2_argument: Type,
    #[cfg(test)]
    mir_unit_28_2_returned: Type,
    #[cfg(test)]
    mir_unit_28_2_caller: Type,
    #[cfg(test)]
    mir_unit_29_0_source: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_0_argument: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_0_returned: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_0_caller: &'static crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_1_source: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_1_argument: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_1_returned: crate::experimental_wasi::WasiFunction,
    #[cfg(test)]
    mir_unit_29_1_caller: crate::experimental_wasi::WasiFunction,
}
