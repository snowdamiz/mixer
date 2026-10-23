#define _DARWIN_C_SOURCE 1
#define _POSIX_C_SOURCE 200809L
#include "scheduler_probe.h"
#include "../../../native/android/signed-guest-ui/transport/include/mixer_ui_transport.h"
#include <dlfcn.h>
#include <pthread.h>
#include <time.h>
#include <stdlib.h>

/* Verification-only runtime scheduler interception. The product Swift bytes are
 * unchanged. Only the C transport's required-complete symbol is renamed in this
 * build; the wrapper below calls the actual Swift complete exactly once.
 * This hook receives the runtime's exact Job and original enqueue operation. */
typedef void (*enqueue_fn)(void *);
typedef void (*hook_fn)(void *, enqueue_fn);
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    hook_fn *runtime_slot;
    uint64_t target, owner, waiter, captured;
    void *job;
    enqueue_fn original;
    int installed, status;
} probe = {.lock=PTHREAD_MUTEX_INITIALIZER, .changed=PTHREAD_COND_INITIALIZER};
static _Thread_local uint64_t completing_owner, completing_waiter;
static void capture(void *job, enqueue_fn original) {
    pthread_mutex_lock(&probe.lock);
    if (completing_owner && completing_owner == probe.target) {
        if (probe.job || probe.captured) abort();
        probe.job = job; probe.original = original; probe.owner = completing_owner;
        probe.waiter = completing_waiter; ++probe.captured;
        pthread_cond_broadcast(&probe.changed); pthread_mutex_unlock(&probe.lock); return;
    }
    pthread_mutex_unlock(&probe.lock); original(job);
}
__attribute__((constructor)) static void install(void) {
    probe.runtime_slot = (hook_fn *)dlsym(RTLD_DEFAULT, "swift_task_enqueueGlobal_hook");
    if (!probe.runtime_slot || *probe.runtime_slot != NULL) { probe.status = MXUIT_UNAVAILABLE; return; }
    *probe.runtime_slot = capture; probe.installed = 1; probe.status = MXUIT_OK;
}
int32_t mxish_scheduler_install_status(void) { return probe.status; }
int32_t mxish_scheduler_arm(uint64_t owner) {
    pthread_mutex_lock(&probe.lock);
    if (!probe.installed || probe.job || probe.captured || !owner) { pthread_mutex_unlock(&probe.lock); return MXUIT_BUSY; }
    probe.target = owner; pthread_mutex_unlock(&probe.lock); return MXUIT_OK;
}
void mxish_transport_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    if (kind == MXUIT_RETIRE && result == MXUIT_DRAIN_OK) { completing_owner = owner; completing_waiter = waiter; }
    mxuit_complete(owner, waiter, kind, result); // Actual unchanged Swift hook.
    completing_owner = 0; completing_waiter = 0;
}
int32_t mxish_scheduler_wait(void) {
    struct timespec d; clock_gettime(CLOCK_REALTIME, &d); d.tv_sec += 8;
    pthread_mutex_lock(&probe.lock);
    while (!probe.job) if (pthread_cond_timedwait(&probe.changed, &probe.lock, &d)) { pthread_mutex_unlock(&probe.lock); return MXUIT_BUSY; }
    pthread_mutex_unlock(&probe.lock); return MXUIT_OK;
}
uint64_t mxish_scheduler_captured_owner(void) { pthread_mutex_lock(&probe.lock); uint64_t n=probe.owner; pthread_mutex_unlock(&probe.lock); return n; }
uint64_t mxish_scheduler_captured_waiter(void) { pthread_mutex_lock(&probe.lock); uint64_t n=probe.waiter; pthread_mutex_unlock(&probe.lock); return n; }
uint64_t mxish_scheduler_captured_jobs(void) { pthread_mutex_lock(&probe.lock); uint64_t n=probe.captured; pthread_mutex_unlock(&probe.lock); return n; }
void mxish_scheduler_release(void) {
    pthread_mutex_lock(&probe.lock);
    void *job=probe.job; enqueue_fn original=probe.original;
    probe.job=NULL; probe.original=NULL; probe.target=0;
    pthread_mutex_unlock(&probe.lock);
    if (job) original(job); // Exactly once; runtime's original executor is kept.
}
int32_t mxish_scheduler_unhook(void) {
    pthread_mutex_lock(&probe.lock);
    if (probe.job) { pthread_mutex_unlock(&probe.lock); return MXUIT_BUSY; }
    if (probe.installed) { *probe.runtime_slot=NULL; probe.installed=0; }
    pthread_mutex_unlock(&probe.lock); return MXUIT_OK;
}
__attribute__((destructor)) static void cleanup(void) {
    mxish_scheduler_release(); (void)mxish_scheduler_unhook();
}
