#define _POSIX_C_SOURCE 200809L
#include "transport_probe.h"
#include "../../../native/android/signed-guest-ui/transport/include/mixer_ui_transport.h"
#include <pthread.h>
#include <time.h>

extern int32_t mxish_actual_try_reclaim(uint64_t);
extern int32_t mxish_actual_facade_try_reclaim(uint64_t);
extern int32_t mxish_actual_ui_leave(uint64_t, uint64_t);
extern int32_t mxish_actual_request(uint64_t, uint64_t);
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    uint32_t point;
    uint64_t identity, calls, facade_calls, request_owner, request_waiter;
    int held, released;
} probe = {.lock=PTHREAD_MUTEX_INITIALIZER,.changed=PTHREAD_COND_INITIALIZER};
static void hold(uint32_t point, uint64_t identity) {
    pthread_mutex_lock(&probe.lock);
    if (probe.point == point && (!probe.identity || probe.identity == identity)) {
        probe.held=1; pthread_cond_broadcast(&probe.changed);
        while (!probe.released) pthread_cond_wait(&probe.changed,&probe.lock);
        probe.point=0;
    }
    pthread_mutex_unlock(&probe.lock);
}
int32_t mxish_probe_arm(uint32_t point, uint64_t identity) {
    pthread_mutex_lock(&probe.lock);
    if (probe.point || probe.held) { pthread_mutex_unlock(&probe.lock);return MXUIT_BUSY; }
    probe.point=point;probe.identity=identity;probe.released=0;
    pthread_mutex_unlock(&probe.lock);return MXUIT_OK;
}
int32_t mxish_probe_wait(void) {
    struct timespec d;clock_gettime(CLOCK_REALTIME,&d);d.tv_sec+=8;
    pthread_mutex_lock(&probe.lock);
    while(!probe.held)if(pthread_cond_timedwait(&probe.changed,&probe.lock,&d)){pthread_mutex_unlock(&probe.lock);return MXUIT_BUSY;}
    pthread_mutex_unlock(&probe.lock);return MXUIT_OK;
}
void mxish_probe_release(void){pthread_mutex_lock(&probe.lock);probe.released=1;pthread_cond_broadcast(&probe.changed);pthread_mutex_unlock(&probe.lock);}
uint64_t mxish_probe_reclaim_calls(void){pthread_mutex_lock(&probe.lock);uint64_t n=probe.calls;pthread_mutex_unlock(&probe.lock);return n;}
uint64_t mxish_probe_request_owner(void){pthread_mutex_lock(&probe.lock);uint64_t n=probe.request_owner;pthread_mutex_unlock(&probe.lock);return n;}
uint64_t mxish_probe_request_waiter(void){pthread_mutex_lock(&probe.lock);uint64_t n=probe.request_waiter;pthread_mutex_unlock(&probe.lock);return n;}
int32_t mxish_probe_preempt_request(uint64_t owner,uint64_t waiter){return mxish_actual_request(owner,waiter);}
int32_t mxuit_try_reclaim(uint64_t owner){
    pthread_mutex_lock(&probe.lock);uint64_t call=++probe.calls;pthread_mutex_unlock(&probe.lock);
    if(call==2)hold(2,owner); // Actual Swift progress token is already registered.
    int32_t result=mxish_actual_try_reclaim(owner);
    if(call==1 && result==MXUIT_BUSY)hold(1,owner); // First real BUSY, before registration.
    return result;
}
int32_t mxuit_ui_leave(uint64_t facade,uint64_t entry){hold(3,facade);return mxish_actual_ui_leave(facade,entry);}
void mxish_probe_complete(uint64_t owner,uint64_t waiter,uint32_t kind,int32_t result){
    mxuit_complete(owner,waiter,kind,result);
    if(kind==MXUIT_RETIRE)hold(4,owner); // Actual Swift completion returned; C completion tail remains.
}
void mxish_probe_progress(uint64_t callback,uint64_t entry,int32_t fault){
    mxuit_progress(callback,entry,fault);
    if(!fault)hold(5,0); // This remaining tail owns process scalars only.
}
int32_t mxuit_request(uint64_t owner,uint64_t waiter){
    pthread_mutex_lock(&probe.lock);probe.request_owner=owner;probe.request_waiter=waiter;pthread_mutex_unlock(&probe.lock);
    hold(7,owner);
    int32_t result=mxish_actual_request(owner,waiter);
    hold(6,owner); // Exact Swift rendezvous was published before this real call.
    return result;
}

int32_t mxuit_facade_try_reclaim(uint64_t facade){pthread_mutex_lock(&probe.lock);++probe.facade_calls;pthread_mutex_unlock(&probe.lock);hold(8,facade);return mxish_actual_facade_try_reclaim(facade);}
uint64_t mxish_probe_facade_calls(void){pthread_mutex_lock(&probe.lock);uint64_t n=probe.facade_calls;pthread_mutex_unlock(&probe.lock);return n;}
