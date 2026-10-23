#ifndef MIXER_SCHEDULER_PROBE_H
#define MIXER_SCHEDULER_PROBE_H
#include <stdint.h>
int32_t mxish_scheduler_install_status(void);
int32_t mxish_scheduler_arm(uint64_t owner);
int32_t mxish_scheduler_wait(void);
uint64_t mxish_scheduler_captured_owner(void);
uint64_t mxish_scheduler_captured_waiter(void);
uint64_t mxish_scheduler_captured_jobs(void);
void mxish_scheduler_release(void);
int32_t mxish_scheduler_unhook(void);
#endif
