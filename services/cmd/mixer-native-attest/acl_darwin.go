//go:build darwin && cgo

package main

/*
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>

static int check_acl(int fd) {
	struct statfs volume;
	if (fstatfs(fd, &volume) != 0)
		return errno;
	if (strcmp(volume.f_fstypename, "apfs") != 0 ||
	    !(volume.f_flags & MNT_LOCAL) || (volume.f_flags & MNT_IGNORE_OWNERSHIP))
		return ENOTSUP;

	filesec_t security = filesec_init();
	if (security == NULL)
		return ENOMEM;
	struct stat info;
	int result;
	if (fstatx_np(fd, &info, security) != 0) {
		result = errno;
	} else {
		// Query presence after a successful descriptor stat. Passing NULL
		// avoids converting the ACL and conflating absence with a parse error.
		if (filesec_get_property(security, FILESEC_ACL, NULL) == 0)
			result = -1;
		else
			result = errno == ENOENT ? 0 : errno;
	}
	filesec_free(security);
	return result;
}
*/
import "C"

import (
	"errors"
	"os"
	"syscall"
)

func requireNoACL(file *os.File) error {
	conn, err := file.SyscallConn()
	if err != nil {
		return err
	}
	var result C.int
	if err := conn.Control(func(fd uintptr) { result = C.check_acl(C.int(fd)) }); err != nil {
		return err
	}
	switch result {
	case 0:
		return nil
	case -1:
		return errors.New("extended ACL present")
	default:
		return syscall.Errno(result)
	}
}
