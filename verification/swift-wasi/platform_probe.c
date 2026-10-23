/* Original compile-time check of the private Darwin FFI ABI used on this host. */
#include <sys/random.h>
#include <time.h>
#include <stddef.h>
_Static_assert(CLOCK_REALTIME == 0 && CLOCK_MONOTONIC == 6, "Darwin clock ids");
_Static_assert(sizeof(time_t) == sizeof(long), "Darwin time_t representation");
_Static_assert(sizeof(struct timespec) == 2 * sizeof(long), "Darwin timespec representation");
_Static_assert(offsetof(struct timespec, tv_nsec) == sizeof(long), "Darwin timespec offset");
static int (*const random_service)(void *, size_t) __attribute__((unused)) = getentropy;
static int (*const clock_time_service)(clockid_t, struct timespec *) __attribute__((unused)) = clock_gettime;
static int (*const clock_resolution_service)(clockid_t, struct timespec *) __attribute__((unused)) = clock_getres;
