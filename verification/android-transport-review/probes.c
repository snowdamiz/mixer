#define _POSIX_C_SOURCE 200809L
#include "../../native/android/signed-guest-ui/transport/internal.h"
#include <android/looper.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Original review probes. These execute the unchanged production wrapper and
 * core against a deliberately small test implementation of the NDK symbols.
 * This is a POSIX host driver, not Android Looper or Swift Task evidence. */
struct ALooper { int tag; };
static struct ALooper fake_looper = {17};
static int no_looper, reject_add, adds, acquires, releases, registered_fd = -1;
static ALooper_callbackFunc saved_callback;
static void *saved_data;
static _Atomic uint64_t checks;
static void fail(const char *condition, int line) {
    fprintf(stderr, "REVIEW_FAIL line=%d %s\n", line, condition); exit(1);
}
#define REQUIRE(condition) do { \
    atomic_fetch_add_explicit(&checks, 1, memory_order_relaxed); \
    if (!(condition)) fail(#condition, __LINE__); \
} while (0)

ALooper *ALooper_forThread(void) { return no_looper ? NULL : &fake_looper; }
void ALooper_acquire(ALooper *looper) { REQUIRE(looper == &fake_looper); ++acquires; }
void ALooper_release(ALooper *looper) { REQUIRE(looper == &fake_looper); ++releases; }
int ALooper_addFd(ALooper *looper, int fd, int ident, int events,
                 ALooper_callbackFunc callback, void *data) {
    REQUIRE(looper == &fake_looper);
    REQUIRE(ident == ALOOPER_POLL_CALLBACK && events == ALOOPER_EVENT_INPUT);
    REQUIRE(callback != NULL && data != NULL && fd >= 0);
    ++adds;
    if (reject_add) return -1;
    REQUIRE(registered_fd == -1);
    registered_fd = fd; saved_callback = callback; saved_data = data;
    return 1;
}
static struct mxuit_snapshot snapshot(void) {
    struct mxuit_snapshot value; REQUIRE(mxuit_inspect(&value) == MXUIT_OK); return value;
}
static struct mxuit_owner_snapshot owner_snapshot(uint64_t owner) {
    struct mxuit_owner_snapshot value;
    REQUIRE(mxuit_inspect_owner(owner, &value) == MXUIT_OK); return value;
}
static uint64_t acquire_owner(void) {
    uint64_t owner = 0; REQUIRE(mxuit_acquire(&owner) == MXUIT_OK); REQUIRE(owner != 0); return owner;
}
static void install(void) {
    REQUIRE(mxuit_install() == MXUIT_OK); REQUIRE(mxuit_install() == MXUIT_OK);
    REQUIRE(adds == 1 && acquires == 1 && releases == 0);
    REQUIRE((fcntl(registered_fd, F_GETFL) & O_NONBLOCK) != 0);
    REQUIRE((fcntl(registered_fd, F_GETFD) & FD_CLOEXEC) != 0);
}
static int pump(void) {
    struct pollfd pending = {registered_fd, POLLIN, 0};
    int status = poll(&pending, 1, 0);
    REQUIRE(status == 0 || status == 1);
    if (status == 0) return 0;
    REQUIRE((pending.revents & POLLIN) != 0);
    REQUIRE(saved_callback(registered_fd, ALOOPER_EVENT_INPUT, saved_data) == 1);
    return 1;
}
static void retire(uint64_t owner, uint64_t waiter) {
    REQUIRE(mxuit_begin_close(owner) == MXUIT_OK);
    REQUIRE(mxuit_request(owner, waiter) == MXUIT_OK);
    REQUIRE(pump() == 1); REQUIRE(owner_snapshot(owner).retirement_done == 1);
    REQUIRE(mxuit_consumer_joined(owner) == MXUIT_OK);
    REQUIRE(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    REQUIRE(pump() == 1); REQUIRE(mxuit_try_reclaim(owner) == MXUIT_OK);
}

enum scenario { ORDINARY, BATON, RECYCLE, ROUNDS, JOIN_TAIL };
static enum scenario scenario;
static uint64_t first, second, replacement, calls, completions, retires;
static uint64_t owner_calls[MXUIT_OWNER_CAPACITY];
static uint64_t round_owners[MXUIT_OWNER_CAPACITY];
static pthread_mutex_t review_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static int completion_entered, worker_finished;
static pthread_t main_thread;
static struct timespec limit(void) {
    struct timespec result; REQUIRE(clock_gettime(CLOCK_REALTIME, &result) == 0);
    result.tv_sec += 5; return result;
}
static void wait_for(int *condition) {
    struct timespec deadline = limit(); REQUIRE(pthread_mutex_lock(&review_lock) == 0);
    while (!*condition) REQUIRE(pthread_cond_timedwait(&changed, &review_lock, &deadline) == 0);
    REQUIRE(pthread_mutex_unlock(&review_lock) == 0);
}
static void signal_flag(int *condition) {
    REQUIRE(pthread_mutex_lock(&review_lock) == 0); *condition = 1;
    REQUIRE(pthread_cond_broadcast(&changed) == 0); REQUIRE(pthread_mutex_unlock(&review_lock) == 0);
}
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    REQUIRE(pthread_equal(main_thread, pthread_self()));
    REQUIRE(owner != 0 && waiter != 0);
    struct mxuit_snapshot value = snapshot();
    REQUIRE(value.active_helpers == 1 && value.completing == 0 && value.callback_active == 1);
    REQUIRE(owner_snapshot(owner).active_helper == 1);
    ++calls; if (kind == MXUIT_RETIRE) ++retires;
    REQUIRE(kind == MXUIT_PRESENT || kind == MXUIT_RETIRE);
    /* A nested platform callback must neither read the byte nor fence the
     * outer invocation, including when another waiter already rang the pipe. */
    uint64_t fenced = value.fenced_epoch;
    REQUIRE(saved_callback(registered_fd, ALOOPER_EVENT_INPUT, saved_data) == 1);
    REQUIRE(snapshot().fenced_epoch == fenced && snapshot().drains == calls);
    if (scenario == ROUNDS) {
        size_t slot = 0;
        while (slot < MXUIT_OWNER_CAPACITY && round_owners[slot] != owner) ++slot;
        REQUIRE(slot < MXUIT_OWNER_CAPACITY);
        ++owner_calls[slot]; REQUIRE(owner_calls[slot] == waiter);
        REQUIRE(kind == (waiter == 65 ? MXUIT_RETIRE : MXUIT_PRESENT));
    }
    return MXUIT_DRAIN_OK;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    ++completions;
    REQUIRE(result == MXUIT_DRAIN_OK);
    struct mxuit_owner_snapshot value = owner_snapshot(owner);
    REQUIRE(value.active_helper == 0 && value.completing == 1 && value.waiter == 0);
    REQUIRE(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    if ((scenario == BATON && owner == first && waiter == 1) || scenario == JOIN_TAIL) {
        signal_flag(&completion_entered); wait_for(&worker_finished);
        REQUIRE(owner_snapshot(owner).completing == 1);
        REQUIRE(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    }
    if (scenario == RECYCLE && owner == first) {
        REQUIRE(mxuit_try_reclaim(second) == MXUIT_OK);
        replacement = acquire_owner(); REQUIRE(replacement > second);
        REQUIRE(mxuit_request(replacement, 1) == MXUIT_OK);
        REQUIRE(mxuit_hint(second) == MXUIT_STALE);
        REQUIRE(mxuit_begin_close(second) == MXUIT_STALE);
        REQUIRE(mxuit_consumer_joined(second) == MXUIT_STALE);
        REQUIRE(mxuit_request(second, UINT64_MAX) == MXUIT_STALE);
    }
    if (scenario == ROUNDS && kind == MXUIT_PRESENT) {
        if (waiter == 64) REQUIRE(mxuit_begin_close(owner) == MXUIT_OK);
        REQUIRE(mxuit_request(owner, waiter + 1) == MXUIT_OK);
        REQUIRE(mxuit_request(owner, waiter + 2) == MXUIT_BUSY);
    }
}

static void *baton_worker(void *unused) {
    (void)unused; wait_for(&completion_entered);
    REQUIRE(mxuit_install() == MXUIT_WRONG_THREAD);
    REQUIRE(mxuit_request(first, 2) == MXUIT_OK);
    REQUIRE(mxuit_begin_close(first) == MXUIT_OK);
    REQUIRE(mxuit_request(first, 3) == MXUIT_BUSY);
    REQUIRE(mxuit_consumer_joined(first) == MXUIT_BUSY);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_BUSY);
    REQUIRE(owner_snapshot(first).waiter == 1 && owner_snapshot(first).completing == 1);
    uint64_t epoch = snapshot().fenced_epoch;
    REQUIRE(saved_callback(registered_fd, ALOOPER_EVENT_INPUT, saved_data) == 1);
    REQUIRE(snapshot().fenced_epoch == epoch);
    signal_flag(&worker_finished); return NULL;
}
static void completing_baton(void) {
    install(); first = acquire_owner(); scenario = BATON;
    pthread_t worker; REQUIRE(pthread_create(&worker, NULL, baton_worker, NULL) == 0);
    REQUIRE(mxuit_request(first, 1) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(pthread_join(worker, NULL) == 0);
    REQUIRE(calls == 1 && completions == 1 && retires == 0);
    REQUIRE(owner_snapshot(first).closing == 1 && owner_snapshot(first).waiter == 1);
    REQUIRE(pump() == 1); REQUIRE(calls == 2 && retires == 1);
    REQUIRE(mxuit_consumer_joined(first) == MXUIT_OK);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_BUSY); REQUIRE(pump() == 1);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_OK); REQUIRE(pump() == 0);
}
static void slot_reuse_during_scan(void) {
    install(); first = acquire_owner(); second = acquire_owner();
    REQUIRE(mxuit_begin_close(second) == MXUIT_OK);
    REQUIRE(mxuit_request(second, 1) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(mxuit_consumer_joined(second) == MXUIT_OK);
    REQUIRE(mxuit_try_reclaim(second) == MXUIT_BUSY);
    scenario = RECYCLE;
    REQUIRE(mxuit_request(first, 1) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(replacement != 0 && calls == 3 && completions == 3);
    REQUIRE(owner_snapshot(replacement).last_hook_epoch == 2);
    REQUIRE(owner_snapshot(replacement).last_waiter == 1);
    REQUIRE(snapshot().occupied == 2 && snapshot().maximum_active_helpers == 1);
    scenario = ORDINARY; REQUIRE(pump() == 1); REQUIRE(pump() == 0);
    retire(first, 2); retire(replacement, 2);
    REQUIRE(snapshot().occupied == 0);
}
static void many_rounds(void) {
    install(); scenario = ROUNDS;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        round_owners[i] = acquire_owner(); REQUIRE(mxuit_request(round_owners[i], 1) == MXUIT_OK);
    }
    for (uint64_t round = 1; round <= 65; ++round) {
        REQUIRE(pump() == 1);
        REQUIRE(calls == round * MXUIT_OWNER_CAPACITY && completions == calls);
        for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) REQUIRE(owner_calls[i] == round);
        REQUIRE(snapshot().maximum_active_helpers == 1);
        REQUIRE(snapshot().maximum_waiters == MXUIT_OWNER_CAPACITY);
    }
    REQUIRE(retires == 16 && snapshot().waiters == 0);
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        REQUIRE(mxuit_consumer_joined(round_owners[i]) == MXUIT_OK);
        REQUIRE(mxuit_try_reclaim(round_owners[i]) == MXUIT_BUSY);
    }
    uint64_t completed_before_fence = completions;
    REQUIRE(pump() == 1); REQUIRE(completions == completed_before_fence);
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i)
        REQUIRE(mxuit_try_reclaim(round_owners[i]) == MXUIT_OK);
    REQUIRE(pump() == 0 && snapshot().occupied == 0);
    REQUIRE(snapshot().callbacks == 66 && snapshot().owned_fds == 2 && adds == 1);
}
static void *joined_worker(void *unused) {
    (void)unused; wait_for(&completion_entered);
    REQUIRE(mxuit_consumer_joined(first) == MXUIT_OK);
    REQUIRE(owner_snapshot(first).retirement_done == 0);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_BUSY);
    uint64_t other[15];
    for (size_t i = 0; i < 15; ++i) other[i] = acquire_owner();
    REQUIRE(other[14] > other[0]);
    uint64_t rejected = 99; REQUIRE(mxuit_acquire(&rejected) == MXUIT_CAPACITY && rejected == 0);
    signal_flag(&worker_finished); return NULL;
}
static void join_before_completion_returns(void) {
    install(); first = acquire_owner(); scenario = JOIN_TAIL;
    pthread_t worker; REQUIRE(pthread_create(&worker, NULL, joined_worker, NULL) == 0);
    REQUIRE(mxuit_begin_close(first) == MXUIT_OK); REQUIRE(mxuit_request(first, 1) == MXUIT_OK);
    REQUIRE(pump() == 1); REQUIRE(pthread_join(worker, NULL) == 0);
    REQUIRE(owner_snapshot(first).consumer_joined == 1);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_BUSY);
    uint64_t completed_before_fence = completions;
    REQUIRE(pump() == 1); REQUIRE(completions == completed_before_fence);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_OK);
    REQUIRE(acquire_owner() == 17 && snapshot().occupied == 16);
}
static void registration_guards(void) {
    install(); first = acquire_owner(); REQUIRE(mxuit_request(first, 1) == MXUIT_OK);
    struct mxuit_snapshot before = snapshot();
    REQUIRE(saved_callback(registered_fd, ALOOPER_EVENT_INPUT, NULL) == 0);
    REQUIRE(saved_callback(registered_fd + 1, ALOOPER_EVENT_INPUT, saved_data) == 1);
    REQUIRE(snapshot().callback_epoch == before.callback_epoch && snapshot().waiters == 1);
    REQUIRE(pump() == 1); REQUIRE(pump() == 1); REQUIRE(pump() == 0);
    REQUIRE(saved_callback(registered_fd, ALOOPER_EVENT_ERROR, saved_data) == 0);
    REQUIRE(snapshot().fault == MXUIT_IO && snapshot().occupied == 1);
    REQUIRE(mxuit_begin_close(first) == MXUIT_IO);
    REQUIRE(mxuit_try_reclaim(first) == MXUIT_IO);
    REQUIRE(snapshot().registration == 1 && snapshot().owned_fds == 2);
    REQUIRE(adds == 1 && acquires == 1 && releases == 0);
}
static void register_absent(void) {
    no_looper = 1; REQUIRE(mxuit_install() == MXUIT_UNAVAILABLE);
    REQUIRE(mxuit_install() == MXUIT_UNAVAILABLE);
    uint64_t owner = 99; REQUIRE(mxuit_acquire(&owner) == MXUIT_UNAVAILABLE && owner == 0);
    REQUIRE(snapshot().owned_fds == 0 && snapshot().registration == 0);
    REQUIRE(adds == 0 && acquires == 0 && releases == 0);
}
static void register_rejected(void) {
    reject_add = 1; REQUIRE(mxuit_install() == MXUIT_IO);
    REQUIRE(mxuit_install() == MXUIT_IO);
    uint64_t owner = 99; REQUIRE(mxuit_acquire(&owner) == MXUIT_IO && owner == 0);
    REQUIRE(snapshot().owned_fds == 0 && snapshot().registration == 0);
    REQUIRE(adds == 1 && acquires == 1 && releases == 1);
}
static void stale_generation_storm(void) {
    install(); uint64_t previous = 0;
    for (uint64_t iteration = 1; iteration <= 256; ++iteration) {
        uint64_t owner = acquire_owner(); REQUIRE(owner == iteration && owner > previous);
        if (previous != 0) {
            REQUIRE(mxuit_request(previous, UINT64_MAX) == MXUIT_STALE);
            REQUIRE(mxuit_hint(previous) == MXUIT_STALE);
            REQUIRE(mxuit_begin_close(previous) == MXUIT_STALE);
            REQUIRE(mxuit_consumer_joined(previous) == MXUIT_STALE);
            REQUIRE(mxuit_try_reclaim(previous) == MXUIT_STALE);
            REQUIRE(owner_snapshot(owner).last_waiter == 0);
        }
        retire(owner, UINT64_MAX); previous = owner;
    }
    REQUIRE(snapshot().owners_issued == 256 && snapshot().occupied == 0);
    REQUIRE(snapshot().maximum_occupied == 1 && adds == 1 && acquires == 1);
    REQUIRE(snapshot().owned_fds == 2 && snapshot().callbacks == 512 && pump() == 0);
}
static void waiter_is_immediate_demand(void) {
    install(); first = acquire_owner();
    REQUIRE(mxuit_request(first, 1) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(mxuit_request(first, 2) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(mxuit_request(first, 3) == MXUIT_OK); REQUIRE(pump() == 1);
    REQUIRE(snapshot().hints == 0 && calls == 3 && completions == 3);
    REQUIRE(pump() == 1 && pump() == 0);
    retire(first, 4);
}
struct test { const char *name; void (*run)(void); };
static const struct test cases[] = {
    {"completing_baton", completing_baton}, {"slot_reuse_during_scan", slot_reuse_during_scan},
    {"many_rounds", many_rounds}, {"join_before_completion_returns", join_before_completion_returns},
    {"registration_guards", registration_guards}, {"register_absent", register_absent},
    {"register_rejected", register_rejected}, {"stale_generation_storm", stale_generation_storm},
    {"waiter_is_immediate_demand", waiter_is_immediate_demand}
};
int main(int argc, char **argv) {
    main_thread = pthread_self();
    if (argc != 2) return 2;
    if (strcmp(argv[1], "--list") == 0) {
        for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) puts(cases[i].name);
        return 0;
    }
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        if (strcmp(argv[1], cases[i].name) != 0) continue;
        cases[i].run();
        printf("ANDROID_TRANSPORT_REVIEW_PASS %s checks=%" PRIu64 "\n", cases[i].name,
               atomic_load_explicit(&checks, memory_order_relaxed));
        return 0;
    }
    return 2;
}
