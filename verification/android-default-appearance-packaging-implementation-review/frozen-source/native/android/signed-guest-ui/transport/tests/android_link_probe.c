#include "../include/mixer_ui_transport.h"
/* Cross-link probe only. These deliberately inert test link symbols are never
 * included in an application or treated as Android UI execution evidence. The
 * production transport has no weak fallback for any required binding hook. */
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    (void)owner; (void)waiter; (void)kind; return MXUIT_DRAIN_FAILED;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    (void)owner; (void)waiter; (void)kind; (void)result;
}
#ifndef MXUIT_PROBE_OMIT_PROGRESS
void mxuit_progress(uint64_t callback_fence, uint64_t ui_entry_fence, int32_t sticky_fault) {
    (void)callback_fence; (void)ui_entry_fence; (void)sticky_fault;
}
#endif
__attribute__((visibility("default"))) int32_t mxuit_android_link_probe(void) {
    return mxuit_install();
}
