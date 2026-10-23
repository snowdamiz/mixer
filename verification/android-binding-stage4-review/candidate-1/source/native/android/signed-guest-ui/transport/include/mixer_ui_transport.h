#ifndef MIXER_UI_TRANSPORT_H
#define MIXER_UI_TRANSPORT_H
#include <stdint.h>

/* Experimental internal transport, not a frozen/public Android UI contract.
 * No object/frame/model/pointer is retained. Owner and waiter IDs are data.
 * Sixteen owner slots and one process-lifetime pipe/Looper registration.
 * install must be called on the Java-verified Android main Looper thread.
 * consumer_joined is a trusted caller assertion AFTER actual Task.value;
 * C cannot prove a Swift task's lifetime. A separate callback-return fence is
 * still required before reclaim. No callbacks are installed by this API. */
enum { MXUIT_OWNER_CAPACITY = 16, MXUIT_FACADE_CAPACITY = 16 };
enum mxuit_status {
    MXUIT_OK = 0, MXUIT_BUSY = 1, MXUIT_STALE = 2, MXUIT_CLOSED = 3,
    MXUIT_INVALID = 4, MXUIT_CAPACITY = 5, MXUIT_EXHAUSTED = 6,
    MXUIT_UNAVAILABLE = 7, MXUIT_IO = 8, MXUIT_WRONG_THREAD = 9
};
enum mxuit_drain_kind { MXUIT_PRESENT = 1, MXUIT_RETIRE = 2 };
enum mxuit_endpoint_purpose { MXUIT_ATTEMPT = 1, MXUIT_TERMINAL = 2 };
enum mxuit_ui_entry_kind {
    MXUIT_UI_INGRESS = 0, MXUIT_UI_PRESENT = 1,
    MXUIT_UI_RETIRE = 2, MXUIT_UI_CLEANUP = 3
};
enum mxuit_drain_result {
    MXUIT_DRAIN_OK = 0, MXUIT_DRAIN_FAILED = 1,
    MXUIT_DRAIN_CLOSE_PENDING = 2
};

int32_t mxuit_install(void);
int32_t mxuit_acquire(uint64_t *owner);
int32_t mxuit_request(uint64_t owner, uint64_t waiter);
int32_t mxuit_hint(uint64_t owner);
int32_t mxuit_begin_close(uint64_t owner);
int32_t mxuit_consumer_joined(uint64_t owner);
int32_t mxuit_try_reclaim(uint64_t owner);

/* Stable facade accounting is separate from replaceable endpoint ownership.
 * All output identities are zeroed before validation. UI entries are admitted
 * only on the installation thread, before resource/JNI lookup. leave follows
 * the synchronous helper's actual return and has a scalar-only caller tail.
 * A later non-reentrant callback, never leave itself, fences that return.
 * facade_try_reclaim additionally requires the caller's exact final Swift
 * cleanup receipt; C success proves only this scalar record is reusable. */
int32_t mxuit_facade_acquire(uint64_t *facade);
int32_t mxuit_acquire_for_facade(uint64_t facade, uint32_t purpose, uint64_t *owner);
int32_t mxuit_facade_begin_close(uint64_t facade);
int32_t mxuit_ui_enter(uint64_t facade, uint64_t owner, uint64_t waiter,
                      uint32_t kind, uint64_t *entry_serial);
int32_t mxuit_ui_leave(uint64_t facade, uint64_t entry_serial);
int32_t mxuit_ui_validate(uint64_t facade, uint64_t entry_serial);
int32_t mxuit_facade_try_reclaim(uint64_t facade);

/* Required fixed link symbols. The final native binding supplies these exact
 * implementations, with weak model lookup and synchronous Looper-only work.
 * They run outside transport locks. No runtime setter or arbitrary context.
 * drain returns OK or FAILED only. complete must consume its numeric result
 * without retaining a transport owner pointer. It may wake the same fixed task.
 * PRESENT close/failure requires a subsequent RETIRE request by that consumer. */
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind);
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result);
/* Required process-only hook. Changed return fences and the first sticky fault
 * publish outside the C lock. No owner lookup, reclaim, weak/JNI work or wake
 * demand may be hidden in this hook or its post-resume tail. */
void mxuit_progress(uint64_t callback_fence, uint64_t ui_entry_fence, int32_t sticky_fault);

struct mxuit_snapshot {
    uint64_t callback_epoch, fenced_epoch, owners_issued;
    uint64_t callbacks, drains, completions, requests, hints;
    uint32_t occupied, waiters, active_helpers, completing;
    uint32_t maximum_occupied, maximum_waiters, maximum_active_helpers;
    uint32_t owned_fds, registration, pending_pipe_hint, callback_active;
    int32_t fault;
    uint64_t facades_issued, ui_entries_issued, ui_entry_fenced;
    uint64_t active_entry_facade, active_entry_serial;
    uint32_t occupied_facades;
};
struct mxuit_owner_snapshot {
    uint64_t owner, last_waiter, last_hook_epoch;
    uint32_t hint, waiter, active_helper, completing;
    uint32_t closing, retirement_started, retirement_done, consumer_joined;
    uint64_t facade_id, last_entry_serial;
    uint32_t purpose, active_drain_kind;
};
int32_t mxuit_inspect(struct mxuit_snapshot *output);
int32_t mxuit_inspect_owner(uint64_t owner, struct mxuit_owner_snapshot *output);
#endif
