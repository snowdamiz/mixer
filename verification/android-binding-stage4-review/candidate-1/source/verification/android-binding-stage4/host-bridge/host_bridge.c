#define _POSIX_C_SOURCE 200809L
#include "mixer_android_host_bridge.h"
#include "host_test.h"
#include "../../../native/android/signed-guest-ui/transport/internal.h"
#include "../../../native/android/signed-guest-ui/binding/include/mixer_ui_binding.h"
#include <pthread.h>
#include <poll.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* This object is deliberately fixed, never an injected implementation. Its
 * actual host resources are owned and cleared here under real C UI leases. */
struct host_slot {
    uint64_t facade, generation, final_entry;
    uint8_t *tree;
    uint64_t *listener, *weak_owner;
    uint32_t bytes, interaction, cleared;
};
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    struct host_slot slots[16];
    uint64_t issued, destructors, callbacks, nested_checks;
    int fd, started, paused, start_status, active;
    uint32_t hold_point;
    uint64_t hold_facade;
    int held, release;
    uint64_t fail_facade, lose_facade, nested_facade;
} host = {.lock = PTHREAD_MUTEX_INITIALIZER, .changed = PTHREAD_COND_INITIALIZER, .fd = -1};
static struct host_slot *find(uint64_t facade) {
    for (unsigned i = 0; i < 16; ++i) if (host.slots[i].facade == facade) return &host.slots[i];
    return NULL;
}
static void checkpoint(uint32_t point, uint64_t facade) {
    pthread_mutex_lock(&host.lock);
    if (host.hold_point == point && (host.hold_facade == 0 || host.hold_facade == facade)) {
        host.held = 1; pthread_cond_broadcast(&host.changed);
        while (!host.release) pthread_cond_wait(&host.changed, &host.lock);
        host.hold_point = 0;
    }
    pthread_mutex_unlock(&host.lock);
}
static void nested(uint64_t facade) {
    pthread_mutex_lock(&host.lock);
    int run = host.nested_facade == facade;
    int fd = host.fd;
    pthread_mutex_unlock(&host.lock);
    if (run) {
        struct mxuit_snapshot before, after;
        if (mxuit_inspect(&before) != MXUIT_OK || mxuit_callback(fd, 1, 1) != MXUIT_BUSY || mxuit_inspect(&after) != MXUIT_OK) abort();
        if (before.callback_epoch != after.callback_epoch || before.ui_entry_fenced != after.ui_entry_fenced ||
            before.pending_pipe_hint != after.pending_pipe_hint || after.fault != 0) abort();
        pthread_mutex_lock(&host.lock); ++host.nested_checks; pthread_mutex_unlock(&host.lock);
    }
}
int32_t mxis_host_slot_acquire(uint64_t facade, uint64_t entry, uint64_t *generation) {
    if (!generation) return MXUIT_INVALID;
    *generation = 0;
    if (mxuit_ui_validate(facade, entry) != MXUIT_OK) return MXUIT_STALE;
    checkpoint(1, facade); nested(facade);
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (slot) { *generation = slot->generation; pthread_mutex_unlock(&host.lock); return slot->cleared ? MXUIT_CLOSED : MXUIT_OK; }
    if (host.issued == UINT64_MAX) { pthread_mutex_unlock(&host.lock); return MXUIT_EXHAUSTED; }
    for (unsigned i = 0; i < 16; ++i) if (!host.slots[i].facade) { slot = &host.slots[i]; break; }
    if (!slot) { pthread_mutex_unlock(&host.lock); return MXUIT_CAPACITY; }
    uint8_t *tree = calloc(65536, 1);
    uint64_t *listener = calloc(1, sizeof(uint64_t));
    uint64_t *owner = calloc(1, sizeof(uint64_t));
    if (!tree || !listener || !owner) {
        free(tree); free(listener); free(owner); pthread_mutex_unlock(&host.lock); return MXUIT_UNAVAILABLE;
    }
    ++host.issued; *owner = facade;
    *slot = (struct host_slot){.facade=facade, .generation=host.issued, .tree=tree, .listener=listener, .weak_owner=owner};
    *generation = slot->generation;
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxis_host_inspect(uint64_t facade, uint64_t entry, struct mxis_host_snapshot *output) {
    if (!output) return MXUIT_INVALID;
    memset(output, 0, sizeof(*output));
    if (mxuit_ui_validate(facade, entry) != MXUIT_OK) return MXUIT_STALE;
    checkpoint(2, facade);
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (!slot) { pthread_mutex_unlock(&host.lock); return MXUIT_STALE; }
    if (host.lose_facade == facade && slot->weak_owner) { free(slot->weak_owner); slot->weak_owner = NULL; }
    *output = (struct mxis_host_snapshot){slot->facade, slot->generation, slot->final_entry, 1,
        slot->cleared, slot->tree != NULL, slot->listener != NULL, slot->weak_owner != NULL, slot->bytes, slot->interaction};
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment, uint64_t input,
                   uint64_t probe, const uint8_t *packet, uint32_t bytes) {
    if (mxuit_ui_validate(facade, entry) != MXUIT_OK) return MXUIT_STALE;
    if (!attachment || !input || !probe || !packet || !bytes || bytes > 65536) return MXUIT_INVALID;
    checkpoint(3, facade); nested(facade);
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (!slot || slot->cleared || !slot->tree || !slot->listener || !slot->weak_owner) { pthread_mutex_unlock(&host.lock); return MXUIT_STALE; }
    memcpy(slot->tree, packet, bytes); slot->bytes = bytes; *slot->listener = attachment;
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled) {
    if (mxuit_ui_validate(facade, entry) != MXUIT_OK || enabled > 1) return MXUIT_STALE;
    checkpoint(4, facade); nested(facade);
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (!slot || slot->cleared || !slot->weak_owner) { pthread_mutex_unlock(&host.lock); return MXUIT_STALE; }
    slot->interaction = enabled; pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final) {
    if (mxuit_ui_validate(facade, entry) != MXUIT_OK || final > 1) return MXUIT_STALE;
    checkpoint(5, facade); nested(facade);
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (!slot || slot->cleared || !slot->weak_owner || host.fail_facade == facade) { pthread_mutex_unlock(&host.lock); return MXUIT_STALE; }
    slot->bytes = 0; slot->interaction = 0;
    if (slot->tree) memset(slot->tree, 0, 65536);
    if (slot->listener) *slot->listener = 0;
    if (final) {
        free(slot->tree); slot->tree = NULL; free(slot->listener); slot->listener = NULL;
        free(slot->weak_owner); slot->weak_owner = NULL; slot->cleared = 1; slot->final_entry = entry;
    }
    pthread_mutex_unlock(&host.lock);
    checkpoint(6, facade); return MXUIT_OK;
}
int32_t mxis_host_release_destroyed(uint64_t facade, uint64_t generation) {
    checkpoint(7, facade);
    /* Destruction must happen after the actual C facade record disappeared. */
if (mxuit_facade_begin_close(facade) != MXUIT_STALE) return MXUIT_BUSY;
    pthread_mutex_lock(&host.lock);
    struct host_slot *slot = find(facade);
    if (!slot || slot->generation != generation || !slot->cleared || !slot->final_entry || slot->tree || slot->listener || slot->weak_owner) { pthread_mutex_unlock(&host.lock); return MXUIT_STALE; }
    memset(slot, 0, sizeof(*slot)); ++host.destructors;
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxuit_platform_register(int fd) {
    if (host.fd != -1 || fd < 0) return MXUIT_INVALID;
    host.fd = fd; return MXUIT_OK;
}
static void *ui_main(void *unused) {
    (void)unused;
    int32_t status = mxuit_install();
    pthread_mutex_lock(&host.lock); host.start_status = status; host.started = 1;
    pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock);
    if (status != MXUIT_OK) return NULL;
    for (;;) {
        struct pollfd p = {.fd=host.fd, .events=POLLIN};
        int result = poll(&p, 1, -1);
        if (result < 0 && errno == EINTR) continue;
        if (result <= 0) abort();
        pthread_mutex_lock(&host.lock);
        while (host.paused) pthread_cond_wait(&host.changed, &host.lock);
        host.active = 1; pthread_mutex_unlock(&host.lock);
        checkpoint(8, 0);
        (void)mxuit_callback(host.fd, 1, 0);
        checkpoint(9, 0);
        pthread_mutex_lock(&host.lock); host.active = 0; ++host.callbacks;
        pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock);
    }
    return NULL;
}
int32_t mxish_start(void) {
    pthread_t thread;
    pthread_mutex_lock(&host.lock);
    if (host.started) { int result = host.start_status; pthread_mutex_unlock(&host.lock); return result; }
    if (pthread_create(&thread, NULL, ui_main, NULL)) { pthread_mutex_unlock(&host.lock); return MXUIT_UNAVAILABLE; }
    pthread_detach(thread);
    while (!host.started) pthread_cond_wait(&host.changed, &host.lock);
    int result = host.start_status; pthread_mutex_unlock(&host.lock); return result;
}
void mxish_pause(void) { pthread_mutex_lock(&host.lock); host.paused = 1; pthread_mutex_unlock(&host.lock); }
void mxish_resume(void) { pthread_mutex_lock(&host.lock); host.paused = 0; pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock); }
static struct timespec deadline(void) { struct timespec d; clock_gettime(CLOCK_REALTIME, &d); d.tv_sec += 10; return d; }
int32_t mxish_wait_callbacks(uint64_t count) {
    struct timespec d = deadline(); pthread_mutex_lock(&host.lock);
    while (host.callbacks < count) if (pthread_cond_timedwait(&host.changed, &host.lock, &d)) { pthread_mutex_unlock(&host.lock); return MXUIT_BUSY; }
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxish_set_hold(uint32_t point, uint64_t facade) {
    pthread_mutex_lock(&host.lock);
    if (host.hold_point || point < 1 || point > 9) { pthread_mutex_unlock(&host.lock); return MXUIT_BUSY; }
    host.hold_point = point; host.hold_facade = facade; host.held = 0; host.release = 0;
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxish_wait_hold(void) {
    struct timespec d = deadline(); pthread_mutex_lock(&host.lock);
    while (!host.held) if (pthread_cond_timedwait(&host.changed, &host.lock, &d)) { pthread_mutex_unlock(&host.lock); return MXUIT_BUSY; }
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
void mxish_release_hold(void) { pthread_mutex_lock(&host.lock); host.release = 1; pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock); }
void mxish_fail_retire(uint64_t facade) { pthread_mutex_lock(&host.lock); host.fail_facade = facade; pthread_mutex_unlock(&host.lock); }
void mxish_lose_owner(uint64_t facade) { pthread_mutex_lock(&host.lock); host.lose_facade = facade; pthread_mutex_unlock(&host.lock); }
void mxish_nested(uint64_t facade) { pthread_mutex_lock(&host.lock); host.nested_facade = facade; pthread_mutex_unlock(&host.lock); }
uint64_t mxish_nested_checks(void) { pthread_mutex_lock(&host.lock); uint64_t n = host.nested_checks; pthread_mutex_unlock(&host.lock); return n; }
uint64_t mxish_destructors(void) { pthread_mutex_lock(&host.lock); uint64_t n = host.destructors; pthread_mutex_unlock(&host.lock); return n; }
uint64_t mxish_live_allocations(void) {
    uint64_t n = 0; pthread_mutex_lock(&host.lock);
    for (unsigned i = 0; i < 16; ++i) n += (host.slots[i].tree != NULL) + (host.slots[i].listener != NULL) + (host.slots[i].weak_owner != NULL);
    pthread_mutex_unlock(&host.lock); return n;
}
int32_t mxish_inject_syscall(uint32_t operation) { return mxuit_test_fail_syscall(operation, EIO, 1); }
int32_t mxish_set_c_counter(uint32_t which, uint64_t value) {
    switch (which) {
    case 1: return mxuit_test_set_issued(value);
    case 2: return mxuit_test_set_facade_issued(value);
    case 3: return mxuit_test_set_ui_entry_issued(value);
    case 4: return mxuit_test_set_epoch(value);
    default: return MXUIT_INVALID;
    }
}
