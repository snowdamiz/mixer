// Independently authored offline generator; frozen transport 052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439
use crate::experimental_capability::{FailureCode, Operation};
#[rustfmt::skip]
pub(super) fn terminal(operation: Operation, failure: FailureCode) -> &'static [u8] {
    match (operation, failure) {
        (Operation::HttpRequest, FailureCode::Unavailable) => include_bytes!("generated/http_request-unavailable.json"),
        (Operation::HttpRequest, FailureCode::Cancelled) => include_bytes!("generated/http_request-cancelled.json"),
        (Operation::HttpRequest, FailureCode::DeadlineExceeded) => include_bytes!("generated/http_request-deadlineExceeded.json"),
        (Operation::Get, FailureCode::Unavailable) => include_bytes!("generated/storage_get-unavailable.json"),
        (Operation::Get, FailureCode::Cancelled) => include_bytes!("generated/storage_get-cancelled.json"),
        (Operation::Get, FailureCode::DeadlineExceeded) => include_bytes!("generated/storage_get-deadlineExceeded.json"),
        (Operation::Put, FailureCode::Unavailable) => include_bytes!("generated/storage_put-unavailable.json"),
        (Operation::Put, FailureCode::Cancelled) => include_bytes!("generated/storage_put-cancelled.json"),
        (Operation::Put, FailureCode::DeadlineExceeded) => include_bytes!("generated/storage_put-deadlineExceeded.json"),
        (Operation::Delete, FailureCode::Unavailable) => include_bytes!("generated/storage_delete-unavailable.json"),
        (Operation::Delete, FailureCode::Cancelled) => include_bytes!("generated/storage_delete-cancelled.json"),
        (Operation::Delete, FailureCode::DeadlineExceeded) => include_bytes!("generated/storage_delete-deadlineExceeded.json"),
    }
}
