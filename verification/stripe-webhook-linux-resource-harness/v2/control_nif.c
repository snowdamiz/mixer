/* Private Linux/ERTS-only bootstrap. Fixed FD3; no path or FD selector.
 * NIF calls are nonblocking and bounded. No input bytes appear in errors.
 */
#define _GNU_SOURCE
#include "erl_nif.h"
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <linux/capability.h>

static ERL_NIF_TERM atom(ErlNifEnv *env, const char *name) { return enif_make_atom(env, name); }
static ERL_NIF_TERM secure_role(ErlNifEnv *env, int argc, const ERL_NIF_TERM argv[]) {
    (void)argv;
    if (argc != 0 || getuid() != 65534 || geteuid() != 65534 || getpid() != 2) return atom(env, "refused");
    struct rlimit core, size, files;
    if (getrlimit(RLIMIT_CORE, &core) || getrlimit(RLIMIT_FSIZE, &size) || getrlimit(RLIMIT_NOFILE, &files)
        || core.rlim_cur || core.rlim_max || size.rlim_cur || size.rlim_max
        || files.rlim_cur != 256 || files.rlim_max != 256) return atom(env, "refused");
    struct __user_cap_header_struct h = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct d[2];
    memset(d, 0, sizeof(d));
    if (syscall(SYS_capget, &h, d)) return atom(env, "refused");
    for (unsigned i = 0; i < 2; i++)
        if (d[i].effective || d[i].permitted || d[i].inheritable) return atom(env, "refused");
    if (prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1) return atom(env, "refused");
    int was_dumpable = prctl(PR_GET_DUMPABLE, 0, 0, 0, 0);
    if (was_dumpable < 0 || prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) || prctl(PR_GET_DUMPABLE, 0, 0, 0, 0) != 0)
        return atom(env, "refused");
    int type = 0;
    socklen_t size_type = sizeof(type);
    struct sockaddr_storage address;
    socklen_t size_address = sizeof(address);
    if (getsockopt(3, SOL_SOCKET, SO_TYPE, &type, &size_type) || type != SOCK_SEQPACKET
        || getsockname(3, (struct sockaddr *)&address, &size_address) || address.ss_family != AF_UNIX)
        return atom(env, "refused");
    int flags = fcntl(3, F_GETFL);
    if (flags < 0 || fcntl(3, F_SETFL, flags | O_NONBLOCK) < 0
        || fcntl(3, F_SETFD, FD_CLOEXEC) < 0) return atom(env, "refused");
    return enif_make_tuple2(env, atom(env, "ok"), enif_make_int(env, was_dumpable));
}
static ERL_NIF_TERM receive_control(ErlNifEnv *env, int argc, const ERL_NIF_TERM argv[]) {
    (void)argv;
    if (argc != 0) return atom(env, "refused");
    unsigned char data[257];
    union { struct cmsghdr align; unsigned char bytes[CMSG_SPACE(64 * sizeof(int))]; } ancillary;
    struct iovec iov = {data, sizeof(data)};
    struct msghdr msg;
    memset(&msg, 0, sizeof(msg));
    memset(&ancillary, 0, sizeof(ancillary));
    msg.msg_iov = &iov;
    msg.msg_iovlen = 1;
    msg.msg_control = ancillary.bytes;
    msg.msg_controllen = sizeof(ancillary.bytes);
    ssize_t n = recvmsg(3, &msg, MSG_DONTWAIT | MSG_CMSG_CLOEXEC);
    if (n < 0) return atom(env, errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR ? "again" : "refused");
    /* Close ALL received rights, including when another control item or truncation
     * also makes the message invalid. Linux closes rights discarded by truncation.
     */
    for (struct cmsghdr *c = CMSG_FIRSTHDR(&msg); c != NULL; c = CMSG_NXTHDR(&msg, c)) {
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS && c->cmsg_len >= CMSG_LEN(0)) {
            size_t count = (c->cmsg_len - CMSG_LEN(0)) / sizeof(int);
            for (size_t i = 0; i < count; i++) {
                int fd;
                memcpy(&fd, (unsigned char *)CMSG_DATA(c) + i * sizeof(int), sizeof(fd));
                if (fd >= 0) (void)close(fd);
            }
        }
    }
    if (msg.msg_controllen != 0 || (msg.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) || n > 256)
        return atom(env, "refused");
    if (n == 0) return atom(env, "closed");
    ERL_NIF_TERM binary;
    unsigned char *out = enif_make_new_binary(env, (size_t)n, &binary);
    if (out == NULL) return atom(env, "refused");
    memcpy(out, data, (size_t)n);
    return enif_make_tuple2(env, atom(env, "ok"), binary);
}
static ERL_NIF_TERM send_control(ErlNifEnv *env, int argc, const ERL_NIF_TERM argv[]) {
    ErlNifBinary binary;
    if (argc != 1 || !enif_inspect_binary(env, argv[0], &binary) || binary.size == 0 || binary.size > 256)
        return atom(env, "refused");
    ssize_t n = send(3, binary.data, binary.size, MSG_DONTWAIT | MSG_NOSIGNAL);
    return atom(env, n == (ssize_t)binary.size ? "ok" : "refused");
}
static ErlNifFunc funcs[] = {{"secure_role", 0, secure_role, 0},
    {"receive_control", 0, receive_control, 0}, {"send_control", 1, send_control, 0}};
ERL_NIF_INIT(Elixir.MixerHarness.Control, funcs, NULL, NULL, NULL, NULL)
