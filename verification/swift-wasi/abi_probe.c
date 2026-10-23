/* Original assertions against the installed official Preview1 declaration header. */
#include <wasi/api.h>
#include <stddef.h>

_Static_assert(sizeof(__wasi_ciovec_t) == 8, "ciovec wasm32 size");
_Static_assert(offsetof(__wasi_ciovec_t, buf) == 0, "ciovec pointer");
_Static_assert(offsetof(__wasi_ciovec_t, buf_len) == 4, "ciovec length");
_Static_assert(sizeof(__wasi_fdstat_t) == 24, "fdstat size");
_Static_assert(offsetof(__wasi_fdstat_t, fs_filetype) == 0, "fdstat type");
_Static_assert(offsetof(__wasi_fdstat_t, fs_flags) == 2, "fdstat flags");
_Static_assert(offsetof(__wasi_fdstat_t, fs_rights_base) == 8, "fdstat base");
_Static_assert(offsetof(__wasi_fdstat_t, fs_rights_inheriting) == 16, "fdstat inheriting");
_Static_assert(__WASI_RIGHTS_FD_WRITE == 64, "write rights");
_Static_assert(__WASI_CLOCKID_REALTIME == 0 && __WASI_CLOCKID_MONOTONIC == 1, "clock ids");
_Static_assert(__WASI_ERRNO_SUCCESS == 0 && __WASI_ERRNO_BADF == 8, "basic errno");
_Static_assert(__WASI_ERRNO_FAULT == 21 && __WASI_ERRNO_INVAL == 28, "memory errno");
_Static_assert(__WASI_ERRNO_IO == 29 && __WASI_ERRNO_NOSPC == 51, "service errno");
_Static_assert(__WASI_ERRNO_NOTSUP == 58 && __WASI_ERRNO_OVERFLOW == 61, "unsupported errno");
_Static_assert(__WASI_ERRNO_NOTCAPABLE == 76, "capability errno");
