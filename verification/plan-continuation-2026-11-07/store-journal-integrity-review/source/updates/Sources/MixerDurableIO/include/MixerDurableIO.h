#ifndef MIXER_DURABLE_IO_H
#define MIXER_DURABLE_IO_H
/* Owned shim for the POSIX function whose C struct tag collides in Swift. */
int mixer_update_flock(int descriptor, int operation);
#endif
