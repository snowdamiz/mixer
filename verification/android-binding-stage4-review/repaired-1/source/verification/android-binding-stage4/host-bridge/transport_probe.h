#ifndef MIXER_TRANSPORT_PROBE_H
#define MIXER_TRANSPORT_PROBE_H
#include <stdint.h>
int32_t mxish_probe_arm(uint32_t point, uint64_t identity);
int32_t mxish_probe_wait(void);
void mxish_probe_release(void);
uint64_t mxish_probe_reclaim_calls(void);
uint64_t mxish_probe_facade_calls(void);
uint64_t mxish_probe_request_owner(void);
uint64_t mxish_probe_request_waiter(void);
int32_t mxish_probe_preempt_request(uint64_t owner, uint64_t waiter);
#endif
