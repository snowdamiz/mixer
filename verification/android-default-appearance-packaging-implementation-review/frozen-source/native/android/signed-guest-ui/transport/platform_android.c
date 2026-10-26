#include "internal.h"
#include <android/looper.h>
#include <stddef.h>

/* Process-lifetime registration and static userdata: no owner pointer is ever
 * given to ALooper, removed, freed or retargeted. The two pipe FDs and acquired
 * Looper reference deliberately remain baseline resources until process exit. */
static const unsigned char registration_tag = 1;
static ALooper *registered_looper;
static int callback(int fd, int events, void *data) {
    if (data != (const void *)&registration_tag) return 0;
    int failed = (events & (ALOOPER_EVENT_ERROR | ALOOPER_EVENT_HANGUP | ALOOPER_EVENT_INVALID)) != 0;
    int32_t status = mxuit_callback(fd, (events & ALOOPER_EVENT_INPUT) != 0, failed);
    /* Failure closes the transport, never releases owner slots or userdata.
     * No ALooper_removeFd call is treated as a completion barrier. */
    return status == MXUIT_IO || status == MXUIT_EXHAUSTED ? 0 : 1;
}
int32_t mxuit_platform_register(int fd) {
    ALooper *looper = ALooper_forThread();
    if (looper == NULL) return MXUIT_UNAVAILABLE;
    ALooper_acquire(looper);
    if (ALooper_addFd(looper, fd, ALOOPER_POLL_CALLBACK, ALOOPER_EVENT_INPUT,
                     callback, (void *)&registration_tag) != 1) {
        ALooper_release(looper); return MXUIT_IO;
    }
    registered_looper = looper;
    (void)registered_looper;
    return MXUIT_OK;
}
