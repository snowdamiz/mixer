#define _POSIX_C_SOURCE 200809L
#include "../internal.h"
#include <android/looper.h>
#include <errno.h>
#include <inttypes.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Independently authored state-machine probes. The tiny ALooper implementation
 * exercises the actual platform_android.c wrapper on POSIX; it is not an
 * Android Looper, JNI entry, Swift Task or resource-destruction receipt. */
static _Atomic uint64_t checks;
static void fail(const char *expression, int line) {
    fprintf(stderr, "FACADE_FAIL line=%d %s\n", line, expression); exit(1);
}
#define CHECK(expression) do { atomic_fetch_add_explicit(&checks, 1, memory_order_relaxed); \
    if (!(expression)) fail(#expression, __LINE__); } while (0)
struct ALooper { int tag; };
static struct ALooper looper = {1};
static int registered_fd = -1, registration_count, acquire_count, no_looper;
static ALooper_callbackFunc platform_callback;
static void *platform_data;
ALooper *ALooper_forThread(void) { return no_looper ? NULL : &looper; }
void ALooper_acquire(ALooper *value) { CHECK(value == &looper); ++acquire_count; }
void ALooper_release(ALooper *value) { CHECK(value == &looper); }
int ALooper_addFd(ALooper *value, int fd, int ident, int events,
                 ALooper_callbackFunc callback, void *data) {
    CHECK(value == &looper && ident == ALOOPER_POLL_CALLBACK && events == ALOOPER_EVENT_INPUT);
    CHECK(fd >= 0 && callback != NULL && data != NULL && registered_fd == -1);
    registered_fd = fd; platform_callback = callback; platform_data = data;
    ++registration_count; return 1;
}
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    int hold_entry, hold_complete, hold_tail, hold_progress;
    int entry_entered, completion_entered, tail_entered, progress_entered, release;
    int callback_returned, allow_fence;
    int close_in_drain, nested_in_drain, fail_retire, nested_progress, count_lookup;
    uint64_t progress_calls, fault_calls, callback_fence, entry_fence;
    uint64_t drains, completions, lookups, last_entry, target_facade;
    int32_t first_fault, last_result;
} script = {.lock = PTHREAD_MUTEX_INITIALIZER, .changed = PTHREAD_COND_INITIALIZER};

static struct mxuit_snapshot snapshot(void) {
    struct mxuit_snapshot value; CHECK(mxuit_inspect(&value) == MXUIT_OK); return value;
}
static struct mxuit_owner_snapshot owner_snapshot(uint64_t owner) {
    struct mxuit_owner_snapshot value; CHECK(mxuit_inspect_owner(owner, &value) == MXUIT_OK); return value;
}
static struct mxuit_test_facade_snapshot facade_snapshot(uint64_t facade) {
    struct mxuit_test_facade_snapshot value;
    CHECK(mxuit_test_inspect_facade(facade, &value) == MXUIT_OK); return value;
}
static void install(void) {
    CHECK(mxuit_install() == MXUIT_OK); CHECK(mxuit_install() == MXUIT_OK);
    CHECK(registration_count == 1 && acquire_count == 1);
}
static uint64_t acquire_facade(void) {
    uint64_t facade = 99; CHECK(mxuit_facade_acquire(&facade) == MXUIT_OK);
    CHECK(facade != 0 && facade <= INT64_MAX); return facade;
}
static uint64_t endpoint(uint64_t facade, uint32_t purpose) {
    uint64_t owner = 99; CHECK(mxuit_acquire_for_facade(facade, purpose, &owner) == MXUIT_OK);
    CHECK(owner != 0); return owner;
}
static uint64_t enter(uint64_t facade, uint32_t kind) {
    uint64_t entry = 99; CHECK(mxuit_ui_enter(facade, 0, 0, kind, &entry) == MXUIT_OK);
    CHECK(entry != 0); CHECK(mxuit_ui_validate(facade, entry) == MXUIT_OK); return entry;
}
static struct timespec deadline(void) {
    struct timespec value; CHECK(clock_gettime(CLOCK_REALTIME, &value) == 0); value.tv_sec += 5; return value;
}
static void wait_flag(int *flag) {
    struct timespec until = deadline(); CHECK(pthread_mutex_lock(&script.lock) == 0);
    while (!*flag) CHECK(pthread_cond_timedwait(&script.changed, &script.lock, &until) == 0);
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
}
static void signal_flag(int *flag) {
    CHECK(pthread_mutex_lock(&script.lock) == 0); *flag = 1;
    CHECK(pthread_cond_broadcast(&script.changed) == 0); CHECK(pthread_mutex_unlock(&script.lock) == 0);
}
static void hold(int *entered) {
    *entered = 1; CHECK(pthread_cond_broadcast(&script.changed) == 0);
    struct timespec until = deadline();
    while (!script.release) CHECK(pthread_cond_timedwait(&script.changed, &script.lock, &until) == 0);
}
/* Native-to-Java schedule: a fixed helper verifies its active lease before the
 * simulated weak/JNI lookup, and Java synchronously enters the saved platform
 * callback. Failed-event bits prove rejection precedes even fault handling.
 * No code below the helper return may use a resource or invoke Java. */
static void simulated_java_helper(uint64_t facade, uint64_t entry) {
    CHECK(mxuit_ui_validate(facade, entry) == MXUIT_OK);
    struct mxuit_snapshot before = snapshot();
    CHECK(before.active_entry_serial == entry && before.active_entry_facade == facade);
    uint64_t progress_before;
    CHECK(pthread_mutex_lock(&script.lock) == 0); ++script.lookups;
    progress_before = script.progress_calls; CHECK(pthread_mutex_unlock(&script.lock) == 0);
    CHECK(platform_callback(registered_fd, ALOOPER_EVENT_INPUT | ALOOPER_EVENT_ERROR, platform_data) == 1);
    CHECK(mxuit_callback(registered_fd, 1, 1) == MXUIT_BUSY);
    struct mxuit_snapshot after = snapshot();
    CHECK(after.pending_pipe_hint == before.pending_pipe_hint);
    CHECK(after.callback_epoch == before.callback_epoch && after.fenced_epoch == before.fenced_epoch);
    CHECK(after.ui_entry_fenced == before.ui_entry_fenced && after.callbacks == before.callbacks);
    CHECK(after.drains == before.drains && after.completions == before.completions && after.fault == 0);
    CHECK(pthread_mutex_lock(&script.lock) == 0);
    CHECK(script.progress_calls == progress_before); CHECK(pthread_mutex_unlock(&script.lock) == 0);
}
void mxuit_progress(uint64_t callback_fence, uint64_t ui_entry_fence, int32_t sticky_fault) {
    /* Inspection/reentrant fixed C calls here would deadlock if C held its lock. */
    struct mxuit_snapshot value = snapshot();
    CHECK(callback_fence <= value.fenced_epoch && ui_entry_fence <= value.ui_entry_fenced);
    CHECK(sticky_fault == MXUIT_OK || sticky_fault == value.fault);
    CHECK(pthread_mutex_lock(&script.lock) == 0);
    ++script.progress_calls;
    if (sticky_fault != 0) { ++script.fault_calls; CHECK(script.first_fault == 0); script.first_fault = sticky_fault; }
    if (callback_fence > script.callback_fence) script.callback_fence = callback_fence;
    if (ui_entry_fence > script.entry_fence) script.entry_fence = ui_entry_fence;
    int nested = script.nested_progress;
    if (script.hold_progress && sticky_fault == MXUIT_OK) hold(&script.progress_entered);
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
    if (nested && sticky_fault == MXUIT_OK) {
        CHECK(value.callback_active == 1);
        CHECK(mxuit_callback(registered_fd, 1, 0) == MXUIT_BUSY);
        CHECK(snapshot().fenced_epoch == value.fenced_epoch);
    }
    /* Process-only scalar tail; no endpoint/facade record read follows resume. */
}
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    struct mxuit_owner_snapshot record = owner_snapshot(owner);
    CHECK(record.facade_id != 0 && record.active_helper == 1 && record.active_drain_kind == kind);
    CHECK(snapshot().callback_active == 1);
    uint64_t bad = 99;
    CHECK(mxuit_ui_enter(record.facade_id, owner, waiter + 1, kind, &bad) == MXUIT_STALE && bad == 0);
    CHECK(mxuit_ui_enter(record.facade_id, owner, waiter, kind == MXUIT_PRESENT ? MXUIT_UI_RETIRE : MXUIT_UI_PRESENT,
                         &bad) == MXUIT_INVALID && bad == 0);
    CHECK(pthread_mutex_lock(&script.lock) == 0);
    ++script.drains;
    int close = script.close_in_drain, nested = script.nested_in_drain, lookup = script.count_lookup;
    int failed = script.fail_retire;
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
    /* A PRESENT claimed before close remains eligible for its exact lease. */
    if (close) CHECK(mxuit_facade_begin_close(record.facade_id) == MXUIT_OK);
    uint64_t entry = 0;
    CHECK(mxuit_ui_enter(record.facade_id, owner, waiter, kind, &entry) == MXUIT_OK);
    CHECK(mxuit_ui_validate(record.facade_id, entry) == MXUIT_OK);
    CHECK(pthread_mutex_lock(&script.lock) == 0); script.last_entry = entry;
    if (script.hold_entry) hold(&script.entry_entered);
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
    if (nested || lookup) simulated_java_helper(record.facade_id, entry);
    CHECK(mxuit_ui_leave(record.facade_id, entry) == MXUIT_OK);
    /* Only scalar return remains after lease leave. */
    return failed && kind == MXUIT_RETIRE ? MXUIT_DRAIN_FAILED : MXUIT_DRAIN_OK;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    (void)waiter;
    struct mxuit_owner_snapshot value = owner_snapshot(owner);
    CHECK(value.completing == 1 && value.active_helper == 0 && value.active_drain_kind == 0);
    uint64_t invalid = 99;
    CHECK(mxuit_ui_enter(value.facade_id, owner, waiter, kind, &invalid) == MXUIT_STALE && invalid == 0);
    CHECK(pthread_mutex_lock(&script.lock) == 0); ++script.completions; script.last_result = result;
    if (script.hold_complete) hold(&script.completion_entered);
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
}
static int pump(int timeout) {
    struct pollfd fd = {registered_fd, POLLIN, 0};
    int ready = poll(&fd, 1, timeout); CHECK(ready == 0 || ready == 1);
    if (ready == 0) return 0;
    CHECK((fd.revents & POLLIN) != 0);
    int result = platform_callback(registered_fd, ALOOPER_EVENT_INPUT, platform_data);
    CHECK(pthread_mutex_lock(&script.lock) == 0);
    if (script.hold_tail && !script.tail_entered) hold(&script.tail_entered);
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
    return result;
}
static void retire(uint64_t owner) {
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == 1); CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY); CHECK(pump(0) == 1);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_OK);
}
static void no_work(void) { CHECK(pump(0) == 0); CHECK(snapshot().pending_pipe_hint == 0); }

static void facade_capacity(void) {
    uint64_t out = 99; CHECK(mxuit_facade_acquire(&out) == MXUIT_UNAVAILABLE && out == 0);
    CHECK(mxuit_facade_acquire(NULL) == MXUIT_INVALID); install();
    uint64_t facades[16];
    for (size_t i = 0; i < 16; ++i) { facades[i] = acquire_facade(); CHECK(facades[i] == i + 1); }
    out = 99; CHECK(mxuit_facade_acquire(&out) == MXUIT_CAPACITY && out == 0);
    CHECK(snapshot().occupied_facades == 16 && snapshot().occupied == 0 && script.progress_calls == 0);
    CHECK(mxuit_facade_begin_close(facades[4]) == MXUIT_OK);
    CHECK(mxuit_facade_try_reclaim(facades[4]) == MXUIT_OK); CHECK(acquire_facade() > facades[15]);
    CHECK(mxuit_facade_begin_close(facades[4]) == MXUIT_STALE); no_work();
}
static void invalid_identities(void) {
    install(); uint64_t facade = acquire_facade(), out = 99;
    CHECK(mxuit_acquire_for_facade(facade, 0, &out) == MXUIT_INVALID && out == 0);
    out = 99; CHECK(mxuit_acquire_for_facade(0, MXUIT_ATTEMPT, &out) == MXUIT_INVALID && out == 0);
    out = 99; CHECK(mxuit_acquire_for_facade(facade + 1, MXUIT_ATTEMPT, &out) == MXUIT_STALE && out == 0);
    CHECK(mxuit_acquire_for_facade(facade, MXUIT_ATTEMPT, NULL) == MXUIT_INVALID);
    CHECK(mxuit_facade_begin_close(0) == MXUIT_INVALID && mxuit_facade_try_reclaim(0) == MXUIT_INVALID);
    CHECK(mxuit_facade_try_reclaim(facade + 1) == MXUIT_STALE);
    CHECK(mxuit_ui_leave(0, 1) == MXUIT_INVALID && mxuit_ui_validate(facade, 0) == MXUIT_INVALID);
    CHECK(mxuit_ui_leave(facade, 1) == MXUIT_STALE && mxuit_ui_validate(facade + 1, 1) == MXUIT_STALE);
    for (uint32_t kind = 0; kind < 4; ++kind) {
        out = 99;
        CHECK(mxuit_ui_enter(facade, kind == MXUIT_UI_INGRESS || kind == MXUIT_UI_CLEANUP ? 1 : 0,
                             0, kind, &out) == MXUIT_INVALID && out == 0);
    }
    out = 99; CHECK(mxuit_ui_enter(facade, 0, 0, 4, &out) == MXUIT_INVALID && out == 0);
    out = 99; CHECK(mxuit_ui_enter(0, 0, 0, MXUIT_UI_INGRESS, &out) == MXUIT_INVALID && out == 0);
    out = 99; CHECK(mxuit_ui_enter(facade + 1, 0, 0, MXUIT_UI_INGRESS, &out) == MXUIT_STALE && out == 0);
    CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_INGRESS, NULL) == MXUIT_INVALID); no_work();
}
static void direct_entry_nested(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    uint64_t entry = enter(facade, MXUIT_UI_INGRESS), other = acquire_facade(), out = 99;
    simulated_java_helper(facade, entry);
    CHECK(mxuit_ui_enter(other, 0, 0, MXUIT_UI_CLEANUP, &out) == MXUIT_BUSY && out == 0);
    CHECK(mxuit_ui_validate(other, entry) == MXUIT_STALE && mxuit_ui_leave(other, entry) == MXUIT_STALE);
    CHECK(mxuit_ui_leave(facade, entry + 1) == MXUIT_STALE);
    CHECK(mxuit_ui_validate(facade, entry) == MXUIT_OK);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    CHECK(mxuit_ui_validate(facade, entry) == MXUIT_STALE && mxuit_ui_leave(facade, entry) == MXUIT_STALE);
    CHECK(snapshot().ui_entry_fenced == 0 && script.progress_calls == 0);
    CHECK(pump(0) == 1); CHECK(script.drains == 1 && script.lookups == 1);
    CHECK(script.entry_fence == entry); CHECK(pump(0) == 1); no_work();
}
static void no_byte_nested(void) {
    install(); uint64_t facade = acquire_facade(), entry = enter(facade, MXUIT_UI_INGRESS);
    CHECK(snapshot().pending_pipe_hint == 0); simulated_java_helper(facade, entry);
    CHECK(snapshot().pending_pipe_hint == 0);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK); CHECK(pump(0) == 1);
    CHECK(script.progress_calls == 1 && script.entry_fence == entry && script.drains == 0); no_work();
}
static void helper_nested(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    script.nested_in_drain = 1; CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == 1); CHECK(script.lookups == 1 && script.progress_calls == 0);
    CHECK(snapshot().ui_entries_issued == 1 && snapshot().ui_entry_fenced == 0);
    CHECK(pump(0) == 1); CHECK(script.entry_fence == 1 && script.callback_fence == 1); no_work();
}
static void lifecycle_across_attempts(void) {
    install(); uint64_t facade = acquire_facade(), first = endpoint(facade, MXUIT_ATTEMPT), out = 99;
    CHECK(mxuit_acquire_for_facade(facade, MXUIT_ATTEMPT, &out) == MXUIT_BUSY && out == 0);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_BUSY); retire(first);
    CHECK(facade_snapshot(facade).current_endpoint == 0 && facade_snapshot(facade).closing == 0);
    uint64_t entry = enter(facade, MXUIT_UI_INGRESS); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    uint64_t second = endpoint(facade, MXUIT_ATTEMPT); CHECK(second > first);
    CHECK(owner_snapshot(second).last_entry_serial == entry);
    CHECK(mxuit_request(first, 2) == MXUIT_STALE);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK && mxuit_facade_begin_close(facade) == MXUIT_OK);
    CHECK(owner_snapshot(second).closing == 1); CHECK(pump(0) == 1); retire(second);
    out = 99; CHECK(mxuit_acquire_for_facade(facade, MXUIT_ATTEMPT, &out) == MXUIT_CLOSED && out == 0);
    uint64_t terminal = endpoint(facade, MXUIT_TERMINAL); CHECK(terminal > second);
    CHECK(owner_snapshot(terminal).closing == 1); retire(terminal);
    CHECK(facade_snapshot(facade).terminal_issued == 1);
    out = 99; CHECK(mxuit_acquire_for_facade(facade, MXUIT_TERMINAL, &out) == MXUIT_CLOSED && out == 0);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_STALE); no_work();
}
static void terminal_admission(void) {
    install(); uint64_t facade = acquire_facade(), out = 99;
    CHECK(mxuit_acquire_for_facade(facade, MXUIT_TERMINAL, &out) == MXUIT_INVALID && out == 0);
    uint64_t owners[16];
    for (size_t i = 0; i < 16; ++i) CHECK(mxuit_acquire(&owners[i]) == MXUIT_OK);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK);
    out = 99; CHECK(mxuit_acquire_for_facade(facade, MXUIT_TERMINAL, &out) == MXUIT_CAPACITY && out == 0);
    CHECK(facade_snapshot(facade).terminal_issued == 0 && facade_snapshot(facade).current_endpoint == 0);
    CHECK(script.progress_calls == 0 && snapshot().fault == 0); no_work();
}
static void cleanup_without_endpoint(void) {
    install(); uint64_t facade = acquire_facade(); CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK);
    uint64_t out = 99; CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_INGRESS, &out) == MXUIT_CLOSED && out == 0);
    uint64_t entry = enter(facade, MXUIT_UI_CLEANUP);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_BUSY);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK); CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_BUSY);
    CHECK(script.progress_calls == 0); CHECK(pump(0) == 1);
    CHECK(script.entry_fence == entry && mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    out = 99; CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_CLEANUP, &out) == MXUIT_STALE && out == 0); no_work();
}
static void cleanup_inflight_acquire(void) {
    install(); uint64_t facade = acquire_facade(); CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK);
    uint64_t entry = enter(facade, MXUIT_UI_CLEANUP);
    uint64_t owner = endpoint(facade, MXUIT_TERMINAL);
    CHECK(owner_snapshot(owner).last_entry_serial == entry);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); simulated_java_helper(facade, entry);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY && mxuit_facade_try_reclaim(facade) == MXUIT_BUSY);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK); CHECK(pump(0) == 1);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK && mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(pump(0) == 1 && mxuit_try_reclaim(owner) == MXUIT_OK);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_OK); no_work();
}
static void post_retire_cleanup_fence(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == 1 && pump(0) == 1); CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    uint64_t entry = enter(facade, MXUIT_UI_CLEANUP);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY && snapshot().fenced_epoch >= owner_snapshot(owner).last_hook_epoch);
    CHECK(pump(0) == 1 && mxuit_try_reclaim(owner) == MXUIT_OK);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_OK); no_work();
}
static void close_claimed_present(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    script.close_in_drain = 1; CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == 1 && script.last_result == MXUIT_DRAIN_CLOSE_PENDING);
    CHECK(owner_snapshot(owner).retirement_done == 0);
    CHECK(mxuit_request(owner, 2) == MXUIT_OK); CHECK(pump(0) == 1);
    CHECK(script.last_result == MXUIT_DRAIN_OK && owner_snapshot(owner).retirement_done == 1);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(pump(0) == 1 && mxuit_try_reclaim(owner) == MXUIT_OK);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_OK); no_work();
}
static void exact_waiter_and_facade(void) {
    install(); uint64_t facade = acquire_facade(), other = acquire_facade();
    uint64_t owner = endpoint(facade, MXUIT_ATTEMPT), out = 99;
    CHECK(mxuit_ui_enter(other, owner, 1, MXUIT_UI_PRESENT, &out) == MXUIT_STALE && out == 0);
    out = 99; CHECK(mxuit_ui_enter(facade, owner, 1, MXUIT_UI_PRESENT, &out) == MXUIT_STALE && out == 0);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    out = 99; CHECK(mxuit_ui_enter(facade, owner, 1, MXUIT_UI_PRESENT, &out) == MXUIT_BUSY && out == 0);
    CHECK(pump(0) == 1 && pump(0) == 1);
    out = 99; CHECK(mxuit_ui_enter(facade, owner, 1, MXUIT_UI_PRESENT, &out) == MXUIT_STALE && out == 0); no_work();
}
static void *wrong_thread_worker(void *argument) {
    uint64_t facade = *(uint64_t *)argument, out = 99;
    uint64_t active = facade_snapshot(facade).active_entry;
    CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_INGRESS, &out) == MXUIT_WRONG_THREAD && out == 0);
    CHECK(mxuit_ui_validate(facade, active) == MXUIT_WRONG_THREAD);
    CHECK(mxuit_ui_leave(facade, active) == MXUIT_WRONG_THREAD);
    CHECK(mxuit_callback(registered_fd, 1, 1) == MXUIT_WRONG_THREAD);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK); return NULL;
}
static void wrong_thread(void) {
    install(); uint64_t facade = acquire_facade(), entry = enter(facade, MXUIT_UI_INGRESS);
    pthread_t worker; CHECK(pthread_create(&worker, NULL, wrong_thread_worker, &facade) == 0);
    CHECK(pthread_join(worker, NULL) == 0);
    CHECK(snapshot().active_entry_serial == entry && snapshot().fault == 0 && script.progress_calls == 0);
    CHECK(mxuit_ui_validate(facade, entry) == MXUIT_OK); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    CHECK(pump(0) == 1 && mxuit_facade_try_reclaim(facade) == MXUIT_OK); no_work();
}
static void progress_fences(void) {
    install(); uint64_t facade = acquire_facade(); script.nested_progress = 1;
    uint64_t entry = enter(facade, MXUIT_UI_INGRESS); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    CHECK(pump(0) == 1); CHECK(script.progress_calls == 1 && script.entry_fence == entry && script.callback_fence == 0);
    no_work(); entry = enter(facade, MXUIT_UI_INGRESS); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
    CHECK(pump(0) == 1); CHECK(script.progress_calls == 2 && script.entry_fence == entry && script.callback_fence == 1);
    no_work(); CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK && mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    CHECK(script.progress_calls == 2);
}
static void facade_exhaustion(void) {
    install(); CHECK(mxuit_test_set_facade_issued(INT64_MAX - 1) == MXUIT_OK);
    uint64_t facade = acquire_facade(), out = 99; CHECK(facade == INT64_MAX);
    CHECK(mxuit_facade_acquire(&out) == MXUIT_EXHAUSTED && out == 0);
    CHECK(script.progress_calls == 0 && snapshot().fault == 0);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK && mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    out = 99; CHECK(mxuit_facade_acquire(&out) == MXUIT_EXHAUSTED && out == 0); no_work();
}
static void entry_exhaustion(void) {
    install(); uint64_t facade = acquire_facade(); CHECK(mxuit_test_set_ui_entry_issued(UINT64_MAX - 1) == MXUIT_OK);
    uint64_t entry = enter(facade, MXUIT_UI_CLEANUP); CHECK(entry == UINT64_MAX);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK && pump(0) == 1);
    uint64_t out = 99; CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_CLEANUP, &out) == MXUIT_EXHAUSTED && out == 0);
    CHECK(script.fault_calls == 1 && script.first_fault == MXUIT_EXHAUSTED);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_EXHAUSTED && snapshot().occupied_facades == 1);
    CHECK(mxuit_ui_enter(facade, 0, 0, MXUIT_UI_CLEANUP, &out) == MXUIT_EXHAUSTED && script.fault_calls == 1);
}
static void sticky_fault_checks(uint64_t facade, int32_t fault) {
    CHECK(script.fault_calls == 1 && script.first_fault == fault);
    CHECK(facade_snapshot(facade).closing == 1);
    CHECK(mxuit_facade_try_reclaim(facade) == fault);
    uint64_t out = 99; CHECK(mxuit_facade_acquire(&out) == fault && out == 0);
    out = 99; CHECK(mxuit_acquire_for_facade(facade, MXUIT_TERMINAL, &out) == fault && out == 0);
    CHECK(mxuit_facade_begin_close(facade) == fault && script.fault_calls == 1);
}
static void worker_write_fault(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    /* The call originates on a worker, with no possible Looper dispatch. */
    pthread_t worker;
    extern void *request_fault_worker(void *);
    CHECK(pthread_create(&worker, NULL, request_fault_worker, &owner) == 0);
    CHECK(pthread_join(worker, NULL) == 0); sticky_fault_checks(facade, MXUIT_IO);
    CHECK(script.drains == 0 && script.callback_fence == 0 && snapshot().occupied == 1);
}
void *request_fault_worker(void *argument) {
    CHECK(mxuit_request(*(uint64_t *)argument, 1) == MXUIT_IO); return NULL;
}
static void callback_read_fault(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_READ, EIO, 1) == MXUIT_OK);
    CHECK(pump(0) == 0); sticky_fault_checks(facade, MXUIT_IO);
    CHECK(snapshot().callback_epoch == 0 && script.drains == 0);
    CHECK(mxuit_callback(registered_fd, 1, 1) == MXUIT_IO && script.fault_calls == 1);
}
static void leave_write_fault(void) {
    install(); uint64_t facade = acquire_facade(), entry = enter(facade, MXUIT_UI_INGRESS);
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    CHECK(mxuit_ui_leave(facade, entry) == MXUIT_IO); sticky_fault_checks(facade, MXUIT_IO);
    CHECK(snapshot().active_entry_serial == 0 && snapshot().ui_entry_fenced == 0);
}
static void callback_event_fault(void) {
    install(); uint64_t facade = acquire_facade();
    CHECK(platform_callback(registered_fd, ALOOPER_EVENT_ERROR, platform_data) == 0);
    sticky_fault_checks(facade, MXUIT_IO); CHECK(script.progress_calls == 1);
}
static void initialization_fault(void) {
    no_looper = 1; CHECK(mxuit_install() == MXUIT_UNAVAILABLE);
    CHECK(script.fault_calls == 1 && script.first_fault == MXUIT_UNAVAILABLE);
    CHECK(mxuit_install() == MXUIT_UNAVAILABLE && script.fault_calls == 1);
    CHECK(snapshot().owned_fds == 0 && snapshot().occupied_facades == 0);
}
static void failed_retire_pins_facade(void) {
    install(); uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    script.fail_retire = 1; CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK && pump(0) == 1 && pump(0) == 1);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK && mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_BUSY && snapshot().occupied_facades == 1);
    uint64_t out = 99; CHECK(mxuit_acquire_for_facade(facade, MXUIT_TERMINAL, &out) == MXUIT_BUSY && out == 0);
    CHECK(script.fault_calls == 0); no_work();
}

static void *ui_single_callback(void *unused) {
    (void)unused; install(); signal_flag(&script.entry_entered);
    /* Parent publishes owner/request via the script lock release handshake. */
    wait_flag(&script.release);
    CHECK(pthread_mutex_lock(&script.lock) == 0); script.release = 0; script.entry_entered = 0;
    CHECK(pthread_mutex_unlock(&script.lock) == 0);
    CHECK(pump(1000) == 1);
    signal_flag(&script.callback_returned); wait_flag(&script.allow_fence);
    CHECK(pump(1000) == 1);
    return NULL;
}
static void held_stage(int stage) {
    if (stage == 0) script.hold_entry = 1;
    else if (stage == 1) script.hold_complete = 1;
    else script.hold_tail = 1;
    pthread_t ui; CHECK(pthread_create(&ui, NULL, ui_single_callback, NULL) == 0);
    wait_flag(&script.entry_entered);
    uint64_t facade = acquire_facade(), owner = endpoint(facade, MXUIT_ATTEMPT);
    CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK && mxuit_request(owner, 1) == MXUIT_OK);
    /* Separate started flag avoids counting the install handshake as a lease. */
    CHECK(pthread_mutex_lock(&script.lock) == 0); script.entry_entered = 0; script.release = 1;
    CHECK(pthread_cond_broadcast(&script.changed) == 0); CHECK(pthread_mutex_unlock(&script.lock) == 0);
    if (stage == 0) wait_flag(&script.entry_entered);
    else if (stage == 1) wait_flag(&script.completion_entered);
    else wait_flag(&script.tail_entered);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY && mxuit_facade_try_reclaim(facade) == MXUIT_BUSY);
    struct mxuit_snapshot value = snapshot();
    CHECK(value.fenced_epoch == 0 && value.ui_entry_fenced == 0);
    if (stage == 0) CHECK(value.active_helpers == 1 && value.active_entry_serial != 0);
    if (stage == 1) CHECK(value.completing == 1 && value.active_entry_serial == 0);
    if (stage == 2) CHECK(value.callback_active == 0 && value.completing == 0);
    uint64_t facades[15];
    for (size_t i = 0; i < 15; ++i) { facades[i] = acquire_facade(); (void)endpoint(facades[i], MXUIT_ATTEMPT); }
    uint64_t out = 99; CHECK(mxuit_facade_acquire(&out) == MXUIT_CAPACITY && out == 0);
    out = 99; CHECK(mxuit_acquire(&out) == MXUIT_CAPACITY && out == 0);
    CHECK(mxuit_callback(registered_fd, 1, 0) == MXUIT_WRONG_THREAD);
    signal_flag(&script.release); wait_flag(&script.callback_returned);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY && mxuit_facade_try_reclaim(facade) == MXUIT_BUSY);
    /* This thread cannot impersonate the UI thread to advance fences. */
    CHECK(mxuit_callback(registered_fd, 1, 0) == MXUIT_WRONG_THREAD);
    CHECK(snapshot().occupied == 16 && snapshot().occupied_facades == 16);
    signal_flag(&script.allow_fence); CHECK(pthread_join(ui, NULL) == 0);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_OK && mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    CHECK(snapshot().occupied == 15 && snapshot().occupied_facades == 15);
}
static void held_entry(void) { held_stage(0); }
static void held_completion(void) { held_stage(1); }
static void held_callback_tail(void) { held_stage(2); }

static void *held_progress_worker(void *argument) {
    uint64_t *ids = argument; wait_flag(&script.progress_entered);
    CHECK(mxuit_try_reclaim(ids[1]) == MXUIT_OK);
    CHECK(mxuit_facade_try_reclaim(ids[0]) == MXUIT_OK);
    /* Reuse both records while only the process-only progress tail is held. */
    uint64_t replacement = acquire_facade(), owner = endpoint(replacement, MXUIT_ATTEMPT);
    CHECK(replacement > ids[0] && owner > ids[1]);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    signal_flag(&script.release); return NULL;
}
static void held_progress_tail(void) {
    install(); uint64_t ids[2]; ids[0] = acquire_facade(); ids[1] = endpoint(ids[0], MXUIT_ATTEMPT);
    CHECK(mxuit_facade_begin_close(ids[0]) == MXUIT_OK && mxuit_request(ids[1], 1) == MXUIT_OK);
    CHECK(pump(0) == 1 && mxuit_consumer_joined(ids[1]) == MXUIT_OK);
    script.hold_progress = 1; pthread_t worker;
    CHECK(pthread_create(&worker, NULL, held_progress_worker, ids) == 0);
    CHECK(pump(0) == 1); CHECK(pthread_join(worker, NULL) == 0);
    CHECK(snapshot().occupied == 1 && snapshot().occupied_facades == 1);
    CHECK(script.drains == 2 && script.completions == 2 && script.progress_calls == 1);
    script.hold_progress = 0; CHECK(pump(0) == 1); no_work();
}
static void repeated_facades(void) {
    install(); uint64_t previous = 0;
    for (unsigned int iteration = 0; iteration < 100; ++iteration) {
        uint64_t facade = acquire_facade(); CHECK(facade > previous); previous = facade;
        uint64_t owner = endpoint(facade, MXUIT_ATTEMPT); retire(owner);
        CHECK(mxuit_facade_begin_close(facade) == MXUIT_OK);
        uint64_t entry = enter(facade, MXUIT_UI_CLEANUP); CHECK(mxuit_ui_leave(facade, entry) == MXUIT_OK);
        CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_BUSY && pump(0) == 1);
        CHECK(mxuit_facade_try_reclaim(facade) == MXUIT_OK);
    }
    CHECK(snapshot().occupied_facades == 0 && snapshot().occupied == 0);
    CHECK(snapshot().owned_fds == 2 && snapshot().registration == 1 && registration_count == 1); no_work();
}
struct test { const char *name; void (*run)(void); };
static const struct test tests[] = {
    {"facade_capacity", facade_capacity}, {"invalid_identities", invalid_identities},
    {"direct_entry_nested", direct_entry_nested}, {"no_byte_nested", no_byte_nested},
    {"helper_nested", helper_nested}, {"lifecycle_across_attempts", lifecycle_across_attempts},
    {"terminal_admission", terminal_admission}, {"cleanup_without_endpoint", cleanup_without_endpoint},
    {"cleanup_inflight_acquire", cleanup_inflight_acquire}, {"post_retire_cleanup_fence", post_retire_cleanup_fence},
    {"close_claimed_present", close_claimed_present}, {"exact_waiter_and_facade", exact_waiter_and_facade},
    {"wrong_thread", wrong_thread}, {"progress_fences", progress_fences},
    {"facade_exhaustion", facade_exhaustion}, {"entry_exhaustion", entry_exhaustion},
    {"worker_write_fault", worker_write_fault}, {"callback_read_fault", callback_read_fault},
    {"leave_write_fault", leave_write_fault}, {"callback_event_fault", callback_event_fault},
    {"initialization_fault", initialization_fault}, {"failed_retire_pins_facade", failed_retire_pins_facade},
    {"held_entry", held_entry}, {"held_completion", held_completion}, {"held_callback_tail", held_callback_tail},
    {"held_progress_tail", held_progress_tail}, {"repeated_facades", repeated_facades},
};
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (strcmp(argv[1], "--list") == 0) {
        for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) puts(tests[i].name);
        return 0;
    }
    for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) {
        if (strcmp(argv[1], tests[i].name) != 0) continue;
        tests[i].run(); printf("MXUIT_FACADE_PASS %s checks=%" PRIu64 "\n", tests[i].name,
            atomic_load_explicit(&checks, memory_order_relaxed)); return 0;
    }
    return 2;
}
