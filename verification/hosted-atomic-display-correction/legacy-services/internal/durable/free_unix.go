//go:build darwin || linux

package durable

import "syscall"

func AvailableBytes(path string) (uint64, error) {
	var stat syscall.Statfs_t
	if e := syscall.Statfs(path, &stat); e != nil {
		return 0, e
	}
	return uint64(stat.Bavail) * uint64(stat.Bsize), nil
}
