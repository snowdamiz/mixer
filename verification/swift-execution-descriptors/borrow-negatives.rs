// Appended only to a disposable candidate checkout by qualify.py.
mod descriptor_borrow_negatives {
    use super::descriptors::{FunctionSpanView, GlobalView, SegmentExecutionView, SignatureView};
    use super::policy::Policy;
    use super::swift::ValidatedSwiftReactor;
    use crate::experimental_wasi::WasiFunction;

    fn signature_escape(proof: ValidatedSwiftReactor) -> SignatureView<'static> {
        proof.execution_signature(0).unwrap()
    }
    fn type_escape(proof: ValidatedSwiftReactor) -> SignatureView<'static> {
        proof.execution_type(0).unwrap()
    }
    fn function_escape(proof: ValidatedSwiftReactor) -> FunctionSpanView<'static> {
        proof.execution_function(34).unwrap()
    }
    fn global_escape(proof: ValidatedSwiftReactor) -> GlobalView<'static> {
        proof.execution_global(0).unwrap()
    }
    fn data_escape(proof: ValidatedSwiftReactor) -> SegmentExecutionView<'static> {
        proof.execution_data(0).unwrap()
    }
    fn element_escape(proof: ValidatedSwiftReactor) -> SegmentExecutionView<'static> {
        proof.execution_element(0).unwrap()
    }
    fn imports_escape(proof: ValidatedSwiftReactor) -> &'static [WasiFunction; 34] {
        proof.execution_imports()
    }
    fn policy_escape(proof: ValidatedSwiftReactor) -> &'static Policy<'static> {
        proof.decode_policy()
    }
    fn mutate_signature(proof: &ValidatedSwiftReactor) {
        proof.execution_signature(0).unwrap().params[0] = crate::Type::I64;
    }
    fn mutate_function(proof: &ValidatedSwiftReactor) {
        proof.execution_function(34).unwrap().body[0] = 1;
    }
    fn mutate_global(proof: &ValidatedSwiftReactor) {
        proof.execution_global(0).unwrap().initializer[0] = 1;
    }
    fn mutate_data(proof: &ValidatedSwiftReactor) {
        proof.execution_data(0).unwrap().encoded_payload[0] = 1;
    }
    fn mutate_element(proof: &ValidatedSwiftReactor) {
        proof.execution_element(0).unwrap().encoded_payload[0] = 1;
    }
    fn mutate_imports(proof: &ValidatedSwiftReactor) {
        proof.execution_imports()[0] = WasiFunction::RandomGet;
    }
}
