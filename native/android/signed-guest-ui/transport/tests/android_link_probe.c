#include "../include/mixer_ui_transport.h"
/* Cross-link probe only. These deliberately inert test link symbols are never
 * included in an application or treated as Android UI execution evidence. The
 * production transport has no weak fallback for either required binding hook. */
int32_t mxuit_drain(uint64_t owner, uint64_t waiter, uint32_t kind) {
    (void)owner; (void)waiter; (void)kind; return MXUIT_DRAIN_FAILED;
}
void mxuit_complete(uint64_t owner, uint64_t waiter, uint32_t kind, int32_t result) {
    (void)owner; (void)waiter; (void)kind; (void)result;
}
__attribute__((visibility("default"))) int32_t mxuit_android_link_probe(void) {
    return mxuit_install();
}
