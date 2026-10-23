#define _POSIX_C_SOURCE 200809L
#include "mixer_android_host_bridge.h"
#include "host_test.h"
#include "../../../native/android/signed-guest-ui/transport/internal.h"
#include "../../../native/android/signed-guest-ui/binding/include/mixer_ui_binding.h"
#include <pthread.h>
#include <poll.h>
#include <errno.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dirent.h>
#if defined(__APPLE__)
#include <mach/mach.h>
#endif

/* This object is deliberately fixed, never an injected implementation. Its
 * actual host resources are owned and cleared here under real C UI leases. */
struct host_slot {
    uint64_t facade, generation, final_entry;
    uint64_t last_attachment, last_input, last_probe;
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
    uint64_t command_facade;
    uint32_t command_kind;
    int command_pending,command_active,command_done;
    int32_t command_result;
    uint64_t fail_facade, partial_facade, lose_facade, nested_facade;
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
    slot->last_attachment=attachment; slot->last_input=input; slot->last_probe=probe;
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
    if(host.partial_facade==facade){free(slot->tree);slot->tree=NULL;pthread_mutex_unlock(&host.lock);return MXUIT_IO;}
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
extern int32_t mxish_swift_scalar_entry(uint64_t,uint32_t);
static void *ui_main(void *unused) {
    (void)unused;
    int32_t status = mxuit_install();
    pthread_mutex_lock(&host.lock); host.start_status = status; host.started = 1;
    pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock);
    if (status != MXUIT_OK) return NULL;
    for (;;) {
        struct pollfd p = {.fd=host.fd, .events=POLLIN};
        int result = poll(&p, 1, 10); // Test UI command delivery only; product never polls.
        pthread_mutex_lock(&host.lock);
        uint64_t command_facade=host.command_facade;
        uint32_t command_kind=host.command_kind;
        int command=host.command_pending;host.command_pending=0;if(command)host.command_active=1;
        pthread_mutex_unlock(&host.lock);
        if(command){
            int32_t value;
            if(command_kind==4){
                uint64_t entry=0;value=mxuit_ui_enter(command_facade,0,0,MXUIT_UI_CLEANUP,&entry);
                if(value==MXUIT_OK){checkpoint(10,command_facade);value=mxuit_ui_leave(command_facade,entry);}
            }else value=mxish_swift_scalar_entry(command_facade,command_kind);
            pthread_mutex_lock(&host.lock);host.command_result=value;host.command_done=1;host.command_active=0;
            pthread_cond_broadcast(&host.changed);pthread_mutex_unlock(&host.lock);
        }
        if(result==0)continue;
        if (result < 0 && errno == EINTR) continue;
        if (result <= 0) abort();
        pthread_mutex_lock(&host.lock);
        if(host.paused){
            struct timespec retry;clock_gettime(CLOCK_REALTIME,&retry);retry.tv_nsec+=10000000;
            if(retry.tv_nsec>=1000000000){++retry.tv_sec;retry.tv_nsec-=1000000000;}
            (void)pthread_cond_timedwait(&host.changed,&host.lock,&retry);
            pthread_mutex_unlock(&host.lock);continue;
        }
        host.active = 1; pthread_mutex_unlock(&host.lock);
        checkpoint(8, 0);
        struct mxuit_snapshot before,after;
        (void)mxuit_inspect(&before);
        (void)mxuit_callback(host.fd, 1, 0);
        (void)mxuit_inspect(&after);
        if(after.drains>before.drains)checkpoint(9, 0);
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
void mxish_pause(void) {
    pthread_mutex_lock(&host.lock);host.paused=1;
    // Verification pause observes actual callback/command return. It never
    // advances a C fence or publishes a successful result on their behalf.
    while(host.active || host.command_active)pthread_cond_wait(&host.changed,&host.lock);
    pthread_mutex_unlock(&host.lock);
}
void mxish_resume(void) { pthread_mutex_lock(&host.lock); host.paused = 0; pthread_cond_broadcast(&host.changed); pthread_mutex_unlock(&host.lock); }
static struct timespec deadline(void) { struct timespec d; clock_gettime(CLOCK_REALTIME, &d); d.tv_sec += 10; return d; }
int32_t mxish_wait_callbacks(uint64_t count) {
    struct timespec d = deadline(); pthread_mutex_lock(&host.lock);
    while (host.callbacks < count) if (pthread_cond_timedwait(&host.changed, &host.lock, &d)) { pthread_mutex_unlock(&host.lock); return MXUIT_BUSY; }
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
int32_t mxish_set_hold(uint32_t point, uint64_t facade) {
    pthread_mutex_lock(&host.lock);
    if (host.hold_point || point < 1 || point > 10) { pthread_mutex_unlock(&host.lock); return MXUIT_BUSY; }
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
void mxish_partial_retire(uint64_t facade){pthread_mutex_lock(&host.lock);host.partial_facade=facade;pthread_mutex_unlock(&host.lock);}
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

uint64_t mxish_last_id(uint64_t facade,uint32_t kind){
    pthread_mutex_lock(&host.lock);struct host_slot *slot=find(facade);
    uint64_t n=slot ? (kind==1 ? slot->last_attachment : kind==2 ? slot->last_input : slot->last_probe) : 0;
    pthread_mutex_unlock(&host.lock);return n;
}

int32_t mxish_call_entry(uint64_t facade,uint32_t kind){
    pthread_mutex_lock(&host.lock);
    if(host.command_pending || host.command_active || !host.started){pthread_mutex_unlock(&host.lock);return MXUIT_BUSY;}
    host.command_facade=facade;host.command_kind=kind;host.command_done=0;host.command_pending=1;pthread_cond_broadcast(&host.changed);
    struct timespec d=deadline();
    while(!host.command_done)if(pthread_cond_timedwait(&host.changed,&host.lock,&d)){pthread_mutex_unlock(&host.lock);return MXUIT_BUSY;}
    int32_t result=host.command_result;pthread_mutex_unlock(&host.lock);return result;
}

static _Atomic uint32_t debug_phase;
void mxish_debug_mark(uint32_t phase){atomic_store(&debug_phase,phase);pthread_cond_broadcast(&host.changed);}
int32_t mxish_debug_wait(uint32_t phase){
    struct timespec limit=deadline();limit.tv_sec+=110;pthread_mutex_lock(&host.lock);
    while(atomic_load(&debug_phase)<phase){
        struct timespec tick;clock_gettime(CLOCK_REALTIME,&tick);
        if(tick.tv_sec>=limit.tv_sec){pthread_mutex_unlock(&host.lock);return MXUIT_BUSY;}
        tick.tv_nsec+=10000000;if(tick.tv_nsec>=1000000000){++tick.tv_sec;tick.tv_nsec-=1000000000;}
        (void)pthread_cond_timedwait(&host.changed,&host.lock,&tick);
    }
    pthread_mutex_unlock(&host.lock);return MXUIT_OK;
}
__attribute__((noinline)) void mxish_debug_release_point(void){
    /* A fixed verification-only debugger breakpoint, never a product callback. */
    pthread_mutex_lock(&host.lock);pthread_cond_broadcast(&host.changed);pthread_mutex_unlock(&host.lock);
}

static uint64_t directory_count(const char *path,int exclude_self){
    DIR *directory=opendir(path);if(!directory)return UINT64_MAX;
    uint64_t count=0;struct dirent *entry;
    while((entry=readdir(directory))!=NULL)if(entry->d_name[0]!='.')++count;
    closedir(directory);return count-(exclude_self ? 1U:0U);
}
uint64_t mxish_process_fd_count(void){
#if defined(__APPLE__)
    return directory_count("/dev/fd",1);
#else
    return directory_count("/proc/self/fd",1);
#endif
}
uint64_t mxish_process_thread_count(void){
#if defined(__APPLE__)
    thread_act_array_t threads=NULL;mach_msg_type_number_t count=0;
    if(task_threads(mach_task_self(),&threads,&count)!=KERN_SUCCESS)return UINT64_MAX;
    for(mach_msg_type_number_t i=0;i<count;++i)(void)mach_port_deallocate(mach_task_self(),threads[i]);
    (void)vm_deallocate(mach_task_self(),(vm_address_t)threads,count*sizeof(thread_act_t));return count;
#else
    return directory_count("/proc/self/task",0);
#endif
}
