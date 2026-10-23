#include "internal.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { fprintf(stderr,"CHECK_FAILED line=%d %s\n",__LINE__,#c); exit(1); } } while(0)
static int fd = -1, old_schedule;
static uint64_t b, c, fb, fc;
static uint32_t pending_before_c;
static int32_t c_leave;
static struct mxuit_snapshot snapshot(void) {
    struct mxuit_snapshot s; CHECK(mxuit_inspect(&s) == MXUIT_OK); return s;
}
int32_t mxuit_platform_register(int value) { CHECK(fd == -1); fd=value; return MXUIT_OK; }
void mxuit_progress(uint64_t callback, uint64_t entry, int32_t fault) {
    (void)callback; (void)entry; CHECK(fault == MXUIT_OK || fault == MXUIT_IO);
}
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    CHECK(kind == MXUIT_PRESENT && (owner == b || owner == c));
    uint64_t facade=owner == b ? fb:fc, entry=0;
    CHECK(mxuit_ui_enter(facade,owner,waiter,MXUIT_UI_PRESENT,&entry) == MXUIT_OK);
    CHECK(mxuit_ui_validate(facade,entry) == MXUIT_OK);
    if (owner == c) {
        pending_before_c=snapshot().pending_pipe_hint;
        CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE,EIO,1) == MXUIT_OK);
        c_leave=mxuit_ui_leave(facade,entry);
        CHECK(c_leave == (old_schedule ? MXUIT_OK:MXUIT_IO));
    } else CHECK(mxuit_ui_leave(facade,entry) == MXUIT_OK);
    return MXUIT_DRAIN_OK;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    (void)waiter; CHECK(kind == MXUIT_PRESENT && result == MXUIT_DRAIN_OK);
    if (owner == b && old_schedule) {
        struct mxuit_snapshot s=snapshot();
        CHECK(s.completions == 1 && s.callback_active && s.pending_pipe_hint);
        // This is the schedule admitted by the old Swift predicate. b's real
        // completion is visible, but the same callback has not reached c yet.
        CHECK(mxuit_request(c,1) == MXUIT_OK);
    }
}
int main(int argc, char **argv) {
    CHECK(argc == 2 && (!strcmp(argv[1],"old") || !strcmp(argv[1],"fixed")));
    old_schedule=!strcmp(argv[1],"old");
    CHECK(mxuit_install() == MXUIT_OK);
    CHECK(mxuit_facade_acquire(&fb) == MXUIT_OK);
    CHECK(mxuit_acquire_for_facade(fb,MXUIT_ATTEMPT,&b) == MXUIT_OK);
    CHECK(mxuit_facade_acquire(&fc) == MXUIT_OK);
    CHECK(mxuit_acquire_for_facade(fc,MXUIT_ATTEMPT,&c) == MXUIT_OK);
    CHECK(mxuit_request(b,1) == MXUIT_OK);
    CHECK(mxuit_callback(fd,1,0) == MXUIT_OK);
    // A real second callback consumes the real return-fence byte.
    CHECK(mxuit_callback(fd,1,0) == MXUIT_OK);
    struct mxuit_snapshot s=snapshot();
    CHECK(!s.callback_active && !s.pending_pipe_hint && !s.fault);
    if (!old_schedule) {
        CHECK(s.completions == 1);
        CHECK(mxuit_request(c,1) == MXUIT_OK);
        CHECK(mxuit_callback(fd,1,0) == MXUIT_IO);
    }
    s=snapshot();
    CHECK(s.completions == 2 && pending_before_c == (unsigned)old_schedule);
    CHECK(s.fault == (old_schedule ? 0:MXUIT_IO));
    printf("SCHEDULE_PASS %s completions=%llu pending_before_c=%u leave_result=%d fault=%d\n",
        argv[1],(unsigned long long)s.completions,pending_before_c,c_leave,s.fault);
    // Old execution leaves the injected write unconsumed: a later actual write
    // consumes it. This is verification only, never a synthetic product fence.
    if (old_schedule) CHECK(mxuit_request(b,2) == MXUIT_IO && snapshot().fault == MXUIT_IO);
    return 0;
}
