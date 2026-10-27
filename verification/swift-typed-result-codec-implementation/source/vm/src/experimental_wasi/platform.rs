//! Private OS services. No guest address, process environment, path, or descriptor enters here.
use super::Errno;

#[derive(Clone, Copy)]
pub(super) enum Clock {
    Realtime,
    Monotonic,
}

// The platform ABI declarations below are from the installed Darwin/Linux platform APIs.
// All foreign writes target a bounded owned Rust slice or initialized stack timespec.
#[cfg(all(
    target_pointer_width = "64",
    any(
        target_os = "macos",
        target_os = "ios",
        target_os = "linux",
        target_os = "android"
    )
))]
pub(super) fn random(bytes: &mut [u8]) -> Result<(), Errno> {
    #[cfg(any(target_os = "macos", target_os = "ios"))]
    {
        unsafe extern "C" {
            fn getentropy(buffer: *mut std::ffi::c_void, size: usize) -> std::ffi::c_int;
        }
        // getentropy requires <=256 bytes. The caller also checks between these bounded calls.
        if bytes.len() > 256 {
            return Err(Errno::Inval);
        }
        // SAFETY: getentropy receives precisely this exclusively borrowed live slice.
        if unsafe { getentropy(bytes.as_mut_ptr().cast(), bytes.len()) } == 0 {
            Ok(())
        } else {
            Err(Errno::Io)
        }
    }
    #[cfg(any(target_os = "linux", target_os = "android"))]
    {
        unsafe extern "C" {
            fn getrandom(
                buffer: *mut std::ffi::c_void,
                size: usize,
                flags: std::ffi::c_uint,
            ) -> isize;
        }
        // GRND_NONBLOCK avoids waiting for entropy initialization. Short/interrupted calls fail,
        // leaving only scratch modified. There is no retry or weaker source.
        // SAFETY: getrandom receives precisely this exclusively borrowed live slice.
        let count = unsafe { getrandom(bytes.as_mut_ptr().cast(), bytes.len(), 1) };
        if count == bytes.len() as isize {
            Ok(())
        } else {
            Err(Errno::Io)
        }
    }
}
#[cfg(not(all(
    target_pointer_width = "64",
    any(
        target_os = "macos",
        target_os = "ios",
        target_os = "linux",
        target_os = "android"
    )
)))]
pub(super) fn random(_: &mut [u8]) -> Result<(), Errno> {
    Err(Errno::Notsup)
}

#[cfg(all(
    target_pointer_width = "64",
    any(
        target_os = "macos",
        target_os = "ios",
        target_os = "linux",
        target_os = "android"
    )
))]
pub(super) fn clock(clock: Clock, resolution: bool) -> Result<u64, Errno> {
    #[repr(C)]
    struct Timespec {
        seconds: std::ffi::c_long,
        nanos: std::ffi::c_long,
    }
    unsafe extern "C" {
        fn clock_gettime(clock: std::ffi::c_int, value: *mut Timespec) -> std::ffi::c_int;
        fn clock_getres(clock: std::ffi::c_int, value: *mut Timespec) -> std::ffi::c_int;
    }
    #[cfg(any(target_os = "macos", target_os = "ios"))]
    let id = match clock {
        Clock::Realtime => 0,
        Clock::Monotonic => 6,
    };
    #[cfg(any(target_os = "linux", target_os = "android"))]
    let id = match clock {
        Clock::Realtime => 0,
        Clock::Monotonic => 1,
    };
    let mut value = Timespec {
        seconds: 0,
        nanos: 0,
    };
    // SAFETY: both APIs receive a valid stack Timespec with the platform's C representation.
    let result = unsafe {
        if resolution {
            clock_getres(id, &mut value)
        } else {
            clock_gettime(id, &mut value)
        }
    };
    if result != 0 {
        return Err(Errno::Io);
    }
    nanoseconds(value.seconds, value.nanos)
}

#[cfg(any(
    test,
    all(
        target_pointer_width = "64",
        any(
            target_os = "macos",
            target_os = "ios",
            target_os = "linux",
            target_os = "android"
        )
    )
))]
fn nanoseconds(seconds: i64, nanos: i64) -> Result<u64, Errno> {
    if seconds < 0 || !(0..1_000_000_000).contains(&nanos) {
        return Err(Errno::Io);
    }
    (seconds as u64)
        .checked_mul(1_000_000_000)
        .and_then(|v| v.checked_add(nanos as u64))
        .ok_or(Errno::Overflow)
}
#[cfg(not(all(
    target_pointer_width = "64",
    any(
        target_os = "macos",
        target_os = "ios",
        target_os = "linux",
        target_os = "android"
    )
)))]
pub(super) fn clock(_: Clock, _: bool) -> Result<u64, Errno> {
    Err(Errno::Notsup)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn clock_conversion_checks_negative_malformed_and_overflow_values() {
        assert_eq!(nanoseconds(2, 3), Ok(2_000_000_003));
        assert_eq!(nanoseconds(-1, 0), Err(Errno::Io));
        assert_eq!(nanoseconds(0, -1), Err(Errno::Io));
        assert_eq!(nanoseconds(0, 1_000_000_000), Err(Errno::Io));
        assert_eq!(nanoseconds(i64::MAX, 0), Err(Errno::Overflow));
        assert_eq!(nanoseconds(18_446_744_073, 709_551_615), Ok(u64::MAX));
        assert_eq!(
            nanoseconds(18_446_744_073, 709_551_616),
            Err(Errno::Overflow)
        );
    }
}
