use super::diagnostic_result_v1::*;
fn access(view: UnverifiedResultViewV1<'_>) -> &[u8] { view.input }
