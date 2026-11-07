//! Static native-boundary diagnostics do not allocate error strings.
use crate::experimental_capability as mb;
use crate::{Error, MixerVmReport};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Failure {
    pub status: u32,
    pub code: &'static str,
    pub message: &'static str,
}
impl Failure {
    pub(crate) const fn api(message: &'static str) -> Self {
        Self {
            status: 3,
            code: "invalid_arguments",
            message,
        }
    }
    pub(crate) const fn invariant(message: &'static str) -> Self {
        Self {
            status: 4,
            code: "capability_invariant",
            message,
        }
    }
    pub(crate) const fn poisoned() -> Self {
        Self {
            status: 4,
            code: "capability_poisoned",
            message: "capability native state is poisoned",
        }
    }
    pub(crate) const fn terminal() -> Self {
        Self {
            status: 2,
            code: "capability_terminal",
            message: "capability session is terminal",
        }
    }
    pub(super) fn report(self) -> MixerVmReport {
        report(self.status, self.code, self.message, None, 0)
    }
}
pub(super) fn mailbox(e: mb::Error) -> Failure {
    use mb::Error::*;
    match e {
        Poisoned => Failure::poisoned(),
        AllocationFailure => Failure {
            status: 2,
            code: "capability_allocation",
            message: "capability payload allocation failed",
        },
        SessionClosed => Failure::terminal(),
        AlreadyAcknowledged => Failure::api("native work already acknowledged exit"),
        AlreadyTerminal => Failure::api("request is already terminal"),
        StaleRequest => Failure::api("unknown or released request identity"),
        _ => Failure::api("invalid native capability transition"),
    }
}
pub(super) fn vm(error: Error, status: u32) -> MixerVmReport {
    report(
        status,
        error.code,
        &error.message,
        error.function,
        error.offset,
    )
}
fn text<const N: usize>(out: &mut [u8; N], source: &str) {
    let n = source.len().min(N - 1);
    out[..n].copy_from_slice(&source.as_bytes()[..n]);
}
fn report(
    status: u32,
    code: &str,
    message: &str,
    function: Option<u32>,
    offset: usize,
) -> MixerVmReport {
    let mut r = MixerVmReport {
        status,
        function: function.unwrap_or(u32::MAX),
        offset: offset.min(u32::MAX as usize) as u32,
        ..MixerVmReport::default()
    };
    text(&mut r.code, code);
    text(&mut r.message, message);
    r
}
