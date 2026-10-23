#ifndef MIXER_CAPABILITY_DURABLE_IO_H
#define MIXER_CAPABILITY_DURABLE_IO_H
/* Owned shim for the POSIX function whose C struct tag collides in Swift. */
int mixer_capability_update_flock(int descriptor, int operation);
#endif
