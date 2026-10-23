/* Review-only schedule barrier. Uses the actual host bridge lock/condition.
 * No transport, completion, result, or fence state is changed. */
static struct {
    uint64_t target;
    int held, released;
} review_complete;
void mxish_review_arm_completion(uint64_t owner) {
    pthread_mutex_lock(&host.lock);
    if (!owner || review_complete.target) abort();
    review_complete.target = owner;
    review_complete.held = review_complete.released = 0;
    pthread_mutex_unlock(&host.lock);
}
int32_t mxish_review_wait_completion(void) {
    struct timespec d = deadline();
    pthread_mutex_lock(&host.lock);
    while (!review_complete.held) {
        if (pthread_cond_timedwait(&host.changed, &host.lock, &d)) {
            pthread_mutex_unlock(&host.lock); return MXUIT_BUSY;
        }
    }
    pthread_mutex_unlock(&host.lock); return MXUIT_OK;
}
void mxish_review_release_completion(void) {
    pthread_mutex_lock(&host.lock);
    review_complete.released = 1;
    pthread_cond_broadcast(&host.changed);
    pthread_mutex_unlock(&host.lock);
}
void mxish_review_complete_checkpoint(uint64_t owner) {
    pthread_mutex_lock(&host.lock);
    if (review_complete.target == owner) {
        review_complete.held = 1;
        pthread_cond_broadcast(&host.changed);
        while (!review_complete.released) pthread_cond_wait(&host.changed, &host.lock);
        review_complete.target = 0;
    }
    pthread_mutex_unlock(&host.lock);
}
