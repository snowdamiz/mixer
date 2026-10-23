#define _POSIX_C_SOURCE 200809L
#include "../internal.h"
#include <errno.h>
#include <inttypes.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static _Atomic uint64_t checks;
static void die(const char *expression, int line) {
    fprintf(stderr, "FAIL line %d: %s\n", line, expression); exit(1);
}
#define CHECK(expression) do { atomic_fetch_add_explicit(&checks, 1, memory_order_relaxed); \
    if (!(expression)) die(#expression, __LINE__); } while (0)
static int registered_fd = -1, fail_registration;
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    int ready, stop, hold_drain, drain_entered, release_drain;
    int hold_tail, tail_entered, release_tail, reenter, request_again;
    int fail_present, fail_retire, unknown_result, fail_fence, join_in_complete;
    uint64_t drains, completions, presents, retires, cycles;
    int32_t last_result, nested_status, next_status;
    uint32_t last_kind;
} script = { .lock = PTHREAD_MUTEX_INITIALIZER, .changed = PTHREAD_COND_INITIALIZER };

int32_t mxuit_platform_register(int fd) {
    if (fail_registration) return MXUIT_IO;
    CHECK(registered_fd == -1); registered_fd = fd; return MXUIT_OK;
}
static struct mxuit_snapshot inspect(void) {
    struct mxuit_snapshot value; CHECK(mxuit_inspect(&value) == MXUIT_OK); return value;
}
static struct mxuit_owner_snapshot inspect_owner(uint64_t owner) {
    struct mxuit_owner_snapshot value;
    CHECK(mxuit_inspect_owner(owner, &value) == MXUIT_OK); return value;
}
static uint64_t acquire(void) {
    uint64_t owner = 0; CHECK(mxuit_acquire(&owner) == MXUIT_OK); CHECK(owner != 0); return owner;
}
static void install(void) { CHECK(mxuit_install() == MXUIT_OK); CHECK(mxuit_install() == MXUIT_OK); }
static struct timespec deadline(void) {
    struct timespec value; CHECK(clock_gettime(CLOCK_REALTIME, &value) == 0); value.tv_sec += 5; return value;
}
static void await_flag(int *flag) {
    struct timespec limit = deadline(); pthread_mutex_lock(&script.lock);
    while (!*flag) CHECK(pthread_cond_timedwait(&script.changed, &script.lock, &limit) == 0);
    pthread_mutex_unlock(&script.lock);
}
static void release_flag(int *flag) {
    pthread_mutex_lock(&script.lock); *flag = 1; pthread_cond_broadcast(&script.changed); pthread_mutex_unlock(&script.lock);
}
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    CHECK(owner != 0 && waiter != 0); CHECK(kind == MXUIT_PRESENT || kind == MXUIT_RETIRE);
    CHECK(inspect().active_helpers == 1);
    pthread_mutex_lock(&script.lock);
    ++script.drains; if (kind == MXUIT_PRESENT) ++script.presents; else ++script.retires;
    script.drain_entered = 1; pthread_cond_broadcast(&script.changed);
    int reenter = script.reenter;
    int failed = kind == MXUIT_PRESENT ? script.fail_present : script.fail_retire;
    int unknown = script.unknown_result;
    if (script.hold_drain) {
        struct timespec limit = deadline();
        while (!script.release_drain) CHECK(pthread_cond_timedwait(&script.changed, &script.lock, &limit) == 0);
    }
    pthread_mutex_unlock(&script.lock);
    if (reenter) {
        struct mxuit_snapshot before = inspect();
        int32_t result = mxuit_callback(registered_fd, 1, 0);
        CHECK(result == MXUIT_BUSY); CHECK(inspect().fenced_epoch == before.fenced_epoch);
        pthread_mutex_lock(&script.lock); script.nested_status = result; pthread_mutex_unlock(&script.lock);
    }
    return unknown ? 900 : failed ? MXUIT_DRAIN_FAILED : MXUIT_DRAIN_OK;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    struct mxuit_owner_snapshot value = inspect_owner(owner);
    CHECK(value.active_helper == 0 && value.completing == 1);
    pthread_mutex_lock(&script.lock);
    ++script.completions; script.last_result = result; script.last_kind = kind;
    int again = script.request_again; script.request_again = 0;
    int fail_fence = script.fail_fence;
    int join_in_complete = script.join_in_complete;
    pthread_cond_broadcast(&script.changed); pthread_mutex_unlock(&script.lock);
    if (again) {
        CHECK(waiter < UINT64_MAX);
        int32_t next = mxuit_request(owner, waiter + 1);
        CHECK(next == MXUIT_OK);
        pthread_mutex_lock(&script.lock); script.next_status = next; pthread_mutex_unlock(&script.lock);
    }
    if (fail_fence) CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EIO, 1) == MXUIT_OK);
    if (join_in_complete) {
        CHECK(kind == MXUIT_RETIRE);
        CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
        CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    }
}
/* This POSIX driver models serialized platform callback invocation. The tail
 * hold is AFTER core's last owner access and completion return, but BEFORE this
 * callback wrapper has returned to its event loop. It is intentionally outside
 * all transport locks and absent from the Android product source. */
static int32_t pump(int timeout) {
    struct pollfd fd = {registered_fd, POLLIN, 0};
    int status = poll(&fd, 1, timeout);
    if (status == 0) return MXUIT_UNAVAILABLE;
    CHECK(status == 1);
    int32_t result = mxuit_callback(registered_fd, (fd.revents & POLLIN) != 0,
        (fd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0);
    pthread_mutex_lock(&script.lock);
    if (script.hold_tail && !script.tail_entered) {
        script.tail_entered = 1; pthread_cond_broadcast(&script.changed);
        struct timespec limit = deadline();
        while (!script.release_tail) CHECK(pthread_cond_timedwait(&script.changed, &script.lock, &limit) == 0);
    }
    ++script.cycles; pthread_cond_broadcast(&script.changed); pthread_mutex_unlock(&script.lock);
    return result;
}
static void *ui_loop(void *unused) {
    (void)unused; install(); release_flag(&script.ready);
    for (;;) {
        pthread_mutex_lock(&script.lock); int stop = script.stop; pthread_mutex_unlock(&script.lock);
        if (stop) break;
        int32_t result = pump(20);
        CHECK(result == MXUIT_OK || result == MXUIT_UNAVAILABLE);
    }
    return NULL;
}
static pthread_t start_ui(void) {
    pthread_t thread; CHECK(pthread_create(&thread, NULL, ui_loop, NULL) == 0); await_flag(&script.ready); return thread;
}
static void stop_ui(pthread_t thread) { release_flag(&script.stop); CHECK(pthread_join(thread, NULL) == 0); }
static void await_retired(uint64_t owner) {
    struct timespec pause = {0, 1000000};
    for (unsigned int i = 0; i < 5000; ++i) {
        if (inspect_owner(owner).retirement_done) return;
        (void)nanosleep(&pause, NULL);
    }
    CHECK(0);
}
static void await_fence(uint64_t owner) {
    struct timespec pause = {0, 1000000};
    for (unsigned int i = 0; i < 5000; ++i) {
        if (inspect().fenced_epoch >= inspect_owner(owner).last_hook_epoch) return;
        (void)nanosleep(&pause, NULL);
    }
    CHECK(0);
}
static void fence_and_reclaim(uint64_t owner) {
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(pump(0) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_OK);
}

static void capacity(void) {
    uint64_t value = 99; CHECK(mxuit_acquire(&value) == MXUIT_UNAVAILABLE && value == 0);
    CHECK(mxuit_acquire(NULL) == MXUIT_INVALID); install();
    uint64_t owners[MXUIT_OWNER_CAPACITY];
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) { owners[i] = acquire(); CHECK(owners[i] == i + 1); }
    CHECK(mxuit_acquire(&value) == MXUIT_CAPACITY && value == 0);
    CHECK(mxuit_request(0, 1) == MXUIT_STALE); CHECK(mxuit_request(900, 1) == MXUIT_STALE);
    CHECK(mxuit_request(owners[0], 0) == MXUIT_INVALID); CHECK(mxuit_hint(900) == MXUIT_STALE);
    CHECK(mxuit_try_reclaim(owners[0]) == MXUIT_BUSY);
    struct mxuit_snapshot stats = inspect();
    CHECK(stats.occupied == 16 && stats.maximum_occupied == 16);
    CHECK(stats.owned_fds == 2 && stats.registration == 1 && stats.callbacks == 0);
}
static void *flood(void *argument) {
    uint64_t owner = *(uint64_t *)argument;
    for (unsigned int i = 0; i < 10000; ++i) CHECK(mxuit_hint(owner) == MXUIT_OK);
    return NULL;
}
static void coalescing(void) {
    install(); uint64_t owners[16]; pthread_t threads[8];
    for (size_t i = 0; i < 16; ++i) owners[i] = acquire();
    for (size_t i = 0; i < 8; ++i) CHECK(pthread_create(&threads[i], NULL, flood, &owners[i]) == 0);
    for (size_t i = 0; i < 8; ++i) CHECK(pthread_join(threads[i], NULL) == 0);
    CHECK(inspect().pending_pipe_hint == 0); CHECK(pump(0) == MXUIT_UNAVAILABLE);
    for (size_t i = 0; i < 16; ++i) {
        CHECK(mxuit_request(owners[i], 1) == MXUIT_OK); CHECK(mxuit_request(owners[i], 2) == MXUIT_BUSY);
        CHECK(inspect_owner(owners[i]).hint == 1);
    }
    CHECK(inspect().pending_pipe_hint == 1); CHECK(pump(0) == MXUIT_OK);
    struct mxuit_snapshot stats = inspect();
    CHECK(stats.drains == 16 && stats.completions == 16 && stats.maximum_waiters == 16);
    CHECK(stats.maximum_active_helpers == 1 && stats.waiters == 0);
    CHECK(pump(0) == MXUIT_OK); CHECK(pump(0) == MXUIT_UNAVAILABLE);
    CHECK(inspect().callbacks == 2); CHECK(inspect().hints == 80000);
}
static void successor_from_complete(void) {
    install(); uint64_t owner = acquire(); script.request_again = 1;
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(inspect().drains == 1 && inspect().waiters == 1);
    CHECK(pump(0) == MXUIT_OK); CHECK(inspect().drains == 2);
    CHECK(mxuit_request(owner, 2) == MXUIT_STALE);
    CHECK(pump(0) == MXUIT_OK); CHECK(pump(0) == MXUIT_UNAVAILABLE);
}
static void close_before_claim(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_begin_close(owner) == MXUIT_OK);
    CHECK(mxuit_hint(owner) == MXUIT_CLOSED); CHECK(mxuit_consumer_joined(owner) == MXUIT_BUSY);
    CHECK(pump(0) == MXUIT_OK); CHECK(script.retires == 1 && script.presents == 0);
    CHECK(script.last_kind == MXUIT_RETIRE && script.last_result == MXUIT_DRAIN_OK);
    CHECK(mxuit_request(owner, 2) == MXUIT_CLOSED); fence_and_reclaim(owner);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_STALE); CHECK(mxuit_hint(owner) == MXUIT_STALE);
    CHECK(acquire() != owner); CHECK(inspect().owned_fds == 2 && inspect().registration == 1);
}
static void close_during_helper(void) {
    script.hold_drain = 1; pthread_t ui = start_ui(); uint64_t owner = acquire();
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); await_flag(&script.drain_entered);
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 2) == MXUIT_BUSY);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_BUSY); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    release_flag(&script.release_drain);
    struct timespec pause = {0, 1000000};
    for (unsigned int i = 0; i < 5000; ++i) {
        struct mxuit_owner_snapshot value = inspect_owner(owner);
        if (!value.active_helper && !value.completing && !value.waiter) break;
        (void)nanosleep(&pause, NULL); CHECK(i < 4999);
    }
    pthread_mutex_lock(&script.lock);
    CHECK(script.last_result == MXUIT_DRAIN_CLOSE_PENDING); script.hold_drain = 0;
    pthread_mutex_unlock(&script.lock);
    CHECK(mxuit_request(owner, 2) == MXUIT_OK); await_retired(owner);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK); await_fence(owner); stop_ui(ui);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_OK);
    CHECK(script.presents == 1 && script.retires == 1);
}
static void callback_tail(void) {
    script.hold_tail = 1; pthread_t ui = start_ui(); uint64_t owner = acquire();
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    await_flag(&script.tail_entered);
    CHECK(script.drains == 1 && script.completions == 1);
    struct mxuit_snapshot stats = inspect();
    CHECK(stats.active_helpers == 0 && stats.completing == 0 && stats.callback_active == 0);
    CHECK(stats.callback_epoch == 1 && stats.fenced_epoch == 0);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    uint64_t other[15]; for (size_t i = 0; i < 15; ++i) other[i] = acquire();
    uint64_t value = 0; CHECK(mxuit_acquire(&value) == MXUIT_CAPACITY);
    CHECK(mxuit_callback(registered_fd, 1, 0) == MXUIT_WRONG_THREAD);
    CHECK(inspect().fenced_epoch == 0); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    release_flag(&script.release_tail);
    struct timespec pause = {0, 1000000};
    for (unsigned int i = 0; i < 5000 && inspect().fenced_epoch == 0; ++i) (void)nanosleep(&pause, NULL);
    stop_ui(ui); CHECK(inspect().fenced_epoch == 1);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_OK); uint64_t fresh = acquire(); CHECK(fresh > other[14]);
    CHECK(mxuit_request(owner, 2) == MXUIT_STALE); CHECK(inspect_owner(fresh).last_waiter == 0);
}
static void reentrant(void) {
    install(); uint64_t owner = acquire(); script.reenter = 1;
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(script.nested_status == MXUIT_BUSY); CHECK(inspect().fenced_epoch == 0);
    CHECK(pump(0) == MXUIT_OK); CHECK(inspect().fenced_epoch == 1);
}
static void stalled_consumer(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_begin_close(owner) == MXUIT_OK);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_BUSY); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(pump(0) == MXUIT_UNAVAILABLE); CHECK(inspect().occupied == 1);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY); /* actual Task join assertion still absent */
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK); CHECK(mxuit_try_reclaim(owner) == MXUIT_OK);
}
static void failed_retirement(void) {
    install(); uint64_t owner = acquire(); script.fail_retire = 1;
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(mxuit_consumer_joined(owner) == MXUIT_OK); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(mxuit_request(owner, 2) == MXUIT_CLOSED); CHECK(inspect().occupied == 1);
}
static void join_during_completion(void) {
    install(); uint64_t owner = acquire(); script.join_in_complete = 1;
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_OK); CHECK(inspect_owner(owner).consumer_joined == 1);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(pump(0) == MXUIT_OK); CHECK(mxuit_try_reclaim(owner) == MXUIT_OK);
}
static void failed_present(void) {
    install(); uint64_t owner = acquire(); script.fail_present = 1;
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(script.last_result == MXUIT_DRAIN_FAILED); CHECK(inspect_owner(owner).closing == 1);
    CHECK(mxuit_request(owner, 2) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(script.retires == 1); fence_and_reclaim(owner);
}
static void write_failure(int error, uint32_t count) {
    install(); uint64_t owner = acquire();
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, error, count) == MXUIT_OK);
    CHECK(mxuit_request(owner, 1) == MXUIT_IO); CHECK(mxuit_try_reclaim(owner) == MXUIT_IO);
    struct mxuit_snapshot stats = inspect(); CHECK(stats.occupied == 1 && stats.waiters == 1);
    CHECK(stats.callbacks == 0 && stats.fault == MXUIT_IO && stats.owned_fds == 2);
}
static void write_eio(void) { write_failure(EIO, 1); }
static void write_eagain(void) { write_failure(EAGAIN, 1); }
static void write_eintr_exhausted(void) { write_failure(EINTR, 8); }
static void read_failure(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_READ, EIO, 1) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_IO); CHECK(inspect().callback_epoch == 0);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_IO); CHECK(inspect().waiters == 1);
}
static void fence_failure(void) {
    install(); uint64_t owner = acquire(); script.fail_fence = 1;
    CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_IO); CHECK(mxuit_consumer_joined(owner) == MXUIT_OK);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_IO); CHECK(inspect().fenced_epoch == 0);
    CHECK(inspect().occupied == 1 && inspect().owned_fds == 2);
}
static void eintr_recovery(void) {
    install(); uint64_t owner = acquire();
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_WRITE, EINTR, 2) == MXUIT_OK);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(mxuit_test_fail_syscall(MXUIT_TEST_READ, EINTR, 2) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_OK); CHECK(script.completions == 1 && inspect().fault == 0);
}
static void init_failure(uint32_t operation) {
    CHECK(mxuit_test_fail_syscall(operation, EMFILE, 1) == MXUIT_OK);
    CHECK(mxuit_install() == MXUIT_IO); CHECK(mxuit_install() == MXUIT_IO);
    uint64_t owner = 99; CHECK(mxuit_acquire(&owner) == MXUIT_IO && owner == 0);
    CHECK(inspect().owned_fds == 0 && inspect().registration == 0 && inspect().occupied == 0);
}
static void pipe_failure(void) { init_failure(MXUIT_TEST_PIPE); }
static void fcntl_failure(void) { init_failure(MXUIT_TEST_FCNTL); }
static void register_failure(void) {
    fail_registration = 1; CHECK(mxuit_install() == MXUIT_IO);
    CHECK(inspect().owned_fds == 0 && inspect().registration == 0);
    uint64_t owner; CHECK(mxuit_acquire(&owner) == MXUIT_IO);
}
static void owner_exhaustion(void) {
    install(); CHECK(mxuit_test_set_issued(UINT64_MAX - 1) == MXUIT_OK);
    CHECK(acquire() == UINT64_MAX); uint64_t owner = 99;
    CHECK(mxuit_acquire(&owner) == MXUIT_EXHAUSTED && owner == 0); CHECK(inspect().owners_issued == UINT64_MAX);
}
static void waiter_exhaustion(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_request(owner, UINT64_MAX) == MXUIT_OK);
    CHECK(pump(0) == MXUIT_OK); CHECK(mxuit_begin_close(owner) == MXUIT_OK);
    CHECK(mxuit_request(owner, 1) == MXUIT_EXHAUSTED); CHECK(mxuit_try_reclaim(owner) == MXUIT_BUSY);
    CHECK(inspect_owner(owner).last_waiter == UINT64_MAX);
}
static void epoch_exhaustion(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_test_set_epoch(UINT64_MAX) == MXUIT_OK);
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_EXHAUSTED);
    CHECK(inspect().callback_epoch == UINT64_MAX && inspect().fault == MXUIT_EXHAUSTED);
    CHECK(mxuit_try_reclaim(owner) == MXUIT_EXHAUSTED && inspect().occupied == 1);
}
static void wrong_descriptor(void) {
    install(); uint64_t owner = acquire(); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
    CHECK(mxuit_callback(registered_fd + 1, 1, 0) == MXUIT_INVALID);
    CHECK(inspect().callback_epoch == 0 && inspect().pending_pipe_hint == 1);
    CHECK(pump(0) == MXUIT_OK);
}
static void unknown_hook(void) {
    install(); uint64_t owner = acquire(); script.unknown_result = 1;
    CHECK(mxuit_request(owner, 1) == MXUIT_OK); CHECK(pump(0) == MXUIT_OK);
    CHECK(script.last_result == MXUIT_DRAIN_FAILED && inspect_owner(owner).closing == 1);
}
static void repeated_retirement(void) {
    install(); uint64_t previous = 0;
    for (unsigned int i = 0; i < 100; ++i) {
        uint64_t owner = acquire(); CHECK(owner > previous); previous = owner;
        CHECK(mxuit_begin_close(owner) == MXUIT_OK); CHECK(mxuit_request(owner, 1) == MXUIT_OK);
        CHECK(pump(0) == MXUIT_OK); fence_and_reclaim(owner); CHECK(mxuit_hint(owner) == MXUIT_STALE);
    }
    struct mxuit_snapshot stats = inspect();
    CHECK(stats.occupied == 0 && stats.owners_issued == 100 && stats.maximum_occupied == 1);
    CHECK(stats.owned_fds == 2 && stats.registration == 1 && stats.callbacks == 200);
    CHECK(pump(0) == MXUIT_UNAVAILABLE);
}
struct test { const char *name; void (*run)(void); };
static const struct test tests[] = {
    {"capacity", capacity}, {"coalescing", coalescing}, {"successor_from_complete", successor_from_complete},
    {"close_before_claim", close_before_claim}, {"close_during_helper", close_during_helper},
    {"callback_tail", callback_tail}, {"reentrant", reentrant}, {"stalled_consumer", stalled_consumer},
    {"failed_retirement", failed_retirement}, {"join_during_completion", join_during_completion},
    {"failed_present", failed_present},
    {"write_eio", write_eio}, {"write_eagain", write_eagain}, {"write_eintr_exhausted", write_eintr_exhausted},
    {"read_failure", read_failure}, {"fence_failure", fence_failure}, {"eintr_recovery", eintr_recovery},
    {"pipe_failure", pipe_failure}, {"fcntl_failure", fcntl_failure}, {"register_failure", register_failure},
    {"owner_exhaustion", owner_exhaustion}, {"waiter_exhaustion", waiter_exhaustion},
    {"epoch_exhaustion", epoch_exhaustion}, {"wrong_descriptor", wrong_descriptor},
    {"unknown_hook", unknown_hook}, {"repeated_retirement", repeated_retirement},
};
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    if (strcmp(argv[1], "--list") == 0) {
        for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) puts(tests[i].name);
        return 0;
    }
    for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); ++i) {
        if (strcmp(argv[1], tests[i].name) != 0) continue;
        tests[i].run();
        printf("MXUIT_CASE_PASS %s checks=%" PRIu64 "\n", tests[i].name,
            atomic_load_explicit(&checks, memory_order_relaxed)); return 0;
    }
    return 2;
}
