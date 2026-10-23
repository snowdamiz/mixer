#define _POSIX_C_SOURCE 200809L
#include "ReclaimHold.h"
#include "mixer_ui_binding.h"
#include <pthread.h>
#include <time.h>
extern int32_t mxir_actual_try_reclaim(uint64_t owner);
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    uint64_t target, successes;
    int held, released;
} hold = {.lock=PTHREAD_MUTEX_INITIALIZER, .changed=PTHREAD_COND_INITIALIZER};
int32_t mxir_arm(uint64_t owner) {
    pthread_mutex_lock(&hold.lock);
    int32_t result = !owner || hold.target ? MXUIT_INVALID : MXUIT_OK;
    if (result == MXUIT_OK) hold.target=owner;
    pthread_mutex_unlock(&hold.lock); return result;
}
int32_t mxuit_try_reclaim(uint64_t owner) {
    /* Exact original C call once, actual result preserved without alteration. */
    int32_t actual=mxir_actual_try_reclaim(owner);
    pthread_mutex_lock(&hold.lock);
    if (owner==hold.target && actual==MXUIT_OK) {
        ++hold.successes; hold.held=1; pthread_cond_broadcast(&hold.changed);
        while (!hold.released) pthread_cond_wait(&hold.changed,&hold.lock);
    }
    pthread_mutex_unlock(&hold.lock); return actual;
}
int32_t mxir_wait(void) {
    struct timespec deadline; clock_gettime(CLOCK_REALTIME,&deadline); deadline.tv_sec+=10;
    pthread_mutex_lock(&hold.lock);
    while(!hold.held) if(pthread_cond_timedwait(&hold.changed,&hold.lock,&deadline)) {
        pthread_mutex_unlock(&hold.lock); return MXUIT_BUSY;
    }
    pthread_mutex_unlock(&hold.lock); return MXUIT_OK;
}
void mxir_release(void) {
    pthread_mutex_lock(&hold.lock); hold.released=1;
    pthread_cond_broadcast(&hold.changed); pthread_mutex_unlock(&hold.lock);
}
uint64_t mxir_successes(void) {
    pthread_mutex_lock(&hold.lock); uint64_t count=hold.successes;
    pthread_mutex_unlock(&hold.lock); return count;
}
