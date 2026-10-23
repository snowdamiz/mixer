#define _POSIX_C_SOURCE 200809L
#include "internal.h"
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>

struct owner_slot {
    uint64_t id, last_waiter, waiter_token, last_hook_epoch;
    int hint, waiting, active, completing, closing;
    int retirement_started, retirement_done, joined;
    uint64_t facade_id, last_entry_serial;
    uint32_t purpose, active_drain_kind;
};
struct facade_slot {
    uint64_t id;
    int closing, terminal_issued;
    uint64_t current_endpoint, active_entry, last_entry_serial;
};
static struct {
    pthread_mutex_t lock;
    pthread_t ui_thread;
    int initialized, ready, fault, fault_published, fds[2], registered, pipe_pending, in_callback;
    uint64_t issued, epoch, fenced, callbacks, drains, completions, requests, hints;
    uint32_t maximum_occupied, maximum_waiters, maximum_helpers;
    struct owner_slot slots[MXUIT_OWNER_CAPACITY];
    struct facade_slot facades[MXUIT_FACADE_CAPACITY];
    uint64_t facade_issued, ui_entry_issued, ui_entry_fenced;
    uint64_t active_entry_facade, active_entry_serial;
#ifdef MIXER_UI_TRANSPORT_TESTING
    uint32_t fail_operation, fail_times;
    int fail_error;
#endif
} state = { .lock = PTHREAD_MUTEX_INITIALIZER, .fds = {-1, -1} };

static struct owner_slot *find_locked(uint64_t owner) {
    if (owner == 0) return NULL;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i)
        if (state.slots[i].id == owner) return &state.slots[i];
    return NULL;
}
static struct facade_slot *facade_locked(uint64_t facade) {
    if (facade == 0) return NULL;
    for (size_t i = 0; i < MXUIT_FACADE_CAPACITY; ++i)
        if (state.facades[i].id == facade) return &state.facades[i];
    return NULL;
}
static void fail_locked(int32_t status) {
    if (state.fault == 0) state.fault = status;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i)
        if (state.slots[i].id != 0) state.slots[i].closing = 1;
    for (size_t i = 0; i < MXUIT_FACADE_CAPACITY; ++i)
        if (state.facades[i].id != 0) state.facades[i].closing = 1;
}
/* Every fault-creating path returns through this process-only publication.
 * The bit is consumed under lock, so concurrent origins publish first fault
 * exactly once. There is no owner/slot read after the hook resumes a joiner. */
static int32_t finish_locked(int32_t result) {
    const int publish = state.fault != 0 && !state.fault_published;
    const int32_t fault = state.fault;
    const uint64_t callback_fence = state.fenced, entry_fence = state.ui_entry_fenced;
    if (publish) state.fault_published = 1;
    pthread_mutex_unlock(&state.lock);
    if (publish) mxuit_progress(callback_fence, entry_fence, fault);
    return result;
}
static int bump_locked(uint64_t *counter) {
    if (*counter == UINT64_MAX) { fail_locked(MXUIT_EXHAUSTED); return 0; }
    ++*counter;
    return 1;
}
static int32_t available_locked(void) {
    if (!state.ready) return state.fault != 0 ? state.fault : MXUIT_UNAVAILABLE;
    return state.fault;
}
static void maxima_locked(void) {
    uint32_t occupied = 0, waiters = 0, helpers = 0;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        occupied += state.slots[i].id != 0 ? 1U : 0U;
        waiters += state.slots[i].waiting ? 1U : 0U;
        helpers += state.slots[i].active ? 1U : 0U;
    }
    if (occupied > state.maximum_occupied) state.maximum_occupied = occupied;
    if (waiters > state.maximum_waiters) state.maximum_waiters = waiters;
    if (helpers > state.maximum_helpers) state.maximum_helpers = helpers;
}
#ifdef MIXER_UI_TRANSPORT_TESTING
static int injected_locked(uint32_t operation) {
    if (state.fail_operation != operation || state.fail_times == 0) return 0;
    --state.fail_times;
    errno = state.fail_error;
    return 1;
}
#else
static int injected_locked(uint32_t operation) { (void)operation; return 0; }
enum { MXUIT_TEST_PIPE = 1, MXUIT_TEST_FCNTL = 2, MXUIT_TEST_READ = 3, MXUIT_TEST_WRITE = 4 };
#endif
static int configure_fd_locked(int fd, int command, int flag) {
    if (injected_locked(MXUIT_TEST_FCNTL)) return -1;
    int previous = fcntl(fd, command);
    if (previous < 0) return -1;
    return fcntl(fd, command == F_GETFL ? F_SETFL : F_SETFD, previous | flag);
}
/* The one-byte kernel latch is only written under this lock. Failure is sticky;
 * EAGAIN without our own pending bit is not guessed to mean successful delivery.
 * Bounded EINTR retries avoid an unbounded syscall loop under hostile signals. */
static int wake_locked(void) {
    if (state.pipe_pending || state.fault != 0) return state.fault == 0;
    const unsigned char byte = 1;
    for (unsigned int attempt = 0; attempt < 8; ++attempt) {
        ssize_t count = injected_locked(MXUIT_TEST_WRITE) ? -1 : write(state.fds[1], &byte, 1);
        if (count == 1) { state.pipe_pending = 1; return 1; }
        if (count < 0 && errno == EINTR) continue;
        fail_locked(MXUIT_IO); return 0;
    }
    fail_locked(MXUIT_IO); return 0;
}
static int read_hint_locked(void) {
    unsigned char byte = 0;
    for (unsigned int attempt = 0; attempt < 8; ++attempt) {
        ssize_t count = injected_locked(MXUIT_TEST_READ) ? -1 : read(state.fds[0], &byte, 1);
        if (count == 1 && byte == 1) { state.pipe_pending = 0; return 1; }
        if (count < 0 && errno == EINTR) continue;
        fail_locked(MXUIT_IO); return 0;
    }
    fail_locked(MXUIT_IO); return 0;
}
int32_t mxuit_install(void) {
    pthread_mutex_lock(&state.lock);
    if (state.initialized) {
        int32_t result = available_locked();
        if (result == MXUIT_OK && !pthread_equal(state.ui_thread, pthread_self())) result = MXUIT_WRONG_THREAD;
        pthread_mutex_unlock(&state.lock); return result;
    }
    state.initialized = 1;
    state.ui_thread = pthread_self();
    int fds[2] = {-1, -1};
    int made = injected_locked(MXUIT_TEST_PIPE) ? -1 : pipe(fds);
    if (made != 0 || configure_fd_locked(fds[0], F_GETFL, O_NONBLOCK) != 0 ||
        configure_fd_locked(fds[1], F_GETFL, O_NONBLOCK) != 0 ||
        configure_fd_locked(fds[0], F_GETFD, FD_CLOEXEC) != 0 ||
        configure_fd_locked(fds[1], F_GETFD, FD_CLOEXEC) != 0) {
        if (fds[0] >= 0) (void)close(fds[0]);
        if (fds[1] >= 0) (void)close(fds[1]);
        fail_locked(MXUIT_IO); return finish_locked(MXUIT_IO);
    }
    state.fds[0] = fds[0]; state.fds[1] = fds[1];
    /* Registration happens once, on this same thread, before owner admission.
     * The fixed platform registration must not invoke callbacks inline. */
    int32_t result = mxuit_platform_register(fds[0]);
    if (result != MXUIT_OK) {
        (void)close(fds[0]); (void)close(fds[1]);
        state.fds[0] = -1; state.fds[1] = -1;
        fail_locked(result); return finish_locked(result);
    }
    state.registered = 1; state.ready = 1;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_acquire(uint64_t *owner) {
    if (owner == NULL) return MXUIT_INVALID;
    *owner = 0;
    pthread_mutex_lock(&state.lock);
    int32_t result = available_locked();
    if (result != MXUIT_OK) { pthread_mutex_unlock(&state.lock); return result; }
    if (state.issued == UINT64_MAX) { pthread_mutex_unlock(&state.lock); return MXUIT_EXHAUSTED; }
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        if (state.slots[i].id != 0) continue;
        ++state.issued;
        state.slots[i].id = state.issued;
        *owner = state.issued; maxima_locked();
        pthread_mutex_unlock(&state.lock); return MXUIT_OK;
    }
    pthread_mutex_unlock(&state.lock); return MXUIT_CAPACITY;
}
int32_t mxuit_request(uint64_t owner, uint64_t waiter) {
    if (waiter == 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    int32_t result = available_locked();
    if (slot == NULL) result = MXUIT_STALE;
    else if (result == MXUIT_OK) {
        if (slot->retirement_started || slot->joined) result = MXUIT_CLOSED;
        else if (slot->waiting || slot->active) result = MXUIT_BUSY;
        else if (slot->last_waiter == UINT64_MAX) result = MXUIT_EXHAUSTED;
        else if (waiter <= slot->last_waiter) result = MXUIT_STALE;
        else if (bump_locked(&state.requests)) {
            slot->last_waiter = waiter; slot->waiter_token = waiter;
            slot->waiting = 1; slot->hint = 1; maxima_locked();
            if (!wake_locked()) result = state.fault;
        } else result = state.fault;
    }
    return finish_locked(result);
}
int32_t mxuit_hint(uint64_t owner) {
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    int32_t result = available_locked();
    if (slot == NULL) result = MXUIT_STALE;
    else if (result == MXUIT_OK) {
        if (slot->closing) result = MXUIT_CLOSED;
        else if (bump_locked(&state.hints)) {
            slot->hint = 1;
            if (slot->waiting && !slot->active && !slot->completing && !wake_locked()) result = state.fault;
        } else result = state.fault;
    }
    return finish_locked(result);
}
int32_t mxuit_facade_acquire(uint64_t *facade) {
    if (facade == NULL) return MXUIT_INVALID;
    *facade = 0;
    pthread_mutex_lock(&state.lock);
    int32_t result = available_locked();
    if (result != MXUIT_OK) { pthread_mutex_unlock(&state.lock); return result; }
    if (state.facade_issued >= INT64_MAX) { pthread_mutex_unlock(&state.lock); return MXUIT_EXHAUSTED; }
    for (size_t i = 0; i < MXUIT_FACADE_CAPACITY; ++i) {
        if (state.facades[i].id != 0) continue;
        ++state.facade_issued;
        state.facades[i].id = state.facade_issued;
        *facade = state.facade_issued;
        pthread_mutex_unlock(&state.lock); return MXUIT_OK;
    }
    pthread_mutex_unlock(&state.lock); return MXUIT_CAPACITY;
}
int32_t mxuit_acquire_for_facade(uint64_t facade, uint32_t purpose, uint64_t *owner) {
    if (owner == NULL) return MXUIT_INVALID;
    *owner = 0;
    if (facade == 0 || (purpose != MXUIT_ATTEMPT && purpose != MXUIT_TERMINAL)) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct facade_slot *record = facade_locked(facade);
    int32_t result = record == NULL ? MXUIT_STALE : available_locked();
    if (result == MXUIT_OK) {
        if (record->current_endpoint != 0) result = MXUIT_BUSY;
        else if ((purpose == MXUIT_ATTEMPT && record->closing) ||
                 (purpose == MXUIT_TERMINAL && record->terminal_issued)) result = MXUIT_CLOSED;
        else if (purpose == MXUIT_TERMINAL && !record->closing) result = MXUIT_INVALID;
        else if (state.issued == UINT64_MAX) result = MXUIT_EXHAUSTED;
        else {
            result = MXUIT_CAPACITY;
            for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
                struct owner_slot *slot = &state.slots[i];
                if (slot->id != 0) continue;
                ++state.issued;
                slot->id = state.issued; slot->facade_id = facade; slot->purpose = purpose;
                slot->last_entry_serial = record->last_entry_serial;
                slot->closing = record->closing;
                record->current_endpoint = slot->id;
                if (purpose == MXUIT_TERMINAL) record->terminal_issued = 1;
                *owner = slot->id; maxima_locked(); result = MXUIT_OK; break;
            }
        }
    }
    /* Acquisition is admission-safe: no fault origin, hook or pipe demand. */
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_facade_begin_close(uint64_t facade) {
    if (facade == 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct facade_slot *record = facade_locked(facade);
    int32_t result = record == NULL ? MXUIT_STALE : MXUIT_OK;
    if (record != NULL) {
        record->closing = 1;
        struct owner_slot *slot = find_locked(record->current_endpoint);
        if (slot != NULL) slot->closing = 1;
        if (state.fault != 0) result = state.fault;
    }
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_ui_enter(uint64_t facade, uint64_t owner, uint64_t waiter,
                      uint32_t kind, uint64_t *entry_serial) {
    if (entry_serial == NULL) return MXUIT_INVALID;
    *entry_serial = 0;
    if (facade == 0 || kind > MXUIT_UI_CLEANUP ||
        ((kind == MXUIT_UI_INGRESS || kind == MXUIT_UI_CLEANUP) ?
         (owner != 0 || waiter != 0) : (owner == 0 || waiter == 0))) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct facade_slot *record = facade_locked(facade);
    int32_t result = record == NULL ? MXUIT_STALE : available_locked();
    if (result == MXUIT_OK && !pthread_equal(state.ui_thread, pthread_self())) result = MXUIT_WRONG_THREAD;
    if (result == MXUIT_OK && state.active_entry_serial != 0) result = MXUIT_BUSY;
    if (result == MXUIT_OK && kind == MXUIT_UI_INGRESS && record->closing) result = MXUIT_CLOSED;
    if (result == MXUIT_OK && (kind == MXUIT_UI_PRESENT || kind == MXUIT_UI_RETIRE)) {
        struct owner_slot *slot = find_locked(owner);
        if (slot == NULL || slot->facade_id != facade || record->current_endpoint != owner ||
            slot->waiter_token != waiter) result = MXUIT_STALE;
        else if (!state.in_callback || !slot->active) result = MXUIT_BUSY;
        else if (slot->active_drain_kind != kind) result = MXUIT_INVALID;
    }
    if (result == MXUIT_OK) {
        if (!bump_locked(&state.ui_entry_issued)) result = state.fault;
        else {
            *entry_serial = state.ui_entry_issued;
            record->active_entry = *entry_serial; record->last_entry_serial = *entry_serial;
            state.active_entry_facade = facade; state.active_entry_serial = *entry_serial;
            struct owner_slot *slot = find_locked(record->current_endpoint);
            if (slot != NULL) slot->last_entry_serial = *entry_serial;
        }
    }
    return finish_locked(result);
}
static int32_t validate_entry_locked(uint64_t facade, uint64_t entry_serial) {
    struct facade_slot *record = facade_locked(facade);
    if (record == NULL) return MXUIT_STALE;
    if (!state.ready) return available_locked();
    if (!pthread_equal(state.ui_thread, pthread_self())) return MXUIT_WRONG_THREAD;
    if (state.active_entry_facade != facade || state.active_entry_serial != entry_serial ||
        record->active_entry != entry_serial) return MXUIT_STALE;
    return MXUIT_OK;
}
int32_t mxuit_ui_validate(uint64_t facade, uint64_t entry_serial) {
    if (facade == 0 || entry_serial == 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    int32_t result = validate_entry_locked(facade, entry_serial);
    if (result == MXUIT_OK && state.fault != 0) result = state.fault;
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_ui_leave(uint64_t facade, uint64_t entry_serial) {
    if (facade == 0 || entry_serial == 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    int32_t result = validate_entry_locked(facade, entry_serial);
    if (result == MXUIT_OK) {
        facade_locked(facade)->active_entry = 0;
        state.active_entry_facade = 0; state.active_entry_serial = 0;
        if (!wake_locked()) result = state.fault;
    }
    return finish_locked(result);
}
int32_t mxuit_facade_try_reclaim(uint64_t facade) {
    if (facade == 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct facade_slot *record = facade_locked(facade);
    int32_t result = record == NULL ? MXUIT_STALE : available_locked();
    if (result == MXUIT_OK) {
        if (!record->closing || record->current_endpoint != 0 || record->active_entry != 0 ||
            record->last_entry_serial > state.ui_entry_fenced) result = MXUIT_BUSY;
        else memset(record, 0, sizeof(*record));
    }
    /* Caller holds its separate exact cleanup receipt. No hook/fault origin. */
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_begin_close(uint64_t owner) {
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    int32_t result = slot == NULL ? MXUIT_STALE : MXUIT_OK;
    if (slot != NULL) slot->closing = 1;
    if (result == MXUIT_OK && state.fault != 0) result = state.fault;
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_consumer_joined(uint64_t owner) {
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    int32_t result = slot == NULL ? MXUIT_STALE : MXUIT_OK;
    if (slot != NULL) {
        /* A resumed consumer may really finish before complete's C tail returns.
         * Latch that trusted assertion independently; reclaim still checks the
         * helper, completion, successful RETIRE and actual callback fence. */
        if (!slot->closing || !slot->retirement_started) result = MXUIT_BUSY;
        else slot->joined = 1;
    }
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_try_reclaim(uint64_t owner) {
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    int32_t result = slot == NULL ? MXUIT_STALE : available_locked();
    if (slot != NULL && result == MXUIT_OK) {
        struct facade_slot *record = facade_locked(slot->facade_id);
        if (!slot->closing || !slot->retirement_done || !slot->joined || slot->waiting ||
            slot->active || slot->completing || slot->last_hook_epoch > state.fenced ||
            (record != NULL && (record->active_entry != 0 ||
                               slot->last_entry_serial > state.ui_entry_fenced))) result = MXUIT_BUSY;
        else {
            if (record != NULL) record->current_endpoint = 0;
            memset(slot, 0, sizeof(*slot));
        }
    }
    pthread_mutex_unlock(&state.lock); return result;
}
int32_t mxuit_callback(int fd, int input_ready, int failed_event) {
    pthread_mutex_lock(&state.lock);
    /* These checks precede reading the pipe or advancing the return fence.
     * Only the registered thread, with no nested callback, can establish that
     * its previous platform invocation returned. Static userdata never dies. */
    if (!state.ready || fd != state.fds[0]) { pthread_mutex_unlock(&state.lock); return MXUIT_INVALID; }
    if (!pthread_equal(state.ui_thread, pthread_self())) { pthread_mutex_unlock(&state.lock); return MXUIT_WRONG_THREAD; }
    if (state.in_callback || state.active_entry_serial != 0) { pthread_mutex_unlock(&state.lock); return MXUIT_BUSY; }
    if (state.fault != 0) { int32_t result = state.fault; pthread_mutex_unlock(&state.lock); return result; }
    if (failed_event || !input_ready) { fail_locked(MXUIT_IO); return finish_locked(MXUIT_IO); }
    if (!read_hint_locked()) {
        int32_t result = state.fault;
        return finish_locked(result);
    }
    if (state.epoch == UINT64_MAX || !bump_locked(&state.callbacks)) {
        fail_locked(MXUIT_EXHAUSTED); return finish_locked(MXUIT_EXHAUSTED);
    }
    const int progress = state.fenced != state.epoch || state.ui_entry_fenced != state.ui_entry_issued;
    state.fenced = state.epoch; state.ui_entry_fenced = state.ui_entry_issued;
    ++state.epoch; state.in_callback = 1;
    const uint64_t epoch = state.epoch;
    const uint64_t callback_fence = state.fenced, entry_fence = state.ui_entry_fenced;
    pthread_mutex_unlock(&state.lock);
    if (progress) mxuit_progress(callback_fence, entry_fence, MXUIT_OK);
    int ran_hook = 0;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        uint64_t owner = 0, waiter = 0;
        uint32_t kind = MXUIT_PRESENT;
        pthread_mutex_lock(&state.lock);
        struct owner_slot *slot = &state.slots[i];
        if (state.fault == 0 && slot->id != 0 && slot->waiting && slot->hint && !slot->active && !slot->completing) {
            if (bump_locked(&state.drains)) {
                owner = slot->id; waiter = slot->waiter_token;
                kind = slot->closing ? MXUIT_RETIRE : MXUIT_PRESENT;
                slot->hint = 0; slot->active = 1; slot->last_hook_epoch = epoch;
                slot->active_drain_kind = kind;
                if (kind == MXUIT_RETIRE) slot->retirement_started = 1;
                maxima_locked(); ran_hook = 1;
            }
        }
        pthread_mutex_unlock(&state.lock);
        if (owner == 0) continue;
        int32_t result = mxuit_drain(owner, waiter, kind);
        pthread_mutex_lock(&state.lock);
        slot = &state.slots[i];
        if (result != MXUIT_DRAIN_OK) { result = MXUIT_DRAIN_FAILED; slot->closing = 1; }
        else if (kind == MXUIT_PRESENT && slot->closing) result = MXUIT_DRAIN_CLOSE_PENDING;
        /* The old numeric waiter is consumed before its fixed hook resumes the
         * same task. That task may register its next waiter concurrently; the
         * completing lease and current epoch still prevent drain/reclamation. */
        slot->active = 0; slot->active_drain_kind = 0;
        slot->waiting = 0; slot->waiter_token = 0; slot->completing = 1;
        int complete_allowed = bump_locked(&state.completions);
        pthread_mutex_unlock(&state.lock);
        if (complete_allowed) mxuit_complete(owner, waiter, kind, result);
        pthread_mutex_lock(&state.lock);
        slot = &state.slots[i];
        slot->completing = 0;
        if (kind == MXUIT_RETIRE && result == MXUIT_DRAIN_OK && complete_allowed) {
            slot->retirement_done = 1; slot->hint = 0;
        }
        pthread_mutex_unlock(&state.lock);
    }
    pthread_mutex_lock(&state.lock);
    state.in_callback = 0;
    /* A later callback entry, rather than this last C owner access, is the
     * return fence. One extra byte is sufficient and does not self-perpetuate:
     * a no-hook fence callback emits no next fence byte. */
    int runnable = ran_hook;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i)
        if (state.slots[i].waiting && state.slots[i].hint) runnable = 1;
    if (runnable && state.fault == 0) (void)wake_locked();
    int32_t result = state.fault;
    return finish_locked(result);
}
int32_t mxuit_inspect(struct mxuit_snapshot *output) {
    if (output == NULL) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    memset(output, 0, sizeof(*output));
    output->callback_epoch = state.epoch; output->fenced_epoch = state.fenced;
    output->owners_issued = state.issued; output->callbacks = state.callbacks;
    output->drains = state.drains; output->completions = state.completions;
    output->requests = state.requests; output->hints = state.hints;
    output->maximum_occupied = state.maximum_occupied; output->maximum_waiters = state.maximum_waiters;
    output->maximum_active_helpers = state.maximum_helpers;
    output->owned_fds = (state.fds[0] >= 0 ? 1U : 0U) + (state.fds[1] >= 0 ? 1U : 0U);
    output->registration = state.registered ? 1U : 0U;
    output->pending_pipe_hint = state.pipe_pending ? 1U : 0U;
    output->callback_active = state.in_callback ? 1U : 0U; output->fault = state.fault;
    output->facades_issued = state.facade_issued;
    output->ui_entries_issued = state.ui_entry_issued; output->ui_entry_fenced = state.ui_entry_fenced;
    output->active_entry_facade = state.active_entry_facade; output->active_entry_serial = state.active_entry_serial;
    for (size_t i = 0; i < MXUIT_FACADE_CAPACITY; ++i)
        output->occupied_facades += state.facades[i].id != 0 ? 1U : 0U;
    for (size_t i = 0; i < MXUIT_OWNER_CAPACITY; ++i) {
        output->occupied += state.slots[i].id != 0 ? 1U : 0U;
        output->waiters += state.slots[i].waiting ? 1U : 0U;
        output->active_helpers += state.slots[i].active ? 1U : 0U;
        output->completing += state.slots[i].completing ? 1U : 0U;
    }
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_inspect_owner(uint64_t owner, struct mxuit_owner_snapshot *output) {
    if (output == NULL) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct owner_slot *slot = find_locked(owner);
    if (slot == NULL) { pthread_mutex_unlock(&state.lock); return MXUIT_STALE; }
    *output = (struct mxuit_owner_snapshot){slot->id, slot->last_waiter, slot->last_hook_epoch,
        (uint32_t)slot->hint, (uint32_t)slot->waiting, (uint32_t)slot->active,
        (uint32_t)slot->completing, (uint32_t)slot->closing, (uint32_t)slot->retirement_started,
        (uint32_t)slot->retirement_done, (uint32_t)slot->joined,
        slot->facade_id, slot->last_entry_serial, slot->purpose, slot->active_drain_kind};
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
#ifdef MIXER_UI_TRANSPORT_TESTING
int32_t mxuit_test_fail_syscall(uint32_t operation, int error, uint32_t times) {
    if (operation < MXUIT_TEST_PIPE || operation > MXUIT_TEST_WRITE || error <= 0) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    state.fail_operation = operation; state.fail_error = error; state.fail_times = times;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_test_set_issued(uint64_t value) {
    pthread_mutex_lock(&state.lock);
    if (state.issued != 0) { pthread_mutex_unlock(&state.lock); return MXUIT_BUSY; }
    state.issued = value;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_test_set_epoch(uint64_t value) {
    pthread_mutex_lock(&state.lock);
    if (state.epoch != 0 || state.in_callback) { pthread_mutex_unlock(&state.lock); return MXUIT_BUSY; }
    state.epoch = value; state.fenced = value;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_test_set_facade_issued(uint64_t value) {
    pthread_mutex_lock(&state.lock);
    if (state.facade_issued != 0 || value > INT64_MAX) { pthread_mutex_unlock(&state.lock); return MXUIT_BUSY; }
    state.facade_issued = value;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_test_set_ui_entry_issued(uint64_t value) {
    pthread_mutex_lock(&state.lock);
    if (state.ui_entry_issued != 0 || state.active_entry_serial != 0) { pthread_mutex_unlock(&state.lock); return MXUIT_BUSY; }
    state.ui_entry_issued = value;
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
int32_t mxuit_test_inspect_facade(uint64_t facade, struct mxuit_test_facade_snapshot *output) {
    if (output == NULL) return MXUIT_INVALID;
    pthread_mutex_lock(&state.lock);
    struct facade_slot *record = facade_locked(facade);
    if (record == NULL) { pthread_mutex_unlock(&state.lock); return MXUIT_STALE; }
    *output = (struct mxuit_test_facade_snapshot){record->id, record->current_endpoint,
        record->active_entry, record->last_entry_serial, (uint32_t)record->closing,
        (uint32_t)record->terminal_issued};
    pthread_mutex_unlock(&state.lock); return MXUIT_OK;
}
#endif
