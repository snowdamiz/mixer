#define _POSIX_C_SOURCE 200809L
#include "../../native/android/signed-guest-ui/transport/internal.h"
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

/* Independent bounded reviewer harness. Real transport + platform source link
 * against these host-only ALooper symbols. No JNI, Swift or Android runtime. */
static _Atomic uint64_t assertions;
static void bad(const char *what, int line) { fprintf(stderr, "REVIEW_FAIL line=%d %s\n", line, what); exit(1); }
#define REQUIRE(x) do { atomic_fetch_add_explicit(&assertions, 1, memory_order_relaxed); if (!(x)) bad(#x, __LINE__); } while (0)
struct ALooper { int opaque; };
static struct ALooper host_looper;
static int process_fd = -1;
static ALooper_callbackFunc dispatch;
static void *dispatch_data;
ALooper *ALooper_forThread(void) { return &host_looper; }
void ALooper_acquire(ALooper *value) { REQUIRE(value == &host_looper); }
void ALooper_release(ALooper *value) { REQUIRE(value == &host_looper); }
int ALooper_addFd(ALooper *value, int fd, int ident, int events, ALooper_callbackFunc hook, void *data) {
    REQUIRE(value == &host_looper && process_fd == -1 && fd >= 0);
    REQUIRE(ident == ALOOPER_POLL_CALLBACK && events == ALOOPER_EVENT_INPUT && hook != NULL && data != NULL);
    process_fd = fd; dispatch = hook; dispatch_data = data; return 1;
}
static struct mxuit_snapshot inspect(void) { struct mxuit_snapshot s; REQUIRE(mxuit_inspect(&s) == MXUIT_OK); return s; }
static struct mxuit_owner_snapshot owner_state(uint64_t id) {
    struct mxuit_owner_snapshot s; REQUIRE(mxuit_inspect_owner(id, &s) == MXUIT_OK); return s;
}
static struct mxuit_test_facade_snapshot facade_state(uint64_t id) {
    struct mxuit_test_facade_snapshot s; REQUIRE(mxuit_test_inspect_facade(id, &s) == MXUIT_OK); return s;
}
static uint64_t facade(void) { uint64_t id = UINT64_MAX; REQUIRE(mxuit_facade_acquire(&id) == MXUIT_OK && id > 0 && id <= INT64_MAX); return id; }
static uint64_t endpoint(uint64_t f, uint32_t kind) { uint64_t id = 0; REQUIRE(mxuit_acquire_for_facade(f, kind, &id) == MXUIT_OK && id != 0); return id; }
static uint64_t direct(uint64_t f, uint32_t kind) { uint64_t id = 0; REQUIRE(mxuit_ui_enter(f, 0, 0, kind, &id) == MXUIT_OK && id != 0); return id; }
static void install(void) { REQUIRE(mxuit_install() == MXUIT_OK); REQUIRE(mxuit_install() == MXUIT_OK); }
static void callback(void) {
    struct pollfd p = {process_fd, POLLIN, 0}; REQUIRE(poll(&p, 1, 0) == 1 && (p.revents & POLLIN) != 0);
    REQUIRE(dispatch(process_fd, ALOOPER_EVENT_INPUT, dispatch_data) == 1);
}
static void idle(void) { struct pollfd p = {process_fd, POLLIN, 0}; REQUIRE(poll(&p, 1, 0) == 0); REQUIRE(inspect().pending_pipe_hint == 0); }
static struct timespec until(void) { struct timespec t; REQUIRE(clock_gettime(CLOCK_REALTIME, &t) == 0); t.tv_sec += 5; return t; }

static struct {
    pthread_mutex_t lock;
    pthread_cond_t change;
    int flags[12];
    int hold_progress, hold_native, identity, cleanup_completion, skip_entries;
    uint64_t unrelated_facade, unrelated_owner;
    uint64_t drains, completes, cleanup_entry, progress, faults;
    uint64_t callback_max, entry_max;
    int32_t sticky;
    uint64_t sequence[16];
    int observing[16], observed[16];
    uint64_t old_f[16], old_o[16], new_f[16], new_o[16];
} probe = {.lock = PTHREAD_MUTEX_INITIALIZER, .change = PTHREAD_COND_INITIALIZER};
static void locked(void) { REQUIRE(pthread_mutex_lock(&probe.lock) == 0); }
static void unlocked(void) { REQUIRE(pthread_mutex_unlock(&probe.lock) == 0); }
static void set(int n) { locked(); probe.flags[n] = 1; REQUIRE(pthread_cond_broadcast(&probe.change) == 0); unlocked(); }
static void wait_on(int n) {
    struct timespec t = until(); locked(); while (!probe.flags[n]) REQUIRE(pthread_cond_timedwait(&probe.change, &probe.lock, &t) == 0); unlocked();
}
static void wait_while_locked(int n) {
    struct timespec t = until(); while (!probe.flags[n]) REQUIRE(pthread_cond_timedwait(&probe.change, &probe.lock, &t) == 0);
}
/* Each of sixteen test progress cells has a sequence and one condition waiter.
 * This is a native observer model, not evidence about Swift continuations. The
 * hook only moves scalar signals; resumed workers may then use admission APIs. */
void mxuit_progress(uint64_t cb, uint64_t entry, int32_t fault) {
    struct mxuit_snapshot s = inspect(); /* Also rejects a hidden C-lock resume. */
    REQUIRE(cb <= s.fenced_epoch && entry <= s.ui_entry_fenced);
    REQUIRE(fault == 0 || fault == s.fault);
    locked();
    ++probe.progress;
    if (cb > probe.callback_max) probe.callback_max = cb;
    if (entry > probe.entry_max) probe.entry_max = entry;
    if (fault != 0) { REQUIRE(probe.sticky == 0); probe.sticky = fault; ++probe.faults; }
    for (size_t i = 0; i < 16; ++i) ++probe.sequence[i];
    REQUIRE(pthread_cond_broadcast(&probe.change) == 0);
    if (probe.hold_progress && fault == 0) {
        probe.flags[0] = 1; REQUIRE(pthread_cond_broadcast(&probe.change) == 0); wait_while_locked(1);
    }
    unlocked();
}
static void rejected_entry(uint64_t f, uint64_t o, uint64_t w, uint32_t k, int32_t expected) {
    uint64_t result = UINT64_MAX;
    REQUIRE(mxuit_ui_enter(f, o, w, k, &result) == expected && result == 0);
}
int32_t mxuit_drain(uint64_t o, uint64_t w, uint32_t k) {
    struct mxuit_owner_snapshot s = owner_state(o);
    REQUIRE(s.active_helper == 1 && s.active_drain_kind == k && s.waiter == 1);
    if (probe.identity && s.facade_id != 0) {
        rejected_entry(s.facade_id, probe.unrelated_owner, w, k, MXUIT_STALE);
        rejected_entry(probe.unrelated_facade, o, w, k, MXUIT_STALE);
        rejected_entry(s.facade_id, o, w + 1, k, MXUIT_STALE);
        rejected_entry(s.facade_id, o, w, k == MXUIT_PRESENT ? MXUIT_UI_RETIRE : MXUIT_UI_PRESENT, MXUIT_INVALID);
    }
    if (!probe.skip_entries && s.facade_id != 0) {
        uint64_t lease = 0; REQUIRE(mxuit_ui_enter(s.facade_id, o, w, k, &lease) == MXUIT_OK);
        REQUIRE(mxuit_ui_validate(s.facade_id, lease) == MXUIT_OK);
        if (probe.identity) {
            rejected_entry(probe.unrelated_facade, 0, 0, MXUIT_UI_CLEANUP, MXUIT_BUSY);
            struct mxuit_snapshot before = inspect();
            REQUIRE(mxuit_callback(process_fd, 1, 1) == MXUIT_BUSY);
            struct mxuit_snapshot after = inspect();
            REQUIRE(after.callback_epoch == before.callback_epoch && after.fenced_epoch == before.fenced_epoch);
            REQUIRE(after.ui_entry_fenced == before.ui_entry_fenced && after.pending_pipe_hint == before.pending_pipe_hint);
            REQUIRE(after.drains == before.drains && after.completions == before.completions && after.fault == 0);
        }
        if (probe.hold_native) { set(2); wait_on(3); }
        REQUIRE(mxuit_ui_leave(s.facade_id, lease) == MXUIT_OK);
    }
    locked(); ++probe.drains; unlocked();
    return MXUIT_DRAIN_OK;
}
void mxuit_complete(uint64_t o, uint64_t w, uint32_t k, int32_t result) {
    struct mxuit_owner_snapshot s = owner_state(o); REQUIRE(s.completing == 1 && s.active_helper == 0);
    REQUIRE(result == MXUIT_DRAIN_OK); /* These probes stop before claims. */
    if (s.facade_id != 0) rejected_entry(s.facade_id, o, w, k, MXUIT_STALE);
    if (probe.cleanup_completion && s.facade_id != 0) {
        uint64_t lease = direct(s.facade_id, MXUIT_UI_CLEANUP);
        REQUIRE(mxuit_ui_validate(s.facade_id, lease) == MXUIT_OK);
        REQUIRE(mxuit_ui_leave(s.facade_id, lease) == MXUIT_OK);
        probe.cleanup_entry = lease;
    }
    if (k == MXUIT_RETIRE) REQUIRE(mxuit_consumer_joined(o) == MXUIT_OK);
    REQUIRE(mxuit_try_reclaim(o) == MXUIT_BUSY);
    if (probe.hold_native) { set(4); wait_on(5); }
    locked(); ++probe.completes; unlocked();
}
static void retire_now(uint64_t o, uint64_t w) {
    REQUIRE(mxuit_begin_close(o) == MXUIT_OK && mxuit_request(o, w) == MXUIT_OK);
    callback(); REQUIRE(mxuit_try_reclaim(o) == MXUIT_BUSY); callback(); REQUIRE(mxuit_try_reclaim(o) == MXUIT_OK);
}

static void exact_active_drain_matrix(void) {
    install(); uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT);
    probe.unrelated_facade = facade(); probe.unrelated_owner = endpoint(probe.unrelated_facade, MXUIT_ATTEMPT); probe.identity = 1;
    REQUIRE(mxuit_request(o, 41) == MXUIT_OK); callback(); callback();
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK); REQUIRE(mxuit_request(o, 42) == MXUIT_OK);
    callback(); REQUIRE(mxuit_try_reclaim(o) == MXUIT_BUSY); callback(); REQUIRE(mxuit_try_reclaim(o) == MXUIT_OK);
    REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_OK); REQUIRE(probe.drains == 2 && probe.completes == 2); idle();
}
static void nested_reject_before_read(void) {
    install(); uint64_t f = facade(), other = facade(), lease = direct(f, MXUIT_UI_INGRESS);
    REQUIRE(mxuit_test_fail_syscall(MXUIT_TEST_READ, EIO, 1) == MXUIT_OK);
    rejected_entry(other, 0, 0, MXUIT_UI_INGRESS, MXUIT_BUSY);
    rejected_entry(other, 0, 0, MXUIT_UI_CLEANUP, MXUIT_BUSY);
    REQUIRE(mxuit_ui_leave(other, lease) == MXUIT_STALE && mxuit_ui_validate(other, lease) == MXUIT_STALE);
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK);
    REQUIRE(mxuit_callback(process_fd, 1, 1) == MXUIT_BUSY);
    REQUIRE(mxuit_callback(process_fd, 1, 0) == MXUIT_BUSY);
    REQUIRE(inspect().fault == 0 && inspect().pending_pipe_hint == 0 && probe.progress == 0);
    REQUIRE(mxuit_ui_validate(f, lease) == MXUIT_OK && mxuit_ui_leave(f, lease) == MXUIT_OK);
    REQUIRE(inspect().ui_entry_fenced == 0 && inspect().pending_pipe_hint == 1);
    REQUIRE(mxuit_callback(process_fd, 1, 0) == MXUIT_IO); /* injection survived both rejected entries */
    REQUIRE(inspect().callback_epoch == 0 && inspect().ui_entry_fenced == 0);
    REQUIRE(probe.faults == 1 && probe.sticky == MXUIT_IO && probe.drains == 0);
}
static void completion_cleanup_needs_new_fence(void) {
    install(); uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT);
    probe.cleanup_completion = 1;
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK && mxuit_request(o, 1) == MXUIT_OK); callback();
    REQUIRE(probe.cleanup_entry == 2 && owner_state(o).last_entry_serial == 2 && facade_state(f).last_entry_serial == 2);
    REQUIRE(inspect().ui_entry_fenced == 0 && mxuit_try_reclaim(o) == MXUIT_BUSY);
    callback(); REQUIRE(probe.entry_max == 2 && mxuit_try_reclaim(o) == MXUIT_OK);
    REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_OK); idle();
}
static void terminal_capacity_retry(void) {
    install(); uint64_t f = facade(), occupants[16];
    for (size_t i = 0; i < 16; ++i) REQUIRE(mxuit_acquire(&occupants[i]) == MXUIT_OK);
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK); uint64_t out = 99;
    REQUIRE(mxuit_acquire_for_facade(f, MXUIT_TERMINAL, &out) == MXUIT_CAPACITY && out == 0);
    REQUIRE(facade_state(f).terminal_issued == 0 && probe.progress == 0); idle();
    retire_now(occupants[8], 1);
    uint64_t terminal = endpoint(f, MXUIT_TERMINAL); REQUIRE(terminal > occupants[15]);
    REQUIRE(facade_state(f).terminal_issued == 1 && owner_state(terminal).closing == 1);
    retire_now(terminal, 1); out = 99;
    REQUIRE(mxuit_acquire_for_facade(f, MXUIT_TERMINAL, &out) == MXUIT_CLOSED && out == 0);
    REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_OK); uint64_t replacement = facade(); REQUIRE(replacement > f);
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_STALE); idle();
}
static void *replace_all(void *unused) {
    (void)unused; wait_on(0);
    for (size_t i = 0; i < 16; ++i) {
        REQUIRE(mxuit_try_reclaim(probe.old_o[i]) == MXUIT_OK);
        REQUIRE(mxuit_facade_try_reclaim(probe.old_f[i]) == MXUIT_OK);
    }
    for (size_t i = 0; i < 16; ++i) {
        probe.new_f[i] = facade(); probe.new_o[i] = endpoint(probe.new_f[i], MXUIT_ATTEMPT);
        REQUIRE(probe.new_f[i] > probe.old_f[15] && probe.new_o[i] > probe.old_o[15]);
        REQUIRE(mxuit_request(probe.new_o[i], 7) == MXUIT_OK);
    }
    set(1); return NULL;
}
static void full_reuse_during_progress(void) {
    install();
    for (size_t i = 0; i < 16; ++i) {
        probe.old_f[i] = facade(); probe.old_o[i] = endpoint(probe.old_f[i], MXUIT_ATTEMPT);
        REQUIRE(mxuit_facade_begin_close(probe.old_f[i]) == MXUIT_OK && mxuit_request(probe.old_o[i], 1) == MXUIT_OK);
    }
    callback(); REQUIRE(probe.drains == 16 && probe.completes == 16);
    probe.hold_progress = 1; pthread_t t; REQUIRE(pthread_create(&t, NULL, replace_all, NULL) == 0);
    callback(); REQUIRE(pthread_join(t, NULL) == 0); probe.hold_progress = 0;
    REQUIRE(probe.drains == 32 && probe.completes == 32 && inspect().occupied == 16 && inspect().occupied_facades == 16);
    for (size_t i = 0; i < 16; ++i) {
        REQUIRE(mxuit_try_reclaim(probe.old_o[i]) == MXUIT_STALE);
        REQUIRE(mxuit_facade_try_reclaim(probe.old_f[i]) == MXUIT_STALE);
        REQUIRE(owner_state(probe.new_o[i]).last_waiter == 7);
    }
    callback(); idle(); REQUIRE(inspect().owned_fds == 2 && inspect().registration == 1);
}
struct fault_actor { size_t index; uint64_t owner; };
static void *fault_actor(void *argument) {
    struct fault_actor *a = argument;
    locked(); probe.observing[a->index] = 1; uint64_t before = probe.sequence[a->index];
    REQUIRE(pthread_cond_broadcast(&probe.change) == 0); wait_while_locked(6); unlocked();
    REQUIRE(mxuit_request(a->owner, 1) == MXUIT_IO);
    locked();
    struct timespec t = until();
    while (probe.sequence[a->index] == before) REQUIRE(pthread_cond_timedwait(&probe.change, &probe.lock, &t) == 0);
    REQUIRE(probe.sticky == MXUIT_IO); probe.observed[a->index] = 1; unlocked(); return NULL;
}
static void concurrent_fault_fanout(void) {
    install(); struct fault_actor args[16]; pthread_t threads[16];
    REQUIRE(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    for (size_t i = 0; i < 16; ++i) { args[i].index = i; uint64_t f = facade(); args[i].owner = endpoint(f, MXUIT_ATTEMPT); REQUIRE(pthread_create(&threads[i], NULL, fault_actor, &args[i]) == 0); }
    locked(); struct timespec t = until();
    for (size_t i = 0; i < 16; ++i) while (!probe.observing[i]) REQUIRE(pthread_cond_timedwait(&probe.change, &probe.lock, &t) == 0);
    unlocked(); set(6);
    for (size_t i = 0; i < 16; ++i) { REQUIRE(pthread_join(threads[i], NULL) == 0); REQUIRE(probe.observed[i] == 1); REQUIRE(owner_state(args[i].owner).closing == 1); REQUIRE(mxuit_try_reclaim(args[i].owner) == MXUIT_IO); }
    REQUIRE(probe.faults == 1 && probe.progress == 1 && probe.drains == 0 && probe.completes == 0);
    REQUIRE(inspect().occupied == 16 && inspect().occupied_facades == 16 && inspect().callback_epoch == 0);
    uint64_t out = 99; REQUIRE(mxuit_facade_acquire(&out) == MXUIT_IO && out == 0);
    REQUIRE(mxuit_callback(process_fd, 1, 1) == MXUIT_IO && probe.faults == 1);
}
static void *fault_during_progress_actor(void *unused) {
    (void)unused; wait_on(0);
    uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT);
    REQUIRE(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    REQUIRE(mxuit_request(o, 1) == MXUIT_IO);
    locked(); REQUIRE(probe.sticky == MXUIT_IO && probe.faults == 1); unlocked(); set(1); return NULL;
}
static void fault_races_healthy_progress(void) {
    install(); uint64_t f = facade(), entry = direct(f, MXUIT_UI_CLEANUP);
    REQUIRE(mxuit_ui_leave(f, entry) == MXUIT_OK); probe.hold_progress = 1;
    pthread_t t; REQUIRE(pthread_create(&t, NULL, fault_during_progress_actor, NULL) == 0);
    REQUIRE(dispatch(process_fd, ALOOPER_EVENT_INPUT, dispatch_data) == 0);
    REQUIRE(pthread_join(t, NULL) == 0);
    REQUIRE(probe.progress == 2 && probe.faults == 1 && probe.entry_max == entry && probe.sticky == MXUIT_IO);
    REQUIRE(inspect().fault == MXUIT_IO && inspect().ui_entry_fenced == entry && probe.drains == 0);
    REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_IO);
}
static void *held_ui(void *unused) {
    (void)unused; install(); set(7); wait_on(8);
    callback(); set(9); wait_on(10); /* Platform-return tail, before another dispatch. */
    callback(); set(11); return NULL;
}
static void all_native_tails(void) {
    probe.hold_native = 1; pthread_t t; REQUIRE(pthread_create(&t, NULL, held_ui, NULL) == 0); wait_on(7);
    uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT);
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK && mxuit_request(o, 1) == MXUIT_OK); set(8); wait_on(2);
    uint64_t entry = inspect().active_entry_serial; REQUIRE(entry != 0);
    REQUIRE(mxuit_consumer_joined(o) == MXUIT_OK);
    REQUIRE(mxuit_try_reclaim(o) == MXUIT_BUSY && mxuit_facade_try_reclaim(f) == MXUIT_BUSY);
    REQUIRE(mxuit_ui_validate(f, entry) == MXUIT_WRONG_THREAD && mxuit_ui_leave(f, entry) == MXUIT_WRONG_THREAD);
    REQUIRE(mxuit_callback(process_fd, 1, 1) == MXUIT_WRONG_THREAD);
    set(3); wait_on(4);
    REQUIRE(inspect().active_entry_serial == 0 && inspect().completing == 1 && mxuit_try_reclaim(o) == MXUIT_BUSY);
    set(5); wait_on(9);
    REQUIRE(inspect().callback_active == 0 && inspect().completing == 0 && mxuit_try_reclaim(o) == MXUIT_BUSY);
    REQUIRE(inspect().ui_entry_fenced == 0 && inspect().fenced_epoch == 0);
    set(10); wait_on(11); REQUIRE(pthread_join(t, NULL) == 0);
    REQUIRE(mxuit_try_reclaim(o) == MXUIT_OK && mxuit_facade_try_reclaim(f) == MXUIT_OK); idle();
}
static void all_bits_entry_fence(void) {
    install(); uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT); probe.skip_entries = 1;
    REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK && mxuit_request(o, 1) == MXUIT_OK); callback(); callback();
    REQUIRE(mxuit_test_set_ui_entry_issued(UINT64_MAX - 1) == MXUIT_OK);
    uint64_t lease = direct(f, MXUIT_UI_CLEANUP); REQUIRE(lease == UINT64_MAX);
    REQUIRE(owner_state(o).last_entry_serial == UINT64_MAX && mxuit_try_reclaim(o) == MXUIT_BUSY);
    REQUIRE(mxuit_ui_leave(f, lease) == MXUIT_OK && mxuit_try_reclaim(o) == MXUIT_BUSY);
    callback(); REQUIRE(probe.entry_max == UINT64_MAX && inspect().ui_entry_fenced == UINT64_MAX);
    REQUIRE(mxuit_try_reclaim(o) == MXUIT_OK && mxuit_facade_try_reclaim(f) == MXUIT_OK); idle();
}
static void *fault_active_actor(void *argument) {
    uint64_t o = *(uint64_t *)argument;
    REQUIRE(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    REQUIRE(mxuit_request(o, 1) == MXUIT_IO); return NULL;
}
static void active_entry_fault_unwinds(void) {
    install(); uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT), lease = direct(f, MXUIT_UI_INGRESS);
    pthread_t t; REQUIRE(pthread_create(&t, NULL, fault_active_actor, &o) == 0); REQUIRE(pthread_join(t, NULL) == 0);
    REQUIRE(mxuit_callback(process_fd, 1, 1) == MXUIT_BUSY);
    REQUIRE(mxuit_ui_validate(f, lease) == MXUIT_IO && inspect().active_entry_serial == lease);
    REQUIRE(mxuit_ui_leave(f, lease) == MXUIT_IO && inspect().active_entry_serial == 0);
    REQUIRE(mxuit_callback(process_fd, 1, 0) == MXUIT_IO && inspect().ui_entry_fenced == 0);
    REQUIRE(probe.faults == 1 && probe.progress == 1 && mxuit_try_reclaim(o) == MXUIT_IO);
    REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_IO && inspect().occupied_facades == 1);
}
static void lost_wake_registration_orders(void) {
    install();
    for (int order = 0; order < 3; ++order) {
        uint64_t f = facade(), o = endpoint(f, MXUIT_ATTEMPT);
        REQUIRE(mxuit_facade_begin_close(f) == MXUIT_OK && mxuit_request(o, 1) == MXUIT_OK); callback();
        locked(); uint64_t seq = probe.sequence[0]; unlocked();
        REQUIRE(mxuit_try_reclaim(o) == MXUIT_BUSY);
        if (order == 0) callback(); /* fence before waiter registration */
        locked(); int registered = probe.sequence[0] == seq; if (registered) probe.observing[0] = 1; unlocked();
        if (order == 0) REQUIRE(!registered);
        if (order == 1) callback(); /* registered waiter sees fence signal */
        if (order == 2) callback(); /* fence between registration and reclaim retry */
        REQUIRE(mxuit_try_reclaim(o) == MXUIT_OK);
        locked(); REQUIRE(probe.sequence[0] > seq); probe.observing[0] = 0; unlocked();
        REQUIRE(mxuit_facade_try_reclaim(f) == MXUIT_OK); idle();
    }
    REQUIRE(probe.faults == 0 && inspect().occupied == 0 && inspect().occupied_facades == 0);
}
struct test { const char *name; void (*body)(void); };
static const struct test tests[] = {
    {"exact_active_drain_matrix", exact_active_drain_matrix},
    {"nested_reject_before_read", nested_reject_before_read},
    {"completion_cleanup_needs_new_fence", completion_cleanup_needs_new_fence},
    {"terminal_capacity_retry", terminal_capacity_retry},
    {"full_reuse_during_progress", full_reuse_during_progress},
    {"concurrent_fault_fanout", concurrent_fault_fanout},
    {"fault_races_healthy_progress", fault_races_healthy_progress},
    {"all_native_tails", all_native_tails},
    {"all_bits_entry_fence", all_bits_entry_fence},
    {"active_entry_fault_unwinds", active_entry_fault_unwinds},
    {"lost_wake_registration_orders", lost_wake_registration_orders},
};
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (strcmp(argv[1], "--list") == 0) { for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) puts(tests[i].name); return 0; }
    for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) if (strcmp(argv[1], tests[i].name) == 0) {
        tests[i].body(); printf("MXUIT_REVIEW_PASS %s assertions=%" PRIu64 "\n", tests[i].name, atomic_load_explicit(&assertions, memory_order_relaxed)); return 0;
    }
    return 2;
}
